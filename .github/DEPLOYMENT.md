# Quick Deployment Guide

Steps to deploy TripSage AI frontend to Vercel.

## Prerequisites

- GitHub account with repository access
- Vercel account (free tier available)
- Environment variables configured

## Deploy in 3 Steps

### 1. Import to Vercel

1. Visit [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Vercel will auto-detect Next.js settings

### 2. Configure Environment Variables

Add these in Vercel Dashboard → Project → Settings → Environment Variables:

```bash
# Required
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=your_analytics_id
SENTRY_DSN=your_sentry_dsn
```

### 3. Deploy

Click "Deploy" - Vercel handles the build and deployment automatically.

## CI/CD Setup

Add these repository secrets for automated deployments:

- `VERCEL_TOKEN` - From Vercel → Settings → Tokens
- `VERCEL_ORG_ID` - From Vercel → Settings → General  
- `VERCEL_PROJECT_ID` - From Project → Settings → General

## Cost Estimates

- **Free tier**: Personal projects, ~10K monthly visitors
- **Pro ($20/month)**: Commercial use, ~100K-500K monthly visitors
- **Enterprise**: High-traffic applications, custom pricing

## Need More Help?

- **Guide**: [docs/deployment/comprehensive-guide.md](../docs/deployment/comprehensive-guide.md)
- **Cost Planning**: [docs/deployment/cost-planning.md](../docs/deployment/cost-planning.md)
- **Troubleshooting**: Check Vercel deployment logs
- **Support**: [Vercel Support](https://vercel.com/support) or create GitHub issue

---
*This guide focuses on essential deployment steps. For detailed configuration, platform alternatives, and business planning, see the documentation in `/docs/deployment/`.*
