"""
Router for flight management.

This module provides endpoints for searching and managing flights.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def flights_health():
    """Health check endpoint for flights."""
    return {"status": "ok", "service": "flights"}
