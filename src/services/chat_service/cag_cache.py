"""
Cache-Augmented Generation (CAG) — semantic vector cache backed by Qdrant.

Architecture:
    Uses a dedicated Qdrant collection (``cag_cache``)

How it works:
    1. Every cached entry is a Qdrant point containing:
       - **vector**         : embedded query (float32)
       - **payload.query**  : original question (text)
       - **payload.answer** : generated response (text)
       - **payload.evidence_urls** : JSON-encoded source list
       - **payload.ts**     : unix timestamp (for TTL filtering)
    2. ``get(query)`` embeds the query, runs KNN-1 search;
       if cosine similarity ≥ threshold → cache **HIT**.
    3. ``set(query, response)`` embeds the query, upserts point so
       future *semantically similar* queries hit the cache.

Why Qdrant over Redis Stack:
    - Standard Redis Cloud (free tier) does NOT include the RediSearch
      module required for FT.CREATE / FT.SEARCH vector search.
    - Qdrant Cloud is already provisioned for RAG — adding a second
      collection is zero-cost and requires no extra infrastructure.
    - Same sub-millisecond HNSW vector search, same cosine metric.

Why semantic > hash-based (MD5):
    - "What is the leave policy?"  →  "How many leave days do staff get?"
      Same meaning, different words.  MD5 would MISS both;
      semantic search catches the paraphrase with ~0.95 cosine similarity.

Dependencies:
    - Qdrant Cloud (already configured for RAG)
    - An embedder with ``embed_query(text) → List[float]``
"""
# Add the parent directory to sys.path to allow importing from src

import os,sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import time
import uuid
from typing import Any,Dict,Optional

from logger import setup_logger
from config import params
try:
    from infrastructure.db.qdrant_manager import (
        get_qdrant_client,
        collection_exists,
        ensure_collection
    )
except ImportError:
    # Fallback or error handling if qdrant_manager is not available
    # For now, we'll just re-raise or log a warning if it's critical
    raise
from qdrant_client.http.models import PointStruct

logger = setup_logger(__name__)

# ── Defaults ─────────────────────────────────────────────────

_DEFAULT_COLLECTION = "cag_cache"

class CAGCache:
    """
    Qdrant-backed semantic cache for pre-computed RAG responses.

    Each point stores:
        vector   → query embedding (float32)
        payload  → query, answer, evidence_urls, ts

    Lookup is a KNN-1 search; a hit is declared when
    ``cosine_similarity ≥ similarity_threshold``.

    Usage::

        cache = CAGCache(embedder=embedder)

        # Semantic lookup
        cached = cache.get("How many leave days?")
        if cached:
            return cached["answer"]

        # Store new entry (semantically indexed)
        cache.set("What is the leave policy?", {"answer": "...", "evidence_urls": [...]})
    """

    def __init__(
        self,
        embedder: Any,
        collection_name: Optional[str] = None,
        dim: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:

        """
        Initialise the semantic CAG cache.

        Args:
            embedder: Object with ``embed_query(text) -> List[float]``.
            collection_name: Qdrant collection for CAG (default: ``cag_cache``).
            dim: Embedding dimension (auto-detected from config if None).
            similarity_threshold: Min cosine similarity for a hit (0.90–0.95).
            ttl_seconds: Entries older than this are ignored; 0 → no expiry.
        """

        self.embedder = embedder
        self.collection_name = collection_name or _DEFAULT_COLLECTION
        self.dim = dim or params['embedding']['embedding_dim']
        self.similarity_threshold = similarity_threshold or params['cag']['similarity_threshold']
        self.ttl_seconds = ttl_seconds or params['cag']['cache_ttl']
        
        self._available = False

        self._client = get_qdrant_client()
        try:
            if not collection_exists(self.collection_name):
                ensure_collection(self.collection_name)
            self._available = True
            logger.info(
                "CAG cache ready (Qdrant collection='%s', dim=%d, threshold=%.2f)",
                self.collection_name,
                self.dim,
                self.similarity_threshold,
            )
        except Exception as exc:
            logger.warning(
                "CAG cache DISABLED — Qdrant unavailable: %s. "
                "All lookups will miss; every query runs full RAG.",
                exc,
            )


    # ── public API ────────────────────────────────────────────

    def get(self,query: str) -> Optional[Dict[str,Any]]:
        """
        Semantic cache lookup via KNN-1 search.

        Embeds *query*, searches the Qdrant HNSW index, and returns
        the cached response if ``cosine_similarity ≥ threshold``.

        Args:
            query: Natural-language question.

        Returns:
            Dict with ``query``, ``verdict``, ``confidence_score``, ``explanation``, ``top_sources``, ``ts``,
            ``score`` — or ``None`` on miss.
        """
        if not self._available:
            return None
        
        try:
            vec = self.embedder.embed_query(query)
        except Exception as exc:
            logger.error("CAG cache: embedder failed: %s", exc)
            return None
        
        try:
            result = self._client.query_points(
                collection_name=self.collection_name,
                query=vec,
                limit=1,
                with_payload=True,
            )
            points = result.points
        except Exception as exc:
            # If collection is missing at runtime, disable cache and log error
            if "404" in str(exc) or "Not found" in str(exc):
                logger.warning("CAG cache collection '%s' missing at runtime. Attempting to recreate...", self.collection_name)
                try:
                    ensure_collection(self.collection_name)
                except Exception:
                    self._available = False
            
            logger.error("CAG cache: search failed: %s", exc)
            return None
        
        if not points:
            return None
        
        point = points[0]
        payload = point.payload
        score = point.score
        
        if score < self.similarity_threshold:
            return None
        
        # TTL check
        if self.ttl_seconds > 0 and time.time() - payload["ts"] > self.ttl_seconds:
            return None
        
        logger.info("CAG cache HIT for query: %s", query)

        return {
            "query": payload["query"],
            "verdict":payload["verdict"],
            "confidence_score":payload["confidence_score"],
            "explanation":payload["explanation"],
            "top_sources":payload["top_sources"],
            "ts": payload["ts"],
            "score": score,
        }
    
    def set(self,query: str, response: Dict[str,Any]) -> None:
        """
        Cache a response, indexed by the query's embedding.

        Args:
            query: Original user query.
            response: Dict with ``verdict``, ``confidence_score``, ``explanation``, ``top_sources``. ``ts``
        """
        if not self._available:
            return

        # Embed query
        try:
            query_vec = self.embedder.embed_query(query)
        except Exception as exc:
            logger.warning("CAG embed failed on SET: %s", exc)
            return
        
        point_id = str(uuid.uuid4())
        payload = {
            "query": query,
            "verdict":response["verdict"],
            "confidence_score":response["confidence_score"],
            "explanation":response["explanation"],
            "top_sources":response["top_sources"],
            "ts": time.time(),
        }

        try:
            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=query_vec,
                        payload=payload,
                    )
                ],
            )
            logger.info("CAG cache SET for query: %s", query)
        except Exception as exc:
            if "404" in str(exc) or "Not found" in str(exc):
                 try:
                    ensure_collection(self.collection_name)
                 except Exception:
                    pass
            logger.error("CAG cache: upsert failed: %s", exc)
    
    def clear(self) -> None:
        """
        Drop and recreate the CAG cache collection.

        All cached entries are removed. The collection is recreated
        immediately so the cache is ready for new entries.
        """
        if not self._available:
            return

        try:
            self._client.delete_collection(self.collection_name)
            logger.info("Dropped CAG cache collection '%s'", self.collection_name)
        except Exception:
            pass  # Collection may not exist

        ensure_collection()
        logger.info("CAG cache cleared and collection recreated")

