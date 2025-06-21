#!/usr/bin/env python
"""
TripSage Database Connection Verification Script

This script verifies the connection to the Supabase database
and checks that the required tables exist.

Usage: python verify_connection.py
"""

import asyncio
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.client import get_supabase_client
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Tables that should exist
REQUIRED_TABLES = [
    "users",
    "trips",
    "flights",
    "accommodations",
    "transportation",
    "itinerary_items",
    "search_parameters",
    "price_history",
    "trip_notes",
    "saved_options",
    "trip_comparison",
]


async def verify_connection() -> None:
    """
    Verify the connection to the Supabase database and check that required tables exist.
    """
    print("Connecting to Supabase...")

    try:
        # Get a Supabase client
        supabase = get_supabase_client()

        # Test a simple query to verify connection
        _response = supabase.table("trips").select("id").limit(1).execute()

        print("✅ Successfully connected to Supabase!")

        # Verify tables
        print("\nChecking required tables:")

        # Get list of tables using system schema
        table_response = None
        try:
            table_response = supabase.rpc("get_tables").execute()
        except Exception:
            print("Unable to list tables using RPC. Using alternative method...")

        if table_response and table_response.data:
            # If we have table list, check required tables
            table_names = [t["table_name"] for t in table_response.data]

            for table in REQUIRED_TABLES:
                if table in table_names:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"❌ Table '{table}' does not exist")
        else:
            # Alternative method to check tables individually
            for table in REQUIRED_TABLES:
                try:
                    _test_response = supabase.table(table).select("id").limit(1).execute()
                    print(f"✅ Table '{table}' exists")
                except Exception as e:
                    if "42P01" in str(e):  # PostgreSQL error code for table does not exist
                        print(f"❌ Table '{table}' does not exist")
                    else:
                        print(f"❓ Could not verify table '{table}': {str(e)}")

        print("\nDatabase verification complete!")
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_connection())
