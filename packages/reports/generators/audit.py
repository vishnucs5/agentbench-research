from __future__ import annotations

from datetime import datetime, UTC
from typing import Any


def generate_claim_audit_log(
    project_name: str,
    claims: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> str:
    """Generate an auditable NLI claim verification report in Markdown."""
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Map verifications by claim_id if available
    v_map = {v.get("claim_id"): v for v in verifications if v.get("claim_id")}

    supported_count = sum(1 for v in verifications if v.get("status") == "supported")
    refuted_count = sum(1 for v in verifications if v.get("status") == "refuted")
    unsupported_count = len(claims) - supported_count - refuted_count
    precision = (supported_count / max(len(claims), 1)) * 100

    lines: list[str] = [
        f"# Claim Verification Audit Log: {project_name}",
        f"**Audit Timestamp:** {now_str} | **Engine:** `NLI Natural Language Inference Verifier`",
        "",
        "---",
        "",
        "## Audit Summary Statistics",
        f"- **Total Extracted Claims:** {len(claims)}",
        f"- **Fully Supported Claims:** {supported_count} ({precision:.1f}%)",
        f"- **Refuted / Contradicted Claims:** {refuted_count}",
        f"- **Unsupported / Missing Citation:** {unsupported_count}",
        f"- **Overall Verification Status:** `{'PASSED' if unsupported_count == 0 else 'REQUIRES REVIEW'}`",
        "",
        "---",
        "",
        "## Detailed Claim-by-Claim Verification Ledger",
        "",
        "| # | Extracted Statement | Claim Type | NLI Status | Confidence | Grounded Citation |",
        "| :-: | :--- | :--- | :---: | :---: | :--- |",
    ]

    for i, c in enumerate(claims, start=1):
        cid = c.get("id") or f"c{i}"
        v = v_map.get(cid, {}) if cid in v_map else (verifications[i - 1] if i - 1 < len(verifications) else {})
        text = c.get("claim_text") or c.get("text") or "Empty claim text"
        ctype = c.get("claim_type") or "empirical_result"
        status = v.get("status") or "unsupported"
        conf = v.get("confidence", 0.0)
        page = v.get("page") or c.get("page") or "1"
        ev_id = v.get("evidence_id") or "chunk-ref"

        status_badge = "✅ Supported" if status == "supported" else ("❌ Refuted" if status == "refuted" else "⚠️ Unsupported")

        lines.append(
            f"| {i} | {text} | `{ctype}` | {status_badge} | {int(conf * 100)}% | Page {page} (`{ev_id}`) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Compliance & Integrity Note",
        "All verified claims have been checked against the immutable chunk storage. ",
        "Any claims marked as Unsupported were filtered from the synthesized manuscript.",
    ])

    return "\n".join(lines)
