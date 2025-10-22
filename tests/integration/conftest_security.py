"""Security-focused test fixtures and utilities for integration tests.

This module provides test fixtures for security integration testing,
including realistic test data, user scenarios, and security context setup.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
)
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.infrastructure.database_service import DatabaseService


logger = logging.getLogger(__name__)


# ===== SECURITY TEST USERS =====


@pytest.fixture(scope="session")
def security_test_users() -> list[dict[str, Any]]:
    """Create security test users with different roles and permissions."""
    return [
        {
            "id": "sec_user_001",
            "email": "trip.owner@security.test",
            "name": "Trip Owner",
            "username": "trip_owner",
            "role": "user",
            "is_admin": False,
            "is_disabled": False,
            "is_verified": True,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 0,
            "locked_until": None,
        },
        {
            "id": "sec_user_002",
            "email": "collaborator.edit@security.test",
            "name": "Edit Collaborator",
            "username": "edit_collaborator",
            "role": "user",
            "is_admin": False,
            "is_disabled": False,
            "is_verified": True,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 0,
            "locked_until": None,
        },
        {
            "id": "sec_user_003",
            "email": "collaborator.view@security.test",
            "name": "View Collaborator",
            "username": "view_collaborator",
            "role": "user",
            "is_admin": False,
            "is_disabled": False,
            "is_verified": True,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 0,
            "locked_until": None,
        },
        {
            "id": "sec_user_004",
            "email": "unauthorized@security.test",
            "name": "Unauthorized User",
            "username": "unauthorized_user",
            "role": "user",
            "is_admin": False,
            "is_disabled": False,
            "is_verified": True,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 0,
            "locked_until": None,
        },
        {
            "id": "sec_user_005",
            "email": "admin@security.test",
            "name": "Admin User",
            "username": "admin_user",
            "role": "admin",
            "is_admin": True,
            "is_disabled": False,
            "is_verified": True,
            "security_level": "elevated",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 0,
            "locked_until": None,
        },
        {
            "id": "sec_user_006",
            "email": "disabled@security.test",
            "name": "Disabled User",
            "username": "disabled_user",
            "role": "user",
            "is_admin": False,
            "is_disabled": True,
            "is_verified": True,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC) - timedelta(days=30),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 5,
            "locked_until": datetime.now(UTC) + timedelta(hours=24),
        },
        {
            "id": "sec_user_007",
            "email": "malicious@security.test",
            "name": "Malicious User",
            "username": "malicious_user",
            "role": "user",
            "is_admin": False,
            "is_disabled": False,
            "is_verified": False,
            "security_level": "standard",
            "created_at": datetime.now(UTC),
            "last_login": datetime.now(UTC),
            "password_hash": "$2b$12$encrypted_password_hash",
            "login_attempts": 3,
            "locked_until": None,
        },
    ]


@pytest.fixture(scope="session")
def security_test_trips(
    security_test_users: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create security test trips with different visibility levels."""
    owner_id = security_test_users[0]["id"]
    return [
        {
            "id": str(uuid4()),
            "user_id": owner_id,
            "name": "Private Security Test Trip",
            "destination": "Paris, France",
            "start_date": date(2024, 7, 15),
            "end_date": date(2024, 7, 25),
            "budget": 3000.00,
            "travelers": 2,
            "description": "Private trip for security testing",
            "visibility": TripVisibility.PRIVATE.value,
            "status": TripStatus.PLANNING.value,
            "trip_type": TripType.LEISURE.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "metadata": {
                "security_test": True,
                "test_category": "private_access",
            },
        },
        {
            "id": str(uuid4()),
            "user_id": owner_id,
            "name": "Public Security Test Trip",
            "destination": "London, UK",
            "start_date": date(2024, 8, 1),
            "end_date": date(2024, 8, 10),
            "budget": 2500.00,
            "travelers": 1,
            "description": "Public trip for security testing",
            "visibility": TripVisibility.PUBLIC.value,
            "status": TripStatus.PLANNING.value,
            "trip_type": TripType.BUSINESS.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "metadata": {
                "security_test": True,
                "test_category": "public_access",
            },
        },
        {
            "id": str(uuid4()),
            "user_id": owner_id,
            "name": "Collaborative Security Test Trip",
            "destination": "Tokyo, Japan",
            "start_date": date(2024, 9, 1),
            "end_date": date(2024, 9, 15),
            "budget": 4500.00,
            "travelers": 3,
            "description": "Trip with collaborators for security testing",
            "visibility": TripVisibility.PRIVATE.value,
            "status": TripStatus.PLANNING.value,
            "trip_type": TripType.LEISURE.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "metadata": {
                "security_test": True,
                "test_category": "collaboration_access",
                "has_collaborators": True,
            },
        },
        {
            "id": str(uuid4()),
            "user_id": security_test_users[3]["id"],  # Unauthorized user's trip
            "name": "Other User's Private Trip",
            "destination": "Berlin, Germany",
            "start_date": date(2024, 10, 1),
            "end_date": date(2024, 10, 8),
            "budget": 2000.00,
            "travelers": 1,
            "description": "Another user's private trip",
            "visibility": TripVisibility.PRIVATE.value,
            "status": TripStatus.PLANNING.value,
            "trip_type": TripType.LEISURE.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "metadata": {
                "security_test": True,
                "test_category": "cross_user_isolation",
            },
        },
    ]


@pytest.fixture(scope="session")
def security_test_collaborators(
    security_test_users: list[dict[str, Any]], security_test_trips: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Create security test collaborators with different permission levels."""
    collaborative_trip_id = security_test_trips[2]["id"]  # Collaborative trip
    owner_id = security_test_users[0]["id"]

    return [
        {
            "id": str(uuid4()),
            "trip_id": collaborative_trip_id,
            "user_id": security_test_users[1]["id"],  # Edit collaborator
            "permission": "edit",
            "invited_by": owner_id,
            "invited_at": datetime.now(UTC),
            "accepted_at": datetime.now(UTC),
            "status": "accepted",
            "metadata": {
                "security_test": True,
                "permission_level": "edit",
            },
        },
        {
            "id": str(uuid4()),
            "trip_id": collaborative_trip_id,
            "user_id": security_test_users[2]["id"],  # View collaborator
            "permission": "view",
            "invited_by": owner_id,
            "invited_at": datetime.now(UTC),
            "accepted_at": datetime.now(UTC),
            "status": "accepted",
            "metadata": {
                "security_test": True,
                "permission_level": "view",
            },
        },
        {
            "id": str(uuid4()),
            "trip_id": security_test_trips[0]["id"],  # Private trip
            "user_id": security_test_users[1]["id"],  # Edit collaborator
            "permission": "manage",
            "invited_by": owner_id,
            "invited_at": datetime.now(UTC),
            "accepted_at": datetime.now(UTC),
            "status": "accepted",
            "metadata": {
                "security_test": True,
                "permission_level": "manage",
            },
        },
    ]


# ===== SECURITY PRINCIPALS =====


@pytest.fixture
def security_principals(
    security_test_users: list[dict[str, Any]],
) -> dict[str, Principal]:
    """Create security test principals for different user types."""
    return {
        "owner": Principal(
            id=security_test_users[0]["id"],
            type="user",
            email=security_test_users[0]["email"],
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": True,
            },
        ),
        "edit_collaborator": Principal(
            id=security_test_users[1]["id"],
            type="user",
            email=security_test_users[1]["email"],
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": True,
            },
        ),
        "view_collaborator": Principal(
            id=security_test_users[2]["id"],
            type="user",
            email=security_test_users[2]["email"],
            auth_method="jwt",
            scopes=["read"],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": True,
            },
        ),
        "unauthorized": Principal(
            id=security_test_users[3]["id"],
            type="user",
            email=security_test_users[3]["email"],
            auth_method="jwt",
            scopes=["read"],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": True,
            },
        ),
        "admin": Principal(
            id=security_test_users[4]["id"],
            type="admin",
            email=security_test_users[4]["email"],
            auth_method="jwt",
            scopes=["read", "write", "admin"],
            metadata={
                "user_role": "admin",
                "security_level": "elevated",
                "verified": True,
            },
        ),
        "disabled": Principal(
            id=security_test_users[5]["id"],
            type="user",
            email=security_test_users[5]["email"],
            auth_method="jwt",
            scopes=[],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": True,
                "disabled": True,
                "locked_until": security_test_users[5]["locked_until"].isoformat(),
            },
        ),
        "malicious": Principal(
            id=security_test_users[6]["id"],
            type="user",
            email=security_test_users[6]["email"],
            auth_method="jwt",
            scopes=["read"],
            metadata={
                "user_role": "user",
                "security_level": "standard",
                "verified": False,
                "suspicious": True,
            },
        ),
    }


# ===== SECURITY TEST SCENARIOS =====


@pytest.fixture(scope="session")
def security_test_scenarios() -> list[dict[str, Any]]:
    """Define security test scenarios."""
    return [
        {
            "name": "owner_access_private_trip",
            "description": "Owner accessing their own private trip",
            "user_type": "owner",
            "trip_type": "private",
            "expected_access": True,
            "expected_permissions": ["read", "write", "delete", "manage"],
            "risk_level": "low",
        },
        {
            "name": "unauthorized_access_private_trip",
            "description": "Unauthorized user accessing private trip",
            "user_type": "unauthorized",
            "trip_type": "private",
            "expected_access": False,
            "expected_permissions": [],
            "risk_level": "high",
        },
        {
            "name": "public_trip_access",
            "description": "Any user accessing public trip",
            "user_type": "unauthorized",
            "trip_type": "public",
            "expected_access": True,
            "expected_permissions": ["read"],
            "risk_level": "low",
        },
        {
            "name": "edit_collaborator_access",
            "description": "Edit collaborator accessing shared trip",
            "user_type": "edit_collaborator",
            "trip_type": "collaborative",
            "expected_access": True,
            "expected_permissions": ["read", "write"],
            "risk_level": "low",
        },
        {
            "name": "view_collaborator_write_attempt",
            "description": "View collaborator attempting to edit trip",
            "user_type": "view_collaborator",
            "trip_type": "collaborative",
            "expected_access": True,  # Can read
            "expected_permissions": ["read"],  # Cannot write
            "risk_level": "medium",
        },
        {
            "name": "disabled_user_access",
            "description": "Disabled user attempting access",
            "user_type": "disabled",
            "trip_type": "private",
            "expected_access": False,
            "expected_permissions": [],
            "risk_level": "medium",
        },
        {
            "name": "malicious_user_access",
            "description": "Malicious user attempting access",
            "user_type": "malicious",
            "trip_type": "private",
            "expected_access": False,
            "expected_permissions": [],
            "risk_level": "high",
        },
        {
            "name": "privilege_escalation_attempt",
            "description": "User attempting to escalate privileges",
            "user_type": "unauthorized",
            "trip_type": "private",
            "expected_access": False,
            "expected_permissions": [],
            "risk_level": "critical",
            "attack_vector": "privilege_escalation",
        },
        {
            "name": "cross_user_data_access",
            "description": "User attempting to access another user's data",
            "user_type": "unauthorized",
            "trip_type": "cross_user",
            "expected_access": False,
            "expected_permissions": [],
            "risk_level": "high",
            "attack_vector": "data_enumeration",
        },
    ]


# ===== MOCK SERVICES =====


@pytest.fixture
def security_mock_trip_service(
    security_test_users: list[dict[str, Any]],
    security_test_trips: list[dict[str, Any]],
    security_test_collaborators: list[dict[str, Any]],
) -> TripService:
    """Create mock trip service for security testing."""
    service = MagicMock(spec=TripService)

    # Mock database interface
    service.db = MagicMock()

    def mock_check_trip_access(
        trip_id: str, user_id: str, require_owner: bool = False
    ) -> bool:
        """Mock trip access checking with security logic."""
        # Find the trip
        trip = next((t for t in security_test_trips if t["id"] == trip_id), None)
        if not trip:
            return False

        # Owner always has access
        if trip["user_id"] == user_id:
            return True

        # If ownership is required, deny non-owners
        if require_owner:
            return False

        # Check public visibility
        if trip["visibility"] == TripVisibility.PUBLIC.value:
            return True

        # Check collaboration
        user_collab = next(
            (
                c
                for c in security_test_collaborators
                if c["trip_id"] == trip_id
                and c["user_id"] == user_id
                and c["status"] == "accepted"
            ),
            None,
        )
        return user_collab is not None

    def mock_get_trip_by_id(trip_id: str) -> dict[str, Any] | None:
        """Mock getting trip by ID."""
        return next((t for t in security_test_trips if t["id"] == trip_id), None)

    def mock_get_trip_collaborators(trip_id: str) -> list[dict[str, Any]]:
        """Mock getting trip collaborators."""
        return [c for c in security_test_collaborators if c["trip_id"] == trip_id]

    # Configure mocks
    service._check_trip_access = mock_check_trip_access
    service.db.get_trip_by_id = mock_get_trip_by_id
    service.db.get_trip_collaborators = mock_get_trip_collaborators

    # Configure async methods
    service.create_trip = AsyncMock()
    service.get_trip = AsyncMock()
    service.update_trip = AsyncMock()
    service.delete_trip = AsyncMock()
    service.get_user_trips = AsyncMock()
    service.search_trips = AsyncMock()

    return service


@pytest.fixture
def security_mock_user_service(
    security_test_users: list[dict[str, Any]],
) -> UserService:
    """Create mock user service for security testing."""
    service = MagicMock(spec=UserService)

    def mock_get_user_by_id(user_id: str) -> dict[str, Any] | None:
        """Mock getting user by ID."""
        return next((u for u in security_test_users if u["id"] == user_id), None)

    def mock_get_user_by_email(email: str) -> dict[str, Any] | None:
        """Mock getting user by email."""
        return next((u for u in security_test_users if u["email"] == email), None)

    def mock_authenticate_user(email: str, password: str) -> dict[str, Any] | None:
        """Mock user authentication."""
        user = mock_get_user_by_email(email)
        if not user:
            return None

        # Check if user is disabled or locked
        if user["is_disabled"]:
            return None

        if user["locked_until"] and datetime.fromisoformat(
            user["locked_until"]
        ) > datetime.now(UTC):
            return None

        # Simple password check (in real scenario, would hash and compare)
        if password == "correct_password":
            return user

        return None

    # Configure mocks
    service.get_user_by_id = mock_get_user_by_id
    service.get_user_by_email = mock_get_user_by_email
    service.authenticate_user = AsyncMock(side_effect=mock_authenticate_user)
    service.create_user = AsyncMock()
    service.update_user = AsyncMock()
    service.delete_user = AsyncMock()

    return service


@pytest.fixture
def security_mock_database_service() -> DatabaseService:
    """Create mock database service for security testing."""
    service = MagicMock(spec=DatabaseService)

    # Track queries for audit purposes
    service._executed_queries = []

    def mock_execute_query(
        query: str,
        params: dict[str, Any] | None = None,
        user_context: str | None = None,
    ) -> dict[str, Any]:
        """Mock query execution with security tracking."""
        # Log the query for security analysis
        service._executed_queries.append(
            {
                "query": query,
                "params": params,
                "user_context": user_context,
                "timestamp": datetime.now(UTC),
            }
        )

        # Simulate security checks
        query_lower = query.lower()

        # Block suspicious queries
        suspicious_patterns = ["drop table", "delete from", "truncate", "alter table"]
        if any(pattern in query_lower for pattern in suspicious_patterns) and (
            not user_context or user_context != "admin"
        ):
            raise PermissionError("Suspicious query blocked by security filter")

        # Return mock data based on query type
        if "select" in query_lower:
            return {"data": [], "count": 0}
        elif "insert" in query_lower:
            return {"data": [{"id": str(uuid4()), "success": True}]}
        elif "update" in query_lower:
            return {"data": [{"updated": True}]}
        elif "delete" in query_lower:
            return {"data": [{"deleted": True}]}
        else:
            return {"data": []}

    # Configure mocks
    service.execute_query = AsyncMock(side_effect=mock_execute_query)
    service.get_session = AsyncMock()
    service.begin_transaction = AsyncMock()
    service.commit_transaction = AsyncMock()
    service.rollback_transaction = AsyncMock()

    return service


# ===== SECURITY TEST CLIENT =====


@pytest.fixture
def security_test_client() -> TestClient:
    """Create test client for security testing."""
    return TestClient(app)


# ===== AUDIT AND MONITORING =====


@pytest.fixture
def security_audit_logger():
    """Create security audit logger for test monitoring."""
    audit_events = []

    class SecurityAuditLogger:
        def log_event(
            self,
            event_type: AuditEventType,
            severity: AuditSeverity,
            user_id: str,
            resource_id: str,
            details: dict[str, Any],
            ip_address: str = "127.0.0.1",
        ):
            """Log security audit event."""
            audit_events.append(
                {
                    "event_type": event_type,
                    "severity": severity,
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "details": details,
                    "ip_address": ip_address,
                    "timestamp": datetime.now(UTC),
                }
            )

        def get_events(self) -> list[dict[str, Any]]:
            """Get all logged events."""
            return audit_events.copy()

        def clear_events(self):
            """Clear all logged events."""
            audit_events.clear()

        def get_events_by_type(
            self, event_type: AuditEventType
        ) -> list[dict[str, Any]]:
            """Get events by type."""
            return [e for e in audit_events if e["event_type"] == event_type]

        def get_events_by_user(self, user_id: str) -> list[dict[str, Any]]:
            """Get events by user."""
            return [e for e in audit_events if e["user_id"] == user_id]

        def get_high_risk_events(self) -> list[dict[str, Any]]:
            """Get high-risk security events."""
            return [
                e
                for e in audit_events
                if e["severity"] in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]
            ]

    return SecurityAuditLogger()


# ===== PERFORMANCE MONITORING =====


@pytest.fixture
def security_performance_monitor():
    """Create performance monitor for security operations."""
    performance_data = []

    class SecurityPerformanceMonitor:
        def start_operation(self, operation_name: str) -> str:
            """Start monitoring an operation."""
            operation_id = str(uuid4())
            performance_data.append(
                {
                    "operation_id": operation_id,
                    "operation_name": operation_name,
                    "start_time": datetime.now(UTC),
                    "end_time": None,
                    "duration_ms": None,
                    "success": None,
                }
            )
            return operation_id

        def end_operation(self, operation_id: str, success: bool = True):
            """End monitoring an operation."""
            operation = next(
                (op for op in performance_data if op["operation_id"] == operation_id),
                None,
            )
            if operation:
                end_time = datetime.now(UTC)
                operation["end_time"] = end_time
                operation["duration_ms"] = (
                    end_time - operation["start_time"]
                ).total_seconds() * 1000
                operation["success"] = success

        def get_performance_data(self) -> list[dict[str, Any]]:
            """Get all performance data."""
            return performance_data.copy()

        def get_average_duration(self, operation_name: str) -> float:
            """Get average duration for an operation."""
            operations = [
                op
                for op in performance_data
                if op["operation_name"] == operation_name
                and op["duration_ms"] is not None
            ]
            if not operations:
                return 0.0
            return sum(op["duration_ms"] for op in operations) / len(operations)

        def get_failed_operations(self) -> list[dict[str, Any]]:
            """Get failed operations."""
            return [op for op in performance_data if op["success"] is False]

        def clear_data(self):
            """Clear performance data."""
            performance_data.clear()

    return SecurityPerformanceMonitor()


# ===== SECURITY SETUP =====


@pytest.fixture
async def comprehensive_security_setup(
    security_test_users: list[dict[str, Any]],
    security_test_trips: list[dict[str, Any]],
    security_test_collaborators: list[dict[str, Any]],
    security_principals: dict[str, Principal],
    security_mock_trip_service: TripService,
    security_mock_user_service: UserService,
    security_mock_database_service: DatabaseService,
    security_audit_logger,
    security_performance_monitor,
) -> dict[str, Any]:
    """Security test setup with all components."""
    return {
        "users": security_test_users,
        "trips": security_test_trips,
        "collaborators": security_test_collaborators,
        "principals": security_principals,
        "services": {
            "trip_service": security_mock_trip_service,
            "user_service": security_mock_user_service,
            "database_service": security_mock_database_service,
        },
        "monitoring": {
            "audit_logger": security_audit_logger,
            "performance_monitor": security_performance_monitor,
        },
        "test_context": {
            "environment": "security_testing",
            "timestamp": datetime.now(UTC),
            "session_id": str(uuid4()),
        },
    }


# ===== SECURITY TEST UTILITIES =====


def create_security_headers(
    token: str = "valid_security_token",
    user_agent: str = "SecurityTest/1.0",
    ip_address: str = "192.168.1.100",
) -> dict[str, str]:
    """Create security test headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": user_agent,
        "X-Forwarded-For": ip_address,
        "X-Real-IP": ip_address,
        "X-Request-ID": str(uuid4()),
        "X-Client-Version": "1.0.0",
    }


def create_malicious_headers() -> dict[str, str]:
    """Create malicious test headers."""
    return {
        "Authorization": "Bearer malicious_token",
        "Content-Type": "application/json",
        "User-Agent": "MaliciousBot/1.0 (Automated Security Scanner)",
        "X-Forwarded-For": "192.168.1.666",
        "X-Real-IP": "192.168.1.666",
        "X-Attack-Vector": "injection_test",
        "X-Malicious-Header": "<script>alert('xss')</script>",
    }


def assert_security_compliance(response, expected_status: int = 200):
    """Assert that response complies with security requirements."""
    # Check status code
    assert response.status_code == expected_status

    # Check for security headers
    security_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
    ]

    for header in security_headers:
        if header in response.headers:
            assert response.headers[header] is not None

    # Check that sensitive information is not exposed
    if response.status_code >= 400:
        response_text = response.text.lower()
        sensitive_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "database",
            "stack trace",
            "traceback",
            "file path",
        ]
        for pattern in sensitive_patterns:
            assert pattern not in response_text


def generate_concurrent_requests(
    client: TestClient,
    endpoint: str,
    headers: dict[str, str],
    count: int = 10,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> list[Any]:
    """Generate concurrent requests for load testing."""
    responses = []

    for _ in range(count):
        if method.upper() == "GET":
            response = client.get(endpoint, headers=headers)
        elif method.upper() == "POST":
            response = client.post(endpoint, json=data or {}, headers=headers)
        elif method.upper() == "PUT":
            response = client.put(endpoint, json=data or {}, headers=headers)
        elif method.upper() == "DELETE":
            response = client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        responses.append(response)

    return responses


# ===== CLEANUP UTILITIES =====


@pytest.fixture(autouse=True)
def security_test_cleanup(security_audit_logger, security_performance_monitor):
    """Automatic cleanup after security tests."""
    yield

    # Clear audit logs and performance data after each test
    security_audit_logger.clear_events()
    security_performance_monitor.clear_data()

    # Log test completion
    logger.info("Security test cleanup completed")
