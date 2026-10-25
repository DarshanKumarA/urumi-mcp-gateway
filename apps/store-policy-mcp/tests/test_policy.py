import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from store_policy_mcp.models import Input
from store_policy_mcp.logic import execute
from store_policy_mcp.policies import POLICIES


class PolicyTests(unittest.TestCase):
    def test_known_cod(self):
        r = execute(Input(key="cod"))
        self.assertEqual(r.title, "Cash on Delivery")
        self.assertIn("not prepaid", r.guidance)

    def test_dispatch(self):
        r = execute(Input(key="dispatch"))
        self.assertIn("on-hold", r.guidance)
        self.assertIn("processing", r.guidance)

    def test_cancellation_is_not_refund(self):
        self.assertIn("not a refund operation", execute(Input(key="cancellation")).guidance)

    def test_unknown_policy(self):
        for key in ("unknown", "../secret", "http://invalid", "COD", " cod", "", "x" * 1000):
            with self.assertRaises(ValidationError):
                Input(key=key)

    def test_strict_type(self):
        for key in (1, True, None, [], {}):
            with self.assertRaises(ValidationError):
                Input(key=key)

    def test_extra_fields(self):
        with self.assertRaises(ValidationError):
            Input(key="cod", path="/tmp/anything")

    def test_allowlisted_output(self):
        for key in POLICIES:
            self.assertEqual(set(execute(Input(key=key)).model_dump()), {"key", "title", "guidance"})

    def test_dataset_immutable(self):
        with self.assertRaises(TypeError):
            POLICIES["cod"] = None
        with self.assertRaises(ValidationError):
            POLICIES["cod"].guidance = "changed"

    def test_deterministic(self):
        self.assertEqual(execute(Input(key="cod")), execute(Input(key="cod")))

    def test_no_io(self):
        with patch("builtins.open", side_effect=AssertionError("file access")), patch("socket.create_connection", side_effect=AssertionError("network access")):
            self.assertEqual(execute(Input(key="cod")).key, "cod")
        for p in (Path(__file__).parents[1] / "src/store_policy_mcp").glob("*.py"):
            tree = ast.parse(p.read_text())
            self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"eval", "exec", "open", "compile", "__import__"} for n in ast.walk(tree)))
