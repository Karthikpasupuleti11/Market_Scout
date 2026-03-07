"""
Supervisor Agent — Main Agent

The brain of the multi-agent system. Uses DETERMINISTIC routing first,
with LLM as a fallback only for ambiguous states.

Routing priority (checked top to bottom, first match wins):
  1. Error?              → done (exit)
  2. Has report?         → output_guardrail
  3. Max iterations?     → force-finish (analysis → synthesis)
  4. Critic REVISE?      → analysis (re-analyse, NOT re-research)
  5. No search results?  → research
  6. No scored features? → analysis
  7. Features + not approved? → critic
  8. Critic approved?    → synthesis
  9. LLM fallback        → ask the LLM

Components:
  • planner.py — deterministic routing fallback
  • memory.py — tracks routing history
"""

import json
import logging
from typing import Dict, Any

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from agents.supervisor.planner import deterministic_route
from agents.supervisor.memory import SupervisorMemory

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


def supervisor_node(state: GraphState) -> Dict[str, Any]:
    """Supervisor Agent — deterministic-first routing with LLM fallback."""
    company_name = state.get("company_name", "")
    iteration = state.get("iteration_count", 0)

    # ── Collect state signals ──────────────────────────────────────
    has_search_results = bool(state.get("search_results"))
    has_filtered_results = bool(state.get("filtered_results"))
    has_scored_features = bool(state.get("scored_features"))
    critic_approved = state.get("critic_approved", False)
    critic_feedback = state.get("critic_feedback", "")
    has_synthesis = bool(state.get("synthesis_report"))
    has_error = bool(state.get("error"))
    delegation_request = state.get("delegation_request", "")

    logger.info(
        "SUPERVISOR — State check: iteration=%d, search=%s, filtered=%s, "
        "scored=%s, critic_approved=%s, feedback=%s, synthesis=%s",
        iteration, has_search_results, has_filtered_results,
        has_scored_features, critic_approved, bool(critic_feedback), has_synthesis,
    )

    # ══════════════════════════════════════════════════════════════
    #  DETERMINISTIC ROUTING (checked in priority order)
    # ══════════════════════════════════════════════════════════════

    # ── 1. Error → exit ────────────────────────────────────────────
    if has_error and not delegation_request:
        logger.info("SUPERVISOR → done (error detected)")
        return {"next_agent": "done"}

    # ── 2. Report exists → output guardrail ────────────────────────
    if has_synthesis:
        logger.info("SUPERVISOR → output_guardrail (report complete)")
        return {"next_agent": "output_guardrail"}

    # ── 3. Max iterations → force pipeline to finish ───────────────
    if iteration >= MAX_ITERATIONS:
        logger.warning("SUPERVISOR → force-finishing (iteration %d >= max %d)", iteration, MAX_ITERATIONS)
        if has_scored_features:
            logger.info("SUPERVISOR → synthesis (has %d scored features)", len(state.get("scored_features", [])))
            return {"next_agent": "synthesis", "critic_approved": True, "critic_feedback": ""}
        elif has_filtered_results:
            logger.info("SUPERVISOR → analysis (has articles, needs features)")
            return {"next_agent": "analysis", "critic_approved": True, "critic_feedback": ""}
        else:
            logger.info("SUPERVISOR → synthesis (no data, will produce empty report)")
            return {"next_agent": "synthesis", "critic_approved": True, "critic_feedback": ""}

    # ── 4. Critic REVISE → re-analyse (NOT re-research) ───────────
    #  The Critic's feedback is about analysis QUALITY (descriptions,
    #  evidence, sources), not about needing different search results.
    #  So we clear analysis outputs and route to analysis, keeping
    #  the filtered_results (articles) intact.
    if critic_feedback and not critic_approved:
        logger.info(
            "SUPERVISOR → analysis (Critic REVISED iteration %d→%d, re-analysing with feedback)",
            iteration, iteration + 1,
        )
        return {
            "next_agent": "analysis",
            "iteration_count": iteration + 1,
            # Keep search data intact — articles are fine
            # Clear only analysis outputs for re-processing
            "extracted_features": [],
            "verified_features": [],
            "scored_features": [],
            "critic_feedback": "",        # Clear so it doesn't re-trigger
            "critic_approved": False,
        }

    # ── 5. Delegation request (analysis needs data) → research ─────
    if delegation_request == "need_more_data":
        logger.info("SUPERVISOR → research (delegation: analysis needs more data)")
        return {
            "next_agent": "research",
            "delegation_request": "",
            "error": "",
        }

    # ── 6. No search results → research ────────────────────────────
    if not has_search_results:
        logger.info("SUPERVISOR → research (no search results yet)")
        return {"next_agent": "research"}

    # ── 7. Has results but no scored features → analysis ───────────
    if has_search_results and not has_scored_features:
        logger.info("SUPERVISOR → analysis (has search results, needs features)")
        return {"next_agent": "analysis"}

    # ── 8. Has scored features but not approved → critic ───────────
    if has_scored_features and not critic_approved:
        logger.info("SUPERVISOR → critic (has %d features, needs review)", len(state.get("scored_features", [])))
        return {"next_agent": "critic"}

    # ── 9. Critic approved → synthesis ─────────────────────────────
    if critic_approved:
        logger.info("SUPERVISOR → synthesis (critic approved)")
        return {"next_agent": "synthesis"}

    # ══════════════════════════════════════════════════════════════
    #  LLM FALLBACK (should rarely reach here)
    # ══════════════════════════════════════════════════════════════
    logger.warning("SUPERVISOR — No deterministic route matched, using LLM fallback")

    try:
        decision = _llm_route(state, company_name, iteration)
    except Exception as exc:
        logger.warning("SUPERVISOR — LLM routing failed: %s — using deterministic fallback", exc)
        decision = deterministic_route(state)

    logger.info("SUPERVISOR → '%s' (LLM/fallback, iteration %d)", decision, iteration)
    return {"next_agent": decision}


def _llm_route(state: GraphState, company_name: str, iteration: int) -> str:
    """LLM-driven routing — used only when deterministic rules don't match."""
    agent_messages = state.get("agent_messages", [])
    recent_messages = agent_messages[-3:] if agent_messages else []
    messages_summary = "\n".join(
        [f"  [{m.get('from', '?')} → {m.get('to', '?')}]: {m.get('message', '')[:100]}"
         for m in recent_messages]
    ) or "  No messages yet."

    state_summary = {
        "company_name": company_name,
        "iteration": iteration,
        "has_search_results": bool(state.get("search_results")),
        "num_search_results": len(state.get("search_results", [])),
        "has_scored_features": bool(state.get("scored_features")),
        "num_features": len(state.get("scored_features", [])),
        "critic_approved": state.get("critic_approved", False),
    }

    prompt = f"""Pipeline state:
{json.dumps(state_summary, indent=2)}

Recent agent messages:
{messages_summary}

ROUTING RULES:
1. No search_results → "research"
2. search_results but no scored_features → "analysis"
3. scored_features but not approved → "critic"
4. critic_approved → "synthesis"

Respond with EXACTLY one word: research, analysis, critic, or synthesis."""

    response = invoke_llm(
        [
            {"role": "system", "content": "You route tasks to agents. Respond with one word only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0, max_tokens=10,
    )

    decision = response.strip().lower().strip('"').strip("'").strip(".")
    valid = {"research", "analysis", "critic", "synthesis"}
    if decision not in valid:
        return deterministic_route(state)
    return decision
