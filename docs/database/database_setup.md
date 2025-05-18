# TripSage Database Setup

This document provides detailed instructions for setting up and using the TripSage Supabase database.

## Overview

TripSage uses a PostgreSQL database hosted on Supabase for storing all travel planning data. The database is organized with a relational schema that captures trips, flights, accommodations, transportation options, and other travel-related information.

## Project Information

- **Project Name:** tripsage_planner
- **Region:** us-east-2
- **Database:** PostgreSQL 15.8

## Setup Instructions

### 1. Environment Configuration

Add the following environment variables to your local development environment:

```bash
export SUPABASE_URL="https://your-project-id.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
```

For local development, create a `.env` file in the project root with these variables. **Important:** Do not commit this file to version control.

### 2. Applying Migrations

The migration scripts in the `/migrations` directory should be applied in numerical order:

```bash
# Connect to your Supabase database
cd migrations

# Run each migration file in order
psql [CONNECTION_STRING] -f 20250508_01_initial_schema_core_tables.sql
psql [CONNECTION_STRING] -f 20250508_02_dependent_tables.sql
psql [CONNECTION_STRING] -f 20250508_03_complex_relationship_tables.sql
psql [CONNECTION_STRING] -f 20250508_04_indexes.sql
```

Alternatively, you can apply migrations through the Supabase dashboard:

1. Navigate to your project in the [Supabase Dashboard](https://app.supabase.io)
2. Go to the SQL Editor
3. Copy and paste each migration file and execute them in order

### 3. Creating a New Supabase Project

If you need to create a new Supabase project:

1. Go to [Supabase Dashboard](https://app.supabase.io)
2. Click "New Project"
3. Enter "tripsage_planner" as the name
4. Select your organization and region (preferably us-east-1)
5. Set up a secure database password
6. Click "Create Project"

### 4. Verification

To verify the database setup, you can use the provided verification script:

```bash
node scripts/verification/verify_connection.js
```

Or manually run these SQL queries:

```sql
-- Check if tables were created successfully
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'idx_%';
```

## Database Schema

### Core Tables

#### `users`

Stores information about users of the TripSage system.

| Column           | Type                     | Description              |
| ---------------- | ------------------------ | ------------------------ |
| id               | BIGINT                   | Primary key              |
| name             | TEXT                     | User's name              |
| email            | TEXT                     | User's email             |
| preferences_json | JSONB                    | User preferences as JSON |
| created_at       | TIMESTAMP WITH TIME ZONE | Creation timestamp       |
| updated_at       | TIMESTAMP WITH TIME ZONE | Update timestamp         |

#### `trips`

The central table that stores trip information.

| Column      | Type                     | Description                                             |
| ----------- | ------------------------ | ------------------------------------------------------- |
| id          | BIGINT                   | Primary key                                             |
| name        | TEXT                     | Trip name/title                                         |
| start_date  | DATE                     | Trip start date                                         |
| end_date    | DATE                     | Trip end date                                           |
| destination | TEXT                     | Primary destination                                     |
| budget      | NUMERIC                  | Total budget                                            |
| travelers   | INTEGER                  | Number of travelers                                     |
| status      | TEXT                     | Trip status (planning, booked, completed, canceled)     |
| trip_type   | TEXT                     | Type of trip (leisure, business, family, solo, other)   |
| flexibility | JSONB                    | Flexibility parameters (e.g., date range, budget range) |
| created_at  | TIMESTAMP WITH TIME ZONE | Creation timestamp                                      |
| updated_at  | TIMESTAMP WITH TIME ZONE | Update timestamp                                        |

### Travel Options Tables

#### `flights`

Stores flight options for trips.

| Column           | Type                     | Description                              |
| ---------------- | ------------------------ | ---------------------------------------- |
| id               | BIGINT                   | Primary key                              |
| trip_id          | BIGINT                   | Reference to trips table                 |
| origin           | TEXT                     | Origin airport/city                      |
| destination      | TEXT                     | Destination airport/city                 |
| airline          | TEXT                     | Airline name                             |
| departure_time   | TIMESTAMP WITH TIME ZONE | Departure time                           |
| arrival_time     | TIMESTAMP WITH TIME ZONE | Arrival time                             |
| price            | NUMERIC                  | Flight price                             |
| booking_link     | TEXT                     | Booking URL                              |
| segment_number   | INTEGER                  | Segment number for multi-leg flights     |
| search_timestamp | TIMESTAMP WITH TIME ZONE | When the flight was found                |
| booking_status   | TEXT                     | Status (viewed, saved, booked, canceled) |
| data_source      | TEXT                     | Data source (API provider)               |

#### `accommodations`

Stores accommodation options for trips.

| Column              | Type                     | Description                              |
| ------------------- | ------------------------ | ---------------------------------------- |
| id                  | BIGINT                   | Primary key                              |
| trip_id             | BIGINT                   | Reference to trips table                 |
| name                | TEXT                     | Accommodation name                       |
| type                | TEXT                     | Type (hotel, apartment, hostel, etc.)    |
| check_in            | DATE                     | Check-in date                            |
| check_out           | DATE                     | Check-out date                           |
| price_per_night     | NUMERIC                  | Price per night                          |
| total_price         | NUMERIC                  | Total price for the stay                 |
| location            | TEXT                     | Location                                 |
| rating              | NUMERIC                  | Rating (0-5 scale)                       |
| amenities           | JSONB                    | Amenities as JSON                        |
| booking_link        | TEXT                     | Booking URL                              |
| search_timestamp    | TIMESTAMP WITH TIME ZONE | When the accommodation was found         |
| booking_status      | TEXT                     | Status (viewed, saved, booked, canceled) |
| cancellation_policy | TEXT                     | Cancellation policy                      |
| distance_to_center  | NUMERIC                  | Distance to center                       |
| neighborhood        | TEXT                     | Neighborhood                             |

#### `transportation`

Stores transportation options for trips.

| Column         | Type                     | Description                                   |
| -------------- | ------------------------ | --------------------------------------------- |
| id             | BIGINT                   | Primary key                                   |
| trip_id        | BIGINT                   | Reference to trips table                      |
| type           | TEXT                     | Type (car_rental, public_transit, taxi, etc.) |
| provider       | TEXT                     | Provider name                                 |
| pickup_date    | TIMESTAMP WITH TIME ZONE | Pickup date/time                              |
| dropoff_date   | TIMESTAMP WITH TIME ZONE | Dropoff date/time                             |
| price          | NUMERIC                  | Price                                         |
| notes          | TEXT                     | Additional notes                              |
| booking_status | TEXT                     | Status (viewed, saved, booked, canceled)      |

### Planning and Organization Tables

#### `itinerary_items`

Stores items in a trip itinerary.

| Column      | Type    | Description                            |
| ----------- | ------- | -------------------------------------- |
| id          | BIGINT  | Primary key                            |
| trip_id     | BIGINT  | Reference to trips table               |
| type        | TEXT    | Type (activity, meal, transport, etc.) |
| date        | DATE    | Date of the item                       |
| time        | TIME    | Time of the item                       |
| description | TEXT    | Description                            |
| cost        | NUMERIC | Cost of the item                       |
| notes       | TEXT    | Additional notes                       |

#### `search_parameters`

Stores search parameters used for finding travel options.

| Column         | Type                     | Description               |
| -------------- | ------------------------ | ------------------------- |
| id             | BIGINT                   | Primary key               |
| trip_id        | BIGINT                   | Reference to trips table  |
| timestamp      | TIMESTAMP WITH TIME ZONE | Search timestamp          |
| parameter_json | JSONB                    | Search parameters as JSON |

#### `trip_notes`

Stores notes attached to trips.

| Column    | Type                     | Description              |
| --------- | ------------------------ | ------------------------ |
| id        | BIGINT                   | Primary key              |
| trip_id   | BIGINT                   | Reference to trips table |
| timestamp | TIMESTAMP WITH TIME ZONE | Note timestamp           |
| content   | TEXT                     | Note content             |

### Analysis and Tracking Tables

#### `price_history`

Stores historical price data for various entities.

| Column      | Type                     | Description                               |
| ----------- | ------------------------ | ----------------------------------------- |
| id          | BIGINT                   | Primary key                               |
| entity_type | TEXT                     | Entity type (flight, accommodation, etc.) |
| entity_id   | BIGINT                   | Entity ID                                 |
| timestamp   | TIMESTAMP WITH TIME ZONE | Price timestamp                           |
| price       | NUMERIC                  | Price amount                              |

#### `saved_options`

Stores saved travel options for comparison.

| Column      | Type                     | Description                               |
| ----------- | ------------------------ | ----------------------------------------- |
| id          | BIGINT                   | Primary key                               |
| trip_id     | BIGINT                   | Reference to trips table                  |
| option_type | TEXT                     | Option type (flight, accommodation, etc.) |
| option_id   | BIGINT                   | Option ID                                 |
| timestamp   | TIMESTAMP WITH TIME ZONE | Saved timestamp                           |
| notes       | TEXT                     | Additional notes                          |

#### `trip_comparison`

Stores comparison data between different trip options.

| Column          | Type   | Description              |
| --------------- | ------ | ------------------------ |
| id              | BIGINT | Primary key              |
| trip_id         | BIGINT | Reference to trips table |
| comparison_json | JSONB  | Comparison data as JSON  |

## Common Usage Patterns

The `/migrations/20250508_05_example_queries.sql` file contains examples of common SQL queries for:

1. Creating new trips and adding travel options
2. Retrieving trip information and search results
3. Tracking price changes and budget allocation
4. Managing saved options and trip comparisons
5. Analyzing travel trends and patterns

## Database Design Notes

1. **Foreign Key Constraints**: All tables with trip_id have ON DELETE CASCADE constraints to ensure referential integrity when a trip is deleted.

2. **Check Constraints**: Various check constraints (e.g., dates, prices, status values) help maintain data validity.

3. **Triggers**: Automatic triggers update the updated_at timestamps when records are modified.

4. **Indexes**: Comprehensive indexing strategy for optimized query performance, including B-tree indexes for common lookup columns and GIN indexes for JSONB fields.

5. **JSONB Storage**: Flexible schema for structured data such as user preferences, trip flexibility options, accommodation amenities, and search parameters.

## Best Practices

1. **Use Prepared Statements**: When implementing database queries in code, use prepared statements to prevent SQL injection.

2. **Limit Result Sets**: Use LIMIT and OFFSET for pagination when retrieving large result sets.

3. **Database Transactions**: Use transactions when performing multiple related operations to ensure data consistency.

4. **Validate Input**: Validate input data before inserting into the database to maintain data integrity.

5. **Regular Backups**: Configure regular backups of the database to prevent data loss.

## Troubleshooting

If you encounter issues with the database setup:

1. **Check Connection**: Verify that your connection string or environment variables are correct.

2. **Check Migration Errors**: Look for error messages in the migration output and address any issues.

3. **Check Constraints**: If inserts or updates fail, check if they violate any constraints.

4. **Examine Logs**: Review the Supabase logs for any database errors or performance issues.

5. **Database Reset**: If needed, you can use the rollback script to completely reset the database schema.

## Contact

For questions or issues related to the TripSage database, please contact:

- GitHub Repository: [https://github.com/BjornMelin/tripsage-ai](https://github.com/BjornMelin/tripsage-ai)
- Project Maintainer: Bjorn Melin
