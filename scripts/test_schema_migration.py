#!/usr/bin/env python3
"""
Test script for Supabase schema migration (BJO-121)

This script validates the schema changes for foreign key constraints 
and UUID references without actually running the migration.

Usage: python scripts/test_schema_migration.py
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from tripsage_core.models.db.memory import Memory, SessionMemory, MemoryCreate
    from tripsage_core.models.db.api_key import ApiKeyDB, ApiKeyCreate
    from tripsage_core.models.db.chat import ChatSessionDB
    from datetime import datetime, timezone
    from uuid import UUID
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def test_memory_models():
    """Test memory models with UUID user_id fields."""
    print("\n🧠 Testing Memory Models...")
    
    try:
        # Test Memory model with UUID user_id
        test_uuid = uuid4()
        memory = Memory(
            id=uuid4(),
            user_id=test_uuid,
            memory="User prefers window seats",
            embedding=[0.1] * 1536,
            metadata={"preference": "seating"},
            categories=["travel"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert isinstance(memory.user_id, UUID), f"user_id should be UUID, got {type(memory.user_id)}"
        print("✅ Memory model validation passed")
        
        # Test SessionMemory model with UUID user_id
        session_memory = SessionMemory(
            id=uuid4(),
            session_id=uuid4(),
            user_id=test_uuid,
            message_index=1,
            role="user",
            content="I want to book a flight",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )
        assert isinstance(session_memory.user_id, UUID), f"user_id should be UUID, got {type(session_memory.user_id)}"
        print("✅ SessionMemory model validation passed")
        
        # Test MemoryCreate model
        memory_create = MemoryCreate(
            user_id=test_uuid,
            memory="User likes aisle seats",
            categories=["preferences"]
        )
        assert isinstance(memory_create.user_id, UUID), f"user_id should be UUID, got {type(memory_create.user_id)}"
        print("✅ MemoryCreate model validation passed")
        
    except Exception as e:
        print(f"❌ Memory model test failed: {e}")
        return False
    
    return True


def test_api_key_models():
    """Test API key models with UUID user_id fields."""
    print("\n🔑 Testing API Key Models...")
    
    try:
        # Test ApiKeyDB model with UUID user_id
        test_uuid = uuid4()
        api_key = ApiKeyDB(
            id=uuid4(),
            user_id=test_uuid,
            name="Test API Key",
            service="openai",
            encrypted_key="encrypted_test_key",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert isinstance(api_key.user_id, UUID), f"user_id should be UUID, got {type(api_key.user_id)}"
        print("✅ ApiKeyDB model validation passed")
        
        # Test ApiKeyCreate model
        api_key_create = ApiKeyCreate(
            user_id=test_uuid,
            name="Create Test Key",
            service="anthropic",
            encrypted_key="encrypted_create_key"
        )
        assert isinstance(api_key_create.user_id, UUID), f"user_id should be UUID, got {type(api_key_create.user_id)}"
        print("✅ ApiKeyCreate model validation passed")
        
    except Exception as e:
        print(f"❌ API Key model test failed: {e}")
        return False
    
    return True


def test_chat_models():
    """Test chat models with UUID user_id fields."""
    print("\n💬 Testing Chat Models...")
    
    try:
        # Test ChatSessionDB model with UUID user_id
        test_uuid = uuid4()
        chat_session = ChatSessionDB(
            id=uuid4(),
            user_id=test_uuid,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert isinstance(chat_session.user_id, UUID), f"user_id should be UUID, got {type(chat_session.user_id)}"
        print("✅ ChatSessionDB model validation passed")
        
    except Exception as e:
        print(f"❌ Chat model test failed: {e}")
        return False
    
    return True


def test_uuid_validation():
    """Test that models properly validate UUID formats."""
    print("\n🔍 Testing UUID Validation...")
    
    try:
        # Test invalid UUID strings should be rejected
        test_cases = [
            "invalid_uuid",
            "123",
            "",
            "not-a-uuid-at-all"
        ]
        
        for invalid_uuid in test_cases:
            try:
                # This should fail validation
                Memory(
                    id=uuid4(),
                    user_id=invalid_uuid,  # This should cause validation error
                    memory="Test memory",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                print(f"❌ Should have rejected invalid UUID: {invalid_uuid}")
                return False
            except Exception:
                # Expected to fail - this is good
                pass
        
        print("✅ UUID validation correctly rejects invalid formats")
        
        # Test valid UUID should be accepted
        valid_uuid = uuid4()
        memory = Memory(
            id=uuid4(),
            user_id=valid_uuid,
            memory="Test memory",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert memory.user_id == valid_uuid
        print("✅ UUID validation correctly accepts valid UUIDs")
        
    except Exception as e:
        print(f"❌ UUID validation test failed: {e}")
        return False
    
    return True


def validate_migration_sql():
    """Validate the migration SQL file exists and has expected content."""
    print("\n📄 Validating Migration SQL...")
    
    migration_file = project_root / "supabase" / "migrations" / "20250610_01_fix_user_id_constraints.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        content = migration_file.read_text()
        
        # Check for key migration components
        expected_components = [
            "ALTER TABLE memories",
            "ALTER COLUMN user_id TYPE UUID",
            "FOREIGN KEY (user_id) REFERENCES auth.users(id)",
            "ALTER TABLE session_memories",
            "ENABLE ROW LEVEL SECURITY",
            "CREATE POLICY",
            "Users can only access their own memories",
            "Users can only access their own session memories"
        ]
        
        missing_components = []
        for component in expected_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Migration file missing components: {missing_components}")
            return False
        
        print("✅ Migration SQL file contains all expected components")
        print(f"✅ Migration file size: {len(content)} characters")
        
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False
    
    return True


def main():
    """Run all schema migration tests."""
    print("🚀 Running Schema Migration Tests for BJO-121")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Run all test functions
    test_functions = [
        validate_migration_sql,
        test_memory_models,
        test_api_key_models,
        test_chat_models,
        test_uuid_validation,
    ]
    
    for test_func in test_functions:
        if not test_func():
            all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All schema migration tests PASSED!")
        print("\n✅ Ready to apply migration:")
        print("   1. Database foreign key constraints will be added")
        print("   2. Python models are updated for UUID consistency")
        print("   3. RLS policies will be enabled for security")
        print("   4. Data integrity will be maintained")
        sys.exit(0)
    else:
        print("❌ Some tests FAILED! Please fix issues before applying migration.")
        sys.exit(1)


if __name__ == "__main__":
    main()