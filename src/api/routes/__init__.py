"""
Routes package for the TripSage API.

This package contains the route modules for the TripSage API.
"""

from src.api.routes import admin, auth, flights, trips, users

# Define which modules should be exposed
__all__ = ["admin", "auth", "flights", "trips", "users"]
