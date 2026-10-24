"""Guarded order updates use dummy credentials and mock REST exclusively."""

import asyncio
import copy
import json
import unittest
from typing import get_args
from unittest.mock import patch

import httpx
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER
from pydantic import ValidationError

from woo_mcp.config import Config
from woo_mcp.models import OrderStatus, UpdateOrderStatusInput, WritableOrderStatus
from woo_mcp.woocommerce import WooClient, WooError
from test_orders import ORDER, PRIVATE, assert_private_absent
from test_products import CREDS

UPDATE = {"order_id": 12, "status": "completed", "expected_status": "processing"}
STATUS_REJECTION = {
    "code": "rest_invalid_param", "message": "SYNTHETIC-PRIVATE",
    "data": {"status": 400, "params": {"status": "SYNTHETIC-PRIVATE"},
             "details": {"status": {"code": "rest_not_in_enum", "message": "SYNTHETIC-PRIVATE"}}},
}


class UpdateInputTests(unittest.TestCase):
    def test_valid_status_sets(self):
        for status in get_args(WritableOrderStatus):
            for expected in get_args(OrderStatus):
                self.assertEqual(UpdateOrderStatusInput(order_id=12, status=status,
                    expected_status=expected).model_dump(),
                    dict(order_id=12, status=status, expected_status=expected))

    def test_invalid_id(self):
        for value in (0, -1, True, "12", 12.0, None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                UpdateOrderStatusInput.model_validate({**UPDATE, "order_id": value})

    def test_invalid_targets(self):
        for value in ("refunded", "trash", "checkout-draft", "wc-processing", "custom", " completed ", 1, None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                UpdateOrderStatusInput.model_validate({**UPDATE, "status": value})

    def test_invalid_expected_status(self):
        for value in ("trash", "checkout-draft", "custom", "wc-processing", True, None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                UpdateOrderStatusInput.model_validate({**UPDATE, "expected_status": value})

    def test_required_fields_and_extras(self):
        for key in UPDATE:
            with self.assertRaises(ValidationError):
                UpdateOrderStatusInput.model_validate({k: v for k, v in UPDATE.items() if k != key})
        for key in ("metadata", "refund", "url", "customer_note"):
            with self.assertRaises(ValidationError):
                UpdateOrderStatusInput.model_validate({**UPDATE, key: "SYNTHETIC-PRIVATE"})


class UpdateClientTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler, values=None, config=None):
        self.calls = []
        def tracked(request):
            self.calls.append(request.method)
            return handler(request)
        async with WooClient(config or Config(), CREDS, transport=httpx.MockTransport(tracked)) as client:
            return await client.update_order_status(UpdateOrderStatusInput.model_validate(values or UPDATE))

    def assert_calls(self, puts):
        self.assertEqual(self.calls.count("GET"), 1)
        self.assertEqual(self.calls.count("PUT"), puts)
        self.assertEqual(self.calls, ["GET"] + ["PUT"] * puts)

    def assert_error(self, error, code, unknown=False):
        self.assertEqual(error.code, code)
        self.assertEqual(error.write_outcome, "unknown" if unknown else None)
        self.assertIs(error.retry_safe, False if unknown else None)
        self.assertEqual(str(error), code + ("; write_outcome=unknown; retry_safe=false" if unknown else ""))
        assert_private_absent(self, str(error))
        self.assertNotIn("Authorization", str(error))

    async def test_exact_get_put_payload_signature_and_private_normalization(self):
        def handler(request):
            self.assertEqual(request.url.path, "/wp-json/wc/v3/orders/12")
            self.assertEqual(request.url.host, "urumi-wordpress.urumi.svc.cluster.local")
            self.assertEqual(request.headers["host"], "store.urumi.test:8080")
            if request.method == "GET":
                self.assertEqual(dict(request.url.params), {"_fields": "id,status"})
                self.assertEqual(request.content, b"")
                return httpx.Response(200, json=ORDER)
            self.assertEqual(request.method, "PUT")
            self.assertEqual(dict(request.url.params), {})
            self.assertEqual(json.loads(request.content), {"status": "completed"})
            self.assertEqual(request.headers["content-type"], "application/json")
            signer = Client(CREDS.consumer_key, client_secret=CREDS.consumer_secret,
                            signature_method=SIGNATURE_HMAC_SHA256, signature_type=SIGNATURE_TYPE_AUTH_HEADER,
                            nonce="fixture-nonce", timestamp="1700000000")
            expected = signer.sign("http://store.urumi.test:8080/wp-json/wc/v3/orders/12", http_method="PUT",
                                   headers={"Content-Type": "application/json"})[1]["Authorization"]
            self.assertEqual(request.headers["authorization"], expected)
            for secret in (CREDS.consumer_key, CREDS.consumer_secret, "oauth_"):
                self.assertNotIn(secret, str(request.url))
                self.assertNotIn(secret, request.content.decode())
            return httpx.Response(200, json={**ORDER, "status": "completed"})
        with patch("oauthlib.oauth1.rfc5849.generate_nonce", return_value="fixture-nonce"), patch(
                "oauthlib.oauth1.rfc5849.generate_timestamp", return_value="1700000000"):
            result = await self.request(handler)
        self.assertEqual(result.model_dump(), dict(order_id=12, observed_before_status="processing",
                                                  after_status="completed", changed=True))
        assert_private_absent(self, result.model_dump_json())
        self.assert_calls(1)

    async def test_missing_order_and_other_get_errors_never_put(self):
        for status, code in ((404, "NOT_FOUND"), (401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"),
                             (400, "WOO_REQUEST_REJECTED"), (500, "WOO_UPSTREAM_ERROR"),
                             (302, "WOO_CONFIGURATION_ERROR")):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(status, json=PRIVATE))
            self.assert_error(raised.exception, code)
            self.assert_calls(0)

    async def test_get_network_failure_is_not_write_ambiguity(self):
        for error, code in ((httpx.ReadTimeout("SYNTHETIC-PRIVATE"), "WOO_TIMEOUT"),
                            (httpx.ConnectError("SYNTHETIC-PRIVATE"), "WOO_UNREACHABLE")):
            def handler(request):
                raise error
            with self.assertRaises(WooError) as raised:
                await self.request(handler)
            self.assert_error(raised.exception, code)
            self.assert_calls(0)

    async def test_bad_get_identity_status_and_payload_never_put(self):
        for data in (None, [], {}, {"id": 13, "status": "processing"}, {"id": "12", "status": "processing"},
                     {"id": 12, "status": "checkout-draft"}, {"id": 12, "status": PRIVATE}):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(200, json=data))
            self.assert_error(raised.exception, "WOO_INVALID_RESPONSE")
            self.assert_calls(0)

    async def test_conflict_precedes_noop_and_never_puts(self):
        # Target already equals current, but caller's expected value is stale.
        with self.assertRaises(WooError) as raised:
            await self.request(lambda r: httpx.Response(200, json={**ORDER, "status": "completed"}))
        self.assertEqual(str(raised.exception),
                         "STATE_CONFLICT; expected_status=processing; observed_status=completed")
        self.assertEqual(raised.exception.code, "STATE_CONFLICT")
        self.assertIsNone(raised.exception.write_outcome)
        assert_private_absent(self, str(raised.exception))
        self.assert_calls(0)

    async def test_same_status_noop_all_targets(self):
        for status in get_args(WritableOrderStatus):
            result = await self.request(lambda r: httpx.Response(200, json={"id": 12, "status": status}),
                                        {**UPDATE, "status": status, "expected_status": status})
            self.assertEqual(result.model_dump(), dict(order_id=12, observed_before_status=status,
                                                       after_status=status, changed=False))
            self.assert_calls(0)

    async def test_refunded_can_be_observed_without_invented_transition_matrix(self):
        result = await self.request(lambda r: httpx.Response(200, json={"id": 12,
            "status": "refunded" if r.method == "GET" else "processing"}),
            {**UPDATE, "expected_status": "refunded", "status": "processing"})
        self.assertTrue(result.changed)
        self.assertEqual(result.observed_before_status, "refunded")
        self.assert_calls(1)

    async def test_non_atomic_guard_does_not_prevent_intervening_write(self):
        store = {"status": "processing"}
        def handler(request):
            if request.method == "GET":
                response = httpx.Response(200, json={"id": 12, **store})
                store["status"] = "on-hold"  # Simulated concurrent administrator.
                return response
            self.assertEqual(store["status"], "on-hold")
            store.update(json.loads(request.content))
            return httpx.Response(200, json={"id": 12, **store})
        result = await self.request(handler)
        self.assertEqual(result.observed_before_status, "processing")
        self.assertEqual(store["status"], "completed")
        self.assert_calls(1)

    async def test_wrong_status_identity_or_malformed_put_is_unknown(self):
        for data in (None, [], {}, {"id": 13, "status": "completed"}, {"id": "12", "status": "completed"},
                     {"id": 12, "status": "processing"}, {"id": 12, "status": "custom"},
                     {"id": 12, "status": PRIVATE}):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(200, json=ORDER if r.method == "GET" else data))
            self.assert_error(raised.exception, "WOO_INVALID_RESPONSE", True)
            self.assert_calls(1)

    async def test_put_network_failures_one_attempt_unknown(self):
        for error, code in ((httpx.ReadTimeout("SYNTHETIC-PRIVATE"), "WOO_TIMEOUT"),
                            (httpx.WriteTimeout("SYNTHETIC-PRIVATE"), "WOO_TIMEOUT"),
                            (httpx.ConnectError("SYNTHETIC-PRIVATE"), "WOO_UNREACHABLE"),
                            (httpx.ReadError("SYNTHETIC-PRIVATE"), "WOO_UNREACHABLE")):
            def handler(request):
                if request.method == "GET":
                    return httpx.Response(200, json=ORDER)
                raise error
            with self.assertRaises(WooError) as raised:
                await self.request(handler)
            self.assert_error(raised.exception, code, True)
            self.assert_calls(1)

    async def test_put_http_ambiguity_never_retries_or_reconciles(self):
        for status, code in ((500, "WOO_UPSTREAM_ERROR"), (503, "WOO_UPSTREAM_ERROR"),
                             (408, "WOO_REQUEST_REJECTED"), (302, "WOO_CONFIGURATION_ERROR"),
                             (307, "WOO_CONFIGURATION_ERROR"), (201, "WOO_INVALID_RESPONSE"),
                             (202, "WOO_INVALID_RESPONSE"), (204, "WOO_INVALID_RESPONSE")):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(200, json=ORDER) if r.method == "GET" else
                                   httpx.Response(status, json=PRIVATE, headers={"Location": "http://invalid"}))
            self.assert_error(raised.exception, code, True)
            self.assert_calls(1)

    async def test_clear_status_parameter_rejection(self):
        with self.assertRaises(WooError) as raised:
            await self.request(lambda r: httpx.Response(200, json=ORDER) if r.method == "GET" else
                               httpx.Response(400, json=STATUS_REJECTION))
        self.assert_error(raised.exception, "INVALID_TRANSITION")
        self.assert_calls(1)

    async def test_generic_rejection_not_guessed_from_code_or_message(self):
        cases = [PRIVATE, {"code": "unknown_plugin_code", "message": "Invalid transition"},
                 {"code": "rest_invalid_param"}, {"code": "rest_invalid_param", "data": []}]
        for field, value in (("params", {"other": "bad"}), ("params", {"status": "bad", "other": "bad"}),
                             ("details", {"status": {"code": "unrecognized"}}), ("status", 422)):
            case = copy.deepcopy(STATUS_REJECTION)
            case["data"][field] = value
            cases.append(case)
        for data in cases:
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(200, json=ORDER) if r.method == "GET" else
                                   httpx.Response(400, json=data))
            self.assert_error(raised.exception, "WOO_REQUEST_REJECTED")
            self.assert_calls(1)

    async def test_other_rejected_put_responses(self):
        for status, code in ((401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"), (404, "NOT_FOUND"),
                             (409, "WOO_REQUEST_REJECTED"), (422, "WOO_REQUEST_REJECTED"),
                             (429, "WOO_REQUEST_REJECTED")):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(200, json=ORDER) if r.method == "GET" else
                                   httpx.Response(status, json=STATUS_REJECTION))
            self.assert_error(raised.exception, code)
            self.assert_calls(1)

    async def test_json_and_size_failure_distinguish_get_from_put(self):
        for phase in ("GET", "PUT"):
            for body, code in ((b"SYNTHETIC-PRIVATE", "WOO_INVALID_RESPONSE"),
                               (b"x" * 65537, "WOO_RESPONSE_TOO_LARGE")):
                with self.assertRaises(WooError) as raised:
                    await self.request(lambda r: httpx.Response(200, content=body) if r.method == phase else
                                       httpx.Response(200, json=ORDER))
                self.assert_error(raised.exception, code, phase == "PUT")
                self.assert_calls(int(phase == "PUT"))

    async def test_unusable_rejection_body_is_conservative(self):
        with self.assertRaises(WooError) as raised:
            await self.request(lambda r: httpx.Response(200, json=ORDER) if r.method == "GET" else
                               httpx.Response(400, text="SYNTHETIC-PRIVATE malformed"))
        self.assert_error(raised.exception, "WOO_INVALID_RESPONSE", True)
        self.assert_calls(1)

    async def test_committed_update_lost_response_stays_unknown(self):
        store = {"id": 12, "status": "processing"}
        class LostResponse(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{"id":12,'
                raise httpx.ReadError("SYNTHETIC-PRIVATE lost response")
        def handler(request):
            if request.method == "GET":
                return httpx.Response(200, json=store)
            store.update(json.loads(request.content))
            return httpx.Response(200, stream=LostResponse())
        with self.assertRaises(WooError) as raised:
            await self.request(handler)
        self.assert_error(raised.exception, "WOO_UNREACHABLE", True)
        self.assertEqual(store["status"], "completed")
        self.assert_calls(1)

    async def test_deadline_get_vs_put(self):
        for phase in ("GET", "PUT"):
            async def handler(request):
                if request.method == phase:
                    await asyncio.sleep(1)
                return httpx.Response(200, json=ORDER)
            with self.assertRaises(WooError) as raised:
                await self.request(handler, config=Config(deadline_seconds=0.01))
            self.assert_error(raised.exception, "WOO_TIMEOUT", phase == "PUT")
            self.assert_calls(int(phase == "PUT"))

    async def test_unexpected_error_and_cancellation_never_replay(self):
        for error in (RuntimeError("SYNTHETIC-PRIVATE"), asyncio.CancelledError()):
            def handler(request):
                if request.method == "GET":
                    return httpx.Response(200, json=ORDER)
                raise error
            if isinstance(error, asyncio.CancelledError):
                with self.assertRaises(asyncio.CancelledError):
                    await self.request(handler)
            else:
                with self.assertRaises(WooError) as raised:
                    await self.request(handler)
                self.assert_error(raised.exception, "WOO_INTERNAL_ERROR", True)
            self.assert_calls(1)
