"""Deterministic context-boundary spend gate.

verdict_scheme (k-way):
    cleared          — spend within authorized context boundaries
    boundary_crossed — spend crosses a boundary; re-authorization required
    vetoed           — spend crosses a boundary + veto policy triggers block
"""

import hashlib
import json


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


CONTEXT_LEVELS = ["session", "task", "tool", "external"]


def _level_index(level: str) -> int:
    try:
        return CONTEXT_LEVELS.index(level)
    except ValueError:
        return -1


def _validate_spend(spend: dict) -> list[str]:
    """Validate spend request schema."""
    errors = []
    required = ["agent_id", "amount", "currency", "recipient",
                "current_context", "spend_context", "tool_name"]
    for field in required:
        if field not in spend:
            errors.append(f"missing field: {field}")
        elif spend[field] is None or (isinstance(spend[field], str) and not spend[field]):
            errors.append(f"empty field: {field}")
    if "current_context" in spend and _level_index(spend.get("current_context", "")) < 0:
        errors.append(f"invalid current_context: {spend['current_context']}")
    if "spend_context" in spend and _level_index(spend.get("spend_context", "")) < 0:
        errors.append(f"invalid spend_context: {spend['spend_context']}")
    return errors


def check_boundary(spend: dict) -> dict:
    """Check if the spend crosses a context boundary.

    A boundary is crossed when spend_context is wider (lower index = broader scope)
    than current_context — the agent is spending in a context it hasn't been
    explicitly authorized for.

    Returns:
        {boundary_crossed: bool, gap: int, current: str, spend_ctx: str}
    """
    current = spend["current_context"]
    spend_ctx = spend["spend_context"]
    ci = _level_index(current)
    si = _level_index(spend_ctx)
    # Lower index = broader scope (session > task > tool > external)
    # Boundary crossed when spend is in a broader scope than current
    crossed = si < ci
    return {
        "boundary_crossed": crossed,
        "gap": ci - si if crossed else 0,
        "current_context": current,
        "spend_context": spend_ctx,
    }


def apply_veto_policy(spend: dict, boundary: dict) -> dict:
    """Apply veto policy to a boundary-crossing spend.

    Veto rules (from VetoEscrow):
        - amount > veto_threshold + boundary gap >= 2 → vetoed
        - recipient in blocked_recipients → vetoed
        - tool in restricted_tools → vetoed
        - otherwise → boundary_crossed (re-auth required)

    Returns:
        {verdict: "vetoed"|"boundary_crossed", reasons: [...]}
    """
    policy = spend.get("veto_policy", {})
    reasons = []
    vetoed = False

    veto_threshold = policy.get("veto_threshold", 100.0)
    blocked_recipients = policy.get("blocked_recipients", [])
    restricted_tools = policy.get("restricted_tools", [])

    # Rule 1: amount + gap combo
    if spend["amount"] > veto_threshold and boundary["gap"] >= 2:
        reasons.append(f"amount {spend['amount']} > threshold {veto_threshold}"
                       f" with boundary gap {boundary['gap']}")
        vetoed = True

    # Rule 2: blocked recipient
    if spend["recipient"] in blocked_recipients:
        reasons.append(f"recipient '{spend['recipient']}' is blocked")
        vetoed = True

    # Rule 3: restricted tool
    if spend["tool_name"] in restricted_tools:
        reasons.append(f"tool '{spend['tool_name']}' is restricted")
        vetoed = True

    return {
        "verdict": "vetoed" if vetoed else "boundary_crossed",
        "reasons": reasons,
    }


def evaluate_spend(spend: dict, audit_log: list[dict] | None = None) -> dict:
    """Full pipeline: validate → check boundary → apply veto → verdict.

    Args:
        spend: Spend request with agent context info and veto policy.
        audit_log: Optional hash-chained audit log.

    Returns:
        {verdict, boundary, veto, audit_log, errors}
    """
    errors = _validate_spend(spend)
    if errors:
        return {
            "agent_id": spend.get("agent_id", ""),
            "verdict": "invalid_schema",
            "boundary": {},
            "veto": {},
            "audit_hash": "",
            "audit_log": audit_log or [],
            "errors": errors,
        }

    boundary = check_boundary(spend)

    if not boundary["boundary_crossed"]:
        verdict = "cleared"
        veto = {"verdict": "cleared", "reasons": []}
    else:
        veto = apply_veto_policy(spend, boundary)
        verdict = veto["verdict"]

    payload = {
        "verdict": verdict,
        "agent_id": spend["agent_id"],
        "amount": spend["amount"],
        "boundary": boundary,
    }
    audit_hash = _sha256(json.dumps(payload, sort_keys=True))

    if audit_log is None:
        audit_log = []
    prev_hash = audit_log[-1]["hash"] if audit_log else _sha256("GENESIS")
    entry = {
        "index": len(audit_log) + 1,
        "agent_id": spend["agent_id"],
        "verdict": verdict,
        "hash": audit_hash,
        "prev_hash": prev_hash,
    }
    audit_log.append(entry)

    return {
        "agent_id": spend["agent_id"],
        "amount": spend["amount"],
        "verdict": verdict,
        "boundary": boundary,
        "veto": veto,
        "audit_hash": audit_hash,
        "audit_log": audit_log,
        "errors": [],
    }
