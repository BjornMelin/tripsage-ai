#!/usr/bin/env python3
"""
Example script demonstrating the usage of the Crawl4AI MCP client.

This script shows how to initialize the client, crawl URLs, extract content,
and ask questions about the crawled content.
"""

import asyncio
import logging

from tripsage.clients.webcrawl.crawl4ai_mcp_client import (
    Crawl4AICrawlParams,
    get_crawl4ai_client,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_basic_crawl():
    """Test basic URL crawling with markdown extraction."""
    logger.info("Testing basic URL crawling...")

    client = get_crawl4ai_client()
    url = "https://example.com"

    try:
        # Crawl URL with markdown extraction
        result = await client.extract_markdown(url)
        logger.info(f"Crawled {url}")
        logger.info(f"Content length: {len(result.get('content', ''))}")
        return result
    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        return None


async def test_multi_format_crawl():
    """Test crawling with multiple output formats."""
    logger.info("Testing multi-format crawling...")

    client = get_crawl4ai_client()
    url = "https://example.com"

    params = Crawl4AICrawlParams(
        url=url,
        markdown=True,
        html=True,
        screenshot=True,
    )

    try:
        result = await client.crawl_url(url, params)
        logger.info(f"Multi-format crawl completed for {url}")

        # Check what formats were returned
        formats = []
        if "markdown" in result:
            formats.append("markdown")
        if "html" in result:
            formats.append("html")
        if "screenshot" in result:
            formats.append("screenshot")

        logger.info(f"Formats returned: {', '.join(formats)}")
        return result
    except Exception as e:
        logger.error(f"Error in multi-format crawl: {e}")
        return None


async def test_javascript_execution():
    """Test JavaScript execution on a page."""
    logger.info("Testing JavaScript execution...")

    client = get_crawl4ai_client()
    url = "https://example.com"

    # Simple JavaScript to get page title
    js_code = """
    return {
        title: document.title,
        url: window.location.href,
        timestamp: new Date().toISOString()
    };
    """

    try:
        result = await client.execute_js(url, js_code)
        logger.info(f"JavaScript executed on {url}")
        logger.info(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error executing JavaScript: {e}")
        return None


async def test_question_answering():
    """Test question answering about crawled content."""
    logger.info("Testing question answering...")

    client = get_crawl4ai_client()
    urls = [
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/JavaScript",
    ]

    question = "What are the main differences between Python and JavaScript?"

    try:
        result = await client.ask(urls, question)
        logger.info(f"Asked question: {question}")
        logger.info(f"Answer: {result.get('answer', 'No answer provided')}")
        return result
    except Exception as e:
        logger.error(f"Error in question answering: {e}")
        return None


async def test_batch_crawl():
    """Test batch crawling of multiple URLs."""
    logger.info("Testing batch crawling...")

    client = get_crawl4ai_client()
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
    ]

    try:
        results = await client.batch_crawl(urls, markdown=True, html=False)
        logger.info(f"Batch crawled {len(results)} URLs")

        for i, result in enumerate(results):
            if "error" in result:
                logger.error(f"Error for {urls[i]}: {result['error']}")
            else:
                logger.info(f"Successfully crawled {urls[i]}")

        return results
    except Exception as e:
        logger.error(f"Error in batch crawling: {e}")
        return None


async def main():
    """Run all test functions."""
    logger.info("Starting Crawl4AI MCP client tests...")

    tests = [
        ("Basic Crawl", test_basic_crawl),
        ("Multi-Format Crawl", test_multi_format_crawl),
        ("JavaScript Execution", test_javascript_execution),
        ("Question Answering", test_question_answering),
        ("Batch Crawl", test_batch_crawl),
    ]

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            await test_func()
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")

    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
