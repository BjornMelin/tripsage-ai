/**
 * OpenAI Agents SDK MCP Server Configuration
 *
 * This file configures MCP servers for use with OpenAI Agents SDK in TripSage.
 * It defines the connection and initialization parameters for Airbnb, Google Maps,
 * and Flights MCP servers.
 */

require("dotenv").config();

const config = {
  mcpServers: {
    // Airbnb MCP Server configuration
    airbnb: {
      command: "npx",
      args: ["-y", "@openbnb/mcp-server-airbnb"],
      env: {
        // Optional API key if required by the MCP server
        AIRBNB_API_KEY: "${AIRBNB_API_KEY}",
      },
    },
    // Google Maps MCP Server configuration
    "google-maps": {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-google-maps"],
      env: {
        GOOGLE_MAPS_API_KEY: "${GOOGLE_MAPS_API_KEY}",
      },
    },
    // Flights MCP Server configuration
    flights: {
      command: "npx",
      args: ["-y", "@ravinahp/flights-mcp"],
      env: {
        DUFFEL_API_KEY: "${DUFFEL_API_KEY}",
        DUFFEL_API_VERSION: "2023-06-02",
        REDIS_URL: "${REDIS_URL}",
      },
    },
  },
};

module.exports = config;
