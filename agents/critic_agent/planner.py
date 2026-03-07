"""
Critic Agent — Planner

The Critic Agent has a simple strategy: review everything it receives.
This planner exists for structural consistency across all agent packages.
In the future, it could decide review depth based on iteration count.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def plan_review(features: List[Dict], iteration: int) -> Dict[str, Any]:
    """Plan the review strategy based on context.

    Strategy:
      - Iteration 0: Full strict review (first pass)
      - Iteration 1+: Lenient review (already been through one cycle)
    """
    if iteration == 0:
        strategy = "strict"
        logger.info("CRITIC PLANNER — First pass: strict review of %d features", len(features))
    else:
        strategy = "lenient"
        logger.info("CRITIC PLANNER — Iteration %d: lenient review of %d features", iteration, len(features))

    return {
        "strategy": strategy,
        "feature_count": len(features),
        "iteration": iteration,
    }
