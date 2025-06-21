# 🔧 TripSage Operators Documentation Archive

> **ARCHIVED: June 16, 2025 - Backup created during documentation consolidation**  
> **Status**: Restored from archive for reference preservation  
> **Current Documentation**: See [docs/operators/](../../operators/) for active operator documentation

> **Historical Note**: This backup contains comprehensive documentation for TripSage operators covering deployment, configuration, security, and operational procedures as they existed before the consolidation effort.

## 📂 Documentation Structure

### 🚀 Deployment & Installation

| Document | Purpose | Scope |
|----------|---------|-------|
| [Installation Guide](INSTALLATION_GUIDE.md) | Complete setup instructions | Development & Production |
| [Production Deployment](PRODUCTION_DEPLOYMENT.md) | Production deployment guide | Production environment |
| [Supabase Production Setup](SUPABASE_PRODUCTION_SETUP.md) | Supabase production configuration | Database & Auth |
| [Deployment Strategy](DEPLOYMENT_STRATEGY.md) | CI/CD and deployment architecture | All environments |
| [Node.js Compatibility](NODEJS_COMPATIBILITY_GUIDE.md) | Node.js version requirements | Frontend deployment |

### ⚙️ Configuration Management

| Document | Purpose | Environment |
|----------|---------|-------------|
| [Environment Variables](ENVIRONMENT_VARIABLES.md) | All environment variables reference | 🌍 All environments |
| [Settings Reference](SETTINGS_REFERENCE.md) | Application settings & options | 📊 Configuration |
| [Deployment Configs](DEPLOYMENT_CONFIGS.md) | Deployment-specific configurations | 🚀 Production |
| [OAuth Setup Guide](OAUTH_SETUP_GUIDE.md) | OAuth authentication configuration | 🔐 Authentication |
| [Extensions & Automation](EXTENSIONS_AND_AUTOMATION.md) | Database extensions & automation | 🔧 Infrastructure |

### 🔒 Security Documentation

| Document | Purpose | Priority |
|----------|---------|----------|
| [Security Overview](SECURITY_OVERVIEW.md) | Overall security architecture | High |
| [Security Best Practices](SECURITY_BEST_PRACTICES.md) | Security implementation guidelines | High |
| [RLS Implementation](RLS_IMPLEMENTATION.md) | Row-Level Security configuration | Critical |
| [Security Testing](SECURITY_TESTING.md) | Security testing procedures | High |
| [Security Runbook](security-runbook.md) | Security incident response | Critical |

### 📊 Operations & Monitoring

| Document | Purpose | Status |
|----------|---------|--------|
| [Infrastructure Upgrade Summary](INFRASTRUCTURE_UPGRADE_SUMMARY.md) | Recent infrastructure changes | ✅ Complete |
| [Monitoring Setup](monitoring-setup.md) | Monitoring & observability config | 📝 Stub |
| [Backup Procedures](backup-procedures.md) | Backup and restoration guide | 📝 Stub |
| [Disaster Recovery](disaster-recovery.md) | DR planning and procedures | 📝 Stub |
| [Scaling Guide](scaling-guide.md) | Horizontal and vertical scaling | 📝 Stub |
| [Troubleshooting Guide](troubleshooting-guide.md) | Common issues and solutions | 📝 Stub |

## 🌍 Environment Setup

### **Development Environment**

```bash
# Core API Keys (Required)
OPENAI_API_KEY=sk-your-openai-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# External Service Keys
GOOGLE_MAPS_API_KEY=your-google-maps-key
DUFFEL_API_TOKEN=your-duffel-token
OPENWEATHERMAP_API_KEY=your-weather-key

# Infrastructure
DRAGONFLY_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost:5432/tripsage

# Development Settings
DEBUG=true
LOG_LEVEL=debug
ENVIRONMENT=development
```

### **Production Environment**

```bash
# Security (Required)
SECRET_KEY=your-256-bit-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-fernet-encryption-key

# Database (Production)
DATABASE_URL=postgresql://prod-user:secure-pass@prod-host:5432/tripsage
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Caching (Production)
DRAGONFLY_URL=redis://prod-cache:6379
CACHE_TTL=3600
CACHE_MAX_SIZE=1000000

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=https://api.honeycomb.io
OTEL_SERVICE_NAME=tripsage-api
GRAFANA_URL=https://your-grafana.com
```

## 🚩 Feature Flags

### **Core Feature Flags**

```python
# Infrastructure Toggles
FEATURE_CACHE_PROVIDER: dragonfly  # DragonflyDB is now the default
FEATURE_DATABASE_PROVIDER: supabase
FEATURE_VECTOR_SEARCH: pgvector

# AI Features
FEATURE_MEMORY_SYSTEM: mem0 | neo4j | disabled
FEATURE_AGENT_ORCHESTRATION: langgraph | simple
FEATURE_CONVERSATION_HISTORY: enabled | disabled

# External Integrations
FEATURE_FLIGHT_SEARCH: duffel | amadeus | disabled
FEATURE_ACCOMMODATION_SEARCH: airbnb | booking | disabled
FEATURE_WEATHER_SERVICE: openweathermap | disabled
```

### **Gradual Rollout Flags**

```python
# Percentage-based rollouts
ROLLOUT_NEW_SEARCH_UI: 25  # 25% of users
ROLLOUT_ENHANCED_MEMORY: 10  # 10% of users
ROLLOUT_AGENT_HANDOFFS: 50  # 50% of users

# User segment flags
PREMIUM_FEATURES_ENABLED: true
BETA_FEATURES_ENABLED: false
ENTERPRISE_FEATURES_ENABLED: true
```

## 📊 Application Settings

### **API Configuration**

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  reload: false
  access_log: true
  
  cors:
    allow_origins: ["https://app.tripsage.ai"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["*"]
    allow_credentials: true

  rate_limiting:
    default_limit: "1000/hour"
    burst_limit: "100/minute"
    premium_limit: "10000/hour"
```

### **Database Configuration**

```yaml
database:
  url: "${DATABASE_URL}"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  
  migrations:
    auto_upgrade: false
    backup_before_migration: true
    
  vector_search:
    index_type: "hnsw"
    m: 16
    ef_construction: 200
    ef: 100
```

### **Caching Configuration**

```yaml
cache:
  backend: "dragonfly"
  url: "${DRAGONFLY_URL}"
  ttl: 3600
  max_size: 1000000
  
  settings:
    compression: true
    serializer: "pickle"
    key_prefix: "tripsage:"
    
  policies:
    search_results: 300  # 5 minutes
    user_preferences: 86400  # 24 hours
    static_data: 604800  # 7 days
```

## 🔒 Security Configuration

### **Authentication Settings**

```yaml
auth:
  jwt:
    algorithm: "HS256"
    access_token_expire: 3600  # 1 hour
    refresh_token_expire: 604800  # 7 days
    
  api_keys:
    default_permissions: ["read:trips", "write:trips"]
    max_keys_per_user: 10
    
  oauth:
    google:
      client_id: "${GOOGLE_OAUTH_CLIENT_ID}"
      client_secret: "${GOOGLE_OAUTH_CLIENT_SECRET}"
      scopes: ["openid", "email", "profile"]
```

### **Encryption Settings**

```yaml
encryption:
  algorithm: "fernet"  # AES-128 CBC + HMAC-SHA256
  key: "${ENCRYPTION_KEY}"
  
  fields:
    - "user.api_keys"
    - "user.oauth_tokens"
    - "trip.payment_info"
    
security:
  rate_limiting:
    enabled: true
    default_limit: "100/hour"
    
  audit_logging:
    enabled: true
    log_requests: true
    log_responses: false
    sensitive_fields: ["password", "api_key"]
```

## 📝 Logging Configuration

### **Log Levels**

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "json"
  
  loggers:
    tripsage: "INFO"
    tripsage.agents: "DEBUG"
    tripsage.memory: "INFO"
    uvicorn: "WARNING"
    sqlalchemy.engine: "WARNING"
    
  handlers:
    console:
      enabled: true
      format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
      
    file:
      enabled: true
      filename: "/var/log/tripsage/app.log"
      max_bytes: 10485760  # 10MB
      backup_count: 5
      
    structured:
      enabled: true
      format: "json"
      fields: ["timestamp", "level", "logger", "message", "context"]
```

## 📈 Monitoring Configuration

### **OpenTelemetry Setup**

```yaml
telemetry:
  service_name: "tripsage-api"
  service_version: "2.0.0"
  
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "${OTEL_EXPORTER_OTLP_ENDPOINT}"
    headers:
      "x-honeycomb-team": "${HONEYCOMB_API_KEY}"
      
  metrics:
    enabled: true
    export_interval: 30000  # 30 seconds
    
  instrumentation:
    fastapi: true
    sqlalchemy: true
    redis: true
    httpx: true
```

### **Health Checks**

```yaml
health:
  endpoint: "/health"
  checks:
    database:
      enabled: true
      timeout: 5
      
    cache:
      enabled: true
      timeout: 2
      
    external_services:
      enabled: true
      timeout: 10
      services: ["openai", "supabase", "google_maps"]
      
  intervals:
    liveness: 30  # seconds
    readiness: 10  # seconds
```

## 🚀 Deployment Configurations

### **Docker Configuration**

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    image: tripsage/api:latest
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - DRAGONFLY_URL=${DRAGONFLY_URL}
      - DRAGONFLY_PASSWORD=${DRAGONFLY_PASSWORD}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - dragonfly
      
  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly
    command: dragonfly --logtostderr
    ports:
      - "6379:6379"
    volumes:
      - dragonfly_data:/data
```

### **Kubernetes Configuration**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tripsage-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: tripsage/api:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: tripsage-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## 🔗 Configuration Templates

### **Environment Templates**

- **[.env.development]**: Development environment template
- **[.env.staging]**: Staging environment template
- **[.env.production]**: Production environment template
- **[.env.test]**: Test environment template

### **Infrastructure Templates**

- **[docker-compose.dev.yml]**: Development Docker setup
- **[docker-compose.prod.yml]**: Production Docker setup
- **[k8s-manifests/]**: Kubernetes deployment manifests

## 🔗 Related Documentation

### **Setup & Installation**

- **[Getting Started](../01_GETTING_STARTED/README.md)** - Initial setup
- **[Development Guide](../developers/README.md)** - Developer resources
- **[API Reference](../06_API_REFERENCE/README.md)** - API documentation

### **Architecture & Design**

- **[System Overview](../03_ARCHITECTURE/SYSTEM_OVERVIEW.md)** - Architecture overview
- **[Database Architecture](../03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)** - Database design
- **[WebSocket Infrastructure](../03_ARCHITECTURE/WEBSOCKET_INFRASTRUCTURE.md)** - Real-time features

---

*This operators section provides comprehensive guidance for deploying, configuring, and managing TripSage across development, staging, and production environments. For development-focused documentation, see the [developers](../developers/) section.*
