"""Synthetic OpenRouter wire fixtures; no provider or upstream requests."""
import json
import unittest
from types import SimpleNamespace
import httpx2
from urumi_gateway.openrouter import OpenRouterProvider
from urumi_gateway.chat import ChatError

TOOL = SimpleNamespace(name="woocommerce__list_orders", description="Orders",
                       input_schema={"type": "object"})


class OpenRouterTests(unittest.IsolatedAsyncioTestCase):
    async def run_response(self, response, *, tools=()):
        self.requests = []
        def handle(request):
            self.requests.append(request)
            if isinstance(response, Exception):
                raise response
            return response
        p = OpenRouterProvider("SYNTHETIC-ONLY", "fixture/model", transport=httpx2.MockTransport(handle))
        try:
            return await p.turn("hello", tools, [])
        finally:
            await p.close()

    async def test_text_and_request_contract(self):
        turn = await self.run_response(httpx2.Response(200, json={"choices": [{
            "finish_reason": "stop", "message": {"role": "assistant", "content": "OK"}}]}))
        self.assertEqual(turn.text, "OK")
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/chat/completions")
        self.assertNotIn("SYNTHETIC-ONLY", str(request.url))
        body = json.loads(request.content)
        self.assertEqual(body["provider"], {"allow_fallbacks": False, "require_parameters": True})
        self.assertEqual(body["messages"][1]["content"], "hello")

    async def test_tool_schema_and_id_roundtrip(self):
        message = {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1",
            "type": "function", "function": {"name": TOOL.name, "arguments": '{"date":"today"}'}}]}
        turn = await self.run_response(httpx2.Response(200, json={"choices": [{
            "finish_reason": "tool_calls", "message": message}]}), tools=[TOOL])
        self.assertEqual(turn.calls, [{"name": TOOL.name, "arguments": {"date": "today"}}])
        body = json.loads(self.requests[0].content)
        self.assertEqual(body["tools"][0]["function"]["parameters"], TOOL.input_schema)
        p = OpenRouterProvider("SYNTHETIC-ONLY", "fixture/model")
        try:
            history = p.exchange(turn, [{"name": TOOL.name, "result": {"items": []}}])
            self.assertEqual(history[1]["tool_call_id"], "call_1")
            self.assertEqual(json.loads(history[1]["content"]), {"items": []})
        finally:
            await p.close()

    async def test_status_errors_are_sanitized_without_retry(self):
        for status, code in [(401,"PROVIDER_AUTH_FAILED"),(402,"PROVIDER_QUOTA"),
                             (429,"PROVIDER_RATE_LIMIT"),(503,"PROVIDER_UNAVAILABLE"),
                             (302,"PROVIDER_UNAVAILABLE")]:
            with self.subTest(status=status):
                with self.assertRaises(ChatError) as caught:
                    await self.run_response(httpx2.Response(status, text="PRIVATE UPSTREAM BODY"))
                self.assertEqual(str(caught.exception), code)
                self.assertEqual(len(self.requests), 1)

    async def test_timeout_no_retry(self):
        with self.assertRaisesRegex(ChatError, '^PROVIDER_TIMEOUT$'):
            await self.run_response(httpx2.ReadTimeout("PRIVATE"))
        self.assertEqual(len(self.requests), 1)

    async def test_malformed_response(self):
        with self.assertRaisesRegex(ChatError, '^PROVIDER_INVALID_RESPONSE$'):
            await self.run_response(httpx2.Response(200, text="PRIVATE"))

    async def test_oversized_response(self):
        with self.assertRaisesRegex(ChatError, '^PROVIDER_INVALID_RESPONSE$'):
            await self.run_response(httpx2.Response(200, content=b'x'*262145))

    async def test_tool_arguments_must_be_object(self):
        with self.assertRaisesRegex(ChatError, '^PROVIDER_INVALID_RESPONSE$'):
            await self.run_response(httpx2.Response(200, json={"choices": [{"finish_reason":"tool_calls",
                "message":{"role":"assistant","tool_calls":[{"id":"a","type":"function",
                "function":{"name":TOOL.name,"arguments":"[]"}}]}}]}))
