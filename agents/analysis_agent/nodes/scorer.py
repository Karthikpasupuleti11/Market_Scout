"""
Analysis Agent — Scorer Tool

Calculates confidence scores using weighted formula:
  Confidence = (Recency × 0.4) + (Verification × 0.3) + (Authority × 0.3)
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from dateutil import parser as dateutil_parser
from app.config import settings

logger = logging.getLogger(__name__)


def _recency_score(publish_date_str: str, now: datetime) -> float:
    if not publish_date_str:
        return 0.8
    try:
        pub_date = dateutil_parser.parse(publish_date_str)
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        days_old = (now - pub_date).total_seconds() / 86400
        if days_old <= 1:
            return 1.0
        if days_old <= settings.DATE_WINDOW_DAYS:
            return max(0.5, 1.0 - (days_old / settings.DATE_WINDOW_DAYS) * 0.5)
        return 0.3
    except (ValueError, OverflowError):
        return 0.8


def _verification_score(source_count: int) -> float:
    if source_count <= 0:
        return 0.2
    if source_count == 1:
        return 0.4
    return min(1.0, 0.4 + math.log2(source_count) * 0.3)


def _authority_score(raw_score: float) -> float:
    return max(0.0, min(1.0, raw_score))


def scorer_tool(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate confidence scores for verified features."""
    now = datetime.now(timezone.utc)
    logger.info("SCORER — Calculating confidence for %d features", len(features))

    if not features:
        return {"scored_features": []}

    scored: List[Dict[str, Any]] = []

    for feature in features:
        recency = _recency_score(feature.get("publish_date"), now)
        verification = _verification_score(feature.get("source_count", 1))
        authority = _authority_score(feature.get("source_authority", 0.5))

        final = (recency * 0.4) + (verification * 0.3) + (authority * 0.3)
        final = round(min(1.0, final), 3)

        scored.append({
            **feature,
            "confidence_score": final,
            "score_breakdown": {
                "recency": round(recency, 3),
                "verification": round(verification, 3),
                "authority": round(authority, 3),
                "weights": {"recency": 0.4, "verification": 0.3, "authority": 0.3},
            },
        })

    scored.sort(key=lambda x: x["confidence_score"], reverse=True)
    logger.info("SCORER — Scored %d features (top: %.3f, bottom: %.3f)",
                len(scored), scored[0]["confidence_score"] if scored else 0,
                scored[-1]["confidence_score"] if scored else 0)

    return {"scored_features": scored}
