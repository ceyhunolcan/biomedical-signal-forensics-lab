"""Markdown formatting for a single trust report."""
from __future__ import annotations

from ..reliability.biomarker_trust_score import TrustReport


def render(report: TrustReport, participant_id: str | None = None) -> str:
    lines = [
        "## Digital Biomarker Trust Score",
        "",
        f"- **Participant**: `{participant_id or 'N/A'}`",
        f"- **Overall score**: {report.overall_trust_score:.2f} / 100",
        f"- **Category**: {report.category}",
        "",
        "| Component | Score |",
        "|---|---|",
    ]
    for k, v in report.components.__dict__.items():
        lines.append(f"| {k} | {v:.2f} |")
    lines += [
        "",
        f"_Explanation: {report.explanation}_",
        "",
        "> Research prototype only. Not medical advice, diagnosis, treatment, "
        "or a medical device.",
    ]
    return "\n".join(lines)
