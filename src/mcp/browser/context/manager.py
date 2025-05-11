"""Browser context manager for TripSage Playwright integration."""

import asyncio
import random
import time
from typing import Dict

from playwright.async_api import BrowserContext, async_playwright

from src.mcp.browser.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PlaywrightManager:
    """Manages browser instances and contexts for Playwright automation."""

    def __init__(self):
        """Initialize the PlaywrightManager."""
        self.playwright = None
        self.browser = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.last_activity = {}
        self._maintenance_task = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize playwright and browser if not already initialized."""
        if not self.playwright:
            logger.info("Initializing Playwright")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=Config.PLAYWRIGHT_HEADLESS, slow_mo=Config.PLAYWRIGHT_SLOW_MO
            )

            # Start maintenance task
            if not self._maintenance_task:
                self._maintenance_task = asyncio.create_task(self._maintain_contexts())

    async def get_context(self, session_id: str = "default") -> BrowserContext:
        """Get or create a browser context for the given session ID.

        Args:
            session_id: Unique identifier for the session

        Returns:
            A browser context for the session
        """
        async with self._lock:
            await self.initialize()

            if session_id not in self.contexts:
                logger.info(f"Creating new browser context for session {session_id}")

                # Get user agent from pool
                user_agent = self._get_random_user_agent()

                # Create context with stealth settings
                self.contexts[session_id] = await self.browser.new_context(
                    viewport={
                        "width": Config.VIEWPORT_WIDTH,
                        "height": Config.VIEWPORT_HEIGHT,
                    },
                    user_agent=user_agent,
                    locale="en-US",
                    timezone_id="America/New_York",
                    color_scheme="light",
                    device_scale_factor=1.0,
                    is_mobile=False,
                    has_touch=False,
                    ignore_https_errors=Config.IGNORE_HTTPS_ERRORS,
                )

                # Add additional evasion scripts
                await self._add_stealth_scripts(self.contexts[session_id])

                # Set geolocation if specified
                if Config.GEOLOCATION_ENABLED:
                    await self.contexts[session_id].set_geolocation(
                        {
                            "latitude": Config.GEOLOCATION_LATITUDE,
                            "longitude": Config.GEOLOCATION_LONGITUDE,
                            "accuracy": Config.GEOLOCATION_ACCURACY,
                        }
                    )

                # Add browser permissions if needed
                if Config.BROWSER_PERMISSIONS:
                    await self.contexts[session_id].grant_permissions(
                        Config.BROWSER_PERMISSIONS
                    )

                # Set HTTP credentials if specified
                if Config.HTTP_CREDENTIALS_ENABLED:
                    await self.contexts[session_id].set_extra_http_headers(
                        {"Authorization": f"Basic {Config.HTTP_CREDENTIALS}"}
                    )

            # Update last activity timestamp
            self.last_activity[session_id] = time.time()

            return self.contexts[session_id]

    async def close_context(self, session_id: str = "default"):
        """Close the browser context for the given session ID.

        Args:
            session_id: Unique identifier for the session
        """
        async with self._lock:
            if session_id in self.contexts:
                logger.info(f"Closing browser context for session {session_id}")
                await self.contexts[session_id].close()
                del self.contexts[session_id]

                if session_id in self.last_activity:
                    del self.last_activity[session_id]

    async def close(self):
        """Close all browser contexts and the browser."""
        async with self._lock:
            logger.info("Closing all browser contexts and browser")
            # Cancel maintenance task if running
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
                self._maintenance_task = None

            # Close all contexts
            for session_id in list(self.contexts.keys()):
                await self.close_context(session_id)

            # Close browser and playwright
            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

    async def _maintain_contexts(self):
        """Periodically check and close inactive contexts."""
        while True:
            try:
                await asyncio.sleep(Config.CONTEXT_CLEANUP_INTERVAL)

                current_time = time.time()
                async with self._lock:
                    for session_id, last_active in list(self.last_activity.items()):
                        # Check if context has been inactive for too long
                        if current_time - last_active > Config.CONTEXT_MAX_IDLE_TIME:
                            logger.info(f"Closing inactive context: {session_id}")
                            if session_id in self.contexts:
                                await self.contexts[session_id].close()
                                del self.contexts[session_id]
                            del self.last_activity[session_id]
            except asyncio.CancelledError:
                # Task was cancelled, exit the loop
                break
            except Exception as e:
                logger.error(f"Error in context maintenance: {e}")

    async def _add_stealth_scripts(self, context: BrowserContext):
        """Add scripts to help avoid bot detection.

        Args:
            context: Browser context to add scripts to
        """
        # Override navigator properties to avoid fingerprinting
        await context.add_init_script(
            """
        () => {
            const newProto = navigator.__proto__;
            delete newProto.webdriver;
            navigator.__proto__ = newProto;
            
            // Add language preference
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Modify plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [1, 2, 3, 4, 5].map(() => ({
                        name: `Plugin ${Math.floor(Math.random() * 10000)}`,
                        description: 'This plugin enables various media types',
                        filename: `plugin_${Math.floor(Math.random() * 10000)}.dll`,
                        length: Math.floor(Math.random() * 5) + 1
                    }));
                },
            });
        }
        """
        )

    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the pool.

        Returns:
            A random user agent string
        """
        return random.choice(Config.USER_AGENT_POOL)


# Singleton instance
_playwright_manager = None


def get_playwright_manager() -> PlaywrightManager:
    """Get or create the PlaywrightManager singleton.

    Returns:
        The PlaywrightManager instance
    """
    global _playwright_manager

    if _playwright_manager is None:
        _playwright_manager = PlaywrightManager()

    return _playwright_manager
