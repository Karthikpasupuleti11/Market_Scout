"""
Research Agent — Date Filter Tool

Filters articles to the 7-day recency window.
Audit logs discarded URLs to Redis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from dateutil import parser as dateutil_parser

from cache.redis_client import append_audit_log
from app.config import settings
from observability.metrics import URLS_DISCARDED

logger = logging.getLogger(__name__)


def date_filter_tool(articles: List[Dict[str, Any]], company_name: str) -> Dict[str, Any]:
    """Filter articles to the 7-day window. Returns filtered + discarded."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.DATE_WINDOW_DAYS)

    valid: List[Dict[str, Any]] = []
    discarded: List[Dict[str, Any]] = []

    logger.info(
        "DATE FILTER — Checking %d articles against %d-day window (cutoff: %s)",
        len(articles), settings.DATE_WINDOW_DAYS, cutoff.isoformat(),
    )

    for article in articles:
        url = article.get("url", "unknown")
        raw_date = article.get("publish_date")

        pub_date = None
        if raw_date:
            try:
                if isinstance(raw_date, str):
                    pub_date = dateutil_parser.parse(raw_date)
                elif isinstance(raw_date, datetime):
                    pub_date = raw_date
            except (ValueError, OverflowError) as exc:
                logger.debug("DATE FILTER — Unparseable date for %s: %s", url[:60], exc)

        if pub_date:
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            if pub_date >= cutoff:
                valid.append(article)
            else:
                reason = f"Article older than {settings.DATE_WINDOW_DAYS} days (published {pub_date.date()})"
                discarded.append({"url": url, "reason": reason, "publish_date": pub_date.isoformat(),
                                  "timestamp": now.isoformat()})
                URLS_DISCARDED.labels(reason="expired").inc()
        else:
            reason = "No publish date found — discarded as potentially stale"
            discarded.append({"url": url, "reason": reason, "publish_date": None,
                              "timestamp": now.isoformat()})
            URLS_DISCARDED.labels(reason="no_date").inc()

    # Audit log
    if discarded:
        audit_key = f"mscout:audit:discarded:{company_name.lower().replace(' ', '_')}"
        for entry in discarded:
            append_audit_log(audit_key, entry)

    logger.info("DATE FILTER — %d passed, %d discarded", len(valid), len(discarded))

    return {"filtered_results": valid, "discarded_urls": discarded}
