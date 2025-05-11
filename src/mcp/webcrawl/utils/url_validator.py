"""URL validation and normalization utilities for WebCrawl MCP."""

import re
from typing import Optional
from urllib.parse import ParseResult, urlparse, urlunparse

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Regular expression for validating URLs
URL_REGEX = re.compile(
    r"^(?:http|https)://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# List of common URL parameters to remove for caching
CACHEABLE_PARAMS_TO_REMOVE = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
    "zanpid",
    "_ga",
]


def validate_url(url: str) -> bool:
    """Validate a URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is valid, False otherwise

    Raises:
        ValueError: If the URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Use regex to validate URL format
    if not URL_REGEX.match(url):
        raise ValueError(f"Invalid URL format: {url}")

    # Parse URL to validate components
    try:
        parsed = urlparse(url)

        # Check if scheme is http or https
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"URL must use http or https scheme: {url}")

        # Check if netloc is not empty
        if not parsed.netloc:
            raise ValueError(f"URL must have a valid domain: {url}")

    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        raise ValueError(f"Invalid URL: {url}")

    return True


def normalize_url(
    url: str, remove_tracking: bool = True, remove_fragments: bool = True
) -> str:
    """Normalize a URL for consistent processing.

    Args:
        url: The URL to normalize
        remove_tracking: Whether to remove tracking parameters
        remove_fragments: Whether to remove URL fragments

    Returns:
        Normalized URL
    """
    try:
        # Parse URL
        parsed = urlparse(url)

        # Ensure scheme is https if http
        scheme = "https" if parsed.scheme == "http" else parsed.scheme

        # Convert domain to lowercase
        netloc = parsed.netloc.lower()

        # Remove 'www.' prefix from domain if present
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Process query parameters if needed
        query = parsed.query
        if remove_tracking and query:
            # Parse query parameters
            params = query.split("&")
            filtered_params = []

            for param in params:
                if "=" not in param:
                    continue

                key, value = param.split("=", 1)
                if key.lower() not in CACHEABLE_PARAMS_TO_REMOVE:
                    filtered_params.append(param)

            query = "&".join(filtered_params)

        # Remove fragment if needed
        fragment = "" if remove_fragments else parsed.fragment

        # Rebuild URL
        normalized = urlunparse(
            ParseResult(
                scheme=scheme,
                netloc=netloc,
                path=parsed.path,
                params=parsed.params,
                query=query,
                fragment=fragment,
            )
        )

        return normalized
    except Exception as e:
        logger.error(f"URL normalization error: {str(e)}")
        # Return original URL if normalization fails
        return url


def extract_domain(url: str) -> str:
    """Extract domain from a URL.

    Args:
        url: The URL to extract domain from

    Returns:
        Domain name without scheme, path, etc.
    """
    try:
        # Parse URL
        parsed = urlparse(url)

        # Extract domain
        domain = parsed.netloc.lower()

        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        return domain
    except Exception as e:
        logger.error(f"Domain extraction error: {str(e)}")
        # Return original URL if extraction fails
        return url


def get_cache_key(url: str) -> str:
    """Generate a cache key for a URL.

    Args:
        url: The URL to generate a cache key for

    Returns:
        Cache key
    """
    # Normalize URL for consistent cache keys
    normalized = normalize_url(url)

    # Use a deterministic hash function
    return f"url:{normalized}"


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain.

    Args:
        url1: First URL
        url2: Second URL

    Returns:
        True if the URLs belong to the same domain, False otherwise
    """
    domain1 = extract_domain(url1)
    domain2 = extract_domain(url2)

    return domain1 == domain2
