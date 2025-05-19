#!/bin/bash
# Script to set up and start the Google Calendar MCP server

# Define the Google Calendar MCP repository
REPO_URL="https://github.com/nspady/google-calendar-mcp.git"
REPO_DIR="google-calendar-mcp"
MCP_PORT=3003

# Exit on error
set -e

# Check if the repository directory exists
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning Google Calendar MCP repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
else
    echo "Updating Google Calendar MCP repository..."
    cd "$REPO_DIR"
    git pull
fi

# Install npm dependencies
echo "Installing dependencies..."
npm install

# Check if OAuth keys exist
if [ ! -f "gcp-oauth.keys.json" ]; then
    echo "Creating OAuth keys template..."
    cp gcp-oauth.keys.example.json gcp-oauth.keys.json
    
    # Get OAuth credentials from environment or prompt user
    if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
        echo "Using OAuth credentials from environment variables..."
        # Use jq to update the keys file
        jq --arg id "$GOOGLE_CLIENT_ID" --arg secret "$GOOGLE_CLIENT_SECRET" \
           '.installed.client_id = $id | .installed.client_secret = $secret' \
           gcp-oauth.keys.json > temp.json && mv temp.json gcp-oauth.keys.json
    else
        echo "==================================================================="
        echo "WARNING: OAuth credentials not found in environment variables."
        echo "Please manually edit gcp-oauth.keys.json with your credentials."
        echo "You can obtain these from the Google Cloud Console:"
        echo "https://console.cloud.google.com/apis/credentials"
        echo "==================================================================="
    fi
fi

# Build the TypeScript code
echo "Building the MCP server..."
npm run build

# Start the server with environment variable for port
echo "Starting Google Calendar MCP server on port $MCP_PORT..."
PORT=$MCP_PORT npm run start