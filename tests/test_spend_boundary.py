"""Tests for SpendBoundary — context-boundary spend gate."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from SpendBoundary.engine import (
    _sha256,
    _validate_spend,
    check_boundary,
    apply_veto_policy,
    evaluate_spend,
)
from SpendBoundary.report import render_report


def _spend(**overrides):
    s = {
        "agent_id": "test-agent",
        "amount": 50.0,
        "currency": "USD",
        "recipient": "safe-vendor",
        "current_context": "tool",
        "spend_context": "tool",
        "tool_name": "text_completion",
        "veto_policy": {
            "veto_threshold": 100.0,
            "blocked_recipients": ["bad-actor"],
            "restricted_tools": ["sudo_exec"],
        },
    }
    s.update(overrides)
    return s


class TestValidateSpend(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(_validate_spend(_spend()), [])

    def test_missing_field(self):
        s = _spend()
        del s["agent_id"]
        errors = _validate_spend(s)
        self.assertTrue(any("agent_id" in e for e in errors))

    def test_invalid_context(self):
        s = _spend(current_context="invalid")
        errors = _validate_spend(s)
        self.assertTrue(any("current_context" in e for e in errors))


class TestCheckBoundary(unittest.TestCase):
    def test_same_context(self):
        r = check_boundary(_spend(current_context="tool", spend_context="tool"))
        self.assertFalse(r["boundary_crossed"])
        self.assertEqual(r["gap"], 0)

    def test_boundary_crossed(self):
        r = check_boundary(_spend(current_context="tool", spend_context="task"))
        self.assertTrue(r["boundary_crossed"])
        self.assertEqual(r["gap"], 1)

    def test_narrower_ok(self):
        r = check_boundary(_spend(current_context="task", spend_context="tool"))
        self.assertFalse(r["boundary_crossed"])

    def test_max_gap(self):
        r = check_boundary(_spend(current_context="external", spend_context="session"))
        self.assertTrue(r["boundary_crossed"])
        self.assertEqual(r["gap"], 3)


class TestVetoPolicy(unittest.TestCase):
    def test_no_boundary_cross(self):
        b = {"boundary_crossed": False, "gap": 0}
        r = apply_veto_policy(_spend(), b)
        self.assertEqual(r["verdict"], "boundary_crossed")  # never called if not crossed

    def test_amount_gap_combo(self):
        s = _spend(amount=500.0, current_context="external", spend_context="session")
        b = check_boundary(s)
        r = apply_veto_policy(s, b)
        self.assertEqual(r["verdict"], "vetoed")

    def test_blocked_recipient(self):
        s = _spend(recipient="bad-actor", current_context="tool", spend_context="task")
        b = check_boundary(s)
        r = apply_veto_policy(s, b)
        self.assertEqual(r["verdict"], "vetoed")

    def test_restricted_tool(self):
        s = _spend(tool_name="sudo_exec", current_context="tool", spend_context="task")
        b = check_boundary(s)
        r = apply_veto_policy(s, b)
        self.assertEqual(r["verdict"], "vetoed")

    def test_boundary_crossed_no_veto(self):
        s = _spend(amount=10.0, current_context="tool", spend_context="task")
        b = check_boundary(s)
        r = apply_veto_policy(s, b)
        self.assertEqual(r["verdict"], "boundary_crossed")


class TestFullPipeline(unittest.TestCase):
    def test_cleared(self):
        r = evaluate_spend(_spend())
        self.assertEqual(r["verdict"], "cleared")
        self.assertEqual(r["errors"], [])
        self.assertEqual(len(r["audit_log"]), 1)

    def test_boundary_crossed(self):
        r = evaluate_spend(_spend(current_context="tool", spend_context="task"))
        self.assertEqual(r["verdict"], "boundary_crossed")

    def test_vetoed_amount(self):
        r = evaluate_spend(_spend(amount=500.0, current_context="external", spend_context="session"))
        self.assertEqual(r["verdict"], "vetoed")

    def test_vetoed_recipient(self):
        r = evaluate_spend(_spend(recipient="bad-actor", current_context="tool", spend_context="task"))
        self.assertEqual(r["verdict"], "vetoed")

    def test_vetoed_tool(self):
        r = evaluate_spend(_spend(tool_name="sudo_exec", current_context="tool", spend_context="task"))
        self.assertEqual(r["verdict"], "vetoed")

    def test_invalid_schema(self):
        r = evaluate_spend({})
        self.assertEqual(r["verdict"], "invalid_schema")
        self.assertTrue(len(r["errors"]) > 0)

    def test_audit_log_chain(self):
        r1 = evaluate_spend(_spend())
        r2 = evaluate_spend(_spend(agent_id="agent-2"), audit_log=r1["audit_log"])
        self.assertEqual(len(r2["audit_log"]), 2)
        self.assertEqual(r2["audit_log"][1]["prev_hash"], r2["audit_log"][0]["hash"])


class TestReport(unittest.TestCase):
    def test_cleared_report(self):
        r = evaluate_spend(_spend())
        md = render_report(r)
        self.assertIn("cleared", md)
        self.assertIn("test-agent", md)

    def test_vetoed_report(self):
        r = evaluate_spend(_spend(tool_name="sudo_exec", current_context="tool", spend_context="task"))
        md = render_report(r)
        self.assertIn("vetoed", md)

    def test_invalid_report(self):
        r = evaluate_spend({})
        md = render_report(r)
        self.assertIn("Schema Errors", md)


class TestCli(unittest.TestCase):
    def test_sample(self):
        with tempfile.TemporaryDirectory() as td:
            from SpendBoundary.cli import cmd_sample

            class Args:
                out = td
            cmd_sample(Args())
            files = os.listdir(td)
            self.assertGreater(len(files), 0)
            for f in files:
                with open(os.path.join(td, f), "r") as fh:
                    json.load(fh)

    def test_evaluate_cleared(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "spend.json")
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(_spend(), f)
            r = subprocess.run(
                [sys.executable, "-m", "SpendBoundary", "evaluate", "--spend", sp],
                capture_output=True, text=True, encoding="utf-8",
                cwd=os.path.join(os.path.dirname(__file__), ".."),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["verdict"], "cleared")

    def test_report_cli(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "spend.json")
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(_spend(), f)
            ev = subprocess.run(
                [sys.executable, "-m", "SpendBoundary", "evaluate", "--spend", sp],
                capture_output=True, text=True, encoding="utf-8",
                cwd=os.path.join(os.path.dirname(__file__), ".."),
            )
            vp = os.path.join(td, "verdict.json")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(ev.stdout)
            rp = subprocess.run(
                [sys.executable, "-m", "SpendBoundary", "report", "--input", vp],
                capture_output=True, text=True, encoding="utf-8",
                cwd=os.path.join(os.path.dirname(__file__), ".."),
            )
            self.assertEqual(rp.returncode, 0, rp.stderr)
            self.assertIn("cleared", rp.stdout)


if __name__ == "__main__":
    unittest.main()
