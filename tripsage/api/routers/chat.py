"""Chat router for TripSage API.

This module provides endpoints for AI chat functionality, including streaming
responses compatible with Vercel AI SDK.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tripsage.agents.travel import TravelPlanningAgent
from tripsage.api.core.dependencies import get_session_memory
from tripsage.api.middlewares.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Global agent instance (singleton pattern)
_travel_agent = None


def get_travel_agent() -> TravelPlanningAgent:
    """Get or create the travel planning agent singleton."""
    global _travel_agent
    if _travel_agent is None:
        _travel_agent = TravelPlanningAgent()
    return _travel_agent


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
    user_id: str = Depends(get_current_user),
    session_memory: dict = Depends(get_session_memory),
):
    """Handle chat requests with optional streaming.

    Args:
        request: Chat request
        user_id: Current user ID
        session_memory: Session memory

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

    # Build context
    context = {
        "user_id": user_id,
        "session_id": str(request.session_id) if request.session_id else None,
        "session_memory": session_memory,
        "message_history": [msg.model_dump() for msg in request.messages[:-1]],
    }

    # Handle streaming vs non-streaming
    if request.stream:
        # Return streaming response with Vercel AI SDK protocol
        return StreamingResponse(
            stream_agent_response(agent, last_message.content, context),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Vercel-AI-Data-Stream": "v1",
            },
        )
    else:
        # Return regular JSON response
        response = await agent.run(last_message.content, context)
        return ChatResponse(
            content=response.get("content", ""),
            tool_calls=response.get("tool_calls", []),
            finish_reason="stop",
        )


@router.post("/sessions/{session_id}/continue")
async def continue_session(
    session_id: UUID,
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    session_memory: dict = Depends(get_session_memory),
):
    """Continue an existing chat session.

    Args:
        session_id: Session ID to continue
        request: Chat request
        user_id: Current user ID
        session_memory: Session memory

    Returns:
        StreamingResponse for streaming requests, ChatResponse otherwise
    """
    # Override session_id in request
    request.session_id = session_id

    # Delegate to main chat endpoint
    return await chat(request, user_id, session_memory)


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Get chat history for a session.

    Args:
        session_id: Session ID
        user_id: Current user ID

    Returns:
        List of messages in the session
    """
    # TODO: Implement session history retrieval from database
    # For now, return empty history
    return {
        "session_id": str(session_id),
        "messages": [],
        "created_at": None,
        "updated_at": None,
    }
