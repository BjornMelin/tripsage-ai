/**
 * Admin Configuration Page
 * 
 * Next.js page component for the configuration management interface.
 * Provides access to the ConfigurationManager component with proper authentication.
 */

import { Metadata } from 'next';
import { Suspense } from 'react';
import ConfigurationManager from '@/components/admin/configuration-manager';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export const metadata: Metadata = {
  title: 'Agent Configuration - TripSage Admin',
  description: 'Manage AI agent configurations, monitor performance, and track version history',
};

export default function ConfigurationPage() {
  return (
    <div className="container mx-auto py-6">
      <Suspense 
        fallback={
          <div className="flex items-center justify-center min-h-[400px]">
            <LoadingSpinner size="lg" />
          </div>
        }
      >
        <ConfigurationManager />
      </Suspense>
    </div>
  );
}