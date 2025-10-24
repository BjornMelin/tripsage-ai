"""Base agent integration for LangGraph orchestration.

This module provides the high-level ``BaseAgent`` class that bridges service
injection, LangGraph orchestration, and LangChain language models for the
TripSage platform.  The class encapsulates conversation state management,
memory synchronization, and graceful fallbacks when orchestration is
unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreTripSageError
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemoryService,
    UserContextResponse,
)
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

_DEFAULT_INSTRUCTIONS = (
    "You are TripSage, an expert travel planning assistant. Coordinate the "
    "specialized trip-planning agents, incorporate persisted user memories, "
    "and provide concise next steps for the traveller."
)


class BaseAgent:  # pylint: disable=too-many-instance-attributes
    """High-level orchestration-aware agent wrapper."""

    def __init__(
        self,
        name: str,
        services: AppServiceContainer,
        orchestrator: TripSageOrchestrator,
        *,
        instructions: str | None = None,
        llm: BaseChatModel | None = None,
        summary_interval: int = 10,
    ) -> None:
        """Initialize the agent with LangChain + LangGraph primitives.

        Args:
            name: Logical agent name.
            services: Application service container.
            orchestrator: TripSage LangGraph orchestrator singleton.
            instructions: Optional system instructions overriding defaults.
            llm: Optional pre-configured chat model instance.
            summary_interval: Number of messages between memory summaries.
        """
        self.name = name
        self.instructions = instructions or _DEFAULT_INSTRUCTIONS
        self.services = services
        self.llm: BaseChatModel = llm or self._create_llm()
        self._summary_interval = max(summary_interval, 0)
        self._last_summary_index = 0
        self._orchestrator: TripSageOrchestrator | None = orchestrator

        self.messages_history: list[dict[str, Any]] = []
        self.session_id = str(uuid4())
        self.session_data: dict[str, Any] = {}

    async def run(
        self,
        user_input: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a user input through LangGraph, falling back when needed."""
        resolved_context = context.copy() if context else {}
        resolved_user_id = user_id or cast(str, resolved_context.get("user_id", "anon"))
        resolved_session = session_id or resolved_context.get(
            "session_id", self.session_id
        )

        await self._hydrate_session(resolved_user_id)

        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": self._now(),
        }
        self.messages_history.append(user_message)

        try:
            orchestrator = await self._ensure_orchestrator()
            result = await orchestrator.process_message(
                user_id=resolved_user_id,
                message=user_input,
                session_id=resolved_session,
            )
            response_text = cast(str, result.get("response", ""))
            self.session_id = cast(str, result.get("session_id", resolved_session))

            assistant_message = {
                "role": "assistant",
                "content": response_text,
                "timestamp": self._now(),
                "agent": result.get("agent_used", self.name),
            }
            self.messages_history.append(assistant_message)

            if self._should_summarize():
                await self._persist_session_summary(resolved_user_id, resolved_context)

            return result
        except Exception as exc:
            logger.exception("Falling back to direct LLM run for %s", self.name)
            log_exception(exc)

            fallback_text = await self._generate_fallback_response(user_input)
            assistant_message = {
                "role": "assistant",
                "content": fallback_text,
                "timestamp": self._now(),
                "agent": self.name,
                "fallback": True,
            }
            self.messages_history.append(assistant_message)

            error_message = (
                str(exc)
                if isinstance(exc, CoreTripSageError)
                else "Orchestration unavailable; responded with fallback LLM."
            )

            return {
                "response": fallback_text,
                "session_id": self.session_id,
                "agent_used": self.name,
                "error": error_message,
            }

    async def stream_message(
        self,
        user_input: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Stream orchestration status followed by the final response."""
        yield {
            "type": "status",
            "data": {
                "status": "processing",
                "message": "Processing your request...",
            },
        }

        result = await self.run(
            user_input,
            user_id=user_id,
            session_id=session_id,
            context=context,
        )

        yield {"type": "response", "data": result}

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Return the in-memory conversation history."""
        return list(self.messages_history)

    def reset_session(self) -> None:
        """Reset session-scoped state."""
        self.session_id = str(uuid4())
        self.messages_history.clear()
        self.session_data.clear()
        self._last_summary_index = 0

    async def _ensure_orchestrator(self):
        """Lazy-load the LangGraph orchestrator."""
        if self._orchestrator is None:
            raise RuntimeError("TripSageOrchestrator is not configured")
        await self._orchestrator.initialize()
        return self._orchestrator

    async def _hydrate_session(self, user_id: str) -> None:
        """Populate session metadata from memory service when available."""
        if self.session_data.get("user_id") == user_id:
            return

        memory_service = self._get_memory_service()
        if not memory_service:
            self.session_data["user_id"] = user_id
            return

        try:
            context = await memory_service.get_user_context(user_id)
        except Exception:
            logger.exception("Failed to hydrate session context for %s", user_id)
            self.session_data["user_id"] = user_id
            return

        hydrated = self._context_to_session_data(context, user_id)
        self.session_data.update(hydrated)

    def _context_to_session_data(
        self, context: UserContextResponse, user_id: str
    ) -> dict[str, Any]:
        """Convert ``UserContextResponse`` into session metadata."""
        return {
            "user_id": user_id,
            "preferences": context.preferences,
            "past_trips": context.past_trips,
            "summary": context.summary,
            "insights": context.insights,
        }

    def _should_summarize(self) -> bool:
        """Return True when conversation should be summarized."""
        if self._summary_interval <= 0:
            return False
        if (
            len(self.messages_history) - self._last_summary_index
            < self._summary_interval
        ):
            return False
        self._last_summary_index = len(self.messages_history)
        return True

    async def _persist_session_summary(
        self, user_id: str, context: dict[str, Any]
    ) -> None:
        """Persist a conversation summary into memory service."""
        memory_service = self._get_memory_service()
        if not memory_service:
            return

        summary = await self._summarize_conversation()
        payload = ConversationMemoryRequest(
            messages=[
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.messages_history[-self._summary_interval :]
                if "content" in msg
            ],
            session_id=self.session_id,
            trip_id=context.get("trip_id"),
            metadata={
                "agent": self.name,
                "summary": summary,
                "type": "session_summary",
            },
        )
        try:
            await memory_service.add_conversation_memory(user_id, payload)
        except Exception:
            logger.exception("Failed to persist session summary for %s", user_id)

    async def _summarize_conversation(self) -> str:
        """Generate a concise summary of the latest conversation window."""
        recent_turns = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in self.messages_history[-self._summary_interval :]
            if "content" in msg
        )

        prompt = [
            SystemMessage(
                content=(
                    "Summarize the following travel-planning conversation in fewer "
                    "than 80 words, highlighting user preferences, constraints, and "
                    "open questions."
                )
            ),
            HumanMessage(content=recent_turns),
        ]
        response = await self.llm.ainvoke(prompt)
        return cast(str, getattr(response, "content", str(response)))

    async def _generate_fallback_response(self, user_input: str) -> str:
        """Call the underlying chat model directly when orchestration fails."""
        prompt_messages = self._build_conversation_prompt()
        prompt_messages.append(HumanMessage(content=user_input))

        response = await self.llm.ainvoke(prompt_messages)
        if isinstance(response, AIMessage):
            return cast(str, response.content)
        return cast(str, getattr(response, "content", str(response)))

    def _build_conversation_prompt(
        self,
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        """Construct chat messages from history with system instructions."""
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=self.instructions)
        ]
        for message in self.messages_history:
            role = message.get("role")
            content = cast(str, message.get("content", ""))
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def _create_llm(self) -> BaseChatModel:
        """Instantiate the default chat model."""
        settings = get_settings()
        api_key_raw = settings.openai_api_key
        secret_key = (
            api_key_raw
            if isinstance(api_key_raw, SecretStr) or api_key_raw is None
            else SecretStr(api_key_raw)
        )
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.model_temperature,
            api_key=secret_key,
        )

    def _get_memory_service(self) -> MemoryService | None:
        """Return the optional memory service from the DI container."""
        try:
            return self.services.get_optional_service(
                "memory_service",
                expected_type=MemoryService,
            )
        except TypeError:
            logger.warning("Memory service present but type mismatch; ignoring.")
            return None

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(UTC).isoformat()
