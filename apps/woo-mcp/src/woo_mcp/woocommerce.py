"""Shared REST reads, product creation and guarded status updates. No retries."""

import asyncio
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER

from .config import Config, Credentials
from .models import (CreatedProduct, CreateProductInput, GetOrderInput, ListOrdersInput, ListProductsInput, OrderCollection,
                     OrderDetail, OrderStatusSnapshot, Product, ProductCollection,
                     UpdateOrderStatusInput, UpdatedOrderStatus)
from .orders import DETAIL_FIELDS, SUMMARY_FIELDS, date_parameters, normalize_order, resolve_date_window

PATH = "/wp-json/wc/v3/products"
FIELDS = "id,name,sku,price,status,stock_status"
MAX_BYTES = 65536


class WooError(Exception):
    """Fixed safe code only; never expose upstream messages or request objects."""

    def __init__(self, code, status=None, *, write_unknown=False):
        self.code = code
        self.status = status
        self.write_outcome = "unknown" if write_unknown else None
        self.retry_safe = False if write_unknown else None
        message = code + ("; write_outcome=unknown; retry_safe=false" if write_unknown else "")
        super().__init__(message)


class WooStateConflict(WooError):
    """Only validated status enums enter this safe conflict message."""

    def __init__(self, query: UpdateOrderStatusInput, observed: OrderStatusSnapshot):
        super().__init__("STATE_CONFLICT")
        self.args = (f"STATE_CONFLICT; expected_status={query.expected_status}; "
                     f"observed_status={observed.status}",)


def order_status_result(data, order_id):
    result = OrderStatusSnapshot.model_validate({"id": data["id"], "status": data["status"]})
    if result.id != order_id:
        raise ValueError()
    return result


def status_parameter_rejected(data):
    """Recognize WP's status-enum rejection, not localized messages/plugin guesses."""
    if not isinstance(data, dict) or data.get("code") != "rest_invalid_param":
        return False
    details = data.get("data")
    if not isinstance(details, dict) or details.get("status") != 400:
        return False
    params, errors = details.get("params"), details.get("details")
    if not isinstance(params, dict) or set(params) != {"status"} or not isinstance(errors, dict):
        return False
    error = errors.get("status")
    return isinstance(error, dict) and error.get("code") == "rest_not_in_enum"


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


def product_result(data, currency):
    return Product.model_validate({**{name: data[name] for name in Product.model_fields
                                      if name != "currency"}, "currency": currency})


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
            items = [product_result(item, self.config.currency) for item in data]
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

    async def create_product(self, query: CreateProductInput) -> CreatedProduct:
        if query.sku is not None:
            existing = await self.list_products(ListProductsInput(sku=query.sku, per_page=1))
            if existing.items:
                raise WooError("DUPLICATE_SKU")
        payload = {"name": query.name, "type": "simple", "regular_price": query.price,
                   "status": query.status, "stock_status": query.stock_status}
        if query.sku is not None:
            payload["sku"] = query.sku
        data, _ = await self._request("POST", self.config.canonical_origin + PATH,
                                      self.config.connection_origin + PATH, payload=payload)
        try:
            product = product_result(data, self.config.currency)
            if (product.type != "simple" or product.status != query.status
                    or product.stock_status != query.stock_status
                    or Decimal(product.regular_price) != Decimal(query.price)
                    or (query.sku is not None and product.sku != query.sku)):
                raise ValueError()
            return CreatedProduct(product=product)
        except (ValueError, TypeError, KeyError, InvalidOperation):
            # A bad response does not undo a possible committed product.
            raise WooError("WOO_INVALID_RESPONSE", write_unknown=True) from None

    async def update_order_status(self, query: UpdateOrderStatusInput) -> UpdatedOrderStatus:
        path = f"/wp-json/wc/v3/orders/{query.order_id}"
        # Fetch only identity/status. Never reuse a full customer-bearing order DTO.
        suffix = path + "?" + urlencode({"_fields": "id,status"})
        data, _ = await self._get(self.config.canonical_origin + suffix,
                                  self.config.connection_origin + suffix)
        try:
            before = order_status_result(data, query.order_id)
        except (ValueError, TypeError, KeyError):
            raise WooError("WOO_INVALID_RESPONSE") from None
        if before.status != query.expected_status:
            raise WooStateConflict(query, before)
        if before.status == query.status:
            return UpdatedOrderStatus(order_id=query.order_id, observed_before_status=before.status,
                                      after_status=before.status, changed=False)
        # Advisory guard only: another actor can write between this GET and PUT.
        data, _ = await self._request("PUT", self.config.canonical_origin + path,
                                      self.config.connection_origin + path,
                                      payload={"status": query.status})
        try:
            after = order_status_result(data, query.order_id)
            if after.status != query.status:
                raise ValueError()
            return UpdatedOrderStatus(order_id=query.order_id, observed_before_status=before.status,
                                      after_status=after.status, changed=True)
        except (ValueError, TypeError, KeyError):
            raise WooError("WOO_INVALID_RESPONSE", write_unknown=True) from None

    async def _get(self, canonical, connection):
        return await self._request("GET", canonical, connection)

    async def _request(self, method, canonical, connection, *, payload=None):
        writing = method in {"POST", "PUT"}
        attempted = False
        try:
            async with asyncio.timeout(self.config.deadline_seconds):
                # OAuthLib signs method + canonical origin. JSON is not included
                # as form parameters; HTTP OAuth does not protect this JSON body.
                headers_in = {"Content-Type": "application/json"} if writing else {}
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if writing else None
                _, headers, _ = self._signer.sign(canonical, http_method=method, headers=headers_in)
                headers.update({"Host": self.config.host, "Accept": "application/json"})
                attempted = writing  # Conservative: sending may fail after bytes leave.
                async with self._http.stream(method, connection, headers=headers, content=body) as response:
                    status = response.status_code
                    if 300 <= status < 400:
                        raise WooError("WOO_CONFIGURATION_ERROR", status, write_unknown=writing)
                    # Only inspect bounded structured evidence for known rejections.
                    sku_error = method == "POST" and status in (400, 409)
                    status_error = method == "PUT" and status == 400
                    if status != (201 if method == "POST" else 200) and not (sku_error or status_error):
                        code = {401: "WOO_AUTH_FAILED", 403: "WOO_FORBIDDEN",
                                404: "NOT_FOUND"}.get(status,
                                "WOO_UPSTREAM_ERROR" if status >= 500 else
                                "WOO_INVALID_RESPONSE" if writing and status < 300 else "WOO_REQUEST_REJECTED")
                        raise WooError(code, status, write_unknown=writing and
                                       (status >= 500 or status == 408 or status < 300))
                    content = bytearray()
                    async for part in response.aiter_bytes():
                        if len(content) + len(part) > MAX_BYTES:
                            raise WooError("WOO_RESPONSE_TOO_LARGE", status, write_unknown=writing)
                        content.extend(part)
                    try:
                        data = json.loads(content, parse_float=Decimal)
                    except (ValueError, TypeError, InvalidOperation):
                        raise WooError("WOO_INVALID_RESPONSE", status, write_unknown=writing) from None
                    if sku_error:
                        if isinstance(data, dict) and data.get("code") == "product_invalid_sku":
                            raise WooError("DUPLICATE_SKU", status)
                        raise WooError("WOO_REQUEST_REJECTED", status)
                    if status_error:
                        code = "INVALID_TRANSITION" if status_parameter_rejected(data) else "WOO_REQUEST_REJECTED"
                        raise WooError(code, status)
                    return data, response.headers
        except (httpx.TimeoutException, TimeoutError):
            raise WooError("WOO_TIMEOUT", write_unknown=attempted) from None
        except httpx.RequestError:
            raise WooError("WOO_UNREACHABLE", write_unknown=attempted) from None
        except WooError:
            raise
        except Exception:
            # No exception/request repr escapes, including unforeseen failures
            # after submission. Cancellation still propagates without replay.
            raise WooError("WOO_INTERNAL_ERROR", write_unknown=attempted) from None


def is_demo_product(product):
    try:
        return (product["id"] == 11 and product["sku"] == "URUMI-DEMO-001"
                and product["name"] == "Urumi Demo Mug" and Decimal(product["price"]) == 499
                and product["status"] == "publish" and product["stock_status"] == "instock")
    except (KeyError, InvalidOperation):
        return False
