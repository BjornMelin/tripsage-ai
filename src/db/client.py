"""
Supabase client implementation for TripSage.

This module provides Supabase client initialization and connection management.
"""

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from src.db.config import config
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Load environment variables
load_dotenv()

# Global client instance
_supabase_client: Optional[Client] = None


def create_supabase_client(
    url: Optional[str] = None,
    key: Optional[str] = None,
    use_service_key: bool = False,
    **options: Dict[str, Any],
) -> Client:
    """
    Create a new Supabase client with the provided URL and key.

    Args:
        url: The URL of the Supabase project. Defaults to SUPABASE_URL env var.
        key: The API key for the Supabase project. Defaults to SUPABASE_ANON_KEY env var,
             or SUPABASE_SERVICE_ROLE_KEY if use_service_key is True.
        use_service_key: Whether to use the service role key instead of the anon key.
        **options: Additional options to pass to the Supabase client.

    Returns:
        A Supabase client instance.

    Raises:
        ValueError: If the URL or key is not provided and not available in the environment.
    """
    # Use provided values or fall back to config
    final_url = url or config.supabase_url

    if not final_url:
        raise ValueError(
            "Supabase URL not provided and not found in environment variables"
        )

    if use_service_key:
        final_key = key or (
            config.supabase_service_role_key.get_secret_value()
            if config.supabase_service_role_key
            else None
        )
        if not final_key:
            raise ValueError(
                "Supabase service role key not provided and not found in environment variables"
            )
    else:
        final_key = key or (
            config.supabase_anon_key.get_secret_value()
            if config.supabase_anon_key
            else None
        )
        if not final_key:
            raise ValueError(
                "Supabase anon key not provided and not found in environment variables"
            )

    try:
        return create_client(final_url, final_key, **options)
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        raise


def get_supabase_client(use_service_key: bool = False) -> Client:
    """
    Get or create a Supabase client singleton instance.

    Args:
        use_service_key: Whether to use the service role key instead of the anon key.

    Returns:
        A Supabase client instance.
    """
    global _supabase_client

    if _supabase_client is None:
        try:
            _supabase_client = create_supabase_client(use_service_key=use_service_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    return _supabase_client


def reset_client() -> None:
    """Reset the global Supabase client, forcing it to be reinitialized on next use."""
    global _supabase_client
    _supabase_client = None
    logger.debug("Supabase client has been reset")
