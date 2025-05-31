"""Common WebSocket models for TripSage API.

This module provides Pydantic v2 common models for WebSocket communication,
including event types, message schemas, and connection management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class WebSocketEventType(str, Enum):
    """WebSocket event types."""

    # Chat events
    CHAT_MESSAGE = "chat_message"
    CHAT_MESSAGE_CHUNK = "chat_message_chunk"
    CHAT_MESSAGE_COMPLETE = "chat_message_complete"
    CHAT_TYPING_START = "chat_typing_start"
    CHAT_TYPING_STOP = "chat_typing_stop"

    # Tool events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"

    # Agent status events
    AGENT_STATUS_UPDATE = "agent_status_update"
    AGENT_TASK_START = "agent_task_start"
    AGENT_TASK_PROGRESS = "agent_task_progress"
    AGENT_TASK_COMPLETE = "agent_task_complete"
    AGENT_ERROR = "agent_error"

    # Connection events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_ERROR = "connection_error"
    CONNECTION_HEARTBEAT = "connection_heartbeat"
    CONNECTION_CLOSE = "connection_close"

    # System events
    ERROR = "error"
    NOTIFICATION = "notification"
    SYSTEM_MESSAGE = "system_message"


class ConnectionStatus(str, Enum):
    """WebSocket connection status."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    """Tool call status types."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class WebSocketToolCall(BaseModel):
    """Tool call information for WebSocket events."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Tool call ID")
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    status: ToolCallStatus = Field(
        default=ToolCallStatus.PENDING, description="Tool call status"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if tool call failed")
    start_time: datetime = Field(
        default_factory=datetime.utcnow, description="Tool call start time"
    )
    end_time: Optional[datetime] = Field(None, description="Tool call completion time")
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )


class WebSocketMessage(BaseModel):
    """WebSocket message model."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Message ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    session_id: Optional[UUID] = Field(None, description="Chat session ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tool_calls: Optional[List[WebSocketToolCall]] = Field(
        None, description="Tool calls"
    )
    is_partial: bool = Field(
        False, description="Whether this is a partial message chunk"
    )
    chunk_index: Optional[int] = Field(
        None, description="Chunk index for partial messages"
    )


class WebSocketAgentStatus(BaseModel):
    """Agent status information."""

    agent_id: str = Field(..., description="Agent identifier")
    is_active: bool = Field(False, description="Whether agent is actively processing")
    current_task: Optional[str] = Field(None, description="Current task description")
    progress: int = Field(0, ge=0, le=100, description="Task progress percentage")
    status_message: Optional[str] = Field(None, description="Detailed status message")
    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )
    active_tools: List[str] = Field(
        default_factory=list, description="Currently active tools"
    )
    total_tools_executed: int = Field(0, description="Total tools executed in session")
    error_count: int = Field(0, description="Number of errors encountered")


class WebSocketEvent(BaseModel):
    """Base WebSocket event model."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Event ID")
    type: WebSocketEventType = Field(..., description="Event type")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    user_id: Optional[UUID] = Field(None, description="User ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event payload."""
        if not isinstance(v, dict):
            raise ValueError("Payload must be a dictionary")
        return v


class ChatMessageEvent(WebSocketEvent):
    """Chat message WebSocket event."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.CHAT_MESSAGE, description="Event type"
    )
    message: WebSocketMessage = Field(..., description="Chat message")

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "message": self.message.model_dump(),
            "session_id": str(self.session_id) if self.session_id else None,
        }


class ChatMessageChunkEvent(WebSocketEvent):
    """Chat message chunk WebSocket event for streaming."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.CHAT_MESSAGE_CHUNK, description="Event type"
    )
    content: str = Field(..., description="Message chunk content")
    chunk_index: int = Field(..., description="Chunk index")
    is_final: bool = Field(False, description="Whether this is the final chunk")

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "is_final": self.is_final,
            "session_id": str(self.session_id) if self.session_id else None,
        }


class AgentStatusEvent(WebSocketEvent):
    """Agent status WebSocket event."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.AGENT_STATUS_UPDATE, description="Event type"
    )
    agent_status: WebSocketAgentStatus = Field(..., description="Agent status")

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "agent_status": self.agent_status.model_dump(),
            "user_id": str(self.user_id) if self.user_id else None,
        }


class ToolCallEvent(WebSocketEvent):
    """Tool call WebSocket event."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.TOOL_CALL_START, description="Event type"
    )
    tool_call: WebSocketToolCall = Field(..., description="Tool call information")

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "tool_call": self.tool_call.model_dump(),
            "session_id": str(self.session_id) if self.session_id else None,
        }


class ErrorEvent(WebSocketEvent):
    """Error WebSocket event."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.ERROR, description="Event type"
    )
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "details": self.details or {},
        }


class ConnectionEvent(WebSocketEvent):
    """Connection status WebSocket event."""

    type: WebSocketEventType = Field(
        default=WebSocketEventType.CONNECTION_ESTABLISHED, description="Event type"
    )
    status: ConnectionStatus = Field(..., description="Connection status")
    connection_id: str = Field(..., description="Connection ID")

    @property
    def payload(self) -> Dict[str, Any]:
        """Get event payload."""
        return {
            "status": self.status,
            "connection_id": self.connection_id,
            "user_id": str(self.user_id) if self.user_id else None,
        }


class WebSocketConnectionInfo(BaseModel):
    """WebSocket connection information."""

    connection_id: str = Field(..., description="Unique connection ID")
    user_id: UUID = Field(..., description="User ID")
    session_id: Optional[UUID] = Field(None, description="Chat session ID")
    connected_at: datetime = Field(
        default_factory=datetime.utcnow, description="Connection timestamp"
    )
    last_heartbeat: datetime = Field(
        default_factory=datetime.utcnow, description="Last heartbeat timestamp"
    )
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    status: ConnectionStatus = Field(
        default=ConnectionStatus.CONNECTED, description="Connection status"
    )
    subscribed_channels: List[str] = Field(
        default_factory=list, description="Subscribed channels"
    )


# Union type for all WebSocket events
WebSocketEventUnion = Union[
    ChatMessageEvent,
    ChatMessageChunkEvent,
    AgentStatusEvent,
    ToolCallEvent,
    ErrorEvent,
    ConnectionEvent,
]


# Event payload validation schemas
WEBSOCKET_EVENT_SCHEMAS = {
    WebSocketEventType.CHAT_MESSAGE: ChatMessageEvent,
    WebSocketEventType.CHAT_MESSAGE_CHUNK: ChatMessageChunkEvent,
    WebSocketEventType.AGENT_STATUS_UPDATE: AgentStatusEvent,
    WebSocketEventType.TOOL_CALL_START: ToolCallEvent,
    WebSocketEventType.TOOL_CALL_PROGRESS: ToolCallEvent,
    WebSocketEventType.TOOL_CALL_COMPLETE: ToolCallEvent,
    WebSocketEventType.ERROR: ErrorEvent,
    WebSocketEventType.CONNECTION_ESTABLISHED: ConnectionEvent,
    WebSocketEventType.CONNECTION_ERROR: ConnectionEvent,
}
