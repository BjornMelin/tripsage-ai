# Trip Security Usage Examples

This document demonstrates how to use the new trip access verification system in TripSage API endpoints.

## Overview

The trip security system provides access control for trip-related operations through:

- **Access Levels**: `READ`, `WRITE`, `OWNER`, `COLLABORATOR`
- **Permissions**: `VIEW`, `EDIT`, `MANAGE`
- **FastAPI Dependencies**: Pre-configured and custom dependency injection
- **Decorators**: Clean, declarative endpoint protection
- **Audit Logging**: Security event tracking

## Basic Usage

### Using Pre-configured Dependencies

```python
from fastapi import APIRouter, status
from tripsage.api.core.trip_security import (
    TripReadAccessDep,
    TripOwnerAccessDep,
    TripEditPermissionDep,
)
from tripsage.api.core.dependencies import RequiredPrincipalDep

router = APIRouter(tags=["trips"])

@router.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    access_result: TripReadAccessDep,  # Verifies read access
    principal: RequiredPrincipalDep,
):
    """Get trip details - requires read access."""
    # Access already verified, proceed with operation
    return {"trip_id": trip_id, "access_level": access_result.access_level}

@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    access_result: TripOwnerAccessDep,  # Verifies owner access
    principal: RequiredPrincipalDep,
):
    """Delete trip - requires owner access."""
    # Only trip owner can delete
    return {"message": "Trip deleted successfully"}

@router.put("/trips/{trip_id}")
async def update_trip(
    trip_id: str,
    access_result: TripEditPermissionDep,  # Verifies edit permission
    principal: RequiredPrincipalDep,
):
    """Update trip - requires edit permission."""
    # Owner or collaborators with edit permission can update
    return {"message": "Trip updated successfully"}
```

### Using Decorators

```python
from tripsage.api.core.trip_security import (
    require_trip_access,
    TripAccessLevel,
    TripAccessPermission,
)

@router.get("/trips/{trip_id}/details")
@require_trip_access(TripAccessLevel.READ)
async def get_trip_details(
    trip_id: str,
    principal: RequiredPrincipalDep,
):
    """Get detailed trip information."""
    # Access verification handled by decorator
    return {"trip_id": trip_id, "details": "..."}

@router.post("/trips/{trip_id}/collaborators")
@require_trip_access(
    TripAccessLevel.COLLABORATOR,
    TripAccessPermission.MANAGE
)
async def add_collaborator(
    trip_id: str,
    principal: RequiredPrincipalDep,
):
    """Add collaborator - requires manage permission."""
    # Only users with manage permission can add collaborators
    return {"message": "Collaborator added"}
```

### Custom Dependencies

```python
from tripsage.api.core.trip_security import (
    create_trip_access_dependency,
    TripAccessLevel,
    TripAccessPermission,
)
from typing import Annotated
from fastapi import Depends

# Create custom dependency for specific use case
ViewOnlyAccessDep = Annotated[
    TripAccessResult,
    Depends(create_trip_access_dependency(
        TripAccessLevel.COLLABORATOR,
        TripAccessPermission.VIEW
    ))
]

@router.get("/trips/{trip_id}/readonly-summary")
async def get_readonly_summary(
    trip_id: str,
    access_result: ViewOnlyAccessDep,
    principal: RequiredPrincipalDep,
):
    """Get read-only trip summary."""
    return {
        "trip_id": trip_id,
        "can_edit": access_result.permission_granted in [
            TripAccessPermission.EDIT,
            TripAccessPermission.MANAGE
        ]
    }
```

## Advanced Usage

### Multiple Access Checks

```python
from tripsage.api.core.trip_security import (
    check_trip_ownership,
    check_trip_collaboration,
    get_user_trip_permissions,
)

@router.get("/trips/{trip_id}/permissions")
async def get_trip_permissions(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Get detailed permission information for current user."""
    permissions = await get_user_trip_permissions(
        trip_id, principal, trip_service
    )
    return permissions

@router.post("/trips/{trip_id}/conditional-action")
async def conditional_action(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Perform different actions based on access level."""
    is_owner = await check_trip_ownership(trip_id, principal, trip_service)
    
    if is_owner:
        # Owner-specific logic
        return {"action": "owner_action_performed"}
    
    has_collab = await check_trip_collaboration(
        trip_id, principal, trip_service, TripAccessPermission.EDIT
    )
    
    if has_collab:
        # Collaborator logic
        return {"action": "collaborator_action_performed"}
    
    # Read-only logic
    return {"action": "readonly_action_performed"}
```

### Error Handling

```python
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
)

@router.put("/trips/{trip_id}/sensitive-data")
async def update_sensitive_data(
    trip_id: str,
    access_result: TripOwnerAccessDep,
    principal: RequiredPrincipalDep,
):
    """Update sensitive trip data - owner only."""
    try:
        # The dependency already verified owner access
        # Proceed with sensitive operation
        return {"message": "Sensitive data updated"}
    except Exception as e:
        # Handle any additional errors
        logger.exception(f"Failed to update sensitive data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip data"
        )
```

### WebSocket Security

```python
from fastapi import WebSocket, WebSocketDisconnect
from tripsage.api.core.trip_security import verify_trip_access, TripAccessContext

@router.websocket("/trips/{trip_id}/live-updates")
async def trip_live_updates(
    websocket: WebSocket,
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """WebSocket endpoint with trip access verification."""
    # Verify access before accepting connection
    context = TripAccessContext(
        trip_id=trip_id,
        principal_id=principal.id,
        required_level=TripAccessLevel.READ,
        operation="websocket_connection",
        ip_address=websocket.client.host if websocket.client else "unknown",
    )
    
    access_result = await verify_trip_access(context, trip_service)
    if not access_result.is_authorized:
        await websocket.close(code=1008, reason="Access denied")
        return
    
    await websocket.accept()
    try:
        while True:
            # Handle WebSocket communication
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass
```

## Integration with Existing Routes

### Updating Existing Trip Endpoints

```python
# Before - Manual access checking
@router.get("/trips/{trip_id}")
async def get_trip_old(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    # Manual access check (old way)
    has_access = await trip_service._check_trip_access(trip_id, principal.id)
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Rest of logic...

# After - Using new security system
@router.get("/trips/{trip_id}")
async def get_trip_new(
    trip_id: str,
    access_result: TripReadAccessDep,  # Automatic verification
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    # Access already verified, proceed directly
    # Additional context available in access_result
    logger.info(f"User {principal.id} accessing trip {trip_id} as {access_result.access_level}")
    # Rest of logic...
```

### Collaboration Endpoints

```python
@router.get("/trips/{trip_id}/collaborators")
@require_trip_access(TripAccessLevel.COLLABORATOR)
async def list_collaborators(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """List trip collaborators - any collaborator can view."""
    # Implementation here
    pass

@router.post("/trips/{trip_id}/collaborators")
async def add_collaborator(
    trip_id: str,
    access_result: TripManagePermissionDep,  # Requires manage permission
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Add collaborator - requires manage permission."""
    if not access_result.permission_granted == TripAccessPermission.MANAGE:
        raise HTTPException(
            status_code=403,
            detail="Adding collaborators requires manage permission"
        )
    # Implementation here
    pass

@router.delete("/trips/{trip_id}/collaborators/{user_id}")
async def remove_collaborator(
    trip_id: str,
    user_id: str,
    access_result: TripOwnerAccessDep,  # Only owner can remove
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Remove collaborator - owner only."""
    # Implementation here
    pass
```

## Best Practices

### 1. Choose Appropriate Access Levels

```python
# For viewing operations
access_result: TripReadAccessDep

# For editing trip content
access_result: TripEditPermissionDep

# For managing collaborators, settings
access_result: TripManagePermissionDep

# For deleting trips, changing ownership
access_result: TripOwnerAccessDep
```

### 2. Use Meaningful Operation Names

```python
context = TripAccessContext(
    trip_id=trip_id,
    principal_id=principal.id,
    required_level=TripAccessLevel.WRITE,
    operation="update_trip_itinerary",  # Descriptive operation name
)
```

### 3. Handle Access Results Appropriately

```python
@router.post("/trips/{trip_id}/action")
async def trip_action(
    trip_id: str,
    access_result: TripCollaboratorAccessDep,
    principal: RequiredPrincipalDep,
):
    # Use access result information to customize response
    response = {"trip_id": trip_id}
    
    if access_result.is_owner:
        response["owner_actions"] = ["delete", "transfer_ownership"]
    
    if access_result.permission_granted == TripAccessPermission.MANAGE:
        response["manage_actions"] = ["add_collaborator", "change_settings"]
    
    if access_result.permission_granted in [TripAccessPermission.EDIT, TripAccessPermission.MANAGE]:
        response["edit_actions"] = ["update_itinerary", "add_notes"]
    
    return response
```

### 4. Audit Important Operations

```python
# The system automatically audits access events, but you can add
# operation-specific auditing for important actions

from tripsage_core.services.business.audit_logging_service import audit_security_event

@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    access_result: TripOwnerAccessDep,
    principal: RequiredPrincipalDep,
):
    # Perform deletion
    # ...
    
    # Additional audit for trip deletion
    await audit_security_event(
        event_type=AuditEventType.DATA_DELETION,
        severity=AuditSeverity.HIGH,
        message=f"Trip {trip_id} deleted by owner",
        actor_id=principal.id,
        target_resource=trip_id,
        risk_score=80,
    )
    
    return {"message": "Trip deleted successfully"}
```

## Testing

### Unit Tests

```python
import pytest
from tripsage.api.core.trip_security import verify_trip_access, TripAccessContext

@pytest.mark.asyncio
async def test_trip_access_verification():
    # Mock dependencies and test access verification
    context = TripAccessContext(
        trip_id="test-trip-id",
        principal_id="test-user-id",
        required_level=TripAccessLevel.READ,
        operation="test_operation",
    )
    
    # Test with mocked trip service
    result = await verify_trip_access(context, mock_trip_service)
    assert result.is_authorized
```

### Integration Tests

```python
from fastapi.testclient import TestClient

def test_trip_endpoint_security(client: TestClient):
    # Test that endpoint requires authentication
    response = client.get("/api/trips/test-id")
    assert response.status_code == 401
    
    # Test with valid authentication
    headers = {"Authorization": "Bearer valid-token"}
    response = client.get("/api/trips/test-id", headers=headers)
    # Should succeed or return 403 based on access rights
    assert response.status_code in [200, 403]
```

This security system provides fine-grained access control while maintaining clean, readable code and audit trails for all trip-related operations.
