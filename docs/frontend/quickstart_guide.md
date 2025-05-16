# TripSage Frontend Quick Start Guide

Get up and running with the TripSage frontend in minutes! This guide will walk you through setting up your development environment, understanding the project structure, and building your first features.

## Prerequisites

- **Node.js 20+** and **npm 10+**
- **Git** for version control
- **VS Code** (recommended) with extensions:
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
  - TypeScript and JavaScript Language Features
- **Vercel CLI** (optional, for deployment)

## Quick Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/tripsage/tripsage-frontend.git
cd tripsage-frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local
```

### 2. Configure Environment

Edit `.env.local` with your API keys:

```env
# Required for development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here

# Optional services
NEXT_PUBLIC_GOOGLE_MAPS_KEY=your_google_maps_key
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn
```

### 3. Start Development Server

```bash
# Start the development server
npm run dev

# Open http://localhost:3000
```

## Project Structure Overview

```
tripsage-frontend/
├── app/                    # Next.js App Router pages
│   ├── (auth)/            # Authentication pages
│   ├── (dashboard)/       # Main app pages
│   └── api/               # API routes
├── components/            # React components
│   ├── ui/               # Base UI components
│   ├── features/         # Feature components
│   └── agents/           # Agent-specific components
├── lib/                   # Utilities and integrations
├── stores/               # Zustand state stores
└── public/               # Static assets
```

## Core Concepts

### 1. Component Architecture

All components follow a consistent pattern:

```typescript
// components/features/ExampleComponent.tsx
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ExampleComponentProps {
  title: string;
  className?: string;
}

export function ExampleComponent({ 
  title, 
  className 
}: ExampleComponentProps) {
  const [state, setState] = useState('');

  return (
    <div className={cn('p-4 bg-card rounded-lg', className)}>
      <h2 className="text-xl font-bold">{title}</h2>
      {/* Component content */}
    </div>
  );
}
```

### 2. State Management

We use Zustand for client state and React Query for server state:

```typescript
// stores/exampleStore.ts
import { create } from 'zustand';

interface ExampleStore {
  items: Item[];
  addItem: (item: Item) => void;
  removeItem: (id: string) => void;
}

export const useExampleStore = create<ExampleStore>((set) => ({
  items: [],
  addItem: (item) => set((state) => ({ 
    items: [...state.items, item] 
  })),
  removeItem: (id) => set((state) => ({ 
    items: state.items.filter(item => item.id !== id) 
  })),
}));
```

### 3. API Integration

Use the provided API client for backend communication:

```typescript
// lib/api/example.ts
import { apiClient } from './client';
import { z } from 'zod';

const ItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  // ... other fields
});

export async function getItems() {
  return apiClient.request(
    '/api/items',
    { method: 'GET' },
    z.array(ItemSchema)
  );
}

export async function createItem(data: CreateItemInput) {
  return apiClient.request(
    '/api/items',
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
    ItemSchema
  );
}
```

## Common Tasks

### Creating a New Component

1. Create the component file:
```bash
touch components/features/MyNewComponent.tsx
```

2. Implement the component:
```typescript
export function MyNewComponent() {
  return (
    <div className="p-4 bg-card rounded-lg">
      <h2 className="text-xl font-bold">My New Component</h2>
      {/* Add your content here */}
    </div>
  );
}
```

3. Add it to a page:
```typescript
// app/(dashboard)/my-page/page.tsx
import { MyNewComponent } from '@/components/features/MyNewComponent';

export default function MyPage() {
  return (
    <div className="container mx-auto py-8">
      <MyNewComponent />
    </div>
  );
}
```

### Adding a New API Route

1. Create the route file:
```bash
mkdir -p app/api/my-endpoint
touch app/api/my-endpoint/route.ts
```

2. Implement the route:
```typescript
// app/api/my-endpoint/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // Your logic here
  return NextResponse.json({ message: 'Success' });
}

export async function POST(request: NextRequest) {
  const data = await request.json();
  // Process the data
  return NextResponse.json({ success: true });
}
```

### Integrating with MCP Servers

```typescript
// hooks/useMCPData.ts
import { useQuery } from '@tanstack/react-query';
import { mcpManager } from '@/lib/mcp/manager';

export function useMCPData(serverId: string) {
  return useQuery({
    queryKey: ['mcp', serverId],
    queryFn: async () => {
      const data = await mcpManager.invoke(
        serverId,
        'getData',
        { /* params */ }
      );
      return data;
    },
  });
}
```

### Adding Real-time Features

```typescript
// hooks/useRealtimeUpdates.ts
import { useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export function useRealtimeUpdates(channel: string) {
  const { on, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = on(channel, (data) => {
      // Handle real-time data
      console.log('Received:', data);
    });

    return unsubscribe;
  }, [isConnected, channel, on]);
}
```

## Styling Guidelines

### Using Tailwind CSS

```tsx
// Consistent spacing and colors
<div className="p-4 bg-background text-foreground">
  <h1 className="text-2xl font-bold mb-4">Title</h1>
  <p className="text-muted-foreground">Description</p>
</div>

// Responsive design
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Grid items */}
</div>

// Dark mode support (automatic with our theme)
<div className="bg-card dark:bg-card-dark">
  {/* Content */}
</div>
```

### Using shadcn/ui Components

```tsx
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

export function MyForm() {
  return (
    <Card className="p-6">
      <form className="space-y-4">
        <Input
          type="email"
          placeholder="Email"
          className="w-full"
        />
        <Button type="submit" className="w-full">
          Submit
        </Button>
      </form>
    </Card>
  );
}
```

## Testing

### Unit Tests

```typescript
// __tests__/components/MyComponent.test.tsx
import { render, screen } from '@testing-library/react';
import { MyComponent } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

### Integration Tests

```typescript
// __tests__/integration/user-flow.test.ts
import { test, expect } from '@playwright/test';

test('user can create a trip', async ({ page }) => {
  await page.goto('/');
  await page.click('[data-testid="create-trip"]');
  await page.fill('[data-testid="destination"]', 'Paris');
  await page.click('[data-testid="submit"]');
  
  await expect(page).toHaveURL('/trips/[id]');
});
```

## Debugging Tips

### 1. React DevTools
- Install the React DevTools browser extension
- Use it to inspect component props and state
- Profile component performance

### 2. Network Tab
- Monitor API calls in the browser's Network tab
- Check request/response payloads
- Verify authentication headers

### 3. Console Logging
```typescript
// Structured logging
console.group('API Call');
console.log('Endpoint:', endpoint);
console.log('Params:', params);
console.log('Response:', response);
console.groupEnd();
```

### 4. Error Boundaries
```typescript
// Wrap components that might error
<ErrorBoundary fallback={<ErrorFallback />}>
  <MyComponent />
</ErrorBoundary>
```

## Deployment

### Local Build
```bash
# Build for production
npm run build

# Start production server
npm start
```

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel

# Deploy to production
vercel --prod
```

## Common Issues & Solutions

### 1. Module Not Found Errors
```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
```

### 2. TypeScript Errors
```bash
# Check types
npm run type-check

# Fix common issues
npm run lint:fix
```

### 3. Environment Variables Not Loading
- Ensure `.env.local` exists
- Restart the dev server after changes
- Check variable names start with `NEXT_PUBLIC_` for client-side access

### 4. Tailwind Classes Not Working
- Ensure the class is included in `tailwind.config.js`
- Check for typos in class names
- Verify the component is wrapped in a Tailwind-enabled parent

## Next Steps

1. **Explore the Codebase**
   - Browse existing components in `/components`
   - Check out example pages in `/app`
   - Review integration patterns in `/lib`

2. **Build a Feature**
   - Start with a simple component
   - Add state management if needed
   - Integrate with the API
   - Add tests

3. **Contribute**
   - Follow the coding standards
   - Write comprehensive tests
   - Document your changes
   - Submit a pull request

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Query Documentation](https://tanstack.com/query)

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discord**: Join our community for discussions
- **Documentation**: Check `/docs` for detailed guides
- **Code Examples**: Browse `/examples` for patterns

Happy coding! 🚀