"""
Qdrant Cloud client for RAG knowledge-base and CAG semantic cache.

Handles:
- Connection to Qdrant Cloud (or local Qdrant)
- Collection creation with proper embedding dimensions
- Upserting document chunks with metadata
- Similarity search (cosine)
- Auto-ingest KB if collection is missing or empty

collections:
    ``cag_cache``  — CAG semantic cache (query → answer, TTL-filtered)
"""

import sys
import os

# Add the parent directory to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logger import setup_logger
from typing import Any,Dict,Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams
)

from config import (
    params,
    QDRANT_API_KEY,
    QDRANT_URL
)

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_qdrant_client: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:

    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    if not QDRANT_URL:
        raise RuntimeError(
            "QDRANT_URL is not set.  Add it to your .env file.\n"
            "Example: QDRANT_URL=https://xxxxx.us-east.aws.cloud.qdrant.io"
        )
    if not QDRANT_API_KEY:
        raise RuntimeError(
            "QDRANT_API_KEY is not set.  Add it to your .env file."
        )
    
    _qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30
    )
    logger.info("Qdrant client initialized")
    return _qdrant_client

# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

def ensure_collection(
    collection_name: str = params['cag']['collection_name'],
    embedding_dim: int = params['embedding']['embedding_dim'],
    distance: Distance = Distance.COSINE,
    on_disk: bool = False
) -> None:
    
    """
    Create the Qdrant collection if it does not exist.

    Safe to call repeatedly (idempotent).
    """

    client  = get_qdrant_client()

    existing = [c.name for c in client.get_collections().collections]

    if collection_name in existing:
        logger.info(f"Collection '{collection_name}' already exists.")
        return
    
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embedding_dim, distance=distance,on_disk=on_disk)
    )
    logger.info(f"Created collection '{collection_name}' with embedding dimension {embedding_dim}")


def delete_collection(collection_name: str = params['cag']['collection_name']) -> None:
    """
    Delete the Qdrant collection.
    """
    client = get_qdrant_client()
    client.delete_collection(collection_name=collection_name)
    logger.info(f"Deleted collection '{collection_name}'")


def collection_info(collection_name: str = params['cag']['collection_name']) -> Dict[str, Any]:
    """Return collection stats (point count, vector size, etc.)."""
    client = get_qdrant_client()
    info = client.get_collection(collection_name)
    return {
        "name": collection_name,
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "vector_size": info.config.params.vectors.size,  # type: ignore[union-attr]
        "distance": info.config.params.vectors.distance.name,  # type: ignore[union-attr]
        "status": info.status.name,
    }

def collection_exists(collection_name: str = params['cag']['collection_name']) -> bool:
    """Check whether *collection_name* exists in Qdrant."""
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    return collection_name in existing