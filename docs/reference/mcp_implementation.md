# MCP Server Implementation Guide

This document provides detailed examples and guidelines for implementing MCP servers in the TripSage project.

## FastMCP 2.0 Server Implementation

```python
from fastmcp import FastMCP, Context
from typing import Annotated, List, Dict, Any
from pydantic import Field

# Create server with descriptive name
mcp = FastMCP(name="TripSage Weather MCP")

# Define tools with proper type annotations and validation
@mcp.tool()
async def get_weather_forecast(
    location: str,
    days: Annotated[int, Field(gt=0, le=10)],
    ctx: Context
) -> dict:
    """Get weather forecast for a location.

    Args:
        location: City or location name
        days: Number of days to forecast (1-10)
        ctx: MCP context object for logging and progress

    Returns:
        Dict containing forecast data
    """
    await ctx.info(f"Fetching {days}-day forecast for {location}")
    # Implementation...

    # Report progress to client
    await ctx.report_progress(0.5, f"Retrieved weather data for {location}")

    # Sample processing with LLM if needed
    weather_summary = await ctx.sample("Summarize this weather data briefly", weather_data)

    return {"location": location, "forecast": [...], "summary": weather_summary}

# Define resources with proper URIs
@mcp.resource("weather://locations/popular")
def get_popular_locations() -> List[str]:
    """Get list of popular travel destinations."""
    return ["Paris", "Tokyo", "New York", "London", "Dubai"]

# Error handling example
@mcp.tool()
async def get_historical_weather(
    location: str,
    date: str,
    ctx: Context
) -> Dict[str, Any]:
    """Get historical weather for a location on a specific date.

    Args:
        location: City or location name
        date: Date in YYYY-MM-DD format
        ctx: MCP context object

    Returns:
        Dict containing historical weather data
    """
    try:
        await ctx.info(f"Fetching historical weather for {location} on {date}")
        # Implementation...
        return {"location": location, "date": date, "data": [...]}
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        return {"error": "WEATHER_API_ERROR", "message": str(e)}

# Run with appropriate transport
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=3000)
```

## Context Object Usage

The Context object provides several important capabilities for MCP tools:

### Logging

```python
async def search_flights(origin: str, destination: str, ctx: Context):
    await ctx.debug("Debug-level message")
    await ctx.info(f"Searching flights from {origin} to {destination}")
    await ctx.warning("Potential issue with flight search parameters")
    await ctx.error("Error in flight search API response")
```

### Progress Reporting

```python
async def complex_operation(ctx: Context):
    await ctx.report_progress(0.1, "Initializing search...")
    # First phase of work

    await ctx.report_progress(0.5, "Processing results...")
    # Middle phase of work

    await ctx.report_progress(0.9, "Finalizing...")
    # Final phase of work

    await ctx.report_progress(1.0, "Completed")
```

### Resource Access

```python
async def get_weather_for_popular_cities(ctx: Context):
    # Access a registered resource
    popular_cities = await ctx.read_resource("weather://locations/popular")

    results = []
    for city in popular_cities:
        weather = await get_weather(city)
        results.append(weather)

    return results
```

### LLM Assistance

```python
async def analyze_reviews(hotel_id: str, ctx: Context):
    reviews = await fetch_hotel_reviews(hotel_id)

    # Ask the LLM to help analyze the reviews
    sentiment_summary = await ctx.sample(
        "Analyze these hotel reviews and summarize the sentiment. " +
        "Focus on cleanliness, service, and location.",
        reviews
    )

    return {
        "hotel_id": hotel_id,
        "reviews_count": len(reviews),
        "sentiment_summary": sentiment_summary
    }
```

## Error Handling Best Practices

1. **Proper Exception Handling**

```python
@mcp.tool()
async def book_flight(booking_details: Dict[str, Any], ctx: Context):
    try:
        # Attempt to book the flight
        booking = await flight_api.create_booking(booking_details)
        return {"success": True, "booking_id": booking.id}
    except ValidationError as e:
        # Handle validation errors specifically
        await ctx.error(f"Booking validation failed: {str(e)}")
        return {"success": False, "error": "VALIDATION_ERROR", "details": str(e)}
    except APIConnectionError as e:
        # Handle API connection issues
        await ctx.error(f"Flight API connection error: {str(e)}")
        return {"success": False, "error": "CONNECTION_ERROR", "details": str(e)}
    except Exception as e:
        # Catch other unexpected errors
        await ctx.error(f"Unexpected error during flight booking: {str(e)}")
        return {"success": False, "error": "UNKNOWN_ERROR", "details": str(e)}
```

2. **Input Validation**

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date

class FlightBookingInput(BaseModel):
    passenger_name: str = Field(..., min_length=2)
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date
    return_date: Optional[date] = None

    @validator("return_date")
    def validate_return_date(cls, v, values):
        if v and "departure_date" in values and v < values["departure_date"]:
            raise ValueError("Return date must be after departure date")
        return v

@mcp.tool()
async def book_round_trip(booking: FlightBookingInput, ctx: Context):
    # The input is already validated by Pydantic
    # Implementation...
```

3. **Graceful Degradation**

```python
@mcp.tool()
async def get_flight_options(origin: str, destination: str, ctx: Context):
    try:
        # Try primary API
        options = await primary_flight_api.search(origin, destination)
        return options
    except Exception as e:
        await ctx.warning(f"Primary flight API failed: {str(e)}, trying backup...")
        try:
            # Fall back to secondary API
            options = await backup_flight_api.search(origin, destination)
            return options
        except Exception as backup_e:
            await ctx.error(f"Backup flight API also failed: {str(backup_e)}")
            # Return empty but valid response
            return {"options": [], "error": "ALL_APIS_FAILED"}
```
