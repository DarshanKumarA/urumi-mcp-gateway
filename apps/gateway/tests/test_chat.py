"""No real provider or store calls. Real session/audit/repository/core boundaries."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID
import httpx2
from mcp.types import Tool, ToolAnnotations, CallToolResult, TextContent
from urumi_gateway.api import create_app
from urumi_gateway.chat import Turn, ChatError, sanitize, Message
from urumi_gateway.models import Upstream, Timeouts
from urumi_gateway.mcp_auth import Principal
from test_persistence import DatabaseFixture
from test_identity import PASSWORD

ORIGIN="http://127.0.0.1:8000"
class ScriptedProvider:
    def __init__(self, turns): self.turns=list(turns); self.histories=[]
    async def turn(self,message,tools,history):
        self.histories.append(list(history))
        value=self.turns.pop(0)
        if isinstance(value,Exception): raise value
        return value
    def exchange(self,turn,results): return results

class FixtureUpstream:
    timeouts=Timeouts(1,1)
    def __init__(self): self.calls=[]; self.fail=False
    async def discover(self,server):
        names={'woocommerce':['list_orders','create_product'],'arithmetic':['sum_amounts'],'store_policy':['get_policy']}[server.slug]
        return [Tool(name=n,description='Untrusted fixture description',input_schema={'type':'object'},
            annotations=ToolAnnotations(read_only_hint=n!='create_product')) for n in names]
    async def call(self,server,name,args,**kwargs):
        self.calls.append((server.slug,name,args))
        await asyncio.sleep(.001)
        if self.fail: return CallToolResult(is_error=True,content=[TextContent(type='text',text='private fixture response')])
        data={'list_orders':{'items':[{'id':12,'total':'499','payment_method':'cod'}]},
              'sum_amounts':{'total':'499','average':'499'},'get_policy':{'key':'cod','guidance':'Collect on delivery'},
              'create_product':{'created':True,'product':{'id':99}}}[name]
        return CallToolResult(content=[],structured_content=data)

def call(name, args=None): return Turn('',[{'name':name,'arguments':args or {}}])
class ChatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=DatabaseFixture();self.up=FixtureUpstream()
        for slug in ('woocommerce','arithmetic','store_policy'):
            await self.db.repo.add(Upstream(slug,slug,'http://localhost:9000/mcp'))
        self.provider=ScriptedProvider([Turn('Fixture answer',[])])
        self.app=create_app(self.db.repo,upstream=self.up,provider=self.provider)
        self.identity=self.app.state.identity
        self.admin=await self.identity.bootstrap_admin('fixture_admin',PASSWORD)
        invite=await self.identity.invite(self.admin,'fixture_member')
        self.member=await self.identity.accept(invite['token'],PASSWORD)
        self.http=httpx2.AsyncClient(base_url=ORIGIN,transport=httpx2.ASGITransport(app=self.app),headers={'Origin':ORIGIN})
        await self.http.post('/api/auth/login',json={'username':'fixture_member','password':PASSWORD})
    async def asyncTearDown(self):
        await self.http.aclose();self.db.close()
    async def run_turns(self,turns):
        self.provider.turns=turns
        response=await self.http.post('/api/chat',json={'message':'Synthetic operational request'})
        self.assertEqual(response.status_code,200);return response.json()
    async def test_no_tool_answer(self):
        r=await self.run_turns([Turn('Hello',[])]);self.assertEqual(r,dict(answer='Hello',trace=[],error=None))
        self.assertEqual((await self.app.state.audits.list_events())['total'],0)
    async def test_one_tool_audit_session(self):
        r=await self.run_turns([call('woocommerce__list_orders'),Turn('One order',[])])
        self.assertEqual(len(r['trace']),1)
        row=(await self.app.state.audits.list_events())['items'][0]
        self.assertEqual(row['user_id'],self.member['id']);self.assertEqual(row['auth_source'],'session')
        self.assertIsNone(row['api_key_id']);self.assertEqual(row['outcome'],'succeeded')
    async def test_arithmetic_composition(self):
        r=await self.run_turns([call('woocommerce__list_orders',{'date':'today'}),call('arithmetic__sum_amounts',{'amounts':['499']}),Turn('Total 499; average 499',[])])
        self.assertEqual([x['tool'] for x in r['trace']],['woocommerce__list_orders','arithmetic__sum_amounts'])
        self.assertIn('items',self.provider.histories[1][0]['result'])
    async def test_policy_composition(self):
        r=await self.run_turns([call('woocommerce__list_orders'),call('store_policy__get_policy',{'key':'cod'}),Turn('Collect on delivery',[])])
        self.assertEqual(len(r['trace']),2);self.assertIsNone(r['error'])
    async def test_product_create_once(self):
        r=await self.run_turns([call('woocommerce__create_product',{'name':'Fixture','price':'5'}),Turn('Created',[])])
        self.assertIsNone(r['error']);self.assertEqual(len(self.up.calls),1)
    async def test_duplicate_write_blocked(self):
        c=call('woocommerce__create_product',{'name':'Fixture','price':'5'})
        r=await self.run_turns([c,c]);self.assertEqual(r['error'],'CHAT_WRITE_REPEAT_BLOCKED');self.assertEqual(len(self.up.calls),1)
    async def test_unknown_tool(self):
        r=await self.run_turns([call('unknown__action')]);self.assertEqual(r['error'],'CHAT_UNKNOWN_TOOL');self.assertEqual(self.up.calls,[])
    async def test_disabled_server(self):
        s=await self.db.repo.get_by_slug('woocommerce');await self.db.repo.edit(s.id,enabled=False)
        r=await self.run_turns([call('woocommerce__list_orders')]);self.assertEqual(r['error'],'CHAT_UNKNOWN_TOOL');self.assertEqual(self.up.calls,[])
    async def test_provider_timeout(self):
        r=await self.run_turns([ChatError('PROVIDER_TIMEOUT')]);self.assertEqual(r['error'],'PROVIDER_TIMEOUT')
    async def test_provider_rate_limit(self):
        r=await self.run_turns([ChatError('PROVIDER_RATE_LIMIT')]);self.assertEqual(r['error'],'PROVIDER_RATE_LIMIT')
    async def test_max_rounds(self):
        self.app.state.chat.max_rounds=1
        r=await self.run_turns([call('woocommerce__list_orders'),call('woocommerce__list_orders')]);self.assertEqual(r['error'],'CHAT_ROUND_LIMIT');self.assertEqual(len(self.up.calls),1)
    async def test_failure_stops_no_replay(self):
        self.up.fail=True
        r=await self.run_turns([call('woocommerce__create_product')]);self.assertEqual(r['error'],'CHAT_TOOL_FAILED');self.assertEqual(len(self.up.calls),1)
        self.assertNotIn('private fixture',json.dumps(r));self.assertEqual(r['trace'][0]['outcome'],'failed')
    async def test_concurrent_session_attribution(self):
        class ConcurrentProvider(ScriptedProvider):
            async def turn(self,message,tools,history):
                await asyncio.sleep(.005)
                return Turn('done',[]) if history else call('woocommerce__list_orders')
        self.app.state.chat.provider=ConcurrentProvider([])
        principals=[Principal(u['id'],u['username'],u['role'],None,'session') for u in (self.admin,self.member)]
        replies=await asyncio.gather(*(self.app.state.chat.run(p,'fixture') for p in principals))
        self.assertTrue(all(r['error'] is None for r in replies))
        rows=(await self.app.state.audits.list_events())['items']
        self.assertEqual({r['user_id'] for r in rows},{self.admin['id'],self.member['id']})
        self.assertTrue(all(r['api_key_id'] is None and r['auth_source']=='session' for r in rows))
    async def test_no_identity_input(self):
        r=await self.http.post('/api/chat',json={'message':'Hi','user_id':str(self.admin['id'])});self.assertEqual(r.status_code,422)
    async def test_same_origin_required(self):
        r=await self.http.post('/api/chat',json={'message':'Hi'},headers={'Origin':'http://foreign.invalid'});self.assertEqual(r.status_code,403)
    async def test_session_required(self):
        self.http.cookies.clear();r=await self.http.post('/api/chat',json={'message':'Hi'});self.assertEqual(r.status_code,401)
    async def test_member_catalog(self):
        r=await self.http.get('/api/catalog');self.assertEqual(r.status_code,200)
        self.assertEqual(len(r.json()['tools']),4);self.assertNotIn('credential',r.text)
        self.assertEqual((await self.http.get('/api/servers')).status_code,403)
    async def test_not_configured(self):
        self.app.state.chat.provider=None;r=await self.run_turns([]);self.assertEqual(r['error'],'CHAT_NOT_CONFIGURED')
    async def test_malformed_response(self):
        r=await self.run_turns([Turn('',[])]);self.assertEqual(r['error'],'PROVIDER_INVALID_RESPONSE')
    async def test_start_failure_zero_dispatch(self):
        with patch.object(self.app.state.audits,'start',new=AsyncMock(side_effect=RuntimeError('fixture'))):
            r=await self.run_turns([call('woocommerce__create_product')])
        self.assertEqual(r['error'],'CHAT_TOOL_FAILED');self.assertEqual(self.up.calls,[])
    async def test_safe_provider_exception(self):
        r=await self.run_turns([RuntimeError('sensitive fixture exception')]);self.assertNotIn('sensitive',json.dumps(r))
    async def test_empty_and_oversized_message(self):
        for value in ('   ','a'*4001):
            self.assertEqual((await self.http.post('/api/chat',json={'message':value})).status_code,422)

class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_provider_wire_logs_are_suppressed(self):
        import logging
        from urumi_gateway.provider import suppress_provider_wire_logs
        logger = logging.getLogger('google_genai._api_client')
        suppress_provider_wire_logs()
        with self.assertNoLogs(logger, level='WARNING'):
            logger.warning('synthetic private wire content')

    def test_private_fields_removed(self):
        self.assertEqual(sanitize({'id':12,'billing':{'private':'hidden'},'email':'hidden','items':[{'order_key':'hidden','quantity':1}]}),{'id':12,'items':[{'quantity':1}]})
    async def test_sdk_configuration_and_signature_preservation(self):
        from google.genai import types
        from urumi_gateway.provider import GeminiProvider
        with patch('urumi_gateway.provider.genai.Client') as client:
            model_content=types.Content(role='model',parts=[types.Part(function_call=types.FunctionCall(name='arithmetic__sum_amounts',args={'amounts':['1']}),thought_signature=b'synthetic-signature')])
            client.return_value.aio.models.generate_content=AsyncMock(return_value=types.GenerateContentResponse(candidates=[types.Candidate(content=model_content)]))
            p=GeminiProvider('synthetic-provider-fixture-only')
            t=Tool(name='arithmetic__sum_amounts',input_schema={'type':'object'})
            r=await p.turn('test',[t],[])
            config=client.return_value.aio.models.generate_content.call_args.kwargs['config']
            self.assertTrue(config.automatic_function_calling.disable)
            self.assertEqual(client.call_args.kwargs['http_options'].retry_options.attempts,1)
            self.assertEqual(p.exchange(r,[{'name':t.name,'result':{'total':'1'}}])[0],model_content)
    async def test_sdk_timeout_sanitized(self):
        from urumi_gateway.provider import GeminiProvider
        with patch('urumi_gateway.provider.genai.Client') as client:
            client.return_value.aio.models.generate_content=AsyncMock(side_effect=TimeoutError('secret'))
            with self.assertRaisesRegex(ChatError,'PROVIDER_TIMEOUT'):
                await GeminiProvider('synthetic-provider-fixture-only').turn('test',[],[])

    async def test_sdk_auth_rate_and_other_failures_are_sanitized(self):
        from google.genai import errors
        from urumi_gateway.provider import GeminiProvider
        for status, expected in ((401, 'PROVIDER_AUTH_FAILED'), (403, 'PROVIDER_AUTH_FAILED'),
                                 (429, 'PROVIDER_RATE_LIMIT'), (500, 'PROVIDER_UNAVAILABLE')):
            with self.subTest(status=status), patch('urumi_gateway.provider.genai.Client') as client:
                client.return_value.aio.models.generate_content = AsyncMock(
                    side_effect=errors.APIError(status, {'message': 'private fixture details'}))
                with self.assertRaises(ChatError) as caught:
                    await GeminiProvider('synthetic-provider-fixture-only').turn('test', [], [])
                self.assertEqual(str(caught.exception), expected)
                self.assertEqual(client.return_value.aio.models.generate_content.await_count, 1)

    async def test_sdk_truncated_answer_is_not_success(self):
        from google.genai import types
        from urumi_gateway.provider import GeminiProvider
        with patch('urumi_gateway.provider.genai.Client') as client:
            client.return_value.aio.models.generate_content = AsyncMock(return_value=
                types.GenerateContentResponse(candidates=[types.Candidate(
                    content=types.Content(parts=[types.Part(text='Incomplete answer')]),
                    finish_reason=types.FinishReason.MAX_TOKENS)]))
            with self.assertRaisesRegex(ChatError, 'PROVIDER_INVALID_RESPONSE'):
                await GeminiProvider('synthetic-provider-fixture-only').turn('test', [], [])
