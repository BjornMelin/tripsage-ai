"""
Database configuration for TripSage.

This module contains the configuration settings for the Supabase connection.
"""

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    """
    Database configuration model.

    Attributes:
        supabase_url: The URL of the Supabase project.
        supabase_anon_key: The anonymous key for the Supabase project.
        supabase_service_role_key: The service role key for the Supabase project (optional).
    """

    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_anon_key: SecretStr = Field(env="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr = Field(
        env="SUPABASE_SERVICE_ROLE_KEY", default=None
    )


# Instance for easy importing
config = DatabaseConfig(
    supabase_url=os.getenv("SUPABASE_URL", ""),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
    supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
)
