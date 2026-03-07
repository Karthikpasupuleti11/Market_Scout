"""
Analysis Agent — Feature Extractor Tool (PARALLEL)

Extracts structured features from articles using parallel LLM calls.
"""

import json
import re
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)

MAX_EXTRACT_THREADS = 5


def _clean_json_response(raw: str) -> str:
    cleaned = re.sub(r"```json\s?|\s?```", "", raw).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned


def _extract_single_article(article: Dict[str, Any], company_name: str) -> List[Dict[str, Any]]:
    """Extract features from a single article. Thread-safe."""
    url = article.get("url", "")

    # Cache check
    cache_key = make_cache_key("features", url)
    cached = get_cache(cache_key)
    if cached:
        return cached

    article_text = article.get("article_text", "")[:8000]

    system_message = {
        "role": "system",
        "content": (
            "You are a precise extraction engine for technical product updates. "
            "Use ONLY the text provided in DATA. "
            "If a feature, model, parameter, or metric is not EXPLICITLY mentioned in DATA, "
            "do NOT infer, assume, or invent it. "
            "If there are no explicit technical changes in DATA, return an empty JSON list []. "
            "NEVER fabricate feature names, version numbers, or performance metrics."
        ),
    }

    user_prompt = f"""Analyse the following technical update for {company_name}.

TASK: Extract ONLY specific, verifiable technical changes. For each feature, provide:
  - A concise title (max 10 words)
  - A detailed summary (2-3 sentences) explaining WHAT the feature does, HOW it works, and WHY it matters
  - Supporting evidence as a direct quote from the text

DATA:
{article_text}

REQUIRED JSON FORMAT (list of objects):
[
  {{
    "feature_summary": "2-3 sentence detailed explanation.",
    "feature_title": "Short title (max 10 words)",
    "category": "model_release" | "api_update" | "performance" | "capability" | "sdk_update" | "infrastructure" | "docs",
    "metrics": ["list of numerical data points explicitly stated in DATA"],
    "confidence": 0.0,
    "evidence": "Direct quote from DATA (max 200 chars)"
  }}
]

CONSTRAINTS:
  1. Do NOT use outside knowledge — only DATA.
  2. Do NOT invent model names, versions, or benchmarks.
  3. Each feature MUST have a detailed feature_summary.
  4. Each feature MUST have supporting evidence.
  5. If no qualifying technical changes exist, return [].

Return ONLY the JSON list."""

    try:
        response = invoke_llm(
            [system_message, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        cleaned = _clean_json_response(response)
        features = json.loads(cleaned)
        if not isinstance(features, list):
            features = []

        article_features = []
        for f in features:
            f["source_authority"] = article.get("authority_score", 0.5)
            f["url"] = url
            f["publish_date"] = article.get("publish_date")
            article_features.append(f)

        set_cache(cache_key, article_features)
        return article_features

    except json.JSONDecodeError as exc:
        logger.warning("EXTRACTOR — JSON parse error for %s: %s", url[:60], exc)
        return []
    except Exception as exc:
        logger.warning("EXTRACTOR — Error for %s: %s", url[:60], exc)
        return []


def extractor_tool(articles: List[Dict[str, Any]], company_name: str) -> Dict[str, Any]:
    """Extract features from all articles in PARALLEL."""
    logger.info("EXTRACTOR — Processing %d articles in parallel for '%s'", len(articles), company_name)

    if not articles:
        return {"extracted_features": []}

    all_features: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=MAX_EXTRACT_THREADS) as executor:
        futures = {executor.submit(_extract_single_article, a, company_name): a for a in articles}
        for future in as_completed(futures):
            try:
                features = future.result()
                all_features.extend(features)
            except Exception as exc:
                logger.warning("EXTRACTOR — Parallel extraction failed: %s", exc)

    logger.info("EXTRACTOR — Total features extracted: %d (parallel)", len(all_features))
    return {"extracted_features": all_features}
