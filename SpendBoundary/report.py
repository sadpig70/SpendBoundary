"""Markdown report renderer for SpendBoundary verdicts."""


def render_report(result: dict) -> str:
    """Render a human-readable Markdown report."""
    agent = result.get("agent_id", "unknown")
    verdict = result["verdict"]
    amount = result.get("amount", 0)
    boundary = result.get("boundary", {})
    veto = result.get("veto", {})
    audit_hash = result.get("audit_hash", "")
    errors = result.get("errors", [])

    lines = [
        "# SpendBoundary -- Spend Verdict Report",
        "",
        f"**Agent**: `{agent}`",
        f"**Amount**: {amount}",
        f"**Verdict**: `{verdict}`",
        f"**Audit Hash**: `{audit_hash}`",
        "",
    ]

    if errors:
        lines.append("## Schema Errors")
        for e in errors:
            lines.append(f"- `{e}`")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Context Boundary Check")
    lines.append("")
    lines.append(f"- Current context: `{boundary.get('current_context', '')}`")
    lines.append(f"- Spend context: `{boundary.get('spend_context', '')}`")
    lines.append(f"- Boundary crossed: **{boundary.get('boundary_crossed', False)}**")
    lines.append(f"- Gap: {boundary.get('gap', 0)}")
    lines.append("")

    if veto.get("reasons"):
        lines.append("## Veto Reasons")
        lines.append("")
        for r in veto["reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    lines.append("## Decision")
    lines.append("")
    desc = {
        "cleared": "Spend within authorized context boundary. Proceed.",
        "boundary_crossed": "Spend crosses a context boundary. Re-authorization required before proceeding.",
        "vetoed": "Spend crosses a context boundary AND triggers veto policy. Spend is blocked.",
        "invalid_schema": "Spend request validation failed. See errors above.",
    }
    lines.append(desc.get(verdict, "Unknown verdict."))
    lines.append("")

    return "\n".join(lines)
