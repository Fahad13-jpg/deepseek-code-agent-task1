"""Offline packaging fixture. Never presented as a DeepSeek-generated project."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from fractions import Fraction  # Include this module in the frozen smoke-test runtime.

from .agent import Agent, RunConfig
from .client import Reply, DeepSeekClient
from .inputs import preprocess

FIXTURE = {
    "README.md": "# Offline self-test fixture\n\nThis small project is a deterministic packaging test, not AI-generated output.\nRun: python -m unittest discover -s tests\n",
    "requirements.txt": "# Python standard library only\n",
    "fraction_math.py": "from fractions import Fraction\n\ndef add(a, b):\n    return str(Fraction(a) + Fraction(b))\n",
    "tests/test_fraction_math.py": "import unittest\nfrom fraction_math import add\n\nclass FractionTest(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add('1/2', '1/3'), '5/6')\n    def test_reduce(self):\n        self.assertEqual(add('1/4', '1/4'), '1/2')\n    def test_zero_denominator(self):\n        with self.assertRaises(ZeroDivisionError):\n            add('1/0', '1/2')\n",
}


class FixtureClient:
    api_key = ""

    def __init__(self):
        self.turn = 0

    def complete(self, messages, tools, on_text=lambda text: None, **kwargs):
        self.turn += 1
        if self.turn == 1:
            calls = [("write_file", {"path": path, "content": content}) for path, content in FIXTURE.items()]
        elif self.turn == 2:
            calls = [("check_project", {}), ("run_python_tests", {})]
        else:
            text = "Offline packaging fixture complete. This verifies the harness, not the live DeepSeek API."
            on_text(text)
            return Reply({"role": "assistant", "content": text, "reasoning_content": ""}, {}, "stop")
        return Reply({"role": "assistant", "content": "", "reasoning_content": "",
                      "tool_calls": [{"id": f"fixture-{self.turn}-{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}} for i, (name, args) in enumerate(calls)]}, {}, "tool_calls")


def run_self_test(output: Path) -> int:
    from .ui import resource_root
    source = resource_root() / "examples"
    data = preprocess(source / "Architecture_Documentation.md", source / "Architecture_View.md")
    # Mock transports bypass SSLContext construction. Initialize the actual
    # production HTTP transport here, without sending any network request.
    output.mkdir(parents=True, exist_ok=True)
    try:
        client = DeepSeekClient("offline-transport-check-no-request")
        client.close()
    except Exception as exc:
        report = {"success": False, "test_mode": "offline fixture; no API called",
                  "tls_transport_initialized": False, "error": str(exc)}
        (output / "self-test-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1
    report = Agent(FixtureClient(), RunConfig(output, "offline-self-test", execute_tests=True), data).run()
    report["tls_transport_initialized"] = True
    report["test_mode"] = "offline fixture; no API called"
    report["success"] = report["status"] == "completed" and report["python_tests"].get("passed") is True
    output.mkdir(parents=True, exist_ok=True)
    (output / "self-test-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1
