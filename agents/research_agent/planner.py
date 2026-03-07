"""
Research Agent — Planner

Generates targeted search queries using LLM reasoning.
Incorporates critic feedback to broaden or refocus queries.
"""

import json
import re
import logging
from typing import Dict, Any, List

from pydantic import BaseModel, field_validator

from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache

logger = logging.getLogger(__name__)


class SearchPlannerOutput(BaseModel):
    queries: List[str]

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one search query is required.")
        if len(v) > 5:
            v = v[:5]
        return [q.strip() for q in v if q.strip()]


def _extract_json(raw: str) -> dict:
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    raise ValueError(f"No valid JSON found in LLM response: {raw[:200]}")


def plan_queries(company_name: str, critic_feedback: str = "") -> List[str]:
    """Generate search queries for a company. Returns list of query strings."""
    logger.info("RESEARCH PLANNER — Generating queries for: '%s'", company_name)

    # Cache check (skip if critic feedback suggests new approach)
    if not critic_feedback:
        cache_key = make_cache_key("search_queries", company_name)
        cached = get_cache(cache_key)
        if cached:
            logger.info("RESEARCH PLANNER — Cache hit, returning %d queries", len(cached))
            return cached

    feedback_section = ""
    if critic_feedback:
        feedback_section = f"""
IMPORTANT — Previous analysis was rejected. Critic feedback:
{critic_feedback}
Adjust your queries to address these concerns. Try different source types."""

    prompt = f"""You are a Market Intelligence search strategist.

Generate exactly 4 highly targeted search queries to discover
TECHNICAL FEATURE updates released in the last 7 days for:

Company: {company_name}
{feedback_section}

Query categories (one per category):
  1. Official release notes / changelogs
  2. API or SDK updates
  3. New model releases or capability announcements
  4. Developer documentation changes

Constraints:
  - Focus ONLY on: APIs, models, SDKs, architectures, performance benchmarks
  - AVOID: financial news, stock analysis, HR updates, opinion pieces, lawsuits
  - Each query must include temporal modifiers (e.g. "2026", "latest", "new")

Return ONLY this exact JSON format:
{{
  "queries": ["query1", "query2", "query3", "query4"]
}}"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict JSON generator for enterprise search planning. "
                "Return ONLY valid JSON with no preamble or explanation."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.3, max_tokens=512)
        parsed = _extract_json(response)
        validated = SearchPlannerOutput(**parsed)
        queries = validated.queries
    except Exception as exc:
        logger.error("RESEARCH PLANNER — LLM / parse error: %s", exc)
        queries = [
            f"{company_name} latest technical feature release 2026",
            f"{company_name} API update changelog new",
            f"{company_name} developer documentation SDK update",
            f"{company_name} new model release announcement",
        ]
        logger.warning("RESEARCH PLANNER — Using fallback queries")

    # Cache result
    if not critic_feedback:
        cache_key = make_cache_key("search_queries", company_name)
        set_cache(cache_key, queries)

    logger.info("RESEARCH PLANNER — Generated %d queries", len(queries))
    return queries
