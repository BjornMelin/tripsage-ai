"""
Router for destination management.

This module provides endpoints for searching and managing destinations.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def destinations_health():
    """Health check endpoint for destinations."""
    return {"status": "ok", "service": "destinations"}
