'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { TripCreateSchema, TripCreateInput } from '@/lib/schemas/trip';
import { createTrip } from '@/lib/validation/server-actions';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function TripCreateForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<TripCreateInput>({
    resolver: zodResolver(TripCreateSchema),
    defaultValues: {
      travelers: 1,
      budget: {
        currency: 'USD',
      },
    },
  });

  const onSubmit = async (data: TripCreateInput) => {
    setIsSubmitting(true);
    
    try {
      const result = await createTrip(data);
      
      if (result.success) {
        router.push(`/trips/${result.data.id}`);
      } else {
        // Handle error
        console.error('Failed to create trip:', result.error);
      }
    } catch (error) {
      console.error('Error creating trip:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Trip Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium">
          Trip Name
        </label>
        <input
          {...register('name')}
          type="text"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          placeholder="My Amazing Trip"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium">
          Description
        </label>
        <textarea
          {...register('description')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          rows={3}
        />
      </div>

      {/* Destinations */}
      <div>
        <label className="block text-sm font-medium">Destinations</label>
        <div className="mt-1 space-y-2">
          <input
            {...register('destinations.0')}
            type="text"
            className="block w-full rounded-md border-gray-300 shadow-sm"
            placeholder="Paris, France"
          />
        </div>
        {errors.destinations && (
          <p className="mt-1 text-sm text-red-600">{errors.destinations.message}</p>
        )}
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="startDate" className="block text-sm font-medium">
            Start Date
          </label>
          <input
            {...register('startDate')}
            type="date"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.startDate && (
            <p className="mt-1 text-sm text-red-600">{errors.startDate.message}</p>
          )}
        </div>
        
        <div>
          <label htmlFor="endDate" className="block text-sm font-medium">
            End Date
          </label>
          <input
            {...register('endDate')}
            type="date"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.endDate && (
            <p className="mt-1 text-sm text-red-600">{errors.endDate.message}</p>
          )}
        </div>
      </div>

      {/* Budget */}
      <div>
        <label htmlFor="budget.total" className="block text-sm font-medium">
          Total Budget
        </label>
        <div className="mt-1 flex gap-2">
          <select
            {...register('budget.currency')}
            className="rounded-md border-gray-300 shadow-sm"
          >
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
          </select>
          <input
            {...register('budget.total', { valueAsNumber: true })}
            type="number"
            className="flex-1 rounded-md border-gray-300 shadow-sm"
            placeholder="0.00"
          />
        </div>
        {errors.budget?.total && (
          <p className="mt-1 text-sm text-red-600">{errors.budget.total.message}</p>
        )}
      </div>

      {/* Travelers */}
      <div>
        <label htmlFor="travelers" className="block text-sm font-medium">
          Number of Travelers
        </label>
        <input
          {...register('travelers', { valueAsNumber: true })}
          type="number"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          min="1"
        />
        {errors.travelers && (
          <p className="mt-1 text-sm text-red-600">{errors.travelers.message}</p>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Creating...' : 'Create Trip'}
      </button>
    </form>
  );
}