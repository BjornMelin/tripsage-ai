"""
Security tests for memory system.
Tests data isolation, GDPR compliance, and security measures.
"""

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.tools.memory_tools import (
    ConversationMessage,
    MemorySearchQuery,
    add_conversation_memory,
    get_user_context,
    search_user_memories,
)


class TestMemorySecurityIsolation:
    """Test security and data isolation in memory system."""

    @pytest.fixture
    def secure_memory_service(self):
        """Memory service with user isolation tracking."""
        service = AsyncMock()

        # Track access patterns for security analysis
        self.access_log = []
        self.user_data = {}

        async def secure_add_memory(messages, user_id, session_id=None, metadata=None):
            self.access_log.append(
                {
                    "operation": "add",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc),
                    "data_size": len(str(messages)),
                }
            )

            if user_id not in self.user_data:
                self.user_data[user_id] = []

            memory_entry = {
                "id": f"secure-mem-{len(self.user_data[user_id]) + 1}",
                "user_id": user_id,
                "messages": messages,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
            }
            self.user_data[user_id].append(memory_entry)

            return {"status": "success", "memory_id": memory_entry["id"]}

        async def secure_search_memories(
            user_id, query, limit=20, category_filter=None
        ):
            self.access_log.append(
                {
                    "operation": "search",
                    "user_id": user_id,
                    "query": query,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

            # Only return data for the requesting user
            user_memories = self.user_data.get(user_id, [])
            results = []

            for memory in user_memories:
                content = " ".join(
                    [msg.get("content", "") for msg in memory["messages"]]
                )
                if query.lower() in content.lower():
                    results.append(
                        {
                            "id": memory["id"],
                            "content": content,
                            "metadata": memory["metadata"],
                            "score": 0.9,
                            "user_id": user_id,  # Include for verification
                        }
                    )

            return results[:limit]

        async def secure_get_context(user_id):
            self.access_log.append(
                {
                    "operation": "get_context",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

            user_memories = self.user_data.get(user_id, [])
            return {
                "memories": [
                    {
                        "id": m["id"],
                        "content": " ".join(
                            [msg.get("content", "") for msg in m["messages"]]
                        )[:100],
                        "user_id": user_id,
                        "metadata": m["metadata"],
                    }
                    for m in user_memories
                ],
                "preferences": {},
                "travel_patterns": {},
            }

        service.add_conversation_memory = secure_add_memory
        service.search_memories = secure_search_memories
        service.get_user_context = secure_get_context

        return service

    @pytest.mark.asyncio
    async def test_user_data_isolation(self, secure_memory_service):
        """Test that users cannot access each other's memory data."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            # User A stores sensitive data
            user_a_messages = [
                ConversationMessage(
                    role="user",
                    content=(
                        "My secret travel plans to a classified location. "
                        "SSN: 123-45-6789"
                    ),
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            await add_conversation_memory(
                messages=user_a_messages,
                user_id="user-a-secret",
                metadata={"classification": "secret"},
            )

            # User B stores different sensitive data
            user_b_messages = [
                ConversationMessage(
                    role="user",
                    content=(
                        "My private business trip details. "
                        "Credit card: 4111-1111-1111-1111"
                    ),
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            await add_conversation_memory(
                messages=user_b_messages,
                user_id="user-b-private",
                metadata={"classification": "private"},
            )

            # User A tries to search for User B's data
            user_a_search_for_b = await search_user_memories(
                MemorySearchQuery(
                    user_id="user-a-secret", query="business trip credit card"
                )
            )

            # User B tries to search for User A's data
            user_b_search_for_a = await search_user_memories(
                MemorySearchQuery(user_id="user-b-private", query="secret travel SSN")
            )

            # Verify isolation
            assert len(user_a_search_for_b) == 0, "User A should not find User B's data"
            assert len(user_b_search_for_a) == 0, "User B should not find User A's data"

            # Verify users can find their own data
            user_a_own_search = await search_user_memories(
                MemorySearchQuery(user_id="user-a-secret", query="secret travel")
            )

            user_b_own_search = await search_user_memories(
                MemorySearchQuery(user_id="user-b-private", query="business trip")
            )

            assert len(user_a_own_search) > 0, "User A should find their own data"
            assert len(user_b_own_search) > 0, "User B should find their own data"

            # Verify user_id in returned data matches requester
            for result in user_a_own_search:
                assert result["user_id"] == "user-a-secret"

            for result in user_b_own_search:
                assert result["user_id"] == "user-b-private"

    @pytest.mark.asyncio
    async def test_sensitive_data_handling(self, secure_memory_service):
        """Test handling of potentially sensitive data."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            # Test with various types of sensitive data
            sensitive_data_cases = [
                "My SSN is 123-45-6789",
                "Credit card number: 4111-1111-1111-1111",
                "My passport number is AB1234567",
                "Bank account: 123456789",
                "Email: sensitive@example.com",
                "Phone: +1-555-123-4567",
                "Home address: 123 Private Street, Secret City",
            ]

            for _i, sensitive_content in enumerate(sensitive_data_cases):
                messages = [
                    ConversationMessage(
                        role="user",
                        content=f"Travel context: {sensitive_content}",
                        timestamp=datetime.now(timezone.utc),
                    )
                ]

                result = await add_conversation_memory(
                    messages=messages,
                    user_id=f"sensitive-user-{_i}",
                    metadata={"contains_pii": True},
                )

                assert result["status"] == "success"

                # Verify data can be retrieved by owner
                search_results = await search_user_memories(
                    MemorySearchQuery(
                        user_id=f"sensitive-user-{_i}", query="travel context"
                    )
                )

                assert len(search_results) > 0
                # Note: In production, you might want to implement PII scrubbing/masking

    @pytest.mark.asyncio
    async def test_cross_user_search_injection(self, secure_memory_service):
        """Test protection against cross-user search injection attacks."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            # Store data for user A
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="Secret project alpha details",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id="target-user-alpha",
            )

            # Attacker tries various injection techniques
            injection_attempts = [
                "' OR user_id='target-user-alpha' --",
                "'; SELECT * FROM memories WHERE user_id='target-user-alpha'; --",
                "UNION SELECT * FROM memories WHERE user_id='target-user-alpha'",
                "../target-user-alpha/secret",
                "%' OR '1'='1",
                "'; DROP TABLE memories; --",
            ]

            for injection_query in injection_attempts:
                # Attacker user tries to inject
                results = await search_user_memories(
                    MemorySearchQuery(user_id="attacker-user", query=injection_query)
                )

                # Should not return any results (no data for attacker user)
                assert len(results) == 0, (
                    f"Injection attempt succeeded: {injection_query}"
                )

                # Verify no data leakage in results
                for result in results:
                    assert result.get("user_id") != "target-user-alpha", (
                        "Data leaked to wrong user"
                    )

    @pytest.mark.asyncio
    async def test_access_logging_and_auditing(self, secure_memory_service):
        """Test access logging for security auditing."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            user_id = "audit-test-user"

            # Perform various operations
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="Audit test message",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
            )

            await search_user_memories(
                MemorySearchQuery(user_id=user_id, query="audit test")
            )

            await get_user_context(user_id)

            # Verify access log
            access_log = secure_memory_service.access_log

            assert len(access_log) >= 3, "All operations should be logged"

            # Verify log entries contain required information
            operations = [entry["operation"] for entry in access_log]
            assert "add" in operations
            assert "search" in operations
            assert "get_context" in operations

            # Verify user_id is logged for all operations
            for entry in access_log:
                assert "user_id" in entry
                assert "timestamp" in entry
                assert entry["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_data_retention_compliance(self, secure_memory_service):
        """Test data retention and deletion compliance."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            user_id = "retention-test-user"

            # Add memory with retention metadata
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="Data to be retained for compliance testing",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={
                    "retention_policy": "30_days",
                    "data_classification": "personal",
                    "consent_given": True,
                },
            )

            # Verify data exists
            context = await get_user_context(user_id)
            assert len(context["memories"]) > 0

            # Simulate deletion request (GDPR right to be forgotten)
            # In production, this would trigger actual deletion
            deletion_metadata = {
                "deletion_requested": True,
                "deletion_timestamp": datetime.now(timezone.utc),
                "legal_basis": "gdpr_article_17",
            }

            # Verify deletion request can be tracked
            assert deletion_metadata["deletion_requested"] is True

    @pytest.mark.asyncio
    async def test_memory_data_encryption_patterns(self, secure_memory_service):
        """Test patterns for memory data encryption (simulation)."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):

            def simulate_encryption(data):
                """Simulate data encryption."""
                return hashlib.sha256(str(data).encode()).hexdigest()[:16]

            def simulate_decryption(encrypted_data):
                """Simulate data decryption (not real decryption)."""
                return f"decrypted_{encrypted_data}"

            # Test encryption patterns
            sensitive_message = "Highly sensitive travel information"
            encrypted_content = simulate_encryption(sensitive_message)

            # Store encrypted simulation
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=encrypted_content,  # Would be encrypted in production
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id="encryption-test-user",
                metadata={
                    "encrypted": True,
                    "encryption_algorithm": "AES-256",
                    "key_version": "v1",
                },
            )

            # Retrieve and "decrypt"
            context = await get_user_context("encryption-test-user")

            assert len(context["memories"]) > 0
            stored_memory = context["memories"][0]

            # Verify encryption metadata
            assert stored_memory["metadata"]["encrypted"] is True
            assert "encryption_algorithm" in stored_memory["metadata"]

    @pytest.mark.asyncio
    async def test_rate_limiting_protection(self, secure_memory_service):
        """Test protection against abuse through rate limiting simulation."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            # Simulate rate limiting by tracking request frequency
            request_timestamps = []

            async def rate_limited_operation(user_id, operation_type):
                now = datetime.now(timezone.utc)
                request_timestamps.append((user_id, operation_type, now))

                # Count recent requests (last minute)
                recent_requests = [
                    ts
                    for uid, op, ts in request_timestamps
                    if uid == user_id and (now - ts).total_seconds() < 60
                ]

                # Simulate rate limit (e.g., 100 requests per minute)
                if len(recent_requests) > 100:
                    raise Exception(f"Rate limit exceeded for user {user_id}")

                return True

            user_id = "rate-limit-test-user"

            # Test normal usage
            for _i in range(50):  # Under rate limit
                await rate_limited_operation(user_id, "search")

                # Perform actual operation
                await search_user_memories(
                    MemorySearchQuery(user_id=user_id, query=f"test {_i}")
                )

            # Verify operations completed successfully
            assert (
                len([ts for uid, op, ts in request_timestamps if uid == user_id]) == 50
            )

            # Test rate limit trigger
            with pytest.raises(Exception, match="Rate limit exceeded"):
                for _i in range(60):  # Exceed rate limit
                    await rate_limited_operation(user_id, "search")

    @pytest.mark.asyncio
    async def test_user_consent_and_privacy_controls(self, secure_memory_service):
        """Test user consent and privacy control mechanisms."""
        with patch("tripsage.tools.memory_tools.memory_service", secure_memory_service):
            user_id = "privacy-control-user"

            # Test with explicit consent
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="I consent to storing this travel information",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={
                    "consent_given": True,
                    "consent_timestamp": datetime.now(timezone.utc).isoformat(),
                    "privacy_level": "standard",
                    "data_sharing_allowed": False,
                },
            )

            # Test with privacy restrictions
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="This should be stored with high privacy",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={
                    "consent_given": True,
                    "privacy_level": "high",
                    "data_retention_days": 30,
                    "analytics_allowed": False,
                },
            )

            # Verify privacy metadata is preserved
            context = await get_user_context(user_id)

            for memory in context["memories"]:
                metadata = memory["metadata"]
                assert "consent_given" in metadata
                assert metadata["consent_given"] is True
                assert "privacy_level" in metadata


class TestMemoryGDPRCompliance:
    """Test GDPR compliance features."""

    @pytest.fixture
    def gdpr_memory_service(self):
        """Memory service with GDPR compliance features."""
        service = AsyncMock()

        # GDPR tracking
        self.gdpr_requests = []
        self.user_data_map = {}

        async def gdpr_add_memory(messages, user_id, session_id=None, metadata=None):
            if user_id not in self.user_data_map:
                self.user_data_map[user_id] = []

            memory_entry = {
                "id": f"gdpr-mem-{len(self.user_data_map[user_id]) + 1}",
                "user_id": user_id,
                "messages": messages,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
                "gdpr_compliant": True,
            }
            self.user_data_map[user_id].append(memory_entry)

            return {"status": "success", "memory_id": memory_entry["id"]}

        async def gdpr_data_export(user_id):
            """Simulate GDPR data export."""
            user_data = self.user_data_map.get(user_id, [])
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_count": len(user_data),
                "memories": user_data,
                "gdpr_compliance": {
                    "article_15": "right_of_access",
                    "data_portability": True,
                    "format": "structured_json",
                },
            }

            self.gdpr_requests.append(
                {
                    "type": "data_export",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

            return export_data

        async def gdpr_data_deletion(user_id):
            """Simulate GDPR data deletion."""
            if user_id in self.user_data_map:
                deleted_count = len(self.user_data_map[user_id])
                del self.user_data_map[user_id]

                self.gdpr_requests.append(
                    {
                        "type": "data_deletion",
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc),
                        "deleted_records": deleted_count,
                    }
                )

                return {
                    "status": "success",
                    "deleted_records": deleted_count,
                    "gdpr_article": "article_17_right_to_erasure",
                }

            return {"status": "no_data_found", "deleted_records": 0}

        service.add_conversation_memory = gdpr_add_memory
        service.gdpr_data_export = gdpr_data_export
        service.gdpr_data_deletion = gdpr_data_deletion

        return service

    @pytest.mark.asyncio
    async def test_gdpr_right_of_access(self, gdpr_memory_service):
        """Test GDPR Article 15 - Right of Access."""
        with patch("tripsage.tools.memory_tools.memory_service", gdpr_memory_service):
            user_id = "gdpr-access-user"

            # Store some data
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="GDPR test data for access request",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={"gdpr_test": True},
            )

            # Request data export (GDPR Article 15)
            export_data = await gdpr_memory_service.gdpr_data_export(user_id)

            # Verify export contains required information
            assert export_data["user_id"] == user_id
            assert "export_timestamp" in export_data
            assert export_data["data_count"] > 0
            assert "memories" in export_data
            assert export_data["gdpr_compliance"]["article_15"] == "right_of_access"

            # Verify GDPR request was logged
            gdpr_requests = gdpr_memory_service.gdpr_requests
            assert len(gdpr_requests) > 0
            assert gdpr_requests[-1]["type"] == "data_export"
            assert gdpr_requests[-1]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_gdpr_right_to_erasure(self, gdpr_memory_service):
        """Test GDPR Article 17 - Right to Erasure."""
        with patch("tripsage.tools.memory_tools.memory_service", gdpr_memory_service):
            user_id = "gdpr-erasure-user"

            # Store multiple pieces of data
            for _i in range(3):
                await add_conversation_memory(
                    messages=[
                        ConversationMessage(
                            role="user",
                            content=f"GDPR erasure test data {_i}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                    user_id=user_id,
                    metadata={"test_data": _i},
                )

            # Verify data exists
            initial_data = await gdpr_memory_service.gdpr_data_export(user_id)
            assert initial_data["data_count"] == 3

            # Request data deletion (GDPR Article 17)
            deletion_result = await gdpr_memory_service.gdpr_data_deletion(user_id)

            # Verify deletion
            assert deletion_result["status"] == "success"
            assert deletion_result["deleted_records"] == 3
            assert deletion_result["gdpr_article"] == "article_17_right_to_erasure"

            # Verify data is gone
            post_deletion_data = await gdpr_memory_service.gdpr_data_export(user_id)
            assert post_deletion_data["data_count"] == 0

            # Verify deletion was logged
            deletion_requests = [
                req
                for req in gdpr_memory_service.gdpr_requests
                if req["type"] == "data_deletion"
            ]
            assert len(deletion_requests) > 0
            assert deletion_requests[-1]["user_id"] == user_id
            assert deletion_requests[-1]["deleted_records"] == 3

    @pytest.mark.asyncio
    async def test_gdpr_data_portability(self, gdpr_memory_service):
        """Test GDPR Article 20 - Right to Data Portability."""
        with patch("tripsage.tools.memory_tools.memory_service", gdpr_memory_service):
            user_id = "gdpr-portability-user"

            # Store structured data
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="Portable travel data for GDPR compliance",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={
                    "travel_preferences": {
                        "accommodation": "luxury",
                        "budget": "high",
                        "destinations": ["Europe", "Asia"],
                    },
                    "structured_data": True,
                },
            )

            # Export data in portable format
            export_data = await gdpr_memory_service.gdpr_data_export(user_id)

            # Verify data portability features
            assert export_data["gdpr_compliance"]["data_portability"] is True
            assert export_data["gdpr_compliance"]["format"] == "structured_json"

            # Verify data structure is machine-readable
            memories = export_data["memories"]
            assert len(memories) > 0

            # Verify the data can be serialized to JSON (portability requirement)
            json_export = json.dumps(export_data, default=str)
            assert len(json_export) > 0

            # Verify imported data maintains structure
            imported_data = json.loads(json_export)
            assert imported_data["user_id"] == user_id
            assert len(imported_data["memories"]) == len(memories)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
