"""
Router for accommodation management.

This module provides endpoints for searching and managing accommodations.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def accommodations_health():
    """Health check endpoint for accommodations."""
    return {"status": "ok", "service": "accommodations"}
