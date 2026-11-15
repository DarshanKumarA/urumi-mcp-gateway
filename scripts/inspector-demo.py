"""Read-only external prompt acceptance using the official MCP Inspector CLI.

Run with the gateway virtual environment. Secrets are prompted without echo;
--stdin-credentials is for protected in-memory automation, never a credential file.
The model sees gateway tool schemas/results, never the gateway or provider key.
"""
import argparse
import asyncio
import getpass
import json
import logging
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/gateway/src"))
from mcp.types import Tool
from urumi_gateway.openrouter import OpenRouterProvider

READ_TOOLS = {"woocommerce__list_orders", "woocommerce__get_order",
              "woocommerce__list_products", "arithmetic__sum_amounts",
              "store_policy__get_policy"}


def inspect(args, key, method, tool=None, arguments=None):
    request = dict(url=args.url, key=key, method=method, tool=tool, arguments=arguments)
    result = subprocess.run(
        [str(args.node), str(ROOT / "scripts/inspector-bridge.mjs"), str(args.inspector.resolve())],
        input=json.dumps(request), capture_output=True, text=True, timeout=60,
        encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        # Never print subprocess output on failure: it can contain untrusted content.
        raise RuntimeError("INSPECTOR_FAILED (check endpoint, key, revocation and runtime)")
    if len(result.stdout) > 2 * 1024 * 1024:
        raise RuntimeError("INSPECTOR_RESULT_LIMIT")
    if key in result.stdout:
        raise RuntimeError("CREDENTIAL_REFLECTION_REJECTED")
    data = json.loads(result.stdout)["result"]
    if data.get("isError"):
        raise RuntimeError("TOOL_FAILED; no retry performed")
    return data


async def run(args, credentials):
    key = credentials["gateway_key"]
    catalog = await asyncio.to_thread(inspect, args, key, "tools/list")
    print(json.dumps({"client": "MCP Inspector 2.15.0", "endpoint": args.url,
                      "tools": [t["name"] for t in catalog["tools"]]}), flush=True)
    if args.discovery_only:
        return
    tools = [Tool.model_validate(t) for t in catalog["tools"] if t["name"] in READ_TOOLS]
    provider = OpenRouterProvider(credentials["provider_key"], args.model)
    history, count = [], 0
    try:
        for round_number in range(5):
            turn = await provider.turn(args.prompt, tools, history)
            if not turn.calls:
                answer = turn.text
                for secret in credentials.values():
                    answer = answer.replace(secret, "[redacted]")
                print(json.dumps({"answer": answer}), flush=True)
                return
            results = []
            for call in turn.calls:
                count += 1
                if count > 10 or call["name"] not in READ_TOOLS:
                    raise RuntimeError("READ_ONLY_CALL_LIMIT")
                data = await asyncio.to_thread(inspect, args, key, "tools/call",
                                              call["name"], call["arguments"])
                result = data.get("structuredContent")
                if result is None:
                    raise RuntimeError("STRUCTURED_RESULT_REQUIRED")
                safe = json.dumps({"tool": call["name"], "arguments": call["arguments"],
                                   "result": result})
                if any(secret in safe for secret in credentials.values()):
                    raise RuntimeError("CREDENTIAL_REFLECTION_REJECTED")
                print(safe, flush=True)
                results.append({"name": call["name"], "result": result})
            history.extend(provider.exchange(turn, results))
        raise RuntimeError("PROMPT_ROUND_LIMIT")
    finally:
        await provider.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://gateway.urumi.test:8080/mcp")
    parser.add_argument("--node", type=Path, default=ROOT / ".venv/inspector/node_modules/node/bin/node.exe")
    parser.add_argument("--inspector", type=Path, default=ROOT / ".venv/inspector/node_modules/@modelcontextprotocol/inspector/clients/cli/build/index.js")
    parser.add_argument("--model", default="z-ai/glm-5.3-flash")
    parser.add_argument("--prompt", default="What orders came in today, and what are their total and average order values? Use WooCommerce and Arithmetic, include order IDs and store timezone, and verify pagination.")
    parser.add_argument("--discovery-only", action="store_true")
    parser.add_argument("--stdin-credentials", action="store_true")
    args = parser.parse_args()
    target = urlsplit(args.url)
    if target.scheme not in {"http", "https"} or not target.hostname or target.username or target.password or target.query or target.fragment:
        parser.error("Use a plain HTTP(S) gateway endpoint without credentials or query parameters")
    if not args.node.is_file() or not args.inspector.is_file():
        parser.error("Install Inspector and a supported Node runtime; see docs/demo.md")
    logging.disable(logging.CRITICAL)
    try:
        if args.stdin_credentials:
            data = sys.stdin.read(16385)
            if len(data) > 16384:
                raise ValueError("INPUT_LIMIT")
            credentials = json.loads(data)
        else:
            credentials = {"gateway_key": getpass.getpass("User B gateway API key: ")}
            if not args.discovery_only:
                credentials["provider_key"] = getpass.getpass("OpenRouter API key (client LLM): ")
        required = {"gateway_key"} | (set() if args.discovery_only else {"provider_key"})
        if not required <= credentials.keys() or any(not isinstance(credentials[k], str) or not credentials[k] for k in required):
            raise ValueError("CREDENTIAL_INPUT_INVALID")
        asyncio.run(run(args, credentials))
        return 0
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
    except Exception as error:
        # Do not expose credentials, provider response bodies, or exception reprs.
        print("External acceptance failed: " + type(error).__name__ + "; details suppressed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
