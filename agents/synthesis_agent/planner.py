"""
Synthesis Agent — Planner

Decides report generation strategy based on available data.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def plan_synthesis(scored_features: List[Dict], company_name: str) -> Dict[str, Any]:
    """Plan synthesis strategy based on data quality.

    Strategy:
      - "full"     → 5+ features with good confidence → full LLM report
      - "minimal"  → 1-4 features → streamlined report
      - "empty"    → 0 features → empty report (no LLM call needed)
    """
    if not scored_features:
        strategy = "empty"
    elif len(scored_features) >= 5:
        strategy = "full"
    else:
        strategy = "minimal"

    avg_confidence = 0.0
    if scored_features:
        avg_confidence = sum(f.get("confidence_score", 0) for f in scored_features) / len(scored_features)

    logger.info(
        "SYNTHESIS PLANNER — Strategy: '%s' for '%s' (%d features, avg confidence: %.2f)",
        strategy, company_name, len(scored_features), avg_confidence,
    )

    return {
        "strategy": strategy,
        "feature_count": len(scored_features),
        "avg_confidence": round(avg_confidence, 3),
    }
