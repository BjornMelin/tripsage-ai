# Browser Automation MCP Integration Guide

This document provides a comprehensive guide to TripSage's browser automation strategy, focusing on the integration of external MCP servers like Playwright MCP and Stagehand MCP for tasks requiring direct browser interaction.

## 1. Overview and Strategy

Browser automation is essential for TripSage to perform tasks that cannot be achieved through standard APIs or static web crawling. These tasks include:

*   Checking real-time flight status on airline websites.
*   Automating flight check-in procedures.
*   Verifying booking details on provider websites, especially when confirmation APIs are lacking.
*   Capturing screenshots for verification or user records.
*   Monitoring dynamic price changes on specific pages.
*   Interacting with websites that heavily rely on JavaScript or require user login for data access.

**Strategic Shift**: TripSage has moved away from a custom-built Browser MCP. Instead, it integrates with **specialized external MCP servers** built for browser automation, primarily:
1.  **Playwright MCP**: For precise, script-based browser automation leveraging the Playwright framework.
2.  **Stagehand MCP (Considered for future/advanced use)**: For AI-driven, more resilient browser automation that can adapt to UI changes.

This approach aligns with the "external first" MCP strategy, reducing custom development and maintenance while leveraging robust, dedicated solutions. TripSage interacts with these external MCPs via its Python-based `BrowserAutomationClient`.

## 2. Evaluation of Browser Automation Technologies

A thorough evaluation of browser automation frameworks was conducted, considering performance, compatibility, cost, integration complexity, and resilience.

### Key Findings:

*   **Playwright**:
    *   **Performance**: Excellent, significantly faster than Selenium (e.g., ~35% faster navigation).
    *   **Compatibility**: Strong cross-browser support (Chromium, Firefox, WebKit).
    *   **Language Support**: First-class Python support, ideal for TripSage.
    *   **Cost**: Free and open-source.
    *   **Features**: Rich API, auto-waiting, network interception, multi-page support.
    *   **Reliability**: Good, especially with auto-waiting.
    *   **TripSage Fit**: Optimal due to Python bindings and performance.
*   **Stagehand (Playwright-based AI Framework)**:
    *   **Performance**: Built on Playwright, slight AI overhead but potentially faster for complex adaptive tasks.
    *   **Resilience**: Outstanding due to AI adaptation to DOM changes.
    *   **Language Support**: Primarily JavaScript/TypeScript; requires a bridge for Python.
    *   **Cost**: Framework is free, but LLM API calls for AI features incur costs.
    *   **TripSage Fit**: Promising for future use, especially for volatile UIs, but adds complexity and LLM dependency.
*   **Browser-use (Previous Consideration)**:
    *   **Limitations**: Free tier limited to 100 minutes/month, JavaScript-only, less direct Python integration.
    *   **Decision**: Deprecated in favor of Playwright/Stagehand MCPs for better control, unlimited usage (self-hosted), and Python synergy.
*   **Selenium**:
    *   **Limitations**: Slower performance, more prone to flakiness compared to Playwright.
    *   **Decision**: Not preferred due to Playwright's advantages.

**Recommendation**:
*   **Primary**: Utilize a **Playwright MCP server** for most browser automation tasks due to its performance, Python compatibility, and rich feature set.
*   **Secondary/Future**: Consider integrating a **Stagehand MCP server** for tasks requiring high resilience to UI changes or natural language command capabilities.

## 3. Playwright MCP Server Integration

TripSage assumes an external Playwright MCP server is running. This server would expose Playwright's capabilities as MCP tools.

### 3.1. Typical Playwright MCP Tools (Conceptual)

A Playwright MCP server would typically expose tools like:

*   `playwright_navigate`: Navigates to a URL.
    *   Params: `url` (string), `session_id` (string, optional for context reuse).
*   `playwright_click`: Clicks an element.
    *   Params: `selector` (string), `session_id`.
*   `playwright_fill`: Fills a form field.
    *   Params: `selector` (string), `text` (string), `session_id`.
*   `playwright_screenshot`: Captures a screenshot.
    *   Params: `path` (string, optional), `full_page` (bool, optional), `session_id`.
    *   Output: Base64 encoded image or path to saved file.
*   `playwright_get_text`: Extracts text from an element or page.
    *   Params: `selector` (string, optional for specific element), `session_id`.
*   `playwright_get_html`: Extracts HTML content.
    *   Params: `selector` (string, optional), `session_id`.
*   `playwright_run_script`: Executes custom JavaScript on the page.
    *   Params: `script` (string), `session_id`.
*   `playwright_manage_context`: Creates, closes, or lists browser contexts/sessions.

### 3.2. TripSage Configuration for Playwright MCP

```plaintext
# .env
PLAYWRIGHT_MCP_ENDPOINT=http://localhost:3001 # URL of the Playwright MCP server
# PLAYWRIGHT_MCP_API_KEY=... # If the Playwright MCP is secured
```
This endpoint is configured in TripSage's centralized settings.

## 4. TripSage Browser Automation Client and Tools

TripSage implements a `BrowserAutomationClient` in Python that interacts with the external Playwright MCP (and potentially Stagehand MCP in the future). This client then powers specific, high-level function tools for agent use.

### 4.1. `BrowserAutomationClient` (`src/mcp/browser/client.py`)

```python
# src/mcp/browser/client.py (Conceptual Snippet)
from typing import Dict, Any, List, Optional
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)

class BrowserAutomationClient(BaseMCPClient):
    def __init__(self, mcp_server_name: str = "playwright_mcp"): # Default to Playwright MCP
        # mcp_server_name allows switching between playwright_mcp, stagehand_mcp, etc.
        # based on configuration in settings.mcp_servers
        mcp_config = getattr(settings.mcp_servers, mcp_server_name)
        super().__init__(
            server_name=mcp_server_name,
            endpoint=mcp_config.endpoint,
            api_key=mcp_config.api_key.get_secret_value() if mcp_config.api_key else None
        )
        logger.info(f"Initialized BrowserAutomationClient for {mcp_server_name}.")
        self.active_session_id: Optional[str] = None # Simple session management

    async def _ensure_session(self, session_id: Optional[str] = None) -> str:
        # Basic session management; a real Playwright MCP might handle this more robustly
        if session_id:
            self.active_session_id = session_id
            return session_id
        if not self.active_session_id:
            # response = await self.invoke_tool("playwright_manage_context", {"action": "create"})
            # self.active_session_id = response.get("session_id")
            self.active_session_id = "default_session" # Placeholder
        return self.active_session_id

    async def navigate(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = await self._ensure_session(session_id)
        return await self.invoke_tool("playwright_navigate", {"url": url, "session_id": sid})

    async def click(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = await self._ensure_session(session_id)
        return await self.invoke_tool("playwright_click", {"selector": selector, "session_id": sid})

    async def fill(self, selector: str, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = await self._ensure_session(session_id)
        return await self.invoke_tool("playwright_fill", {"selector": selector, "text": text, "session_id": sid})

    async def get_text(self, selector: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = await self._ensure_session(session_id)
        params = {"session_id": sid}
        if selector:
            params["selector"] = selector
        return await self.invoke_tool("playwright_get_text", params)
    
    async def screenshot(self, session_id: Optional[str] = None, full_page: bool = True) -> Dict[str, Any]:
        sid = await self._ensure_session(session_id)
        return await self.invoke_tool("playwright_screenshot", {"session_id": sid, "full_page": full_page})

    # ... other wrapped Playwright MCP tools ...

    async def close_session(self, session_id: Optional[str] = None) -> None:
        sid_to_close = session_id or self.active_session_id
        if sid_to_close:
            # await self.invoke_tool("playwright_manage_context", {"action": "close", "session_id": sid_to_close})
            if self.active_session_id == sid_to_close:
                self.active_session_id = None
```

### 4.2. High-Level Agent Tools (`src/agents/tools/browser_tools.py`)

These tools use the `BrowserAutomationClient` to perform specific travel-related tasks.

```python
# src/agents/tools/browser_tools.py
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from agents import function_tool
# from ....mcp.browser.client import BrowserAutomationClient # Adjust import
# from ....services.browser_service import BrowserService # If a service layer is added

# browser_client = BrowserAutomationClient() # Instantiated via factory or DI
# browser_service = BrowserService(browser_client) # If using a service layer

# --- Pydantic Models for Agent Tool Inputs ---
class FlightStatusParams(BaseModel):
    airline_name: str = Field(..., description="Full name of the airline (e.g., 'American Airlines').")
    flight_number: str = Field(..., description="Flight number (e.g., 'AA123').")
    flight_date: str = Field(..., description="Date of the flight (YYYY-MM-DD).")

class BookingVerificationParams(BaseModel):
    booking_provider: str = Field(..., description="Name of the booking provider (e.g., 'Expedia', 'United Airlines').")
    confirmation_code: str = Field(..., description="Booking confirmation code or PNR.")
    passenger_last_name: str = Field(..., description="Last name of one of the passengers.")
    passenger_first_name: Optional[str] = Field(None, description="First name of the passenger (optional).")
    booking_type: str = Field("flight", description="Type of booking: 'flight', 'hotel', 'car'.")


# --- Agent Function Tools ---
@function_tool
async def check_flight_status_on_website(params: FlightStatusParams) -> Dict[str, Any]:
    """
    Checks the real-time status of a flight by navigating the airline's website.
    Use this if API-based flight status is unavailable or needs verification.
    """
    # This tool would use browser_service or browser_client to:
    # 1. Determine the airline's flight status URL.
    # 2. Navigate to the URL.
    # 3. Fill in the flight number and date.
    # 4. Submit the form.
    # 5. Scrape the status (e.g., "On Time", "Delayed", "Landed").
    # 6. Capture a screenshot.
    # return await browser_service.get_flight_status(
    #     airline_name=params.airline_name,
    #     flight_number=params.flight_number,
    #     flight_date=params.flight_date
    # )
    return {"status": "Not Implemented - Conceptual", "airline": params.airline_name, "flight": params.flight_number} # Placeholder

@function_tool
async def verify_booking_on_website(params: BookingVerificationParams) -> Dict[str, Any]:
    """
    Verifies booking details (flight, hotel, car) by accessing the provider's website.
    Useful for confirming details or when direct API access for booking management is not available.
    """
    # This tool would use browser_service or browser_client to:
    # 1. Navigate to the provider's "manage booking" or "find trip" page.
    # 2. Enter confirmation code, last name, etc.
    # 3. Scrape key booking details (dates, times, locations, passenger names).
    # 4. Capture a screenshot of the booking summary.
    # return await browser_service.verify_booking_details(
    #     provider=params.booking_provider,
    #     confirmation_code=params.confirmation_code,
    #     # ... other params
    # )
    return {"status": "Not Implemented - Conceptual", "confirmation": params.confirmation_code} # Placeholder

# ... other tools like automate_flight_check_in, monitor_webpage_price ...
```
A `BrowserService` layer can be added between the agent tools and the `BrowserAutomationClient` to encapsulate complex multi-step automation sequences (e.g., logging into an airline website, navigating to flight status, and then filling the form).

## 5. Performance and Resource Management

*   **Browser Context Reuse**: The `BrowserAutomationClient` should manage and reuse browser contexts (`session_id`) where appropriate to minimize the overhead of launching new browser instances for every task.
*   **Headless Mode**: Run browsers in headless mode for production/automated tasks to save resources. Enable headed mode for debugging.
*   **Timeouts**: Implement appropriate timeouts for navigation, element interaction, and page loading.
*   **Resource Cleanup**: Ensure browser instances and contexts are properly closed after use to prevent resource leaks. The Playwright MCP server should handle robust cleanup.
*   **Concurrency**: If the Playwright MCP server supports concurrent sessions, the `BrowserAutomationClient` can be made to manage multiple active sessions.

## 6. Caching

*   Results from browser automation tasks (e.g., flight status, verified booking details) should be cached using TripSage's Redis cache.
*   Cache TTLs should be relatively short for dynamic data like flight status (e.g., 5-15 minutes) and longer for more static verification data (e.g., 1-6 hours).

## 7. Error Handling and Resilience

*   Browser automation can be brittle due to website UI changes.
*   **Robust Selectors**: Use selectors that are less likely to change (e.g., based on `data-testid` attributes if available, or stable ARIA roles, rather than relying solely on CSS classes or complex XPath).
*   **Retry Mechanisms**: Implement retries for transient network issues or element loading delays.
*   **Explicit Waits**: Use Playwright's auto-waiting capabilities and add explicit waits for specific conditions where necessary.
*   **Screenshots on Failure**: Capture screenshots when an automation task fails to aid in debugging.
*   **Fallback to Simpler Methods**: If browser automation fails for a task (e.g., flight status), the agent should be able to fall back to API-based methods or inform the user.

## 8. Security Considerations

*   **Input Sanitization**: Sanitize any user-provided data that might be typed into web forms.
*   **Credential Management**: If automation involves logging into websites, handle credentials securely. Avoid storing them directly; prefer methods where the user performs login in their own session if possible, or use securely managed service account credentials if automating backend tasks.
*   **Data Scraping**: Be mindful of website terms of service and data privacy when scraping information. Only extract necessary and publicly available data.

## 9. Conclusion

By integrating with external, specialized Playwright and Stagehand MCPs, TripSage gains powerful and flexible browser automation capabilities. The `BrowserAutomationClient` and high-level agent tools provide a clean, Python-native interface for AI agents to perform complex web interactions, enhancing TripSage's ability to gather real-time information and automate travel-related tasks. This approach prioritizes using robust, maintained external solutions over building custom browser automation infrastructure from scratch.