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
from tripsage.api.schemas.chat import ChatRequest, ChatResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
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
        response = await chat_service.chat_completion(user_id, request)
        return response

    except Exception as e:
        logger.exception(f"Chat request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        ) from e


@router.post("/sessions", response_model=dict)
async def create_session(
    title: str,
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
    """
    try:
        user_id = get_principal_id(principal)

        from tripsage.api.schemas.chat import SessionCreateRequest

        session_request = SessionCreateRequest(title=title)

        session = await chat_service.create_session(user_id, session_request)
        return session

    except Exception as e:
        logger.exception(f"Session creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed",
        ) from e


@router.get("/sessions", response_model=list[dict])
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
        sessions = await chat_service.list_sessions(user_id)
        return sessions

    except Exception as e:
        logger.exception(f"Session listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session listing failed",
        ) from e


@router.get("/sessions/{session_id}", response_model=dict)
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
        session = await chat_service.get_session(user_id, session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Session retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session retrieval failed",
        ) from e


@router.get("/sessions/{session_id}/messages", response_model=list[dict])
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
        messages = await chat_service.get_messages(user_id, session_id, limit)
        return messages

    except Exception as e:
        logger.exception(f"Message retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message retrieval failed",
        ) from e


@router.post("/sessions/{session_id}/messages", response_model=dict)
async def create_message(
    session_id: UUID,
    content: str,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
    role: str = "user",
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
    """
    try:
        user_id = get_principal_id(principal)

        from tripsage.api.schemas.chat import CreateMessageRequest

        message_request = CreateMessageRequest(content=content, role=role)

        message = await chat_service.create_message(
            user_id, session_id, message_request
        )
        return message

    except Exception as e:
        logger.exception(f"Message creation failed")
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
        success = await chat_service.delete_session(user_id, session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Session deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session deletion failed",
        ) from e
