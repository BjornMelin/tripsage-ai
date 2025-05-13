# Browser Tools for TripSage

This module provides browser automation functionality for TripSage agents, utilizing external Microservice Coordination Protocol (MCP) servers: Playwright MCP and Stagehand MCP.

## Overview

The browser tools module replaces the custom Browser MCP implementation with external MCP integrations, following GitHub Issue #26. This approach offers several advantages:

- Leverages specialized maintained browser automation services
- Provides both precise control (Playwright) and AI-driven automation (Stagehand)
- Reduces maintenance burden by using dedicated MCP servers
- Enables caching of operation results for improved performance

## Available Tools

The module provides the following tools for agent use:

1. **check_flight_status** - Checks the status of a flight using airline website

   - Parameters: airline, flight_number, date
   - Returns: FlightStatusResponse with status, departure info, arrival info, and notes

2. **verify_booking** - Verifies booking details across various travel providers

   - Parameters: booking_type, confirmation_number, provider, email
   - Returns: BookingVerificationResponse with verification status and details

3. **monitor_price** - Sets up price monitoring for a product on a specified webpage
   - Parameters: url, product_name, target_price, notification_email
   - Returns: PriceMonitorResponse with monitoring ID and status

## Usage

Import the tools directly:

```python
from src.agents.tools.browser.browser_tools import (
    check_flight_status,
    verify_booking,
    monitor_price,
)

# Check flight status
status = check_flight_status(
    airline="Delta",
    flight_number="DL123",
    date="2025-05-15"
)

# Verify a booking
verification = verify_booking(
    booking_type="flight",
    confirmation_number="ABC123",
    provider="Delta",
    email="user@example.com"
)

# Set up price monitoring
monitoring = monitor_price(
    url="https://example.com/product",
    product_name="Premium Hotel Room",
    target_price=199.99,
    notification_email="user@example.com"
)
```

## Configuration

The tools use configurations from TripSage's AppSettings. Ensure these settings are properly configured in your environment:

```python
# Example AppSettings configuration
PLAYWRIGHT_MCP_CONFIG = PlaywrightMCPConfig(
    base_url="https://playwright-mcp.example.com",
    api_key="your-api-key-here"
)

STAGEHAND_MCP_CONFIG = StagehandMCPConfig(
    base_url="https://stagehand-mcp.example.com",
    api_key="your-api-key-here"
)
```

## Caching

Browser operations can be time-consuming, so results are cached using Redis:

- Cache keys are generated based on function parameters
- Cache entries expire after a configurable time period (default: 1 hour)
- Cache can be bypassed by setting `force_refresh=True` in function calls

## Error Handling

The tools handle various error scenarios:

- Connection failures to MCP servers
- Invalid inputs or missing parameters
- Authentication failures
- Operation timeouts
- Caching issues

All errors are logged and appropriate exceptions are raised with context-specific messages.

## Extending the Tools

To add new browser automation tools:

1. Define Pydantic models for request and response
2. Implement the core functionality in BrowserService
3. Create an async function that calls the service
4. Add a synchronous wrapper for non-async contexts
5. Update unit tests with the new functionality
