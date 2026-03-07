"""
Market Intelligence Scout — Output Guardrail

Post-Synthesis security gate. Validates the final report before returning to user.

Checks:
  1. Report completeness — summary + features + sources exist
  2. Score sanity — confidence scores between 0.0–1.0
  3. Prompt leak detection — system prompts not in report
  4. Data exposure — no API keys, internal paths, PII
  5. URL validation — all cited sources were actually scraped
"""

import re
import logging
from typing import Dict, Any, List

from graph.state import GraphState

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Detection Patterns
# ────────────────────────────────────────────────────────────────────

PROMPT_LEAK_PATTERNS = [
    r"you are a.*analyst",
    r"you are a.*classifier",
    r"you are a.*critic",
    r"respond with exactly",
    r"return only.*json",
    r"do not invent",
    r"system prompt",
    r"NVIDIA_API_KEY",
    r"TAVILY_API_KEY",
    r"HF_API_TOKEN",
]

SENSITIVE_PATTERNS = [
    r"nvapi-[A-Za-z0-9_-]{20,}",           # NVIDIA API key
    r"tvly-[A-Za-z0-9]{20,}",              # Tavily API key
    r"hf_[A-Za-z0-9]{20,}",                # HuggingFace token
    r"sk-[A-Za-z0-9]{20,}",                # OpenAI-style key
    r"(?:password|passwd|pwd)\s*[:=]\s*\S+", # Password patterns
    r"C:\\\\Users\\\\",                      # Windows paths
    r"/home/\w+/",                           # Unix paths
]


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def output_guardrail_node(state: GraphState) -> Dict[str, Any]:
    """
    Output Guardrail — validates the final report before returning to user.

    Checks:
      1. Report completeness (summary + features + sources)
      2. Confidence score sanity (0.0–1.0)
      3. Prompt leak detection
      4. Sensitive data exposure (API keys, paths → redacted)
      5. URL validation (cited sources were actually scraped)
    """
    report = state.get("synthesis_report", {})

    if not report:
        logger.warning("OUTPUT GUARDRAIL — No report to validate")
        return {"synthesis_report": report}

    issues: List[str] = []
    sanitized_report = dict(report)

    # ── 1. Report Completeness ─────────────────────────────────────
    if not report.get("executive_summary"):
        issues.append("Missing executive_summary")
    if not report.get("features"):
        issues.append("Missing features list")
    if not report.get("company_name"):
        issues.append("Missing company_name")

    # ── 2. Confidence Score Sanity ─────────────────────────────────
    features = report.get("features", [])
    for i, feature in enumerate(features):
        score = feature.get("confidence_score", 0)
        if score < 0.0 or score > 1.0:
            issues.append(f"Feature #{i+1} has invalid confidence_score: {score}")
            feature["confidence_score"] = max(0.0, min(1.0, score))

    # ── 3. Prompt Leak Detection ───────────────────────────────────
    report_text = str(report).lower()
    for pattern in PROMPT_LEAK_PATTERNS:
        if re.search(pattern, report_text, re.IGNORECASE):
            issues.append(f"Potential prompt leak detected: '{pattern}'")

    # ── 4. Sensitive Data Exposure ─────────────────────────────────
    report_str = str(report)
    for pattern in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, report_str, re.IGNORECASE)
        if matches:
            issues.append(f"Sensitive data exposure detected: {len(matches)} matches")
            exec_summary = sanitized_report.get("executive_summary", "")
            sanitized_report["executive_summary"] = re.sub(
                pattern, "[REDACTED]", exec_summary, flags=re.IGNORECASE
            )
            for feature in sanitized_report.get("features", []):
                desc = feature.get("description", "")
                feature["description"] = re.sub(
                    pattern, "[REDACTED]", desc, flags=re.IGNORECASE
                )

    # ── 5. URL Validation ──────────────────────────────────────────
    scraped_urls = set()
    for article in state.get("scraped_articles", []):
        scraped_urls.add(article.get("url", ""))
    for result in state.get("search_results", []):
        scraped_urls.add(result.get("url", ""))

    for feature in features:
        source_url = feature.get("source_url", "")
        if source_url and source_url not in scraped_urls:
            issues.append(f"Feature cites unverified URL: {source_url[:60]}")

    # ── Log Results ────────────────────────────────────────────────
    if issues:
        logger.warning("OUTPUT GUARDRAIL — Found %d issues: %s", len(issues), issues[:5])
    else:
        logger.info("OUTPUT GUARDRAIL — All checks passed ✓")

    sanitized_report["guardrail_validation"] = {
        "passed": len(issues) == 0,
        "issues_count": len(issues),
        "checks_run": ["completeness", "score_sanity", "prompt_leak", "data_exposure", "url_validation"],
    }

    return {"synthesis_report": sanitized_report}
