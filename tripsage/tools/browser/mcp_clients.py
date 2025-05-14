"""
MCP Client implementations for Browser Tools.
"""

import json
import logging
import uuid
from typing import Any, Dict

import httpx

from tripsage.utils.error_handling import TripSageError
from tripsage.utils.settings import settings

# Setup logging
logger = logging.getLogger(__name__)

# Constants for MCP server types
MCP_TYPE_PLAYWRIGHT = "playwright"
MCP_TYPE_STAGEHAND = "stagehand"


class BrowserError(TripSageError):
    """Error raised when browser automation fails."""

    pass


class MCPClient:
    """Base client for MCP server communication."""

    def __init__(self, mcp_type: str):
        """Initialize MCP client.

        Args:
            mcp_type: Type of MCP server to use (playwright or stagehand)
        """
        self.mcp_type = mcp_type

        if mcp_type == MCP_TYPE_PLAYWRIGHT:
            self.endpoint = settings.browser.playwright_mcp_endpoint
            self.api_key = settings.browser.playwright_mcp_api_key
            self.timeout = settings.browser.playwright_mcp_timeout
        elif mcp_type == MCP_TYPE_STAGEHAND:
            self.endpoint = settings.browser.stagehand_mcp_endpoint
            self.api_key = settings.browser.stagehand_mcp_api_key
            self.timeout = settings.browser.stagehand_mcp_timeout
        else:
            raise ValueError(f"Unsupported MCP type: {mcp_type}")

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
        )

    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP method with parameters.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Response data from MCP server

        Raises:
            BrowserError: If MCP server operation fails
        """
        try:
            logger.debug(f"Executing MCP method {method} with params: {params}")

            payload = {
                "method": method,
                "params": params,
                "id": str(uuid.uuid4()),
                "jsonrpc": "2.0",
            }

            response = await self.client.post(
                self.endpoint,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise BrowserError(
                    f"MCP server error: {data['error'].get('message', 'Unknown error')}"
                )

            if "result" not in data:
                raise BrowserError(
                    "Invalid MCP server response: missing 'result' field"
                )

            return data["result"]

        except httpx.HTTPError as e:
            error_msg = f"HTTP error communicating with MCP server: {str(e)}"
            raise BrowserError(error_msg) from e
        except json.JSONDecodeError as err:
            raise BrowserError("Failed to parse MCP server response as JSON") from err
        except Exception as e:
            raise BrowserError(f"MCP server operation failed: {str(e)}") from e

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class PlaywrightMCPClient(MCPClient):
    """Client for Playwright MCP server."""

    def __init__(self):
        """Initialize Playwright MCP client."""
        super().__init__(MCP_TYPE_PLAYWRIGHT)


class StagehandMCPClient(MCPClient):
    """Client for Stagehand MCP server."""

    def __init__(self):
        """Initialize Stagehand MCP client."""
        super().__init__(MCP_TYPE_STAGEHAND)
