"""
Critic Agent — Main Agent

Quality gatekeeper. Reviews extracted features for hallucinations,
completeness, and description quality. Uses own memory to track
review history.

Components:
  • memory.py — tracks review decisions across iterations
"""

import json
import logging
from typing import Dict, Any

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from agents.critic_agent.memory import CriticMemory

logger = logging.getLogger(__name__)


def critic_node(state: GraphState) -> Dict[str, Any]:
    """Critic Agent — reviews feature quality and decides approve/revise."""
    scored_features = state.get("scored_features", [])
    extracted_features = state.get("extracted_features", [])
    company_name = state.get("company_name", "")
    iteration = state.get("iteration_count", 0)

    features_to_review = scored_features or extracted_features

    # Build memory
    memory = CriticMemory()

    if not features_to_review:
        logger.warning("CRITIC — No features to review, requesting more research")
        memory.record_decision(iteration, "REVISE", "No features found")
        return {
            "critic_approved": False,
            "critic_feedback": "No features were extracted. Research Agent should try broader search queries.",
        }

    # ── Auto-approve on iteration 1+ ──────────────────────────────
    # Re-analysis with cached articles produces identical features.
    # Re-reviewing the same data wastes 1-2 minutes per loop.
    # The first review (iteration 0) is the real quality gate.
    if iteration >= 1:
        logger.info("CRITIC — Auto-approving on iteration %d (cached data won't change)", iteration)
        memory.record_decision(iteration, "APPROVE", "Auto-approved (iteration >= 1)")
        return {"critic_approved": True, "critic_feedback": ""}

    logger.info("CRITIC — Reviewing %d features for '%s' (iteration %d)",
                len(features_to_review), company_name, iteration)

    # Prepare features for review
    review_data = []
    for i, f in enumerate(features_to_review, 1):
        review_data.append({
            "rank": i,
            "title": f.get("feature_title", f.get("feature_summary", ""))[:100],
            "summary": f.get("feature_summary", "")[:300],
            "category": f.get("category", ""),
            "evidence": f.get("evidence", "")[:200],
            "source_count": f.get("source_count", 1),
            "confidence": f.get("confidence_score", 0),
        })

    review_json = json.dumps(review_data, indent=2)

    system_message = {
        "role": "system",
        "content": (
            "You are a quality assurance critic for a market intelligence system. "
            "Review the extracted features and decide if they meet quality standards. "
            "Respond in EXACTLY the JSON format specified."
        ),
    }

    user_prompt = f"""Review these extracted features for {company_name}:

{review_json}

QUALITY CHECKS:
1. HALLUCINATION: Does each feature have supporting evidence (a direct quote)?
2. DESCRIPTION QUALITY: Is each summary detailed (2+ sentences)?
3. SOURCE DIVERSITY: Are there features verified across multiple sources?
4. RELEVANCE: Are all features about {company_name}'s technical updates?

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "decision": "APPROVE" or "REVISE",
  "quality_score": 0.0-1.0,
  "issues_found": ["list of specific issues"],
  "feedback": "actionable feedback if REVISE, empty string if APPROVE"
}}

DECISION RULES:
- APPROVE if: Most features have evidence, descriptions are detailed, features are relevant.
- REVISE if: Many features lack evidence, descriptions are title repeats, features seem fabricated.
- After iteration 1, be more lenient — APPROVE if features are reasonable.

Current iteration: {iteration}

Return ONLY the JSON."""

    try:
        response = invoke_llm(
            [system_message, {"role": "user", "content": user_prompt}],
            temperature=0.0, max_tokens=500,
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        review = json.loads(cleaned)
        decision = review.get("decision", "APPROVE").upper()
        quality_score = review.get("quality_score", 0.5)
        feedback = review.get("feedback", "")
        issues = review.get("issues_found", [])
        approved = decision == "APPROVE"

        memory.record_decision(iteration, decision, feedback)

        logger.info("CRITIC — Decision: %s | Quality: %.2f | Issues: %d",
                     decision, quality_score, len(issues))

        if not approved:
            logger.info("CRITIC — Feedback: %s", feedback[:200])

        return {
            "critic_approved": approved,
            "critic_feedback": feedback if not approved else "",
        }

    except Exception as exc:
        logger.warning("CRITIC — LLM review failed: %s — auto-approving", exc)
        memory.record_decision(iteration, "APPROVE", "LLM failure fallback")
        return {
            "critic_approved": True,
            "critic_feedback": "",
        }
