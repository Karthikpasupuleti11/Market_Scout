"""Critic Agent — Memory. Tracks review decisions across iterations."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CriticMemory:
    def __init__(self):
        self.decisions: List[Dict[str, Any]] = []

    def record_decision(self, iteration: int, decision: str, feedback: str):
        self.decisions.append({
            "iteration": iteration, "decision": decision,
            "feedback": feedback[:200], "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_summary(self) -> str:
        return f"Made {len(self.decisions)} review decisions."
