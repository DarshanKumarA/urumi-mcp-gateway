"""One-read REST client foundation. No MCP, writes, redirects or retries."""

import asyncio
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER

from .config import Config, Credentials

PATH = "/wp-json/wc/v3/products"
FIELDS = "id,name,sku,price,status,stock_status"
MAX_BYTES = 65536


class WooError(Exception):
    """Fixed safe code only: never retain upstream messages or request objects."""

    def __init__(self, code, status=None):
        super().__init__(code)
        self.code = code
        self.status = status


def product_urls(config, sku):
    if not isinstance(sku, str) or not 1 <= len(sku) <= 64 or any(ord(c) < 32 for c in sku):
        raise WooError("VALIDATION_ERROR")
    query = urlencode({"sku": sku, "per_page": 2, "_fields": FIELDS})
    suffix = PATH + "?" + query
    return config.canonical_origin + suffix, config.connection_origin + suffix


def normalize_product(data, sku):
    if not isinstance(data, list) or len(data) != 1:
        raise WooError("WOO_INVALID_RESPONSE")
    p = data[0]
    if not isinstance(p, dict):
        raise WooError("WOO_INVALID_RESPONSE")
    if (type(p.get("id")) is not int or p["id"] <= 0
            or not isinstance(p.get("name"), str) or not 1 <= len(p["name"]) <= 200
            or p.get("sku") != sku or p.get("status") not in {"publish", "draft", "pending", "private"}
            or p.get("stock_status") not in {"instock", "outofstock", "onbackorder"}
            or not isinstance(p.get("price"), str)
            or not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", p["price"])):
        raise WooError("WOO_INVALID_RESPONSE")
    return {key: p[key] for key in FIELDS.split(",")}


class WooClient:
    def __init__(self, config: Config, credentials: Credentials, *, transport=None):
        self.config = config
        self._signer = Client(credentials.consumer_key, client_secret=credentials.consumer_secret,
                              signature_method=SIGNATURE_HMAC_SHA256,
                              signature_type=SIGNATURE_TYPE_AUTH_HEADER)
        self._http = httpx.AsyncClient(
            transport=transport or httpx.AsyncHTTPTransport(retries=0),
            follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(connect=2, read=5, write=5, pool=1),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._http.aclose()

    async def lookup_product(self, sku):
        canonical, connection = product_urls(self.config, sku)
        try:
            async with asyncio.timeout(self.config.deadline_seconds):
                # OAuthLib owns all cryptography. Sign the Woo home origin, NOT Service DNS.
                _, headers, _ = self._signer.sign(canonical, http_method="GET")
                headers.update({"Host": self.config.host, "Accept": "application/json"})
                async with self._http.stream("GET", connection, headers=headers) as response:
                    status = response.status_code
                    if 300 <= status < 400:
                        raise WooError("WOO_CONFIGURATION_ERROR", status)
                    if status != 200:
                        code = {401: "WOO_AUTH_FAILED", 403: "WOO_FORBIDDEN",
                                404: "NOT_FOUND"}.get(status,
                                "WOO_UPSTREAM_ERROR" if status >= 500 else "WOO_REQUEST_REJECTED")
                        # Do not parse or echo upstream error bodies, headers or Location.
                        raise WooError(code, status)
                    content = bytearray()
                    async for part in response.aiter_bytes():
                        if len(content) + len(part) > MAX_BYTES:
                            raise WooError("WOO_RESPONSE_TOO_LARGE", status)
                        content.extend(part)
                    try:
                        product = normalize_product(json.loads(content), sku)
                    except (ValueError, TypeError):
                        raise WooError("WOO_INVALID_RESPONSE", status) from None
                    return product
        except (httpx.TimeoutException, TimeoutError):
            raise WooError("WOO_TIMEOUT") from None
        except httpx.RequestError:
            raise WooError("WOO_UNREACHABLE") from None


def is_demo_product(product):
    try:
        return (product["id"] == 11 and product["sku"] == "URUMI-DEMO-001"
                and product["name"] == "Urumi Demo Mug" and Decimal(product["price"]) == 499
                and product["status"] == "publish" and product["stock_status"] == "instock")
    except (KeyError, InvalidOperation):
        return False
