"""
Utility functions for scoring flight options and analyzing prices.
"""

from typing import Any, Dict, Optional

from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)


def calculate_flight_value_score(offer_dict: Dict[str, Any]) -> float:
    """Calculate a simple value score for a flight offer. Lower is better."""
    price = offer_dict.get("total_amount", float("inf"))
    if price == float("inf"):
        return price  # Don't score offers without a price

    durations = []
    stops = 0
    for slice_data in offer_dict.get("slices", []):
        duration_minutes = 0
        num_segments = len(slice_data.get("segments", []))
        if num_segments > 0:
            stops += num_segments - 1
        for segment_data in slice_data.get("segments", []):
            segment_duration = segment_data.get("duration_minutes")
            if isinstance(segment_duration, (int, float)):
                duration_minutes += segment_duration
            # Handle cases where duration might be missing or not numeric
            elif isinstance(segment_duration, str):
                try:
                    # Attempt to parse duration string (e.g., "PT2H30M") if needed
                    # This ex assumes duration_minutes is already provided correctly
                    pass
                except ValueError:
                    logger.warning(f"Could not parse duration: {segment_duration}")

        if duration_minutes > 0:
            durations.append(duration_minutes)

    avg_duration = sum(durations) / len(durations) if durations else 0

    # Simple score: price + moderate penalty for duration + higher penalty for stops
    score = price + (avg_duration * 0.5) + (stops * 100)
    return score


def calculate_price_insights(
    price_history_data: Dict[str, Any], current_lowest_price: Optional[float]
) -> Dict[str, Any]:
    """Calculate pricing insights based on historical data and current price.

    Args:
        price_history_data: Dictionary containing historical price data
            (e.g., from client.get_flight_prices)
        current_lowest_price: The current lowest price found for the route, if available

    Returns:
        A dictionary containing calculated insights like trends,
            comparisons, and recommendations.
    """
    insights = {
        "historical": {},
        "analysis": {},
        "recommendation": "unavailable",
    }

    prices = price_history_data.get("prices")

    if not prices or not isinstance(prices, list) or len(prices) == 0:
        insights["message"] = "Insufficient price history available for insights."
        if current_lowest_price is not None:
            insights["recommendation"] = "book_if_needed"  # Can't compare historically
        else:
            insights["recommendation"] = "unavailable"
        return insights

    # Calculate historical stats
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)
    insights["historical"] = {
        "average": round(avg_price, 2),
        "minimum": round(min_price, 2),
        "maximum": round(max_price, 2),
        "count": len(prices),
    }

    # Analyze trends (simple trend check)
    trend = "stable"
    if len(prices) >= 3:
        # Compare last price to average of previous prices
        last_price = prices[-1]
        prev_avg = (
            sum(prices[:-1]) / (len(prices) - 1) if len(prices) > 1 else prices[0]
        )
        if last_price < prev_avg * 0.95:  # More than 5% drop
            trend = "decreasing"
        elif last_price > prev_avg * 1.05:  # More than 5% rise
            trend = "increasing"
    insights["analysis"]["trend"] = trend

    # Generate recommendation based on current lowest price vs history
    recommendation = "monitor"  # Default
    if current_lowest_price is not None:
        # Break long lines for readability and linting
        vs_avg_percent = (
            ((current_lowest_price / avg_price) - 1) * 100 if avg_price > 0 else 0
        )
        vs_min_percent = (
            ((current_lowest_price / min_price) - 1) * 100 if min_price > 0 else 0
        )
        insights["analysis"]["vs_average_percent"] = round(vs_avg_percent, 1)
        insights["analysis"]["vs_minimum_percent"] = round(vs_min_percent, 1)

        if current_lowest_price <= min_price * 1.05:  # Within 5% of historical min
            recommendation = "book_now"
        elif current_lowest_price <= avg_price * 0.9:  # More than 10% below average
            recommendation = "good_price"
        elif trend == "increasing" and current_lowest_price <= avg_price * 1.1:
            recommendation = "consider_booking_soon"
        elif current_lowest_price > max_price * 1.05:  # Far above historical max
            recommendation = "wait_for_deal"
    else:
        recommendation = "no_current_price"  # If search failed or no offers

    insights["recommendation"] = recommendation

    return insights
