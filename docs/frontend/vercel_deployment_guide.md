# Vercel Deployment Guide for TripSage

This guide covers deployment best practices, configuration, and optimization for deploying TripSage to Vercel.

## Pre-Deployment Checklist

### 1. Environment Variables

Create `.env.local` for local development and configure Vercel environment variables:

```env
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# MCP Servers
MCP_FLIGHTS_URL=https://flights-mcp.vercel.app
MCP_WEATHER_URL=https://weather-mcp.vercel.app
MCP_ACCOMMODATION_URL=https://accommodation-mcp.vercel.app

# Redis for SSE/WebSocket
REDIS_URL=redis://...

# Feature Flags
NEXT_PUBLIC_ENABLE_BROWSER_AUTOMATION=false
NEXT_PUBLIC_ENABLE_AI_AGENTS=true
```

### 2. Build Configuration

Update `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React Strict Mode
  reactStrictMode: true,
  
  // Image optimization
  images: {
    domains: [
      'images.unsplash.com',
      'source.unsplash.com',
      'your-supabase-url.supabase.co',
    ],
    formats: ['image/avif', 'image/webp'],
  },
  
  // Experimental features
  experimental: {
    // Enable Server Actions
    serverActions: true,
    // Use Turbopack in development
    turbo: {
      loaders: {
        '.md': ['@mdx-js/loader'],
      },
    },
  },
  
  // Security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ]
  },
  
  // Redirects
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
    ]
  },
}

module.exports = nextConfig
```

## Vercel Project Setup

### 1. Create Vercel Project

```bash
# Install Vercel CLI
pnpm add -g vercel

# Deploy to Vercel
vercel

# Follow prompts to:
# - Set up and deploy
# - Link to existing project (if applicable)
# - Configure project settings
```

### 2. Configure Build Settings

In Vercel Dashboard:

- **Framework Preset**: Next.js
- **Build Command**: `pnpm build`
- **Output Directory**: `.next`
- **Install Command**: `pnpm install`
- **Node.js Version**: 20.x

### 3. Environment Variables

Add environment variables in Vercel Dashboard:

1. Navigate to Project Settings > Environment Variables
2. Add variables for all environments (Production, Preview, Development)
3. Ensure sensitive keys are only in Production

## Edge Runtime Configuration

For optimal performance, configure edge runtime for specific routes:

```typescript
// app/api/chat/route.ts
export const runtime = 'edge'
export const preferredRegion = ['iad1', 'sfo1'] // US East & West

export async function POST(req: Request) {
  // Your chat endpoint logic
}
```

## Caching Strategies

### 1. Static Generation

```typescript
// app/destinations/[slug]/page.tsx
export async function generateStaticParams() {
  const destinations = await getPopularDestinations()
  
  return destinations.map((destination) => ({
    slug: destination.slug,
  }))
}

export async function generateMetadata({ params }: Props) {
  const destination = await getDestination(params.slug)
  
  return {
    title: `${destination.name} Travel Guide | TripSage`,
    description: destination.description,
  }
}
```

### 2. Dynamic Caching

```typescript
// app/api/search/route.ts
import { unstable_cache } from 'next/cache'

const getCachedSearchResults = unstable_cache(
  async (query: string) => {
    return await searchDestinations(query)
  },
  ['search-results'],
  {
    revalidate: 3600, // 1 hour
    tags: ['search'],
  }
)
```

### 3. On-Demand Revalidation

```typescript
// app/api/revalidate/route.ts
import { revalidateTag, revalidatePath } from 'next/cache'

export async function POST(req: Request) {
  const { type, value } = await req.json()
  
  if (type === 'tag') {
    revalidateTag(value)
  } else if (type === 'path') {
    revalidatePath(value)
  }
  
  return Response.json({ revalidated: true })
}
```

## Monitoring and Analytics

### 1. Vercel Analytics

```typescript
// app/layout.tsx
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/next'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
```

### 2. Custom Monitoring

```typescript
// lib/monitoring.ts
export async function trackEvent(
  name: string,
  properties?: Record<string, any>
) {
  if (process.env.NODE_ENV === 'production') {
    // Send to your analytics service
    await fetch('/api/analytics', {
      method: 'POST',
      body: JSON.stringify({
        event: name,
        properties,
        timestamp: new Date().toISOString(),
      }),
    })
  }
}
```

## Performance Optimization

### 1. Image Optimization

```typescript
import Image from 'next/image'

export function DestinationCard({ destination }) {
  return (
    <div>
      <Image
        src={destination.image}
        alt={destination.name}
        width={400}
        height={300}
        loading="lazy"
        placeholder="blur"
        blurDataURL={destination.blurDataURL}
        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
      />
    </div>
  )
}
```

### 2. Code Splitting

```typescript
// Dynamic imports for heavy components
const AgentVisualizer = dynamic(
  () => import('@/components/AgentVisualizer'),
  {
    loading: () => <Skeleton className="h-[400px]" />,
  }
)

const MapView = dynamic(
  () => import('@/components/MapView'),
  {
    ssr: false, // Disable SSR for client-only components
  }
)
```

### 3. Font Optimization

```typescript
// app/layout.tsx
import { Inter, Playfair_Display } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
})
```

## Security Best Practices

### 1. API Route Protection

```typescript
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { verifyAuth } from '@/lib/auth'

export async function middleware(request: NextRequest) {
  // Protect API routes
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const token = request.headers.get('authorization')?.split(' ')[1]
    
    if (!token || !(await verifyAuth(token))) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: '/api/:path*',
}
```

### 2. Content Security Policy

```typescript
// app/layout.tsx
export const metadata = {
  other: {
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' *.vercel-insights.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self'",
      "connect-src 'self' *.supabase.co *.vercel-insights.com",
    ].join('; '),
  },
}
```

## Deployment Scripts

### 1. Pre-deployment Script

```json
// package.json
{
  "scripts": {
    "predeploy": "pnpm run type-check && pnpm run lint && pnpm run test",
    "deploy": "vercel --prod",
    "type-check": "tsc --noEmit",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives"
  }
}
```

### 2. GitHub Actions for CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Vercel

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'pnpm'
      
      - name: Install dependencies
        run: pnpm install
      
      - name: Type check
        run: pnpm type-check
      
      - name: Lint
        run: pnpm lint
      
      - name: Test
        run: pnpm test
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check Node.js version compatibility
   - Verify all environment variables are set
   - Review build logs for specific errors

2. **Runtime Errors**
   - Check browser console for client-side errors
   - Review Vercel Functions logs
   - Verify API endpoints are accessible

3. **Performance Issues**
   - Use Vercel Analytics to identify bottlenecks
   - Implement caching strategies
   - Optimize bundle size with next/dynamic

### Debug Mode

```typescript
// lib/debug.ts
export const isDebugMode = process.env.NEXT_PUBLIC_DEBUG === 'true'

export function debugLog(...args: any[]) {
  if (isDebugMode) {
    console.log('[DEBUG]', ...args)
  }
}
```

## Post-Deployment

1. **Monitor Performance**
   - Set up alerts for errors and performance degradation
   - Monitor Core Web Vitals
   - Track API response times

2. **Regular Updates**
   - Keep dependencies updated
   - Review and optimize caching strategies
   - Monitor costs and optimize resource usage

3. **Backup and Recovery**
   - Set up database backups
   - Document rollback procedures
   - Test disaster recovery plans

This deployment guide ensures TripSage is production-ready with optimal performance, security, and reliability on Vercel.