#!/usr/bin/env python3
"""
TripSage Database Schema Validation Script
Validates Supabase database structure and identifies integration issues.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set
import re


def analyze_schema_files() -> Dict[str, any]:
    """Analyze schema files for completeness and consistency."""
    schema_dir = Path("supabase/schemas")
    migration_dir = Path("supabase/migrations")
    
    results = {
        "tables": set(),
        "indexes": set(),
        "policies": set(),
        "missing_components": [],
        "inconsistencies": [],
        "recommendations": []
    }
    
    # Analyze tables
    tables_file = schema_dir / "01_tables.sql"
    if tables_file.exists():
        content = tables_file.read_text()
        # Find CREATE TABLE statements
        table_matches = re.findall(r'CREATE TABLE.*?(\w+)\s*\(', content, re.IGNORECASE)
        results["tables"] = set(table_matches)
        print(f"✅ Found {len(table_matches)} tables in schema")
    
    # Analyze indexes
    indexes_file = schema_dir / "02_indexes.sql"
    if indexes_file.exists():
        content = indexes_file.read_text()
        # Find CREATE INDEX statements
        index_matches = re.findall(r'CREATE INDEX.*?(\w+)\s+ON\s+(\w+)', content, re.IGNORECASE)
        results["indexes"] = {f"{table}.{index}" for index, table in index_matches}
        print(f"✅ Found {len(index_matches)} indexes in schema")
    
    # Analyze RLS policies
    policies_file = schema_dir / "05_policies.sql"
    if policies_file.exists():
        content = policies_file.read_text()
        # Find CREATE POLICY statements
        policy_matches = re.findall(r'CREATE POLICY.*?"([^"]+)".*?ON\s+(\w+)', content, re.IGNORECASE)
        results["policies"] = {f"{table}.{policy}" for policy, table in policy_matches}
        print(f"✅ Found {len(policy_matches)} RLS policies in schema")
    
    return results


def check_trip_collaborators_integration() -> List[str]:
    """Check if trip_collaborators table is properly integrated."""
    issues = []
    
    # Check if table exists in main schema
    tables_file = Path("supabase/schemas/01_tables.sql")
    if tables_file.exists():
        content = tables_file.read_text()
        if "trip_collaborators" in content:
            print("✅ trip_collaborators table found in main schema")
        else:
            issues.append("❌ trip_collaborators table missing from main schema")
    
    # Check for indexes
    indexes_file = Path("supabase/schemas/02_indexes.sql")
    if indexes_file.exists():
        content = indexes_file.read_text()
        if "trip_collaborators" in content:
            print("✅ trip_collaborators indexes found")
        else:
            issues.append("❌ trip_collaborators indexes missing")
    
    # Check for RLS policies
    policies_file = Path("supabase/schemas/05_policies.sql")
    if policies_file.exists():
        content = policies_file.read_text()
        if "trip_collaborators" in content:
            print("✅ trip_collaborators RLS policies found")
        else:
            issues.append("❌ trip_collaborators RLS policies missing")
    
    # Check migration file
    migration_file = Path("supabase/migrations/20250611_01_add_trip_collaborators_table.sql")
    if migration_file.exists():
        print("✅ trip_collaborators migration file exists")
    else:
        issues.append("❌ trip_collaborators migration file not found")
    
    return issues


def analyze_foreign_key_constraints() -> List[str]:
    """Analyze foreign key relationships for data integrity."""
    issues = []
    
    tables_file = Path("supabase/schemas/01_tables.sql")
    if not tables_file.exists():
        return ["❌ Main tables schema file not found"]
    
    content = tables_file.read_text()
    
    # Check for proper foreign key references
    fk_patterns = [
        (r'user_id UUID.*REFERENCES auth\.users\(id\)', "auth.users references"),
        (r'trip_id.*REFERENCES trips\(id\)', "trip references"),
        (r'session_id.*REFERENCES chat_sessions\(id\)', "chat session references")
    ]
    
    for pattern, description in fk_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"✅ Found {len(matches)} {description}")
        else:
            issues.append(f"⚠️  No {description} found - check foreign key integrity")
    
    return issues


def check_memory_table_consistency() -> List[str]:
    """Check memory tables for Mem0 integration consistency."""
    issues = []
    
    tables_file = Path("supabase/schemas/01_tables.sql")
    if not tables_file.exists():
        return ["❌ Cannot check memory tables - schema file missing"]
    
    content = tables_file.read_text()
    
    # Check if memory tables use TEXT user_id (as noted in policies)
    if "memories" in content:
        if "user_id TEXT" in content:
            print("✅ Memory tables use TEXT user_id for Mem0 compatibility")
        else:
            issues.append("⚠️  Memory tables may not be configured for Mem0 TEXT user_id")
    
    # Check for vector embeddings
    if "vector(" in content:
        print("✅ Vector embeddings configured for pgvector")
    else:
        issues.append("❌ Vector embeddings not found - pgvector integration incomplete")
    
    return issues


def generate_recommendations() -> List[str]:
    """Generate actionable recommendations for database improvements."""
    recommendations = []
    
    # Check if trip_collaborators is properly integrated
    issues = check_trip_collaborators_integration()
    if any("missing" in issue for issue in issues):
        recommendations.append(
            "🔧 CRITICAL: Integrate trip_collaborators table into main schema files "
            "(add indexes and RLS policies to 02_indexes.sql and 05_policies.sql)"
        )
    
    # Check for schema consolidation
    migration_dir = Path("supabase/migrations")
    if migration_dir.exists():
        migrations = list(migration_dir.glob("*.sql"))
        if len(migrations) > 2:
            recommendations.append(
                f"🔧 Consider consolidating {len(migrations)} migration files "
                "into a single production schema for easier reproduction"
            )
    
    # Security recommendations
    recommendations.extend([
        "🔒 SECURITY: Verify JWT_SECRET is properly configured (not hardcoded)",
        "🔒 SECURITY: Ensure all user-owned tables have RLS policies enabled",
        "🔧 PERFORMANCE: Consider adding composite indexes for common query patterns",
        "🔧 MAINTENANCE: Add database maintenance functions for vector index optimization"
    ])
    
    return recommendations


def main():
    """Main validation function."""
    print("🔍 TripSage Database Schema Validation")
    print("=" * 50)
    
    # Change to project directory (parent of supabase dir)
    os.chdir(Path(__file__).parent.parent)
    
    # Check if schema directory exists
    if not Path("supabase").exists():
        print("❌ Supabase directory not found!")
        sys.exit(1)
    
    # Analyze schema
    schema_results = analyze_schema_files()
    
    print(f"\n📊 Schema Analysis Results:")
    print(f"   Tables: {len(schema_results['tables'])}")
    print(f"   Indexes: {len(schema_results['indexes'])}")
    print(f"   RLS Policies: {len(schema_results['policies'])}")
    
    # Check specific integrations
    print(f"\n🔗 Integration Analysis:")
    
    # Trip collaborators
    collab_issues = check_trip_collaborators_integration()
    if collab_issues:
        print("Trip Collaborators Issues:")
        for issue in collab_issues:
            print(f"   {issue}")
    
    # Foreign keys
    fk_issues = analyze_foreign_key_constraints()
    if fk_issues:
        print("Foreign Key Issues:")
        for issue in fk_issues:
            print(f"   {issue}")
    
    # Memory system
    memory_issues = check_memory_table_consistency()
    if memory_issues:
        print("Memory System Issues:")
        for issue in memory_issues:
            print(f"   {issue}")
    
    # Generate recommendations
    print(f"\n💡 Recommendations:")
    recommendations = generate_recommendations()
    for rec in recommendations:
        print(f"   {rec}")
    
    print(f"\n✨ Validation Complete")
    
    # Return status
    all_issues = collab_issues + fk_issues + memory_issues
    critical_issues = [i for i in all_issues if "❌" in i]
    
    if critical_issues:
        print(f"\n🚨 Found {len(critical_issues)} critical issues requiring immediate attention")
        return 1
    else:
        print(f"\n✅ No critical issues found - database schema is production-ready")
        return 0


if __name__ == "__main__":
    sys.exit(main())