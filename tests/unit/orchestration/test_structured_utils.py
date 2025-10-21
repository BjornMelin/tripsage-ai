"""Tests for the structured output helper utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict

from tripsage.orchestration.utils.structured import StructuredExtractor, model_to_dict


class _SampleModel(BaseModel):
    """Simple schema for structured extraction tests."""

    model_config = ConfigDict(extra="forbid")

    value: str


@pytest.mark.asyncio
async def test_structured_extractor_calls_structured_llm():
    """Extractor should invoke structured LLM with composed messages."""
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(return_value=_SampleModel(value="ok"))

    llm = MagicMock()
    llm.with_structured_output.return_value = runnable

    extractor = StructuredExtractor(llm, _SampleModel)

    result = await extractor.extract_from_prompts(
        system_prompt="system role", user_prompt="user message"
    )

    assert isinstance(result, _SampleModel)
    runnable.ainvoke.assert_awaited_once()
    (messages,), _ = runnable.ainvoke.await_args
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert model_to_dict(result) == {"value": "ok"}


@pytest.mark.asyncio
async def test_structured_extractor_handles_errors(caplog):
    """Extractor should swallow errors and return None."""
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    llm = MagicMock()
    llm.with_structured_output.return_value = runnable

    extractor = StructuredExtractor(llm, _SampleModel)

    result = await extractor.extract_from_prompts(
        system_prompt="system role", user_prompt="user message"
    )

    assert result is None
    assert "Structured extraction failed" in caplog.text
