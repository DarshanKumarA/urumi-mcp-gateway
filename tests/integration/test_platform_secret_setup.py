import base64
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("setup",Path(__file__).resolve().parents[2]/"scripts/setup-platform-secrets.py")
setup=importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

class SetupTests(unittest.TestCase):
    def existing(self, name):
        return {"type":"Opaque","data":{k:base64.b64encode(b"SYNTHETIC-ONLY").decode() for k in setup.CONTRACTS[name]}}
    def test_existing_secrets_never_replaced_or_prompted(self):
        def call(*args, **kw):
            return {"status":{"phase":"Active"}} if args[1]=="namespace" else self.existing(args[2])
        with patch.object(setup,"kubectl",side_effect=call) as run, patch.object(setup,"values_for") as prompt:
            self.assertEqual(setup.run("create"),0)
            prompt.assert_not_called()
            self.assertTrue(all(c.args[0]=="get" for c in run.call_args_list))
    def test_missing_check_never_creates(self):
        with patch.object(setup,"kubectl",side_effect=[{"status":{"phase":"Active"}},None,None,None,None]) as run:
            self.assertEqual(setup.run("check"),1)
            self.assertEqual(run.call_count,5)
    def test_conflict_aborts_before_any_create(self):
        with patch.object(setup,"kubectl",side_effect=[{"status":{"phase":"Active"}},None,{"type":"Opaque","data":{}}]) as run:
            with self.assertRaises(ValueError): setup.run("create")
            self.assertTrue(all(c.args[0]=="get" for c in run.call_args_list))
    def test_payload_uses_stdin_create_only(self):
        with patch.object(setup,"kubectl",side_effect=[{"status":{"phase":"Active"}},None,*[self.existing(n) for n in list(setup.CONTRACTS)[1:]],None]) as run:
            self.assertEqual(setup.run("create"),0)
            self.assertEqual(run.call_args.args,("create","-f","-","-o","name"))
            self.assertIn('"stringData"',run.call_args.kwargs["body"])
    def test_empty_values_rejected(self):
        obj=self.existing("urumi-openrouter"); obj["data"]["api-key"]=""
        with self.assertRaises(ValueError): setup.check_existing("urumi-openrouter",obj)

if __name__=="__main__": unittest.main()
