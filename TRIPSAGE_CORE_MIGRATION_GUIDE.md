# TripSage Core Migration Guide

## Overview

This guide helps you migrate from the old scattered configuration and model structure to the new centralized `tripsage_core` module introduced in PR #198.

## What Changed

### New Structure

```plaintext
tripsage_core/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── base_app_settings.py     # CoreAppSettings
├── exceptions/
│   ├── __init__.py
│   └── exceptions.py            # Centralized exception system
├── models/
│   ├── __init__.py
│   ├── base_core_model.py       # TripSageModel, TripSageDomainModel, etc.
│   ├── domain/                  # Core business entities
│   │   ├── __init__.py
│   │   ├── accommodation.py
│   │   ├── flight.py
│   │   └── memory.py
│   └── db/                      # Database models
│       └── ...
└── services/                    # Core services (future)
```

### Key Changes

1. **Configuration Management**: `AppSettings` → `CoreAppSettings`
2. **Exception System**: Unified hierarchy with `CoreTripSageError` base
3. **Model Organization**: Domain models moved to `tripsage_core/models/domain/`
4. **Base Models**: Centralized in `tripsage_core/models/base_core_model.py`

## Migration Steps

### 1. Configuration (High Priority)

#### Old Way

```python
from tripsage.config.app_settings import AppSettings, settings
```

#### New Way

```python
from tripsage_core.config.base_app_settings import CoreAppSettings, get_settings

# Use the new settings
settings = get_settings()
```

### 2. Exception Handling (High Priority)

#### Old Way

```python
from tripsage.utils.error_handling import TripSageError, ValidationError
```

#### New Way

```python
from tripsage_core.exceptions.exceptions import (
    CoreTripSageError,
    CoreValidationError,
    create_validation_error  # Factory function
)
```

### 3. Base Models (Medium Priority)

#### Old Way

```python
from tripsage.models.base import TripSageModel
```

#### New Way

```python
from tripsage_core.models.base_core_model import (
    TripSageModel,           # For general use
    TripSageDomainModel,     # For domain entities
    TripSageDBModel          # For database models
)
```

### 4. Domain Models (Medium Priority)

#### Old Way

```python
from tripsage.models.accommodation import AccommodationListing
from tripsage.models.flight import FlightOffer
from tripsage.models.memory import TravelMemory
```

#### New Way

```python
from tripsage_core.models.domain import (
    AccommodationListing,
    FlightOffer,
    TravelMemory
)
```

### 5. Database Models (Low Priority)

Database models have moved but backwards compatibility is maintained.

#### New Location

```python
from tripsage_core.models.db import User, Trip, ApiKeyDB
```

## Environment Variables

### New Core Settings

The `CoreAppSettings` class provides comprehensive configuration management:

```python
# Core application settings
APP_NAME=TripSage
ENVIRONMENT=development  # development, testing, staging, production
DEBUG=false
LOG_LEVEL=INFO

# Security (REQUIRED in production)
JWT_SECRET_KEY=your-secret-key-here
API_KEY_MASTER_SECRET=master-secret-for-byok

# Core API keys
OPENAI_API_KEY=your-openai-key
GOOGLE_MAPS_API_KEY=your-google-maps-key
DUFFEL_API_KEY=your-duffel-key
OPENWEATHERMAP_API_KEY=your-weather-key

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Cache
DRAGONFLY_URL=redis://localhost:6379/0

# External services
CRAWL4AI_API_URL=http://localhost:8000/api
```

### Configuration Validation

The new system includes production-specific validation:

```python
from tripsage_core.config.base_app_settings import init_settings

# This will validate all critical settings
settings = init_settings()

# Check for any configuration errors
errors = settings.validate_critical_settings()
if errors:
    for error in errors:
        print(f"Configuration error: {error}")
```

## Backwards Compatibility

### Automatic Migration

The new system maintains full backwards compatibility:

- Old import paths continue to work with deprecation warnings
- Existing code functions without modification
- Gradual migration is supported

### Deprecation Warnings

You'll see warnings like:

```
DeprecationWarning: tripsage.models.base is deprecated. 
Use tripsage_core.models.base_core_model instead.
```

These are safe to ignore during migration but should be addressed over time.

## Testing Considerations

### Known Issue: Pytest Configuration

There's currently a pytest configuration issue with importing `tripsage_core` modules in tests. The functionality works correctly (as verified by standalone test scripts), but pytest needs additional configuration.

**Workaround**: Tests can be run via direct Python scripts for now.

**Fix in Progress**: Pytest configuration will be updated in a follow-up commit.

## Production Deployment

### Required Changes for Production

1. **Update secrets** - Change default JWT and API key secrets
2. **Set environment** - Use `ENVIRONMENT=production`
3. **Disable debug** - Ensure `DEBUG=false`
4. **Configure external services** - Use production URLs for DragonflyDB and Crawl4AI

### Validation

Run this before deployment:

```python
from tripsage_core.config.base_app_settings import CoreAppSettings

settings = CoreAppSettings()
if settings.is_production():
    errors = settings.validate_critical_settings()
    if errors:
        raise ValueError(f"Production validation failed: {errors}")
```

## Benefits of Migration

### Immediate Benefits

- **Centralized configuration** - All settings in one place
- **Enhanced security** - Proper secret management
- **Better validation** - Environment-specific checks
- **Improved organization** - Clear separation of concerns

### Long-term Benefits

- **Scalability** - Easier to add new configuration options
- **Maintainability** - Centralized error handling and models
- **Testing** - Better isolation and mocking capabilities
- **Performance** - Optimized settings caching

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're using the new import paths
2. **Configuration Errors**: Check environment variables are set correctly
3. **Deprecation Warnings**: Update imports to new paths
4. **Test Issues**: Use direct Python scripts for now

### Getting Help

- Check the comprehensive test verification script results
- Review the detailed PR #198 AI review
- Examine the `tripsage_core` source code for examples

## Timeline

- **Immediate**: Update configuration imports in critical code paths
- **Next Sprint**: Migrate exception handling
- **Future**: Gradually update all model imports
- **Cleanup**: Remove deprecated imports after full migration

## Verification

Run this script to verify your migration:

```python
# Test basic imports
from tripsage_core.config.base_app_settings import CoreAppSettings
from tripsage_core.exceptions.exceptions import CoreTripSageError
from tripsage_core.models.domain import AccommodationListing

# Test configuration
settings = CoreAppSettings(_env_file=None)
print(f"✅ Settings loaded: {settings.app_name}")

# Test exceptions
error = CoreTripSageError("Test error")
print(f"✅ Exception system: {error.message}")

# Test domain models
listing = AccommodationListing(
    id="test",
    name="Test Hotel",
    property_type="hotel",
    location={"city": "Test", "country": "Test"},
    price_per_night=100.0,
    currency="USD",
    max_guests=2
)
print(f"✅ Domain models: {listing.name}")

print("🎉 Migration verification complete!")
```

## Conclusion

The `tripsage_core` module provides a solid foundation for the TripSage application with improved security, organization, and maintainability. The migration can be done gradually thanks to full backwards compatibility.
