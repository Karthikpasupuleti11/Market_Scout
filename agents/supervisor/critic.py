"""
Supervisor Agent — Self-Critic

Reviews routing decisions for consistency and pipeline health.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def self_review(decision: str, iteration: int, state_summary: Dict) -> Dict[str, Any]:
    """Review the Supervisor's own routing decision.

    Flags issues like:
      - Routing to synthesis before critic has approved
      - Routing to research when data already exists
      - Exceeding max iterations without progress
    """
    issues = []

    if decision == "synthesis" and not state_summary.get("critic_approved"):
        issues.append("Routing to synthesis before critic approval")

    if decision == "research" and state_summary.get("has_scored_features"):
        if not state_summary.get("critic_feedback"):
            issues.append("Routing to research when scored features already exist")

    if iteration >= 3:
        issues.append(f"Pipeline at iteration {iteration} — may be stuck in loop")

    if issues:
        logger.warning("SUPERVISOR CRITIC — Flagged %d issues: %s", len(issues), issues)

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
    }
