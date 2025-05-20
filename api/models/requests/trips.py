"""
Request models for trip endpoints.

This module defines Pydantic models for validating incoming trip-related requests.
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class TripDestination(BaseModel):
    """Model for a trip destination."""
    
    name: str = Field(..., description="Destination name")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    coordinates: Optional[Dict[str, float]] = Field(
        None, 
        description="Coordinates (latitude, longitude)",
    )
    arrival_date: Optional[date] = Field(None, description="Date of arrival")
    departure_date: Optional[date] = Field(None, description="Date of departure")
    duration_days: Optional[int] = Field(None, description="Duration in days")


class TripPreferences(BaseModel):
    """Model for trip preferences."""
    
    budget: Optional[Dict[str, Any]] = Field(
        None,
        description="Budget information",
        example={
            "total": 2000,
            "currency": "USD",
            "accommodation_budget": 1000,
            "transportation_budget": 600,
            "food_budget": 300,
            "activities_budget": 100,
        },
    )
    accommodation: Optional[Dict[str, Any]] = Field(
        None,
        description="Accommodation preferences",
        example={
            "type": "hotel",
            "min_rating": 3.5,
            "amenities": ["wifi", "breakfast"],
            "location_preference": "city_center",
        },
    )
    transportation: Optional[Dict[str, Any]] = Field(
        None,
        description="Transportation preferences",
        example={
            "flight_preferences": {
                "seat_class": "economy",
                "max_stops": 1,
                "preferred_airlines": [],
                "time_window": "flexible",
            },
            "local_transportation": ["public_transport", "walking"],
        },
    )
    activities: Optional[List[str]] = Field(
        None,
        description="Preferred activities",
        example=["sightseeing", "museums", "outdoor_activities"],
    )
    dietary_restrictions: Optional[List[str]] = Field(
        None,
        description="Dietary restrictions",
        example=["vegetarian", "gluten_free"],
    )
    accessibility_needs: Optional[List[str]] = Field(
        None,
        description="Accessibility needs",
        example=["wheelchair_accessible", "elevator_access"],
    )


class CreateTripRequest(BaseModel):
    """Request model for creating a trip."""
    
    title: str = Field(
        ..., 
        description="Trip title", 
        min_length=1, 
        max_length=100,
    )
    description: Optional[str] = Field(
        None, 
        description="Trip description",
        max_length=500,
    )
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destinations: List[TripDestination] = Field(
        ..., 
        description="Trip destinations",
        min_items=1,
    )
    preferences: Optional[TripPreferences] = Field(
        None, 
        description="Trip preferences",
    )
    
    @model_validator(mode="after")
    def validate_dates(self) -> "CreateTripRequest":
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class UpdateTripRequest(BaseModel):
    """Request model for updating a trip."""
    
    title: Optional[str] = Field(
        None, 
        description="Trip title", 
        min_length=1, 
        max_length=100,
    )
    description: Optional[str] = Field(
        None, 
        description="Trip description",
        max_length=500,
    )
    start_date: Optional[date] = Field(None, description="Trip start date")
    end_date: Optional[date] = Field(None, description="Trip end date")
    destinations: Optional[List[TripDestination]] = Field(
        None, 
        description="Trip destinations",
    )
    
    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateTripRequest":
        """Validate that end_date is after start_date if both are provided."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class TripPreferencesRequest(TripPreferences):
    """Request model for updating trip preferences."""
    pass