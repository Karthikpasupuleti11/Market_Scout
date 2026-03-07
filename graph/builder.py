"""
Market Intelligence Scout — LangGraph Multi-Agent Orchestration (v3.0)

Industry-grade self-contained agent architecture:
  • Supervisor Agent   — LLM-driven dynamic routing (own planner, memory)
  • Research Agent     — Search + Scrape + Date Filter (PARALLEL tools)
  • Analysis Agent     — Filter + Extract + Verify + Score (PARALLEL tools)
  • Critic Agent       — Quality review with feedback loops (own memory)
  • Synthesis Agent    — Final report generation (own memory)
  • Output Guardrail   — Validates report before returning to user

Pipeline:
  [Input Guardrails] → [Supervisor] ⇄ [Research | Analysis | Critic]
                              ↓
                      [Synthesis] → [Output Guardrail] → DONE
"""

import logging
import time
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from graph.state import GraphState
from observability.metrics import NODE_LATENCY, NODE_SUCCESS

# ── Agent Package Imports ──────────────────────────────────────────
from guardrails.input_guardrail import guardrails_node
from guardrails.output_guardrail import output_guardrail_node
from agents.supervisor import supervisor_node
from agents.research_agent import research_agent_node
from agents.analysis_agent import analysis_agent_node
from agents.critic_agent import critic_node
from agents.synthesis_agent import synthesis_node

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Node Instrumentation Wrapper
# ────────────────────────────────────────────────────────────────────

def _instrument_node(name: str, fn):
    """Wrap a node function with Prometheus latency and success metrics."""
    def wrapper(state: GraphState) -> Dict[str, Any]:
        start = time.time()
        try:
            result = fn(state)
            NODE_SUCCESS.labels(node_name=name, status="success").inc()
            return result
        except Exception as exc:
            NODE_SUCCESS.labels(node_name=name, status="failure").inc()
            raise
        finally:
            NODE_LATENCY.labels(node_name=name).observe(time.time() - start)
    wrapper.__name__ = fn.__name__
    return wrapper


# ────────────────────────────────────────────────────────────────────
# Error Exit Node
# ────────────────────────────────────────────────────────────────────

def error_exit_node(state: GraphState) -> Dict[str, Any]:
    """Terminal node for pipeline failures."""
    error_msg = state.get("error", "Unknown pipeline error")
    company = state.get("company_name", "N/A")

    logger.error("PIPELINE ERROR — Company: '%s' — Error: %s", company, error_msg)

    return {
        "synthesis_report": {
            "company_name": company,
            "generated_at": "",
            "executive_summary": f"Pipeline terminated: {error_msg}",
            "features": [],
            "total_sources_analysed": 0,
            "total_features_verified": 0,
            "metadata": {"error": error_msg, "pipeline_version": "3.0-multi-agent"},
        }
    }


# ────────────────────────────────────────────────────────────────────
# Conditional Edge Functions (Dynamic Routing)
# ────────────────────────────────────────────────────────────────────

def _check_guardrail(state: GraphState) -> str:
    if state.get("error"):
        return "error_exit"
    return "supervisor"


def _route_supervisor(state: GraphState) -> str:
    """Route based on Supervisor's LLM-driven decision."""
    next_agent = state.get("next_agent", "done")

    if state.get("error"):
        return "error_exit"

    route_map = {
        "research": "research",
        "analysis": "analysis",
        "critic": "critic",
        "synthesis": "synthesis",
        "output_guardrail": "output_guardrail",
        "done": "done",
    }
    return route_map.get(next_agent, "done")


def _after_worker(state: GraphState) -> str:
    """After worker agent → route back to Supervisor."""
    if state.get("error"):
        return "error_exit"
    return "supervisor"


# ────────────────────────────────────────────────────────────────────
# Graph Builder
# ────────────────────────────────────────────────────────────────────

def build_graph():
    """Assemble and compile the multi-agent LangGraph pipeline.

    Architecture:
      Input Guardrails → Supervisor → {Research, Analysis, Critic, Synthesis}
                             ↑                            ↓
                             └──── loop back to Supervisor ┘
                                        ↓
                             Synthesis → Output Guardrail → DONE
    """
    builder = StateGraph(GraphState)

    # ── Register all nodes (instrumented) ──────────────────────────
    builder.add_node("guardrails", _instrument_node("guardrails", guardrails_node))
    builder.add_node("supervisor", _instrument_node("supervisor", supervisor_node))
    builder.add_node("research", _instrument_node("research", research_agent_node))
    builder.add_node("analysis", _instrument_node("analysis", analysis_agent_node))
    builder.add_node("critic", _instrument_node("critic", critic_node))
    builder.add_node("synthesis", _instrument_node("synthesis", synthesis_node))
    builder.add_node("output_guardrail", _instrument_node("output_guardrail", output_guardrail_node))
    builder.add_node("error_exit", error_exit_node)

    # ── Entry point ────────────────────────────────────────────────
    builder.set_entry_point("guardrails")

    # ── Guardrails → Supervisor or Error ───────────────────────────
    builder.add_conditional_edges("guardrails", _check_guardrail, {
        "supervisor": "supervisor",
        "error_exit": "error_exit",
    })

    # ── Supervisor → Dynamic routing to agents ─────────────────────
    builder.add_conditional_edges("supervisor", _route_supervisor, {
        "research": "research",
        "analysis": "analysis",
        "critic": "critic",
        "synthesis": "synthesis",
        "output_guardrail": "output_guardrail",
        "error_exit": "error_exit",
        "done": END,
    })

    # ── Worker agents → back to Supervisor ─────────────────────────
    builder.add_conditional_edges("research", _after_worker, {
        "supervisor": "supervisor",
        "error_exit": "error_exit",
    })

    builder.add_conditional_edges("analysis", _after_worker, {
        "supervisor": "supervisor",
        "error_exit": "error_exit",
    })

    builder.add_conditional_edges("critic", _after_worker, {
        "supervisor": "supervisor",
        "error_exit": "error_exit",
    })

    # ── Synthesis → Output Guardrail → DONE ────────────────────────
    builder.add_edge("synthesis", "output_guardrail")
    builder.add_edge("output_guardrail", END)
    builder.add_edge("error_exit", END)

    # ── Compile ────────────────────────────────────────────────────
    compiled = builder.compile()
    logger.info("GRAPH — Multi-agent pipeline compiled (Supervisor + 5 worker agents + Output Guardrail)")

    return compiled