#!/bin/bash

# TripSage Documentation Reorganization Script
# Based on Final Consolidation Report findings
# Execute from repository root directory

set -e  # Exit on any error

echo "🚀 Starting TripSage Documentation Reorganization..."
echo "📍 Working directory: $(pwd)"

# Verify we're in the correct directory
if [[ ! -d "docs" ]]; then
    echo "❌ Error: docs directory not found. Please run from repository root."
    exit 1
fi

echo "✅ Found docs directory. Proceeding with reorganization..."

# Create backup
echo "📦 Creating backup of current documentation..."
cp -r docs docs_backup_$(date +%Y%m%d_%H%M%S)

# ========================================
# PHASE 1: Remove Duplicates and Critical Issues
# ========================================

echo "🗑️  PHASE 1: Removing duplicates and critical issues..."

# Remove duplicate search/caching folder
if [[ -d "docs/05_SEARCH_AND_CACHING" ]]; then
    echo "   Removing duplicate folder: 05_SEARCH_AND_CACHING/"
    rm -rf docs/05_SEARCH_AND_CACHING/
fi

# Remove duplicate installation folder  
if [[ -d "docs/07_INSTALLATION_AND_SETUP" ]]; then
    echo "   Removing duplicate folder: 07_INSTALLATION_AND_SETUP/"
    rm -rf docs/07_INSTALLATION_AND_SETUP/
fi

# Remove isolated testing folder (content will be integrated)
if [[ -d "docs/testing" ]]; then
    echo "   Removing isolated testing folder (content to be integrated)"
    rm -rf docs/testing/
fi

# Remove security subfolder and reorganize
if [[ -d "docs/07_CONFIGURATION/SECURITY" ]]; then
    echo "   Reorganizing security documentation..."
    # Move security files to main config folder
    if [[ -f "docs/07_CONFIGURATION/SECURITY/OVERVIEW.md" ]]; then
        mv docs/07_CONFIGURATION/SECURITY/OVERVIEW.md docs/07_CONFIGURATION/security_overview.md
    fi
    if [[ -f "docs/07_CONFIGURATION/SECURITY/SECURITY_BEST_PRACTICES.md" ]]; then
        mv docs/07_CONFIGURATION/SECURITY/SECURITY_BEST_PRACTICES.md docs/07_CONFIGURATION/security_best_practices.md
    fi
    if [[ -f "docs/07_CONFIGURATION/SECURITY/RLS_IMPLEMENTATION.md" ]]; then
        mv docs/07_CONFIGURATION/SECURITY/RLS_IMPLEMENTATION.md docs/07_CONFIGURATION/rls_implementation.md
    fi
    if [[ -f "docs/07_CONFIGURATION/SECURITY/SECURITY_TESTING.md" ]]; then
        mv docs/07_CONFIGURATION/SECURITY/SECURITY_TESTING.md docs/07_CONFIGURATION/security_testing.md
    fi
    # Remove empty security folder
    rmdir docs/07_CONFIGURATION/SECURITY/ 2>/dev/null || true
fi

echo "✅ PHASE 1 Complete: Duplicates and critical issues removed"

# ========================================
# PHASE 2: Fix File Naming Conventions
# ========================================

echo "📝 PHASE 2: Fixing file naming conventions..."

# Navigate to API reference folder
cd docs/06_API_REFERENCE/

# Fix naming violations in API reference
if [[ -f "REAL_TIME_COLLABORATION_GUIDE.md" ]]; then
    echo "   Renaming: REAL_TIME_COLLABORATION_GUIDE.md -> real_time_collaboration_guide.md"
    mv REAL_TIME_COLLABORATION_GUIDE.md real_time_collaboration_guide.md
fi

if [[ -f "WEBSOCKET_CONNECTION_GUIDE.md" ]]; then
    echo "   Renaming: WEBSOCKET_CONNECTION_GUIDE.md -> websocket_connection_guide.md"
    mv WEBSOCKET_CONNECTION_GUIDE.md websocket_connection_guide.md
fi

if [[ -f "WEBSOCKET_API.md" ]]; then
    echo "   Renaming: WEBSOCKET_API.md -> websocket_api.md"
    mv WEBSOCKET_API.md websocket_api.md
fi

if [[ -f "REST_API_ENDPOINTS.md" ]]; then
    echo "   Renaming: REST_API_ENDPOINTS.md -> rest_api_endpoints.md"
    mv REST_API_ENDPOINTS.md rest_api_endpoints.md
fi

if [[ -f "DATABASE_SCHEMA.md" ]]; then
    echo "   Renaming: DATABASE_SCHEMA.md -> database_schema.md"
    mv DATABASE_SCHEMA.md database_schema.md
fi

if [[ -f "DATABASE_TRIGGERS.md" ]]; then
    echo "   Renaming: DATABASE_TRIGGERS.md -> database_triggers.md"
    mv DATABASE_TRIGGERS.md database_triggers.md
fi

if [[ -f "DATA_MODELS.md" ]]; then
    echo "   Renaming: DATA_MODELS.md -> data_models.md"
    mv DATA_MODELS.md data_models.md
fi

if [[ -f "ERROR_CODES.md" ]]; then
    echo "   Renaming: ERROR_CODES.md -> error_codes.md"
    mv ERROR_CODES.md error_codes.md
fi

if [[ -f "AUTHENTICATION_API.md" ]]; then
    echo "   Renaming: AUTHENTICATION_API.md -> authentication_api.md"
    mv AUTHENTICATION_API.md authentication_api.md
fi

if [[ -f "STORAGE_ARCHITECTURE.md" ]]; then
    echo "   Renaming: STORAGE_ARCHITECTURE.md -> storage_architecture.md"
    mv STORAGE_ARCHITECTURE.md storage_architecture.md
fi

if [[ -f "API_EXAMPLES.md" ]]; then
    echo "   Renaming: API_EXAMPLES.md -> api_examples.md"
    mv API_EXAMPLES.md api_examples.md
fi

# Return to docs root
cd ..

# Mark oversized files for splitting
if [[ -f "06_API_REFERENCE/real_time_collaboration_guide.md" ]]; then
    echo "   Marking oversized file: real_time_collaboration_guide.md"
    mv 06_API_REFERENCE/real_time_collaboration_guide.md 06_API_REFERENCE/real_time_collaboration_guide.OVERSIZED.md
fi

if [[ -f "06_API_REFERENCE/websocket_connection_guide.md" ]]; then
    echo "   Marking oversized file: websocket_connection_guide.md"
    mv 06_API_REFERENCE/websocket_connection_guide.md 06_API_REFERENCE/websocket_connection_guide.OVERSIZED.md
fi

echo "✅ PHASE 2 Complete: File naming conventions fixed"

# ========================================
# PHASE 3: Content Reorganization
# ========================================

echo "🔀 PHASE 3: Content reorganization..."

# Move API examples from user guides to API reference
if [[ -f "08_USER_GUIDES/API_USAGE_EXAMPLES.md" ]]; then
    echo "   Moving API examples to API reference folder"
    mv 08_USER_GUIDES/API_USAGE_EXAMPLES.md 06_API_REFERENCE/api_usage_examples.md
fi

# Create missing configuration files
echo "   Creating missing configuration files..."
if [[ ! -f "07_CONFIGURATION/feature_flags.md" ]]; then
    cat > 07_CONFIGURATION/feature_flags.md << 'EOF'
# Feature Flags Configuration

> **Feature Toggle Management for TripSage**
> Documentation for managing feature flags across environments

## Overview

TripSage uses feature flags to control functionality rollout, A/B testing, and safe deployment practices.

## Implementation

Feature flags are managed through environment variables and runtime configuration.

*This file was created during documentation reorganization - content to be added based on actual implementation.*
EOF
fi

if [[ ! -f "07_CONFIGURATION/logging_configuration.md" ]]; then
    cat > 07_CONFIGURATION/logging_configuration.md << 'EOF'
# Logging Configuration

> **Application Logging Setup and Management**
> Configuration guides for logging across all TripSage environments

## Overview

Comprehensive logging configuration for development, staging, and production environments.

## Implementation

Logging is handled through structured JSON logging with configurable levels.

*This file was created during documentation reorganization - content to be added based on actual implementation.*
EOF
fi

if [[ ! -f "07_CONFIGURATION/monitoring_setup.md" ]]; then
    cat > 07_CONFIGURATION/monitoring_setup.md << 'EOF'
# Monitoring Setup

> **Observability and Monitoring Configuration**
> Setup guides for application monitoring and observability

## Overview

Monitoring setup using OpenTelemetry, Grafana, and other observability tools.

## Implementation

Comprehensive monitoring covers application metrics, traces, and logs.

*This file was created during documentation reorganization - content to be added based on actual implementation.*
EOF
fi

# Reorganize research content
echo "   Reorganizing research content..."
if [[ -d "10_RESEARCH/reviews" ]]; then
    mkdir -p 10_RESEARCH/implementation_reports/
    mv 10_RESEARCH/reviews/* 10_RESEARCH/implementation_reports/ 2>/dev/null || true
    rmdir 10_RESEARCH/reviews/ 2>/dev/null || true
fi

echo "✅ PHASE 3 Complete: Content reorganization finished"

# ========================================
# PHASE 4: Update Documentation Structure
# ========================================

echo "📚 PHASE 4: Updating documentation structure..."

# Rename research folder to follow numbering convention
if [[ -d "10_RESEARCH" ]]; then
    echo "   Renaming research folder to follow convention"
    mv 10_RESEARCH 09_RESEARCH
fi

# Create new user guide files as placeholders
echo "   Creating new user guide files..."

if [[ ! -f "08_USER_GUIDES/user_journey.md" ]]; then
    cat > 08_USER_GUIDES/user_journey.md << 'EOF'
# User Journey Guide

> **End-to-End User Experience Documentation**
> Complete user workflows from onboarding to trip completion

## Overview

This guide walks through the complete TripSage user experience.

*This file was created during documentation reorganization - content to be added based on user research.*
EOF
fi

if [[ ! -f "08_USER_GUIDES/travel_planning_guide.md" ]]; then
    cat > 08_USER_GUIDES/travel_planning_guide.md << 'EOF'
# Travel Planning Guide

> **Step-by-Step Travel Planning with TripSage**
> Comprehensive guide for planning trips using TripSage features

## Overview

Complete walkthrough of trip planning features and capabilities.

*This file was created during documentation reorganization - content to be added based on feature documentation.*
EOF
fi

if [[ ! -f "08_USER_GUIDES/troubleshooting.md" ]]; then
    cat > 08_USER_GUIDES/troubleshooting.md << 'EOF'
# Troubleshooting Guide

> **Common Issues and Solutions**
> User-focused troubleshooting for TripSage application

## Overview

Common problems users encounter and their solutions.

*This file was created during documentation reorganization - content to be added based on support requests.*
EOF
fi

# Create feature documentation placeholders
echo "   Creating missing feature documentation..."

if [[ ! -f "05_FEATURES_AND_INTEGRATIONS/memory_system.md" ]]; then
    cat > 05_FEATURES_AND_INTEGRATIONS/memory_system.md << 'EOF'
# Memory System

> **AI Memory and Context Management**
> TripSage's intelligent memory system using Mem0

## Overview

The memory system provides context-aware conversations and personalized recommendations.

*This file was created during documentation reorganization - content to be added based on actual implementation.*
EOF
fi

if [[ ! -f "05_FEATURES_AND_INTEGRATIONS/agent_capabilities.md" ]]; then
    cat > 05_FEATURES_AND_INTEGRATIONS/agent_capabilities.md << 'EOF'
# Agent Capabilities

> **AI Agent Features and Abilities**
> Comprehensive overview of TripSage AI agent capabilities

## Overview

Multi-agent orchestration for specialized travel planning tasks.

*This file was created during documentation reorganization - content to be added based on agent implementation.*
EOF
fi

if [[ ! -f "05_FEATURES_AND_INTEGRATIONS/authentication_system.md" ]]; then
    cat > 05_FEATURES_AND_INTEGRATIONS/authentication_system.md << 'EOF'
# Authentication System

> **User Authentication and Authorization**
> Complete authentication system documentation

## Overview

Secure user authentication using Supabase Auth with JWT tokens.

*This file was created during documentation reorganization - content to be added based on auth implementation.*
EOF
fi

if [[ ! -f "05_FEATURES_AND_INTEGRATIONS/notification_system.md" ]]; then
    cat > 05_FEATURES_AND_INTEGRATIONS/notification_system.md << 'EOF'
# Notification System

> **Real-time Notifications and Alerts**
> User notification and communication system

## Overview

Real-time notifications for trip updates, bookings, and system alerts.

*This file was created during documentation reorganization - content to be added based on notification implementation.*
EOF
fi

echo "✅ PHASE 4 Complete: Documentation structure updated"

# ========================================
# FINAL VERIFICATION
# ========================================

echo "🔍 FINAL VERIFICATION: Checking reorganization results..."

# Count files and folders
total_docs=$(find docs -name "*.md" | wc -l)
echo "   📊 Total documentation files: $total_docs"

# Check for remaining duplicates
duplicate_count=0
if [[ -d "docs/05_SEARCH_AND_CACHING" ]]; then
    echo "   ⚠️  Warning: 05_SEARCH_AND_CACHING still exists"
    duplicate_count=$((duplicate_count + 1))
fi

if [[ -d "docs/07_INSTALLATION_AND_SETUP" ]]; then
    echo "   ⚠️  Warning: 07_INSTALLATION_AND_SETUP still exists"
    duplicate_count=$((duplicate_count + 1))
fi

if [[ $duplicate_count -eq 0 ]]; then
    echo "   ✅ No duplicate folders found"
else
    echo "   ❌ Found $duplicate_count duplicate folders"
fi

# Check for proper naming conventions
uppercase_files=$(find docs -name "*.md" | grep -E '[A-Z]' | wc -l)
if [[ $uppercase_files -eq 0 ]]; then
    echo "   ✅ All files follow naming conventions"
else
    echo "   ⚠️  Found $uppercase_files files with uppercase letters"
fi

echo ""
echo "🎉 REORGANIZATION COMPLETE!"
echo ""
echo "📋 Summary:"
echo "   - Removed duplicate folders and content"
echo "   - Fixed file naming conventions"
echo "   - Reorganized content placement"
echo "   - Created missing configuration files"
echo "   - Added placeholder files for missing content"
echo ""
echo "📁 Backup created at: docs_backup_$(date +%Y%m%d_%H%M%S)"
echo ""
echo "🔗 Next Steps:"
echo "   1. Review the FINAL_CONSOLIDATION_REPORT.md for detailed analysis"
echo "   2. Update content in newly created placeholder files"
echo "   3. Fix module paths and imports in technical documentation"
echo "   4. Verify all cross-references and internal links"
echo "   5. Update Pydantic v1 examples to v2 syntax"
echo ""
echo "✨ Documentation reorganization complete!"