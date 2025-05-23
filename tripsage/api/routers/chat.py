"""Chat router for TripSage API.

This module provides endpoints for AI chat functionality, including streaming
responses compatible with Vercel AI SDK and session persistence.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.agents.travel import TravelPlanningAgent
from tripsage.api.core.dependencies import get_db, get_session_memory
from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.services.chat_service import ChatService, RateLimiter
from tripsage.models.db.user import UserDB

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (singleton pattern)
_travel_agent = None
_rate_limiter = None


def get_travel_agent() -> TravelPlanningAgent:
    """Get or create the travel planning agent singleton."""
    global _travel_agent
    if _travel_agent is None:
        _travel_agent = TravelPlanningAgent()
    return _travel_agent


def get_rate_limiter() -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_messages=10, window_seconds=60)
    return _rate_limiter


async def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    """Get chat service instance."""
    return ChatService(db, rate_limiter=get_rate_limiter())


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[UUID] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Chat response model for non-streaming requests."""

    id: UUID = Field(default_factory=uuid4, description="Response ID")
    content: str = Field(..., description="Response content")
    tool_calls: Optional[list[dict]] = Field(None, description="Tool calls made")
    finish_reason: str = Field("stop", description="Finish reason")


async def format_vercel_stream_chunk(chunk_type: str, content: str) -> str:
    """Format a chunk for Vercel AI SDK data stream protocol.

    Args:
        chunk_type: Type of chunk (0=text, 3=error, d=finish)
        content: Content to send

    Returns:
        Formatted chunk string
    """
    if chunk_type == "text":
        # Text part format: 0:string\n
        return f'0:"{content}"\n'
    elif chunk_type == "error":
        # Error part format: 3:string\n
        return f'3:"{content}"\n'
    elif chunk_type == "finish":
        # Finish message part format: d:{finishReason,usage}\n
        finish_data = (
            '{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}'
        )
        return f"d:{finish_data}\n"
    return ""


async def stream_agent_response(
    agent: TravelPlanningAgent,
    user_input: str,
    context: dict,
) -> AsyncGenerator[str, None]:
    """Stream the agent response using Vercel AI SDK protocol.

    Args:
        agent: Travel planning agent
        user_input: User input message
        context: Request context

    Yields:
        Formatted stream chunks
    """
    try:
        # Run the agent
        response = await agent.run(user_input, context)

        # Extract content
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        # For now, we'll send the entire response as chunks
        # In a real implementation, we'd stream from the LLM directly
        words = content.split()
        chunk_size = 5  # Send 5 words at a time

        # Stream text in chunks
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield await format_vercel_stream_chunk("text", chunk)
            # Small delay to simulate streaming
            await asyncio.sleep(0.05)

        # Send tool calls if any
        if tool_calls:
            # Tool calls could be streamed in a real implementation
            # For now, we'll just log them
            logger.info(f"Tool calls made: {tool_calls}")

        # Send finish message
        yield await format_vercel_stream_chunk("finish", "")

    except Exception as e:
        logger.error(f"Error in stream_agent_response: {str(e)}")
        yield await format_vercel_stream_chunk("error", str(e))


@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: UserDB = Depends(get_current_user),
    session_memory: dict = Depends(get_session_memory),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Handle chat requests with optional streaming and session persistence.

    Args:
        request: Chat request
        current_user: Current user object
        session_memory: Session memory
        chat_service: Chat service instance

    Returns:
        StreamingResponse for streaming requests, ChatResponse otherwise
    """
    # Get the travel agent
    agent = get_travel_agent()

    # Get the last user message
    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided",
        )

    last_message = request.messages[-1]
    if last_message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user",
        )

    # Create or get session
    session_id = request.session_id
    if not session_id:
        # Create new session
        session = await chat_service.create_session(
            user_id=current_user.id,
            metadata={"agent": "travel_planning", "stream": request.stream},
        )
        session_id = session.id
        logger.info(f"Created new chat session {session_id} for user {current_user.id}")
    else:
        # Verify session exists and belongs to user
        try:
            session = await chat_service.get_session(
                session_id, user_id=current_user.id
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied",
            )

    # Store incoming message
    try:
        await chat_service.add_message(
            session_id=session_id,
            role=last_message.role,
            content=last_message.content,
            user_id=current_user.id,
        )
    except Exception as e:
        if "Rate limit exceeded" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        raise

    # Build context with session history
    recent_messages = await chat_service.get_recent_messages(
        session_id=session_id, limit=50, max_tokens=4000
    )

    context = {
        "user_id": str(current_user.id),
        "session_id": str(session_id),
        "session_memory": session_memory,
        "message_history": [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages.messages[
                :-1
            ]  # Exclude last message we just added
        ],
    }

    # Handle streaming vs non-streaming
    if request.stream:
        # Return streaming response with Vercel AI SDK protocol
        async def stream_with_persistence():
            """Stream response and persist assistant message."""
            full_content = ""
            tool_calls = []

            async for chunk in stream_agent_response(
                agent, last_message.content, context
            ):
                # Extract content from chunk if it's a text chunk
                if chunk.startswith('0:"'):
                    content_part = chunk[3:-2]  # Remove 0:" prefix and "\n suffix
                    full_content += content_part
                yield chunk

            # Store assistant response after streaming completes
            if full_content:
                await chat_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    metadata={"tool_calls": tool_calls} if tool_calls else None,
                )

        return StreamingResponse(
            stream_with_persistence(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Vercel-AI-Data-Stream": "v1",
                "X-Session-Id": str(session_id),  # Include session ID in response
            },
        )
    else:
        # Return regular JSON response
        response = await agent.run(last_message.content, context)

        # Store assistant response
        await chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=response.get("content", ""),
            metadata={"tool_calls": response.get("tool_calls", [])}
            if response.get("tool_calls")
            else None,
        )

        return ChatResponse(
            id=session_id,  # Use session ID as response ID for consistency
            content=response.get("content", ""),
            tool_calls=response.get("tool_calls", []),
            finish_reason="stop",
        )


@router.post("/sessions/{session_id}/continue")
async def continue_session(
    session_id: UUID,
    request: ChatRequest,
    current_user: UserDB = Depends(get_current_user),
    session_memory: dict = Depends(get_session_memory),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Continue an existing chat session.

    Args:
        session_id: Session ID to continue
        request: Chat request
        current_user: Current user object
        session_memory: Session memory
        chat_service: Chat service instance

    Returns:
        StreamingResponse for streaming requests, ChatResponse otherwise
    """
    # Override session_id in request
    request.session_id = session_id

    # Delegate to main chat endpoint
    return await chat(request, current_user, session_memory, chat_service)


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    current_user: UserDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = 100,
    offset: int = 0,
):
    """Get chat history for a session.

    Args:
        session_id: Session ID
        current_user: Current user object
        chat_service: Chat service instance
        limit: Maximum number of messages to return
        offset: Number of messages to skip

    Returns:
        Session with message history
    """
    # Get session (verifies access)
    try:
        session = await chat_service.get_session(session_id, user_id=current_user.id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    # Get messages
    messages = await chat_service.get_messages(session_id, limit=limit, offset=offset)

    return {
        "session_id": str(session.id),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ],
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "metadata": session.metadata,
    }


@router.get("/sessions")
async def list_sessions(
    current_user: UserDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = 20,
):
    """List active chat sessions for the current user.

    Args:
        current_user: Current user object
        chat_service: Chat service instance
        limit: Maximum number of sessions to return

    Returns:
        List of active sessions with statistics
    """
    sessions = await chat_service.get_active_sessions(current_user.id, limit=limit)

    return {
        "sessions": [
            {
                "id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": session.message_count,
                "last_message_at": session.last_message_at.isoformat()
                if session.last_message_at
                else None,
                "metadata": session.metadata,
            }
            for session in sessions
        ]
    }


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: UUID,
    current_user: UserDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """End a chat session.

    Args:
        session_id: Session ID to end
        current_user: Current user object
        chat_service: Chat service instance

    Returns:
        Success message
    """
    # Verify session belongs to user
    try:
        await chat_service.get_session(session_id, user_id=current_user.id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    # End the session
    await chat_service.end_session(session_id)

    return {"message": "Session ended successfully", "session_id": str(session_id)}
