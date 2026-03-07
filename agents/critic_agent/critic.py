"""
Critic Agent — Self-Critic

Meta-review: the Critic reviewing its own decision quality.
Prevents flip-flopping between APPROVE/REVISE across iterations.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def self_review(decision: str, iteration: int, previous_decisions: list) -> Dict[str, Any]:
    """Review the Critic's own decision for consistency.

    Flags issues like:
      - Approving on iteration 0 with very few features
      - Flip-flopping (APPROVE → REVISE → APPROVE)
      - Revising after max iterations (should auto-approve)
    """
    issues = []

    # Check: approving too early with no features
    if decision == "APPROVE" and iteration == 0:
        logger.debug("CRITIC SELF-REVIEW — Early approval on first pass")

    # Check: flip-flopping
    if len(previous_decisions) >= 2:
        last_two = previous_decisions[-2:]
        if last_two == ["APPROVE", "REVISE"] or last_two == ["REVISE", "APPROVE"]:
            issues.append("Flip-flopping detected between APPROVE/REVISE")

    # Check: should auto-approve after max iterations
    if iteration >= 2 and decision == "REVISE":
        issues.append("Still revising after 2+ iterations — should auto-approve")

    if issues:
        logger.info("CRITIC SELF-REVIEW — Flagged %d issues: %s", len(issues), issues)

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
    }
