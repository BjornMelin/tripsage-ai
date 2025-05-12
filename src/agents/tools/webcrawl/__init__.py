"""
Web crawling tools for TripSage.

This package provides agent tools for web crawling, search, and content extraction
using external MCP servers (Crawl4AI and Firecrawl).
"""

from .crawl4ai_client import get_client as get_crawl4ai_client  # noqa: F401
from .firecrawl_client import get_client as get_firecrawl_client  # noqa: F401
from .persistence import get_persistence_manager  # noqa: F401
from .result_normalizer import get_normalizer  # noqa: F401
from .source_selector import SourceType, get_source_selector  # noqa: F401
