# Administrator Guide

Manage system configuration, monitoring, and TripSage deployment operations.

## Admin Access

Admin functionality requires JWT tokens with admin privileges (`metadata.is_admin: true` or admin role). Admin endpoints are protected with `AdminPrincipalDep`.

### Admin-Only Endpoints

- `/api/config/*`: Agent configuration management
- `/api/dashboard/*`: System monitoring and analytics

## System Configuration

### Agent Configuration

Admin users can manage AI agent configurations through `/api/config` endpoints:

**Available Agents:**

- Budget Agent
- Destination Research Agent
- Itinerary Agent

**Configuration Management:**

- View current agent configurations
- Update model settings and parameters
- Manage configuration versions
- Set environment-specific overrides

```bash
# List available agent types (admin only)
GET /api/config/agents

# Get configuration for specific agent (admin only)
GET /api/config/agents/{agent_type}

# Update agent configuration (admin only)
PUT /api/config/agents/{agent_type}
```

## Analytics & Monitoring

Admin users can access comprehensive system analytics through `/api/dashboard` endpoints:

### System Overview

```bash
# Get system status and metrics
GET /api/dashboard/overview

# Get real-time metrics
GET /api/dashboard/metrics/realtime

# Get usage statistics
GET /api/dashboard/usage
```

**Available Metrics:**

- System status and health indicators
- Real-time performance metrics (response times, throughput)
- Usage statistics (requests, users, API calls)
- Rate limiting status and quota information
- Service health status for all components

### Alert Management

```bash
# Get active alerts
GET /api/dashboard/alerts

# Get alert history
GET /api/dashboard/alerts/history
```

**Alert Types:**

- Rate limit violations
- System performance degradation
- Service availability issues
- Security events

### User Activity Monitoring

```bash
# Get user activity data
GET /api/dashboard/users/activity

# Get top consumers and usage patterns
GET /api/dashboard/users/top-consumers
```

## Security & Audit

### Authentication Auditing

All authentication events are logged via the audit logging service:

- JWT token validation attempts
- Authentication successes and failures
- Security events and violations
- Admin access patterns

### Access Control

Admin access is controlled through:

- JWT metadata (`is_admin: true`)
- Role-based permissions (admin, superadmin, site_admin)
- Endpoint-level authorization checks

## Health Monitoring

### Health Endpoints

```bash
# Basic health check
GET /health

# Comprehensive health check
GET /health?full=true

# Database health
GET /health/database

# Cache health
GET /health/cache
```

**Health Checks Include:**

- Database connectivity and performance
- Redis/Upstash cache availability
- External API service status
- System resource utilization

## Maintenance Operations

### Database Operations

- Connection monitoring and recovery
- Performance optimization checks
- Query execution monitoring
- Backup verification procedures

### Cache Management

- Redis connection health monitoring
- Memory usage and eviction tracking
- Performance optimization
- Connection pool management

### System Updates

1. Review configuration changes through admin endpoints
2. Test agent configuration updates
3. Monitor system health post-deployment
4. Rollback procedures available through configuration versioning

## Troubleshooting

### Common Issues

**Authentication Problems:**

- Verify JWT token validity and admin claims
- Check audit logs for authentication failures
- Validate admin role configuration

**Performance Issues:**

- Check dashboard metrics for bottlenecks
- Monitor database and cache performance
- Review rate limiting status

**Configuration Problems:**

- Use admin endpoints to verify agent configurations
- Check system health for service dependencies
- Review dashboard alerts for system issues

### Diagnostic Procedures

1. Check system health endpoints
2. Review dashboard metrics and alerts
3. Examine audit logs for security events
4. Verify agent configuration status
5. Monitor rate limiting and usage patterns
