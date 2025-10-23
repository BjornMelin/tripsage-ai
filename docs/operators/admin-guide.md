# 🔧 Administrator Guide

> **Complete Admin Reference for TripSage**  
> Manage users, configure settings, and maintain your TripSage deployment

## 📋 Admin Dashboard Overview

### Accessing Admin Panel

1. **Login** with admin credentials
2. **Navigate** to Settings → Admin Dashboard
3. **Verify** admin role indicator in top bar
4. **Access** admin-only features and controls

### Dashboard Layout

```text
┌─────────────────────────────────────────────────────┐
│  🔧 Admin Dashboard                    [👤 Admin]    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  📊 System Status        👥 Active Users: 1,247     │
│  ✅ All Systems          📈 API Calls: 45.2k/hr    │
│  🔄 Last Check: 2m       💾 Storage: 67% used      │
│                                                      │
│  [Users] [Settings] [Analytics] [Security] [Logs]   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## 👥 User Management

### User Administration

**View All Users:**

- Search by email, name, or ID
- Filter by plan type, status, join date
- Sort by activity, spending, trips created
- Export user lists to CSV

**User Actions:**

- 👁️ View detailed profile and activity
- ✏️ Edit user information and preferences
- 🔒 Reset passwords and 2FA
- 🚫 Suspend or ban accounts
- 💳 Manage subscriptions
- 📧 Send direct messages

### Role Management

**Available Roles:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| **User** | Standard features | Regular travelers |
| **Premium** | Full feature set + API | Power users |
| **Business** | Team features + reporting | Corporate accounts |
| **Admin** | Full system access | System administrators |
| **Support** | User assistance tools | Support team |

**Assigning Roles:**

1. Navigate to Users → Select User
2. Click "Edit Roles"
3. Select appropriate role(s)
4. Add role expiration (optional)
5. Save and notify user

### Team Management

**Creating Teams:**

- Business/Enterprise feature
- Centralized billing
- Shared trip planning
- Usage reporting
- Policy enforcement

**Team Settings:**

- Member limits
- Spending controls
- Approval workflows
- Feature restrictions
- Reporting access

## ⚙️ System Configuration

### General Settings

**Application Settings:**

```yaml
# Core Configuration
app_name: "TripSage"
app_url: "https://app.tripsage.ai"
support_email: "support@tripsage.ai"
default_language: "en"
timezone: "UTC"

# Feature Flags
enable_ai_chat: true
enable_realtime_collab: true
enable_api_access: true
enable_mobile_apps: true
maintenance_mode: false
```

**Email Configuration:**

- SMTP settings
- Email templates
- Sending limits
- Bounce handling
- Unsubscribe management

### API Configuration

**Rate Limiting:**

```yaml
rate_limits:
  free_tier:
    requests_per_hour: 100
    requests_per_month: 1000
  premium_tier:
    requests_per_hour: 1000
    requests_per_month: 50000
  enterprise:
    custom: true
```

**API Keys Management:**

- Generate master keys
- Set expiration policies
- Monitor usage
- Revoke compromised keys
- Audit access logs

### Integration Settings

**External Services:**

| Service | Configuration | Status |
|---------|---------------|---------|
| **OpenAI** | API key, model selection | ✅ Active |
| **Duffel** | API credentials, test mode | ✅ Active |
| **Google Maps** | API key, quotas | ✅ Active |
| **Supabase** | Project URL, service key | ✅ Active |
| **DragonflyDB** | Connection string | ✅ Active |

**Webhook Configuration:**

- Endpoint URLs
- Authentication
- Retry policies
- Event types
- Payload formats

## 📊 Analytics & Reporting

### System Metrics

**Real-Time Dashboard:**

- Active users
- API request rate
- Response times
- Error rates
- Cache hit rates

**Performance Monitoring:**

```text
┌─────────────────────────────────────┐
│ Response Time (last 24h)            │
│ ────────────────────────────        │
│ P50: 127ms  P95: 342ms  P99: 891ms │
│                                     │
│ API Endpoints:                      │
│ /search     : 89ms avg             │
│ /flights    : 234ms avg            │
│ /chat       : 156ms avg            │
└─────────────────────────────────────┘
```

### Usage Analytics

**User Behavior:**

- Trip planning patterns
- Popular destinations
- Booking conversion rates
- Feature adoption
- User retention

**Business Metrics:**

- Revenue by plan type
- Customer acquisition cost
- Lifetime value
- Churn analysis
- Growth trends

### Custom Reports

**Report Builder:**

1. Select data source
2. Choose metrics
3. Apply filters
4. Set schedule
5. Configure delivery

**Available Reports:**

- User activity summary
- API usage breakdown
- Revenue reports
- Error analysis
- Performance trends

## 🔒 Security Management

### Access Control

**Authentication Settings:**

- Password policies
- 2FA requirements
- Session management
- SSO configuration
- OAuth providers

**Security Policies:**

```yaml
security:
  password_min_length: 12
  password_require_special: true
  session_timeout_minutes: 60
  max_login_attempts: 5
  lockout_duration_minutes: 30
  require_2fa_admin: true
```

### Audit Logging

**Tracked Events:**

- User logins/logouts
- Permission changes
- Data exports
- API access
- Configuration changes
- Security incidents

**Log Management:**

- Retention policies
- Search and filter
- Export capabilities
- Alert configuration
- Compliance reports

### Data Protection

**Privacy Controls:**

- Data retention settings
- Deletion policies
- Anonymization rules
- Export restrictions
- GDPR compliance tools

**Backup Management:**

- Automated backups
- Retention periods
- Recovery testing
- Encryption verification
- Off-site storage

## 🚨 Monitoring & Alerts

### System Health

**Health Checks:**

- Database connectivity
- Cache performance
- API availability
- External services
- Storage capacity

**Alert Configuration:**

```yaml
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 5%"
    threshold_minutes: 5
    notify: ["admin@tripsage.ai", "ops-team"]
    
  - name: "Low Disk Space"
    condition: "disk_usage > 90%"
    notify: ["infrastructure-team"]
    
  - name: "API Degradation"
    condition: "response_time_p95 > 1000ms"
    notify: ["dev-team", "support-team"]
```

### Incident Management

**Incident Response:**

1. Alert triggered
2. Automatic diagnostics
3. Team notification
4. Status page update
5. Resolution tracking

**Status Page Management:**

- Component status
- Incident creation
- Update posting
- Subscriber notifications
- Historical uptime

## 🛠️ Maintenance Operations

### Database Management

**Regular Tasks:**

- Performance optimization
- Index maintenance
- Backup verification
- Query analysis
- Storage monitoring

**Migration Management:**

- Schema updates
- Data migrations
- Rollback procedures
- Testing protocols
- Deployment windows

### Cache Operations

**DragonflyDB Management:**

- Memory usage monitoring
- Key analysis
- Performance tuning
- Cluster health
- Failover testing

### Update Management

**System Updates:**

1. Review changelog
2. Test in staging
3. Schedule maintenance
4. Notify users
5. Deploy update
6. Verify success
7. Monitor metrics

## 📱 Support Tools

### User Support

**Support Dashboard:**

- Ticket queue
- User lookup
- Trip inspection
- Booking verification
- Refund processing

**Support Actions:**

- View user sessions
- Impersonate users (with audit)
- Modify bookings
- Issue credits
- Send notifications

### Troubleshooting

**Diagnostic Tools:**

- User session replay
- API request logs
- Error stack traces
- Performance profiling
- Database queries

**Common Issues:**

- Payment failures → Check payment logs
- Sync issues → Verify cache state
- Login problems → Review auth logs
- Slow performance → Check metrics
- Data inconsistency → Run integrity checks

## 🎯 Best Practices

### Daily Tasks

- ✅ Check system health dashboard
- ✅ Review error logs
- ✅ Monitor API usage
- ✅ Address support tickets
- ✅ Verify backup completion

### Weekly Tasks

- 📊 Generate usage reports
- 🔍 Review security logs
- 💾 Database maintenance
- 📈 Performance analysis
- 👥 Team sync meeting

### Monthly Tasks

- 🔐 Security audit
- 💰 Billing reconciliation
- 📊 Business metrics review
- 🔄 Update procedures
- 📚 Documentation updates

## 🚀 Deployment & Scaling

### Infrastructure Management

**Scaling Triggers:**

- CPU usage > 70%
- Memory usage > 80%
- Request queue depth
- Response time degradation
- Storage capacity

**Scaling Actions:**

- Horizontal pod scaling
- Database read replicas
- Cache cluster expansion
- CDN optimization
- Load balancer tuning

### Deployment Process

**Production Deployment:**

1. Code review approval
2. Automated testing
3. Staging deployment
4. QA verification
5. Production rollout
6. Health monitoring
7. Rollback ready

---

**Need admin support?** Contact the infrastructure team or check the [internal wiki](https://internal.tripsage.ai/wiki) for detailed procedures.

> Remember: With great power comes great responsibility. Always follow security protocols and audit requirements! 🔐
