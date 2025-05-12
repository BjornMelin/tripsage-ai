"""
Web crawling tools for TripSage.

This package provides agent tools for web crawling, search, and content extraction
using external MCP servers (Crawl4AI and Firecrawl).
"""

from .crawl4ai_client import get_client as get_crawl4ai_client
from .firecrawl_client import get_client as get_firecrawl_client
from .persistence import get_persistence_manager
from .result_normalizer import get_normalizer
from .source_selector import get_source_selector, SourceType