"""Order reads use mock REST only; all personal-looking fixture data is synthetic."""

import copy
import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from woo_mcp.config import Config
from woo_mcp.models import GetOrderInput, ListOrdersInput, OrderStatus
from woo_mcp.orders import date_parameters, resolve_date_window
from woo_mcp.woocommerce import WooClient, WooError
from test_products import CREDS, HEADERS
from typing import get_args

PRIVATE = {"billing": {"first_name": "SYNTHETIC-FIRST", "last_name": "SYNTHETIC-LAST",
                       "company": "SYNTHETIC-COMPANY", "email": "fixture@example.invalid",
                       "phone": "TEST-PHONE-NOT-A-NUMBER"},
           "shipping": {"address_1": "SYNTHETIC-ADDRESS"}, "customer_id": 999,
           "customer_note": "SYNTHETIC-NOTE", "order_key": "SYNTHETIC-ORDER-KEY",
           "meta_data": [{"key": "private", "value": "SYNTHETIC-METADATA"}]}
PRIVATE_TEXT = ("SYNTHETIC-", "fixture@example.invalid", "TEST-PHONE-NOT-A-NUMBER",
                "billing", "customer_id", "customer_note", "order_key", "meta_data")
ORDER = {"id": 12, "status": "processing", "date_created_gmt": "2026-10-21T02:24:15",
         "currency": "INR", "total": "499.00", "payment_method": "cod",
         "shipping_total": "0.00", "total_tax": "0.00", **PRIVATE,
         "line_items": [{"product_id": 11, "variation_id": 0, "name": "Urumi Demo Mug",
                         "sku": "URUMI-DEMO-001", "quantity": 1, "price": 499,
                         "subtotal": "499.00", "total": "499.00", **PRIVATE}],
         "shipping_lines": [{"method_id": "free_shipping", "method_title": "Free shipping",
                             "total": "0.00", **PRIVATE}]}


def assert_private_absent(test, text):
    for value in PRIVATE_TEXT + (CREDS.consumer_key, CREDS.consumer_secret):
        test.assertNotIn(value, text)


class OrderInputTests(unittest.TestCase):
    def test_get_id(self):
        self.assertEqual(GetOrderInput(order_id=12).order_id, 12)
        for args in ({}, {"order_id": 0}, {"order_id": -1}, {"order_id": True},
                     {"order_id": "12"}, {"order_id": 12.0}, {"order_id": 12, "extra": 1}):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                GetOrderInput.model_validate(args)

    def test_list_defaults_statuses(self):
        self.assertEqual(ListOrdersInput().model_dump(), dict(page=1, per_page=20, status=None, date=None))
        for status in get_args(OrderStatus):
            self.assertEqual(ListOrdersInput(status=status).status, status)

    def test_list_invalid(self):
        for args in ({"page": True}, {"page": 0}, {"per_page": "20"}, {"per_page": 51},
                     {"status": "trash"}, {"date": "2026-02-30"}, {"date": "20261021"},
                     {"date": "2026-1-1"}, {"date": 20261021}, {"date": " today "}, {"url": "x"}):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                ListOrdersInput.model_validate(args)

    def test_timezone_config(self):
        self.assertEqual(Config().store_timezone, "Asia/Kolkata")
        with self.assertRaises(ValueError):
            Config(store_timezone="not-a-zone")


class OrderDateTests(unittest.TestCase):
    def test_explicit_window_utc(self):
        window = resolve_date_window("2026-10-23", "Asia/Kolkata")
        self.assertEqual(window.start_inclusive.isoformat(), "2026-10-22T18:30:00+00:00")
        self.assertEqual(window.end_exclusive.isoformat(), "2026-10-23T18:30:00+00:00")
        self.assertEqual(date_parameters(window), dict(dates_are_gmt="true",
                         after="2026-10-22T18:29:59Z", before="2026-10-23T18:30:00Z"))

    def test_today_kolkata_midnight(self):
        for instant, expected in (("2026-10-22T18:29:59+00:00", "2026-10-22"),
                                  ("2026-10-22T18:30:00+00:00", "2026-10-23")):
            result = resolve_date_window("today", "Asia/Kolkata", now=datetime.fromisoformat(instant))
            self.assertEqual(result.date, expected)

    def test_strict_second_boundaries(self):
        w = resolve_date_window("2026-10-23", "Asia/Kolkata")
        params = date_parameters(w)
        after, before = (datetime.fromisoformat(params[k]) for k in ("after", "before"))
        for instant, included in ((w.start_inclusive-timedelta(seconds=1), False),
                                  (w.start_inclusive, True),
                                  (w.end_exclusive-timedelta(seconds=1), True),
                                  (w.end_exclusive, False)):
            self.assertEqual(after < instant < before, included)

    def test_leap_day_and_year_rollover(self):
        for day in ("2024-02-29", "2026-12-31"):
            w = resolve_date_window(day, "Asia/Kolkata")
            self.assertEqual(w.end_exclusive-w.start_inclusive, timedelta(days=1))

    def test_omitted_date_and_naive_clock(self):
        self.assertIsNone(resolve_date_window(None, "Asia/Kolkata"))
        with self.assertRaises(ValueError):
            resolve_date_window("today", "Asia/Kolkata", now=datetime(2026, 10, 23))


class OrderClientTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler, query=None, *, detail=False):
        async with WooClient(Config(), CREDS, transport=httpx.MockTransport(handler)) as client:
            return await (client.get_order(query or GetOrderInput(order_id=12)) if detail else
                          client.list_orders(query or ListOrdersInput()))

    async def test_detail_path_normalization_privacy(self):
        def handler(r):
            self.assertEqual(r.method, "GET")
            self.assertEqual(r.url.path, "/wp-json/wc/v3/orders/12")
            self.assertEqual(set(r.url.params), {"_fields"})
            self.assertEqual(r.headers["host"], "store.urumi.test:8080")
            self.assertNotIn(CREDS.consumer_key, str(r.url))
            return httpx.Response(200, json=ORDER)
        result = await self.request(handler, detail=True)
        self.assertEqual(result.id, 12)
        self.assertEqual(result.created_at.isoformat(), "2026-10-21T02:24:15+00:00")
        self.assertEqual(result.line_items[0].unit_price, "499")
        self.assertIsNone(result.line_items[0].variation_id)
        self.assertEqual(result.shipping_lines[0].method_id, "free_shipping")
        self.assertEqual(result.tax_total, "0.00")
        self.assertEqual(set(result.model_dump()), {"id", "status", "created_at", "currency", "total",
                         "payment_method", "line_items", "shipping_lines", "shipping_total", "tax_total"})
        assert_private_absent(self, result.model_dump_json())

    async def test_decimal_price_variation_deleted_product(self):
        data = copy.deepcopy(ORDER)
        data["line_items"][0].update(product_id=0, variation_id=23, sku=None)
        body = json.dumps(data).replace('"price": 499', '"price": 0.123456789012345678')
        result = await self.request(lambda r: httpx.Response(200, text=body), detail=True)
        self.assertEqual(result.line_items[0].unit_price, "0.123456789012345678")
        self.assertEqual(result.line_items[0].variation_id, 23)

    async def test_detail_malformed(self):
        for data in (None, [], {}, {**ORDER, "id": 13}, {**ORDER, "id": "12"},
                     {**ORDER, "date_created_gmt": None}, {**ORDER, "date_created_gmt": "2026-02-30T00:00:00"},
                     {**ORDER, "total": 499}, {**ORDER, "line_items": [PRIVATE]},
                     {**ORDER, "shipping_lines": None}, {**ORDER, "line_items": {}},
                     {**ORDER, "shipping_lines": {}}):
            with self.subTest(kind=type(data).__name__), self.assertRaisesRegex(WooError, "^WOO_INVALID_RESPONSE$"):
                await self.request(lambda r: httpx.Response(200, json=data), detail=True)

    async def test_bad_line_values(self):
        for update in ({"price": True}, {"quantity": "1"}, {"quantity": 0}, {"variation_id": False},
                       {"price": "499"}, {"price": -1}):
            data = copy.deepcopy(ORDER); data["line_items"][0].update(update)
            with self.subTest(update=update), self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda r: httpx.Response(200, json=data), detail=True)
        body = json.dumps(ORDER).replace('"price": 499', '"price": 1e999999')
        with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
            await self.request(lambda r: httpx.Response(200, text=body), detail=True)

    async def test_list_defaults_no_date_privacy(self):
        def handler(r):
            self.assertEqual(r.method, "GET")
            self.assertEqual(r.url.path, "/wp-json/wc/v3/orders")
            self.assertEqual(dict(r.url.params), dict(page="1", per_page="20",
                _fields="id,status,date_created_gmt,currency,total,payment_method"))
            return httpx.Response(200, json=[ORDER], headers=HEADERS)
        result = await self.request(handler)
        self.assertIsNone(result.date_window)
        self.assertFalse(result.has_more)
        self.assertEqual(set(result.items[0].model_dump()),
                         {"id", "status", "created_at", "currency", "total", "payment_method"})
        assert_private_absent(self, result.model_dump_json())

    async def test_statuses_and_pagination(self):
        for status in get_args(OrderStatus):
            def handler(r):
                self.assertEqual(r.url.params["status"], status)
                self.assertEqual(r.url.params["page"], "2")
                self.assertEqual(r.url.params["per_page"], "1")
                return httpx.Response(200, json=[{**ORDER, "status": status}],
                                      headers={"X-WP-Total": "3", "X-WP-TotalPages": "3"})
            result = await self.request(handler, ListOrdersInput(page=2, per_page=1, status=status))
            self.assertTrue(result.has_more)
            self.assertEqual(result.total, 3)

    async def test_explicit_date_request(self):
        def handler(r):
            self.assertEqual(r.url.params["after"], "2026-10-20T18:29:59Z")
            self.assertEqual(r.url.params["before"], "2026-10-21T18:30:00Z")
            self.assertEqual(r.url.params["dates_are_gmt"], "true")
            self.assertNotIn("date", r.url.params)
            return httpx.Response(200, json=[ORDER], headers=HEADERS)
        result = await self.request(handler, ListOrdersInput(date="2026-10-21"))
        self.assertEqual(result.date_window.date, "2026-10-21")

    async def test_today_resolved_once_before_request(self):
        import woo_mcp.orders as dates
        clock = datetime(2026, 10, 20, 18, 30, tzinfo=UTC)
        with patch.object(dates, "datetime", wraps=datetime) as fake:
            fake.now.side_effect = [clock, AssertionError("clock read twice")]
            result = await self.request(lambda r: httpx.Response(200, json=[ORDER], headers=HEADERS),
                                        ListOrdersInput(date="today"))
            self.assertEqual(result.date_window.date, "2026-10-21")
            fake.now.assert_called_once_with(UTC)

    async def test_runtime_boundary_guard(self):
        for timestamp, good in (("2026-10-20T18:29:59", False), ("2026-10-20T18:30:00", True),
                                ("2026-10-21T18:29:59", True), ("2026-10-21T18:30:00", False)):
            handler = lambda r: httpx.Response(200, json=[{**ORDER, "date_created_gmt": timestamp}], headers=HEADERS)
            if good:
                self.assertEqual((await self.request(handler, ListOrdersInput(date="2026-10-21"))).total, 1)
            else:
                with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                    await self.request(handler, ListOrdersInput(date="2026-10-21"))

    async def test_bad_pagination_and_duplicate_ids(self):
        for headers in ({}, {**HEADERS, "X-WP-Total": "-1"}, {**HEADERS, "X-WP-TotalPages": "2"},
                        {**HEADERS, "X-WP-Total": "1.0"}, {**HEADERS, "X-WP-Total": "2"},
                        [("X-WP-Total", "1"), ("X-WP-Total", "1"), ("X-WP-TotalPages", "1")]):
            with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda r: httpx.Response(200, json=[ORDER], headers=headers))
        with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
            await self.request(lambda r: httpx.Response(200, json=[ORDER, ORDER],
                               headers={"X-WP-Total": "2", "X-WP-TotalPages": "1"}))

    async def test_empty_list(self):
        result = await self.request(lambda r: httpx.Response(200, json=[],
                                   headers={"X-WP-Total": "0", "X-WP-TotalPages": "0"}))
        self.assertEqual(result.items, [])
        self.assertFalse(result.has_more)

    async def test_malformed_summary(self):
        for data in ([None], [{}], {"items": [ORDER]}, [{**ORDER, "currency": "invalid"}],
                     [{**ORDER, "status": "unknown"}], [{**ORDER, "date_created_gmt": "bad"}]):
            with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda r: httpx.Response(200, json=data, headers=HEADERS))

    async def test_unrepresentable_window_no_request(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(500)
        for day in ("0001-01-01", "9999-12-31"):
            with self.assertRaisesRegex(WooError, "VALIDATION_ERROR"):
                await self.request(handler, ListOrdersInput(date=day))
        self.assertEqual(calls, [])

    async def test_safe_errors_no_retry_both_operations(self):
        for detail in (False, True):
            for status, code in ((401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"), (404, "NOT_FOUND"),
                                 (422, "WOO_REQUEST_REJECTED"), (500, "WOO_UPSTREAM_ERROR"),
                                 (302, "WOO_CONFIGURATION_ERROR")):
                calls = []
                def handler(r):
                    calls.append(r)
                    return httpx.Response(status, json=PRIVATE)
                with self.assertRaises(WooError) as raised:
                    await self.request(handler, detail=detail)
                self.assertEqual(str(raised.exception), code)
                assert_private_absent(self, str(raised.exception))
                self.assertEqual(len(calls), 1)

    async def test_transport_errors_both_operations(self):
        for detail in (False, True):
            for error, code in ((httpx.ConnectError("SYNTHETIC-PRIVATE"), "WOO_UNREACHABLE"),
                                (httpx.ReadTimeout("SYNTHETIC-PRIVATE"), "WOO_TIMEOUT")):
                def handler(r):
                    raise error
                with self.assertRaisesRegex(WooError, "^"+code+"$"):
                    await self.request(handler, detail=detail)

    async def test_bad_json_oversize_both_operations(self):
        for detail in (False, True):
            for body, code in ((b"not json", "WOO_INVALID_RESPONSE"),
                               (b"x" * 65537, "WOO_RESPONSE_TOO_LARGE")):
                with self.assertRaisesRegex(WooError, "^"+code+"$"):
                    await self.request(lambda r: httpx.Response(200, content=body), detail=detail)
