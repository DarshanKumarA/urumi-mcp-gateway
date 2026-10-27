"""Bounded OpenRouter client tools adapter; execution stays in InvocationService."""
import asyncio
import json

import httpx2

from .chat import SYSTEM, ChatError, Turn


class OpenRouterProvider:
    def __init__(self, key, model, timeout=30, *, transport=None):
        if not key or not model or len(model) > 128 or not 1 <= timeout <= 60:
            raise ValueError("CHAT_CONFIGURATION_INVALID")
        self.model, self.timeout = model, timeout
        self.client = httpx2.AsyncClient(
            headers={"Authorization": "Bearer " + key},
            timeout=timeout, follow_redirects=False, trust_env=False,
            transport=transport or httpx2.AsyncHTTPTransport(retries=0))

    async def close(self):
        await self.client.aclose()

    async def turn(self, message, tools, history):
        from .provider import suppress_provider_wire_logs
        suppress_provider_wire_logs()
        try:
            declarations = []
            for tool in tools:
                if len(json.dumps(tool.input_schema)) > 16000:
                    raise ChatError("CHAT_SCHEMA_LIMIT")
                declarations.append({"type": "function", "function": {
                    "name": tool.name, "description": (tool.description or "Gateway tool")[:500],
                    "parameters": tool.input_schema}})
            body = {"model": self.model, "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": message}, *history],
                "max_tokens": 4096, "stream": False,
                "provider": {"allow_fallbacks": False, "require_parameters": True}}
            if declarations:
                body["tools"] = declarations
            async with asyncio.timeout(self.timeout):
                async with self.client.stream("POST", "https://openrouter.ai/api/v1/chat/completions",
                                              json=body) as response:
                    if response.status_code != 200:
                        code = {401: "PROVIDER_AUTH_FAILED", 403: "PROVIDER_AUTH_FAILED",
                                402: "PROVIDER_QUOTA", 429: "PROVIDER_RATE_LIMIT"}.get(
                                    response.status_code, "PROVIDER_UNAVAILABLE")
                        raise ChatError(code)
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 262144:
                            raise ChatError("PROVIDER_INVALID_RESPONSE")
            payload = json.loads(data)
            choices = payload["choices"]
            if len(choices) != 1 or choices[0]["finish_reason"] not in ("stop", "tool_calls"):
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            source = choices[0]["message"]
            if source.get("role") != "assistant":
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            text = source.get("content") or ""
            if not isinstance(text, str):
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            raw_calls = source.get("tool_calls") or []
            if not isinstance(raw_calls, list) or len(raw_calls) > 4:
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            calls, wire_calls, ids = [], [], set()
            for call in raw_calls:
                ident, function = call["id"], call["function"]
                if (call["type"] != "function" or not isinstance(ident, str)
                        or not ident or len(ident) > 256 or ident in ids
                        or not isinstance(function["name"], str)
                        or not isinstance(function["arguments"], str)
                        or len(function["arguments"]) > 16000):
                    raise ChatError("PROVIDER_INVALID_RESPONSE")
                args = json.loads(function["arguments"])
                if not isinstance(args, dict):
                    raise ChatError("PROVIDER_INVALID_RESPONSE")
                ids.add(ident)
                calls.append({"name": function["name"], "arguments": args})
                wire_calls.append({"id": ident, "type": "function", "function": {
                    "name": function["name"], "arguments": function["arguments"]}})
            content = {"role": "assistant", "content": text or None}
            if wire_calls:
                content["tool_calls"] = wire_calls
            # Some providers require their opaque reasoning details on the next turn.
            if "reasoning_details" in source:
                content["reasoning_details"] = source["reasoning_details"]
            return Turn(text, calls, content)
        except (TimeoutError, httpx2.TimeoutException):
            raise ChatError("PROVIDER_TIMEOUT") from None
        except ChatError:
            raise
        except httpx2.TransportError:
            raise ChatError("PROVIDER_UNAVAILABLE") from None
        except Exception:
            raise ChatError("PROVIDER_INVALID_RESPONSE") from None

    def exchange(self, turn, results):
        calls = turn.content.get("tool_calls", [])
        if len(calls) != len(results):
            raise ChatError("PROVIDER_INVALID_RESPONSE")
        messages = [turn.content]
        for call, result in zip(calls, results):
            if call["function"]["name"] != result["name"]:
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result["result"])})
        return messages
