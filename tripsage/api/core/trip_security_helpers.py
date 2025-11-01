"""Helper functions for trip access verification.

This module contains helper functions extracted from verify_trip_access to
reduce complexity and improve maintainability.
"""

from collections.abc import Callable
from typing import Any

from tripsage.api.core.trip_security import (
    TripAccessContext,
    TripAccessLevel,
    TripAccessPermission,
)
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
)


async def check_access_level_requirement(
    context: TripAccessContext,
    granted_level: TripAccessLevel,
    granted_permission: TripAccessPermission | None,
    is_owner: bool,
    is_collaborator: bool,
    *,
    audit_security_event: Callable[..., Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Check if granted access level meets required level.

    Args:
        context: Trip access context
        granted_level: The granted access level
        granted_permission: The granted permission
        is_owner: Whether user is owner
        is_collaborator: Whether user is collaborator
        audit_security_event: Function to audit security events

    Returns:
        Tuple of (is_authorized, denial_result_dict)
    """
    if not context.required_level:
        return True, None

    level_hierarchy: dict[TripAccessLevel, int] = {
        TripAccessLevel.READ: 1,
        TripAccessLevel.COLLABORATOR: 2,
        TripAccessLevel.OWNER: 3,
    }

    required_level_value = level_hierarchy.get(context.required_level, 3)
    granted_level_value = level_hierarchy.get(granted_level, 0)

    if granted_level_value < required_level_value:
        await audit_security_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.MEDIUM,
            message=(
                f"Insufficient access level for operation: "
                f"{context.operation}. Required: "
                f"{context.required_level.value}, "
                f"Granted: {granted_level.value}"
            ),
            actor_id=context.principal_id,
            ip_address=context.ip_address or "unknown",
            target_resource=context.trip_id,
            risk_score=45,
            user_agent=context.user_agent,
            operation_type=context.operation,
            required_level=context.required_level.value,
            granted_level=granted_level.value,
        )

        return False, {
            "is_authorized": False,
            "access_level": granted_level,
            "permission_granted": granted_permission,
            "is_owner": is_owner,
            "is_collaborator": is_collaborator,
            "trip_visibility": None,
            "denial_reason": (
                f"Operation requires {context.required_level.value} "
                f"access level, but user has {granted_level.value}"
            ),
        }

    return True, None
