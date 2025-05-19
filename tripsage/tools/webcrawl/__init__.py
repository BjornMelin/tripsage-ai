"""
Web crawling tools package for TripSage.

This package provides interfaces for web crawling, search, and content extraction
tools that interact with external web services via MCPs.
"""

from .crawl4ai_client import Crawl4AIClient
from .firecrawl_client import FirecrawlClient
from .persistence import WebcrawlPersistenceManager
from .result_normalizer import ResultNormalizer
from .source_selector import SourceSelector, SourceType

__all__ = [
    "Crawl4AIClient",
    "FirecrawlClient",
    "WebcrawlPersistenceManager",
    "ResultNormalizer",
    "SourceSelector",
    "SourceType",
]
