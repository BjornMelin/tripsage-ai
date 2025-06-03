# syntax=docker/dockerfile:1
# =============================================================================
# Supabase MCP Development Service
# =============================================================================
# Mock/stub service for Supabase functionality in local development environment

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install the Supabase MCP package with specific version for consistency
RUN npm install -g supabase-mcp@1.0.0 && \
    npm cache clean --force

# Create non-root user for security
RUN addgroup -g 1001 -S mcpuser && \
    adduser -S mcpuser -u 1001 -G mcpuser

# Switch to non-root user
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node --version || exit 1

# Set default command
CMD ["supabase-mcp"]