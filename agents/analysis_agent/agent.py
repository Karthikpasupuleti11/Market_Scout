"""
Analysis Agent — Main Agent

Self-contained agent for data analysis.
Uses its own planner, tools (with parallel execution), critic, and memory.

Flow:
  1. Planner decides analysis strategy
  2. Content filter (PARALLEL LLM)
  3. Authority check
  4. Feature extraction (PARALLEL LLM)
  5. Verification (SBERT clustering)
  6. Scoring
  7. Self-critic reviews quality
  8. Returns results + handoff message
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from graph.state import GraphState
from agents.analysis_agent.planner import plan_analysis
from agents.analysis_agent.nodes.content_filter import content_filter_tool
from agents.analysis_agent.nodes.authority import authority_tool
from agents.analysis_agent.nodes.extractor import extractor_tool
from agents.analysis_agent.nodes.verifier import verifier_tool
from agents.analysis_agent.nodes.scorer import scorer_tool
from agents.analysis_agent.critic import self_review
from agents.analysis_agent.memory import build_memory_from_state

logger = logging.getLogger(__name__)


def analysis_agent_node(state: GraphState) -> Dict[str, Any]:
    """Analysis Agent — self-contained with own tools, planner, critic, memory."""
    company_name = state.get("company_name", "")
    iteration = state.get("iteration_count", 0)
    articles = state.get("filtered_results", [])
    critic_feedback = state.get("critic_feedback", "")

    logger.info("ANALYSIS AGENT — Starting (iteration %d) for '%s' with %d articles",
                iteration, company_name, len(articles))

    # ── Build memory ───────────────────────────────────────────────
    memory = build_memory_from_state(state)
    tools_used = []

    if not articles:
        logger.warning("ANALYSIS AGENT — No articles to analyse, requesting delegation")
        return {
            "delegation_request": "need_more_data",
            "tools_used": [],
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "analysis_agent", "to": "supervisor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "No articles to analyse. Requesting more data from Research Agent.",
            }],
        }

    # ── Step 1: Plan ───────────────────────────────────────────────
    plan_analysis(articles, has_critic_feedback=bool(critic_feedback))

    # ── Step 2: Content filter (PARALLEL) ──────────────────────────
    filter_result = content_filter_tool(articles)
    filtered = filter_result.get("filtered_results", [])
    tools_used.append("content_filter")

    if not filtered:
        logger.warning("ANALYSIS AGENT — All articles filtered out, requesting delegation")
        return {
            "delegation_request": "need_more_data",
            "tools_used": tools_used,
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "analysis_agent", "to": "supervisor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "All articles filtered out. Requesting broader research.",
            }],
        }

    # ── Step 3: Authority check ────────────────────────────────────
    authority_result = authority_tool(filtered, company_name)
    filtered = authority_result.get("filtered_results", filtered)
    tools_used.append("authority_check")

    # ── Step 4: Feature extraction (PARALLEL) ──────────────────────
    extract_result = extractor_tool(filtered, company_name)
    extracted = extract_result.get("extracted_features", [])
    tools_used.append("extract_features")

    # ── Step 5: Verification ───────────────────────────────────────
    verify_result = verifier_tool(extracted)
    verified = verify_result.get("verified_features", [])
    tools_used.append("verify_features")

    # ── Step 6: Scoring ────────────────────────────────────────────
    score_result = scorer_tool(verified)
    scored = score_result.get("scored_features", [])
    tools_used.append("score_features")

    # ── Step 7: Self-critic ────────────────────────────────────────
    review = self_review(scored)

    # ── Record iteration ───────────────────────────────────────────
    memory.record_iteration(iteration, tools_used, len(scored))

    # ── Build handoff message ──────────────────────────────────────
    handoff = (
        f"Analysis complete (iteration {iteration}). "
        f"Extracted {len(scored)} scored features from {len(filtered)} articles. "
        f"Self-review: {'PASSED' if review['passed'] else 'FLAGGED — ' + ', '.join(review['issues'])}. "
        f"Tools used: {tools_used}."
    )

    logger.info("ANALYSIS AGENT — Completed with %d scored features", len(scored))

    return {
        "filtered_results": filtered,
        "extracted_features": extracted,
        "verified_features": verified,
        "scored_features": scored,
        "tools_used": tools_used,
        "agent_messages": state.get("agent_messages", []) + [{
            "from": "analysis_agent", "to": "supervisor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": handoff,
        }],
    }
