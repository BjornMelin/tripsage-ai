# TripSage Database Module

This module provides a complete database access layer for the TripSage application using the Repository pattern with support for multiple PostgreSQL providers (Supabase and Neon).

## Architecture

The database module follows a clean architecture design with these key components:

1. **Provider Layer**: Abstracts different database providers (Supabase, Neon)
2. **Client Layer**: Responsible for establishing and managing the database connection
3. **Models Layer**: Defines the data models with validation and business logic
4. **Repository Layer**: Abstracts database operations for each entity
5. **Migrations Layer**: Handles database schema changes and versioning

## Key Features

- **Provider Agnostic**: Support for both Supabase (production) and Neon (development)
- **Type Safety**: Strong typing with Pydantic for data validation
- **Repository Pattern**: Clean separation of concerns for data access
- **Connection Management**: Efficient connection handling with pooling
- **Error Handling**: Consistent error handling and logging
- **Migrations**: Versioned database schema changes

## Directory Structure

```plaintext
src/db/
├── __init__.py          # Package initialization
├── client.py            # Database client management
├── config.py            # Configuration handling
├── factory.py           # Provider factory
├── initialize.py        # Database initialization
├── migrations.py        # Migration runner
├── providers.py         # Database provider implementations
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

## Provider Configuration

### Using Supabase (Default - Production)

For Supabase (default for production environments), configure the following environment variables:

```env
DB_PROVIDER=supabase
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

### Using Neon (Development)

For Neon (recommended for development environments), configure:

```env
DB_PROVIDER=neon
NEON_CONNECTION_STRING=postgresql://username:password@host/database
```

The Neon connection string follows the standard PostgreSQL format, typically looking like:
`postgresql://your-username:your-password@your-project-id.g.neon.tech/neondb`

### Development Workflow with Neon

Neon is recommended for development environments due to its superior branching capabilities and unlimited free projects. Here's how to use it effectively:

1. **Create a Neon Account** at [neon.tech](https://neon.tech)
2. **Create a Project** in Neon's dashboard
3. **Set Up a Branch for Development**:
   ```bash
   # Create a new branch in Neon tied to your git branch
   neonctl branches create --name feature-xyz
   
   # Get connection details for the branch
   neonctl connection-string --branch feature-xyz
   ```
4. **Configure Environment**:
   ```bash
   # Update .env file with connection details
   DB_PROVIDER=neon
   NEON_CONNECTION_STRING=postgresql://username:password@host/database
   ```
5. **Run Migrations**:
   ```bash
   python -m src.db.migrations
   ```

#### Benefits of Neon for Development

- **Unlimited free projects** for development and testing
- **Superior branching capabilities** - instantly create isolated database environments
- **Per-developer database branches** - developers can work on isolated branches
- **Database branching tied to git workflow** - create a database branch for each git branch
- **No impact on production data** - work with a clean, isolated copy of the schema

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
succeeded, failed = await run_migrations()

# Dry run to preview migrations
succeeded, failed = await run_migrations(dry_run=True)

# Run up to a specific migration
succeeded, failed = await run_migrations(up_to="20250508_03_complex_relationship_tables.sql")
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

- **UserRepository**: User management and authentication
- **TripRepository**: Trip planning and management
- **FlightRepository**: Flight search and booking

## Database Providers

### Supabase Provider

Default provider for production environments:

- Integrated authentication system
- Real-time subscriptions
- Row-Level Security (RLS) policies
- Comprehensive UI tools for database management

### Neon Provider

Recommended provider for development environments:

- Unlimited free projects
- Superior branching capabilities
- PostgreSQL compatibility
- Instant database copies for testing

## Contributing

When adding a new entity:

1. Create a model class extending `BaseDBModel`
2. Create a repository class extending `BaseRepository`
3. Update `initialize.py` to register the model and repository
4. Create migration files as needed

When working with a new database branch:

1. Create a new branch in Neon dashboard or CLI
2. Update your `.env` file with the new connection string
3. Run migrations to set up the schema
4. Verify the connection with a simple query