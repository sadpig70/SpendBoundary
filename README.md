# SpendBoundary

> AI Agent Context-Boundary Spend Gate — veto agent spends that cross context boundaries without re-authorization.

## One-sentence pitch

`SpendBoundary` answers: *Does this AI agent spend cross a context boundary that requires re-authorization, and should it be vetoed?*

## Why this matters

AI agents spend money across tools, APIs, and services. But when a long-running agent keeps context across scopes and later triggers a spend in a broader context than it was authorized for, it creates a boundary-crossing risk. SpendBoundary catches this.

It recombines three primitives:

- **ContextCreep** — ranks attack paths when AI agents cross memory/tool boundaries
- **SpendMesh** — puts a treasury control in front of every agent spend
- **VetoEscrow** — interruptible clearing gate for high-risk decisions

## What it is not

- Not a payment processor or billing engine.
- Not an agent runtime or orchestration framework.
- Not a permission system or IAM.

It gates the *spend decision* — not the money movement.

## Install / Run

Requires Python 3.10+ and no external packages.

```bash
python -m pip install -e .
python -m SpendBoundary sample --out examples
python -m SpendBoundary evaluate --spend examples/cleared_spend.json
python -m SpendBoundary report --input verdict.json
```

## CLI

| Subcommand | Purpose |
|---|---|
| `sample` | Write deterministic sample spend fixtures. |
| `evaluate` | Evaluate a spend request against context boundaries + veto policy. |
| `report` | Render a Markdown report from a verdict. |

## Context levels

| Level | Scope |
|---|---|
| `session` | Full agent session (broadest) |
| `task` | Single task within session |
| `tool` | Single tool invocation (narrowest) |
| `external` | External system call |

A boundary is crossed when `spend_context` is broader (lower index) than `current_context`.

## Verdict scheme

| Verdict | Condition |
|---|---|
| `cleared` | Spend within authorized context boundary. |
| `boundary_crossed` | Spend crosses a boundary; re-authorization required. |
| `vetoed` | Boundary crossed + veto policy triggers block. |

## Python API

```python
from SpendBoundary import evaluate_spend, render_report

spend = {
    "agent_id": "agent-01",
    "amount": 500.0,
    "currency": "USD",
    "recipient": "external-vendor",
    "current_context": "tool",
    "spend_context": "session",
    "tool_name": "text_completion",
    "veto_policy": {
        "veto_threshold": 100.0,
        "blocked_recipients": ["malicious-actor"],
        "restricted_tools": ["sudo_exec"],
    },
}

result = evaluate_spend(spend)
print(result["verdict"])  # "vetoed"
print(render_report(result))
```

## Tests

```bash
python -m unittest discover -s tests -q
```

## License

MIT License — see [LICENSE](LICENSE).
