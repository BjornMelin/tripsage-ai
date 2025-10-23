"""Web crawling tools package for TripSage.

This package provides interfaces for web crawling, search, and content extraction
tools that interact with external web services via MCPs.

Note: This module has been updated to support direct Crawl4AI SDK integration
      instead of MCP-based approach for performance improvements.
"""

# Import only the components that don't depend on legacy MCP clients
from .models import UnifiedCrawlResult
from .result_normalizer import ResultNormalizer
from .source_selector import WebCrawlSourceSelector


__all__ = [
    "ResultNormalizer",
    "UnifiedCrawlResult",
    "WebCrawlSourceSelector",
]
