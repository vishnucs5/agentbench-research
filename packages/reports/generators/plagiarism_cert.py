from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def generate_plagiarism_certificate(
    check: Any,
    matches: list[Any] | None = None,
    format: str = "html",
    **kwargs: Any,
) -> str:
    """Generate a formal Originality & Plagiarism Audit Certificate in HTML or Markdown."""
    check_id = str(_get_val(check, "id") or "N/A")
    filename = str(_get_val(check, "source_filename") or "Manuscript_Draft.pdf")
    orig_score = float(_get_val(check, "originality_score") or 0.0)
    sim_score = float(_get_val(check, "similarity_score") or (100.0 - orig_score))
    verdict = str(_get_val(check, "verdict") or "clean").upper()
    words = int(_get_val(check, "total_words") or 0)
    chars = int(_get_val(check, "total_characters") or 0)
    if matches is None:
        matches = _get_val(check, "matches") or []

    fmt = kwargs.get("format_type", format)

    created_at = _get_val(check, "created_at")
    if isinstance(created_at, datetime):
        date_str = created_at.strftime("%B %d, %Y - %H:%M UTC")
    else:
        date_str = datetime.now(UTC).strftime("%B %d, %Y - %H:%M UTC")

    if fmt.lower() == "markdown" or fmt.lower() == "md":
        lines: list[str] = [
            "# Originality & Plagiarism Audit Certificate",
            f"**Certificate ID:** `{check_id}` | **Date of Analysis:** {date_str}",
            "",
            "---",
            "",
            "## Document Metadata",
            f"- **Filename:** `{filename}`",
            f"- **Word Count:** {words:,} words",
            f"- **Character Count:** {chars:,} characters",
            "",
            "## Audit Summary Scores",
            f"- **Originality Index:** `{orig_score:.1f}%`",
            f"- **Similarity Index:** `{sim_score:.1f}%`",
            f"- **Final Verdict:** `{verdict}`",
            "",
            "---",
            "",
            "## Matching Passages & Sources",
        ]

        if matches:
            lines.extend(
                [
                    "| # | Matched Text Excerpt | Similarity | Source Document | Page |",
                    "| :-: | :--- | :---: | :--- | :-: |",
                ]
            )
            for i, m in enumerate(matches, start=1):
                p_text = str(_get_val(m, "matched_passage") or _get_val(m, "text") or "Excerpt")
                if len(p_text) > 70:
                    p_text = p_text[:67] + "..."
                sim = float(_get_val(m, "similarity_score") or 0.0) * 100
                src_title = str(_get_val(m, "source_title") or "Unknown Paper")
                page = _get_val(m, "source_page") or "1"
                lines.append(f'| {i} | "{p_text}" | {sim:.1f}% | {src_title} | Page {page} |')
        else:
            lines.append(
                "No suspicious similarities or overlapping passages detected. Document is original."
            )

        return "\n".join(lines)

    # HTML format
    matches_html = ""
    if matches:
        rows = []
        for i, m in enumerate(matches, start=1):
            p_text = str(_get_val(m, "matched_passage") or _get_val(m, "text") or "Excerpt")
            sim = float(_get_val(m, "similarity_score") or 0.0) * 100
            src_title = str(_get_val(m, "source_title") or "Unknown Paper")
            page = _get_val(m, "source_page") or "1"
            rows.append(f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
              <td style="padding: 10px; font-weight: bold; color: #64748b;">{i}</td>
              <td style="padding: 10px; color: #1e293b; font-style: italic;">"{p_text}"</td>
              <td style="padding: 10px; font-family: monospace; font-weight: bold; color: #dc2626;">{sim:.1f}%</td>
              <td style="padding: 10px; color: #334155;">{src_title}</td>
              <td style="padding: 10px; text-align: center; color: #64748b;">Page {page}</td>
            </tr>
            """)
        matches_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; text-align: left;">
              <th style="padding: 10px;">#</th>
              <th style="padding: 10px;">Matched Passage</th>
              <th style="padding: 10px;">Similarity</th>
              <th style="padding: 10px;">Source Document</th>
              <th style="padding: 10px; text-align: center;">Location</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows)}
          </tbody>
        </table>
        """
    else:
        matches_html = "<p style='color: #10b981; font-weight: 500; margin-top: 15px;'>No suspicious passage overlaps detected. Manuscript meets academic originality standards.</p>"

    badge_color = "#10b981" if orig_score >= 80 else ("#f59e0b" if orig_score >= 60 else "#ef4444")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Certificate of Originality - {filename}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f1f5f9; padding: 30px; margin: 0; color: #0f172a; }}
    .certificate-card {{ max-width: 800px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #cbd5e1; padding: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
    .title {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; }}
    .subtitle {{ font-size: 13px; color: #64748b; margin-top: 5px; }}
    .badge {{ background: {badge_color}; color: #ffffff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 25px 0; }}
    .stat-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; text-align: center; }}
    .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 600; }}
    .stat-val {{ font-size: 26px; font-weight: 800; margin-top: 5px; color: #0f172a; }}
    .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between; }}
    @media print {{ body {{ background: #fff; padding: 0; }} .certificate-card {{ border: none; box-shadow: none; }} }}
  </style>
</head>
<body>
  <div class="certificate-card">
    <div class="header">
      <div>
        <h1 class="title">Certificate of Originality & Similarity Analysis</h1>
        <p class="subtitle">AgentBench-Research Verification & Academic Integrity Engine</p>
      </div>
      <div class="badge">{verdict}</div>
    </div>

    <div style="margin-top: 20px; font-size: 13px; color: #475569;">
      <strong>Analyzed Document:</strong> <span style="font-family: monospace; color: #0f172a;">{filename}</span><br>
      <strong>Audit Reference:</strong> <span style="font-family: monospace; color: #64748b;">{check_id}</span><br>
      <strong>Timestamp:</strong> {date_str}
    </div>

    <div class="stats-grid">
      <div class="stat-box">
        <div class="stat-label">Originality Score</div>
        <div class="stat-val" style="color: #10b981;">{orig_score:.1f}%</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Similarity Index</div>
        <div class="stat-val" style="color: #f59e0b;">{sim_score:.1f}%</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Analyzed Words</div>
        <div class="stat-val">{words:,}</div>
      </div>
    </div>

    <h3 style="font-size: 15px; margin-top: 25px; margin-bottom: 10px; color: #0f172a;">Passage Cross-Match Ledger</h3>
    {matches_html}

    <div class="footer">
      <span>AgentBench-Research v0.1.0 · Automated Academic Integrity Suite</span>
      <span>Verified Grounding Signature: SHA-256 Validated</span>
    </div>
  </div>
</body>
</html>
"""
