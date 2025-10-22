"""Chat router for TripSage API.

This module provides endpoints for AI chat functionality using the unified
chat service for clean separation of concerns.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from tripsage.api.core.dependencies import (
    ChatServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CreateMessageRequest,
    SessionCreateRequest,
)
from tripsage_core.observability.otel import (
    http_route_attr_fn,
    record_histogram,
    trace_span,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
@trace_span(name="api.chat.completion")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def chat(
    request: ChatRequest,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Handle chat requests with optional streaming and session persistence.

    Args:
        request: Chat request with messages and options
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        Chat response with assistant message
    """
    try:
        user_id = get_principal_id(principal)

        # Delegate to unified chat service
        return await chat_service.chat_completion(user_id, request)

    except Exception as e:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        ) from e


@router.post("/sessions", response_model=dict, status_code=status.HTTP_201_CREATED)
@trace_span(name="api.chat.sessions.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_session(
    body: SessionCreateRequest,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Create a new chat session.

    Args:
        title: Session title
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        Created session information

    Args:
        body: Session creation request body
    """
    try:
        user_id = get_principal_id(principal)

        from tripsage_core.services.business.chat_service import (
            ChatSessionCreateRequest,
        )

        # Convert API request to core request
        session_request = ChatSessionCreateRequest(
            title=body.title, metadata=body.metadata, trip_id=None
        )

        session = await chat_service.create_session(user_id, session_request)
        return session.model_dump() if hasattr(session, "model_dump") else session

    except Exception as e:
        logger.exception("Session creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed",
        ) from e


@router.get("/sessions", response_model=list[dict])
@trace_span(name="api.chat.sessions.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def list_sessions(
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """List chat sessions for the current user.

    Args:
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        List of user's chat sessions
    """
    try:
        user_id = get_principal_id(principal)
        sessions = await chat_service.get_user_sessions(user_id)
        return [s.model_dump() if hasattr(s, "model_dump") else s for s in sessions]

    except Exception as e:
        logger.exception("Session listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session listing failed",
        ) from e


@router.get("/sessions/{session_id}", response_model=dict)
@trace_span(name="api.chat.sessions.get")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_session(
    session_id: UUID,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Get a specific chat session.

    Args:
        session_id: Session ID
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        Session details
    """
    try:
        user_id = get_principal_id(principal)
        session = await chat_service.get_session(str(session_id), user_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return session.model_dump() if hasattr(session, "model_dump") else session

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Session retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session retrieval failed",
        ) from e


@router.get("/sessions/{session_id}/messages", response_model=list[dict])
@trace_span(name="api.chat.messages.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_session_messages(
    session_id: UUID,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
    limit: int = 50,
):
    """Get messages from a chat session.

    Args:
        session_id: Session ID
        principal: Current authenticated principal
        chat_service: Unified chat service
        limit: Maximum number of messages to return

    Returns:
        List of session messages
    """
    try:
        user_id = get_principal_id(principal)
        messages = await chat_service.get_messages(str(session_id), user_id, limit)
        return [m.model_dump() if hasattr(m, "model_dump") else m for m in messages]

    except Exception as e:
        logger.exception("Message retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message retrieval failed",
        ) from e


@router.post("/sessions/{session_id}/messages", response_model=dict)
@trace_span(name="api.chat.messages.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_message(
    session_id: UUID,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
    body: CreateMessageRequest,
):
    """Create a new message in a session.

    Args:
        session_id: Session ID
        content: Message content
        role: Message role (user/assistant)
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        Created message

    Args:
        body: Message creation request body
    """
    try:
        user_id = get_principal_id(principal)

        from tripsage_core.services.business.chat_service import MessageCreateRequest

        service_req = MessageCreateRequest(
            role=body.role, content=body.content, metadata=None, tool_calls=None
        )
        message = await chat_service.add_message(str(session_id), user_id, service_req)
        return message.model_dump() if hasattr(message, "model_dump") else message

    except Exception as e:
        logger.exception("Message creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message creation failed",
        ) from e


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Delete a chat session.

    Args:
        session_id: Session ID to delete
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        Success message
    """
    try:
        user_id = get_principal_id(principal)
        success = await chat_service.end_session(str(session_id), user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Session deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session deletion failed",
        ) from e
