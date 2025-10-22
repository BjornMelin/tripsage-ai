# TripSage Deployment Guide

## Overview

This guide covers deploying TripSage with containerization, security best practices,
and monitoring. The application is designed for Python 3.13+ and follows cloud-native deployment patterns.

## Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Access to Supabase project
- OpenAI API key
- Redis/DragonflyDB instance (optional)

## Deployment Environments

### Development Deployment

#### Local Development with Docker

```bash
# 1. Clone and setup
git clone <repository>
cd tripsage
cp .env.example .env

# 2. Configure environment
# Edit .env with your development values
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=https://your-dev-project.supabase.co
DATABASE_SERVICE_KEY=your-dev-service-key
OPENAI_API_KEY=your-openai-key

# 3. Build and run
docker-compose up --build
```

#### Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  tripsage:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    env_file:
      - .env.development
    volumes:
      - .:/app
      - /app/.venv  # Cache Python packages
    command: uvicorn tripsage.api.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - redis

  redis:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    ports:
      - "6379:6379"
    command: --logtostderr --cache_mode
    volumes:
      - dragonfly_data:/data

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: pnpm dev

volumes:
  dragonfly_data:
```

### Production Deployment

#### Production Docker Configuration

```dockerfile
# Dockerfile.production
FROM python:3.13-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Production stage
FROM base as production
ENV ENVIRONMENT=production
ENV DEBUG=false
ENV PYTHONPATH=/app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "tripsage.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  tripsage:
    build:
      context: .
      dockerfile: Dockerfile.production
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    secrets:
      - database_service_key
      - database_jwt_secret
      - secret_key
      - openai_api_key
    volumes:
      - /run/secrets:/run/secrets:ro
    depends_on:
      - redis
      - postgres
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tripsage.rule=Host(`api.tripsage.com`)"
      - "traefik.http.routers.tripsage.tls=true"
      - "traefik.http.routers.tripsage.tls.certresolver=letsencrypt"

  redis:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    restart: unless-stopped
    command: --logtostderr --cache_mode --requirepass_file=/run/secrets/redis_password
    secrets:
      - redis_password
    volumes:
      - dragonfly_data:/data
    ports:
      - "127.0.0.1:6379:6379"

  traefik:
    image: traefik:v3.0
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - ./acme.json:/acme.json
    labels:
      - "traefik.enable=true"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.production
    restart: unless-stopped
    environment:
      - NODE_ENV=production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`tripsage.com`)"
      - "traefik.http.routers.frontend.tls=true"

secrets:
  database_service_key:
    file: ./secrets/database_service_key.txt
  database_jwt_secret:
    file: ./secrets/database_jwt_secret.txt
  secret_key:
    file: ./secrets/secret_key.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
  redis_password:
    file: ./secrets/redis_password.txt

volumes:
  dragonfly_data:
    driver: local
```

## Cloud Deployment

### AWS ECS Deployment

#### Task Definition

```json
{
  "family": "tripsage",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "tripsage",
      "image": "your-registry/tripsage:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "DEBUG",
          "value": "false"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_SERVICE_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:tripsage/database-service-key"
        },
        {
          "name": "OPENAI_API_KEY", 
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:tripsage/openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tripsage",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Google Cloud Run

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: tripsage
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      serviceAccountName: tripsage-service-account
      containers:
      - image: gcr.io/PROJECT-ID/tripsage:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DEBUG
          value: "false"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-url
              key: url
        - name: DATABASE_SERVICE_KEY
          valueFrom:
            secretKeyRef:
              name: database-service-key
              key: key
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tripsage
  labels:
    app: tripsage
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tripsage
  template:
    metadata:
      labels:
        app: tripsage
    spec:
      containers:
      - name: tripsage
        image: your-registry/tripsage:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DEBUG
          value: "false"
        envFrom:
        - secretRef:
            name: tripsage-secrets
        resources:
          limits:
            cpu: "1000m"
            memory: "2Gi"
          requests:
            cpu: "500m"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL

---
apiVersion: v1
kind: Service
metadata:
  name: tripsage-service
spec:
  selector:
    app: tripsage
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tripsage-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.tripsage.com
    secretName: tripsage-tls
  rules:
  - host: api.tripsage.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tripsage-service
            port:
              number: 80
```

## Security Configuration

### Production Security Checklist

- [ ] **Secrets Management**: Use secret management service (AWS Secrets Manager, etc.)
- [ ] **HTTPS Only**: Enforce HTTPS in production
- [ ] **Non-root User**: Run containers as non-root user
- [ ] **Network Isolation**: Use private networks and security groups
- [ ] **Resource Limits**: Set CPU and memory limits
- [ ] **Health Checks**: Configure liveness and readiness probes
- [ ] **Logging**: Centralized logging with structured format
- [ ] **Monitoring**: Application and infrastructure monitoring
- [ ] **Backup**: Database backup strategy

### Environment-Specific Security

```bash
# Production security validation
python -c "
from tripsage_core.config import get_settings
settings = get_settings()
report = settings.get_security_report()
if not report['production_ready']:
    print('❌ Security issues detected:')
    for warning in report['warnings']:
        print(f'  - {warning}')
    exit(1)
else:
    print('✅ Production security validation passed')
"
```

### Secrets Management

#### AWS Secrets Manager Integration

```python
# scripts/deploy/setup_secrets.py
import boto3
import json

def setup_aws_secrets():
    """Setup secrets in AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    
    secrets = {
        'tripsage/database-service-key': 'your-actual-service-key',
        'tripsage/database-jwt-secret': 'your-actual-jwt-secret',
        'tripsage/secret-key': 'your-actual-secret-key',
        'tripsage/openai-api-key': 'your-actual-openai-key',
    }
    
    for secret_name, secret_value in secrets.items():
        try:
            client.create_secret(
                Name=secret_name,
                SecretString=secret_value,
                Description=f'TripSage {secret_name.split("/")[-1]}'
            )
            print(f'✅ Created secret: {secret_name}')
        except client.exceptions.ResourceExistsException:
            print(f'⚠️  Secret already exists: {secret_name}')

if __name__ == '__main__':
    setup_aws_secrets()
```

## Monitoring and Observability

### Health Checks

```python
# tripsage/api/endpoints/health.py
from fastapi import APIRouter, Depends, HTTPException
from tripsage_core.config import Settings, get_settings
import asyncio
import aioredis
from supabase import create_client

router = APIRouter()

@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """Health check endpoint."""
    checks = {
        "status": "healthy",
        "environment": settings.environment,
        "checks": {}
    }
    
    # Database health check
    try:
        supabase = create_client(
            str(settings.database_url),
            settings.database_service_key.get_secret_value()
        )
        # Simple query to test connection
        result = supabase.table('_health').select('*').limit(1).execute()
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # Redis health check (if configured)
    if settings.redis_url:
        try:
            redis = aioredis.from_url(str(settings.redis_url))
            await redis.ping()
            checks["checks"]["redis"] = "healthy"
            await redis.close()
        except Exception as e:
            checks["checks"]["redis"] = f"unhealthy: {str(e)}"
            checks["status"] = "unhealthy"
    
    # Security validation
    security_report = settings.get_security_report()
    checks["checks"]["security"] = "healthy" if security_report["production_ready"] else "warnings"
    checks["security_warnings"] = security_report.get("warnings", [])
    
    if checks["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=checks)
    
    return checks

@router.get("/ready")
async def readiness_check():
    """Simple readiness check for load balancers."""
    return {"status": "ready"}
```

### OTEL Metrics

```python
# tripsage/observability/metrics.py
from opentelemetry import metrics
from fastapi import Request
import time

meter = metrics.get_meter("tripsage")
REQ_COUNT = meter.create_counter(
    "http.server.requests", description="HTTP requests"
)
REQ_DURATION = meter.create_histogram(
    "http.server.duration", unit="s", description="HTTP request duration"
)

# Middleware for metrics collection
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    # Record OTEL metrics
    duration = time.time() - start_time
    attrs = {
        "http.method": request.method,
        "http.route": request.url.path,
        "http.status_code": response.status_code,
    }
    REQ_DURATION.record(duration, attrs)
    REQ_COUNT.add(1, attrs)
    return response

# With OpenTelemetry, export metrics via OTLP using the OTEL Collector.
# A simple FastAPI middleware example using OTEL is provided in metrics docs.
```

### Structured Logging

```python
# tripsage/observability/logging.py
import structlog
import logging.config
from tripsage_core.config import get_settings

def setup_logging():
    """Setup structured logging with JSON output."""
    settings = get_settings()
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "default": {
                "level": settings.log_level,
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["default"],
        },
    })
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy TripSage

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python 3.13
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[test,lint]
    
    - name: Lint with ruff
      run: |
        ruff check .
        ruff format --check .
    
    - name: Type check with mypy
      run: mypy .
    
    - name: Test with pytest
      run: pytest --cov=tripsage --cov=tripsage_core
    
    - name: Security scan with bandit
      run: bandit -r tripsage tripsage_core

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: Dockerfile.production
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      run: |
        # Add your deployment script here
        echo "Deploying to production..."
```

## Database Migrations

### Production Migration Script

```bash
#!/bin/bash
# scripts/deploy/migrate.sh

set -e

echo "🚀 Starting TripSage production migration..."

# 1. Validate configuration
echo "📋 Validating configuration..."
python -c "
from tripsage_core.config import validate_configuration
if not validate_configuration():
    print('❌ Configuration validation failed')
    exit(1)
print('✅ Configuration validation passed')
"

# 2. Check database connectivity
echo "🔌 Testing database connection..."
python scripts/database/test_connection.py

# 3. Run database migrations
echo "📊 Running database migrations..."
python scripts/database/run_migrations.py

# 4. Validate deployment
echo "🔍 Validating deployment..."
curl -f http://localhost:8000/health || {
    echo "❌ Health check failed"
    exit 1
}

echo "✅ Migration completed successfully!"
```

## Troubleshooting

### Common Deployment Issues

1. **Configuration Validation Errors**

   ```bash
   # Check configuration
   python -c "from tripsage_core.config import get_settings; print(get_settings().get_security_report())"
   ```

2. **Database Connection Issues**

   ```bash
   # Test database connection
   python -c "
   from tripsage_core.config import get_settings
   from supabase import create_client
   settings = get_settings()
   client = create_client(str(settings.database_url), settings.database_service_key.get_secret_value())
   print('Database connection successful')
   "
   ```

3. **Secret Management Issues**

   ```bash
   # Verify secrets are loaded correctly
   python -c "
   from tripsage_core.config import get_settings
   settings = get_settings()
   print('Secrets validation:', settings.validate_secrets_security())
   "
   ```

4. **Container Health Check Failures**

   ```bash
   # Debug health endpoint
   curl -v http://localhost:8000/health
   
   # Check container logs
   docker logs tripsage-container
   ```

### Performance Optimization

1. **Container Resource Tuning**
   - Monitor CPU and memory usage
   - Adjust worker count based on load
   - Use connection pooling for databases

2. **Caching Strategy**
   - Configure Redis for session storage
   - Implement application-level caching
   - Use CDN for static assets

3. **Database Optimization**
   - Monitor query performance
   - Implement proper indexing
   - Use read replicas for scaling

This deployment guide provides coverage of deploying TripSage in various environments with proper security, monitoring, and observability practices.
