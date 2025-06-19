#!/bin/bash

# ===================================================================
# Supabase Edge Functions Deployment Script
# ===================================================================
# This script deploys all Edge Functions and sets up database triggers

set -e

echo "🚀 Deploying TripSage Edge Functions..."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI is not installed. Please install it first:"
    echo "   npm install -g supabase"
    exit 1
fi

# Check if we're in a Supabase project
if [ ! -f "config.toml" ]; then
    echo "❌ Not in a Supabase project directory. Please run from the supabase/ directory."
    exit 1
fi

echo "📦 Deploying Edge Functions..."

# Deploy all functions
echo "  📝 Deploying trip-notifications..."
supabase functions deploy trip-notifications

echo "  📁 Deploying file-processing..."
supabase functions deploy file-processing

echo "  🔄 Deploying cache-invalidation..."
supabase functions deploy cache-invalidation

echo "✅ All Edge Functions deployed successfully!"

# Set up database triggers
echo "🔧 Setting up database triggers..."
supabase db reset --linked
psql -h localhost -p 54322 -d postgres -U postgres -f functions/setup_edge_function_triggers.sql

echo "✅ Database triggers configured!"

# Display function URLs
echo "📋 Edge Function URLs:"
PROJECT_REF=$(grep 'project_id' config.toml | cut -d'"' -f2)
if [ -n "$PROJECT_REF" ]; then
    echo "  🔗 Trip Notifications: https://$PROJECT_REF.supabase.co/functions/v1/trip-notifications"
    echo "  🔗 File Processing: https://$PROJECT_REF.supabase.co/functions/v1/file-processing"
    echo "  🔗 Cache Invalidation: https://$PROJECT_REF.supabase.co/functions/v1/cache-invalidation"
else
    echo "  🔗 Functions are deployed but project reference not found in config.toml"
fi

echo ""
echo "🎉 Deployment complete! Next steps:"
echo ""
echo "1. Set environment variables (secrets):"
echo "   supabase secrets set RESEND_API_KEY=your_resend_api_key"
echo "   supabase secrets set REDIS_URL=redis://your-redis-url:6379"
echo "   supabase secrets set REDIS_PASSWORD=your_redis_password"
echo "   supabase secrets set WEBHOOK_SECRET=your_webhook_secret"
echo ""
echo "2. Test the functions:"
echo "   curl -X POST https://$PROJECT_REF.supabase.co/functions/v1/trip-notifications ..."
echo ""
echo "3. Monitor function logs:"
echo "   supabase functions logs trip-notifications"
echo ""
echo "📖 See README.md for detailed usage instructions."