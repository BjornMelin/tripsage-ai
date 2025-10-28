"""Chat router for TripSage API.

This module provides endpoints for AI chat functionality using the unified
chat service for clean separation of concerns. It handles chat completions,
streaming responses, session management, and message operations.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.api.core.dependencies import (
    ChatServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage.api.limiting import limiter
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


EndpointCallable = TypeVar("EndpointCallable", bound=Callable[..., Awaitable[Any]])


def rate_limit(
    limit_value: str, **kwargs: Any
) -> Callable[[EndpointCallable], EndpointCallable]:
    """Typed wrapper around SlowAPI's limit decorator."""
    typed_limit = cast(
        Callable[..., Callable[[EndpointCallable], EndpointCallable]],
        cast(Any, limiter).limit,
    )
    return typed_limit(limit_value, **kwargs)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
@rate_limit("20/minute")
@trace_span(name="api.chat.completion")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def chat(
    chat_request: ChatRequest,
    request: Request,
    response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Handle chat requests with optional streaming and session persistence.

    Args:
        chat_request: Chat request with messages and options
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        ChatResponse: Chat response with assistant message.

    Raises:
        HTTPException: If chat request processing fails.
    """
    try:
        user_id = get_principal_id(principal)

        # Delegate to unified chat service
        return await chat_service.chat_completion(user_id, chat_request)

    except Exception as e:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        ) from e


@router.post("/stream")
@rate_limit("40/minute")
@trace_span(name="api.chat.stream")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
):
    r"""Stream chat responses as Server-Sent Events (SSE).

    Yields JSON lines formatted as SSE: "data: {json}\n\n" where json contains
    token deltas and a final message.

    Args:
        request: Chat request with messages and options.
        http_request: Raw HTTP request (required by SlowAPI for headers).
        http_response: Raw HTTP response (required by SlowAPI for headers).
        principal: Current authenticated principal.

    Yields:
        str: Server-Sent Events formatted strings with chat response data.

    Raises:
        HTTPException: If streaming setup or processing fails.
    """

    async def event_gen():  # type: ignore[no-redef]
        try:
            user_id = get_principal_id(principal)
            # System prompt aligned with non-streaming endpoint
            system_prompt = (
                "You are TripSage AI, an expert travel planning assistant. "
                "You help users plan trips, find flights and accommodations, "
                "create itineraries, and provide destination recommendations. "
                "Be helpful, informative, and personalized in your responses."
            )

            # Build message list
            mapped = [
                HumanMessage(content=m.content)
                for m in request.messages
                if str(m.role) == "user"
            ]
            # We currently ignore assistant/tool messages for simplicity

            # Initialize model
            from tripsage_core.config import get_settings

            settings = get_settings()
            model_name = getattr(request, "model", "gpt-4o-mini")
            temperature = getattr(request, "temperature", 0.7)
            max_tokens = getattr(request, "max_tokens", 4096)

            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=settings.openai_api_key,
                model_kwargs={"max_tokens": max_tokens},
                streaming=True,
            )

            # Send started event
            yield f"data: {json.dumps({'type': 'started', 'user': user_id})}\n\n"

            full = ""
            async for chunk in llm.astream(
                [SystemMessage(content=system_prompt), *mapped]
            ):
                part = getattr(chunk, "content", None)
                if part:
                    full += part
                    yield f"data: {json.dumps({'type': 'delta', 'content': part})}\n\n"
                # Keep the event loop responsive
                await asyncio.sleep(0)

            # Final event
            yield f"data: {json.dumps({'type': 'final', 'content': full})}\n\n"
            # Done marker
            yield "data: [DONE]\n\n"
        except Exception as e:  # pragma: no cover  # noqa: BLE001
            err = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err)}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
    }
    return StreamingResponse(
        event_gen(), headers=headers, media_type="text/event-stream"
    )


@router.post(
    "/sessions", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
@trace_span(name="api.chat.sessions.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_session(
    body: SessionCreateRequest,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Create a new chat session.

    Args:
        body: Session creation request body
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        chat_service: Unified chat service
    """
    try:
        user_id = get_principal_id(principal)

        from tripsage_core.services.business.chat_service import (
            ChatSessionCreateRequest,
        )

        # Convert API request to core request
        metadata: dict[str, Any] | None = body.metadata

        session_request = ChatSessionCreateRequest(
            title=body.title,
            metadata=metadata,
            trip_id=None,
        )

        session = await chat_service.create_session(user_id, session_request)
        return session.model_dump() if hasattr(session, "model_dump") else session

    except Exception as e:
        logger.exception("Session creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed",
        ) from e


@router.get("/sessions", response_model=list[dict[str, Any]])
@trace_span(name="api.chat.sessions.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def list_sessions(
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """List chat sessions for the current user.

    Args:
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        chat_service: Unified chat service

    Returns:
        list[dict]: List of user's chat sessions.

    Raises:
        HTTPException: If session listing fails.
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


@router.get("/sessions/{session_id}", response_model=dict[str, Any])
@trace_span(name="api.chat.sessions.get")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_session(
    session_id: UUID,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Get a specific chat session.

    Args:
        session_id: Session ID
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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


@router.get("/sessions/{session_id}/messages", response_model=list[dict[str, Any]])
@trace_span(name="api.chat.messages.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_session_messages(  # pylint: disable=too-many-positional-arguments
    session_id: UUID,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
    limit: int = 50,
):
    """Get messages from a chat session.

    Args:
        session_id: Session ID
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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


@router.post("/sessions/{session_id}/messages", response_model=dict[str, Any])
@trace_span(name="api.chat.messages.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_message(  # pylint: disable=too-many-positional-arguments
    session_id: UUID,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
    body: CreateMessageRequest,
):
    """Create a new message in a session.

    Args:
        session_id: Session ID
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        chat_service: Unified chat service
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
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    chat_service: ChatServiceDep,
):
    """Delete a chat session.

    Args:
        session_id: Session ID to delete
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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
