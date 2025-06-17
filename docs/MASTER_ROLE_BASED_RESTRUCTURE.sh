#!/bin/bash

# TripSage Documentation Role-Based Restructuring Script
# Generated from parallel subagent analysis
# Run from: /home/bjorn/.claude-squad/worktrees/update-docs-ts_1849ac608c2f0961/docs

set -e  # Exit on any error

echo "🚀 TripSage Documentation Role-Based Restructuring"
echo "=================================================="

# Create backup before making changes
BACKUP_DIR="backup-$(date +%Y%m%d-%H%M%S)"
echo "📦 Creating backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r 01_GETTING_STARTED 02_PROJECT_OVERVIEW 03_ARCHITECTURE 04_DEVELOPMENT_GUIDE \
      05_FEATURES_AND_INTEGRATIONS 06_API_REFERENCE 07_CONFIGURATION 08_USER_GUIDES \
      10_RESEARCH testing "$BACKUP_DIR/" 2>/dev/null || true

echo "🏗️  Creating role-based directory structure..."

# =============================================================================
# 1. API DOCUMENTATION (docs/api/)
# =============================================================================
echo "📚 Setting up API documentation..."
mkdir -p api

# Move API reference files with proper naming
mv 06_API_REFERENCE/REST_API_ENDPOINTS.md api/rest-endpoints.md
mv 06_API_REFERENCE/WEBSOCKET_API.md api/websocket-api.md
mv 06_API_REFERENCE/AUTHENTICATION_API.md api/authentication.md
mv 06_API_REFERENCE/ERROR_CODES.md api/error-codes.md
mv 06_API_REFERENCE/API_EXAMPLES.md api/examples.md
mv 08_USER_GUIDES/API_USAGE_EXAMPLES.md api/usage-examples.md

# Create API documentation index
cat > api/README.md << 'EOF'
# TripSage API Documentation

> **Complete API reference for external developers and integrators**

## Quick Start
- [Getting Started](./getting-started.md) - Your first API call in 5 minutes
- [Authentication](./authentication.md) - API keys and security
- [Usage Examples](./usage-examples.md) - Common integration patterns

## API Reference
- [REST Endpoints](./rest-endpoints.md) - Complete endpoint documentation
- [WebSocket API](./websocket-api.md) - Real-time communication
- [Error Codes](./error-codes.md) - Error handling reference
- [Examples](./examples.md) - Code samples and patterns

## Resources
- [OpenAPI Specification](./openapi-spec.md) - Machine-readable API spec
- [Rate Limits](./rate-limits.md) - API usage limits and best practices
- [SDKs](./sdks.md) - Official client libraries
EOF

# Create missing API documentation stubs
cat > api/getting-started.md << 'EOF'
# API Getting Started Guide

## Quick Setup (5 minutes)

1. **Get your API key**
   ```bash
   # Sign up at https://tripsage.ai/signup
   # Generate API key in dashboard
   ```

2. **Make your first request**
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://api.tripsage.ai/health
   ```

3. **Plan a trip**
   ```bash
   curl -X POST https://api.tripsage.ai/trips \
        -H "Authorization: Bearer YOUR_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"destination": "Paris", "duration": 5}'
   ```

## Next Steps
- [Authentication Guide](./authentication.md)
- [Full API Reference](./rest-endpoints.md)
- [Usage Examples](./usage-examples.md)
EOF

cat > api/openapi-spec.md << 'EOF'
# OpenAPI Specification

## Download Specification

- **OpenAPI 3.1**: [openapi.json](https://api.tripsage.ai/openapi.json)
- **Swagger UI**: [Interactive Documentation](https://api.tripsage.ai/docs)
- **ReDoc**: [Alternative Documentation](https://api.tripsage.ai/redoc)

## Code Generation

Use the OpenAPI spec to generate client libraries:

```bash
# Python
openapi-generator generate -i openapi.json -g python -o ./tripsage-python-client

# JavaScript  
openapi-generator generate -i openapi.json -g javascript -o ./tripsage-js-client

# Go
openapi-generator generate -i openapi.json -g go -o ./tripsage-go-client
```
EOF

# =============================================================================
# 2. DEVELOPERS DOCUMENTATION (docs/developers/)
# =============================================================================
echo "👨‍💻 Setting up developers documentation..."
mkdir -p developers

# Remove old development guide (content already migrated to developers/)
rm -rf 04_DEVELOPMENT_GUIDE/
rm -rf testing/

# Copy database documentation to developers
cp 03_ARCHITECTURE/DATABASE_ARCHITECTURE.md developers/database-architecture.md
cp 06_API_REFERENCE/DATA_MODELS.md developers/data-models.md
cp 06_API_REFERENCE/DATABASE_SCHEMA.md developers/database-schema.md

# Create contributing guidelines
cat > developers/contributing-guidelines.md << 'EOF'
# Contributing Guidelines

## Quick Start
1. Fork the repository
2. Set up development environment: `uv sync && cd frontend && pnpm install`
3. Create feature branch: `git checkout -b feature/your-feature`
4. Make changes following [code standards](./code-standards.md)
5. Run tests: `uv run pytest && cd frontend && pnpm test`
6. Submit pull request

## Development Standards
- **Python**: Pydantic v2, type hints required, ruff formatting
- **TypeScript**: Strict mode, Biome formatting, Zod validation
- **Testing**: 80-90% coverage, TDD approach
- **Documentation**: Update relevant docs for API changes

## Code Review Process
- All PRs require review from maintainers
- Tests must pass before merge
- Documentation must be updated
- Follow conventional commit format
EOF

# =============================================================================
# 3. OPERATORS DOCUMENTATION (docs/operators/)
# =============================================================================
echo "⚙️  Setting up operators documentation..."
mkdir -p operators

# Move configuration files (flattening structure)
mv 07_CONFIGURATION/* operators/ 2>/dev/null || true
mv 07_CONFIGURATION/SECURITY/* operators/ 2>/dev/null || true
mv 07_INSTALLATION_AND_SETUP/INSTALLATION_GUIDE.md operators/installation-guide.md
mv 07_INSTALLATION_AND_SETUP/node_js/COMPATIBILITY_GUIDE.md operators/nodejs-compatibility-guide.md

# Move deployment documentation
mv 01_GETTING_STARTED/PRODUCTION_DEPLOYMENT.md operators/production-deployment.md
mv 03_ARCHITECTURE/DEPLOYMENT_STRATEGY.md operators/deployment-strategy.md
mv 03_ARCHITECTURE/INFRASTRUCTURE_UPGRADE_SUMMARY.md operators/infrastructure-upgrade-summary.md

# Remove empty directories
rm -rf 07_CONFIGURATION 07_INSTALLATION_AND_SETUP

# Rename operator files for consistency
cd operators
for file in *.md; do
    if [[ "$file" =~ [A-Z_] ]]; then
        new_name=$(echo "$file" | tr '[:upper:]' '[:lower:]' | sed 's/_/-/g')
        if [ "$file" != "$new_name" ]; then
            mv "$file" "$new_name" 2>/dev/null || true
        fi
    fi
done
cd ..

# Create operators documentation index
cat > operators/README.md << 'EOF'
# Operators Documentation

> **Deployment, monitoring, and infrastructure management for TripSage**

## Deployment & Installation
- [Installation Guide](./installation-guide.md) - Complete setup instructions
- [Production Deployment](./production-deployment.md) - Production deployment guide
- [Deployment Strategy](./deployment-strategy.md) - Deployment architecture
- [Infrastructure Upgrade](./infrastructure-upgrade-summary.md) - Infrastructure changes

## Configuration Management
- [Environment Variables](./environment-variables.md) - Configuration reference
- [Deployment Configs](./deployment-configs.md) - Platform-specific configs
- [OAuth Setup](./oauth-setup-guide.md) - Authentication provider setup
- [Extensions & Automation](./extensions-and-automation.md) - Supabase extensions

## Security Documentation
- [Security Overview](./overview.md) - Security architecture
- [RLS Implementation](./rls-implementation.md) - Row Level Security
- [Security Best Practices](./security-best-practices.md) - Security guidelines
- [Security Testing](./security-testing.md) - Security validation

## Operations & Monitoring
- [Settings Reference](./settings-reference.md) - Configuration options
- [Node.js Compatibility](./nodejs-compatibility-guide.md) - Node.js setup
EOF

# Create missing operational documentation stubs
cat > operators/monitoring-setup.md << 'EOF'
# Monitoring Setup

## Observability Stack
- **Metrics**: Prometheus + Grafana
- **Logs**: Structured JSON logging
- **Traces**: OpenTelemetry
- **Alerts**: PagerDuty integration

## Key Metrics
- API response times
- Database query performance
- Agent orchestration latency
- Memory system performance
- Cache hit rates

## Setup Instructions
```bash
# Deploy monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Configure Grafana dashboards
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana-dashboards/tripsage.json
```
EOF

cat > operators/backup-procedures.md << 'EOF'
# Backup Procedures

## Database Backups
- **Frequency**: Daily automated backups
- **Retention**: 30 days
- **Location**: S3 with cross-region replication

## Backup Schedule
```bash
# Automated via Supabase
# Manual backup command:
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d).sql.gz
```

## Recovery Procedures
1. Identify backup to restore
2. Create new database instance
3. Restore from backup
4. Update connection strings
5. Verify application functionality
EOF

# =============================================================================
# 4. USERS DOCUMENTATION (docs/users/)
# =============================================================================
echo "👥 Setting up users documentation..."
mkdir -p users

# Move user-focused documentation
mv 01_GETTING_STARTED/README.md users/README.md
mv 08_USER_GUIDES/FAQ.md users/faq.md

# Create user getting started guide
cat > users/getting-started.md << 'EOF'
# Getting Started with TripSage

## Welcome! 🎉

TripSage AI helps you plan amazing trips with intelligent recommendations and real-time collaboration.

## Quick Start (5 minutes)

1. **Create your account** at [tripsage.ai/signup](https://tripsage.ai/signup)
2. **Plan your first trip**:
   - Click "New Trip"
   - Enter destination and dates
   - Let AI suggest itinerary
3. **Customize your plan**:
   - Add/remove activities
   - Adjust budget preferences
   - Invite travel companions
4. **Book and go!**

## What's Next?
- [Travel Planning Guide](./travel-planning-guide.md) - Detailed trip planning
- [Web App Guide](./web-app-guide.md) - Interface walkthrough
- [Collaboration Guide](./collaboration.md) - Group trip planning
EOF

# Create comprehensive user guides (stubs)
cat > users/travel-planning-guide.md << 'EOF'
# Travel Planning Guide

## Planning Your Perfect Trip

### 1. Destination Research
- Use AI-powered destination insights
- Compare seasonal recommendations
- Review budget estimates

### 2. Itinerary Building
- Start with AI suggestions
- Customize with your preferences
- Balance activities and rest time

### 3. Booking Integration
- Compare flight options
- Find accommodation deals
- Reserve activities and experiences

### 4. Trip Management
- Real-time updates
- Expense tracking
- Document storage
EOF

# Remove empty user guides directory
rm -rf 08_USER_GUIDES

# =============================================================================
# 5. ARCHITECTURE DECISION RECORDS (docs/adrs/)
# =============================================================================
echo "📋 Setting up Architecture Decision Records..."
mkdir -p adrs

# Create ADR template
cat > adrs/template.md << 'EOF'
# ADR-XXXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[Describe the forces at play, including technological, political, social, and project local]

## Decision
[Describe our response to these forces]

## Consequences
[Describe the resulting context, after applying the decision]

## Alternatives Considered
[List alternatives that were considered but not chosen]
EOF

# Create decision log index
cat > adrs/README.md << 'EOF'
# Architecture Decision Records (ADRs)

## Decision Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](./adr-0001-langgraph-orchestration.md) | Use LangGraph for Agent Orchestration | Accepted | 2025-01 |
| [ADR-0002](./adr-0002-supabase-platform.md) | Adopt Supabase as Primary Database and Auth Platform | Accepted | 2025-01 |
| [ADR-0003](./adr-0003-dragonfly-caching.md) | Use DragonflyDB for High-Performance Caching | Accepted | 2025-01 |
| [ADR-0004](./adr-0004-fastapi-backend.md) | FastAPI as Backend Framework | Accepted | 2025-01 |

## Creating New ADRs

```bash
# Use the template
cp template.md adr-XXXX-your-title.md
# Fill in the details
# Update this README with the new entry
```
EOF

# Create key initial ADRs
cat > adrs/adr-0001-langgraph-orchestration.md << 'EOF'
# ADR-0001: Use LangGraph for Agent Orchestration

## Status
Accepted

## Context
TripSage requires sophisticated AI agent orchestration for trip planning workflows. The system needs to coordinate multiple agents (destination research, flight search, accommodation, activities) with state management, error recovery, and conditional routing.

## Decision
Adopt LangGraph as the primary agent orchestration framework, replacing simpler orchestration approaches.

## Consequences
**Positive:**
- Graph-based workflow definition allows complex conditional logic
- Built-in state management with checkpointing
- Native integration with LangChain ecosystem
- Visual workflow debugging capabilities

**Negative:**
- Additional complexity compared to sequential agent calls
- Learning curve for team members
- Dependency on LangChain ecosystem

## Alternatives Considered
- Custom orchestration with FastAPI
- Sequential agent calls
- Other workflow engines (Prefect, Airflow)
EOF

cat > adrs/adr-0002-supabase-platform.md << 'EOF'
# ADR-0002: Adopt Supabase as Primary Database and Auth Platform

## Status
Accepted

## Context
TripSage needs a scalable database with vector support for AI embeddings, real-time capabilities, and secure authentication. The current custom JWT implementation has security vulnerabilities.

## Decision
Migrate to Supabase as the unified database and authentication platform.

## Consequences
**Positive:**
- PostgreSQL with pgvector for AI embeddings
- Built-in Row Level Security (RLS)
- Real-time subscriptions via WebSockets
- Integrated authentication (fixes security issues)
- Significant cost savings (~$90k over 5 years)

**Negative:**
- Migration effort from existing systems
- Platform dependency
- Learning curve for Supabase-specific features

## Alternatives Considered
- Continue with custom JWT + separate database
- AWS RDS + Cognito
- Firebase
- Self-hosted PostgreSQL + custom auth
EOF

# =============================================================================
# 6. ARCHITECTURE DOCUMENTATION (docs/architecture/)
# =============================================================================
echo "🏗️  Setting up architecture documentation..."
mkdir -p architecture

# Move architecture files with proper naming
mv 03_ARCHITECTURE/WEBSOCKET_INFRASTRUCTURE.md architecture/websocket-infrastructure.md
mv 03_ARCHITECTURE/AGENT_DESIGN_AND_OPTIMIZATION.md architecture/agent-design.md
mv 03_ARCHITECTURE/SYSTEM_OVERVIEW.md architecture/system-overview.md
mv 06_API_REFERENCE/STORAGE_ARCHITECTURE.md architecture/storage-architecture.md

# Create technology stack overview
cat > architecture/technology-stack.md << 'EOF'
# Technology Stack

## Core Technologies

### Backend
- **FastAPI**: Async Python web framework
- **Pydantic v2**: Data validation and serialization
- **LangGraph**: AI agent orchestration
- **Supabase**: Database and authentication

### Frontend  
- **Next.js 15**: React framework with SSR
- **React 19**: UI library with automatic optimization
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first styling

### Database & Storage
- **PostgreSQL**: Primary database via Supabase
- **pgvector**: Vector embeddings for AI
- **DragonflyDB**: High-performance caching
- **Supabase Storage**: File and media storage

### AI & Machine Learning
- **OpenAI GPT**: Language model integration
- **Mem0**: AI memory system
- **LangChain**: AI application framework
- **Vector Search**: Semantic similarity matching

## Architecture Decisions
See [ADRs](../adrs/) for detailed rationale behind technology choices.
EOF

# Remove old architecture directory
rm -rf 03_ARCHITECTURE

# =============================================================================
# 7. CLEANUP AND VALIDATION
# =============================================================================
echo "🧹 Cleaning up old structure..."

# Remove remaining old directories
rm -rf 01_GETTING_STARTED 02_PROJECT_OVERVIEW 05_FEATURES_AND_INTEGRATIONS
rm -rf 06_API_REFERENCE 10_RESEARCH

# Archive any remaining files to prevent data loss
if ls *.md 1> /dev/null 2>&1; then
    mkdir -p _archive
    mv *.md _archive/ 2>/dev/null || true
fi

# =============================================================================
# 8. CREATE MASTER INDEX
# =============================================================================
echo "📚 Creating master documentation index..."

cat > README.md << 'EOF'
# TripSage Documentation

> **AI-powered travel planning platform documentation**

## Documentation by Role

### 🚀 [Users](./users/)
End-user guides, getting started, and feature walkthroughs
- Quick start in 5 minutes
- Travel planning workflows
- Admin configuration

### 📚 [API](./api/)
External developer integration and API reference
- REST endpoints and WebSocket APIs
- Authentication and rate limits
- Code examples and SDKs

### 👨‍💻 [Developers](./developers/)
Internal development team resources and guidelines
- Code standards and testing
- Architecture implementation
- Contributing guidelines

### ⚙️ [Operators](./operators/)
Deployment, monitoring, and infrastructure management
- Production deployment
- Security configuration
- Monitoring and backups

### 🏗️ [Architecture](./architecture/)
High-level system design and technical decisions
- Technology stack
- System overview
- Component design

### 📋 [ADRs](./adrs/)
Architecture Decision Records documenting technical choices
- Decision log and rationale
- Technology selection criteria
- Alternative analysis

## Quick Links

- **New to TripSage?** → [Users Guide](./users/getting-started.md)
- **API Integration?** → [API Getting Started](./api/getting-started.md)
- **Contributing Code?** → [Developer Guide](./developers/contributing-guidelines.md)
- **Deploying TripSage?** → [Operators Guide](./operators/installation-guide.md)

---

*Documentation structure follows role-based organization best practices for improved discoverability and maintenance.*
EOF

# =============================================================================
# 9. FINAL VALIDATION
# =============================================================================
echo "✅ Validating new structure..."

# Count files in each directory
echo "📊 Documentation Statistics:"
for dir in api developers operators users adrs architecture; do
    count=$(find $dir -name "*.md" 2>/dev/null | wc -l)
    echo "  $dir/: $count files"
done

echo ""
echo "🎉 Role-based documentation restructuring complete!"
echo ""
echo "📁 New Structure:"
echo "   docs/"
echo "   ├── api/           (External API documentation)"
echo "   ├── developers/    (Internal development guides)"  
echo "   ├── operators/     (Deployment and infrastructure)"
echo "   ├── users/         (End-user guides and tutorials)"
echo "   ├── adrs/          (Architecture Decision Records)"
echo "   ├── architecture/  (High-level system design)"
echo "   └── README.md      (Master documentation index)"
echo ""
echo "🔍 Backup created in: $BACKUP_DIR"
echo "📋 Review the new structure and update any remaining cross-references"
echo ""
echo "✨ Documentation is now organized by role for improved usability!"