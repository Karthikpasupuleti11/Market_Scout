"""
Research Agent — Self-Critic

Reviews research quality before returning to Supervisor.
Checks: enough articles? diverse sources? relevant content?
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def self_review(state: Dict[str, Any]) -> Dict[str, Any]:
    """Review research quality. Returns assessment with pass/flag status."""
    filtered = state.get("filtered_results", [])
    search_results = state.get("search_results", [])
    scraped = state.get("scraped_articles", [])

    issues = []

    # Check: enough articles found?
    if len(filtered) == 0:
        issues.append("No articles passed date validation")
    elif len(filtered) < 3:
        issues.append(f"Only {len(filtered)} articles found (low coverage)")

    # Check: scraping success rate
    if search_results and scraped:
        success_rate = len(scraped) / len(search_results)
        if success_rate < 0.3:
            issues.append(f"Low scraping success rate: {success_rate:.0%}")

    # Check: source diversity
    if filtered:
        domains = set()
        for article in filtered:
            url = article.get("url", "")
            if "/" in url:
                domain = url.split("/")[2] if len(url.split("/")) > 2 else ""
                domains.add(domain)
        if len(domains) < 2:
            issues.append(f"Low source diversity: only {len(domains)} unique domain(s)")

    result = {
        "passed": len(issues) == 0,
        "issues": issues,
        "article_count": len(filtered),
        "source_count": len(search_results),
    }

    if issues:
        logger.info("RESEARCH CRITIC — Flagged %d issues: %s", len(issues), issues)
    else:
        logger.info("RESEARCH CRITIC — Passed (found %d articles)", len(filtered))

    return result
