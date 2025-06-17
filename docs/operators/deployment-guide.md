# 🚀 TripSage Deployment Guide

> **Platform Selection | CI/CD Strategy | Production Deployment**
> Complete deployment strategy from development to production

## 📋 Table of Contents

- [Platform Comparison & Cost Calculator](#platform-comparison--cost-calculator)
- [CI/CD Strategy](#cicd-strategy)  
- [Production Deployment](#production-deployment)
- [Monitoring & Operations](#monitoring--operations)

---

## Platform Comparison & Cost Calculator

- [Cost Calculator & Planning](#-cost-calculator--planning)
- [Vercel Deployment (Recommended)](#-vercel-deployment-recommended)
- [Alternative Platforms](#-alternative-platforms)
- [Cost Optimization Strategies](#-cost-optimization-strategies)
- [Monitoring & Maintenance](#-monitoring--maintenance)

## 🚀 Quick Start Deployment

### Recommended Platform: Vercel

**Best for**: Modern web applications, Next.js optimization, serverless functions

```bash
# 1-Minute Deploy
git clone https://github.com/your-org/tripsage-ai
cd tripsage-ai/frontend
pnpm install
vercel --prod

# Or via Vercel Dashboard
# 1. Visit vercel.com/new
# 2. Import GitHub repository
# 3. Configure environment variables
# 4. Deploy automatically
```

### Required Environment Variables

```bash
# Core Configuration
NEXT_PUBLIC_API_URL=https://api.tripsage.ai
NEXT_PUBLIC_ENVIRONMENT=production

# Database & Auth
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXTAUTH_URL=https://your-domain.vercel.app
NEXTAUTH_SECRET=your-secure-secret-key

# External Services
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...

# Monitoring & Analytics
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=your-analytics-id
SENTRY_DSN=https://...@sentry.io/...
```

## 📊 Platform Comparisons

| Platform | Best For | Cost Range | Setup Time | Pros | Cons |
|----------|----------|------------|------------|------|------|
| **Vercel** | Next.js apps, serverless | $0-200/month | 5 min | Excellent Next.js support, automatic optimization | Can get expensive at scale |
| **Netlify** | Static sites, edge functions | $0-150/month | 10 min | Strong static hosting, good free tier | Less optimal for dynamic apps |
| **Railway** | Simple container deployment | $5-100/month | 15 min | Simple pricing, database included | Limited scaling options |
| **AWS Amplify** | Enterprise, complex integrations | $20-500/month | 30 min | Full AWS ecosystem, enterprise features | Complex setup, steep learning curve |
| **Self-Hosted** | Maximum control, predictable costs | $10-200/month | 2-4 hours | Full control, predictable pricing | Requires DevOps expertise |

## 💰 Cost Calculator & Planning

### Traffic-Based Estimates

#### Calculate Your Requirements

```plaintext
Monthly Visitors: _____ 
Page Views per Visitor: _____ 
Average Page Size: _____ KB
API Calls per Page: _____
Function Execution Time: _____ ms
```

#### Calculation Formulas

```bash
# Bandwidth Calculation
Monthly Bandwidth = Visitors × Page Views × Page Size × 1.2 (overhead)
Example: 50,000 × 5 × 500KB × 1.2 = 150 GB/month

# Edge Requests Calculation
Monthly Edge Requests = Visitors × Page Views × (API Calls + 3 static)
Example: 50,000 × 5 × (8 + 3) = 2.75M requests/month

# Function Duration Calculation
Monthly Function Hours = (API Calls × Execution Time × Visitors × Page Views) / 3,600,000
Example: (8 × 200ms × 50,000 × 5) / 3,600,000 = 1.11 GB-hours/month
```

### Cost Examples by Business Type

#### 🏠 Personal Travel Blog (10K visitors/month)

- **Bandwidth**: ~30 GB
- **Edge Requests**: ~200,000
- **Function Time**: 0.5 GB-hours
- **Recommended**: Vercel Hobby (Free)
- **Monthly Cost**: **$0**

#### 🚀 Growing Travel Startup (25K visitors/month)

- **Bandwidth**: ~200 GB
- **Edge Requests**: ~2.5M
- **Function Time**: 15 GB-hours
- **Recommended**: Vercel Pro
- **Monthly Cost**: **$20-30**

#### 🏢 Established Platform (100K visitors/month)

- **Bandwidth**: ~800 GB
- **Edge Requests**: ~15M
- **Function Time**: 80 GB-hours
- **Recommended**: Vercel Pro + overages
- **Monthly Cost**: **$60-85**

#### 🌍 Enterprise Solution (500K+ visitors/month)

- **Bandwidth**: 3+ TB
- **Edge Requests**: 50M+
- **Function Time**: 500+ GB-hours
- **Recommended**: Vercel Enterprise
- **Monthly Cost**: **$500-2,000+**

## 🔧 Vercel Deployment (Recommended)

### 1. Project Configuration

Create `vercel.json` in project root:

```json
{
  "framework": "nextjs",
  "buildCommand": "cd frontend && pnpm build",
  "outputDirectory": "frontend/.next",
  "installCommand": "cd frontend && pnpm install --frozen-lockfile",
  "devCommand": "cd frontend && pnpm dev",
  "regions": ["iad1", "fra1"],
  "functions": {
    "frontend/src/app/api/**/*.ts": {
      "runtime": "nodejs20.x",
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "Referrer-Policy",
          "value": "origin-when-cross-origin"
        }
      ]
    }
  ]
}
```

### 2. Performance Optimization

```typescript
// next.config.ts
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable SWC minification
  swcMinify: true,
  
  // Compress images
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
  },
  
  // Enable experimental features
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  
  // Bundle analyzer for production
  ...(process.env.ANALYZE === 'true' && {
    bundleAnalyzer: {
      enabled: true,
    },
  }),
}

export default nextConfig
```

### 3. Custom Domain Setup

```dns
# For apex domain (tripsage.ai)
A     @     76.76.19.61
AAAA  @     2600:1f13:e42:ad00::1

# For subdomain (app.tripsage.ai)
CNAME app   cname.vercel-dns.com
```

## 🌐 Alternative Platforms

### 1. Netlify Deployment

```bash
# Install Netlify CLI
npm install -g netlify-cli
netlify login
netlify deploy --prod
```

**Cost Structure**:

- Free: 100GB bandwidth, 300 build minutes
- Pro ($19/month): 400GB bandwidth, 25,000 function invocations

### 2. Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway deploy
```

**Cost Structure**:

- Starter: $5/month (512MB RAM, shared CPU)
- Pro: $20-50/month (1-2GB RAM, dedicated CPU)

### 3. AWS Amplify

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli
amplify configure
amplify init
amplify publish
```

**Cost Structure**:

- Small app: $10-20/month
- Medium app: $30-60/month
- Large app: $100-300/month

### 4. Self-Hosted VPS

```bash
# Example Docker deployment
docker build -t tripsage-frontend .
docker run -p 3000:3000 tripsage-frontend
```

**Cost Structure**:

- Basic VPS: $5-10/month (1GB RAM, 1 CPU)
- Production VPS: $20-40/month (4GB RAM, 2 CPU)
- CDN: $5-20/month (Cloudflare Pro)

## 🎯 Cost Optimization Strategies

### For Small Projects (< 10K visitors)

1. **Static Generation**: Pre-render pages when possible
2. **Image Optimization**: Use Next.js Image optimization
3. **Minimal API Calls**: Batch requests, implement caching
4. **Free Tier Usage**: Maximize free tier benefits

### For Growing Projects (10K-100K visitors)

1. **Edge Caching**: Implement caching for API responses
2. **Code Splitting**: Reduce initial bundle size
3. **Database Optimization**: Efficient queries, connection pooling
4. **Usage Monitoring**: Set up spend alerts

### For Large Projects (100K+ visitors)

1. **CDN Strategy**: External CDN for static assets
2. **Function Optimization**: Reduce execution time and memory
3. **Database Scaling**: Read replicas, caching layers
4. **Cost Analytics**: Detailed usage analysis and optimization

### Universal Optimization Tips

#### 1. Reduce Function Execution Time

```typescript
// Implement caching
export const revalidate = 3600 // 1 hour

// Use React cache for expensive operations
import { cache } from 'react'
const getExpensiveData = cache(async () => {
  // Expensive operation
})
```

#### 2. Minimize Data Transfer

- Enable compression
- Optimize images (WebP/AVIF)
- Use CDN for static assets

#### 3. Smart Caching Policies

```yaml
cache_policies:
  search_results: 300      # 5 minutes
  user_preferences: 86400  # 24 hours
  static_data: 604800      # 7 days
```

## 📈 Monitoring & Maintenance

### Analytics Setup

```typescript
// Add to app/layout.tsx
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/next'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
```

### Error Monitoring

```bash
# Install Sentry
pnpm add @sentry/nextjs

# Configure in sentry.client.config.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
})
```

### Performance Budget

```json
{
  "scripts": {
    "analyze": "ANALYZE=true pnpm build",
    "lighthouse": "lhci autorun"
  }
}
```

### Key Metrics to Track

- **Core Web Vitals**: LCP, FID, CLS
- **Load Time**: <3 seconds
- **Bundle Size**: <1MB initial load
- **Function Duration**: <10 seconds average

## 🚨 Troubleshooting

### Common Issues

#### Build Failures

```bash
# Check build logs in platform dashboard
pnpm install --frozen-lockfile  # Dependency issues
pnpm type-check                 # TypeScript errors
pnpm lint --fix                 # Linting errors
```

#### Environment Variable Issues

- Verify in platform dashboard
- Check preview vs production environments
- Ensure NEXT_PUBLIC_ prefix for client-side vars

#### Function Timeout

```json
// Platform configuration
{
  "functions": {
    "frontend/src/app/api/**/*.ts": {
      "maxDuration": 30
    }
  }
}
```

#### Large Bundle Size

```bash
# Analyze bundle
pnpm analyze

# Common optimizations:
# - Dynamic imports for large components
# - Tree-shake unused dependencies
# - Optimize images and assets
```

## 📅 Growth Planning Timeline

### Year 1: MVP Launch

- **Target**: 1,000-5,000 monthly users
- **Platform**: Vercel Hobby/Pro
- **Estimated cost**: $0-40/month
- **Focus**: Product development, user feedback

### Year 2: Market Expansion

- **Target**: 10,000-50,000 monthly users
- **Platform**: Vercel Pro
- **Estimated cost**: $50-150/month
- **Focus**: Performance optimization, feature expansion

### Year 3: Scale & Optimize

- **Target**: 50,000-200,000 monthly users
- **Platform**: Vercel Pro/Enterprise or multi-cloud
- **Estimated cost**: $200-800/month
- **Focus**: Infrastructure optimization, cost management

## ⚠️ Hidden Costs to Consider

### Additional Services

- **Database hosting**: $20-100/month (Supabase, PlanetScale)
- **External APIs**: $50-500/month (Maps, payments, etc.)
- **Monitoring tools**: $10-50/month (Sentry, DataDog)
- **Email service**: $10-100/month (SendGrid, Postmark)
- **Analytics**: $0-200/month (Mixpanel, Amplitude)

### Development Tools

- **Design tools**: $10-50/month (Figma, Adobe)
- **Testing tools**: $20-100/month (Playwright Cloud, Percy)
- **CI/CD**: $0-100/month (additional runners, storage)

### Compliance & Security

- **SSL certificates**: $0-200/year (Let's Encrypt free, premium certs)
- **Security scanning**: $50-500/month (Snyk, Dependabot Pro)
- **Compliance tools**: $100-1000/month (SOC2, PCI-DSS)

## 🎯 Platform Selection Guide

### Choose Vercel If

- Using Next.js or React
- Want zero-config deployment
- Need excellent performance out-of-the-box
- Budget allows for usage-based pricing

### Choose Netlify If

- Building mostly static sites
- Need strong free tier
- Want alternative to Vercel

### Choose Railway If

- Want simple, predictable pricing
- Need database included
- Prefer container-based deployment

### Choose Self-Hosted If

- Monthly costs exceed $200
- Need specific compliance requirements
- Want predictable, fixed costs
- Have DevOps expertise

---

*This deployment configuration guide provides comprehensive guidance for choosing the right platform and optimizing costs throughout your application's growth journey.*
-e
---

## CI/CD Strategy

- **Frontend**: Next.js application serving the user interface
- **Backend API**: FastAPI service handling core business logic
- **Direct SDK Integrations**: Simplified service integrations for different domains
  - Flight APIs (direct SDK integration)
  - Accommodation APIs (direct SDK integration)
  - Google Maps SDK (location services)
  - Time services (direct SDK)
  - Weather services (direct SDK)
- **Database**: Unified Supabase PostgreSQL with pgvector for all data storage
- **Memory System**: Mem0 with PostgreSQL backend for intelligent memory management

### 1.2 Infrastructure Components

The deployment infrastructure includes:

- **Containerization**: Docker for packaging applications
- **Container Registry**: GitHub Container Registry (GHCR)
- **Orchestration**: Kubernetes for production, Docker Compose for development
- **Hosting**: Vercel for frontend, managed Kubernetes for backend services
- **Database**: Managed Supabase instance
- **Caching**: DragonflyDB (Redis-compatible) for high-performance caching
- **Monitoring**: Datadog for observability
- **CDN**: Vercel Edge Network

## 2. Environments

TripSage uses the following environments:

### 2.1 Development

- **Purpose**: Individual developer environments
- **Infrastructure**: Local Docker Compose
- **Database**: Local Supabase instance
- **Deployment**: Manual, via Docker Compose
- **Branch Strategy**: Feature branches

### 2.2 Staging

- **Purpose**: Integration testing and pre-production validation
- **Infrastructure**: Kubernetes cluster (staging namespace)
- **Database**: Staging Supabase instance
- **Deployment**: Automated via CI/CD
- **Branch Strategy**: Main branch

### 2.3 Production

- **Purpose**: Live user-facing environment
- **Infrastructure**: Kubernetes cluster (production namespace)
- **Database**: Production Supabase instance
- **Deployment**: Automated via CI/CD with manual approval
- **Branch Strategy**: Release branches, tagged versions

## 3. Containerization Strategy

### 3.1 Docker Implementation

Each component of TripSage is containerized using Docker:

```dockerfile
# Example Dockerfile for FastAPI backend
FROM python:3.11-slim as base

WORKDIR /app

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Run with gunicorn for production
CMD ["gunicorn", "src.api.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 3.2 Multi-Stage Builds

For optimized container images, TripSage implements multi-stage builds:

```dockerfile
# Example multi-stage build for Next.js frontend
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

CMD ["npm", "start"]
```

### 3.3 Container Security

TripSage implements security best practices for containers:

- Non-root users in containers
- Minimal base images
- Security scanning with Trivy
- Immutable image tags using SHA digests
- Regular security audits and updates

## 4. CI/CD Pipeline Implementation

### 4.1 GitHub Actions Workflow

TripSage uses GitHub Actions for CI/CD automation:

```yaml
# .github/workflows/ci-cd.yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    tags: ["v*"]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest
      - name: Run linting
        run: ruff check .
      - name: Check types
        run: mypy src/

  build-and-push:
    needs: test
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=sha,format=short
            type=ref,event=branch
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build-and-push
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
      - name: Set up kubeconfig
        run: |
          mkdir -p $HOME/.kube
          echo "${{ secrets.KUBE_CONFIG }}" > $HOME/.kube/config
      - name: Update deployment
        run: |
          IMAGE_TAG=$(echo ${{ github.sha }} | cut -c1-7)
          kubectl set image deployment/tripsage-api api=ghcr.io/${{ github.repository }}:${IMAGE_TAG} -n staging
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/tripsage-api -n staging --timeout=180s

  deploy-production:
    needs: deploy-staging
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://tripsage.example.com
    steps:
      - uses: actions/checkout@v3
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
      - name: Set up kubeconfig
        run: |
          mkdir -p $HOME/.kube
          echo "${{ secrets.KUBE_CONFIG }}" > $HOME/.kube/config
      - name: Update deployment
        run: |
          VERSION=${GITHUB_REF#refs/tags/}
          kubectl set image deployment/tripsage-api api=ghcr.io/${{ github.repository }}:${VERSION} -n production
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/tripsage-api -n production --timeout=300s
```

### 4.2 Vercel Deployment

Frontend deployment leverages Vercel's Git integration:

```json
// vercel.json
{
  "version": 2,
  "builds": [{ "src": "package.json", "use": "@vercel/next" }],
  "routes": [{ "src": "/(.*)", "dest": "/$1" }],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.tripsage.example.com"
  },
  "github": {
    "enabled": true,
    "silent": true
  }
}
```

## 5. Deployment Strategies

### 5.1 Blue/Green Deployments

For zero-downtime deployments, TripSage implements a blue/green strategy:

1. Create new deployment (green) alongside existing deployment (blue)
2. Run tests and validation on green deployment
3. Switch traffic gradually from blue to green deployment
4. Monitor for issues and perform automated rollback if necessary
5. Terminate blue deployment when green is stable

Implementation in Kubernetes:

```yaml
# Kubernetes service for blue/green switching
apiVersion: v1
kind: Service
metadata:
  name: tripsage-api
  namespace: production
spec:
  selector:
    app: tripsage-api
    version: green # Switch between blue/green
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### 5.2 Canary Deployments

For riskier changes, TripSage implements canary deployments:

1. Deploy new version to a small subset of nodes (5-10%)
2. Monitor performance, errors, and user feedback
3. Gradually increase traffic to new version if metrics are satisfactory
4. Rollback immediately if issues are detected

Implementation using service mesh (Istio):

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: tripsage-api
spec:
  hosts:
    - api.tripsage.example.com
  http:
    - route:
        - destination:
            host: tripsage-api-v1
          weight: 90
        - destination:
            host: tripsage-api-v2
          weight: 10
```

### 5.3 Feature Flags

TripSage implements feature flags for controlled feature rollouts:

```python
# Example feature flag implementation
import os
from functools import lru_cache

@lru_cache()
def get_feature_flags():
    """Get feature flags from environment or config service."""
    return {
        "enable_new_search_algorithm": os.getenv("FEATURE_NEW_SEARCH", "false").lower() == "true",
        "enable_price_prediction": os.getenv("FEATURE_PRICE_PREDICTION", "false").lower() == "true",
        "enable_alternative_routes": os.getenv("FEATURE_ALTERNATIVE_ROUTES", "false").lower() == "true",
    }

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    return get_feature_flags().get(feature_name, False)
```

## 6. Kubernetes Configuration

### 6.1 Resource Management

TripSage defines resource requirements for all services:

```yaml
# Example deployment with resource limits
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tripsage-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tripsage-api
  template:
    metadata:
      labels:
        app: tripsage-api
    spec:
      containers:
        - name: api
          image: ghcr.io/organization/tripsage-api:v1.0.0
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### 6.2 Horizontal Pod Autoscaling

TripSage implements autoscaling based on metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tripsage-api
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tripsage-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 6.3 Config Maps and Secrets

Environment-specific configuration is managed via Config Maps and Secrets:

```yaml
# Example ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: tripsage-config
  namespace: production
data:
  LOG_LEVEL: "info"
  CACHE_TTL: "1800"
  API_RATE_LIMIT: "100"

# Example Secret (do not commit actual secrets)
apiVersion: v1
kind: Secret
metadata:
  name: tripsage-secrets
  namespace: production
type: Opaque
data:
  SUPABASE_URL: <base64_encoded_value>
  SUPABASE_KEY: <base64_encoded_value>
  JWT_SECRET: <base64_encoded_value>
```

## 7. Database Deployment

### 7.1 Supabase Configuration

TripSage uses Supabase for database storage, with separate projects for each environment:

- **Development**: Local Supabase or developer-specific cloud instance
- **Staging**: Dedicated staging Supabase project
- **Production**: Production Supabase project with high availability

### 7.2 Migration Strategy

Database migrations follow a structured approach:

1. Migrations are version-controlled in the `/migrations` directory
2. Each migration is numbered and timestamped (e.g., `20250508_01_initial_schema.sql`)
3. Migrations are applied automatically during CI/CD pipeline
4. Rollback scripts are provided for each migration

Example migration script:

```sql
-- Migration: 20250508_01_initial_schema.sql
-- Description: Initial schema setup
BEGIN;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trips table
CREATE TABLE IF NOT EXISTS trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    name TEXT NOT NULL,
    destination TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMIT;
```

## 8. Monitoring and Observability

### 8.1 Logging Strategy

TripSage implements structured logging:

```python
# Example structured logging
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, service_name):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)

    def _log(self, level, message, **kwargs):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level),
            json.dumps(log_data)
        )

    def info(self, message, **kwargs):
        self._log("INFO", message, **kwargs)

    def error(self, message, **kwargs):
        self._log("ERROR", message, **kwargs)

    def warning(self, message, **kwargs):
        self._log("WARNING", message, **kwargs)

    def debug(self, message, **kwargs):
        self._log("DEBUG", message, **kwargs)
```

### 8.2 Metrics Collection

Key metrics tracked for all services:

- Request rate and latency
- Error rate and types
- Resource usage (CPU, memory)
- Database query performance
- Cache hit/miss rates
- Business metrics (searches, bookings)

### 8.3 Dashboards and Alerts

TripSage uses Datadog for dashboards and alerts:

- **Service Dashboards**: Performance metrics for each service
- **Business Dashboards**: User activity and business KPIs
- **Alerts**: Configured for anomalies and SLA violations

## 9. Disaster Recovery

### 9.1 Backup Strategy

TripSage implements a comprehensive backup strategy:

- **Database**: Daily automated Supabase backups with 30-day retention
- **Configurations**: Version-controlled in Git
- **Container Images**: Immutable and preserved in registry
- **Knowledge Graph**: Daily Neo4j database dumps

### 9.2 Recovery Plans

Recovery time objectives (RTO) and recovery point objectives (RPO):

| Resource              | RPO       | RTO        |
| --------------------- | --------- | ---------- |
| Supabase Database     | 24 hours  | 1 hour     |
| Neo4j Knowledge Graph | 24 hours  | 2 hours    |
| Application Services  | Immediate | 10 minutes |
| Static Content        | Immediate | 5 minutes  |

### 9.3 Failover Procedures

Automated and manual failover procedures are documented for:

- Database failover
- Service instance failures
- Region or zone outages
- Cache failures

## 10. Security Considerations

### 10.1 Network Security

- Private Kubernetes cluster with limited ingress
- Service mesh for encrypted service-to-service communication
- Web Application Firewall (WAF) for public endpoints
- Network policies to restrict pod communication

### 10.2 Secret Management

- Kubernetes Secrets for sensitive configuration
- No secrets in container images or Git repositories
- Regular secret rotation
- Principle of least privilege for service accounts

### 10.3 Compliance and Auditing

- Audit logging for all administrative actions
- Compliance with data protection regulations
- Regular security scanning of containers and dependencies
- Penetration testing schedule

## 11. Deployment Checklist

Pre-deployment verification checklist:

- [ ] All tests passing in CI pipeline
- [ ] Security scans completed with no critical issues
- [ ] Documentation updated
- [ ] Database migrations tested
- [ ] Resource requirements verified
- [ ] Rollback plan documented
- [ ] On-call schedule confirmed
- [ ] Monitoring dashboards updated

## 12. Implementation Timeline

TripSage deployment infrastructure will be implemented in phases:

### Phase 1: Foundation (Month 1)

- Set up CI/CD pipelines
- Configure containerization
- Deploy staging environment
- Implement monitoring basics

### Phase 2: Production Readiness (Month 2)

- Set up production environment
- Implement blue/green deployments
- Configure autoscaling
- Establish backup and recovery

### Phase 3: Optimization (Month 3)

- Implement canary deployments
- Add advanced monitoring
- Optimize resource usage
- Conduct load testing

### Phase 4: Scaling (Month 4 onwards)

- Implement global CDN
- Add geographic redundancy
- Optimize for cost
- Implement advanced security measures

## Conclusion

This deployment and CI/CD strategy provides a comprehensive framework for deploying and maintaining the TripSage travel planning system. By implementing microservices architecture with containerization, automated CI/CD pipelines, and robust monitoring, TripSage can achieve rapid, reliable deployments while maintaining high availability and performance.

The strategy emphasizes modern best practices including zero-downtime deployments, infrastructure as code, and comprehensive observability, setting a foundation for scalable and maintainable infrastructure as the application grows.

## References

1. Kubernetes Documentation: [kubernetes.io/docs](https://kubernetes.io/docs/)
2. GitHub Actions Documentation: [docs.github.com/en/actions](https://docs.github.com/en/actions)
3. Vercel Deployment: [vercel.com/docs](https://vercel.com/docs)
4. "Implementing Content Caching Strategies", Equinix (2024)
5. "Modern Deployment Strategies", OpsLevel (2023)
6. "7 Best Practices For Optimizing Your Vercel Deployment", Kapsys (2024)
-e

---

## Production Deployment

- [ ] **Supabase Pro/Enterprise**: Required for pgvector, real-time features, and production SLA
- [ ] **DragonflyDB Instance**: High-performance cache deployment (25x faster than Redis)
- [ ] **Domain & SSL**: Production domain with SSL certificates
- [ ] **CI/CD Pipeline**: GitHub Actions or equivalent for automated deployment
- [ ] **Monitoring Stack**: Prometheus, Grafana, and alerting systems
- [ ] **Backup Strategy**: Automated database backups and disaster recovery plan

### Supabase Project Preparation

- [ ] **Plan Verification**: Confirm Supabase plan supports all required extensions
- [ ] **Extension Checklist**: pgvector, pg_cron, pg_net, pgcrypto, uuid-ossp
- [ ] **Resource Planning**: Estimate connection limits, storage, and compute requirements
- [ ] **Security Planning**: RLS policies, authentication configuration, API key management
- [ ] **Performance Planning**: Index optimization, connection pooling, cache configuration

### Application Readiness

- [ ] **Environment Configuration**: Production environment variables configured and secured
- [ ] **Database Schema**: All migrations tested and ready for deployment
- [ ] **Security Policies**: RLS policies implemented and tested
- [ ] **Real-time Features**: WebSocket integration and real-time subscriptions configured
- [ ] **Performance Optimization**: Indexes, connection pooling, and caching optimized
- [ ] **Health Checks**: Comprehensive health endpoints implemented
- [ ] **Monitoring Integration**: Application metrics and alerting configured
- [ ] **Testing Suite**: End-to-end tests passing in staging environment

## Deployment Steps

### 1. Supabase Project Setup

```bash
# Login and connect to Supabase
supabase login
supabase projects list

# Link to your production project
supabase link --project-ref [your-project-ref]

# Verify project connection
supabase status
```

**Enable Required Extensions:**

```sql
-- Execute in Supabase SQL Editor or via CLI
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_net";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### 2. Database Schema Deployment

```bash
# Deploy complete schema using consolidated migration
supabase db push

# Verify schema deployment
supabase db diff

# Check extension installation
psql -d "$DATABASE_URL" -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_cron', 'pg_net');"
```

### 3. Security Configuration

```bash
# Test RLS policies
psql -d "$DATABASE_URL" -c "SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# Verify authentication settings
curl -X POST "https://[project-ref].supabase.co/auth/v1/signup" \
  -H "apikey: [anon-key]" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

### 4. Application Deployment

```bash
# Deploy backend application
docker build -t tripsage-api:production .
docker run -d --name tripsage-api \
  --env-file .env.production \
  -p 8000:8000 \
  tripsage-api:production

# Deploy frontend application
cd frontend
npm run build
npm run start

# Verify deployment
curl https://api.your-domain.com/health
curl https://your-domain.com/api/health
```

**Environment Configuration:**

- [ ] **Production Variables**: All environment variables set and secured
- [ ] **API Keys**: Supabase keys configured correctly
- [ ] **Cache Configuration**: DragonflyDB connection configured
- [ ] **Memory System**: Mem0 integration configured
- [ ] **External APIs**: All service API keys configured

### 5. Performance Optimization

**Vector Search Configuration:**

```sql
-- Create optimized vector indexes
CREATE INDEX memories_embedding_hnsw_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- User-specific vector index
CREATE INDEX memories_user_embedding_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64)
WHERE user_id IS NOT NULL;
```

**Cache Optimization:**

```bash
# Configure DragonflyDB connection
export DRAGONFLY_URL="rediss://username:password@your-host:6380/0"
export DRAGONFLY_POOL_SIZE=20
export DRAGONFLY_TIMEOUT=5

# Test cache connectivity
python -c "import redis; r = redis.from_url('$DRAGONFLY_URL'); print(r.ping())"
```

**Connection Pool Configuration:**

```bash
# Optimize database connections
export SUPABASE_POOL_SIZE=20
export SUPABASE_MAX_OVERFLOW=30
export SUPABASE_POOL_TIMEOUT=30
```

### 6. Real-time Feature Setup

```sql
-- Create real-time publication
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
ALTER PUBLICATION supabase_realtime ADD TABLE itinerary_items;
```

**Test Real-time Functionality:**

```javascript
// Frontend real-time test
const subscription = supabase
  .channel('trips-changes')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'trips'
  }, (payload) => console.log('Change:', payload))
  .subscribe()
```

## Post-Deployment Validation

### Performance Testing

**Database Performance:**

```sql
-- Test vector search performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT content, embedding <=> '[0.1,0.2,...]'::vector as similarity 
FROM memories 
WHERE user_id = 'test-user-id'
ORDER BY embedding <=> '[0.1,0.2,...]'::vector 
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%';
```

**Performance Targets:**

- [ ] **Vector Search**: <100ms p95 latency for similarity queries
- [ ] **Database QPS**: >471 queries per second capacity
- [ ] **Cache Hit Rate**: >95% for DragonflyDB
- [ ] **Memory Operations**: <50ms for Mem0 operations
- [ ] **Real-time Latency**: <200ms for WebSocket messages
- [ ] **API Response Time**: <500ms p95 for REST endpoints

### Functional Testing

**Core Features:**

```bash
# Test API endpoints
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/trips
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/chat/sessions
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/search/destinations

# Test real-time features
wscat -c "wss://api.your-domain.com/ws?token=<token>"

# Test vector search
curl -X POST https://api.your-domain.com/memory/search \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "hotels in Paris", "limit": 5}'
```

**End-to-End Testing:**

- [ ] **User Registration**: Complete signup and email verification flow
- [ ] **Trip Creation**: Create, edit, and share trip functionality
- [ ] **Real-time Collaboration**: Multi-user trip editing
- [ ] **Chat System**: AI agent conversations and tool calls
- [ ] **Search Features**: Flight, hotel, and destination search
- [ ] **Memory System**: Context retention across sessions
- [ ] **BYOK System**: User API key management
- [ ] **Error Scenarios**: Graceful error handling and recovery

### Monitoring & Alerting Setup

**Database Monitoring:**

```sql
-- Monitor active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Monitor slow queries
SELECT query, calls, total_exec_time, mean_exec_time 
FROM pg_stat_statements 
WHERE mean_exec_time > 100 
ORDER BY mean_exec_time DESC;

-- Monitor cache hit ratio
SELECT 
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
```

**Application Metrics:**

- [ ] **Response Times**: P50, P95, P99 latencies tracked
- [ ] **Error Rates**: 4xx and 5xx error rates monitored
- [ ] **Throughput**: Requests per second tracking
- [ ] **Vector Search**: Query performance and accuracy metrics
- [ ] **Real-time**: WebSocket connection and message metrics
- [ ] **Memory System**: Mem0 operation performance
- [ ] **Cache Performance**: DragonflyDB hit rates and latency

**Alerting Configuration:**

```yaml
# Example Prometheus alerts
groups:
  - name: tripsage.alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected

      - alert: SlowVectorSearch
        expr: histogram_quantile(0.95, vector_search_duration_seconds) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Vector search performance degraded

      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High database connection count
```

## Rollback Procedure

If issues arise, follow this rollback sequence:

### Immediate Rollback (Application Level)

1. **Revert Code**: Deploy previous application version
2. **Restore Environment**: Restore previous environment variables
3. **Health Check**: Verify application stability

### Database Rollback (If Needed)

1. **Migration Rollback**: Use Supabase CLI to rollback migrations if needed

   ```bash
   supabase db reset
   # Or create a rollback migration
   supabase migration new rollback_pgvector_extensions
   ```

2. **Data Restoration**: Restore from backup if data corruption occurs

3. **Service Restoration**: Verify all services operational

## Success Criteria

### Performance Targets

**Database Performance:**

- [ ] **Vector Search**: <100ms p95, 471+ QPS capacity
- [ ] **Query Performance**: <50ms p95 for standard queries
- [ ] **Connection Pool**: <80% utilization under normal load
- [ ] **Cache Hit Rate**: >95% for DragonflyDB

**Application Performance:**

- [ ] **API Response Times**: <500ms p95 for REST endpoints
- [ ] **WebSocket Latency**: <200ms for real-time messages
- [ ] **Memory Operations**: <50ms for Mem0 queries
- [ ] **Error Rate**: <0.1% for critical endpoints

**Infrastructure Metrics:**

- [ ] **Availability**: >99.9% uptime SLA
- [ ] **Scalability**: Handle 10x current traffic load
- [ ] **Cost Optimization**: 80% reduction from previous architecture

### Operational Targets

**Architecture Consolidation:**

- [ ] **Unified Database**: Single Supabase instance for all data operations
- [ ] **Real-time Features**: Live collaboration and agent monitoring operational
- [ ] **Security Model**: RLS policies enforced across all user data
- [ ] **Cache Integration**: DragonflyDB providing 25x performance improvement
- [ ] **Memory System**: Mem0 with 91% performance improvement operational

**Development Workflow:**

- [ ] **CI/CD Pipeline**: Automated deployment and testing functional
- [ ] **Monitoring**: Comprehensive observability and alerting active
- [ ] **Documentation**: Architecture and deployment guides complete
- [ ] **Team Readiness**: Development and operations teams trained

## Post-Deployment Optimization

### Week 1: Immediate Monitoring

**Performance Validation:**

```bash
# Daily performance check script
#!/bin/bash
echo "🔍 TripSage Production Health Check - $(date)"

# API health check
curl -f https://api.your-domain.com/health/detailed

# Database performance
psql -d "$DATABASE_URL" -c "SELECT COUNT(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Vector search performance test
time curl -X POST https://api.your-domain.com/memory/search \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"query": "test search", "limit": 5}'

# Cache performance
redis-cli -u "$DRAGONFLY_URL" ping

echo "✅ Health check complete"
```

**Monitoring Tasks:**

- [ ] **Daily Metrics Review**: Performance, error rates, and usage patterns
- [ ] **Real-time Monitoring**: WebSocket connections and message throughput
- [ ] **Security Monitoring**: Authentication failures and suspicious activity
- [ ] **Cost Tracking**: Infrastructure costs and usage optimization
- [ ] **User Experience**: Response times and error rates from user perspective

### Week 2-4: Performance Optimization

**Database Optimization:**

```sql
-- Analyze query performance
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements 
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Optimize vector indexes based on usage
SELECT 
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_tup_read / idx_tup_fetch as selectivity
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%';

-- Update table statistics
ANALYZE memories;
ANALYZE trips;
ANALYZE chat_messages;
```

**Performance Tuning:**

- [ ] **Vector Index Optimization**: Tune HNSW parameters based on query patterns
- [ ] **Connection Pool Tuning**: Optimize pool sizes based on usage
- [ ] **Cache Configuration**: Adjust TTL strategies for optimal hit rates
- [ ] **Query Optimization**: Index creation and query plan improvements
- [ ] **Resource Scaling**: Assess need for compute or storage upgrades

### Month 1: Strategic Assessment

**Performance Analysis:**

```python
# Performance metrics collection script
import psycopg2
import redis
import time
from datetime import datetime, timedelta

def collect_performance_metrics():
    metrics = {
        'timestamp': datetime.utcnow(),
        'database': {
            'connections': get_db_connections(),
            'query_performance': get_slow_queries(),
            'vector_search_performance': get_vector_metrics(),
            'cache_hit_ratio': get_cache_hit_ratio()
        },
        'application': {
            'response_times': get_api_metrics(),
            'error_rates': get_error_rates(),
            'websocket_connections': get_ws_metrics()
        },
        'infrastructure': {
            'cpu_usage': get_cpu_metrics(),
            'memory_usage': get_memory_metrics(),
            'storage_usage': get_storage_metrics()
        }
    }
    return metrics
```

**Strategic Evaluation:**

- [ ] **Cost Analysis**: Detailed comparison with previous architecture costs
- [ ] **Performance Benchmarking**: Actual vs. projected performance metrics
- [ ] **Scalability Assessment**: Growth capacity and scaling requirements
- [ ] **Security Review**: Security posture and compliance validation
- [ ] **Operational Efficiency**: Developer productivity and maintenance overhead
- [ ] **Future Roadmap**: Next phase improvements and feature additions

## Emergency Contacts

**Database Issues:**

- Primary: Database Team Lead
- Secondary: Platform Engineering
- Escalation: CTO

**Application Issues:**

- Primary: Backend Team Lead
- Secondary: DevOps Engineer
- Escalation: Engineering Manager

## Additional Resources

- [Supabase pgvector Documentation](https://supabase.com/docs/guides/database/extensions/pgvector)
- [pgvector Performance Tuning Guide](https://github.com/pgvector/pgvector#performance)
- [Migration Summary Documentation](./MIGRATION_SUMMARY.md)
- [Supabase Migration Guide](https://supabase.com/docs/guides/cli/local-development#database-migrations)
- [Supabase CLI Reference](https://supabase.com/docs/reference/cli)

---

**Migration Lead:** *[Your Name]*  
**Date:** *[Deployment Date]*  
**Sign-off:** *[Stakeholder Approval]*
