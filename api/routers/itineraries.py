"""
Router for itinerary management.

This module provides endpoints for creating and managing itineraries.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def itineraries_health():
    """Health check endpoint for itineraries."""
    return {"status": "ok", "service": "itineraries"}
