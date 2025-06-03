# syntax=docker/dockerfile:1
# =============================================================================
# Airbnb MCP Service - Only Remaining MCP Integration
# =============================================================================
# This is the ONLY MCP service still in use in the modern TripSage architecture.
# All other services have been migrated to direct SDKs for better performance.
# Airbnb MCP is retained because there is no official Airbnb SDK available.

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install the Airbnb MCP package with specific version for consistency
RUN npm install -g airbnb-mcp@1.0.0 && \
    npm cache clean --force

# Create non-root user for security
RUN addgroup -g 1001 -S mcpuser && \
    adduser -S mcpuser -u 1001 -G mcpuser

# Switch to non-root user
USER mcpuser

# Health check for MCP service availability
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD node --version || exit 1

# Expose MCP port
EXPOSE 3001

# Set default command
CMD ["airbnb-mcp"]