# 🚀 Deployment Guide for TripSage AI Frontend

This guide provides comprehensive instructions for deploying the TripSage AI frontend with cost estimates and configuration details.

## 📋 Table of Contents

- [Quick Start with Vercel](#quick-start-with-vercel)
- [Cost Estimates](#cost-estimates)
- [Step-by-Step Setup](#step-by-step-setup)
- [Alternative Deployment Options](#alternative-deployment-options)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

💡 **Need help estimating costs for your specific use case?** Use our [Cost Calculator](./cost-planning.md)

## 🚀 Quick Start with Vercel

### Prerequisites
- GitHub account with repository access
- Vercel account (free or paid)
- Node.js 20+ installed locally

### 1-Minute Deploy
1. **Fork/Clone** this repository
2. **Visit** [vercel.com/new](https://vercel.com/new)
3. **Import** your GitHub repository
4. **Configure** environment variables (see below)
5. **Deploy** - Vercel handles the rest!

### Required Environment Variables
```bash
# Add these in Vercel Dashboard → Project → Settings → Environment Variables
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional: Analytics & Monitoring
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=your_analytics_id
SENTRY_DSN=your_sentry_dsn
```

## 💰 Cost Estimates

### Vercel Pricing Breakdown

#### 🆓 **Hobby Plan (Free)**
- **Cost**: $0/month
- **Suitable for**: Personal projects, demos, low-traffic sites
- **Limitations**: 
  - Non-commercial use only
  - 100 GB bandwidth/month
  - 100,000 edge requests/month
  - 100 GB-hours function execution
- **Estimated traffic**: ~10,000 monthly visitors

#### 💼 **Pro Plan ($20/month)**
- **Cost**: $20/month + usage overages
- **Suitable for**: Commercial apps, small-medium teams
- **Included**:
  - 1 TB bandwidth/month
  - 10M edge requests/month
  - 1,000 GB-hours function execution
  - Advanced analytics & monitoring
  - Custom domains & SSL
- **Usage overages**:
  - Additional bandwidth: $0.15/GB
  - Additional edge requests: $2/1M requests
  - Additional function time: $0.18/GB-hour
- **Estimated traffic**: ~100,000-500,000 monthly visitors

#### 🏢 **Enterprise Plan (Custom)**
- **Cost**: Custom pricing (typically $500+/month)
- **Suitable for**: Large teams, high-traffic applications
- **Features**: Advanced security, SLA, dedicated support
- **Estimated traffic**: 1M+ monthly visitors

### Real-World Cost Examples

#### Small Travel Blog (10K visitors/month)
- **Platform**: Vercel Hobby
- **Monthly cost**: **$0**
- **Bandwidth**: ~20 GB
- **Page views**: ~50,000

#### Growing Travel Platform (50K visitors/month)
- **Platform**: Vercel Pro
- **Monthly cost**: **$20-35**
- **Bandwidth**: ~100 GB
- **Page views**: ~250,000
- **Additional costs**: Analytics $10/month

#### Large Travel Marketplace (200K visitors/month)
- **Platform**: Vercel Pro with overages
- **Monthly cost**: **$60-120**
- **Bandwidth**: ~400 GB (overage: $45)
- **Page views**: ~1M
- **Additional costs**: Enhanced monitoring $20/month

## 🔧 Step-by-Step Setup

### 1. Create Vercel Account & Connect GitHub

```bash
# Option A: Using Vercel CLI
npm i -g vercel
vercel login
vercel --prod

# Option B: Web Interface
# Visit https://vercel.com/signup
# Connect your GitHub account
# Import repository
```

### 2. Configure GitHub Repository Secrets

Add these secrets in **GitHub → Settings → Secrets and variables → Actions**:

```yaml
# Required for CI/CD deployment
VERCEL_TOKEN: xxxxx           # From Vercel → Settings → Tokens
VERCEL_ORG_ID: team_xxxxx     # From Vercel → Settings → General
VERCEL_PROJECT_ID: prj_xxxxx  # From Project → Settings → General

# Optional for coverage reporting
CODECOV_TOKEN: xxxxx          # From codecov.io
```

### 3. Project Configuration

Create `vercel.json` in your project root:

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

### 4. Environment Variables Setup

**Production Environment** (`vercel.com/dashboard → project → settings → environment variables`):

```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://api.tripsage.ai
NEXT_PUBLIC_ENVIRONMENT=production

# Database
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...

# Authentication
NEXTAUTH_URL=https://your-domain.vercel.app
NEXTAUTH_SECRET=your-secret-key

# External APIs
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...

# Analytics & Monitoring
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=your-analytics-id
NEXT_PUBLIC_POSTHOG_KEY=phc_...
SENTRY_DSN=https://...@sentry.io/...

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_ERROR_REPORTING=true
```

### 5. Domain Configuration

#### Custom Domain Setup
1. **Add Domain**: Vercel Dashboard → Domains → Add
2. **DNS Configuration**:
   ```dns
   # For apex domain (tripsage.ai)
   A     @     76.76.19.61
   AAAA  @     2600:1f13:e42:ad00::1

   # For subdomain (app.tripsage.ai)
   CNAME app   cname.vercel-dns.com
   ```
3. **SSL Certificate**: Automatically provisioned by Vercel

### 6. Performance Optimization

#### Vercel-Specific Optimizations
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

## 🌐 Alternative Deployment Options

### 1. **Netlify** - Vercel Alternative
**Cost**: Free tier + $19/month Pro
**Pros**: Strong static site hosting, edge functions
**Setup time**: ~15 minutes

```bash
# Install Netlify CLI
npm install -g netlify-cli
netlify login
netlify deploy --prod
```

**Estimated monthly costs**:
- Free: 100GB bandwidth, 300 build minutes
- Pro ($19/month): 400GB bandwidth, 25,000 function invocations

### 2. **Railway** - Simple Container Deployment
**Cost**: $5/month + usage ($0.000463/GB-second)
**Pros**: Database included, simple pricing
**Setup time**: ~10 minutes

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway deploy
```

**Estimated monthly costs**:
- Starter: $5/month (512MB RAM, shared CPU)
- Pro: $20-50/month (1-2GB RAM, dedicated CPU)

### 3. **AWS Amplify** - Enterprise Option
**Cost**: $0.01/build minute + $0.15/GB hosting
**Pros**: AWS integration, enterprise features
**Setup time**: ~30 minutes

**Estimated monthly costs**:
- Small app: $10-20/month
- Medium app: $30-60/month
- Large app: $100-300/month

### 4. **Self-Hosted VPS** - Maximum Control
**Cost**: $5-50/month (DigitalOcean, Linode, Hetzner)
**Pros**: Full control, predictable pricing
**Setup time**: ~2-4 hours

```bash
# Example Docker deployment
docker build -t tripsage-frontend .
docker run -p 3000:3000 tripsage-frontend
```

**Estimated monthly costs**:
- Basic VPS: $5-10/month (1GB RAM, 1 CPU)
- Production VPS: $20-40/month (4GB RAM, 2 CPU)
- CDN: $5-20/month (Cloudflare Pro)

## 📊 Monitoring & Maintenance

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
// package.json
{
  "scripts": {
    "analyze": "ANALYZE=true pnpm build",
    "lighthouse": "lhci autorun"
  }
}
```

## 🛠 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check build logs in Vercel dashboard
# Common fixes:
pnpm install --frozen-lockfile  # Dependency issues
pnpm type-check                 # TypeScript errors
pnpm lint --fix                 # Linting errors
```

#### 2. Environment Variable Issues
```bash
# Verify in Vercel dashboard
# Check preview vs production environments
# Ensure NEXT_PUBLIC_ prefix for client-side vars
```

#### 3. Function Timeout
```json
// vercel.json
{
  "functions": {
    "frontend/src/app/api/**/*.ts": {
      "maxDuration": 30
    }
  }
}
```

#### 4. Large Bundle Size
```bash
# Analyze bundle
pnpm analyze

# Common optimizations:
# - Dynamic imports for large components
# - Tree-shake unused dependencies
# - Optimize images and assets
```

### Performance Monitoring

#### Key Metrics to Track
- **Core Web Vitals**: LCP, FID, CLS
- **Load Time**: <3 seconds
- **Bundle Size**: <1MB initial load
- **Function Duration**: <10 seconds average

#### Alerts Setup
```javascript
// vercel.json
{
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 30
    }
  },
  "crons": [
    {
      "path": "/api/health",
      "schedule": "0 */5 * * * *"
    }
  ]
}
```

## 💡 Cost Optimization Tips

### 1. **Reduce Function Execution Time**
- Use caching strategies
- Optimize database queries
- Implement request memoization

### 2. **Minimize Data Transfer**
- Enable compression
- Optimize images (WebP/AVIF)
- Use CDN for static assets

### 3. **Smart Caching**
```typescript
// Implement edge caching
export const revalidate = 3600 // 1 hour

// Use React cache for expensive operations
import { cache } from 'react'
const getExpensiveData = cache(async () => {
  // Expensive operation
})
```

### 4. **Monitor Usage**
- Set up spend alerts in Vercel
- Review usage dashboard monthly
- Optimize high-traffic endpoints

---

## 📞 Support

- **Vercel Support**: [vercel.com/support](https://vercel.com/support)
- **GitHub Issues**: [Project Issues](https://github.com/BjornMelin/tripsage-ai/issues)
- **Documentation**: [Next.js Deployment](https://nextjs.org/docs/deployment)

**Need help?** Create an issue in the repository with:
- Deployment platform
- Error messages
- Configuration details
- Expected vs actual behavior