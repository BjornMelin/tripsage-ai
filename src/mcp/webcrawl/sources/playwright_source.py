"""Implementation of the Playwright source for web crawling."""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.source_interface import (
    BlogInsights,
    CrawlSource,
    DestinationInfo,
    EventList,
    ExtractedContent,
    ExtractionOptions,
    MonitorOptions,
    PriceMonitorResult,
    TopicResult,
)
from src.utils.logging import get_logger

from ..sources.base import BlogSource

# Initialize logger
logger = get_logger(__name__)

# Import function for calling MCP tools
try:
    from src.utils.mcp import call_mcp_tool
except ImportError:
    # Define a mock function if the real one is not available
    logger.warning("Failed to import call_mcp_tool, using mock implementation")

    async def call_mcp_tool(
        tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock implementation of call_mcp_tool."""
        logger.error(f"Called mock call_mcp_tool with {tool_name} and {parameters}")
        raise NotImplementedError("call_mcp_tool is not available")


class PlaywrightSource(CrawlSource):
    """Implementation of the Playwright source for web crawling.

    This source uses the existing Playwright MCP tools for browser automation.
    It's primarily used for content that requires JavaScript rendering or interaction.
    """

    def __init__(
        self,
        mcp_endpoint: Optional[str] = None,
        browser_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Playwright source.

        Args:
            mcp_endpoint: Optional MCP endpoint,
                defaults to Config.PLAYWRIGHT_MCP_ENDPOINT
            browser_config: Optional browser configuration
        """
        self.mcp_endpoint = mcp_endpoint or Config.PLAYWRIGHT_MCP_ENDPOINT
        self.browser_config = browser_config or Config.PLAYWRIGHT_CONFIG

    async def extract_page_content(
        self, url: str, options: Optional[ExtractionOptions] = None
    ) -> ExtractedContent:
        """Extract content from a webpage using Playwright.

        Args:
            url: The URL of the webpage to extract content from
            options: Optional extraction options

        Returns:
            The extracted content

        Raises:
            Exception: If the extraction fails
        """
        options = options or {}

        try:
            # Navigate to the URL
            await call_mcp_tool(
                "mcp__playwright__playwright_navigate",
                {
                    "url": url,
                    "browserType": self.browser_config.get("browser", "chromium"),
                    "headless": self.browser_config.get("headless", True),
                    "width": self.browser_config.get("viewport", {}).get("width", 1280),
                    "height": self.browser_config.get("viewport", {}).get(
                        "height", 720
                    ),
                    "timeout": options.get("timeout", Config.REQUEST_TIMEOUT * 1000),
                    "waitUntil": "networkidle",
                },
            )

            # Wait for additional time if specified
            if options.get("wait", 0) > 0:
                await call_mcp_tool(
                    "mcp__playwright__playwright_wait",
                    {"time": options.get("wait", 0) / 1000},  # Convert ms to seconds
                )

            # Extract page title
            title_script = "document.title"
            title_result = await call_mcp_tool(
                "mcp__playwright__playwright_evaluate", {"script": title_script}
            )

            # Extract content based on selectors
            content = ""
            if options.get("selectors") and len(options.get("selectors", [])) > 0:
                # Extract content from specific selectors
                for selector in options.get("selectors", []):
                    try:
                        # Check if selector exists
                        check_script = f"!!document.querySelector('{selector}')"
                        exists = await call_mcp_tool(
                            "mcp__playwright__playwright_evaluate",
                            {"script": check_script},
                        )

                        if exists:
                            # Extract content from selector
                            extract_script = (
                                f"document.querySelector('{selector}').textContent"
                            )
                            selector_content = await call_mcp_tool(
                                "mcp__playwright__playwright_evaluate",
                                {"script": extract_script},
                            )

                            content += (
                                f"## Content from {selector}\n\n{selector_content}\n\n"
                            )
                    except Exception as selector_error:
                        logger.warning(
                            f"Error extracting content from selector {selector}: "
                            f"{str(selector_error)}"
                        )
            else:
                # Extract all visible text if no selectors specified
                content = await call_mcp_tool(
                    "mcp__playwright__playwright_get_visible_text", {}
                )

            # Get images if requested
            images = None
            if options.get("include_images", False):
                try:
                    # Take screenshot
                    screenshot = await call_mcp_tool(
                        "mcp__playwright__playwright_screenshot",
                        {
                            "name": f"screenshot_{url.replace('://', '_')}"
                            f"{url.replace('/', '_')}",
                            "fullPage": True,
                            "storeBase64": True,
                        },
                    )

                    if "base64" in screenshot:
                        images = [screenshot["base64"]]

                    # Extract image URLs
                    image_urls_script = """
                    Array.from(document.querySelectorAll('img'))
                        .filter(img => img.width > 100 && img.height > 100)
                        .map(img => img.src)
                    """

                    img_urls = await call_mcp_tool(
                        "mcp__playwright__playwright_evaluate",
                        {"script": image_urls_script},
                    )

                    if img_urls and isinstance(img_urls, list):
                        if not images:
                            images = []
                        images.extend(img_urls)
                except Exception as img_error:
                    logger.warning(f"Error extracting images: {str(img_error)}")

            # Extract metadata
            metadata = {}
            try:
                metadata_script = """
                {
                    author: document.querySelector('meta[name="author"]')?.content || 
                            document.querySelector('meta[property="article:author"]')?.content,
                    publishDate: document.querySelector('meta[name="published_time"]')
                               ?.content || 
                               document.querySelector('meta[property="article:published_time"]')
                               ?.content,
                    lastModified: document.querySelector('meta[name="modified_time"]')
                                ?.content || 
                                document.querySelector('meta[property="article:modified_time"]')
                                ?.content,
                    siteName: document.querySelector('meta[property="og:site_name"]')
                            ?.content
                }
                """
                meta_result = await call_mcp_tool(
                    "mcp__playwright__playwright_evaluate", {"script": metadata_script}
                )

                if meta_result:
                    metadata = meta_result
            except Exception as meta_error:
                logger.warning(f"Error extracting metadata: {str(meta_error)}")

            # Close the browser
            await call_mcp_tool("mcp__playwright__playwright_close", {})

            # Convert content format if needed
            if options.get("format", "markdown") == "text":
                # Already in text format
                pass
            elif options.get("format", "markdown") == "html":
                # Get HTML content
                content = await call_mcp_tool(
                    "mcp__playwright__playwright_get_visible_html", {}
                )

            return {
                "url": url,
                "title": title_result or "Unknown Title",
                "content": content,
                "images": images,
                "metadata": metadata,
                "format": options.get("format", "markdown"),
            }
        except Exception as e:
            logger.error(
                f"Error extracting content from {url} with Playwright: {str(e)}"
            )
            raise Exception(
                f"Failed to extract page content with Playwright: {str(e)}"
            ) from e
        finally:
            # Ensure the browser is closed
            try:
                await call_mcp_tool("mcp__playwright__playwright_close", {})
            except Exception:
                pass

    async def search_destination_info(
        self, destination: str, topics: Optional[List[str]] = None, max_results: int = 5
    ) -> DestinationInfo:
        """Search for information about a travel destination using Playwright.

        This implementation searches for destination information by automating
        browser interactions with travel websites.

        Args:
            destination: The name of the destination
            topics: Optional list of topics to search for
            max_results: Maximum number of results per topic

        Returns:
            Information about the destination

        Raises:
            Exception: If the search fails
        """
        try:
            # Prepare search topics if not provided
            search_topics = topics or [
                "attractions",
                "things to do",
                "best time to visit",
                "local cuisine",
                "transportation",
            ]

            # Initialize result structure
            result: DestinationInfo = {
                "destination": destination,
                "topics": {},
                "sources": [],
            }

            # Use dedicated travel sites for reliable information
            travel_sites = [
                {
                    "url": f"https://www.lonelyplanet.com/search?q={destination}",
                    "name": "Lonely Planet",
                },
                {
                    "url": f"https://www.tripadvisor.com/Search?q={destination}",
                    "name": "TripAdvisor",
                },
                {
                    "url": f"https://www.visitacity.com/en/search?q={destination}",
                    "name": "Visitacity",
                },
            ]

            # Process each topic
            for topic in search_topics:
                result["topics"][topic] = []

                # Try to find information for this topic from travel sites
                for site in travel_sites:
                    if len(result["topics"][topic]) >= max_results:
                        break

                    try:
                        # Navigate to the site
                        await call_mcp_tool(
                            "mcp__playwright__playwright_navigate",
                            {
                                "url": site["url"],
                                "browserType": self.browser_config.get(
                                    "browser", "chromium"
                                ),
                                "headless": self.browser_config.get("headless", True),
                                "width": self.browser_config.get("viewport", {}).get(
                                    "width", 1280
                                ),
                                "height": self.browser_config.get("viewport", {}).get(
                                    "height", 720
                                ),
                                "waitUntil": "networkidle",
                            },
                        )

                        # Wait for search results to load
                        await call_mcp_tool(
                            "mcp__playwright__playwright_wait",
                            {"time": 3},  # Wait 3 seconds
                        )

                        # Find relevant results
                        search_script = f"""
                        Array.from(document.querySelectorAll('a'))
                            .filter(a => a.textContent && 
                                   a.textContent.toLowerCase().includes('{topic.lower()}'))
                            .map(a => ({{
                                title: a.textContent.trim(),
                                url: a.href,
                                snippet: a.closest('div')?.textContent?.trim() || ''
                            }}))
                            .slice(0, {max_results})
                        """

                        search_results = await call_mcp_tool(
                            "mcp__playwright__playwright_evaluate",
                            {"script": search_script},
                        )

                        # Process search results
                        for item in search_results:
                            # Extract domain from URL
                            domain = site["name"]

                            # Create topic result
                            topic_result: TopicResult = {
                                "title": item.get("title", ""),
                                "content": item.get("snippet", ""),
                                "source": domain,
                                "url": item.get("url", ""),
                                "confidence": 0.75,  # Default confidence
                            }

                            result["topics"][topic].append(topic_result)

                            # Add source to sources list if not already there
                            if domain not in result["sources"]:
                                result["sources"].append(domain)

                            # Stop if we have enough results
                            if len(result["topics"][topic]) >= max_results:
                                break
                    except Exception as site_error:
                        logger.warning(
                            f"Error searching {site['name']} for {topic}: "
                            f"{str(site_error)}"
                        )

            # Close the browser
            await call_mcp_tool("mcp__playwright__playwright_close", {})

            return result
        except Exception as e:
            logger.error(
                f"Error searching destination info for {destination} "
                f"with Playwright: {str(e)}"
            )
            raise Exception(
                f"Failed to search destination information with Playwright: {str(e)}"
            ) from e
        finally:
            # Ensure the browser is closed
            try:
                await call_mcp_tool("mcp__playwright__playwright_close", {})
            except Exception:
                pass

    async def monitor_price_changes(
        self, url: str, price_selector: str, options: Optional[MonitorOptions] = None
    ) -> PriceMonitorResult:
        """Set up monitoring for price changes on a webpage using Playwright.

        This implementation is especially useful for monitoring prices on sites
        that require JavaScript or have dynamic content.

        Args:
            url: The URL of the webpage to monitor
            price_selector: CSS selector for the price element
            options: Optional monitoring options

        Returns:
            The price monitoring result

        Raises:
            Exception: If the monitoring setup fails
        """
        options = options or {}

        try:
            # Generate a unique monitoring ID
            import uuid

            monitoring_id = f"price_monitor_{uuid.uuid4().hex[:8]}"

            # Navigate to the URL
            await call_mcp_tool(
                "mcp__playwright__playwright_navigate",
                {
                    "url": url,
                    "browserType": self.browser_config.get("browser", "chromium"),
                    "headless": self.browser_config.get("headless", True),
                    "width": self.browser_config.get("viewport", {}).get("width", 1280),
                    "height": self.browser_config.get("viewport", {}).get(
                        "height", 720
                    ),
                    "waitUntil": "networkidle",
                },
            )

            # Wait for price element to appear
            wait_script = f"""
            new Promise((resolve, reject) => {{
                const maxAttempts = 10;
                let attempts = 0;
                
                const checkElement = () => {{
                    const element = document.querySelector('{price_selector}');
                    if (element) {{
                        resolve(true);
                    }} else if (attempts < maxAttempts) {{
                        attempts++;
                        setTimeout(checkElement, 500);
                    }} else {{
                        reject(new Error('Price element not found'));
                    }}
                }};
                
                checkElement();
            }})
            """

            await call_mcp_tool(
                "mcp__playwright__playwright_evaluate", {"script": wait_script}
            )

            # Extract price text and parse it
            price_script = f"""
            (() => {{
                const priceElement = document.querySelector('{price_selector}');
                if (!priceElement) return null;
                
                const priceText = priceElement.textContent.trim();
                
                // Try to extract currency and amount
                const currencySymbols = ['$', '€', '£', '¥', '₹', 'A$', 'C$', 
                                       'HK$', '₽', '₩'];
                let currency = '';
                let amount = '';
                
                // Check for currency symbols
                for (const symbol of currencySymbols) {{
                    if (priceText.includes(symbol)) {{
                        currency = symbol;
                        amount = priceText.replace(/[^0-9.,]/g, '');
                        break;
                    }}
                }}
                
                // If no currency symbol found, try to look for currency code
                if (!currency) {{
                    const currencyCodes = ['USD', 'EUR', 'GBP', 'JPY', 'INR', 
                                         'AUD', 'CAD', 'HKD', 'RUB', 'KRW'];
                    for (const code of currencyCodes) {{
                        if (priceText.includes(code)) {{
                            currency = code;
                            amount = priceText.replace(/[^0-9.,]/g, '');
                            break;
                        }}
                    }}
                }}
                
                // If still no currency, default to USD
                if (!currency) {{
                    currency = 'USD';
                    amount = priceText.replace(/[^0-9.,]/g, '');
                }}
                
                // Clean up amount and convert to number
                amount = amount.replace(',', '.');
                
                return {{
                    raw_text: priceText,
                    currency: currency,
                    amount: parseFloat(amount)
                }};
            }})()
            """

            price_result = await call_mcp_tool(
                "mcp__playwright__playwright_evaluate", {"script": price_script}
            )

            # Extract timestamp
            import datetime

            timestamp = datetime.datetime.now().isoformat()

            # Close the browser
            await call_mcp_tool("mcp__playwright__playwright_close", {})

            # Set up frequency for next check
            frequency = options.get("frequency", "daily")
            now = datetime.datetime.now()

            if frequency == "hourly":
                next_check = now + datetime.timedelta(hours=1)
            elif frequency == "daily":
                next_check = now + datetime.timedelta(days=1)
            else:  # weekly
                next_check = now + datetime.timedelta(weeks=1)

            # Initialize price objects
            initial_price = None
            if price_result and "amount" in price_result and "currency" in price_result:
                initial_price = {
                    "amount": price_result["amount"],
                    "currency": price_result["currency"],
                    "timestamp": timestamp,
                }

            return {
                "url": url,
                "initial_price": initial_price,
                "current_price": initial_price,
                "monitoring_id": monitoring_id,
                "status": "scheduled",
                "history": [],
                "next_check": next_check.isoformat(),
            }
        except Exception as e:
            logger.error(
                f"Error setting up price monitoring for {url} with Playwright: {str(e)}"
            )
            raise Exception(
                f"Failed to monitor price changes with Playwright: {str(e)}"
            ) from e
        finally:
            # Ensure the browser is closed
            try:
                await call_mcp_tool("mcp__playwright__playwright_close", {})
            except Exception:
                pass

    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> EventList:
        """Get latest events for a destination using Playwright.

        This implementation uses Playwright to navigate to event listing websites
        and extract event information through browser automation.

        Args:
            destination: The name of the destination
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            categories: Optional list of event categories

        Returns:
            List of events

        Raises:
            Exception: If the event search fails
        """
        try:
            # Format dates for URL parameters
            import datetime

            try:
                start_obj = datetime.datetime.fromisoformat(start_date)
                end_obj = datetime.datetime.fromisoformat(end_date)
                start_formatted = start_obj.strftime("%Y-%m-%d")
                end_formatted = end_obj.strftime("%Y-%m-%d")
            except ValueError:
                # Fallback to original format if parsing fails
                start_formatted = start_date
                end_formatted = end_date

            # Initialize result structure
            events = []
            sources = []

            # Use event listing websites
            event_sites = [
                {
                    "name": "Eventbrite",
                    "url": f"https://www.eventbrite.com/d/{destination}/events/?start_date={start_formatted}&end_date={end_formatted}",
                },
                {
                    "name": "TripAdvisor",
                    "url": f"https://www.tripadvisor.com/Attractions-g28953-Activities-c58-t1,113-{destination}.html",
                },
            ]

            # Process each event site
            for site in event_sites:
                try:
                    # Navigate to the site
                    await call_mcp_tool(
                        "mcp__playwright__playwright_navigate",
                        {
                            "url": site["url"],
                            "browserType": self.browser_config.get(
                                "browser", "chromium"
                            ),
                            "headless": self.browser_config.get("headless", True),
                            "width": self.browser_config.get("viewport", {}).get(
                                "width", 1280
                            ),
                            "height": self.browser_config.get("viewport", {}).get(
                                "height", 720
                            ),
                            "waitUntil": "networkidle",
                        },
                    )

                    # Wait for event listings to load
                    await call_mcp_tool(
                        "mcp__playwright__playwright_wait",
                        {"time": 5},  # Wait 5 seconds
                    )

                    # Define site-specific extraction logic
                    extraction_script = ""
                    if site["name"] == "Eventbrite":
                        extraction_script = """
                        Array.from(document.querySelectorAll('article.eds-event-card-content'))
                            .map(card => {
                                const linkElement = card.querySelector(
                                    'a.eds-event-card-content__action-link');
                                const titleElement = card.querySelector(
                                    '.eds-event-card__formatted-name--is-clamped');
                                const dateElement = card.querySelector(
                                    '.eds-event-card-content__sub-title');
                                const venueElement = card.querySelector(
                                    '.card-text--truncated__content');
                                const priceElement = card.querySelector(
                                    '.eds-event-card-content__price');
                                const imageElement = card.querySelector('img');
                                
                                return {
                                    name: titleElement ? 
                                        titleElement.textContent.trim() : '',
                                    date: dateElement ? 
                                        dateElement.textContent.trim() : '',
                                    venue: venueElement ? 
                                        venueElement.textContent.trim() : '',
                                    price_range: priceElement ? 
                                        priceElement.textContent.trim() : '',
                                    url: linkElement ? linkElement.href : '',
                                    image_url: imageElement ? imageElement.src : '',
                                    category: ''
                                };
                            })
                        """
                    elif site["name"] == "TripAdvisor":
                        extraction_script = """
                        Array.from(document.querySelectorAll('.attraction_element'))
                            .map(element => {
                                const linkElement = element.querySelector(
                                    'a._1QKQOve4');
                                const titleElement = element.querySelector(
                                    '._1QKQOve4');
                                const reviewElement = element.querySelector(
                                    '._11Zy7Yqw');
                                const addressElement = element.querySelector(
                                    '._2bVdZkNQ');
                                const imageElement = element.querySelector(
                                    'div.IhqAp2wb img');
                                
                                return {
                                    name: titleElement ? 
                                        titleElement.textContent.trim() : '',
                                    description: reviewElement ? 
                                        reviewElement.textContent.trim() : '',
                                    venue: addressElement ? 
                                        addressElement.textContent.trim() : '',
                                    url: linkElement ? linkElement.href : '',
                                    image_url: imageElement ? imageElement.src : '',
                                    category: 'Attraction'
                                };
                            })
                        """

                    # Execute the extraction script
                    extraction_results = await call_mcp_tool(
                        "mcp__playwright__playwright_evaluate",
                        {"script": extraction_script},
                    )

                    # Add the site to sources
                    if site["name"] not in sources:
                        sources.append(site["name"])

                    # Process extraction results
                    for event_data in extraction_results:
                        # Apply category filter if specified
                        if (
                            categories
                            and len(categories) > 0
                            and event_data.get("category")
                            and event_data["category"].lower()
                            not in [cat.lower() for cat in categories]
                        ):
                            continue

                        # Create event entry
                        events.append(
                            {
                                "name": event_data.get("name", ""),
                                "description": event_data.get("description", ""),
                                "category": event_data.get("category", ""),
                                "date": event_data.get("date", ""),
                                "time": event_data.get("time", ""),
                                "venue": event_data.get("venue", ""),
                                "address": event_data.get("address", ""),
                                "url": event_data.get("url", ""),
                                "price_range": event_data.get("price_range", ""),
                                "image_url": event_data.get("image_url", ""),
                                "source": site["name"],
                            }
                        )
                except Exception as site_error:
                    logger.warning(
                        f"Error extracting events from {site['name']}: "
                        f"{str(site_error)}"
                    )

            # Close the browser
            await call_mcp_tool("mcp__playwright__playwright_close", {})

            return {
                "destination": destination,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "events": events,
                "sources": sources,
            }
        except Exception as e:
            logger.error(
                f"Error getting events for {destination} with Playwright: {str(e)}"
            )
            raise Exception(
                f"Failed to get latest events with Playwright: {str(e)}"
            ) from e
        finally:
            # Ensure the browser is closed
            try:
                await call_mcp_tool("mcp__playwright__playwright_close", {})
            except Exception:
                pass

    async def crawl_travel_blog(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> BlogInsights:
        """Extract insights from travel blogs using Playwright.

        This implementation uses Playwright to navigate to popular travel blogs
        and extract insights through browser automation.

        Args:
            destination: The name of the destination
            topics: Optional list of topics to extract
            max_blogs: Maximum number of blogs to crawl
            recent_only: Whether to only crawl recent blogs

        Returns:
            The extracted insights

        Raises:
            Exception: If the blog crawling fails
        """
        try:
            # Define the topics to extract if not provided
            query_topics = topics or [
                "hidden gems",
                "local tips",
                "best experiences",
                "safety",
                "budget tips",
            ]

            # Initialize result structure
            result: BlogInsights = {
                "destination": destination,
                "topics": {topic: [] for topic in query_topics},
                "sources": [],
                "extraction_date": datetime.datetime.now().isoformat(),
            }

            # Define blog search URLs
            blog_search_urls = [
                f"https://www.travelblog.org/search/{destination.replace(' ', '+')}",
                f"https://www.nomadicmatt.com/?s={destination.replace(' ', '+')}",
            ]

            # Track how many blogs we've processed
            blogs_processed = 0

            # Process each blog search
            for search_url in blog_search_urls:
                if blogs_processed >= max_blogs:
                    break

                try:
                    # Navigate to the search page
                    await call_mcp_tool(
                        "mcp__playwright__playwright_navigate",
                        {
                            "url": search_url,
                            "browserType": self.browser_config.get(
                                "browser", "chromium"
                            ),
                            "headless": self.browser_config.get("headless", True),
                            "width": self.browser_config.get("viewport", {}).get(
                                "width", 1280
                            ),
                            "height": self.browser_config.get("viewport", {}).get(
                                "height", 720
                            ),
                            "waitUntil": "networkidle",
                        },
                    )

                    # Wait for search results to load
                    await call_mcp_tool(
                        "mcp__playwright__playwright_wait",
                        {"time": 3},  # Wait 3 seconds
                    )

                    # Extract blog post links
                    link_extraction_script = """
                    Array.from(document.querySelectorAll('a'))
                        .filter(a => {
                            // Filter for links that look like blog posts
                            const href = a.href || '';
                            const text = a.textContent || '';
                            return (
                                href.includes('/blog/') || 
                                href.includes('/post/') || 
                                href.includes('/article/') ||
                                (text.length > 20 && a.querySelector('h2, h3, .title'))
                            );
                        })
                        .map(a => ({
                            title: a.textContent.trim(),
                            url: a.href
                        }))
                        .slice(0, 5)  // Get top 5 results
                    """

                    blog_links = await call_mcp_tool(
                        "mcp__playwright__playwright_evaluate",
                        {"script": link_extraction_script},
                    )

                    # Process each blog post
                    for blog_link in blog_links:
                        if blogs_processed >= max_blogs:
                            break

                        try:
                            # Navigate to the blog post
                            await call_mcp_tool(
                                "mcp__playwright__playwright_navigate",
                                {
                                    "url": blog_link["url"],
                                    "browserType": self.browser_config.get(
                                        "browser", "chromium"
                                    ),
                                    "headless": self.browser_config.get(
                                        "headless", True
                                    ),
                                    "width": self.browser_config.get(
                                        "viewport", {}
                                    ).get("width", 1280),
                                    "height": self.browser_config.get(
                                        "viewport", {}
                                    ).get("height", 720),
                                    "waitUntil": "networkidle",
                                },
                            )

                            # Wait for blog content to load
                            await call_mcp_tool(
                                "mcp__playwright__playwright_wait",
                                {"time": 3},  # Wait 3 seconds
                            )

                            # Extract blog details
                            blog_details_script = """
                            {
                                title: document.title,
                                author: document.querySelector('meta[name="author"]')
                                        ?.content || 
                                        document.querySelector('.author')
                                        ?.textContent.trim() || 
                                        'Unknown Author',
                                publish_date: document.querySelector(
                                    'meta[property="article:published_time"]')
                                    ?.content || 
                                    document.querySelector(
                                        '.date, .post-date, time')
                                    ?.textContent.trim() || 
                                    'Unknown Date',
                                content: document.querySelector(
                                    'article, .post-content, .entry-content, .content'
                                    )?.textContent.trim() || 
                                    document.body.textContent.trim()
                            }
                            """

                            blog_details = await call_mcp_tool(
                                "mcp__playwright__playwright_evaluate",
                                {"script": blog_details_script},
                            )

                            # Check if the blog is recent enough
                            if recent_only:
                                # Try to parse the publish date
                                is_recent = (
                                    True  # Default to true if we can't parse the date
                                )

                                if "publish_date" in blog_details:
                                    try:
                                        publish_date = datetime.datetime.fromisoformat(
                                            blog_details["publish_date"]
                                        )
                                        one_year_ago = (
                                            datetime.datetime.now()
                                            - datetime.timedelta(days=365)
                                        )
                                        is_recent = publish_date >= one_year_ago
                                    except (ValueError, TypeError):
                                        # Can't parse the date, so assume it's recent
                                        pass

                                if not is_recent:
                                    continue

                            # Add blog to sources
                            blog_source = {
                                "url": blog_link["url"],
                                "title": blog_details.get("title", ""),
                                "author": blog_details.get("author", ""),
                                "publish_date": blog_details.get("publish_date", ""),
                                "reputation_score": 0.7,  # Default score
                            }

                            result["sources"].append(cast(BlogSource, blog_source))

                            # Create blog source index
                            source_index = len(result["sources"]) - 1

                            # Process content for each topic
                            blog_content = blog_details.get("content", "")

                            for topic in query_topics:
                                # Simple sentiment analysis based on
                                # topic-related content
                                topic_content = self._extract_topic_content(
                                    blog_content, topic
                                )
                                sentiment = self._analyze_sentiment(topic_content)

                                # Extract key points
                                key_points = self._extract_key_points(topic_content, 3)

                                # Add topic insight if we have content
                                if topic_content:
                                    result["topics"][topic].append(
                                        {
                                            "title": blog_details.get("title", ""),
                                            "summary": (
                                                topic_content[:200] + "..."
                                                if len(topic_content) > 200
                                                else topic_content
                                            ),
                                            "key_points": key_points,
                                            "sentiment": sentiment,
                                            "source_index": source_index,
                                        }
                                    )

                            blogs_processed += 1
                        except Exception as blog_error:
                            logger.warning(
                                f"Error processing blog {blog_link['url']}: "
                                f"{str(blog_error)}"
                            )
                except Exception as search_error:
                    logger.warning(
                        f"Error searching blogs with {search_url}: {str(search_error)}"
                    )

            # Close the browser
            await call_mcp_tool("mcp__playwright__playwright_close", {})

            return result
        except Exception as e:
            logger.error(
                f"Error crawling travel blogs for {destination} "
                f"with Playwright: {str(e)}"
            )
            raise Exception(
                f"Failed to crawl travel blogs with Playwright: {str(e)}"
            ) from e
        finally:
            # Ensure the browser is closed
            try:
                await call_mcp_tool("mcp__playwright__playwright_close", {})
            except Exception:
                pass

    def _extract_topic_content(self, content: str, topic: str) -> str:
        """Extract content related to a specific topic from text.

        Args:
            content: The content to extract from
            topic: The topic to extract

        Returns:
            The extracted content
        """
        # Simple extraction based on paragraph proximity to topic keywords
        paragraphs = content.split("\n\n")
        topic_words = set(topic.lower().split())

        relevant_paragraphs = []

        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()

            # Check if paragraph contains topic words
            if any(word in paragraph_lower for word in topic_words):
                relevant_paragraphs.append(paragraph)

        return "\n\n".join(relevant_paragraphs)

    def _analyze_sentiment(self, content: str) -> str:
        """Analyze sentiment of content (positive, neutral, negative).

        Args:
            content: The content to analyze

        Returns:
            The sentiment ("positive", "neutral", or "negative")
        """
        # Simple keyword-based sentiment analysis
        positive_words = [
            "amazing",
            "awesome",
            "beautiful",
            "best",
            "breathtaking",
            "excellent",
            "exceptional",
            "fantastic",
            "favorite",
            "fun",
            "good",
            "great",
            "happy",
            "incredible",
            "love",
            "perfect",
            "recommend",
            "stunning",
            "wonderful",
        ]

        negative_words = [
            "awful",
            "bad",
            "disappointing",
            "dangerous",
            "difficult",
            "expensive",
            "frustrating",
            "horrible",
            "overrated",
            "poor",
            "terrible",
            "ugly",
            "unsafe",
            "waste",
            "worst",
        ]

        content_lower = content.lower()

        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        # Determine sentiment
        if positive_count > negative_count * 2:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _extract_key_points(self, content: str, num_points: int) -> List[str]:
        """Extract key points from content.

        Args:
            content: The content to extract from
            num_points: The number of key points to extract

        Returns:
            The extracted key points
        """
        # Simple key point extraction based on sentences
        import re

        # Split content into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)

        # Filter out short sentences
        sentences = [s for s in sentences if len(s.split()) > 5]

        # Pick sentences that look like key points (may contain factual information)
        key_point_indicators = [
            "must",
            "should",
            "best",
            "top",
            "popular",
            "famous",
            "important",
            "essential",
            "tip",
            "recommend",
            "advice",
            "don't miss",
            "make sure",
            "remember",
            "to visit",
            "a good",
        ]

        key_points = []

        # First pass: Find sentences with key point indicators
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in key_point_indicators):
                key_points.append(sentence)

            if len(key_points) >= num_points:
                break

        # If we don't have enough, just take the first N sentences
        if len(key_points) < num_points and len(sentences) > 0:
            remaining = num_points - len(key_points)
            for sentence in sentences:
                if sentence not in key_points:
                    key_points.append(sentence)
                    remaining -= 1

                    if remaining <= 0:
                        break

        return key_points
