"""Utilities for analysing travel-related memory context."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, cast

from tripsage_core.types import JSONValue


JSONDict = dict[str, JSONValue]
MemoryEntry = JSONDict
MemoryContext = dict[str, list[MemoryEntry]]


def coerce_json_value(value: Any) -> JSONValue:
    """Convert arbitrary objects into a JSON-serialisable value."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        sequence = cast(Iterable[Any], value)
        return [coerce_json_value(item) for item in sequence]
    if isinstance(value, Mapping):
        mapping = cast(Mapping[Any, Any], value)
        return {str(key): coerce_json_value(item) for key, item in mapping.items()}
    return str(value)


def sanitize_memory_entry(entry: Mapping[str, Any]) -> MemoryEntry:
    """Normalise raw memory entries into JSON-compatible dictionaries."""
    return {str(key): coerce_json_value(value) for key, value in entry.items()}


def entry_text(entry: MemoryEntry) -> str:
    """Extract the textual memory content."""
    raw = entry.get("memory")
    return str(raw) if raw is not None else ""


def analyze_destinations(context: MemoryContext) -> dict[str, Any]:
    """Analyse destination preferences from the memory context."""
    tracked_destinations = {
        "Japan",
        "France",
        "Italy",
        "Spain",
        "Thailand",
        "USA",
        "UK",
    }
    destinations: list[str] = []
    for entry in context.get("past_trips", []) + context.get("saved_destinations", []):
        for word in entry_text(entry).lower().split():
            candidate = word.capitalize()
            if candidate in tracked_destinations:
                destinations.append(candidate)

    unique = sorted(set(destinations))
    return {"most_visited": unique, "destination_count": len(unique)}


def analyze_budgets(context: MemoryContext) -> dict[str, Any]:
    """Extract budget insights from memory entries."""
    import re

    budgets: list[int] = []
    for entry in context.get("budget_patterns", []):
        for amount in re.findall(r"\$(\d+)", entry_text(entry)):
            try:
                budgets.append(int(amount))
            except ValueError:
                continue

    if not budgets:
        return {"budget_info": "No budget data available"}

    return {
        "average_budget": sum(budgets) / len(budgets),
        "max_budget": max(budgets),
        "min_budget": min(budgets),
    }


def analyze_frequency(context: MemoryContext) -> dict[str, Any]:
    """Summarise travel frequency based on past trip memories."""
    trips = context.get("past_trips", [])
    return {
        "total_trips": len(trips),
        "estimated_frequency": "Regular" if len(trips) > 5 else "Occasional",
    }


def analyze_activities(context: MemoryContext) -> dict[str, Any]:
    """Identify preferred activities from memory entries."""
    activity_keywords = [
        "museum",
        "beach",
        "hiking",
        "shopping",
        "dining",
        "nightlife",
        "culture",
    ]
    activities: list[str] = []
    relevant_entries = context.get("activity_preferences", []) + context.get(
        "preferences", []
    )
    for entry in relevant_entries:
        content = entry_text(entry).lower()
        for keyword in activity_keywords:
            if keyword in content:
                activities.extend(keyword)

    unique = sorted(set(activities))
    return {
        "preferred_activities": unique,
        "activity_style": "Cultural"
        if "museum" in activities or "culture" in activities
        else "Adventure",
    }


def analyze_travel_style(context: MemoryContext) -> dict[str, Any]:
    """Determine travel styles inferred from memory entries."""
    style_indicators = {
        "luxury": ["luxury", "expensive", "high-end", "premium"],
        "budget": ["budget", "cheap", "affordable", "backpack"],
        "family": ["family", "kids", "children"],
        "solo": ["solo", "alone", "independent"],
        "group": ["group", "friends", "together"],
    }

    all_content = " ".join(
        entry_text(entry).lower() for bucket in context.values() for entry in bucket
    )

    detected_styles: list[str] = []
    for style, keywords in style_indicators.items():
        if any(keyword in all_content for keyword in keywords):
            detected_styles.append(style)

    return {
        "travel_styles": detected_styles,
        "primary_style": detected_styles[0] if detected_styles else "general",
    }


def derive_travel_insights(context: MemoryContext) -> dict[str, Any]:
    """Derive aggregate travel insights from memory buckets."""
    return {
        "preferred_destinations": analyze_destinations(context),
        "budget_range": analyze_budgets(context),
        "travel_frequency": analyze_frequency(context),
        "preferred_activities": analyze_activities(context),
        "travel_style": analyze_travel_style(context),
    }


def generate_context_summary(insights: dict[str, Any]) -> str:
    """Render a human-readable summary from insight data."""
    summary_parts: list[str] = []

    destinations = insights.get("preferred_destinations", {}).get("most_visited", [])
    if destinations:
        summary_parts.append(f"Frequently travels to: {', '.join(destinations[:3])}")

    travel_style = insights.get("travel_style", {}).get("primary_style")
    if travel_style and travel_style != "general":
        summary_parts.append(f"Travel style: {travel_style}")

    budget_info = insights.get("budget_range", {})
    if "average_budget" in budget_info:
        avg_budget = budget_info["average_budget"]
        summary_parts.append(f"Average budget: ${avg_budget:.0f}")

    activities = insights.get("preferred_activities", {}).get(
        "preferred_activities", []
    )
    if activities:
        summary_parts.append(f"Enjoys: {', '.join(activities[:3])}")

    return (
        ". ".join(summary_parts)
        if summary_parts
        else "New user with limited travel history"
    )


__all__ = [
    "JSONDict",
    "MemoryContext",
    "MemoryEntry",
    "coerce_json_value",
    "derive_travel_insights",
    "entry_text",
    "generate_context_summary",
    "sanitize_memory_entry",
]
