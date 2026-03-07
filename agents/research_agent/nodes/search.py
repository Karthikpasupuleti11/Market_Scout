"""
Research Agent — Search Tool (PARALLEL)

Executes Tavily search queries in parallel using ThreadPoolExecutor.
Scores results by domain authority. Deduplicates URLs.
"""

import time
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from tavily import TavilyClient

from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)

MAX_SEARCH_THREADS = 4

# ── Domain Authority Map ───────────────────────────────────────────

DOMAIN_AUTHORITY: Dict[str, float] = {
    "docs.": 1.0, "developer.": 1.0, "blog.": 0.95, "engineering.": 0.95,
    "github.com": 0.90, "arxiv.org": 0.90, "huggingface.co": 0.85,
    "techcrunch.com": 0.80, "theverge.com": 0.75, "venturebeat.com": 0.75,
    "arstechnica.com": 0.75, "thenewstack.io": 0.75, "infoq.com": 0.75,
    "zdnet.com": 0.70, "wired.com": 0.70,
    "producthunt.com": 0.60, "medium.com": 0.40, "reddit.com": 0.35,
}

_tavily: TavilyClient = None


def _get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        if not settings.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not configured.")
        _tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
    return _tavily


def _score_domain(url: str) -> float:
    url_lower = url.lower()
    for domain, weight in DOMAIN_AUTHORITY.items():
        if domain in url_lower:
            return weight
    return 0.50


def _is_domain_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        for allowed in settings.ALLOWED_DOMAINS:
            if hostname.endswith(allowed):
                return True
        for prefix in settings.ALLOWED_DOMAIN_PREFIXES:
            if hostname.startswith(prefix) or prefix in hostname:
                return True
        return False
    except Exception:
        return False


def _execute_single_query(query: str) -> List[Dict[str, Any]]:
    """Execute a single Tavily search with retry logic."""
    client = _get_tavily()
    last_error = None
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            response = client.search(
                query=query,
                search_depth=settings.SEARCH_DEPTH,
                max_results=settings.SEARCH_MAX_RESULTS,
            )
            return response.get("results", [])
        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(
                "SEARCH — Query '%s' attempt %d/%d failed: %s — retrying in %ds",
                query[:50], attempt, settings.MAX_RETRIES, exc, wait,
            )
            if attempt < settings.MAX_RETRIES:
                time.sleep(wait)

    logger.error("SEARCH — Query '%s' failed after %d attempts: %s",
                 query[:50], settings.MAX_RETRIES, last_error)
    return []


def _search_single_query(query: str) -> List[Dict[str, Any]]:
    """Search one query with caching."""
    cache_key = make_cache_key("search_results", query)
    cached = get_cache(cache_key)
    if cached:
        logger.debug("SEARCH — Cache hit for query: '%s'", query[:50])
        return cached

    raw_results = _execute_single_query(query)
    cacheable = [
        {"url": r.get("url", ""), "title": r.get("title", ""), "content": r.get("content", "")}
        for r in raw_results
    ]
    set_cache(cache_key, cacheable)
    return raw_results


def search_tool(queries: List[str], company_name: str) -> Dict[str, Any]:
    """Execute search queries in PARALLEL and return scored, deduplicated results."""
    logger.info("SEARCH — Processing %d queries in parallel for '%s'", len(queries), company_name)

    if not queries:
        return {"search_results": [], "error": "No search queries were generated."}

    # ── Parallel search ────────────────────────────────────────────
    all_raw_results: List[List[Dict]] = []
    with ThreadPoolExecutor(max_workers=MAX_SEARCH_THREADS) as executor:
        futures = {executor.submit(_search_single_query, q): q for q in queries}
        for future in as_completed(futures):
            try:
                results = future.result()
                all_raw_results.append(results)
            except Exception as exc:
                logger.warning("SEARCH — Parallel query failed: %s", exc)

    # ── Deduplicate + score ────────────────────────────────────────
    all_results: List[Dict[str, Any]] = []
    seen_urls: set = set()

    for raw_results in all_raw_results:
        for item in raw_results:
            url = item.get("url", "").strip()
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            authority = _score_domain(url)
            domain_allowed = _is_domain_allowed(url)
            if not domain_allowed:
                authority *= 0.8

            all_results.append({
                "url": url,
                "title": item.get("title", ""),
                "authority_score": round(authority, 2),
                "snippet": item.get("content", ""),
                "domain_allowed": domain_allowed,
            })

    sorted_results = sorted(all_results, key=lambda x: x["authority_score"], reverse=True)
    logger.info("SEARCH — Returning %d results (parallel, deduplicated)", len(sorted_results))

    return {"search_results": sorted_results}
