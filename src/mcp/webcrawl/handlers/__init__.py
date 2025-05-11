# WebCrawl MCP handlers module

from src.mcp.webcrawl.handlers.blog_handler import crawl_travel_blog
from src.mcp.webcrawl.handlers.events_handler import get_latest_events
from src.mcp.webcrawl.handlers.extract_handler import extract_page_content
from src.mcp.webcrawl.handlers.monitor_handler import monitor_price_changes
from src.mcp.webcrawl.handlers.search_handler import search_destination_info

__all__ = [
    "extract_page_content",
    "search_destination_info",
    "monitor_price_changes",
    "get_latest_events",
    "crawl_travel_blog",
]
