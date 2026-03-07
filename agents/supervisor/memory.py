"""
Supervisor Agent — Memory

Tracks routing history across the pipeline run.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SupervisorMemory:
    """Tracks routing decisions for audit trail."""

    def __init__(self):
        self.routing_history: List[Dict[str, Any]] = []
        self.total_routes: int = 0

    def record_decision(self, iteration: int, agent: str, reason: str):
        self.routing_history.append({
            "iteration": iteration,
            "routed_to": agent,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.total_routes += 1

    def get_summary(self) -> str:
        return f"Made {self.total_routes} routing decisions."
