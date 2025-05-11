# TripSage Database Schema

This document provides detailed information about the TripSage database schema and table structure.

## Project Information

- **Project Name:** tripsage_planner
- **Database Type:** PostgreSQL via Supabase

## Schema Naming Conventions

- Use snake_case for all tables and columns (PostgreSQL standard)
- Tables should be lowercase with underscores separating words
- Foreign keys should use the singular form of the referenced table with \_id suffix
- Include created_at and updated_at timestamps on all tables
- Add appropriate comments to tables and complex columns

## Table Definitions

### trips

Primary table for trip information.

| Column      | Type        | Description                                          | Constraints             |
| ----------- | ----------- | ---------------------------------------------------- | ----------------------- |
| id          | uuid        | Primary key                                          | PRIMARY KEY, NOT NULL   |
| user_id     | uuid        | Reference to users table                             | FOREIGN KEY, NOT NULL   |
| title       | text        | Trip title                                           | NOT NULL                |
| description | text        | Trip description                                     |                         |
| start_date  | date        | Trip start date                                      | NOT NULL                |
| end_date    | date        | Trip end date                                        | NOT NULL                |
| budget      | numeric     | Total trip budget                                    | NOT NULL                |
| status      | text        | Trip status (planning, booked, completed, cancelled) | NOT NULL                |
| created_at  | timestamptz | Creation timestamp                                   | DEFAULT now(), NOT NULL |
| updated_at  | timestamptz | Last update timestamp                                | DEFAULT now(), NOT NULL |

### flights

Flight booking information.

| Column            | Type        | Description               | Constraints             |
| ----------------- | ----------- | ------------------------- | ----------------------- |
| id                | uuid        | Primary key               | PRIMARY KEY, NOT NULL   |
| trip_id           | uuid        | Reference to trips table  | FOREIGN KEY, NOT NULL   |
| airline           | text        | Airline name              | NOT NULL                |
| flight_number     | text        | Flight number             | NOT NULL                |
| origin            | text        | Origin airport code       | NOT NULL                |
| destination       | text        | Destination airport code  | NOT NULL                |
| departure_time    | timestamptz | Departure time            | NOT NULL                |
| arrival_time      | timestamptz | Arrival time              | NOT NULL                |
| price             | numeric     | Flight price              | NOT NULL                |
| booking_reference | text        | Booking confirmation code |                         |
| status            | text        | Booking status            | NOT NULL                |
| created_at        | timestamptz | Creation timestamp        | DEFAULT now(), NOT NULL |
| updated_at        | timestamptz | Last update timestamp     | DEFAULT now(), NOT NULL |

### accommodations

Accommodation booking information.

| Column            | Type        | Description                        | Constraints             |
| ----------------- | ----------- | ---------------------------------- | ----------------------- |
| id                | uuid        | Primary key                        | PRIMARY KEY, NOT NULL   |
| trip_id           | uuid        | Reference to trips table           | FOREIGN KEY, NOT NULL   |
| name              | text        | Accommodation name                 | NOT NULL                |
| type              | text        | Type (hotel, hostel, airbnb, etc.) | NOT NULL                |
| location          | text        | Location description               | NOT NULL                |
| check_in_date     | date        | Check-in date                      | NOT NULL                |
| check_out_date    | date        | Check-out date                     | NOT NULL                |
| price             | numeric     | Total price                        | NOT NULL                |
| booking_reference | text        | Booking confirmation code          |                         |
| status            | text        | Booking status                     | NOT NULL                |
| created_at        | timestamptz | Creation timestamp                 | DEFAULT now(), NOT NULL |
| updated_at        | timestamptz | Last update timestamp              | DEFAULT now(), NOT NULL |

### transportation

Local transportation options.

| Column            | Type        | Description                             | Constraints             |
| ----------------- | ----------- | --------------------------------------- | ----------------------- |
| id                | uuid        | Primary key                             | PRIMARY KEY, NOT NULL   |
| trip_id           | uuid        | Reference to trips table                | FOREIGN KEY, NOT NULL   |
| type              | text        | Transport type (train, bus, taxi, etc.) | NOT NULL                |
| origin            | text        | Starting location                       | NOT NULL                |
| destination       | text        | Ending location                         | NOT NULL                |
| departure_time    | timestamptz | Departure time                          | NOT NULL                |
| arrival_time      | timestamptz | Arrival time                            | NOT NULL                |
| price             | numeric     | Price                                   | NOT NULL                |
| booking_reference | text        | Booking confirmation code               |                         |
| status            | text        | Booking status                          | NOT NULL                |
| created_at        | timestamptz | Creation timestamp                      | DEFAULT now(), NOT NULL |
| updated_at        | timestamptz | Last update timestamp                   | DEFAULT now(), NOT NULL |

### itinerary_items

Detailed itinerary planning.

| Column      | Type        | Description              | Constraints             |
| ----------- | ----------- | ------------------------ | ----------------------- |
| id          | uuid        | Primary key              | PRIMARY KEY, NOT NULL   |
| trip_id     | uuid        | Reference to trips table | FOREIGN KEY, NOT NULL   |
| day_number  | integer     | Day of trip              | NOT NULL                |
| start_time  | time        | Start time               | NOT NULL                |
| end_time    | time        | End time                 | NOT NULL                |
| title       | text        | Activity title           | NOT NULL                |
| description | text        | Activity description     |                         |
| location    | text        | Activity location        |                         |
| cost        | numeric     | Estimated cost           |                         |
| priority    | integer     | Activity priority        |                         |
| notes       | text        | Additional notes         |                         |
| created_at  | timestamptz | Creation timestamp       | DEFAULT now(), NOT NULL |
| updated_at  | timestamptz | Last update timestamp    | DEFAULT now(), NOT NULL |

### users

User accounts.

| Column        | Type        | Description           | Constraints             |
| ------------- | ----------- | --------------------- | ----------------------- |
| id            | uuid        | Primary key           | PRIMARY KEY, NOT NULL   |
| email         | text        | User email address    | UNIQUE, NOT NULL        |
| name          | text        | User's full name      | NOT NULL                |
| password_hash | text        | Hashed password       | NOT NULL                |
| preferences   | jsonb       | User preferences      |                         |
| created_at    | timestamptz | Creation timestamp    | DEFAULT now(), NOT NULL |
| updated_at    | timestamptz | Last update timestamp | DEFAULT now(), NOT NULL |

### search_parameters

Saved search parameters.

| Column      | Type        | Description              | Constraints             |
| ----------- | ----------- | ------------------------ | ----------------------- |
| id          | uuid        | Primary key              | PRIMARY KEY, NOT NULL   |
| user_id     | uuid        | Reference to users table | FOREIGN KEY, NOT NULL   |
| search_type | text        | Type of search           | NOT NULL                |
| parameters  | jsonb       | Search parameters        | NOT NULL                |
| created_at  | timestamptz | Creation timestamp       | DEFAULT now(), NOT NULL |
| updated_at  | timestamptz | Last update timestamp    | DEFAULT now(), NOT NULL |

### price_history

Historical pricing data.

| Column      | Type        | Description                          | Constraints             |
| ----------- | ----------- | ------------------------------------ | ----------------------- |
| id          | uuid        | Primary key                          | PRIMARY KEY, NOT NULL   |
| entity_type | text        | Type of entity (flight, hotel, etc.) | NOT NULL                |
| entity_id   | uuid        | ID of the entity                     | NOT NULL                |
| price       | numeric     | Price at this timestamp              | NOT NULL                |
| currency    | text        | Currency code                        | NOT NULL                |
| timestamp   | timestamptz | When price was recorded              | NOT NULL                |
| source      | text        | Source of price information          | NOT NULL                |
| created_at  | timestamptz | Creation timestamp                   | DEFAULT now(), NOT NULL |

### trip_notes

User notes for trips.

| Column     | Type        | Description              | Constraints             |
| ---------- | ----------- | ------------------------ | ----------------------- |
| id         | uuid        | Primary key              | PRIMARY KEY, NOT NULL   |
| trip_id    | uuid        | Reference to trips table | FOREIGN KEY, NOT NULL   |
| user_id    | uuid        | Reference to users table | FOREIGN KEY, NOT NULL   |
| title      | text        | Note title               | NOT NULL                |
| content    | text        | Note content             | NOT NULL                |
| created_at | timestamptz | Creation timestamp       | DEFAULT now(), NOT NULL |
| updated_at | timestamptz | Last update timestamp    | DEFAULT now(), NOT NULL |

### saved_options

Alternative options saved during planning.

| Column      | Type        | Description                          | Constraints             |
| ----------- | ----------- | ------------------------------------ | ----------------------- |
| id          | uuid        | Primary key                          | PRIMARY KEY, NOT NULL   |
| trip_id     | uuid        | Reference to trips table             | FOREIGN KEY, NOT NULL   |
| option_type | text        | Type of option (flight, hotel, etc.) | NOT NULL                |
| option_data | jsonb       | Full option data                     | NOT NULL                |
| is_selected | boolean     | Whether this option was selected     | DEFAULT false, NOT NULL |
| created_at  | timestamptz | Creation timestamp                   | DEFAULT now(), NOT NULL |
| updated_at  | timestamptz | Last update timestamp                | DEFAULT now(), NOT NULL |

### trip_comparison

Comparison between multiple trip options.

| Column          | Type        | Description                      | Constraints             |
| --------------- | ----------- | -------------------------------- | ----------------------- |
| id              | uuid        | Primary key                      | PRIMARY KEY, NOT NULL   |
| user_id         | uuid        | Reference to users table         | FOREIGN KEY, NOT NULL   |
| title           | text        | Comparison title                 | NOT NULL                |
| description     | text        | Comparison description           |                         |
| trip_ids        | uuid[]      | Array of trip IDs being compared | NOT NULL                |
| comparison_data | jsonb       | Structured comparison data       | NOT NULL                |
| created_at      | timestamptz | Creation timestamp               | DEFAULT now(), NOT NULL |
| updated_at      | timestamptz | Last update timestamp            | DEFAULT now(), NOT NULL |
