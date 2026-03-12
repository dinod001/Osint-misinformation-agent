"""
CAG (Cache-Augmented Generation) service combining caching with CRAG.

Pipeline:
    Query --> Semantic Cache (Qdrant cag_cache KNN-1)
          --> HIT? Return instantly (0ms, $0)
          --> MISS? --> Tavili and llm caller
                    --> Cache the result for future hits
                    --> Return answer
"""

import os,sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Any, Dict, Optional

from logger import setup_logger
from config import params
from services.chat_service.cag_cache import CAGCache
from agents.tools.web_search_tool import WebSearchTool
from infrastructure.llm.llm_provider import generator
from infrastructure.llm.embeddings import Embeddings

logger = setup_logger(__name__)

class CAGService:
    """
    Cache-Augmented Generation backed by Corrective RAG.

    Layer 1: Semantic cache (Qdrant cag_cache) -- instant, $0
    Layer 2: Tavily API caller and llm caller
    """

    def __init__(
        self,
        cache: CAGCache = None,
        embedder: Embeddings = None,
        web_search: WebSearchTool = None,
        generator=generator
    ):

        self.embedder = embedder or Embeddings()

        self.cache = cache or CAGCache(self.embedder)

        self.web_search = web_search or WebSearchTool()

        self.generator = generator
    
    def generate(self,query: str, use_cache: bool = True) -> Dict[str,Any]:
        """
        Generate a response using CAG.

        Args:
            query: The query to generate a response for.
            use_cache: Whether to use the cache.

        Returns:
            A dictionary containing the generated response.
        """
        start = time.time()

        if use_cache:
            cached = self.cache.get(query)
            if cached:
                latency_ms = int((time.time() - start) * 1000)
                logger.info("CAG cache hit for query: %s in %dms", query, latency_ms)
                return cached
        
        # cache miss -- run Tavily and llm , later set to cashe

        tool  = self.web_search
        answer = tool.search(query)

        if answer:
            llm_answer = self.generator.invoke(query, answer)
            self.cache.set(query, llm_answer)
            latency_ms = int((time.time() - start) * 1000)
            logger.info("CAG cache miss for query: %s in %dms", query, latency_ms)
            return llm_answer

        
        