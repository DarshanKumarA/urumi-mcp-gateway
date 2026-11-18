"""Bounded Kubernetes Secret store. Database values are opaque references only."""
import base64
import json
import os
from pathlib import Path
import re
import ssl
from uuid import uuid4
import httpx2

PREFIX = "k8s-secret:"

class CredentialStoreUnavailable(Exception):
    def __init__(self): super().__init__("CREDENTIAL_STORE_UNAVAILABLE")

class UnavailableStore:
    def get(self, reference): raise CredentialStoreUnavailable()
    def put(self, value): raise CredentialStoreUnavailable()

class KubernetesCredentialStore:
    def __init__(self, namespace, name, *, directory="/run/kubernetes", transport=None):
        if not all(re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,252}", x) for x in (namespace, name)):
            raise CredentialStoreUnavailable()
        self.directory = Path(directory)
        self.url = "https://kubernetes.default.svc/api/v1/namespaces/" + namespace + "/secrets/" + name
        self.transport = transport

    def request(self, method, body=None):
        from .provider import suppress_provider_wire_logs
        suppress_provider_wire_logs()
        try:
            token = (self.directory / "token").read_text().strip()
            verify = ssl.create_default_context(cafile=str(self.directory / "ca.crt")) if self.transport is None else True
            with httpx2.Client(verify=verify, trust_env=False, follow_redirects=False,
                              timeout=5, transport=self.transport) as client:
                with client.stream(method, self.url, headers={"Authorization": "Bearer " + token}, json=body) as r:
                    if r.status_code == 409: return None
                    if r.status_code != 200: raise CredentialStoreUnavailable()
                    raw = bytearray()
                    for chunk in r.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 1500000: raise CredentialStoreUnavailable()
                    result = json.loads(raw)
                    if result.get("type") != "Opaque" or result.get("metadata", {}).get("deletionTimestamp"):
                        raise CredentialStoreUnavailable()
                    return result
        except Exception:
            raise CredentialStoreUnavailable() from None

    def get(self, reference):
        try:
            key = reference.removeprefix(PREFIX)
            if reference != PREFIX + key or not re.fullmatch(r"[a-f0-9]{32}", key): raise ValueError()
            obj = self.request("GET")
            value = base64.b64decode(obj["data"][key], validate=True).decode("utf-8")
            if not value or len(value) > 16000: raise ValueError()
            return value
        except Exception:
            raise CredentialStoreUnavailable() from None

    def put(self, value):
        if not isinstance(value, str) or not value or len(value) > 16000: raise CredentialStoreUnavailable()
        key = uuid4().hex
        encoded = base64.b64encode(value.encode()).decode()
        for attempt in range(3):
            obj = self.request("GET")
            if obj is None: raise CredentialStoreUnavailable()
            data = obj.setdefault("data", {})
            data[key] = encoded
            # Leave space below Kubernetes' 1 MiB decoded Secret limit.
            if len(json.dumps(data)) > 900000: raise CredentialStoreUnavailable()
            result = self.request("PUT", obj)
            if result is not None:
                reference = PREFIX + key
                if self.get(reference) != value: raise CredentialStoreUnavailable()
                return reference
        raise CredentialStoreUnavailable()


def from_environment():
    return KubernetesCredentialStore(os.environ["URUMI_NAMESPACE"], os.environ["URUMI_UPSTREAM_SECRET_NAME"])


def migrate_credentials(connection, store):
    """Copy and verify before replacing values; caller commits one DB transaction.

    Secret entries are append-only, so failed DB transactions leave safe orphans,
    never broken existing references. Retention also preserves in-flight readers.
    """
    import sqlalchemy as sa
    if not sa.inspect(connection).has_table("mcp_servers"): return
    rows = connection.execute(sa.text("SELECT id, credential_value FROM mcp_servers WHERE credential_value IS NOT NULL")).mappings()
    for row in list(rows):
        value = row["credential_value"]
        if value.startswith(PREFIX):
            store.get(value)
            continue
        ref = store.put(value)
        if store.get(ref) != value: raise CredentialStoreUnavailable()
        connection.execute(sa.text("UPDATE mcp_servers SET credential_value=:ref WHERE id=:id"), {"ref":ref,"id":row["id"]})
