"""
Database configuration for TripSage.

This module contains the configuration settings for the database connection.
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
        supabase_service_role_key: The service role key for the Supabase project.
        database_url: Direct PostgreSQL connection string (optional).
        use_ssl: Whether to use SSL for the database connection.
        pool_size: Connection pool size.
        max_overflow: Maximum number of connections to overflow from the pool.
    """

    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_anon_key: SecretStr = Field(env="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr = Field(
        env="SUPABASE_SERVICE_ROLE_KEY", default=None
    )
    database_url: str = Field(env="DATABASE_URL", default=None)
    use_ssl: bool = Field(env="DATABASE_USE_SSL", default=True)
    pool_size: int = Field(env="DATABASE_POOL_SIZE", default=10)
    max_overflow: int = Field(env="DATABASE_MAX_OVERFLOW", default=5)


# Instance for easy importing
config = DatabaseConfig(
    supabase_url=os.getenv("SUPABASE_URL", ""),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
    supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    database_url=os.getenv("DATABASE_URL"),
    use_ssl=os.getenv("DATABASE_USE_SSL", "True").lower() in ("true", "1", "t"),
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "5")),
)
