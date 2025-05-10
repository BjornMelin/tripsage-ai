# TripSage Frontend Specifications

This document outlines the technical specifications, design patterns, and implementation details for the TripSage frontend application.

## 1. Technology Stack

### Core Technologies

- **React 18+**: For building the user interface
- **TypeScript 5+**: For type safety and better developer experience
- **Next.js 14+**: For server-side rendering, API routes, and improved performance
- **Supabase JS Client**: For database integration and authentication

### UI Framework and Styling

- **Tailwind CSS**: For utility-first styling
- **Headless UI**: For accessible, unstyled components
- **Shadcn/ui**: For reusable, beautifully designed components built on Radix UI
- **Framer Motion**: For smooth animations and transitions

### State Management

- **React Context API**: For global state management
- **Zustand**: For complex state management when needed
- **React Query**: For server state management and data fetching

### Mapping and Visualization

- **Mapbox GL JS**: For interactive maps
- **React Chart.js 2**: For data visualization
- **React DnD**: For drag-and-drop itinerary planning

### Form Handling

- **React Hook Form**: For form validation and handling
- **Zod**: For schema validation

### Testing

- **Vitest**: For unit testing
- **React Testing Library**: For component testing
- **Playwright**: For end-to-end testing

### Building and Deployment

- **Vite**: For fast development and optimized production builds
- **Vercel**: For deployment and hosting

## 2. Application Architecture

### Directory Structure

```plaintext
src/
├── components/         # Reusable UI components
│   ├── ui/             # Base UI components (shadcn/ui)
│   ├── common/         # Common application components
│   ├── features/       # Feature-specific components
│   └── layout/         # Layout components
├── hooks/              # Custom React hooks
├── lib/                # Utility functions and services
│   ├── api/            # API integration services
│   ├── supabase/       # Supabase client and utilities
│   └── utils/          # Helper functions
├── pages/              # Next.js pages
├── store/              # Zustand stores
├── styles/             # Global styles
├── types/              # TypeScript type definitions
└── test/               # Test utilities and mocks
```

### Component Hierarchy

- **Layout Components**: Define the overall structure
  - AppLayout: Main layout with navigation
  - DashboardLayout: Layout for authenticated user dashboard
  - TripPlannerLayout: Layout for trip planning interface
- **Common Components**: Reusable across the application
  - Button, Input, Card, Modal, etc.
  - Calendar, DatePicker, AutoComplete, etc.
- **Feature Components**: Specific to application features
  - TripCard: Displays trip summary
  - DestinationSearch: Search component for finding destinations
  - ItineraryBuilder: Interface for building trip itineraries
  - BudgetPlanner: Tools for budget management
  - WeatherWidget: Display weather information

### State Management Strategy

The application will use a combination of state management approaches:

1. **Component-Level State**: Using `useState` and `useReducer` for component-specific state
2. **Context API**: For shared state within feature boundaries
3. **Zustand**: For more complex global state management
4. **React Query**: For server state, caching, and data synchronization

State will be organized by feature domains:

- **Authentication State**: User authentication and profile information
- **Trip State**: Current trip planning data
- **Search State**: Search parameters and results
- **Preferences State**: User preferences and settings

## 3. UI/UX Design System

### Design Principles

- **Clean and Minimalist**: Focus on content and functionality
- **Responsive Design**: Mobile-first approach with seamless scaling to larger screens
- **Consistent Visual Language**: Maintain consistent spacing, typography, and color usage
- **Accessibility**: Ensure all components are accessible to all users
- **Progressive Enhancement**: Core functionality should work without JavaScript

### Color Palette

- **Primary**: #4F46E5 (Indigo)
- **Secondary**: #10B981 (Emerald)
- **Accent**: #F59E0B (Amber)
- **Neutral**:
  - #1F2937 (Gray 800)
  - #4B5563 (Gray 600)
  - #9CA3AF (Gray 400)
  - #F3F4F6 (Gray 100)
- **Semantic**:
  - Success: #10B981 (Green)
  - Warning: #F59E0B (Amber)
  - Error: #EF4444 (Red)
  - Info: #3B82F6 (Blue)

### Typography

- **Font Family**:
  - Primary: Inter (UI)
  - Secondary: Playfair Display (headings for travel content)
- **Font Sizes**:
  - xs: 0.75rem (12px)
  - sm: 0.875rem (14px)
  - base: 1rem (16px)
  - lg: 1.125rem (18px)
  - xl: 1.25rem (20px)
  - 2xl: 1.5rem (24px)
  - 3xl: 1.875rem (30px)
  - 4xl: 2.25rem (36px)

### Spacing System

- 0: 0px
- px: 1px
- 0.5: 0.125rem (2px)
- 1: 0.25rem (4px)
- 2: 0.5rem (8px)
- 3: 0.75rem (12px)
- 4: 1rem (16px)
- 5: 1.25rem (20px)
- 6: 1.5rem (24px)
- 8: 2rem (32px)
- 10: 2.5rem (40px)
- 12: 3rem (48px)
- 16: 4rem (64px)
- 20: 5rem (80px)
- 24: 6rem (96px)

### Component Library

TripSage will utilize a component library built on shadcn/ui, extending it with custom components specific to the travel planning domain. The component library will include:

- **Navigation**: Navbar, Sidebar, Breadcrumbs, Tabs
- **Data Display**: Table, Card, Timeline, Badge
- **Inputs**: Text Input, Select, Checkbox, Radio, DatePicker
- **Feedback**: Alert, Toast, Modal, Progress
- **Travel Specific**: Map, ItineraryCard, TripTimeline, BudgetDisplay, WeatherDisplay

## 4. Key Features and Implementation

### Authentication and User Management

- **Implementation**: Supabase Auth with JWT
- **Features**:
  - Email/password authentication
  - Social login (Google, Facebook)
  - Password reset
  - Profile management
  - Session persistence

**Example Code**:

```typescript
// hooks/useAuth.ts
import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

type AuthContextType = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check active session
    const getUser = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      setLoading(false);
    };

    getUser();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const value = {
    user,
    loading,
    signIn: async (email: string, password: string) => {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
    },
    signUp: async (email: string, password: string) => {
      const { error } = await supabase.auth.signUp({ email, password });
      if (error) throw error;
    },
    signOut: async () => {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
```

### Trip Planning and Management

- **Implementation**: React components with React Query for data management
- **Features**:
  - Create new trips with destinations
  - Add activities, accommodations, and transportation
  - Manage trip timelines
  - Calculate and manage budget

**Example Code**:

```typescript
// hooks/useTrips.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import type { Trip } from "@/types";

export const useTrips = (userId: string) => {
  const queryClient = useQueryClient();

  const getTrips = async (): Promise<Trip[]> => {
    const { data, error } = await supabase
      .from("trips")
      .select("*")
      .eq("user_id", userId);

    if (error) throw error;
    return data as Trip[];
  };

  const createTrip = async (newTrip: Omit<Trip, "id">): Promise<Trip> => {
    const { data, error } = await supabase
      .from("trips")
      .insert([{ ...newTrip, user_id: userId }])
      .select()
      .single();

    if (error) throw error;
    return data as Trip;
  };

  const updateTrip = async (updatedTrip: Trip): Promise<Trip> => {
    const { data, error } = await supabase
      .from("trips")
      .update(updatedTrip)
      .eq("id", updatedTrip.id)
      .eq("user_id", userId)
      .select()
      .single();

    if (error) throw error;
    return data as Trip;
  };

  const deleteTrip = async (tripId: string): Promise<void> => {
    const { error } = await supabase
      .from("trips")
      .delete()
      .eq("id", tripId)
      .eq("user_id", userId);

    if (error) throw error;
  };

  const tripsQuery = useQuery({
    queryKey: ["trips", userId],
    queryFn: getTrips,
  });

  const createTripMutation = useMutation({
    mutationFn: createTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
    },
  });

  const updateTripMutation = useMutation({
    mutationFn: updateTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
    },
  });

  const deleteTripMutation = useMutation({
    mutationFn: deleteTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
    },
  });

  return {
    trips: tripsQuery.data ?? [],
    isLoading: tripsQuery.isLoading,
    error: tripsQuery.error,
    createTrip: createTripMutation.mutate,
    updateTrip: updateTripMutation.mutate,
    deleteTrip: deleteTripMutation.mutate,
  };
};
```

### Map Integration and Visualization

- **Implementation**: Mapbox GL JS with React wrapper
- **Features**:
  - Interactive maps for destinations
  - Custom map markers for points of interest
  - Route visualization
  - Clustering for multiple points

**Example Code**:

```typescript
// components/features/TripMap.tsx
import { useRef, useEffect, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { PointOfInterest } from "@/types";

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

interface TripMapProps {
  center: [number, number];
  zoom: number;
  pointsOfInterest: PointOfInterest[];
}

export const TripMap = ({ center, zoom, pointsOfInterest }: TripMapProps) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: center,
      zoom: zoom,
    });

    map.current.on("load", () => {
      setMapLoaded(true);
    });

    return () => {
      map.current?.remove();
    };
  }, []);

  // Add markers when map is loaded and when points change
  useEffect(() => {
    if (!mapLoaded || !map.current) return;

    // Remove existing markers
    const markers = document.getElementsByClassName("mapboxgl-marker");
    while (markers[0]) {
      markers[0].remove();
    }

    // Add new markers
    pointsOfInterest.forEach((poi) => {
      const marker = new mapboxgl.Marker({
        color: poi.category === "accommodation" ? "#4F46E5" : "#10B981",
      })
        .setLngLat([poi.longitude, poi.latitude])
        .setPopup(
          new mapboxgl.Popup().setHTML(`
          <h3 class="font-medium">${poi.name}</h3>
          <p class="text-sm">${poi.description}</p>
        `)
        )
        .addTo(map.current!);
    });
  }, [mapLoaded, pointsOfInterest]);

  return (
    <div ref={mapContainer} className="h-full w-full rounded-lg shadow-md" />
  );
};
```

### Search and Filtering

- **Implementation**: Custom hooks with debouncing
- **Features**:
  - Destination search
  - Filtering by budget, dates, and amenities
  - Sorting by relevance, price, etc.

**Example Code**:

```typescript
// hooks/useSearch.ts
import { useState, useEffect, useCallback } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import { searchDestinations } from "@/lib/api/destinations";
import type { Destination, SearchFilters } from "@/types";

export const useSearch = () => {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({
    minBudget: 0,
    maxBudget: 10000,
    startDate: null,
    endDate: null,
    amenities: [],
  });
  const [results, setResults] = useState<Destination[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const debouncedQuery = useDebounce(query, 500);
  const debouncedFilters = useDebounce(filters, 500);

  const fetchResults = useCallback(async () => {
    if (!debouncedQuery && !debouncedFilters.amenities.length) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await searchDestinations(debouncedQuery, debouncedFilters);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("An error occurred"));
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, debouncedFilters]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  return {
    query,
    setQuery,
    filters,
    setFilters,
    results,
    loading,
    error,
    refetch: fetchResults,
  };
};
```

### Itinerary Building

- **Implementation**: React with drag-and-drop functionality
- **Features**:
  - Day-by-day itinerary planning
  - Drag-and-drop activity ordering
  - Time slot management
  - Automatic travel time calculation

**Example Code**:

```typescript
// components/features/ItineraryBuilder.tsx
import { useState } from "react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import type { Activity, Day } from "@/types";

interface ItineraryBuilderProps {
  days: Day[];
  activities: Activity[];
  onUpdate: (days: Day[]) => void;
}

export const ItineraryBuilder = ({
  days,
  activities,
  onUpdate,
}: ItineraryBuilderProps) => {
  return (
    <DndProvider backend={HTML5Backend}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gray-100 p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-3">Available Activities</h3>
          <div className="space-y-2">
            {activities.map((activity) => (
              <ActivityItem key={activity.id} activity={activity} />
            ))}
          </div>
        </div>

        {days.map((day) => (
          <DayColumn key={day.id} day={day} days={days} onUpdate={onUpdate} />
        ))}
      </div>
    </DndProvider>
  );
};

interface ActivityItemProps {
  activity: Activity;
}

const ActivityItem = ({ activity }: ActivityItemProps) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: "activity",
    item: { id: activity.id, activity },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }));

  return (
    <div
      ref={drag}
      className={`bg-white p-3 rounded shadow-sm cursor-grab ${
        isDragging ? "opacity-50" : "opacity-100"
      }`}
    >
      <h4 className="font-medium">{activity.name}</h4>
      <p className="text-sm text-gray-600">{activity.duration} mins</p>
    </div>
  );
};

interface DayColumnProps {
  day: Day;
  days: Day[];
  onUpdate: (days: Day[]) => void;
}

const DayColumn = ({ day, days, onUpdate }: DayColumnProps) => {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: "activity",
    drop: (item: { id: string; activity: Activity }) => {
      const newDays = days.map((d) => {
        if (d.id === day.id) {
          return {
            ...d,
            activities: [...d.activities, item.activity],
          };
        }
        return d;
      });
      onUpdate(newDays);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }));

  return (
    <div
      ref={drop}
      className={`bg-gray-100 p-4 rounded-lg min-h-[300px] ${
        isOver ? "bg-gray-200" : ""
      }`}
    >
      <h3 className="text-lg font-medium mb-3">
        Day {day.dayNumber}: {day.date}
      </h3>

      <div className="space-y-2">
        {day.activities.map((activity) => (
          <div key={activity.id} className="bg-white p-3 rounded shadow-sm">
            <h4 className="font-medium">{activity.name}</h4>
            <p className="text-sm text-gray-600">{activity.duration} mins</p>
          </div>
        ))}

        {day.activities.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            Drop activities here
          </div>
        )}
      </div>
    </div>
  );
};
```

### Budget Planning and Tracking

- **Implementation**: Chart.js with React wrapper
- **Features**:
  - Budget breakdown by category
  - Expense tracking
  - Cost comparison
  - Currency conversion

**Example Code**:

```typescript
// components/features/BudgetBreakdown.tsx
import { useState } from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from "chart.js";
import type { Expense, ExpenseCategory } from "@/types";

ChartJS.register(ArcElement, Tooltip, Legend);

interface BudgetBreakdownProps {
  expenses: Expense[];
  totalBudget: number;
}

export const BudgetBreakdown = ({
  expenses,
  totalBudget,
}: BudgetBreakdownProps) => {
  const [activeCurrency, setActiveCurrency] = useState<string>("USD");

  // Group expenses by category
  const expensesByCategory = expenses.reduce((acc, expense) => {
    const category = expense.category as ExpenseCategory;
    if (!acc[category]) {
      acc[category] = 0;
    }
    acc[category] += expense.amount;
    return acc;
  }, {} as Record<ExpenseCategory, number>);

  // Calculate remaining budget
  const totalSpent = Object.values(expensesByCategory).reduce(
    (a, b) => a + b,
    0
  );
  const remaining = totalBudget - totalSpent;

  const chartData: ChartData<"pie"> = {
    labels: [...Object.keys(expensesByCategory), "Remaining"],
    datasets: [
      {
        data: [
          ...Object.values(expensesByCategory),
          remaining > 0 ? remaining : 0,
        ],
        backgroundColor: [
          "#4F46E5", // Accommodation
          "#10B981", // Transportation
          "#F59E0B", // Food
          "#EF4444", // Activities
          "#3B82F6", // Shopping
          "#8B5CF6", // Misc
          "#E5E7EB", // Remaining
        ],
        borderWidth: 1,
      },
    ],
  };

  const options: ChartOptions<"pie"> = {
    responsive: true,
    plugins: {
      legend: {
        position: "bottom",
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.label || "";
            const value = context.parsed || 0;
            const total = context.dataset.data.reduce(
              (a: number, b: number) => a + b,
              0
            );
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value} ${activeCurrency} (${percentage}%)`;
          },
        },
      },
    },
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Budget Breakdown</h2>
        <select
          value={activeCurrency}
          onChange={(e) => setActiveCurrency(e.target.value)}
          className="border rounded px-2 py-1"
        >
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
          <option value="GBP">GBP</option>
          <option value="JPY">JPY</option>
        </select>
      </div>

      <div className="h-64">
        <Pie data={chartData} options={options} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <div className="bg-gray-100 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500">Total Budget</h3>
          <p className="text-2xl font-bold">
            {totalBudget} {activeCurrency}
          </p>
        </div>
        <div className="bg-gray-100 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500">Remaining</h3>
          <p
            className={`text-2xl font-bold ${
              remaining < 0 ? "text-red-500" : ""
            }`}
          >
            {remaining} {activeCurrency}
          </p>
        </div>
      </div>
    </div>
  );
};
```

### Responsive Design Approach

TripSage will implement a mobile-first approach using Tailwind CSS breakpoints:

- **sm**: 640px (mobile landscape)
- **md**: 768px (tablets)
- **lg**: 1024px (laptops)
- **xl**: 1280px (desktops)
- **2xl**: 1536px (large desktops)

Layout components will leverage Flexbox and CSS Grid to create responsive interfaces that adapt to different screen sizes. For example:

```tsx
// components/layout/TripGrid.tsx
interface TripGridProps {
  children: React.ReactNode;
}

export const TripGrid = ({ children }: TripGridProps) => {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {children}
    </div>
  );
};
```

## 5. Performance Optimization

### Code Splitting and Lazy Loading

Next.js provides built-in support for code splitting. We'll further optimize by:

- Using dynamic imports for large components
- Implementing route-based code splitting
- Lazy loading images and maps

Example:

```typescript
// pages/trips/[id].tsx
import dynamic from "next/dynamic";
import { Suspense } from "react";
import { useRouter } from "next/router";
import { Spinner } from "@/components/ui/spinner";
import { useTripDetails } from "@/hooks/useTripDetails";

// Dynamically import heavy components
const TripMap = dynamic(() => import("@/components/features/TripMap"), {
  ssr: false, // Disable server-side rendering for map component
  loading: () => (
    <div className="h-64 bg-gray-200 animate-pulse rounded-lg"></div>
  ),
});

const ItineraryBuilder = dynamic(
  () => import("@/components/features/ItineraryBuilder"),
  {
    loading: () => <Spinner />,
  }
);

export default function TripDetails() {
  const router = useRouter();
  const { id } = router.query;
  const { trip, isLoading, error } = useTripDetails(id as string);

  if (isLoading) return <Spinner />;
  if (error) return <div>Error loading trip details</div>;
  if (!trip) return <div>Trip not found</div>;

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">{trip.name}</h1>

      <div className="mb-8 h-64">
        <Suspense
          fallback={
            <div className="h-64 bg-gray-200 animate-pulse rounded-lg"></div>
          }
        >
          <TripMap
            center={[trip.longitude, trip.latitude]}
            zoom={12}
            pointsOfInterest={trip.pointsOfInterest}
          />
        </Suspense>
      </div>

      <Suspense fallback={<Spinner />}>
        <ItineraryBuilder
          days={trip.days}
          activities={trip.availableActivities}
          onUpdate={/* Update handler */}
        />
      </Suspense>
    </div>
  );
}
```

### API Optimization

To optimize API interactions:

- Leverage React Query for caching and stale-while-revalidate patterns
- Implement pagination for large datasets
- Use debouncing for search inputs
- Optimize data fetching with GraphQL or custom endpoints

### Asset Optimization

- Optimize images with Next.js Image component
- Use SVG for icons
- Implement responsive images
- Optimize font loading with font-display: swap

## 6. Testing Strategy

### Unit Testing

Unit tests will focus on:

- Utility functions
- Custom hooks
- Individual components

Example:

```typescript
// tests/hooks/useAuth.test.ts
import { renderHook, act } from "@testing-library/react-hooks";
import { useAuth, AuthProvider } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabase";

// Mock supabase
jest.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({
        data: { subscription: { unsubscribe: jest.fn() } },
      })),
      signInWithPassword: jest.fn(),
      signUp: jest.fn(),
      signOut: jest.fn(),
    },
  },
}));

describe("useAuth hook", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return user null and loading true initially", async () => {
    const mockSession = { data: { session: null } };
    (supabase.auth.getSession as jest.Mock).mockResolvedValueOnce(mockSession);

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), {
      wrapper,
    });

    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(true);

    await waitForNextUpdate();

    expect(result.current.loading).toBe(false);
  });

  it("should sign in user successfully", async () => {
    const mockSession = { data: { session: null } };
    (supabase.auth.getSession as jest.Mock).mockResolvedValueOnce(mockSession);
    (supabase.auth.signInWithPassword as jest.Mock).mockResolvedValueOnce({
      error: null,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), {
      wrapper,
    });

    await waitForNextUpdate();

    await act(async () => {
      await result.current.signIn("test@example.com", "password");
    });

    expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: "test@example.com",
      password: "password",
    });
  });
});
```

### Component Testing

Component tests will validate:

- Rendering states (loading, error, success)
- User interactions
- Accessibility requirements

Example:

```typescript
// tests/components/TripCard.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TripCard } from "@/components/features/TripCard";

const mockTrip = {
  id: "1",
  name: "Tokyo Adventure",
  startDate: "2025-06-15",
  endDate: "2025-06-22",
  destination: "Tokyo, Japan",
  image: "/images/tokyo.jpg",
  totalBudget: 2500,
};

describe("TripCard component", () => {
  it("renders trip information correctly", () => {
    render(
      <TripCard
        trip={mockTrip}
        onView={jest.fn()}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("Tokyo, Japan")).toBeInTheDocument();
    expect(screen.getByText("Jun 15 - Jun 22, 2025")).toBeInTheDocument();
    expect(screen.getByText("$2,500")).toBeInTheDocument();
  });

  it("calls onView when view button is clicked", async () => {
    const onView = jest.fn();
    render(
      <TripCard
        trip={mockTrip}
        onView={onView}
        onEdit={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    await userEvent.click(screen.getByText("View Trip"));

    expect(onView).toHaveBeenCalledWith("1");
  });

  it("asks for confirmation before deletion", async () => {
    const onDelete = jest.fn();
    render(
      <TripCard
        trip={mockTrip}
        onView={jest.fn()}
        onEdit={jest.fn()}
        onDelete={onDelete}
      />
    );

    await userEvent.click(screen.getByLabelText("Delete trip"));

    // Confirmation dialog should appear
    expect(
      screen.getByText("Are you sure you want to delete this trip?")
    ).toBeInTheDocument();

    // Confirm deletion
    await userEvent.click(screen.getByText("Delete"));

    expect(onDelete).toHaveBeenCalledWith("1");
  });
});
```

### End-to-End Testing

End-to-end tests will validate:

- User flows (authentication, trip creation, itinerary planning)
- Integration with backend services
- Cross-browser compatibility

Example:

```typescript
// e2e/authentication.spec.ts
import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  test("should allow user to sign up", async ({ page }) => {
    await page.goto("/auth/signup");

    // Fill the signup form
    await page.fill('[name="email"]', "test@example.com");
    await page.fill('[name="password"]', "Password123!");
    await page.fill('[name="confirmPassword"]', "Password123!");

    // Submit the form
    await page.click('button[type="submit"]');

    // Verify success message
    await expect(page.locator(".toast")).toContainText(
      "Account created successfully"
    );

    // Verify redirect to dashboard
    await expect(page).toHaveURL("/dashboard");
  });

  test("should show error for invalid credentials", async ({ page }) => {
    await page.goto("/auth/login");

    // Fill the login form with invalid credentials
    await page.fill('[name="email"]', "test@example.com");
    await page.fill('[name="password"]', "wrongpassword");

    // Submit the form
    await page.click('button[type="submit"]');

    // Verify error message
    await expect(page.locator(".error-message")).toContainText(
      "Invalid email or password"
    );

    // Verify still on login page
    await expect(page).toHaveURL("/auth/login");
  });
});
```

## 7. Deployment and CI/CD

### Deployment Strategy

TripSage will use Vercel for deployment with the following workflow:

1. **Development**: Feature branches with preview deployments
2. **Staging**: Main branch with staging environment
3. **Production**: Production branch with production environment

### CI/CD Pipeline

- **GitHub Actions**: For automated testing and deployment
- **Vercel Integration**: For seamless preview deployments
- **Quality Checks**: ESLint, TypeScript type checking, unit tests

Example GitHub Actions workflow:

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, production]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "18"
          cache: "npm"
      - name: Install dependencies
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check
        run: npm run type-check
      - name: Run tests
        run: npm test

  e2e-tests:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "18"
          cache: "npm"
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      - name: Run E2E tests
        run: npm run test:e2e

  deploy:
    needs: [test, e2e-tests]
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/production')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          vercel-args: ${{ github.ref == 'refs/heads/production' && '--prod' || '' }}
```

## 8. Monitoring and Analytics

### Error Tracking

- **Sentry**: For real-time error tracking and monitoring
- **Logging**: Structured logs with context for debugging

### Performance Monitoring

- **Core Web Vitals**: Track LCP, FID, CLS
- **Custom metrics**: Track component rendering time, API response time

### User Analytics

- **Google Analytics**: For user behavior analysis
- **Hotjar**: For heatmaps and session recordings
- **Custom events**: Track feature usage and conversion paths

## 9. Accessibility Compliance

TripSage is committed to WCAG 2.1 AA compliance:

- **Keyboard navigation**: All features must be accessible via keyboard
- **Screen readers**: Proper ARIA attributes and semantic HTML
- **Color contrast**: Meet AA standards for text and UI elements
- **Focus management**: Clear focus indicators and logical tab order

Example pattern:

```tsx
// components/ui/Dialog.tsx
import { useRef, useEffect } from "react";
import { Dialog as HeadlessDialog } from "@headlessui/react";

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Dialog = ({ isOpen, onClose, title, children }: DialogProps) => {
  const initialFocusRef = useRef<HTMLButtonElement>(null);

  // Trap focus when dialog opens
  useEffect(() => {
    if (isOpen) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          onClose();
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, onClose]);

  return (
    <HeadlessDialog
      open={isOpen}
      onClose={onClose}
      initialFocus={initialFocusRef}
      className="relative z-50"
    >
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <HeadlessDialog.Panel className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
          <HeadlessDialog.Title
            as="h3"
            className="text-lg font-medium text-gray-900"
          >
            {title}
          </HeadlessDialog.Title>

          <div className="mt-4">{children}</div>

          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              ref={initialFocusRef}
              className="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              onClick={onClose}
            >
              Confirm
            </button>
          </div>
        </HeadlessDialog.Panel>
      </div>
    </HeadlessDialog>
  );
};
```

## 10. Implementation Timeline

The frontend implementation will follow this timeline:

### Phase 1: Foundation (2 weeks)

- Project setup and configuration
- Core components and styling
- Authentication system
- Basic navigation and routing

### Phase 2: Core Features (4 weeks)

- Trip creation and management
- Search and filtering
- Map integration
- Basic itinerary planning

### Phase 3: Advanced Features (4 weeks)

- Budget planning and tracking
- Drag-and-drop itinerary builder
- Weather integration
- Recommendation system

### Phase 4: Polish and Optimization (2 weeks)

- Performance optimization
- Accessibility improvements
- Cross-browser testing
- Final UI polishing

### Phase 5: Testing and Deployment (2 weeks)

- Complete test suite
- CI/CD setup
- Documentation
- Production deployment

## Conclusion

This frontend specification outlines a comprehensive plan for building the TripSage travel planning application. By leveraging modern React, TypeScript, and a collection of best-in-class libraries, the frontend will provide a robust, scalable, and user-friendly experience. The focus on performance, accessibility, and testing ensures a high-quality product that meets the needs of travelers planning their adventures.
