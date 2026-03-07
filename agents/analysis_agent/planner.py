"""
Analysis Agent — Planner

Decides analysis strategy based on available data.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def plan_analysis(articles: List[Dict], has_critic_feedback: bool) -> List[str]:
    """Plan which analysis tools to run and in what order."""
    if not articles:
        return []

    steps = ["content_filter"]

    if len(articles) > 3:
        steps.append("authority_check")

    steps.extend(["extract_features", "verify_features", "score_features"])

    if has_critic_feedback:
        logger.info("ANALYSIS PLANNER — Critic feedback present, will focus on quality")

    logger.info("ANALYSIS PLANNER — Planned %d steps: %s", len(steps), steps)
    return steps
