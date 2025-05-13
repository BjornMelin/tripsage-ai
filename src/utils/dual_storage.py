"""
Dual storage strategy for TripSage.

This module provides direct access to the TripStorageService, which implements
the dual storage strategy where structured data is stored in Supabase and
relationships/unstructured data are stored in Neo4j via the Memory MCP.
"""

from src.utils.logging import get_module_logger
from src.utils.trip_storage_service import TripStorageService

logger = get_module_logger(__name__)

# Create service instance - the only thing needed from this module
trip_service = TripStorageService()
