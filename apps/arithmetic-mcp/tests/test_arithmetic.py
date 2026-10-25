import ast
from decimal import localcontext
from pathlib import Path
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from arithmetic_mcp.logic import execute
from arithmetic_mcp.models import Input


class ArithmeticTests(unittest.TestCase):
    def calc(self, values, **kw):
        return execute(Input(amounts=values, **kw))

    def test_decimal_statistics(self):
        self.assertEqual(self.calc(["499", "599"], currency="INR").model_dump(),
            dict(count=2, total="1098", average="549", minimum="499", maximum="599", currency="INR"))

    def test_no_float_artifact(self):
        self.assertEqual(self.calc(["0.1", "0.2"]).total, "0.3")

    def test_negative_values(self):
        r = self.calc(["-10.25", "2", "-0.75"])
        self.assertEqual((r.total, r.average, r.minimum, r.maximum), ("-9", "-3", "-10.25", "2"))

    def test_zero_and_trailing_zeros(self):
        r = self.calc(["0", "-0.000000", "0.00"])
        self.assertEqual((r.total, r.average, r.minimum, r.maximum), ("0", "0", "0", "0"))

    def test_integer_like(self):
        self.assertEqual(self.calc(["1", "2", "3"]).average, "2")

    def test_repeating_average(self):
        self.assertEqual(self.calc(["1", "0", "0"]).average, "0.333333")

    def test_half_even_rounding(self):
        self.assertEqual(self.calc(["0.000001", "0"]).average, "0")
        self.assertEqual(self.calc(["0.000003", "0"]).average, "0.000002")

    def test_precision_bounds_exact_sum(self):
        r = self.calc(["999999999999999999.999999"] * 100)
        self.assertEqual(r.total, "99999999999999999999.9999")
        self.assertEqual(r.average, "999999999999999999.999999")

    def test_ambient_decimal_precision_does_not_change_result(self):
        with localcontext() as c:
            c.prec = 2
            self.assertEqual(self.calc(["1234.123456", "0.000001"]).total, "1234.123457")

    def test_float_integer_boolean_rejected(self):
        for value in (1.25, 1, True, None, {}, []):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Input(amounts=[value])

    def test_malformed_decimal_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e3", "+1", ".5", "1.", " 1", "1\n", "01", "1,000", "", "1+2"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Input(amounts=[value])

    def test_decimal_length_bounds(self):
        for value in ("1000000000000000000", "0.0000001", "9" * 1000):
            with self.assertRaises(ValidationError):
                Input(amounts=[value])

    def test_empty_and_oversized_list_rejected(self):
        for values in ([], ["1"] * 101, "[1]", ("1",)):
            with self.assertRaises(ValidationError):
                Input(amounts=values)

    def test_currency(self):
        self.assertIsNone(self.calc(["1"]).currency)
        for c in ("inr", "IN", "INRR", " INR", 1):
            with self.assertRaises(ValidationError):
                Input(amounts=["1"], currency=c)

    def test_unknown_fields(self):
        with self.assertRaises(ValidationError):
            Input(amounts=["1"], url="http://invalid")

    def test_pure_no_io_execution(self):
        with patch("builtins.open", side_effect=AssertionError("file access")), patch("socket.create_connection", side_effect=AssertionError("network access")):
            self.assertEqual(self.calc(["1", "2"]).total, "3")
        for p in (Path(__file__).parents[1] / "src/arithmetic_mcp").glob("*.py"):
            tree = ast.parse(p.read_text())
            self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"eval", "exec", "open", "compile", "__import__"} for n in ast.walk(tree)))
