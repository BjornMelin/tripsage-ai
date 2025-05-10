"""
TripSage Database Module.

This module provides access to the Supabase database for the TripSage application.
"""

# Expose key components at the module level
from src.db.client import create_supabase_client, get_supabase_client, reset_client
from src.db.config import DatabaseConfig, config
from src.db.initialize import initialize_database, close_database_connection
from src.db.migrations import run_migrations

# Import models
from src.db.models import BaseDBModel, User, Trip, TripStatus, TripType

# Import repositories
from src.db.repositories import BaseRepository, UserRepository, TripRepository

__all__ = [
    # Client and configuration
    'get_supabase_client',
    'create_supabase_client',
    'reset_client',
    'DatabaseConfig',
    'config',
    
    # Initialization and management
    'initialize_database',
    'close_database_connection',
    'run_migrations',
    
    # Models
    'BaseDBModel',
    'User',
    'Trip',
    'TripStatus',
    'TripType',
    
    # Repositories
    'BaseRepository',
    'UserRepository',
    'TripRepository',
]