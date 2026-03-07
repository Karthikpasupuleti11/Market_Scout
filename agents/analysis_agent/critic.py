"""
Analysis Agent — Self-Critic

Reviews extraction quality before returning to Supervisor.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def self_review(scored_features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Review analysis quality. Returns assessment with pass/flag status."""
    issues = []

    if not scored_features:
        issues.append("No features extracted")
        return {"passed": False, "issues": issues, "feature_count": 0}

    # Check: enough features?
    if len(scored_features) < 2:
        issues.append(f"Only {len(scored_features)} feature(s) extracted (low yield)")

    # Check: quality
    low_confidence = [f for f in scored_features if f.get("confidence_score", 0) < 0.3]
    if len(low_confidence) > len(scored_features) * 0.5:
        issues.append(f"{len(low_confidence)}/{len(scored_features)} features have low confidence")

    # Check: evidence
    no_evidence = [f for f in scored_features if not f.get("evidence")]
    if no_evidence:
        issues.append(f"{len(no_evidence)} features missing evidence")

    result = {
        "passed": len(issues) == 0,
        "issues": issues,
        "feature_count": len(scored_features),
    }

    if issues:
        logger.info("ANALYSIS CRITIC — Flagged %d issues: %s", len(issues), issues)
    else:
        logger.info("ANALYSIS CRITIC — Passed (%d features)", len(scored_features))

    return result
