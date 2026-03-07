"""
Analysis Agent — Content Filter Tool (PARALLEL)

Classifies articles as TECHNICAL or REJECT using parallel LLM calls.
"""

import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)

MAX_FILTER_THREADS = 5


def _classify_single_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a single article. Thread-safe. Returns (article, accepted)."""
    title = article.get("title", "N/A")
    text_snippet = article.get("article_text", "")[:600]
    url = article.get("url", "")

    prompt = f"""You are an enterprise content classifier for a Market Intelligence system.

Classify this article's primary intent:

ACCEPT if it contains:
  - API changelogs or SDK updates
  - New model/product releases with technical specs
  - Architecture or infrastructure changes
  - Developer documentation updates
  - Performance benchmark results

REJECT if it is:
  - Stock/financial analysis
  - Corporate restructuring / HR news
  - Opinion articles or commentary
  - Marketing fluff without technical substance
  - Legal or regulatory news

Title: {title}
URL: {url}
Content excerpt:
{text_snippet}

Respond with ONLY one word: ACCEPT or REJECT"""

    messages = [
        {"role": "system", "content": "You are a strict binary classifier. Respond with exactly one word."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.0, max_tokens=10)
        decision = response.strip().upper()
        return {"article": article, "accepted": "ACCEPT" in decision}
    except Exception as exc:
        logger.warning("CONTENT FILTER — LLM error for '%s': %s — defaulting to ACCEPT", title[:40], exc)
        return {"article": article, "accepted": True}


def content_filter_tool(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Filter articles for technical relevance in PARALLEL."""
    logger.info("CONTENT FILTER — Evaluating %d articles in parallel", len(articles))

    if not articles:
        return {"filtered_results": []}

    validated: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=MAX_FILTER_THREADS) as executor:
        futures = {executor.submit(_classify_single_article, a): a for a in articles}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result["accepted"]:
                    validated.append(result["article"])
            except Exception as exc:
                logger.warning("CONTENT FILTER — Parallel classify failed: %s", exc)

    logger.info("CONTENT FILTER — %d/%d articles passed (parallel)", len(validated), len(articles))
    return {"filtered_results": validated}
