"""Chat router for TripSage API.

This module provides endpoints for AI chat functionality, including streaming
responses compatible with Vercel AI SDK, session persistence, and tool calling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.agents.chat import ChatAgent
from tripsage.api.core.dependencies import (
    get_db_dep,
    get_principal_id,
    get_session_memory_dep,
    require_principal_dep,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.services.core.chat_service import ChatService, RateLimiter
from tripsage_core.models.schemas_common.chat import ToolCall

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (singleton pattern)
_chat_agent = None
_rate_limiter = None

# Module-level dependency singletons imported from deps module


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent


def get_rate_limiter() -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_messages=10, window_seconds=60)
    return _rate_limiter


async def get_chat_service(db: AsyncSession = get_db_dep) -> ChatService:
    """Get chat service instance."""
    return ChatService(db, rate_limiter=get_rate_limiter())


# Create module-level dependency for chat service
get_chat_service_dep = Depends(get_chat_service)


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[UUID] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream the response")
    save_history: bool = Field(True, description="Whether to save chat history")
    tools: Optional[list[str]] = Field(
        None, description="List of specific tools to use"
    )


class ChatResponse(BaseModel):
    """Chat response model for non-streaming requests."""

    id: UUID = Field(default_factory=uuid4, description="Response ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    content: str = Field(..., description="Response content")
    tool_calls: Optional[list[dict]] = Field(None, description="Tool calls made")
    finish_reason: str = Field("stop", description="Finish reason")
    usage: Optional[dict] = Field(None, description="Token usage information")


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


def get_user_available_tools(user_id: str) -> List[str]:
    """Get list of tools available to the user based on their API keys.

    Args:
        user_id: User ID string

    Returns:
        List of available tool names
    """
    # Base tools always available
    available_tools = [
        "time_tools",
        "weather_tools",
        "googlemaps_tools",
        "webcrawl_tools",
        "memory_tools",
    ]

    # Add tools based on user's API keys
    # (would check user.api_keys in real implementation)
    # For now, assume all tools are available if user is authenticated
    if user_id:
        available_tools.extend(
            ["flight_tools", "accommodations_tools", "planning_tools"]
        )

    return available_tools


async def format_tool_call_chunk(tool_call: Dict) -> str:
    """Format a tool call for Vercel AI SDK protocol.

    Args:
        tool_call: Tool call dictionary

    Returns:
        Formatted tool call chunk
    """
    # Tool call format: 9:{id,name,args}\n
    tool_data = {
        "id": tool_call.get("id", str(uuid4())),
        "name": tool_call.get("name", ""),
        "args": tool_call.get("arguments", {}),
    }
    return f"9:{json.dumps(tool_data)}\n"


async def format_tool_result_chunk(tool_call_id: str, result: Dict) -> str:
    """Format a tool result for Vercel AI SDK protocol.

    Args:
        tool_call_id: ID of the tool call
        result: Tool execution result

    Returns:
        Formatted tool result chunk
    """
    # Tool result format: a:{callId,result}\n
    result_data = {"callId": tool_call_id, "result": result}
    return f"a:{json.dumps(result_data)}\n"


async def stream_agent_response(
    agent: ChatAgent,
    user_input: str,
    context: dict,
    available_tools: List[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream the agent response using Vercel AI SDK protocol with tool calling.

    Args:
        agent: Chat agent
        user_input: User input message
        context: Request context
        available_tools: Available tools for this user

    Yields:
        Formatted stream chunks
    """
    try:
        # Run the agent with tool calling
        response = await agent.run_with_tools(user_input, context, available_tools)

        # Extract content and metadata
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        routing_info = response.get("routed_to")

        # Send routing information if present
        if routing_info:
            routing_chunk = f"🔄 Routing to {routing_info} specialist...\n\n"
            yield await format_vercel_stream_chunk("text", routing_chunk)
            await asyncio.sleep(0.1)

        # Send tool calls first if any
        if tool_calls:
            for tool_call in tool_calls:
                yield await format_tool_call_chunk(tool_call)
                await asyncio.sleep(0.05)

                # Execute tool call if it has arguments
                if "arguments" in tool_call:
                    try:
                        user_id = context.get("user_id", "anonymous")
                        tool_result = await agent.execute_tool_call(
                            tool_call["name"], tool_call["arguments"], user_id
                        )

                        yield await format_tool_result_chunk(
                            tool_call.get("id", str(uuid4())), tool_result
                        )
                        await asyncio.sleep(0.05)

                    except Exception as e:
                        logger.error(f"Tool execution failed: {str(e)}")
                        error_result = {"status": "error", "error": str(e)}
                        yield await format_tool_result_chunk(
                            tool_call.get("id", str(uuid4())), error_result
                        )

        # Stream text content in chunks
        if content:
            words = content.split()
            chunk_size = 5  # Send 5 words at a time

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield await format_vercel_stream_chunk("text", chunk)
                # Small delay to simulate streaming
                await asyncio.sleep(0.05)

        # Send finish message
        yield await format_vercel_stream_chunk("finish", "")

    except Exception as e:
        logger.error(f"Error in stream_agent_response: {str(e)}")
        yield await format_vercel_stream_chunk("error", str(e))


@router.post("/")
async def chat(
    request: ChatRequest,
    principal: Principal = require_principal_dep,
    session_memory: dict = get_session_memory_dep,
    chat_service: ChatService = get_chat_service_dep,
):
    """Handle chat requests with optional streaming and session persistence.

    Args:
        request: Chat request
        principal: Current authenticated principal
        session_memory: Session memory
        chat_service: Chat service instance

    Returns:
        StreamingResponse for streaming requests, ChatResponse otherwise
    """
    user_id = get_principal_id(principal)
    # Get the chat agent
    agent = get_chat_agent()

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
            user_id=user_id,
            metadata={
                "agent": "travel_planning",
                "stream": request.stream,
                "save_history": request.save_history,
            },
        )
        session_id = session.id
        logger.info(f"Created new chat session {session_id} for user {user_id}")
    else:
        # Verify session exists and belongs to user
        try:
            session = await chat_service.get_session(session_id, user_id=user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied",
            ) from e

    # Store incoming message (only if history saving is enabled)
    if request.save_history:
        try:
            await chat_service.add_message(
                session_id=session_id,
                role=last_message.role,
                content=last_message.content,
                user_id=user_id,
            )
        except Exception as e:
            if "Rate limit exceeded" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(e),
                ) from e
            raise

    # Build context with session history and tool information
    recent_messages = await chat_service.get_recent_messages(
        session_id=session_id, limit=50, max_tokens=4000
    )

    # Get available tools for this user
    available_tools = get_user_available_tools(user_id)

    # Filter tools if specific tools requested
    if request.tools:
        available_tools = [tool for tool in available_tools if tool in request.tools]

    context = {
        "user_id": str(user_id),
        "session_id": str(session_id),
        "session_memory": session_memory,
        "available_tools": available_tools,
        "tool_calling_enabled": True,
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
            tool_results = []

            async for chunk in stream_agent_response(
                agent, last_message.content, context, available_tools
            ):
                # Extract content from chunk based on type
                if chunk.startswith('0:"'):
                    content_part = chunk[3:-2]  # Remove 0:" prefix and "\n suffix
                    full_content += content_part
                elif chunk.startswith("9:"):
                    # Tool call chunk
                    try:
                        tool_call_data = json.loads(chunk[2:])
                        tool_calls.append(tool_call_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse tool call chunk: {chunk}")
                elif chunk.startswith("a:"):
                    # Tool result chunk
                    try:
                        tool_result_data = json.loads(chunk[2:])
                        tool_results.append(tool_result_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse tool result chunk: {chunk}")

                yield chunk

            # Store assistant response after streaming completes
            # (only if history saving is enabled)
            if request.save_history:
                metadata = {}
                if tool_calls:
                    metadata["tool_calls"] = tool_calls
                if tool_results:
                    metadata["tool_results"] = tool_results

                await chat_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    metadata=metadata if metadata else None,
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
        response = await agent.run_with_tools(
            last_message.content, context, available_tools
        )

        # Process tool calls for response format
        processed_tool_calls = []
        if response.get("tool_calls"):
            for tool_call in response["tool_calls"]:
                # Execute tool if not already executed
                tool_result = None
                if "arguments" in tool_call:
                    try:
                        tool_result = await agent.execute_tool_call(
                            tool_call["name"],
                            tool_call["arguments"],
                            str(user_id),
                        )
                    except Exception as e:
                        logger.error(f"Tool execution failed: {str(e)}")
                        tool_result = {"status": "error", "error": str(e)}

                processed_tool_calls.append(
                    ToolCall(
                        id=tool_call.get("id", str(uuid4())),
                        name=tool_call["name"],
                        args=tool_call.get("arguments", {}),
                        result=tool_result,
                    )
                )

        # Store assistant response (only if history saving is enabled)
        if request.save_history:
            metadata = {}
            if processed_tool_calls:
                metadata["tool_calls"] = [
                    {"id": tc.id, "name": tc.name, "args": tc.args, "result": tc.result}
                    for tc in processed_tool_calls
                ]

            await chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=response.get("content", ""),
                metadata=metadata if metadata else None,
            )

        return ChatResponse(
            id=session_id,  # Use session ID as response ID for consistency
            session_id=session_id,
            content=response.get("content", ""),
            tool_calls=processed_tool_calls,
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0},  # Placeholder
        )


@router.post("/sessions/{session_id}/continue")
async def continue_session(
    session_id: UUID,
    request: ChatRequest,
    principal: Principal = require_principal_dep,
    session_memory: dict = get_session_memory_dep,
    chat_service: ChatService = get_chat_service_dep,
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
    return await chat(request, principal, session_memory, chat_service)


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    principal: Principal = require_principal_dep,
    chat_service: ChatService = get_chat_service_dep,
    limit: int = 100,
    offset: int = 0,
):
    """Get chat history for a session.

    Args:
        session_id: Session ID
        principal: Current authenticated principal
        chat_service: Chat service instance
        limit: Maximum number of messages to return
        offset: Number of messages to skip

    Returns:
        Session with message history
    """
    user_id = get_principal_id(principal)
    # Get session (verifies access)
    try:
        session = await chat_service.get_session(session_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        ) from e

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
    principal: Principal = require_principal_dep,
    chat_service: ChatService = get_chat_service_dep,
    limit: int = 20,
):
    """List active chat sessions for the current user.

    Args:
        principal: Current authenticated principal
        chat_service: Chat service instance
        limit: Maximum number of sessions to return

    Returns:
        List of active sessions with statistics
    """
    user_id = get_principal_id(principal)
    sessions = await chat_service.get_active_sessions(user_id, limit=limit)

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
    principal: Principal = require_principal_dep,
    chat_service: ChatService = get_chat_service_dep,
):
    """End a chat session.

    Args:
        session_id: Session ID to end
        principal: Current authenticated principal
        chat_service: Chat service instance

    Returns:
        Success message
    """
    user_id = get_principal_id(principal)
    # Verify session belongs to user
    try:
        await chat_service.get_session(session_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        ) from e

    # End the session
    await chat_service.end_session(session_id)

    return {"message": "Session ended successfully", "session_id": str(session_id)}


@router.get("/export")
async def export_chat_data(
    principal: Principal = require_principal_dep,
    chat_service: ChatService = get_chat_service_dep,
    format: str = "json",
):
    """Export all chat data for the current user.

    Args:
        principal: Current authenticated principal
        chat_service: Chat service instance
        format: Export format (json, csv)

    Returns:
        User's chat data in the requested format
    """
    user_id = get_principal_id(principal)
    # Get all user sessions
    sessions = await chat_service.get_active_sessions(user_id, limit=1000)

    export_data = {
        "user_id": user_id,
        "exported_at": datetime.now(datetime.UTC).isoformat(),
        "sessions": [],
    }

    # Get messages for each session
    for session in sessions:
        messages = await chat_service.get_messages(session.id, limit=10000)

        session_data = {
            "session_id": str(session.id),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "metadata": session.metadata,
            "message_count": session.message_count,
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in messages
            ],
        }
        export_data["sessions"].append(session_data)

    if format.lower() == "csv":
        # Convert to CSV format
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "session_id",
                "message_id",
                "role",
                "content",
                "message_created_at",
                "session_created_at",
            ]
        )

        # Write data
        for session in export_data["sessions"]:
            for message in session["messages"]:
                writer.writerow(
                    [
                        session["session_id"],
                        message["id"],
                        message["role"],
                        message["content"],
                        message["created_at"],
                        session["created_at"],
                    ]
                )

        content = output.getvalue()
        return StreamingResponse(
            io.StringIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=chat_export.csv"},
        )

    # Default JSON format
    return export_data


@router.delete("/data")
async def delete_all_chat_data(
    principal: Principal = require_principal_dep,
    chat_service: ChatService = get_chat_service_dep,
    confirm: bool = False,
):
    """Delete all chat data for the current user.

    Args:
        principal: Current authenticated principal
        chat_service: Chat service instance
        confirm: Confirmation flag

    Returns:
        Success message
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data deletion requires confirmation. Set confirm=true.",
        )

    user_id = get_principal_id(principal)
    # Get all user sessions
    sessions = await chat_service.get_active_sessions(user_id, limit=1000)

    deleted_sessions = 0
    deleted_messages = 0

    # Delete all sessions and their messages
    for session in sessions:
        # Get message count
        messages = await chat_service.get_messages(session.id, limit=10000)
        deleted_messages += len(messages)

        # End/delete the session (this should cascade delete messages)
        await chat_service.end_session(session.id)
        deleted_sessions += 1

    return {
        "message": "All chat data deleted successfully",
        "deleted_sessions": deleted_sessions,
        "deleted_messages": deleted_messages,
    }
