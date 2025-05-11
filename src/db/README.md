# TripSage Database Module

This module provides a complete database access layer for the TripSage application using the Repository pattern with Supabase.

## Architecture

The database module follows a clean architecture design with these key components:

1. **Client Layer**: Responsible for establishing and managing the database connection
2. **Models Layer**: Defines the data models with validation and business logic
3. **Repository Layer**: Abstracts database operations for each entity
4. **Migrations Layer**: Handles database schema changes and versioning

## Key Features

- **Type Safety**: Strong typing with Pydantic for data validation
- **Repository Pattern**: Clean separation of concerns for data access
- **Connection Management**: Efficient connection handling with pooling
- **Error Handling**: Consistent error handling and logging
- **Migrations**: Versioned database schema changes

## Directory Structure

```plaintext
src/db/
├── __init__.py          # Package initialization
├── client.py            # Supabase client management
├── config.py            # Configuration handling
├── initialize.py        # Database initialization
├── migrations.py        # Migration runner
├── models/              # Data models
│   ├── __init__.py
│   ├── base.py          # Base model class
│   ├── flight.py        # Flight model
│   ├── trip.py          # Trip model
│   └── user.py          # User model
└── repositories/        # Data access repositories
    ├── __init__.py
    ├── base.py          # Base repository class
    ├── flight.py        # Flight repository
    ├── trip.py          # Trip repository
    └── user.py          # User repository
```

## Usage Examples

### Initialization

```python
from src.db.initialize import initialize_database

# Initialize the database
await initialize_database()
```

### Using Repositories

```python
from src.db.repositories.user import UserRepository
from src.db.models.user import User

# Create a repository
user_repo = UserRepository()

# Create a new user
new_user = User(
    email="user@example.com",
    name="John Doe",
    password_hash="hashed_password"
)
created_user = await user_repo.create(new_user)

# Get a user by ID
user = await user_repo.get_by_id(1)

# Get a user by email
user = await user_repo.get_by_email("user@example.com")

# Update a user
user.name = "Jane Doe"
updated_user = await user_repo.update(user)

# Delete a user
success = await user_repo.delete(user)
```

### Running Migrations

```python
from src.db.migrations import run_migrations

# Run all pending migrations
succeeded, failed = run_migrations()

# Dry run to preview migrations
succeeded, failed = run_migrations(dry_run=True)

# Run up to a specific migration
succeeded, failed = run_migrations(up_to="20250508_03_complex_relationship_tables.sql")
```

## Configuration

The module is configured through environment variables:

```plaintext
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

## Models

### BaseDBModel

Base class for all models with common functionality:

- ID and timestamp fields
- Validation methods
- Serialization/deserialization
- Type validation

### User Model

Represents a user in the system:

- Identity management (email, name)
- Authentication (password_hash)
- Authorization (is_admin)
- Account status (is_disabled)
- Preferences management

### Trip Model

Represents a travel trip:

- Trip details (name, dates, destination)
- Budget management
- Travel preferences
- Enum-based status tracking

### Flight Model

Represents a flight option:

- Route information (origin, destination)
- Schedule information (departure/arrival times)
- Price tracking
- Booking status management

## Repositories

### BaseRepository

Generic repository with common database operations:

- Create, read, update, delete (CRUD)
- Query operations
- Transaction handling
- Error management

### Specialized Repositories

Entity-specific repositories with specialized methods:

- **UserRepository**: User management
- **TripRepository**: Trip planning and management
- **FlightRepository**: Flight search and booking

## Contributing

When adding a new entity:

1. Create a model class extending `BaseDBModel`
2. Create a repository class extending `BaseRepository`
3. Update `initialize.py` to register the model and repository
4. Create migration files as needed
