"""Official Google GenAI adapter. Manual bounded tool execution, no SDK auto calls."""
import asyncio
import json
import logging
import os
from pathlib import Path
from google import genai
from google.genai import types, errors
from .chat import SYSTEM, Turn, ChatError

class _DiscardWireLog(logging.Filter):
    def filter(self, record):
        return False

def suppress_provider_wire_logs():
    # The pinned SDK/HTTP libraries may log request details or provider messages.
    # Keep application error codes, never their wire-level bodies or headers.
    prefixes = ("google_genai", "httpx", "httpcore")
    for name in set(logging.Logger.manager.loggerDict) | set(prefixes):
        if any(name == p or name.startswith(p + ".") for p in prefixes):
            logger = logging.getLogger(name)
            if not any(isinstance(f, _DiscardWireLog) for f in logger.filters):
                logger.addFilter(_DiscardWireLog())

class GeminiProvider:
    def __init__(self, key, model="gemini-3.8-flash", timeout=30):
        if not key or not 1 <= timeout <= 60 or not model or len(model)>100:
            raise ValueError("CHAT_CONFIGURATION_INVALID")
        self.model, self.timeout=model,timeout
        self.client=genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout*1000,
            retry_options=types.HttpRetryOptions(attempts=1)))
        suppress_provider_wire_logs()

    async def close(self):
        await self.client.aio.aclose()
        self.client.close()

    async def turn(self, message, tools, history):
        suppress_provider_wire_logs()
        try:
            declarations=[]
            for t in tools:
                # Preserve JSON schema; descriptions are bounded data, never system policy.
                schema=t.input_schema
                if len(json.dumps(schema))>16000: raise ChatError("CHAT_SCHEMA_LIMIT")
                declarations.append(types.FunctionDeclaration(name=t.name,
                    description=(t.description or "Gateway tool")[:500],parameters_json_schema=schema))
            config=types.GenerateContentConfig(system_instruction=SYSTEM,
                tools=[types.Tool(function_declarations=declarations)] if declarations else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                max_output_tokens=4096)
            async with asyncio.timeout(self.timeout):
                response=await self.client.aio.models.generate_content(model=self.model,
                    contents=[types.Content(role="user",parts=[types.Part(text=message)]),*history],config=config)
            if not response.candidates or len(response.candidates)!=1: raise ChatError("PROVIDER_INVALID_RESPONSE")
            if response.candidates[0].finish_reason not in (None, types.FinishReason.STOP):
                raise ChatError("PROVIDER_INVALID_RESPONSE")
            content=response.candidates[0].content
            if not content or not content.parts: raise ChatError("PROVIDER_INVALID_RESPONSE")
            calls=[]; text=[]
            for part in content.parts:
                if part.function_call:
                    calls.append({"name":part.function_call.name,"arguments":part.function_call.args})
                elif part.text and not part.thought: text.append(part.text)
            return Turn("\n".join(text),calls,content)
        except TimeoutError: raise ChatError("PROVIDER_TIMEOUT") from None
        except errors.APIError as error:
            code={401:"PROVIDER_AUTH_FAILED",403:"PROVIDER_AUTH_FAILED",429:"PROVIDER_RATE_LIMIT"}.get(error.code,"PROVIDER_UNAVAILABLE")
            raise ChatError(code) from None
        except ChatError: raise
        except Exception: raise ChatError("PROVIDER_INVALID_RESPONSE") from None

    def exchange(self, turn, results):
        # Preserve the complete model Content, including Gemini thought signatures.
        return [turn.content,types.Content(role="user",parts=[types.Part.from_function_response(
            name=r["name"],response=r["result"]) for r in results])]


def from_environment():
    file=os.environ.get("URUMI_GEMINI_API_KEY_FILE")
    key=Path(file).read_text(encoding="utf-8").strip() if file else os.environ.get("GEMINI_API_KEY")
    if not key: return None
    return GeminiProvider(key,os.environ.get("URUMI_GEMINI_MODEL","gemini-3.8-flash"),
                          int(os.environ.get("URUMI_PROVIDER_TIMEOUT_SECONDS","30")))
