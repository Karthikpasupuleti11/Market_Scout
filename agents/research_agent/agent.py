"""
Research Agent — Main Agent

Self-contained ReAct tool-use agent for web research.
Uses its own planner, tools, critic, and memory.

Flow:
  1. Planner generates search queries
  2. Search tool finds URLs (PARALLEL)
  3. Scraper tool fetches articles (PARALLEL)
  4. Date filter validates recency
  5. Self-critic reviews quality
  6. Returns results + handoff message to Supervisor
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from graph.state import GraphState
from agents.research_agent.planner import plan_queries
from agents.research_agent.nodes.search import search_tool
from agents.research_agent.nodes.scraper import scraper_tool
from agents.research_agent.nodes.date_filter import date_filter_tool
from agents.research_agent.critic import self_review
from agents.research_agent.memory import build_memory_from_state

logger = logging.getLogger(__name__)


def research_agent_node(state: GraphState) -> Dict[str, Any]:
    """Research Agent — self-contained agent with own tools, planner, critic, memory."""
    company_name = state.get("company_name", "")
    iteration = state.get("iteration_count", 0)
    critic_feedback = state.get("critic_feedback", "")

    logger.info("RESEARCH AGENT — Starting (iteration %d) for '%s'", iteration, company_name)

    # ── Build memory ───────────────────────────────────────────────
    memory = build_memory_from_state(state)

    # ── Step 1: Plan queries ───────────────────────────────────────
    queries = plan_queries(company_name, critic_feedback=critic_feedback)
    memory.add_queries(queries)
    tools_used = ["plan_queries"]

    # ── Step 2: Search (PARALLEL) ──────────────────────────────────
    search_result = search_tool(queries, company_name)
    search_results = search_result.get("search_results", [])
    tools_used.append("search")

    if not search_results:
        logger.warning("RESEARCH AGENT — No search results found")
        return {
            "search_queries": queries,
            "search_results": [],
            "scraped_articles": [],
            "filtered_results": [],
            "tools_used": tools_used,
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "research_agent", "to": "supervisor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Research failed: no search results found.",
            }],
        }

    # ── Step 3: Scrape (PARALLEL) ──────────────────────────────────
    scrape_result = scraper_tool(search_results, company_name)
    scraped_articles = scrape_result.get("scraped_articles", [])
    memory.add_scraped_urls([a.get("url", "") for a in scraped_articles])
    tools_used.append("scraper")

    # ── Step 4: Date filter ────────────────────────────────────────
    filter_result = date_filter_tool(scraped_articles, company_name)
    filtered_results = filter_result.get("filtered_results", [])
    tools_used.append("date_filter")

    # ── Step 5: Self-critic ────────────────────────────────────────
    review_state = {
        "search_results": search_results,
        "scraped_articles": scraped_articles,
        "filtered_results": filtered_results,
    }
    review = self_review(review_state)

    # ── Record iteration ───────────────────────────────────────────
    memory.record_iteration(iteration, tools_used, len(filtered_results))

    # ── Build handoff message ──────────────────────────────────────
    handoff = (
        f"Research complete (iteration {iteration}). "
        f"Found {len(filtered_results)} articles within 7-day window "
        f"(from {len(search_results)} search results, {len(scraped_articles)} scraped). "
        f"Self-review: {'PASSED' if review['passed'] else 'FLAGGED — ' + ', '.join(review['issues'])}. "
        f"Tools used: {tools_used}."
    )

    logger.info("RESEARCH AGENT — Completed after %d tools (%d articles)", len(tools_used), len(filtered_results))

    return {
        "search_queries": queries,
        "search_results": search_results,
        "scraped_articles": scraped_articles,
        "filtered_results": filtered_results,
        "discarded_urls": filter_result.get("discarded_urls", []),
        "tools_used": tools_used,
        "agent_messages": state.get("agent_messages", []) + [{
            "from": "research_agent", "to": "supervisor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": handoff,
        }],
    }
