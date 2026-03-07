"""
Analysis Agent — Memory

Tracks analysis history across iterations.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AnalysisMemory:
    """Tracks what the Analysis Agent has processed."""

    def __init__(self):
        self.processed_articles: int = 0
        self.extracted_count: int = 0
        self.tools_used: List[str] = []
        self.iteration_history: List[Dict[str, Any]] = []

    def record_iteration(self, iteration: int, tools: List[str], feature_count: int):
        self.iteration_history.append({
            "iteration": iteration,
            "tools_used": tools,
            "features_extracted": feature_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.tools_used.extend(tools)
        self.extracted_count = feature_count

    def get_summary(self) -> str:
        return (
            f"Processed {self.processed_articles} articles, "
            f"extracted {self.extracted_count} features, "
            f"across {len(self.iteration_history)} iterations."
        )


def build_memory_from_state(state: Dict[str, Any]) -> AnalysisMemory:
    memory = AnalysisMemory()
    memory.processed_articles = len(state.get("filtered_results", []))
    memory.extracted_count = len(state.get("scored_features", state.get("extracted_features", [])))
    memory.tools_used = list(state.get("tools_used", []))
    return memory
