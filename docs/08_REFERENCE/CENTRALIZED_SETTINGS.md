# TripSage Centralized Settings System Guide

This document provides an overview and guide to the centralized configuration system used in the TripSage application, based on Pydantic's `BaseSettings`.

## 1. Overview

TripSage's approach to configuration:

- **Single Source of Truth**: All settings via Pydantic models.
- **Type Safety and Validation**: Ensures correctness at startup.
- **Environment Variable Overrides**.
- **`.env` File Support**.
- **SecretStr** for sensitive data.

## 2. Key Benefits

- Simplified environment management.
- Clear default values and field descriptions.
- Automatic validation for complex data types.

## 3. Core Settings Structure

```python
# src/utils/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class DatabasePrimaryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_DB_PRIMARY_')
    url: str = "postgresql://user:pass@localhost:5432/tripsage"
    pool_size: int = 5

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    environment: str = "development"
    debug: bool = False
    db: DatabasePrimaryConfig = DatabasePrimaryConfig()

try:
    settings = AppSettings()
except Exception as e:
    # Log or handle error
    raise
```

## 4. Usage in Application Code

```python
from src.utils.config import settings

def some_function():
    if settings.debug:
        ...
    db_url = settings.db.url
```

## 5. Environment Variables and `.env` File

- `env_file='.env'` in the `model_config` handles loading from `.env`.
- Override with actual environment variables in production.

## 6. Extending Settings

- Add new fields to `AppSettings` or create nested models.
- Provide default values or rely on `.env`/env variables.

## 7. Best Practices

- Use `SecretStr` for API keys/secrets.
- `extra='forbid'` to avoid typos in env var names.
- Add validation for environment-specific constraints.

Centralizing settings ensures a robust, maintainable config system for TripSage.
