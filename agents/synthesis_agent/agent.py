"""
Synthesis Agent — Main Agent

Generates executive-ready intelligence reports from scored features.
Uses own memory to track generated reports.
"""

import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)


def _validate_report(report: dict) -> bool:
    return all(field in report for field in ["executive_summary", "features"])


def _clean_json_response(raw: str) -> str:
    cleaned = re.sub(r"```json\s?|\s?```", "", raw).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned


def synthesis_node(state: GraphState) -> Dict[str, Any]:
    """Synthesis Agent — generates executive-ready intelligence report."""
    scored_features = state.get("scored_features", [])
    company_name = state.get("company_name", "")
    now = datetime.now(timezone.utc)

    logger.info("SYNTHESIS — Generating report for '%s' with %d features",
                company_name, len(scored_features))

    # Cache check
    cache_key = make_cache_key("report", company_name)
    cached = get_cache(cache_key)
    if cached:
        logger.info("SYNTHESIS — Cache hit, returning cached report")
        return {"synthesis_report": cached}

    # Handle empty features
    if not scored_features:
        report = {
            "company_name": company_name,
            "generated_at": now.isoformat(),
            "executive_summary": (
                f"No verified technical feature updates were found for "
                f"{company_name} within the last {settings.DATE_WINDOW_DAYS} days."
            ),
            "features": [],
            "total_sources_analysed": 0,
            "total_features_verified": 0,
            "all_sources": [],
            "metadata": {"pipeline_version": "3.0", "model": settings.LLM_MODEL},
        }
        set_cache(cache_key, report)
        return {"synthesis_report": report}

    # Prepare feature data
    features_for_prompt = []
    for i, f in enumerate(scored_features, 1):
        features_for_prompt.append({
            "rank": i,
            "title": f.get("feature_title", f.get("feature_summary", "")[:80]),
            "summary": f.get("feature_summary", ""),
            "category": f.get("category", ""),
            "confidence": f.get("confidence_score", 0),
            "source_count": f.get("source_count", 1),
            "primary_url": f.get("primary_url", ""),
            "metrics": f.get("metrics", []),
            "evidence": f.get("evidence", ""),
        })

    features_json = json.dumps(features_for_prompt, indent=2)

    system_message = {
        "role": "system",
        "content": (
            "You are an enterprise intelligence analyst. Generate structured JSON reports. "
            "Use ONLY the verified features provided. Do NOT add features, metrics, or "
            "claims not present in the input data."
        ),
    }

    user_prompt = f"""Generate a Market Intelligence Report for {company_name}.

VERIFIED FEATURES DATA:
{features_json}

REQUIRED JSON FORMAT:
{{
  "executive_summary": "2-3 sentence overview with specific metrics.",
  "features": [
    {{
      "rank": 1,
      "title": "Feature title",
      "description": "Detailed 2-3 sentence description",
      "category": "category",
      "confidence_score": 0.95,
      "impact_assessment": "Brief impact assessment",
      "source_url": "primary URL",
      "source_count": 2,
      "key_metrics": ["metric1"]
    }}
  ]
}}

CONSTRAINTS:
  1. Use ONLY facts from VERIFIED FEATURES DATA.
  2. Do NOT invent metrics or capabilities.
  3. Order features by confidence score (descending).

Return ONLY the JSON."""

    try:
        response = invoke_llm(
            [system_message, {"role": "user", "content": user_prompt}],
            temperature=0.1, max_tokens=settings.LLM_MAX_TOKENS,
        )
        cleaned = _clean_json_response(response)
        llm_report = json.loads(cleaned)
        if not _validate_report(llm_report):
            raise ValueError("LLM report missing required fields")
    except Exception as exc:
        logger.warning("SYNTHESIS — LLM failed: %s — using fallback", exc)
        llm_report = {
            "executive_summary": (
                f"{company_name} has released {len(scored_features)} verified "
                f"technical updates in the past {settings.DATE_WINDOW_DAYS} days."
            ),
            "features": [
                {
                    "rank": i + 1,
                    "title": f.get("feature_title", f.get("feature_summary", ""))[:80],
                    "description": f.get("feature_summary", ""),
                    "category": f.get("category", ""),
                    "confidence_score": f.get("confidence_score", 0),
                    "impact_assessment": "Requires manual assessment",
                    "source_url": f.get("primary_url", ""),
                    "source_count": f.get("source_count", 1),
                    "key_metrics": f.get("metrics", []),
                }
                for i, f in enumerate(scored_features)
            ],
        }

    all_sources = list({
        url for f in scored_features
        for url in f.get("all_sources", [f.get("primary_url", "")])
        if url
    })

    report = {
        "company_name": company_name,
        "generated_at": now.isoformat(),
        "executive_summary": llm_report.get("executive_summary", ""),
        "features": llm_report.get("features", []),
        "total_sources_analysed": len(all_sources),
        "total_features_verified": len(scored_features),
        "all_sources": all_sources,
        "metadata": {
            "pipeline_version": "3.0",
            "model": settings.LLM_MODEL,
            "date_window_days": settings.DATE_WINDOW_DAYS,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
            "discarded_urls_count": len(state.get("discarded_urls", [])),
        },
    }

    set_cache(cache_key, report)
    logger.info("SYNTHESIS — Report generated: %d features, %d sources",
                len(report["features"]), report["total_sources_analysed"])

    return {"synthesis_report": report}
