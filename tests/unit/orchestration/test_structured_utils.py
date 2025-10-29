"""Tests for StructuredExtractor and model_to_dict utilities."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from tripsage.orchestration.utils.structured import StructuredExtractor, model_to_dict


class _Schema(BaseModel):
    """Simple schema for extraction tests."""

    value: int


class _LLMStub:
    """LLM stub that returns a structured runnable with ainvoke()."""

    def with_structured_output(self, schema: Any) -> Any:
        """Return a structured runnable with ainvoke()."""

        class _Runnable:
            """Runnable that returns a structured output."""

            async def ainvoke(self, _messages: Any) -> Any:
                """Return a structured output."""
                return schema(value=42)

        return _Runnable()


@pytest.mark.asyncio
async def test_structured_extractor_success() -> None:
    """Extractor returns a Pydantic model instance on success."""
    extractor = StructuredExtractor(_LLMStub(), _Schema)  # type: ignore[arg-type]
    out = await extractor.extract_from_prompts(system_prompt="s", user_prompt="u")
    assert isinstance(out, _Schema)
    assert out.value == 42
    assert model_to_dict(out)["value"] == 42


class _BadRunnable:
    """Bad runnable that raises an exception."""

    async def ainvoke(self, _messages: Any) -> Any:
        """Raise an exception."""
        raise RuntimeError("llm failure")


class _BadLLMStub:
    """LLM stub that returns a bad runnable."""

    def with_structured_output(self, _schema: Any) -> Any:
        """Return a bad runnable."""
        return _BadRunnable()


@pytest.mark.asyncio
async def test_structured_extractor_error_returns_none() -> None:
    """On exception, extractor returns None and model_to_dict returns {}."""
    extractor = StructuredExtractor(_BadLLMStub(), _Schema)  # type: ignore[arg-type]
    out = await extractor.extract_from_prompts(system_prompt="s", user_prompt="u")
    assert out is None
    assert model_to_dict(out) == {}
