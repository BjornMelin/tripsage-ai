"""Minimal provider calls for BYOK-backed LLM usage.

This module intentionally avoids heavy wrappers. It provides small helper
functions that normalize calls across providers to reduce duplication (rationale:
cut repeated boilerplate while keeping direct library usage at call sites).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tripsage_core.services.infrastructure.database_service import DatabaseService


def _messages_to_openai(messages: Sequence[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert generic messages into OpenAI schema.

    Args:
        messages: Sequence of role/content dicts.

    Returns:
        A list of OpenAI-compatible message dicts.
    """
    out: list[dict[str, str]] = []
    for m in messages:
        role = str(m.get("role", "user"))
        content = str(m.get("content", ""))
        out.append({"role": role, "content": content})
    return out


async def call_openai(
    *,
    db: DatabaseService,
    user_id: str,
    model: str,
    messages: Sequence[dict[str, Any]],
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Call OpenAI Chat Completions with the user's BYOK.

    Args:
        db: Database service used to fetch the user's provider key.
        user_id: Auth user id.
        model: OpenAI model name.
        messages: Chat messages.
        max_tokens: Optional max tokens.
        temperature: Optional sampling temperature.

    Returns:
        Assistant content string.
    """
    from openai import OpenAI  # library-first direct use

    api_key = await db.fetch_user_service_api_key(user_id, "openai")
    if not api_key:
        raise ValueError("Missing OpenAI API key for user")

    client = OpenAI(api_key=api_key)
    from typing import cast

    kwargs: dict[str, Any] = {"model": model, "messages": _messages_to_openai(messages)}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    resp = cast(Any, client).chat.completions.create(**kwargs)
    return str(resp.choices[0].message.content or "")


async def call_openrouter(
    *,
    db: DatabaseService,
    user_id: str,
    model: str,
    messages: Sequence[dict[str, Any]],
    max_tokens: int | None = None,
    temperature: float | None = None,
    referer: str | None = None,
    title: str | None = None,
) -> str:
    """Call OpenRouter via OpenAI SDK (OpenAI-compatible base URL).

    Args:
        db: Database service.
        user_id: Auth user id.
        model: Target model on OpenRouter (e.g. "openai/gpt-4o").
        messages: Chat messages.
        max_tokens: Optional max tokens.
        temperature: Optional sampling temperature.
        referer: Optional OpenRouter attribution header.
        title: Optional OpenRouter attribution header.

    Returns:
        Assistant content string.
    """
    from openai import OpenAI

    api_key = await db.fetch_user_service_api_key(user_id, "openrouter")
    if not api_key:
        raise ValueError("Missing OpenRouter API key for user")

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    extra_headers: dict[str, str] = {}
    if referer:
        extra_headers["HTTP-Referer"] = referer
    if title:
        extra_headers["X-Title"] = title

    from typing import cast

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": _messages_to_openai(messages),
    }
    if extra_headers:
        kwargs["extra_headers"] = extra_headers
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    resp = cast(Any, client).chat.completions.create(**kwargs)
    return str(resp.choices[0].message.content or "")


async def call_anthropic(
    *,
    db: DatabaseService,
    user_id: str,
    model: str,
    messages: Sequence[dict[str, Any]],
    max_tokens: int = 1024,
    temperature: float | None = None,
) -> str:
    """Call Anthropic Messages API using official SDK.

    Args:
        db: Database service.
        user_id: Auth user id.
        model: Anthropic model id.
        messages: Chat messages.
        max_tokens: Generation cap.
        temperature: Optional sampling temperature.

    Returns:
        Assistant content string.
    """
    from typing import cast

    from anthropic import Anthropic  # type: ignore[reportMissingImports]

    api_key = await db.fetch_user_service_api_key(user_id, "anthropic")
    if not api_key:
        raise ValueError("Missing Anthropic API key for user")

    client = cast(Any, Anthropic(api_key=api_key))
    # Anthropic expects messages list (user/assistant roles); content is str
    ant_msgs: list[dict[str, str]] = []
    for m in messages:
        role = str(m.get("role", "user"))
        content = str(m.get("content", ""))
        ant_msgs.append({"role": role, "content": content})

    msg = client.messages.create(
        model=model,
        messages=ant_msgs,
        max_tokens=max_tokens,
        **({"temperature": temperature} if temperature is not None else {}),
    )
    # message.content is a list of content blocks; join text blocks
    chunks: list[str] = []
    for c in getattr(msg, "content", []) or []:
        text = getattr(c, "text", None)
        if isinstance(text, str):
            chunks.append(text)
    return "".join(chunks)


async def call_xai(
    *,
    db: DatabaseService,
    user_id: str,
    model: str,
    messages: Sequence[dict[str, Any]],
    base_url: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Call xAI using OpenAI-compatible client if available.

    Args:
        db: Database service.
        user_id: Auth user id.
        model: xAI model identifier.
        messages: Chat messages.
        base_url: API endpoint (defaults to public xAI endpoint if provided by env).
        max_tokens: Optional cap.
        temperature: Optional sampling.

    Returns:
        Assistant content string.
    """
    from os import getenv

    from openai import OpenAI

    api_key = await db.fetch_user_service_api_key(user_id, "xai")
    if not api_key:
        raise ValueError("Missing xAI API key for user")

    resolved_base = base_url or getenv("XAI_API_BASE") or "https://api.x.ai/v1"
    client = OpenAI(api_key=api_key, base_url=resolved_base)
    from typing import cast

    kwargs: dict[str, Any] = {"model": model, "messages": _messages_to_openai(messages)}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    resp = cast(Any, client).chat.completions.create(**kwargs)
    return str(resp.choices[0].message.content or "")
