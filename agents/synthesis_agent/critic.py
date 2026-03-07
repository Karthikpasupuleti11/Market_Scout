"""
Synthesis Agent — Self-Critic

Reviews report quality before handoff to Output Guardrail.
Catches issues the LLM might introduce.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def self_review(report: Dict[str, Any]) -> Dict[str, Any]:
    """Review synthesis quality before passing to Output Guardrail.

    Checks:
      - Executive summary exists and is meaningful (not too short)
      - Features list has entries
      - Feature descriptions aren't just title repeats
    """
    issues = []

    summary = report.get("executive_summary", "")
    if not summary:
        issues.append("Missing executive summary")
    elif len(summary) < 50:
        issues.append(f"Executive summary too short ({len(summary)} chars)")

    features = report.get("features", [])
    if not features:
        issues.append("No features in report")

    # Check for lazy descriptions (just repeating the title)
    for i, f in enumerate(features):
        title = f.get("title", "")
        desc = f.get("description", "")
        if title and desc and title.strip().lower() == desc.strip().lower():
            issues.append(f"Feature #{i+1} description is just a title repeat")

    result = {
        "passed": len(issues) == 0,
        "issues": issues,
        "feature_count": len(features),
    }

    if issues:
        logger.info("SYNTHESIS CRITIC — Flagged %d issues: %s", len(issues), issues)
    else:
        logger.info("SYNTHESIS CRITIC — Report passed review (%d features)", len(features))

    return result
