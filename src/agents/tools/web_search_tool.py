"""
Web Search Tool — Tavily-powered real-time web search.

Used when the agent needs external, up-to-date information that
is not available in the internal knowledge base (Qdrant).
Typical triggers: hospital hours, live status, news, directions.
"""

import os,sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logger import setup_logger
logger = setup_logger(__name__)

from config import params
from tavily import TavilyClient
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from config import (
    TIMEZONE,
    params,
    TAVILY_API_KEY
)

class WebSearchTool:
    """
    Tavily-powered web search tool.

    Returns formatted text suitable for injection into a synthesiser prompt.
    """

    def __init__(
        self,
        api_key: str = TAVILY_API_KEY,
        max_results: int = 5,
        search_depth: str = "basic",
        trusted_sites: List[str] = ["reuters.com", "apnews.com", "bbc.com", "aljazeera.com"]
    ):

        self.client = TavilyClient(api_key=api_key)
        self.max_results = max_results
        self.search_depth = search_depth
        self.trusted_sites = trusted_sites
        self.timezone = ZoneInfo(TIMEZONE)

    # ── core search ───────────────────────────────────────────

    def search(self,query: str) -> str:
        """
        Run a web search and return a formatted text summary.

        Traced via LangFuse so Tavily latency is visible in the dashboard.
        """
        try:
            start = time.perf_counter()
            response = self.client.search(
                query=query,
                max_results=self.max_results,
                search_depth=self.search_depth,
                trusted_sites=self.trusted_sites,
                include_answer=True,
                include_raw_content=False
            )
            if not response:
                return "No web results found for your query."
            latency_ms = int((time.perf_counter() - start) * 1000)

            results = response.get("results", [])
            logger.info("Tavily search: %s results in %.2f seconds", len(results), latency_ms)
            
            
            # ── rank & format ─────────────────────────────────────
            lines: List[str] = []

            answer = response.get("answer")
            if answer:
                lines.append(f"Summary: {answer}\n")

            lines.append("Web sources:")
            for idx, item in enumerate(results[: self.max_results], 1):
                title = item.get("title", "")
                content = item.get("content", "")
                url = item.get("url", "")
                snippet = content[:300] + "…" if len(content) > 300 else content
                lines.append(f"  {idx}. {title}\n     {snippet}\n     URL: {url}")

            checked_at = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M %Z")
            lines.append(f"\n(checked at {checked_at}, {latency_ms}ms)")

            return "\n".join(lines)

        except Exception as exc:
            logger.error("Tavily search failed: %s", exc)
            return "Something went wrong while searching the web."
