"""Response formatting utilities for WebCrawl MCP."""

import datetime
from typing import Any, Dict, Optional

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


def format_response(data: Any) -> Dict[str, Any]:
    """Format a response for the MCP client.

    Args:
        data: Data to format

    Returns:
        Formatted response
    """
    # Add metadata to response
    response = {
        "data": data,
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "success",
        },
    }

    return response


def format_error(
    message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format an error response.

    Args:
        message: Error message
        code: Optional error code
        details: Optional error details

    Returns:
        Formatted error response
    """
    return {
        "error": {
            "message": message,
            "code": code or "UNKNOWN_ERROR",
            "details": details or {},
        },
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "error",
        },
    }


def format_html_to_markdown(html: str) -> str:
    """Convert HTML to markdown.

    Args:
        html: HTML content

    Returns:
        Markdown content
    """
    try:
        # Check if html-to-markdown is available
        from markdownify import markdownify

        # Convert HTML to markdown
        markdown = markdownify(html)

        return markdown
    except ImportError:
        logger.warning("markdownify not available, unable to convert HTML to markdown")

        # Basic fallback conversion
        import re

        # Replace headers
        markdown = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", html)
        markdown = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", markdown)
        markdown = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", markdown)

        # Replace paragraphs
        markdown = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", markdown)

        # Replace links
        markdown = re.sub(
            r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", markdown
        )

        # Replace bold and italic
        markdown = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", markdown)
        markdown = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", markdown)
        markdown = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", markdown)
        markdown = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", markdown)

        # Replace lists
        markdown = re.sub(r"<ul[^>]*>(.*?)</ul>", r"\1", markdown)
        markdown = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", markdown)

        # Remove remaining HTML tags
        markdown = re.sub(r"<[^>]*>", "", markdown)

        # Clean up extra spaces and newlines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown


def normalize_text(text: str) -> str:
    """Normalize text for consistent formatting.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Replace multiple spaces with a single space
    text = " ".join(text.split())

    # Replace multiple newlines with a single newline
    import re

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def summarize_text(text: str, max_words: int = 100) -> str:
    """Summarize text to a maximum number of words.

    Args:
        text: Text to summarize
        max_words: Maximum number of words

    Returns:
        Summarized text
    """
    words = text.split()

    if len(words) <= max_words:
        return text

    # Extract the first max_words words
    summary = " ".join(words[:max_words])

    # Add ellipsis to indicate truncation
    summary += " ..."

    return summary


def clean_text_for_display(text: str, max_length: int = 5000) -> str:
    """Clean text for display in logs and responses.

    Args:
        text: Text to clean
        max_length: Maximum length of the text

    Returns:
        Cleaned text
    """
    # Normalize text
    cleaned = normalize_text(text)

    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + " ..."

    return cleaned
