"""
Supervisor Agent — Planner

Deterministic routing rules for known state patterns.
Acts as fallback when LLM routing fails.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def deterministic_route(state: Dict[str, Any]) -> str:
    """Rule-based routing fallback."""
    if state.get("delegation_request") == "need_more_data":
        return "research"
    if not state.get("search_results"):
        return "research"
    if not state.get("scored_features"):
        return "analysis"
    if not state.get("critic_approved", False):
        return "critic"
    return "synthesis"
