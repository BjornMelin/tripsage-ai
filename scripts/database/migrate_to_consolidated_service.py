#!/usr/bin/env python3
"""
Migration script to update all imports from old database services to the new consolidated service.

This script:
1. Finds all Python files importing old database services
2. Updates imports to use the new consolidated service
3. Updates code patterns to match new API
4. Creates a backup of modified files
5. Generates a migration report
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Old service imports to replace
OLD_IMPORTS = {
    "from tripsage_core.services.infrastructure.database_service import DatabaseService",
    "from tripsage_core.services.infrastructure.database_service import get_database_service",
    "from tripsage_core.services.infrastructure.database_wrapper import DatabaseWrapper",
    "from tripsage_core.services.infrastructure.database_monitor import DatabaseMonitor",
    "from tripsage_core.services.infrastructure.database_pool_manager import DatabasePoolManager",
    "from tripsage_core.services.infrastructure.secure_database_service import SecureDatabaseService",
    "from tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring import EnhancedDatabaseService",
    "from tripsage_core.services.infrastructure.enhanced_database_pool_manager import EnhancedDatabasePoolManager",
    "import tripsage_core.services.infrastructure.database_service",
    "import tripsage_core.services.infrastructure.database_wrapper",
    "import tripsage_core.services.infrastructure.database_monitor",
}

# New consolidated import
NEW_IMPORT = "from tripsage_core.services.infrastructure.consolidated_database_service import ConsolidatedDatabaseService, get_database_service"

# Pattern replacements
PATTERN_REPLACEMENTS = [
    # Class name replacements
    (r"\bDatabaseService\b", "ConsolidatedDatabaseService"),
    (r"\bDatabaseWrapper\b", "ConsolidatedDatabaseService"),
    (r"\bSecureDatabaseService\b", "ConsolidatedDatabaseService"),
    (r"\bEnhancedDatabaseService\b", "ConsolidatedDatabaseService"),
    (r"\bDatabasePoolManager\b", "ConsolidatedDatabaseService"),
    (r"\bEnhancedDatabasePoolManager\b", "ConsolidatedDatabaseService"),
    
    # Method replacements
    (r"\.execute_query\(", ".select("),
    (r"\.execute_insert\(", ".insert("),
    (r"\.execute_update\(", ".update("),
    (r"\.execute_delete\(", ".delete("),
    
    # Monitor integration
    (r"DatabaseMonitor\(\)", "# Monitoring is now integrated in ConsolidatedDatabaseService"),
    (r"\.monitor\.", "."),  # Remove monitor references
    
    # Pool manager references
    (r"\.pool_manager\.", "."),
    (r"\.get_pool\(\)", ".get_client()"),
]


def create_backup(file_path: Path) -> Path:
    """Create a backup of the file before modification."""
    backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    relative_path = file_path.relative_to(Path.cwd())
    backup_path = backup_dir / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def find_files_with_imports(root_dir: Path) -> List[Path]:
    """Find all Python files containing old database service imports."""
    files_to_migrate = []
    
    for file_path in root_dir.rglob("*.py"):
        # Skip migration script itself and test files
        if file_path.name == "migrate_to_consolidated_service.py":
            continue
        if "test" in file_path.parts:
            continue
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Check if file contains any old imports
            for old_import in OLD_IMPORTS:
                if old_import in content:
                    files_to_migrate.append(file_path)
                    break
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return files_to_migrate


def migrate_file(file_path: Path) -> Dict[str, any]:
    """Migrate a single file to use the consolidated service."""
    migration_info = {
        "file": str(file_path),
        "backup": None,
        "imports_replaced": 0,
        "patterns_replaced": 0,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Create backup
        backup_path = create_backup(file_path)
        migration_info["backup"] = str(backup_path)
        
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        original_content = content
        
        # Replace imports
        imports_found = set()
        for old_import in OLD_IMPORTS:
            if old_import in content:
                imports_found.add(old_import)
                content = content.replace(old_import, "")
                migration_info["imports_replaced"] += 1
        
        # Add new import if any old imports were found
        if imports_found:
            # Find the right place to insert the new import
            import_lines = []
            lines = content.split("\n")
            
            # Find where imports are
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    last_import_idx = i
            
            # Insert new import after last import
            lines.insert(last_import_idx + 1, NEW_IMPORT)
            content = "\n".join(lines)
        
        # Apply pattern replacements
        for pattern, replacement in PATTERN_REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                migration_info["patterns_replaced"] += content.count(pattern)
                content = new_content
        
        # Check for potential issues
        if "replica_manager" in content.lower():
            migration_info["warnings"].append("File contains replica_manager references - manual review recommended")
        
        if "security_manager" in content.lower():
            migration_info["warnings"].append("File contains security_manager references - consider using RLS instead")
        
        # Write migrated content
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            migration_info["warnings"].append("No changes made to file")
        
    except Exception as e:
        migration_info["errors"].append(str(e))
    
    return migration_info


def generate_compatibility_layer() -> None:
    """Generate a compatibility layer for gradual migration."""
    compatibility_code = '''"""
Compatibility layer for gradual migration to consolidated database service.

This module provides wrapper classes that maintain the old API while using
the new consolidated service internally.
"""

from typing import Any, Dict, List, Optional
from tripsage_core.services.infrastructure.consolidated_database_service import (
    ConsolidatedDatabaseService,
    ConnectionMode,
    get_database_service,
)


class DatabaseService(ConsolidatedDatabaseService):
    """Compatibility wrapper for old DatabaseService."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default to session mode for compatibility
        self.default_mode = ConnectionMode.SESSION


class DatabaseWrapper(ConsolidatedDatabaseService):
    """Compatibility wrapper for old DatabaseWrapper."""
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Legacy execute_query method."""
        # This would need to parse the query and call appropriate method
        # For now, raise NotImplementedError
        raise NotImplementedError(
            "execute_query is deprecated. Use select(), insert(), update(), or delete() methods instead."
        )


class SecureDatabaseService(ConsolidatedDatabaseService):
    """Compatibility wrapper for old SecureDatabaseService."""
    
    def __init__(self, *args, **kwargs):
        # Extract security-specific parameters
        enable_security_hardening = kwargs.pop("enable_security_hardening", True)
        
        super().__init__(*args, **kwargs)
        
        if enable_security_hardening:
            print("Note: Security hardening is now handled by Supabase RLS. "
                  "Consider migrating your security rules to RLS policies.")


class DatabasePoolManager:
    """Compatibility wrapper for old DatabasePoolManager."""
    
    def __init__(self, *args, **kwargs):
        self._service = ConsolidatedDatabaseService(
            default_mode=ConnectionMode.TRANSACTION
        )
    
    async def initialize(self):
        """Initialize the pool manager."""
        await self._service.connect()
    
    async def get_client(self):
        """Get a database client."""
        return self._service


# Alias old function names
async def get_database_wrapper():
    """Legacy function for getting database wrapper."""
    return await get_database_service()
'''
    
    compatibility_path = Path("tripsage_core/services/infrastructure/database_compatibility.py")
    with open(compatibility_path, "w", encoding="utf-8") as f:
        f.write(compatibility_code)
    
    print(f"Created compatibility layer at: {compatibility_path}")


def generate_migration_report(results: List[Dict[str, any]]) -> None:
    """Generate a detailed migration report."""
    report_path = Path("migration_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Database Service Migration Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary
        total_files = len(results)
        successful = sum(1 for r in results if not r["errors"])
        total_imports = sum(r["imports_replaced"] for r in results)
        total_patterns = sum(r["patterns_replaced"] for r in results)
        
        f.write("## Summary\n\n")
        f.write(f"- Total files processed: {total_files}\n")
        f.write(f"- Successful migrations: {successful}\n")
        f.write(f"- Total imports replaced: {total_imports}\n")
        f.write(f"- Total patterns replaced: {total_patterns}\n\n")
        
        # Detailed results
        f.write("## Detailed Results\n\n")
        
        for result in results:
            f.write(f"### {result['file']}\n\n")
            f.write(f"- Backup: `{result['backup']}`\n")
            f.write(f"- Imports replaced: {result['imports_replaced']}\n")
            f.write(f"- Patterns replaced: {result['patterns_replaced']}\n")
            
            if result["warnings"]:
                f.write("- Warnings:\n")
                for warning in result["warnings"]:
                    f.write(f"  - {warning}\n")
            
            if result["errors"]:
                f.write("- Errors:\n")
                for error in result["errors"]:
                    f.write(f"  - {error}\n")
            
            f.write("\n")
        
        # Next steps
        f.write("## Next Steps\n\n")
        f.write("1. Review the migration results above\n")
        f.write("2. Test the migrated code thoroughly\n")
        f.write("3. Review files with warnings for manual updates\n")
        f.write("4. Run the test suite to ensure everything works\n")
        f.write("5. Remove the compatibility layer once migration is complete\n")
        f.write("6. Delete old database service files\n\n")
        
        # RLS migration guide
        f.write("## RLS Migration Guide\n\n")
        f.write("The new consolidated service relies on Supabase Row Level Security (RLS) ")
        f.write("instead of custom security implementations. Here's how to migrate:\n\n")
        f.write("1. Enable RLS on your tables:\n")
        f.write("   ```sql\n")
        f.write("   ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;\n")
        f.write("   ```\n\n")
        f.write("2. Create policies for each operation:\n")
        f.write("   ```sql\n")
        f.write("   -- Example: Users can only see their own data\n")
        f.write("   CREATE POLICY \"Users see own data\" ON your_table\n")
        f.write("   FOR SELECT USING (auth.uid() = user_id);\n")
        f.write("   ```\n\n")
        f.write("3. Remove security checks from application code\n")
        f.write("4. Use service role key only for admin operations\n\n")
    
    print(f"Migration report generated at: {report_path}")


def main():
    """Main migration function."""
    print("Starting database service migration...")
    
    # Find project root
    project_root = Path.cwd()
    if not (project_root / "tripsage_core").exists():
        print("Error: Must run from project root directory")
        return
    
    # Generate compatibility layer first
    generate_compatibility_layer()
    
    # Find files to migrate
    files_to_migrate = find_files_with_imports(project_root / "tripsage_core")
    print(f"Found {len(files_to_migrate)} files to migrate")
    
    # Migrate each file
    results = []
    for file_path in files_to_migrate:
        print(f"Migrating: {file_path}")
        result = migrate_file(file_path)
        results.append(result)
        
        if result["errors"]:
            print(f"  ❌ Errors: {', '.join(result['errors'])}")
        else:
            print(f"  ✅ Success: {result['imports_replaced']} imports, "
                  f"{result['patterns_replaced']} patterns replaced")
    
    # Generate report
    generate_migration_report(results)
    
    print("\nMigration complete!")
    print("Please review the migration_report.md for details")
    print("Remember to:")
    print("1. Run tests to verify the migration")
    print("2. Review files with warnings")
    print("3. Set up RLS policies in Supabase")
    print("4. Remove old database service files once verified")


if __name__ == "__main__":
    main()