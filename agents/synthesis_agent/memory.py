"""Synthesis Agent — Memory. Tracks generated reports."""

from typing import Dict, Any, List
from datetime import datetime, timezone


class SynthesisMemory:
    def __init__(self):
        self.reports: List[Dict[str, Any]] = []

    def record_report(self, company: str, feature_count: int):
        self.reports.append({
            "company": company, "features": feature_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
