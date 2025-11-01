"""Shared JSON-compatible typing aliases for infrastructure services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from uuid import UUID


type JSONPrimitive = str | int | float | bool | None | datetime | date | UUID
type JSONValue = JSONPrimitive | Mapping[str, JSONValue] | Sequence[JSONValue]
type JSONObject = dict[str, JSONValue]
type JSONObjectMapping = Mapping[str, JSONValue]
type JSONObjectSequence = Sequence[JSONObject]

type FilterValue = JSONValue | Mapping[str, JSONValue]
type FilterMapping = Mapping[str, FilterValue]
type MutableFilterMapping = dict[str, FilterValue]
