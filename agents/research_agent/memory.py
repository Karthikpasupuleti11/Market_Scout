"""
Research Agent — Memory

Tracks research history across iterations to avoid duplicate work.
"""

import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ResearchMemory:
    """Tracks what the Research Agent has done across iterations."""

    def __init__(self):
        self.searched_queries: List[str] = []
        self.scraped_urls: Set[str] = set()
        self.tools_used: List[str] = []
        self.iteration_history: List[Dict[str, Any]] = []

    def record_iteration(self, iteration: int, tools: List[str], result_count: int):
        """Record what happened in this iteration."""
        self.iteration_history.append({
            "iteration": iteration,
            "tools_used": tools,
            "results_found": result_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.tools_used.extend(tools)

    def was_url_scraped(self, url: str) -> bool:
        return url in self.scraped_urls

    def add_scraped_urls(self, urls: List[str]):
        self.scraped_urls.update(urls)

    def add_queries(self, queries: List[str]):
        self.searched_queries.extend(queries)

    def get_summary(self) -> str:
        """Summary of all research activity for handoff messages."""
        return (
            f"Searched {len(self.searched_queries)} queries, "
            f"scraped {len(self.scraped_urls)} URLs, "
            f"across {len(self.iteration_history)} iterations."
        )


def build_memory_from_state(state: Dict[str, Any]) -> ResearchMemory:
    """Build memory from existing state (reconstructs from previous iterations)."""
    memory = ResearchMemory()
    memory.add_queries(state.get("search_queries", []))
    memory.add_scraped_urls([a.get("url", "") for a in state.get("scraped_articles", [])])
    memory.tools_used = list(state.get("tools_used", []))
    return memory
