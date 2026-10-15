import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin" / "fablize" / "__init__.py"
EXTENSION = ROOT / "extension" / "fablize"


class FablizeHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "FABLIZE_DATA": self.temp.name,
            "FABLIZE_ROOT": str(EXTENSION),
        })
        self.env.start()
        sys.modules.pop("ledger", None)
        sys.modules.pop("classify_task", None)
        sys.modules.pop("parse_tool_result", None)
        sys.modules.pop("verify_state", None)
        spec = importlib.util.spec_from_file_location("fablize_hooks_test", PLUGIN)
        self.hooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hooks)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_prompt_classifies_and_injects_context(self):
        result = self.hooks.pre_llm_call(
            session_id="deep-task",
            user_message="Deploy a complex database migration",
        )
        self.assertIn("task mode: deep", result["context"])
        self.assertIn("Risk flags", result["context"])

    def test_post_tool_evidence_satisfies_verify_gate(self):
        self.hooks.pre_llm_call(session_id="verified", user_message="Deploy a complex feature")
        self.hooks.post_tool_call(
            tool_name="write_file", args={"path": "src/app.py"}, result="{}", session_id="verified"
        )
        self.hooks.post_tool_call(
            tool_name="terminal", args={"command": "pytest"},
            result=json.dumps({"exit_code": 0, "stdout": "1 passed"}), session_id="verified"
        )
        self.assertIsNone(self.hooks.pre_verify(session_id="verified"))

    def test_deep_change_without_verification_gets_bounded_gate(self):
        self.hooks.pre_llm_call(session_id="unverified", user_message="Deploy a complex feature")
        self.hooks.post_tool_call(
            tool_name="write_file", args={"path": "src/app.py"}, result="{}", session_id="unverified"
        )
        self.assertEqual(self.hooks.pre_verify(session_id="unverified")["action"], "continue")
        self.assertEqual(self.hooks.pre_verify(session_id="unverified")["action"], "continue")
        self.assertIsNone(self.hooks.pre_verify(session_id="unverified"))


if __name__ == "__main__":
    unittest.main()
