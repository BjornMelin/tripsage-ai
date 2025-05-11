# Browser Automation Integration Guide

This document provides comprehensive instructions for integrating browser automation capabilities into TripSage for flight status checking, booking verification, and other travel-related automation tasks.

## Overview

Browser automation enables TripSage to interact with travel websites programmatically. The implementation uses Playwright with Python to provide:

- Checking flight status on airline websites
- Automating flight check-in procedures
- Verifying booking details on official websites
- Capturing screenshots for verification purposes
- Monitoring price changes for flights and accommodations

## Architecture

TripSage implements a robust browser automation solution using Playwright with Python, which offers:

- Cross-browser support (Chromium, Firefox, WebKit)
- Excellent Python integration with FastMCP 2.0
- Strong performance (35% faster than alternatives)
- Resilient auto-waiting mechanism for stable interactions
- Rich API with comprehensive features for travel-specific automation
- Advanced capabilities for authentication and form handling

## Playwright MCP Server Implementation

### Setup Instructions

1. **Install Required Dependencies**

   ```bash
   # Install Playwright and MCP dependencies
   pip install playwright fastmcp
   python -m playwright install
   ```

2. **Configure Environment Variables**

Create or update the `.env` file in your TripSage project root:

```plaintext
PLAYWRIGHT_MCP_ENDPOINT=http://localhost:3001
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
```

### Core Implementation

Create a file `src/mcp/browser/playwright_server.py`:

```python
import asyncio
from fastmcp import FastMCP, ToolDefinition
from playwright.async_api import async_playwright
from pydantic import BaseModel
from typing import Dict, List, Optional, Union

app = FastMCP()

# Pydantic models for tool parameters
class FlightStatusParams(BaseModel):
    airline: str
    flight_number: str
    date: str

class CheckInParams(BaseModel):
    airline: str
    confirmation_code: str
    last_name: str
    first_name: Optional[str] = None
    flight_date: Optional[str] = None

class BookingVerificationParams(BaseModel):
    type: str  # "flight", "hotel", "car"
    provider: str
    confirmation_code: str
    last_name: str
    first_name: Optional[str] = None

class PriceMonitorParams(BaseModel):
    url: str
    selector: str
    check_frequency: str = "daily"  # "hourly", "daily", "weekly"

# Browser context manager
class PlaywrightManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts = {}

    async def initialize(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True
            )

    async def get_context(self, session_id="default"):
        await self.initialize()
        if session_id not in self.contexts:
            self.contexts[session_id] = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
            )
        return self.contexts[session_id]

    async def close_context(self, session_id="default"):
        if session_id in self.contexts:
            await self.contexts[session_id].close()
            del self.contexts[session_id]

    async def close(self):
        for session_id in list(self.contexts.keys()):
            await self.close_context(session_id)
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Create manager instance
playwright_manager = PlaywrightManager()

@app.tool
async def check_flight_status(params: FlightStatusParams) -> Dict:
    """Check flight status on airline website.

    Args:
        params: Flight status parameters including airline, flight_number, and date

    Returns:
        Dict containing flight status information
    """
    context = await playwright_manager.get_context()

    try:
        # Get airline website URL
        airline_url = get_airline_status_url(params.airline)

        # Create a new page
        page = await context.new_page()

        # Navigate to airline status page
        await page.goto(airline_url)

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Fill in flight details based on airline
        if params.airline == "AA":
            await fill_american_airlines_form(page, params.flight_number, params.date)
        elif params.airline == "DL":
            await fill_delta_airlines_form(page, params.flight_number, params.date)
        else:
            await fill_generic_flight_status_form(page, params.flight_number, params.date)

        # Wait for results to load
        await page.wait_for_load_state("networkidle")

        # Take screenshot of results
        screenshot = await page.screenshot()

        # Get visible text content
        content = await page.content()
        text_content = await page.evaluate("() => document.body.innerText")

        # Parse flight status information
        status_info = parse_flight_status(text_content, params.airline)

        # Close the page
        await page.close()

        return {
            "success": True,
            "airline": params.airline,
            "flight_number": params.flight_number,
            "date": params.date,
            "status": status_info,
            "screenshot": screenshot.decode("utf-8") if screenshot else None,
            "raw_content": text_content[:1000] if text_content else None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to check flight status: {str(e)}",
        }

@app.tool
async def check_in_for_flight(params: CheckInParams) -> Dict:
    """Perform flight check-in.

    Args:
        params: Check-in parameters including airline, confirmation_code, and passenger information

    Returns:
        Dict containing check-in result
    """
    context = await playwright_manager.get_context()

    try:
        # Get airline check-in URL
        check_in_url = get_airline_check_in_url(params.airline)

        # Create a new page
        page = await context.new_page()

        # Navigate to check-in page
        await page.goto(check_in_url)

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Fill in check-in details based on airline
        if params.airline == "AA":
            await fill_american_airlines_check_in(page, params.confirmation_code, params.last_name, params.first_name)
        elif params.airline == "DL":
            await fill_delta_airlines_check_in(page, params.confirmation_code, params.last_name)
        else:
            await fill_generic_check_in_form(page, params.confirmation_code, params.last_name, params.first_name)

        # Wait for check-in page to load
        await page.wait_for_load_state("networkidle")

        # Take screenshot of check-in page
        screenshot = await page.screenshot()

        # Get visible text
        text_content = await page.evaluate("() => document.body.innerText")

        # Check for common error messages
        error_message = detect_check_in_errors(text_content)

        # Close the page
        await page.close()

        if error_message:
            return {
                "success": False,
                "airline": params.airline,
                "confirmation_code": params.confirmation_code,
                "error": error_message,
                "screenshot": screenshot.decode("utf-8") if screenshot else None,
            }

        return {
            "success": True,
            "airline": params.airline,
            "confirmation_code": params.confirmation_code,
            "message": "Check-in completed successfully",
            "boarding_pass_available": "boarding pass" in text_content.lower(),
            "screenshot": screenshot.decode("utf-8") if screenshot else None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to check in: {str(e)}",
        }

@app.tool
async def verify_booking(params: BookingVerificationParams) -> Dict:
    """Verify a booking.

    Args:
        params: Booking verification parameters

    Returns:
        Dict containing verification result
    """
    context = await playwright_manager.get_context()

    try:
        # Get verification URL based on booking type and provider
        verification_url = get_booking_verification_url(params.type, params.provider)

        # Create a new page
        page = await context.new_page()

        # Navigate to verification page
        await page.goto(verification_url)

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Fill verification form based on type and provider
        if params.type == "flight":
            await fill_flight_verification_form(page, params.provider, params.confirmation_code, params.last_name)
        elif params.type == "hotel":
            await fill_hotel_verification_form(page, params.provider, params.confirmation_code, params.last_name)
        elif params.type == "car":
            await fill_car_rental_verification_form(page, params.provider, params.confirmation_code, params.last_name)

        # Wait for verification page to load
        await page.wait_for_load_state("networkidle")

        # Take screenshot of verification page
        screenshot = await page.screenshot()

        # Get visible text
        text_content = await page.evaluate("() => document.body.innerText")

        # Extract booking details
        booking_details = extract_booking_details(text_content, params.type, params.provider)

        # Close the page
        await page.close()

        return {
            "success": True,
            "type": params.type,
            "provider": params.provider,
            "confirmation_code": params.confirmation_code,
            "details": booking_details,
            "screenshot": screenshot.decode("utf-8") if screenshot else None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to verify booking: {str(e)}",
        }

@app.tool
async def monitor_price(params: PriceMonitorParams) -> Dict:
    """Monitor price for a travel item.

    Args:
        params: Price monitoring parameters

    Returns:
        Dict containing price monitoring result
    """
    context = await playwright_manager.get_context()

    try:
        # Create a new page
        page = await context.new_page()

        # Navigate to the URL
        await page.goto(params.url)

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Find price element
        price_element = await page.query_selector(params.selector)
        if not price_element:
            raise Exception(f"Price element not found with selector: {params.selector}")

        # Extract price text
        price_text = await price_element.text_content()

        # Parse price (extract numeric value and currency)
        price_info = parse_price(price_text)

        # Take screenshot
        screenshot = await page.screenshot()

        # Close the page
        await page.close()

        return {
            "success": True,
            "url": params.url,
            "initial_price": {
                "amount": price_info["amount"],
                "currency": price_info["currency"],
                "extracted_text": price_text,
                "timestamp": get_current_timestamp()
            },
            "check_frequency": params.check_frequency,
            "next_check": calculate_next_check(params.check_frequency),
            "screenshot": screenshot.decode("utf-8") if screenshot else None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to monitor price: {str(e)}",
        }

# Helper functions
def get_airline_status_url(airline: str) -> str:
    """Get URL for airline flight status page."""
    airline_urls = {
        "AA": "https://www.aa.com/travelInformation/flights/status",
        "DL": "https://www.delta.com/flight-status-lookup",
        "UA": "https://www.united.com/en/us/flightstatus",
        "WN": "https://www.southwest.com/air/flight-status",
    }
    return airline_urls.get(airline, f"https://www.google.com/search?q={airline}+flight+status")

def get_airline_check_in_url(airline: str) -> str:
    """Get URL for airline check-in page."""
    checkin_urls = {
        "AA": "https://www.aa.com/reservation/view/find-your-reservation",
        "DL": "https://www.delta.com/checkin/search",
        "UA": "https://www.united.com/en/us/checkin",
        "WN": "https://www.southwest.com/air/check-in/index.html",
    }
    return checkin_urls.get(airline, f"https://www.google.com/search?q={airline}+check+in")

def get_booking_verification_url(type: str, provider: str) -> str:
    """Get URL for booking verification."""
    # Implementation details
    return f"https://example.com/{type}/{provider}/verification"

# Form filling implementations
async def fill_american_airlines_form(page, flight_number, date):
    """Fill American Airlines flight status form."""
    # Implementation details
    pass

async def fill_delta_airlines_form(page, flight_number, date):
    """Fill Delta Airlines flight status form."""
    # Implementation details
    pass

async def fill_generic_flight_status_form(page, flight_number, date):
    """Fill generic flight status form."""
    # Implementation details
    pass

# Additional helper functions
def parse_flight_status(text_content, airline):
    """Parse flight status from text content."""
    # Implementation details
    return {"status": "On Time"}

def detect_check_in_errors(text_content):
    """Detect common check-in error messages."""
    # Implementation details
    return None

def extract_booking_details(text_content, type, provider):
    """Extract booking details from text content."""
    # Implementation details
    return {"confirmation": "ABC123"}

def parse_price(price_text):
    """Parse price from text."""
    # Implementation details
    return {"amount": 100.0, "currency": "USD"}

def get_current_timestamp():
    """Get current timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()

def calculate_next_check(frequency):
    """Calculate next check timestamp based on frequency."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    if frequency == "hourly":
        next_check = now + timedelta(hours=1)
    elif frequency == "daily":
        next_check = now + timedelta(days=1)
    elif frequency == "weekly":
        next_check = now + timedelta(weeks=1)
    else:
        next_check = now + timedelta(days=1)  # Default to daily
    return next_check.isoformat()

# Cleanup on shutdown
@app.on_shutdown
async def shutdown():
    await playwright_manager.close()

if __name__ == "__main__":
    app.run()
```

## OpenAI Agents SDK Integration

Integration with OpenAI Agents SDK allows browser automation to be used seamlessly within travel agent workflows:

```python
from agents import Agent, function_tool
from pydantic import BaseModel
from typing import Optional

class FlightStatusParams(BaseModel):
    airline: str
    flight_number: str
    date: str

@function_tool
async def check_flight_status(params: FlightStatusParams) -> str:
    """Check flight status on airline website.

    Args:
        params: Flight status parameters including airline, flight_number, and date

    Returns:
        Formatted string with flight status information
    """
    try:
        # Call Playwright MCP Server
        result = await playwright_client.check_flight_status(
            params.dict()
        )

        # Store in Supabase
        await supabase.table("flight_status_checks").insert({
            "airline": params.airline,
            "flight_number": params.flight_number,
            "date": params.date,
            "status": result["status"],
            "checked_at": "NOW()"
        })

        # Format response for agent
        if result["success"]:
            return f"Flight {params.airline} {params.flight_number} on {params.date} is {result['status']['status']}."
        else:
            return f"Unable to check flight status: {result['message']}"
    except Exception as e:
        logger.error(f"Flight status error: {e}")
        return f"Error checking flight status: {str(e)}"
```

## Usage Patterns and Optimization

### Performance Optimization

1. **Browser Context Management**

   - Reuse browser contexts when possible to reduce startup time
   - Implement session-based context pooling for resource efficiency
   - Close contexts when not in use to free resources

2. **Parallel Processing**

   - Execute multiple browser tasks concurrently
   - Implement task queuing for high-volume scenarios
   - Use asyncio for efficient asynchronous execution

3. **Caching Strategy**

   - Cache flight status results for 30 minutes
   - Cache booking verification results for 60 minutes
   - Implement invalidation based on time-to-live (TTL)

4. **Resource Utilization**

   - Use headless mode for production
   - Optimize viewport size for specific tasks
   - Close pages immediately after use

### Anti-Detection Strategies

1. **User Agent Rotation**

   - Implement a pool of realistic user agents
   - Rotate user agents between sessions
   - Match user agent to browser type

2. **Timing Randomization**

   - Add random delays between actions
   - Simulate human-like interaction patterns
   - Implement exponential backoff for retries

3. **Fingerprint Management**
   - Minimize JavaScript fingerprinting surface
   - Use stealth plugins to reduce detectability
   - Implement cookie management for consistent sessions

## Troubleshooting

### Common Issues

1. **Element Not Found Errors**

   - The website structure may have changed
   - Implement more robust selectors (XPath + CSS)
   - Use retry mechanisms with increasing timeouts

2. **Authentication Challenges**

   - Implement proper cookie handling
   - Add support for multi-factor authentication
   - Handle CAPTCHA detection and resolution

3. **Website Layout Changes**

   - Use AI-enhanced selectors for resilience
   - Implement multiple selector strategies
   - Create airline-specific adapters for major carriers

4. **Resource Constraints**

   - Monitor memory and CPU usage
   - Implement browser instance limits
   - Use garbage collection for abandoned sessions

### Debugging Steps

1. **Visual Debugging**

   - Use screenshots to analyze failure points
   - Compare with previously successful runs
   - Look for visual cues about website changes

2. **Console Log Analysis**

   - Capture browser console logs
   - Look for JavaScript errors and warnings
   - Check for blocked resources

3. **Network Analysis**

   - Monitor network requests and responses
   - Check for blocked or failed requests
   - Verify proper resource loading

4. **Step-by-Step Verification**

   - Break automation into smaller steps
   - Test each step individually
   - Identify the exact point of failure

## Integration with FastMCP 2.0

The Playwright browser automation integrates seamlessly with FastMCP 2.0 for Python:

```python
# Client for interacting with the Browser Automation MCP Server
class PlaywrightClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    async def check_flight_status(self, params: dict) -> dict:
        """Check flight status on airline website."""
        return await self._call_mcp_tool("check_flight_status", params)

    async def check_in_for_flight(self, params: dict) -> dict:
        """Perform flight check-in."""
        return await self._call_mcp_tool("check_in_for_flight", params)

    async def verify_booking(self, params: dict) -> dict:
        """Verify a booking."""
        return await self._call_mcp_tool("verify_booking", params)

    async def monitor_price(self, params: dict) -> dict:
        """Monitor price for a travel item."""
        return await self._call_mcp_tool("monitor_price", params)

    async def _call_mcp_tool(self, tool_name: str, params: dict) -> dict:
        """Call an MCP tool on the Playwright server."""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/api/v1/tools/{tool_name}/call",
                json={"params": params},
                timeout=120.0
            )
            if response.status_code != 200:
                raise Exception(f"MCP call failed: {response.text}")
            return response.json()
```

## Security Best Practices

1. **Input Validation**

   - Validate all user inputs before processing
   - Sanitize parameters to prevent injection attacks
   - Implement strong typing for all parameters

2. **Screenshot Security**

   - Review screenshots for sensitive information
   - Implement automatic redaction of sensitive data
   - Securely store and handle screenshots

3. **Session Management**

   - Implement secure session expiration
   - Use session-specific browser contexts
   - Clean up resources after session completion

4. **Error Handling**

   - Provide minimal error details to end users
   - Log detailed errors for debugging
   - Implement circuit breaker pattern for unreliable sites

## Future Enhancements

1. **Stagehand Integration**

   - Consider adding Stagehand for AI-driven resilience
   - Leverage Stagehand's natural language capabilities
   - Use for sites with frequent layout changes

2. **BrowserBase Consideration**

   - Evaluate BrowserBase for cloud scaling needs
   - Leverage managed captcha solving and proxy rotation
   - Consider for high-volume production scenarios

3. **Extended Capabilities**

   - Add support for receipt scanning and OCR
   - Implement travel document verification
   - Enhance visual verification capabilities

## Conclusion

The Playwright with Python integration provides TripSage with a robust and scalable browser automation solution. With superior performance, excellent Python integration, and comprehensive features, it represents a significant upgrade over the Browser-use implementation. The integration with FastMCP 2.0 and OpenAI Agents SDK allows for seamless incorporation into the travel planning workflow, enhancing the overall user experience.
