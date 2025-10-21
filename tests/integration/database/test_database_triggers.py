"""Integration tests for database triggers.

Tests business logic automation, event notifications, and scheduled jobs.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.services.infrastructure.database_service import DatabaseService


class TestCollaborationTriggers:
    """Test collaboration event triggers and notifications."""

    @pytest.fixture
    async def db_with_test_data(self, db_service: DatabaseService):
        """Set up test data for collaboration tests."""
        # Create test users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        owner_id = str(uuid4())

        # Create test trip
        trip_id = await db_service.execute_query(
            """
            INSERT INTO trips (user_id, name, destination, start_date, end_date, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            owner_id,
            "Test Trip",
            "Paris",
            "2025-07-01",
            "2025-07-10",
            "planning",
        )

        return {
            "trip_id": trip_id[0]["id"],
            "owner_id": owner_id,
            "user1_id": user1_id,
            "user2_id": user2_id,
        }

    async def test_collaboration_notification_trigger(
        self, db_with_test_data, db_service
    ):
        """Test that collaboration changes trigger notifications."""
        data = db_with_test_data

        # Mock pg_notify to capture notifications
        notifications = []

        async def mock_notify(channel, payload):
            notifications.append({"channel": channel, "payload": json.loads(payload)})

        with patch.object(db_service.pool, "acquire") as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.side_effect = mock_notify

            # Add collaborator
            await db_service.execute_query(
                """
                INSERT INTO trip_collaborators
                (trip_id, user_id, added_by, permission_level)
                VALUES ($1, $2, $3, $4)
                """,
                data["trip_id"],
                data["user1_id"],
                data["owner_id"],
                "view",
            )

            # Verify notification was sent
            assert len(notifications) > 0
            notification = notifications[0]
            assert notification["channel"] == "trip_collaboration"
            assert notification["payload"]["event_type"] == "collaborator_added"
            assert notification["payload"]["trip_id"] == data["trip_id"]
            assert notification["payload"]["user_id"] == data["user1_id"]
            assert notification["payload"]["permission_level"] == "view"

    async def test_collaboration_permission_validation(
        self, db_with_test_data, db_service
    ):
        """Test collaboration permission hierarchy validation."""
        data = db_with_test_data

        # Add user1 as admin collaborator
        await db_service.execute_query(
            """
            INSERT INTO trip_collaborators
            (trip_id, user_id, added_by, permission_level)
            VALUES ($1, $2, $3, $4)
            """,
            data["trip_id"],
            data["user1_id"],
            data["owner_id"],
            "admin",
        )

        # Test: Admin cannot grant admin permissions
        with pytest.raises(
            Exception, match="Only trip owners can grant admin permissions"
        ):
            await db_service.execute_query(
                """
                INSERT INTO trip_collaborators
                (trip_id, user_id, added_by, permission_level)
                VALUES ($1, $2, $3, $4)
                """,
                data["trip_id"],
                data["user2_id"],
                data["user1_id"],
                "admin",
            )

        # Test: Users cannot modify their own permissions
        with pytest.raises(Exception, match="Cannot modify your own permission level"):
            await db_service.execute_query(
                """
                UPDATE trip_collaborators
                SET permission_level = 'view'
                WHERE trip_id = $1 AND user_id = $2 AND added_by = $2
                """,
                data["trip_id"],
                data["user1_id"],
            )

    async def test_collaboration_audit_trail(self, db_with_test_data, db_service):
        """Test that collaboration changes are audited."""
        data = db_with_test_data

        # Add collaborator
        await db_service.execute_query(
            """
            INSERT INTO trip_collaborators
            (trip_id, user_id, added_by, permission_level)
            VALUES ($1, $2, $3, $4)
            """,
            data["trip_id"],
            data["user1_id"],
            data["owner_id"],
            "view",
        )

        # Update collaboration permission
        await db_service.execute_query(
            """
            UPDATE trip_collaborators
            SET permission_level = 'edit'
            WHERE trip_id = $1 AND user_id = $2
            """,
            data["trip_id"],
            data["user1_id"],
        )

        # Check audit trail
        audit_records = await db_service.fetch_query(
            """
            SELECT content, metadata
            FROM session_memories
            WHERE metadata->>'type' = 'collaboration_audit'
            AND metadata->'event_data'->>'trip_id' = $1
            ORDER BY created_at DESC
            """,
            str(data["trip_id"]),
        )

        assert len(audit_records) >= 1
        assert "Collaboration updated" in audit_records[0]["content"]
        assert audit_records[0]["metadata"]["operation"] == "UPDATE"


class TestCacheInvalidationTriggers:
    """Test cache invalidation triggers."""

    async def test_trip_cache_invalidation_notification(self, db_service):
        """Test that trip changes trigger cache invalidation notifications."""
        notifications = []

        async def mock_notify(channel, payload):
            notifications.append({"channel": channel, "payload": json.loads(payload)})

        # Create test trip
        trip_id = await db_service.execute_query(
            """
            INSERT INTO trips
            (user_id, name, destination, start_date, end_date, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            str(uuid4()),
            "Test Trip",
            "London",
            "2025-08-01",
            "2025-08-10",
            "planning",
        )

        with patch.object(db_service.pool, "acquire") as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.side_effect = mock_notify

            # Update trip
            await db_service.execute_query(
                """
                UPDATE trips
                SET destination = 'Edinburgh'
                WHERE id = $1
                """,
                trip_id[0]["id"],
            )

            # Verify cache invalidation notification
            assert any(
                n["channel"] == "cache_invalidation"
                and n["payload"]["table_name"] == "trips"
                and n["payload"]["record_id"] == str(trip_id[0]["id"])
                for n in notifications
            )

    async def test_search_cache_cleanup_on_data_change(self, db_service):
        """Test that search cache is cleaned up when related data changes."""
        # Create test trip
        trip_id = await db_service.execute_query(
            """
            INSERT INTO trips
            (user_id, name, destination, start_date, end_date, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            str(uuid4()),
            "Paris Trip",
            "Paris",
            "2025-09-01",
            "2025-09-10",
            "planning",
        )

        # Mock search cache entries
        await db_service.execute_query(
            """
            INSERT INTO search_destinations (query_hash, results, expires_at, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            "test_hash",
            '{"destinations": []}',
            datetime.now() + timedelta(hours=1),
            '{"destination": "Paris"}',
        )

        # Update trip destination (should trigger cache cleanup)
        await db_service.execute_query(
            """
            UPDATE trips
            SET destination = 'Rome'
            WHERE id = $1
            """,
            trip_id[0]["id"],
        )

        # Verify search cache was cleaned up
        remaining_cache = await db_service.fetch_query(
            """
            SELECT * FROM search_destinations
            WHERE metadata->>'destination' = 'Paris'
            """
        )

        assert len(remaining_cache) == 0


class TestBusinessLogicTriggers:
    """Test business logic automation triggers."""

    async def test_auto_expire_chat_sessions(self, db_service):
        """Test automatic expiration of inactive chat sessions."""
        # Create test session
        session_id = str(uuid4())
        user_id = str(uuid4())

        await db_service.execute_query(
            """
            INSERT INTO chat_sessions (id, user_id, updated_at)
            VALUES ($1, $2, $3)
            """,
            session_id,
            user_id,
            datetime.now() - timedelta(hours=25),
        )

        notifications = []

        async def mock_notify(channel, payload):
            if channel == "chat_session_expired":
                notifications.append(
                    {"channel": channel, "payload": json.loads(payload)}
                )

        with patch.object(db_service.pool, "acquire") as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.side_effect = mock_notify

            # Update session (should trigger expiration check)
            await db_service.execute_query(
                """
                UPDATE chat_sessions
                SET updated_at = NOW() - INTERVAL '25 hours'
                WHERE id = $1
                """,
                session_id,
            )

            # Verify session was expired
            session = await db_service.fetch_query(
                """
                SELECT ended_at FROM chat_sessions WHERE id = $1
                """,
                session_id,
            )

            assert session[0]["ended_at"] is not None
            assert len(notifications) > 0
            assert notifications[0]["payload"]["session_id"] == session_id

    async def test_trip_status_update_from_bookings(self, db_service):
        """Test automatic trip status updates based on booking confirmations."""
        # Create test trip
        trip_id = await db_service.execute_query(
            """
            INSERT INTO trips
            (user_id, name, destination, start_date, end_date, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            str(uuid4()),
            "Status Test Trip",
            "Berlin",
            "2025-10-01",
            "2025-10-10",
            "planning",
        )

        # Add confirmed flight booking
        await db_service.execute_query(
            """
            INSERT INTO flights
            (trip_id, origin, destination, departure_time, arrival_time, booking_status)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            trip_id[0]["id"],
            "NYC",
            "Berlin",
            datetime.now() + timedelta(days=30),
            datetime.now() + timedelta(days=30, hours=8),
            "confirmed",
        )

        # Add confirmed accommodation booking
        await db_service.execute_query(
            """
            INSERT INTO accommodations
            (trip_id, name, location, check_in_date, check_out_date, booking_status)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            trip_id[0]["id"],
            "Hotel Berlin",
            "Berlin",
            "2025-10-01",
            "2025-10-10",
            "confirmed",
        )

        # Verify trip status was updated to confirmed
        trip_status = await db_service.fetch_query(
            """
            SELECT status FROM trips WHERE id = $1
            """,
            trip_id[0]["id"],
        )

        assert trip_status[0]["status"] == "confirmed"

        # Cancel a booking and verify status change
        await db_service.execute_query(
            """
            UPDATE flights
            SET booking_status = 'cancelled'
            WHERE trip_id = $1
            """,
            trip_id[0]["id"],
        )

        trip_status = await db_service.fetch_query(
            """
            SELECT status FROM trips WHERE id = $1
            """,
            trip_id[0]["id"],
        )

        assert trip_status[0]["status"] == "needs_attention"

    async def test_orphaned_attachment_cleanup(self, db_service):
        """Test cleanup of orphaned file attachments."""
        # Create test message with attachments
        session_id = str(uuid4())
        message_id = await db_service.execute_query(
            """
            INSERT INTO chat_messages (session_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            session_id,
            "user",
            "Test message",
            '{"attachments": [{"id": "' + str(uuid4()) + '"}]}',
        )

        attachment_id = str(uuid4())
        await db_service.execute_query(
            """
            INSERT INTO file_attachments
            (id, filename, file_path, file_size, content_type)
            VALUES ($1, $2, $3, $4, $5)
            """,
            attachment_id,
            "test.pdf",
            "/tmp/test.pdf",
            1024,
            "application/pdf",
        )

        # Delete message (should trigger orphaned attachment marking)
        await db_service.execute_query(
            """
            DELETE FROM chat_messages WHERE id = $1
            """,
            message_id[0]["id"],
        )

        # Verify attachment was marked as orphaned
        attachment = await db_service.fetch_query(
            """
            SELECT metadata FROM file_attachments WHERE id = $1
            """,
            attachment_id,
        )

        assert attachment[0]["metadata"].get("orphaned")


class TestScheduledJobFunctions:
    """Test scheduled maintenance job functions."""

    async def test_daily_cleanup_job(self, db_service):
        """Test daily cleanup job functionality."""
        # Create old session memories
        old_memory_id = str(uuid4())
        await db_service.execute_query(
            """
            INSERT INTO session_memories (id, session_id, user_id, content, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            old_memory_id,
            str(uuid4()),
            str(uuid4()),
            "Old memory",
            datetime.now() - timedelta(days=8),
        )

        # Create orphaned attachment
        orphaned_attachment_id = str(uuid4())
        await db_service.execute_query(
            """
            INSERT INTO file_attachments
            (id, filename, file_path, file_size, content_type, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            orphaned_attachment_id,
            "old_file.pdf",
            "/tmp/old.pdf",
            1024,
            "application/pdf",
            '{"orphaned": true}',
            datetime.now() - timedelta(days=8),
        )

        # Run daily cleanup
        await db_service.execute_query("SELECT daily_cleanup_job()")

        # Verify old memory was cleaned up
        old_memories = await db_service.fetch_query(
            """
            SELECT * FROM session_memories WHERE id = $1
            """,
            old_memory_id,
        )
        assert len(old_memories) == 0

        # Verify orphaned attachment was deleted
        orphaned_files = await db_service.fetch_query(
            """
            SELECT * FROM file_attachments WHERE id = $1
            """,
            orphaned_attachment_id,
        )
        assert len(orphaned_files) == 0

    async def test_weekly_maintenance_job(self, db_service):
        """Test weekly maintenance job functionality."""
        # Run weekly maintenance
        await db_service.execute_query("SELECT weekly_maintenance_job()")

        # Verify maintenance log was created
        maintenance_logs = await db_service.fetch_query(
            """
            SELECT * FROM session_memories
            WHERE metadata->>'job' = 'weekly_maintenance'
            AND created_at > NOW() - INTERVAL '1 minute'
            """
        )

        assert len(maintenance_logs) >= 1
        assert "Weekly maintenance completed" in maintenance_logs[0]["content"]

    async def test_monthly_cleanup_job(self, db_service):
        """Test monthly deep cleanup job functionality."""
        # Create very old memories
        very_old_memory_id = str(uuid4())
        await db_service.execute_query(
            """
            INSERT INTO memories (id, user_id, content, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            very_old_memory_id,
            str(uuid4()),
            "Very old memory",
            "[" + ",".join(["0.1"] * 1536) + "]",
            datetime.now() - timedelta(days=400),
        )

        # Run monthly cleanup
        await db_service.execute_query("SELECT monthly_cleanup_job()")

        # Verify old memory was cleaned up
        old_memories = await db_service.fetch_query(
            """
            SELECT * FROM memories WHERE id = $1
            """,
            very_old_memory_id,
        )
        assert len(old_memories) == 0

        # Verify cleanup log was created
        cleanup_logs = await db_service.fetch_query(
            """
            SELECT * FROM session_memories
            WHERE metadata->>'job' = 'monthly_cleanup'
            AND created_at > NOW() - INTERVAL '1 minute'
            """
        )

        assert len(cleanup_logs) >= 1
        assert "Monthly deep cleanup completed" in cleanup_logs[0]["content"]


class TestTriggerPerformance:
    """Test trigger performance and overhead."""

    async def test_bulk_collaboration_operations(self, db_service):
        """Test trigger performance with bulk operations."""
        # Create test trip
        trip_id = await db_service.execute_query(
            """
            INSERT INTO trips
            (user_id, name, destination, start_date, end_date, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            str(uuid4()),
            "Bulk Test Trip",
            "Tokyo",
            "2025-11-01",
            "2025-11-10",
            "planning",
        )

        # Measure time for bulk collaboration inserts
        start_time = datetime.now()

        # Insert 100 collaborators
        user_ids = [str(uuid4()) for _ in range(100)]
        owner_id = str(uuid4())

        for user_id in user_ids:
            await db_service.execute_query(
                """
                INSERT INTO trip_collaborators
                (trip_id, user_id, added_by, permission_level)
                VALUES ($1, $2, $3, $4)
                """,
                trip_id[0]["id"],
                user_id,
                owner_id,
                "view",
            )

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 30.0  # 30 seconds for 100 operations

        # Verify all collaborators were added
        collaborator_count = await db_service.fetch_query(
            """
            SELECT COUNT(*) as count FROM trip_collaborators WHERE trip_id = $1
            """,
            trip_id[0]["id"],
        )

        assert collaborator_count[0]["count"] == 100

    async def test_cache_invalidation_overhead(self, db_service):
        """Test cache invalidation trigger overhead."""
        # Create multiple trips for bulk updates
        trip_ids = []
        for i in range(50):
            result = await db_service.execute_query(
                """
                INSERT INTO trips
                (user_id, name, destination, start_date, end_date, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                str(uuid4()),
                f"Trip {i}",
                f"Destination {i}",
                "2025-12-01",
                "2025-12-10",
                "planning",
            )
            trip_ids.append(result[0]["id"])

        # Measure bulk update performance
        start_time = datetime.now()

        for trip_id in trip_ids:
            await db_service.execute_query(
                """
                UPDATE trips SET destination = 'Updated Destination' WHERE id = $1
                """,
                trip_id,
            )

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time
        assert execution_time < 15.0  # 15 seconds for 50 updates

        # Verify all trips were updated
        updated_count = await db_service.fetch_query(
            """
            SELECT COUNT(*) as count FROM trips
            WHERE destination = 'Updated Destination'
            """
        )

        assert updated_count[0]["count"] >= 50
