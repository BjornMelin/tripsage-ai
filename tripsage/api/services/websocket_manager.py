"""WebSocket connection manager for TripSage API.

This module provides WebSocket connection management, including authentication,
connection pooling, message broadcasting, and health monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import WebSocket
from jose import jwt

from tripsage.api.core.config import get_settings
from tripsage.api.models.websocket import (
    ConnectionStatus,
    WebSocketAuthRequest,
    WebSocketAuthResponse,
    WebSocketConnectionInfo,
    WebSocketEvent,
    WebSocketEventType,
    WebSocketSubscribeRequest,
    WebSocketSubscribeResponse,
)

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Individual WebSocket connection wrapper."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.session_id = session_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.status = ConnectionStatus.CONNECTED
        self.subscribed_channels: Set[str] = set()
        self.client_ip: Optional[str] = None
        self.user_agent: Optional[str] = None
        self._send_lock = asyncio.Lock()

    async def send(self, event: WebSocketEvent) -> bool:
        """Send event to WebSocket connection.

        Args:
            event: WebSocket event to send

        Returns:
            True if sent successfully, False otherwise
        """
        async with self._send_lock:
            try:
                message = {
                    "id": event.id,
                    "type": event.type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "session_id": str(event.session_id) if event.session_id else None,
                    "payload": event.payload,
                }

                await self.websocket.send_text(json.dumps(message))
                return True

            except Exception as e:
                logger.error(f"Failed to send message to {self.connection_id}: {e}")
                self.status = ConnectionStatus.ERROR
                return False

    async def send_raw(self, message: Dict) -> bool:
        """Send raw message to WebSocket connection.

        Args:
            message: Raw message dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        async with self._send_lock:
            try:
                await self.websocket.send_text(json.dumps(message))
                return True

            except Exception as e:
                logger.error(f"Failed to send raw message to {self.connection_id}: {e}")
                self.status = ConnectionStatus.ERROR
                return False

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is stale based on last heartbeat.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            True if connection is stale
        """
        return (
            datetime.utcnow() - self.last_heartbeat
        ).total_seconds() > timeout_seconds

    def subscribe_to_channel(self, channel: str) -> None:
        """Subscribe to a channel."""
        self.subscribed_channels.add(channel)
        logger.debug(f"Connection {self.connection_id} subscribed to {channel}")

    def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        self.subscribed_channels.discard(channel)
        logger.debug(f"Connection {self.connection_id} unsubscribed from {channel}")

    def is_subscribed_to_channel(self, channel: str) -> bool:
        """Check if subscribed to a channel."""
        return channel in self.subscribed_channels

    def get_info(self) -> WebSocketConnectionInfo:
        """Get connection information."""
        return WebSocketConnectionInfo(
            connection_id=self.connection_id,
            user_id=self.user_id,
            session_id=self.session_id,
            connected_at=self.connected_at,
            last_heartbeat=self.last_heartbeat,
            client_ip=self.client_ip,
            user_agent=self.user_agent,
            status=self.status,
            subscribed_channels=list(self.subscribed_channels),
        )


class WebSocketManager:
    """WebSocket connection manager."""

    def __init__(self):
        # Connection storage
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[UUID, Set[str]] = {}
        self.session_connections: Dict[UUID, Set[str]] = {}
        self.channel_connections: Dict[str, Set[str]] = {}

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the WebSocket manager."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        # Close all connections
        await self.disconnect_all()

        logger.info("WebSocket manager stopped")

    async def authenticate_connection(
        self, websocket: WebSocket, auth_request: WebSocketAuthRequest
    ) -> WebSocketAuthResponse:
        """Authenticate a WebSocket connection.

        Args:
            websocket: WebSocket instance
            auth_request: Authentication request

        Returns:
            Authentication response
        """
        try:
            # Verify JWT token
            settings = get_settings()
            payload = jwt.decode(
                auth_request.token,
                settings.secret_key,
                algorithms=["HS256"],
            )

            # Validate the token data
            if "sub" not in payload or "user_id" not in payload:
                raise ValueError("Invalid token payload")

            user_id = UUID(payload["user_id"])

            # Create connection
            connection_id = str(uuid4())
            connection = WebSocketConnection(
                websocket=websocket,
                connection_id=connection_id,
                user_id=user_id,
                session_id=auth_request.session_id,
            )

            # Extract client info
            client_host = websocket.client.host if websocket.client else None
            connection.client_ip = client_host

            # Add to connection pools
            self.connections[connection_id] = connection

            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

            if auth_request.session_id:
                if auth_request.session_id not in self.session_connections:
                    self.session_connections[auth_request.session_id] = set()
                self.session_connections[auth_request.session_id].add(connection_id)

            # Subscribe to requested channels
            available_channels = self._get_available_channels(user_id)
            for channel in auth_request.channels:
                if channel in available_channels:
                    connection.subscribe_to_channel(channel)
                    if channel not in self.channel_connections:
                        self.channel_connections[channel] = set()
                    self.channel_connections[channel].add(connection_id)

            logger.info(
                f"Authenticated WebSocket connection {connection_id} for user {user_id}"
            )

            return WebSocketAuthResponse(
                success=True,
                connection_id=connection_id,
                user_id=user_id,
                session_id=auth_request.session_id,
                available_channels=available_channels,
            )

        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            return WebSocketAuthResponse(
                success=False,
                connection_id="",
                error=str(e),
            )

    async def disconnect_connection(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return

        try:
            # Remove from all pools
            self.connections.pop(connection_id, None)

            if connection.user_id and connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]

            if (
                connection.session_id
                and connection.session_id in self.session_connections
            ):
                self.session_connections[connection.session_id].discard(connection_id)
                if not self.session_connections[connection.session_id]:
                    del self.session_connections[connection.session_id]

            # Remove from channels
            for channel in connection.subscribed_channels:
                if channel in self.channel_connections:
                    self.channel_connections[channel].discard(connection_id)
                    if not self.channel_connections[channel]:
                        del self.channel_connections[channel]

            logger.info(f"Disconnected WebSocket connection {connection_id}")

        except Exception as e:
            logger.error(f"Error disconnecting connection {connection_id}: {e}")

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect_connection(connection_id)

    async def send_to_connection(
        self, connection_id: str, event: WebSocketEvent
    ) -> bool:
        """Send event to specific connection.

        Args:
            connection_id: Target connection ID
            event: Event to send

        Returns:
            True if sent successfully
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        return await connection.send(event)

    async def send_to_user(self, user_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a user.

        Args:
            user_id: Target user ID
            event: Event to send

        Returns:
            Number of connections successfully sent to
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0

        for (
            connection_id
        ) in connection_ids.copy():  # Copy to avoid modification during iteration
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def send_to_session(self, session_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a session.

        Args:
            session_id: Target session ID
            event: Event to send

        Returns:
            Number of connections successfully sent to
        """
        connection_ids = self.session_connections.get(session_id, set())
        sent_count = 0

        for (
            connection_id
        ) in connection_ids.copy():  # Copy to avoid modification during iteration
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def send_to_channel(self, channel: str, event: WebSocketEvent) -> int:
        """Send event to all connections subscribed to a channel.

        Args:
            channel: Target channel
            event: Event to send

        Returns:
            Number of connections successfully sent to
        """
        connection_ids = self.channel_connections.get(channel, set())
        sent_count = 0

        for (
            connection_id
        ) in connection_ids.copy():  # Copy to avoid modification during iteration
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def subscribe_connection(
        self, connection_id: str, subscribe_request: WebSocketSubscribeRequest
    ) -> WebSocketSubscribeResponse:
        """Subscribe connection to channels.

        Args:
            connection_id: Connection ID
            subscribe_request: Subscription request

        Returns:
            Subscription response
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return WebSocketSubscribeResponse(
                success=False,
                error="Connection not found",
            )

        # Get available channels for this user
        available_channels = self._get_available_channels(connection.user_id)

        subscribed_channels = []
        failed_channels = []

        # Subscribe to new channels
        for channel in subscribe_request.channels:
            if channel in available_channels:
                connection.subscribe_to_channel(channel)
                if channel not in self.channel_connections:
                    self.channel_connections[channel] = set()
                self.channel_connections[channel].add(connection_id)
                subscribed_channels.append(channel)
            else:
                failed_channels.append(channel)

        # Unsubscribe from channels
        for channel in subscribe_request.unsubscribe_channels:
            connection.unsubscribe_from_channel(channel)
            if channel in self.channel_connections:
                self.channel_connections[channel].discard(connection_id)
                if not self.channel_connections[channel]:
                    del self.channel_connections[channel]

        return WebSocketSubscribeResponse(
            success=True,
            subscribed_channels=subscribed_channels,
            failed_channels=failed_channels,
        )

    def get_connection_info(
        self, connection_id: str
    ) -> Optional[WebSocketConnectionInfo]:
        """Get connection information.

        Args:
            connection_id: Connection ID

        Returns:
            Connection information or None
        """
        connection = self.connections.get(connection_id)
        return connection.get_info() if connection else None

    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection statistics.

        Returns:
            Connection statistics
        """
        return {
            "total_connections": len(self.connections),
            "unique_users": len(self.user_connections),
            "active_sessions": len(self.session_connections),
            "subscribed_channels": len(self.channel_connections),
        }

    def _get_available_channels(self, user_id: Optional[UUID]) -> List[str]:
        """Get available channels for a user.

        Args:
            user_id: User ID

        Returns:
            List of available channels
        """
        if not user_id:
            return []

        # Base channels available to all authenticated users
        channels = [
            "general",
            "notifications",
            f"user:{user_id}",
        ]

        # Add user-specific channels based on permissions/roles
        # This would be extended based on actual requirements

        return channels

    async def _cleanup_stale_connections(self) -> None:
        """Background task to cleanup stale connections."""
        while self._running:
            try:
                stale_connections = []

                for connection_id, connection in self.connections.items():
                    if connection.is_stale():
                        stale_connections.append(connection_id)

                for connection_id in stale_connections:
                    logger.info(f"Cleaning up stale connection {connection_id}")
                    await self.disconnect_connection(connection_id)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def _heartbeat_monitor(self) -> None:
        """Background task to send heartbeat messages."""
        while self._running:
            try:
                # Send heartbeat to all connections
                heartbeat_event = WebSocketEvent(
                    type=WebSocketEventType.CONNECTION_HEARTBEAT,
                    payload={"timestamp": datetime.utcnow().isoformat()},
                )

                for connection_id, connection in self.connections.items():
                    await connection.send(heartbeat_event)
                    connection.update_heartbeat()

                await asyncio.sleep(30)  # Send every 30 seconds

            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
                await asyncio.sleep(30)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
