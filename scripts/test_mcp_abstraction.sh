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

cd /home/bjorn/repos/agents/openai/tripsage-ai
uv run pytest tests/mcp_abstraction/ -v
