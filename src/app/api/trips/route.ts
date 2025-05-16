import { createRouteHandler } from '@/lib/validation/route-handler';
import { TripCreateSchema, TripSearchSchema } from '@/lib/schemas/trip';
import { PaginatedResponseSchema } from '@/lib/schemas/common';
import { z } from 'zod';

// GET /api/trips - List trips with search and pagination
export const GET = createRouteHandler({
  query: TripSearchSchema,
  response: PaginatedResponseSchema(z.object({
    id: z.string(),
    name: z.string(),
    destinations: z.array(z.string()),
    startDate: z.string(),
    endDate: z.string(),
    status: z.enum(['draft', 'planning', 'booked', 'completed']),
    budget: z.object({
      currency: z.string(),
      total: z.number().optional(),
    }),
  })),
  handler: async ({ query }) => {
    // TODO: Implement actual database query
    const mockTrips = [
      {
        id: '1',
        name: 'European Adventure',
        destinations: ['Paris', 'Rome', 'Barcelona'],
        startDate: '2025-06-01',
        endDate: '2025-06-15',
        status: 'planning' as const,
        budget: {
          currency: 'EUR',
          total: 5000,
        },
      },
    ];

    // Apply filters
    let filtered = mockTrips;
    
    if (query.query) {
      filtered = filtered.filter(trip => 
        trip.name.toLowerCase().includes(query.query!.toLowerCase())
      );
    }

    if (query.status) {
      filtered = filtered.filter(trip => trip.status === query.status);
    }

    // Apply pagination
    const total = filtered.length;
    const start = (query.page - 1) * query.limit;
    const end = start + query.limit;
    const paginatedTrips = filtered.slice(start, end);

    return {
      success: true,
      data: paginatedTrips,
      pagination: {
        page: query.page,
        limit: query.limit,
        total,
        totalPages: Math.ceil(total / query.limit),
        hasNext: end < total,
        hasPrev: query.page > 1,
      },
    };
  },
});

// POST /api/trips - Create a new trip
export const POST = createRouteHandler({
  body: TripCreateSchema,
  response: z.object({
    success: z.boolean(),
    data: z.object({
      id: z.string(),
      userId: z.string(),
      status: z.enum(['draft', 'planning', 'booked', 'completed']),
      createdAt: z.date(),
      updatedAt: z.date(),
    }).merge(TripCreateSchema),
  }),
  handler: async ({ body }) => {
    // TODO: Implement actual trip creation
    console.log('Creating trip:', body);

    // Validate date range
    const startDate = new Date(body.startDate);
    const endDate = new Date(body.endDate);
    
    if (startDate >= endDate) {
      throw new Error('End date must be after start date');
    }

    // Mock response
    const newTrip = {
      id: `trip-${Date.now()}`,
      userId: 'user-123', // TODO: Get from auth context
      status: 'draft' as const,
      createdAt: new Date(),
      updatedAt: new Date(),
      ...body,
    };

    return {
      success: true,
      data: newTrip,
    };
  },
});