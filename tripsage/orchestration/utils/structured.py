"""Shared structured-output utilities for LangGraph orchestration."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from logging import Logger, LoggerAdapter
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel


class StructuredExtractor[T_Result: BaseModel]:
    """Helper that wraps ``with_structured_output`` for consistent extraction.

    The helper centralises error handling and message construction so individual
    agent nodes can focus on domain-specific prompts.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        schema: type[T_Result],
        *,
        logger: Logger | LoggerAdapter[Any] | None = None,
    ) -> None:
        """Initialise the extractor with an LLM and structured schema."""
        self._schema = schema
        self._structured_llm = llm.with_structured_output(schema)
        self._logger = logger or logging.getLogger(__name__)

    async def extract(self, messages: Sequence[BaseMessage]) -> T_Result | None:
        """Return structured output for the supplied chat messages."""
        try:
            result = await self._structured_llm.ainvoke(list(messages))
            return cast(T_Result, result)
        except Exception:
            self._logger.exception(
                "Structured extraction failed for schema %s", self._schema.__name__
            )
            return None

    async def extract_from_prompts(
        self, *, system_prompt: str, user_prompt: str
    ) -> T_Result | None:
        """Convenience wrapper that builds message pairs from raw prompts."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        return await self.extract(messages)


def model_to_dict(
    model: BaseModel | None, *, exclude_none: bool = True
) -> dict[str, object]:
    """Normalise structured extraction results into serialisable dictionaries."""
    if model is None:
        return {}
    return model.model_dump(exclude_none=exclude_none)


__all__ = ["StructuredExtractor", "model_to_dict"]
