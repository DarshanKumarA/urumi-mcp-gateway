"""Exactly one authenticated read. Output is fixed evidence, never a raw response."""

import asyncio
import json
import logging
import socket
from urllib.parse import urlsplit

from .config import Config, Credentials
from .woocommerce import PATH, WooClient, WooError, is_demo_product


async def run():
    # Diagnostic/debug logging of signing internals or HTTP traffic is prohibited.
    logging.disable(logging.CRITICAL)
    config = Config()
    evidence = {"connection_origin": config.connection_origin,
                "canonical_origin": config.canonical_origin, "path": PATH,
                "host": config.host, "dns_resolved": False,
                "authorization_supplied": False, "redirect": False}
    try:
        credentials = Credentials.from_directory(config.secret_directory)
        async with asyncio.timeout(3):
            await asyncio.get_running_loop().getaddrinfo(
                urlsplit(config.connection_origin).hostname, 80, type=socket.SOCK_STREAM)
        evidence["dns_resolved"] = True
        async with WooClient(config, credentials) as client:
            evidence["authorization_supplied"] = True
            product = await client.lookup_product("URUMI-DEMO-001")
        evidence["http_status"] = 200
        # Only the exact expected public product may reach this diagnostic's output.
        if not is_demo_product(product):
            raise WooError("UNEXPECTED_PRODUCT", 200)
        evidence.update({"result": "PASS", "product": product})
        print(json.dumps(evidence))
        return 0
    except WooError as error:
        evidence.update({"result": "FAIL", "code": error.code, "http_status": error.status,
                         "redirect": error.status is not None and 300 <= error.status < 400})
    except (OSError, TimeoutError):
        evidence.update({"result": "FAIL", "code": "WOO_UNREACHABLE"})
    except Exception:
        # Suppress exception details/tracebacks; they can retain credentials or payloads.
        evidence.update({"result": "FAIL", "code": "LOCAL_CONFIGURATION_OR_CLIENT_ERROR"})
    print(json.dumps(evidence))
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
