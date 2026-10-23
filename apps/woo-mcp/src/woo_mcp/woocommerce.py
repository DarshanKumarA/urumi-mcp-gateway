"""Shared REST reads. No writes, redirects or retries."""

import asyncio
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER

from .config import Config, Credentials
from .models import (GetOrderInput, ListOrdersInput, ListProductsInput, OrderCollection,
                     OrderDetail, Product, ProductCollection)
from .orders import DETAIL_FIELDS, SUMMARY_FIELDS, date_parameters, normalize_order, resolve_date_window

PATH = "/wp-json/wc/v3/products"
FIELDS = "id,name,sku,price,status,stock_status"
MAX_BYTES = 65536


class WooError(Exception):
    """Fixed safe code only; never expose upstream messages or request objects."""

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


def pagination(data, headers, query):
    counts = []
    for header in ("X-WP-Total", "X-WP-TotalPages"):
        values = headers.get_list(header)
        if len(values) != 1 or not re.fullmatch(r"[0-9]{1,10}", values[0]):
            raise ValueError()
        counts.append(int(values[0]))
    total, pages = counts
    if pages != (total + query.per_page - 1) // query.per_page:
        raise ValueError()
    expected_count = min(query.per_page, max(0, total - (query.page - 1) * query.per_page))
    if not isinstance(data, list) or len(data) != expected_count:
        raise ValueError()
    return total, pages


class WooClient:
    def __init__(self, config: Config, credentials: Credentials, *, transport=None):
        self.config = config
        self._signer = Client(credentials.consumer_key, client_secret=credentials.consumer_secret,
                              signature_method=SIGNATURE_HMAC_SHA256,
                              signature_type=SIGNATURE_TYPE_AUTH_HEADER)
        self._http = httpx.AsyncClient(
            transport=transport or httpx.AsyncHTTPTransport(
                retries=0, limits=httpx.Limits(max_connections=4, max_keepalive_connections=2)),
            follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(connect=2, read=5, write=5, pool=1),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._http.aclose()

    async def lookup_product(self, sku):
        canonical, connection = product_urls(self.config, sku)
        data, _ = await self._get(canonical, connection)
        return normalize_product(data, sku)

    async def list_products(self, query: ListProductsInput) -> ProductCollection:
        fields = [name for name in Product.model_fields if name != "currency"]
        params = query.model_dump(exclude_none=True)
        params["_fields"] = ",".join(fields)
        suffix = PATH + "?" + urlencode(params)
        data, headers = await self._get(self.config.canonical_origin + suffix,
                                        self.config.connection_origin + suffix)
        try:
            total, pages = pagination(data, headers, query)
            items = [Product.model_validate({**{key: item[key] for key in fields},
                                             "currency": self.config.currency}) for item in data]
            if len({item.id for item in items}) != len(items):
                raise ValueError()
            return ProductCollection(items=items, page=query.page, per_page=query.per_page,
                                     total=total, total_pages=pages, has_more=query.page < pages,
                                     currency=self.config.currency)
        except (ValueError, TypeError, KeyError, ValidationError):
            raise WooError("WOO_INVALID_RESPONSE") from None

    async def get_order(self, query: GetOrderInput) -> OrderDetail:
        suffix = f"/wp-json/wc/v3/orders/{query.order_id}?" + urlencode({"_fields": DETAIL_FIELDS})
        data, _ = await self._get(self.config.canonical_origin + suffix,
                                  self.config.connection_origin + suffix)
        try:
            result = normalize_order(data, detail=True)
            if result.id != query.order_id:
                raise ValueError()
            return result
        except (ValueError, TypeError, KeyError, OverflowError):
            raise WooError("WOO_INVALID_RESPONSE") from None

    async def list_orders(self, query: ListOrdersInput) -> OrderCollection:
        try:
            window = resolve_date_window(query.date, self.config.store_timezone)
        except (ValueError, OverflowError):
            raise WooError("VALIDATION_ERROR") from None
        params = query.model_dump(exclude_none=True, exclude={"date"})
        params["_fields"] = SUMMARY_FIELDS
        if window is not None:
            params.update(date_parameters(window))
        suffix = "/wp-json/wc/v3/orders?" + urlencode(params)
        data, headers = await self._get(self.config.canonical_origin + suffix,
                                        self.config.connection_origin + suffix)
        try:
            total, pages = pagination(data, headers, query)
            items = [normalize_order(item) for item in data]
            if len({item.id for item in items}) != len(items):
                raise ValueError()
            if window and any(not window.start_inclusive <= item.created_at < window.end_exclusive
                              for item in items):
                raise ValueError()
            return OrderCollection(items=items, page=query.page, per_page=query.per_page,
                                   total=total, total_pages=pages, has_more=query.page < pages,
                                   date_window=window)
        except (ValueError, TypeError, KeyError, OverflowError):
            raise WooError("WOO_INVALID_RESPONSE") from None

    async def _get(self, canonical, connection):
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
                        data = json.loads(content, parse_float=Decimal)
                    except (ValueError, TypeError):
                        raise WooError("WOO_INVALID_RESPONSE", status) from None
                    return data, response.headers
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
