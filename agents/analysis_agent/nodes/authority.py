"""
Analysis Agent — Authority Check Tool

Classifies sources as PRIMARY or SECONDARY.
"""

import logging
from typing import Dict, Any, List

from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)


def authority_tool(articles: List[Dict[str, Any]], company_name: str) -> Dict[str, Any]:
    """Classify article source credibility for a company."""
    logger.info("AUTHORITY CHECK — Evaluating %d articles for '%s'", len(articles), company_name)

    if not articles:
        return {"filtered_results": []}

    validated: List[Dict[str, Any]] = []

    for article in articles:
        title = article.get("title", "N/A")
        url = article.get("url", "")

        prompt = f"""You are an enterprise source-credibility classifier.

Determine if this article is an OFFICIAL or PRIMARY technical source for {company_name}.

PRIMARY sources include:
  - Official company blogs, docs, or changelogs
  - GitHub repositories owned by {company_name}
  - First-party developer documentation
  - Official press releases with technical detail

SECONDARY sources include:
  - News aggregation sites reporting about {company_name}
  - Third-party commentary or analysis
  - Community discussions

Title: {title}
URL: {url}

Respond with ONLY one word: PRIMARY or SECONDARY"""

        messages = [
            {"role": "system", "content": "You are a strict source classifier. Respond with one word."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = invoke_llm(messages, temperature=0.0, max_tokens=10)
            decision = response.strip().upper()

            if "PRIMARY" in decision:
                validated.append(article)
            else:
                article_copy = dict(article)
                article_copy["authority_score"] = article_copy.get("authority_score", 0.5) * 0.7
                validated.append(article_copy)
        except Exception as exc:
            logger.warning("AUTHORITY — LLM error for '%s': %s — defaulting to include", url[:40], exc)
            validated.append(article)

    logger.info("AUTHORITY CHECK — %d articles passed", len(validated))
    return {"filtered_results": validated}
