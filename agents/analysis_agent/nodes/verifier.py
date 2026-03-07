"""
Analysis Agent — Verifier Tool

SBERT semantic clustering for cross-source verification.
Uses HuggingFace InferenceClient for embeddings.
"""

import logging
import time
from typing import Dict, Any, List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)

_hf_client = None


def _get_hf_client():
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient
        token = settings.HF_API_TOKEN if settings.HF_API_TOKEN else None
        _hf_client = InferenceClient(token=token)
        logger.info("VERIFIER — HF InferenceClient initialised")
    return _hf_client


def _get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            client = _get_hf_client()
            result = client.feature_extraction(
                text=texts,
                model=f"sentence-transformers/{settings.SBERT_MODEL}",
            )
            if hasattr(result, 'tolist'):
                return result.tolist()

            processed = []
            for emb in result:
                if isinstance(emb, (list, np.ndarray)):
                    arr = np.array(emb)
                    if arr.ndim == 2:
                        processed.append(np.mean(arr, axis=0).tolist())
                    else:
                        processed.append(arr.tolist() if hasattr(arr, 'tolist') else list(arr))
                else:
                    processed.append(emb)
            return processed
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning("VERIFIER — HF API attempt %d/%d failed: %s", attempt, settings.MAX_RETRIES, exc)
            if attempt < settings.MAX_RETRIES:
                time.sleep(wait)

    logger.warning("VERIFIER — HF API failed, falling back to local SBERT")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.SBERT_MODEL)
        return model.encode(texts).tolist()
    except Exception as exc:
        logger.error("VERIFIER — Local fallback also failed: %s", exc)
        return []


def _get_embeddings_cached(texts: List[str]) -> List[np.ndarray]:
    embeddings = [None] * len(texts)
    uncached_indices = []
    uncached_texts = []

    for i, text in enumerate(texts):
        cache_key = make_cache_key("embedding", text)
        cached = get_cache(cache_key)
        if cached is not None:
            embeddings[i] = np.array(cached)
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    if uncached_texts:
        logger.info("VERIFIER — Fetching %d embeddings from HF API", len(uncached_texts))
        batch_results = _get_embeddings_batch(uncached_texts)
        for idx, emb in zip(uncached_indices, batch_results):
            embeddings[idx] = np.array(emb)
            cache_key = make_cache_key("embedding", texts[idx])
            set_cache(cache_key, emb, expire=86400)
    else:
        logger.info("VERIFIER — All %d embeddings served from cache", len(texts))

    return embeddings


def verifier_tool(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cross-source verification using SBERT semantic clustering."""
    logger.info("VERIFIER — Processing %d extracted features", len(features))

    if not features:
        return {"verified_features": []}

    summaries = [f.get("feature_summary", "") for f in features]
    embeddings = _get_embeddings_cached(summaries)

    if not embeddings or any(e is None for e in embeddings):
        logger.warning("VERIFIER — Embedding generation failed, passing features through")
        return {"verified_features": [
            {**f, "source_count": 1, "primary_url": f.get("url", ""), "all_sources": [f.get("url", "")]}
            for f in features
        ]}

    embeddings_array = np.array(embeddings)

    verified: List[Dict[str, Any]] = []
    clustered: set = set()

    for i in range(len(features)):
        if i in clustered:
            continue

        cluster = [features[i]]
        clustered.add(i)

        for j in range(i + 1, len(features)):
            if j in clustered:
                continue
            sim = cosine_similarity(
                embeddings_array[i].reshape(1, -1),
                embeddings_array[j].reshape(1, -1),
            )[0][0]
            if sim >= settings.SIMILARITY_THRESHOLD:
                cluster.append(features[j])
                clustered.add(j)

        best = max(cluster, key=lambda x: x.get("source_authority", 0))
        all_urls = list({f.get("url", "") for f in cluster if f.get("url")})
        all_metrics = list({m for f in cluster for m in f.get("metrics", []) if m})
        all_evidence = [f.get("evidence", "") for f in cluster if f.get("evidence")]

        verified.append({
            "feature_summary": best.get("feature_summary", ""),
            "category": best.get("category", ""),
            "metrics": all_metrics,
            "confidence": best.get("confidence", 0.0),
            "evidence": all_evidence[:3],
            "source_count": len(all_urls),
            "primary_url": best.get("url", ""),
            "all_sources": all_urls,
            "publish_date": best.get("publish_date"),
            "source_authority": best.get("source_authority", 0.5),
        })

    logger.info("VERIFIER — Consolidated %d → %d verified features", len(features), len(verified))
    return {"verified_features": verified}
