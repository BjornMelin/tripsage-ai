"""Real-time dashboard monitoring endpoints.

This module provides real-time monitoring capabilities for the dashboard:
- WebSocket connections for live metrics streaming
- Server-sent events for real-time updates
- Live alert notifications
- Real-time system health monitoring
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    CacheDep,
    DatabaseDep,
)
from tripsage_core.services.business.dashboard_service import (
    ApiKeyMonitoringService,  # Compatibility adapter for BJO-211
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard/realtime", tags=["dashboard-realtime"])


class RealtimeMetrics(BaseModel):
    """Real-time metrics data."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requests_per_second: float
    errors_per_second: float
    success_rate: float
    avg_latency_ms: float
    active_connections: int
    cache_hit_rate: float
    memory_usage_percentage: float


class AlertNotification(BaseModel):
    """Real-time alert notification."""

    alert_id: str
    type: str  # "new", "updated", "resolved"
    severity: str
    message: str
    service: str | None = None
    key_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class SystemEvent(BaseModel):
    """System event notification."""

    event_id: str
    event_type: str  # "service_status_change", "rate_limit_exceeded", "maintenance"
    message: str
    severity: str  # "info", "warning", "error", "critical"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    affected_services: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DashboardConnectionManager:
    """Manages WebSocket connections for dashboard clients."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.connection_metadata: dict[WebSocket, dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_type: str = "dashboard",
    ) -> None:
        """Connect a new dashboard client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_type": connection_type,
            "connected_at": datetime.now(UTC),
        }

        logger.info(f"Dashboard WebSocket connection established for user {user_id}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a dashboard client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            metadata = self.connection_metadata.pop(websocket, {})
            user_id = metadata.get("user_id", "unknown")
            logger.info(f"Dashboard WebSocket connection closed for user {user_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send message to specific connection."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str, connection_type: str | None = None) -> None:
        """Broadcast message to all or filtered connections."""
        disconnected = []

        for connection in self.active_connections:
            try:
                # Filter by connection type if specified
                if connection_type:
                    metadata = self.connection_metadata.get(connection, {})
                    if metadata.get("connection_type") != connection_type:
                        continue

                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def send_metrics(self, metrics: RealtimeMetrics) -> None:
        """Send real-time metrics to all dashboard connections."""
        message = {
            "type": "metrics",
            "data": metrics.model_dump(mode="json"),
        }
        await self.broadcast(json.dumps(message), "dashboard")

    async def send_alert(self, alert: AlertNotification) -> None:
        """Send alert notification to all dashboard connections."""
        message = {
            "type": "alert",
            "data": alert.model_dump(mode="json"),
        }
        await self.broadcast(json.dumps(message), "dashboard")

    async def send_system_event(self, event: SystemEvent) -> None:
        """Send system event to all dashboard connections."""
        message = {
            "type": "system_event",
            "data": event.model_dump(mode="json"),
        }
        await self.broadcast(json.dumps(message), "dashboard")


# Global connection manager
dashboard_manager = DashboardConnectionManager()


@router.websocket("/ws/{user_id}")
async def dashboard_websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    cache_service: CacheDep,
    db_service: DatabaseDep,
) -> None:
    """WebSocket endpoint for real-time dashboard updates.

    Provides real-time streaming of:
    - System metrics and performance data
    - Alert notifications
    - System events and status changes
    """
    await dashboard_manager.connect(websocket, user_id, "dashboard")

    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Start background task for sending periodic metrics
        metrics_task = asyncio.create_task(
            _send_periodic_metrics(websocket, monitoring_service)
        )

        # Listen for client messages (e.g., subscription preferences)
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle client messages
                if message.get("type") == "subscribe":
                    # Client wants to subscribe to specific metrics
                    await _handle_subscription(websocket, message, monitoring_service)
                elif message.get("type") == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON from dashboard WebSocket client")
                continue
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        if "metrics_task" in locals():
            metrics_task.cancel()
        dashboard_manager.disconnect(websocket)


@router.get("/events")
async def dashboard_events_stream(
    request: Request,
    cache_service: CacheDep,
    db_service: DatabaseDep,
) -> Any:
    """Server-sent events endpoint for dashboard updates.

    Provides real-time updates via Server-Sent Events (SSE) as an alternative
    to WebSockets for clients that prefer HTTP-based streaming.
    """

    async def event_stream() -> Any:
        """Generate server-sent events."""
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        last_metrics_time = datetime.now(UTC)

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send metrics every 5 seconds
                now = datetime.now(UTC)
                if (now - last_metrics_time).total_seconds() >= 5:
                    try:
                        # Get current metrics
                        dashboard_data = await monitoring_service.get_dashboard_data(
                            time_range_hours=1,
                            top_users_limit=5,
                        )

                        metrics = RealtimeMetrics(
                            requests_per_second=(
                                dashboard_data.total_requests / 3600.0
                            ),  # Simplified
                            errors_per_second=dashboard_data.total_errors / 3600.0,
                            success_rate=dashboard_data.overall_success_rate,
                            avg_latency_ms=150.0,  # Simplified
                            active_connections=len(
                                dashboard_manager.active_connections
                            ),
                            cache_hit_rate=0.85,  # Simplified
                            memory_usage_percentage=65.0,  # Simplified
                        )

                        # Send as SSE
                        yield "event: metrics\n"
                        yield f"data: {metrics.model_dump_json()}\n\n"

                        last_metrics_time = now

                    except Exception as e:
                        logger.error(f"Error generating metrics for SSE: {e}")

                # Send any new alerts
                for alert in monitoring_service.active_alerts.values():
                    if not alert.acknowledged:
                        alert_notification = AlertNotification(
                            alert_id=alert.alert_id,
                            type="new",
                            severity=alert.severity,
                            message=alert.message,
                            service=alert.service,
                            key_id=alert.key_id,
                            details=alert.details,
                        )

                        yield "event: alert\n"
                        yield f"data: {alert_notification.model_dump_json()}\n\n"

                # Wait before next iteration
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/alerts/broadcast")
async def broadcast_alert(
    alert_data: dict[str, Any],
    cache_service: CacheDep,
    db_service: DatabaseDep,
) -> dict[str, Any]:
    """Broadcast an alert to all connected dashboard clients.

    This endpoint can be called by internal services to push
    real-time alerts to the dashboard.
    """
    try:
        alert = AlertNotification(
            alert_id=alert_data.get("alert_id", "unknown"),
            type=alert_data.get("type", "new"),
            severity=alert_data.get("severity", "medium"),
            message=alert_data.get("message", ""),
            service=alert_data.get("service"),
            key_id=alert_data.get("key_id"),
            details=alert_data.get("details", {}),
        )

        await dashboard_manager.send_alert(alert)

        return {
            "success": True,
            "message": "Alert broadcasted successfully",
            "alert_id": alert.alert_id,
        }

    except Exception as e:
        logger.error(f"Failed to broadcast alert: {e}")
        return {
            "success": False,
            "message": f"Failed to broadcast alert: {e!s}",
        }


@router.post("/events/broadcast")
async def broadcast_system_event(
    event_data: dict[str, Any],
    cache_service: CacheDep,
    db_service: DatabaseDep,
) -> dict[str, Any]:
    """Broadcast a system event to all connected dashboard clients.

    This endpoint can be called by internal services to push
    real-time system events to the dashboard.
    """
    try:
        event = SystemEvent(
            event_id=event_data.get("event_id", "unknown"),
            event_type=event_data.get("event_type", "info"),
            message=event_data.get("message", ""),
            severity=event_data.get("severity", "info"),
            affected_services=event_data.get("affected_services", []),
            details=event_data.get("details", {}),
        )

        await dashboard_manager.send_system_event(event)

        return {
            "success": True,
            "message": "System event broadcasted successfully",
            "event_id": event.event_id,
        }

    except Exception as e:
        logger.error(f"Failed to broadcast system event: {e}")
        return {
            "success": False,
            "message": f"Failed to broadcast system event: {e!s}",
        }


@router.get("/connections")
async def get_active_connections() -> dict[str, Any]:
    """Get information about active dashboard connections.

    Returns statistics about currently connected dashboard clients.
    """
    connections_info = []

    for _websocket, metadata in dashboard_manager.connection_metadata.items():
        connections_info.append(
            {
                "user_id": metadata.get("user_id"),
                "connection_type": metadata.get("connection_type"),
                "connected_at": metadata.get("connected_at"),
                "duration_seconds": (
                    datetime.now(UTC) - metadata.get("connected_at", datetime.now(UTC))
                ).total_seconds(),
            }
        )

    return {
        "total_connections": len(dashboard_manager.active_connections),
        "connections": connections_info,
    }


async def _send_periodic_metrics(
    websocket: WebSocket, monitoring_service: ApiKeyMonitoringService
) -> None:
    """Send periodic metrics updates to a WebSocket connection."""
    try:
        while True:
            try:
                # Get current dashboard data
                dashboard_data = await monitoring_service.get_dashboard_data(
                    time_range_hours=1,
                    top_users_limit=5,
                )

                # Create real-time metrics
                metrics = RealtimeMetrics(
                    requests_per_second=(
                        dashboard_data.total_requests / 3600.0
                    ),  # Simplified
                    errors_per_second=dashboard_data.total_errors / 3600.0,
                    success_rate=dashboard_data.overall_success_rate,
                    avg_latency_ms=150.0,  # Would be calculated from actual data
                    active_connections=len(dashboard_manager.active_connections),
                    cache_hit_rate=0.85,  # Would be retrieved from cache service
                    memory_usage_percentage=65.0,  # Would be retrieved from system
                )

                # Send metrics
                message = {
                    "type": "metrics",
                    "data": metrics.model_dump(mode="json"),
                }

                await websocket.send_text(json.dumps(message))

                # Wait 5 seconds before next update
                await asyncio.sleep(5)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error sending periodic metrics: {e}")
                await asyncio.sleep(5)  # Continue trying

    except asyncio.CancelledError:
        pass


async def _handle_subscription(
    websocket: WebSocket,
    message: dict[str, Any],
    monitoring_service: ApiKeyMonitoringService,
) -> None:
    """Handle client subscription requests."""
    try:
        subscription_type = message.get("subscription_type")

        if subscription_type == "alerts":
            # Send current unacknowledged alerts
            for alert in monitoring_service.active_alerts.values():
                if not alert.acknowledged:
                    alert_notification = AlertNotification(
                        alert_id=alert.alert_id,
                        type="current",
                        severity=alert.severity,
                        message=alert.message,
                        service=alert.service,
                        key_id=alert.key_id,
                        details=alert.details,
                    )

                    response = {
                        "type": "alert",
                        "data": alert_notification.model_dump(mode="json"),
                    }

                    await websocket.send_text(json.dumps(response))

        elif subscription_type == "metrics":
            # Send current metrics immediately
            dashboard_data = await monitoring_service.get_dashboard_data(
                time_range_hours=1,
                top_users_limit=5,
            )

            metrics = RealtimeMetrics(
                requests_per_second=dashboard_data.total_requests / 3600.0,
                errors_per_second=dashboard_data.total_errors / 3600.0,
                success_rate=dashboard_data.overall_success_rate,
                avg_latency_ms=150.0,
                active_connections=len(dashboard_manager.active_connections),
                cache_hit_rate=0.85,
                memory_usage_percentage=65.0,
            )

            response = {
                "type": "metrics",
                "data": metrics.model_dump(mode="json"),
            }

            await websocket.send_text(json.dumps(response))

        # Send subscription confirmation
        confirmation = {
            "type": "subscription_confirmed",
            "subscription_type": subscription_type,
        }

        await websocket.send_text(json.dumps(confirmation))

    except Exception as e:
        logger.error(f"Error handling subscription: {e}")


# Export the dashboard manager for use by other services
__all__ = [
    "AlertNotification",
    "DashboardConnectionManager",
    "RealtimeMetrics",
    "SystemEvent",
    "dashboard_manager",
]
