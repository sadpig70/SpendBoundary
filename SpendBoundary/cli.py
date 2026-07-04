"""CLI for SpendBoundary -- sample, evaluate, report."""

import argparse
import json
import os
import sys

from SpendBoundary.engine import evaluate_spend
from SpendBoundary.report import render_report


def _build_samples():
    """Build sample spend requests for each verdict type."""
    return {
        "cleared": {
            "agent_id": "agent-ops-01",
            "amount": 50.0,
            "currency": "USD",
            "recipient": "api-provider-example",
            "current_context": "tool",
            "spend_context": "tool",
            "tool_name": "text_completion",
            "veto_policy": {
                "veto_threshold": 100.0,
                "blocked_recipients": ["malicious-actor"],
                "restricted_tools": ["sudo_exec"],
            },
        },
        "boundary_crossed": {
            "agent_id": "agent-ops-01",
            "amount": 25.0,
            "currency": "USD",
            "recipient": "api-provider-example",
            "current_context": "tool",
            "spend_context": "task",
            "tool_name": "text_completion",
            "veto_policy": {
                "veto_threshold": 100.0,
                "blocked_recipients": ["malicious-actor"],
                "restricted_tools": ["sudo_exec"],
            },
        },
        "vetoed_amount": {
            "agent_id": "agent-ops-02",
            "amount": 500.0,
            "currency": "USD",
            "recipient": "external-vendor",
            "current_context": "tool",
            "spend_context": "session",
            "tool_name": "text_completion",
            "veto_policy": {
                "veto_threshold": 100.0,
                "blocked_recipients": [],
                "restricted_tools": [],
            },
        },
        "vetoed_recipient": {
            "agent_id": "agent-ops-03",
            "amount": 10.0,
            "currency": "USD",
            "recipient": "malicious-actor",
            "current_context": "tool",
            "spend_context": "task",
            "tool_name": "text_completion",
            "veto_policy": {
                "veto_threshold": 100.0,
                "blocked_recipients": ["malicious-actor"],
                "restricted_tools": [],
            },
        },
        "vetoed_tool": {
            "agent_id": "agent-ops-04",
            "amount": 10.0,
            "currency": "USD",
            "recipient": "safe-vendor",
            "current_context": "tool",
            "spend_context": "task",
            "tool_name": "sudo_exec",
            "veto_policy": {
                "veto_threshold": 100.0,
                "blocked_recipients": [],
                "restricted_tools": ["sudo_exec"],
            },
        },
    }


def cmd_sample(args):
    out_dir = args.out or "examples"
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, data in _build_samples().items():
        path = os.path.join(out_dir, f"{name}_spend.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        written.append(path)
    print(f"Wrote {len(written)} sample spends to {out_dir}/")
    for p in written:
        print(f"  {p}")


def cmd_evaluate(args):
    with open(args.spend, "r", encoding="utf-8") as f:
        spend = json.load(f)
    audit_log = None
    if args.audit_log:
        with open(args.audit_log, "r", encoding="utf-8") as f:
            audit_log = json.load(f)
    result = evaluate_spend(spend, audit_log)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_report(args):
    with open(args.input, "r", encoding="utf-8") as f:
        result = json.load(f)
    md = render_report(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Report written to {args.out}")
    else:
        print(md)


def main():
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="spend-boundary",
        description="AI Agent Context-Boundary Spend Gate",
    )
    sub = parser.add_subparsers(dest="command")

    p_sample = sub.add_parser("sample", help="Generate sample spend fixtures")
    p_sample.add_argument("--out", default="examples")

    p_eval = sub.add_parser("evaluate", help="Evaluate a spend request")
    p_eval.add_argument("--spend", required=True, help="Path to spend JSON.")
    p_eval.add_argument("--audit-log", help="Path to existing audit log.")

    p_report = sub.add_parser("report", help="Render a Markdown report")
    p_report.add_argument("--input", required=True, help="Path to verdict JSON.")
    p_report.add_argument("--out", help="Output path for report.")

    args = parser.parse_args()
    if args.command == "sample":
        cmd_sample(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
