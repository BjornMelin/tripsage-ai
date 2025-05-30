"""
External API integration services.

NOTE: Many services have been migrated to tripsage_core.services.external_apis
for better integration with Core settings and exception handling.
"""

from .file_processor import FileProcessor
from .flights_service import DuffelFlightsService as FlightsService

__all__ = [
    "FileProcessor",
    "FlightsService",
]
