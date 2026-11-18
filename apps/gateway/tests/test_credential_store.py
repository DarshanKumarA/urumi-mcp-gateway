"""Synthetic Secret API and transactional migration regression checks."""
import base64
import copy
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import httpx2
import sqlalchemy as sa
from urumi_gateway.credential_store import KubernetesCredentialStore, CredentialStoreUnavailable, migrate_credentials, PREFIX
from urumi_gateway.database import servers
from urumi_gateway.models import Credential, Upstream
from test_persistence import DatabaseFixture, MemoryCredentials

class SecretTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        Path(self.tmp.name, 'token').write_text('SYNTHETIC-TOKEN')
        self.obj = {'apiVersion':'v1','kind':'Secret','type':'Opaque',
                    'metadata':{'name':'vault','resourceVersion':'1'},'data':{}}
        self.calls=[]; self.conflicts=0
        def handle(r):
            self.calls.append(r)
            self.assertEqual(str(r.url),'https://kubernetes.default.svc/api/v1/namespaces/fixture/secrets/vault')
            if r.method == 'PUT':
                if self.conflicts:
                    self.conflicts-=1
                    return httpx2.Response(409)
                incoming=json.loads(r.content)
                self.assertEqual(incoming['metadata']['resourceVersion'], self.obj['metadata']['resourceVersion'])
                self.obj=incoming
                self.obj['metadata']['resourceVersion']=str(int(self.obj['metadata']['resourceVersion'])+1)
            return httpx2.Response(200,json=copy.deepcopy(self.obj))
        self.store=KubernetesCredentialStore('fixture','vault',directory=self.tmp.name,transport=httpx2.MockTransport(handle))
    def tearDown(self): self.tmp.cleanup()
    def test_roundtrip_and_append_preserve_old_values(self):
        first=self.store.put('SYNTHETIC-ONE');second=self.store.put('SYNTHETIC-TWO')
        self.assertNotEqual(first,second)
        self.assertEqual(self.store.get(first),'SYNTHETIC-ONE')
        self.assertEqual(self.store.get(second),'SYNTHETIC-TWO')
        self.assertTrue(first.startswith(PREFIX))
    def test_conflict_bounded_and_safe_retry(self):
        self.conflicts=1
        self.assertEqual(self.store.get(self.store.put('SYNTHETIC')),'SYNTHETIC')
        self.conflicts=3
        with self.assertRaisesRegex(CredentialStoreUnavailable,'^CREDENTIAL_STORE_UNAVAILABLE$'): self.store.put('PRIVATE')
    def test_missing_invalid_reference_and_bad_response_are_sanitized(self):
        for ref in ('PRIVATE', PREFIX+'a'*32):
            with self.assertRaises(CredentialStoreUnavailable): self.store.get(ref)
        self.store.transport=httpx2.MockTransport(lambda r:httpx2.Response(403,text='PRIVATE TOKEN'))
        with self.assertRaisesRegex(CredentialStoreUnavailable,'^CREDENTIAL_STORE_UNAVAILABLE$'): self.store.put('PRIVATE')
    def test_secret_limit_preserves_existing_data(self):
        self.obj['data']={'old':'x'*900000}
        with self.assertRaises(CredentialStoreUnavailable): self.store.put('PRIVATE')
        self.assertFalse(any(r.method=='PUT' for r in self.calls))
    def test_reads_rotated_service_account_token(self):
        self.store.put('SYNTHETIC')
        Path(self.tmp.name,'token').write_text('SYNTHETIC-ROTATED')
        self.store.request('GET')
        self.assertEqual(self.calls[-1].headers['Authorization'],'Bearer SYNTHETIC-ROTATED')

class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=DatabaseFixture()
        self.server=Upstream('fixture','Fixture','http://localhost/mcp',credential=Credential('bearer','SYNTHETIC-PRIVATE'))
        await self.db.repo.add(self.server)
    async def asyncTearDown(self): self.db.close()
    async def test_database_contains_reference_not_raw_credential(self):
        with self.db.engine.connect() as c:
            value=c.execute(sa.select(servers.c.credential_value)).scalar_one()
        self.assertTrue(value.startswith(PREFIX));self.assertNotIn('SYNTHETIC',value)
    async def test_copy_verify_then_migrate_is_idempotent(self):
        with self.db.engine.begin() as c:
            c.execute(servers.update().values(credential_value='SYNTHETIC-PRIVATE'))
            migrate_credentials(c,self.db.credentials)
        count=len(self.db.credentials.data)
        with self.db.engine.begin() as c: migrate_credentials(c,self.db.credentials)
        self.assertEqual(len(self.db.credentials.data),count)
        self.assertEqual((await self.db.repo.get(self.server.id)).credential.value,'SYNTHETIC-PRIVATE')
    async def test_failed_copy_keeps_old_database_value(self):
        with self.db.engine.begin() as c: c.execute(servers.update().values(credential_value='SYNTHETIC-PRIVATE'))
        with patch.object(self.db.credentials,'put',side_effect=CredentialStoreUnavailable()):
            with self.assertRaises(CredentialStoreUnavailable):
                with self.db.engine.begin() as c: migrate_credentials(c,self.db.credentials)
        with self.db.engine.connect() as c:
            self.assertEqual(c.execute(sa.select(servers.c.credential_value)).scalar_one(),'SYNTHETIC-PRIVATE')
