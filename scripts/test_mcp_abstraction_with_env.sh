#!/bin/bash
# Script to run MCP abstraction tests with proper environment variables

export NEO4J_PASSWORD=test_password
export NEO4J_USER=bjorn
export NEO4J_URI=bolt://localhost:7687
export OPENAI_API_KEY=test_key
export ANTHROPIC_API_KEY=test_key
export WEATHER_API_KEY=test_key
export GOOGLE_MAPS_API_KEY=test_key
export SUPABASE_URL=https://test.supabase.co
export SUPABASE_API_KEY=test_key
export TESTING=true
export TRIPSAGE_ENV=test

# Add the full path for Redis URL
export REDIS_URL=redis://localhost:6379/0

# Add MCP URLs
export TIME_MCP_URL=http://localhost:8000
export WEATHER_MCP_URL=http://localhost:8001
export GOOGLEMAPS_MCP_URL=http://localhost:8002
export MEMORY_MCP_URL=http://localhost:8003
export WEBCRAWL_MCP_URL=http://localhost:8004
export FLIGHTS_MCP_URL=http://localhost:8005
export ACCOMMODATIONS_MCP_URL=http://localhost:8006

cd /home/bjorn/repos/agents/openai/tripsage-ai
uv run pytest tests/mcp_abstraction/test_exceptions_direct.py -v