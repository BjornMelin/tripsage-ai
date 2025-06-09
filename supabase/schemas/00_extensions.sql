-- Supabase Extensions Setup
-- Description: Required extensions for TripSage database functionality
-- Dependencies: None (must be run first)

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for AI/ML embeddings and semantic search
-- Note: This extension provides vector data types and operations for storing
-- and querying high-dimensional vectors (embeddings) efficiently
CREATE EXTENSION IF NOT EXISTS "vector";

-- Note: Supabase automatically creates auth.users table with UUID primary keys
-- We reference auth.users(id) for all user relationships throughout the schema