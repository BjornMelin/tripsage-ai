# TripSage Frontend

Modern Next.js 16 application with React 19, TypeScript, and AI-powered travel planning features.

## Tech Stack

- **Framework**: Next.js 16.0.0 with App Router
- **React**: React 19.2.0 with concurrent features
- **Language**: TypeScript 5.9.3 with strict mode
- **Styling**: Tailwind CSS v4.1.15 with CSS-first config
- **State Management**: Zustand 5.0.8
- **Data Fetching**: TanStack Query 5.90.5
- **UI Components**: Radix UI primitives with Tailwind
- **AI Integration**: AI SDK v5.0.76 (@ai-sdk/react)
- **Backend**: Supabase with SSR auth
- **Testing**: Vitest 4.0.1 with Playwright E2E
- **Linting**: Biome 2.2.7
- **Package Manager**: pnpm ≥9.0.0
- **Runtime**: Node.js ≥24

## Getting Started

### Prerequisites

- Node.js ≥24
- pnpm ≥9.0.0

### Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Development Scripts

### Core Commands

```bash
pnpm dev          # Start development server
pnpm build        # Production build
pnpm build:analyze # Build with bundle analyzer
pnpm start        # Start production server
```

### Code Quality

```bash
pnpm type-check   # TypeScript type checking
pnpm biome:check  # Lint and format check
pnpm biome:fix    # Auto-fix linting issues
pnpm format:check # Check formatting
```

### Testing

```bash
pnpm test         # Run unit tests
pnpm test:run     # Run tests once
pnpm test:coverage # Run tests with coverage
pnpm test:e2e     # Run E2E tests with Playwright
```

### Maintenance

```bash
pnpm lint         # ESLint check
pnpm prepare      # Set up Husky git hooks
```

## Project Structure

```text
frontend/
├── middleware.ts    # Next.js SSR cookie-sync with @supabase/ssr
├── src/
│   ├── app/           # Next.js App Router pages
│   ├── components/    # Reusable UI components
│   ├── contexts/      # React context providers
│   ├── hooks/         # Custom React hooks
│   ├── lib/           # Utilities and configurations
│   ├── schemas/       # Zod validation schemas
│   ├── stores/        # Zustand state stores
│   ├── styles/        # Global styles and CSS
│   ├── types/         # TypeScript type definitions
│   ├── __tests__/     # Unit and integration tests
│   └── test-utils/    # Testing utilities
├── e2e/               # End-to-end tests
├── playwright.config.ts
├── vitest.config.ts
└── biome.json
```

## Environment Variables

Create a `.env.local` file with:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Analytics
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=your_analytics_id
```

## Documentation

- **[Frontend Development Guide](../docs/developers/frontend-development.md)** - Complete development setup and patterns
- **[API Documentation](../docs/api/README.md)** - Backend API reference
- **[Architecture Overview](../docs/architecture/README.md)** - System design and data flow

## Deployment

Deploy to Vercel with the [deployment guide](../.github/DEPLOYMENT.md) or check our [production deployment docs](../docs/operators/deployment-guide.md).
