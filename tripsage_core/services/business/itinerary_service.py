"""Minimal, typed itinerary service built on the Supabase DatabaseService.

This service performs the following responsibilities:

* Persist itineraries and itinerary items using ``DatabaseService`` CRUD helpers.
* Provide the small set of operations required by the FastAPI routers.
* Offer lightweight validation (date ranges, ownership checks) and conflict
  detection for overlapping itinerary items.
* Return data in shapes compatible with ``tripsage_core.models.api.itinerary_models``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from enum import Enum
from itertools import pairwise
from typing import Any, Protocol, cast
from uuid import uuid4

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.models.api.itinerary_models import (
    ItineraryResponse as ApiItineraryResponse,
    ItinerarySearchResponse as ApiItinerarySearchResponse,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.base_models import PaginationMeta
from tripsage_core.services.infrastructure.database_service import DatabaseService


LOGGER = logging.getLogger(__name__)

ITINERARIES_TABLE = "itineraries"
ITINERARY_ITEMS_TABLE = "itinerary_items"


class SupportsModelDump(Protocol):
    """Protocol describing objects that expose ``model_dump`` (Pydantic v2)."""

    def model_dump(self, *, exclude_none: bool = False) -> dict[str, Any]:
        """Return a serialisable representation of the model."""
        ...


class ItineraryStatus(str, Enum):
    """Valid itinerary lifecycle states."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class ItineraryRecord(TripSageModel):
    """Internal itinerary representation persisted to Supabase."""

    id: str = Field(..., description="Itinerary identifier")
    user_id: str = Field(..., description="Owner identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Title")
    description: str | None = Field(None, description="User supplied description")
    start_date: date = Field(..., description="Start date (UTC)")
    end_date: date = Field(..., description="End date (UTC)")
    status: ItineraryStatus = Field(
        default=ItineraryStatus.DRAFT, description="Lifecycle status"
    )
    total_budget: float | None = Field(None, ge=0, description="Total budget")
    currency: str | None = Field(None, description="Currency code")
    destinations: list[str] = Field(
        default_factory=list, description="Destination identifiers"
    )
    tags: list[str] = Field(default_factory=list, description="Free-form tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator("end_date")
    @classmethod
    def _validate_date_range(cls, end: date, info: Any) -> date:
        """Ensure ``end_date`` is not before ``start_date``."""
        start: date | None = info.data.get("start_date")
        if start and end < start:
            raise ValueError("End date must be on or after start date")
        return end


class ItineraryItemRecord(TripSageModel):
    """Internal itinerary item representation."""

    id: str = Field(..., description="Itinerary item identifier")
    itinerary_id: str = Field(..., description="Parent itinerary identifier")
    item_type: str = Field(..., description="Item type label")
    title: str = Field(..., min_length=1, max_length=200, description="Item title")
    description: str | None = Field(None, description="Item description")
    item_date: date = Field(..., description="Item date")
    start_time: str | None = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Start time (HH:MM)",
    )
    end_time: str | None = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="End time (HH:MM)",
    )
    cost: float | None = Field(None, ge=0, description="Cost amount")
    currency: str | None = Field(None, description="Currency code")
    booking_reference: str | None = Field(None, description="Booking reference")
    notes: str | None = Field(None, description="Additional notes")
    is_flexible: bool = Field(False, description="Whether the timing is flexible")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator("end_time")
    @classmethod
    def _validate_time_order(cls, end_value: str | None, info: Any) -> str | None:
        """Ensure the end time, when provided, is not before the start time."""
        start_value: str | None = info.data.get("start_time")
        if start_value and end_value and end_value < start_value:
            raise ValueError("End time must be on or after start time")
        return end_value


class ItineraryService:
    """High-cohesion service that encapsulates itinerary operations."""

    def __init__(self, database_service: DatabaseService):
        """Initialise the service with its required infrastructure dependency."""
        self._db = database_service

    async def create_itinerary(
        self,
        user_id: str,
        create_request: SupportsModelDump | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Create a new itinerary owned by ``user_id``.

        Args:
            user_id: Identifier of the itinerary owner.
            create_request: Pydantic model or mapping describing the itinerary.

        Returns:
            Serialised itinerary dictionary ready for API responses.

        Raises:
            CoreValidationError: If the request payload is invalid.
            CoreServiceError: If persistence fails.
        """
        payload = self._normalize_payload(create_request)
        self._ensure_required_fields(payload, {"title", "start_date", "end_date"})
        itinerary = self._build_itinerary_record(user_id, payload)
        await self._insert_itinerary(itinerary)
        return await self.get_itinerary(user_id, itinerary.id)

    async def list_itineraries(self, user_id: str) -> list[dict[str, Any]]:
        """Return all itineraries owned by ``user_id``."""
        rows = await self._safe_select(
            ITINERARIES_TABLE, filters={"user_id": user_id}, order_by="-start_date"
        )
        itineraries = []
        for raw in rows:
            itinerary = self._build_itinerary_from_row(raw)
            items = await self._load_items_for_itinerary(itinerary.id)
            itineraries.append(self._serialize_itinerary(itinerary, items))
        return itineraries

    async def search_itineraries(
        self,
        user_id: str,
        search_request: SupportsModelDump | Mapping[str, Any],
    ) -> ApiItinerarySearchResponse:
        """Search itineraries for ``user_id`` with very light filtering.

        The search honours ``status`` and ``destinations`` filters, falling back to
        returning all itineraries when no filters are supplied.
        """
        payload = self._normalize_payload(search_request, exclude_none=True)
        filters: dict[str, Any] = {"user_id": user_id}
        if status := payload.get("status"):
            filters["status"] = str(status)
        if destinations := payload.get("destinations"):
            filters["destinations"] = destinations

        rows = await self._safe_select(
            ITINERARIES_TABLE,
            filters=filters,
            order_by="-start_date",
        )

        page = int(payload.get("page", 1))
        page_size = int(payload.get("page_size", len(rows) or 1))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_rows = rows[start_idx:end_idx]

        serialized: list[ApiItineraryResponse] = []
        for raw in paginated_rows:
            itinerary = self._build_itinerary_from_row(raw)
            items = await self._load_items_for_itinerary(itinerary.id)
            serialized.append(
                ApiItineraryResponse.model_validate(
                    self._serialize_itinerary(itinerary, items)
                )
            )

        total_items = len(rows)
        total_pages = (total_items + page_size - 1) // page_size
        pagination = PaginationMeta(
            page=page,
            per_page=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=end_idx < total_items,
            has_prev=start_idx > 0,
        )

        return ApiItinerarySearchResponse(
            success=True,
            message=None,
            data=serialized,
            pagination=pagination,
        )

    async def get_itinerary(self, user_id: str, itinerary_id: str) -> dict[str, Any]:
        """Fetch a single itinerary ensuring the caller owns it."""
        raw = await self._get_owned_itinerary_row(user_id, itinerary_id)
        itinerary = self._build_itinerary_from_row(raw)
        items = await self._load_items_for_itinerary(itinerary.id)
        return self._serialize_itinerary(itinerary, items)

    async def update_itinerary(
        self,
        user_id: str,
        itinerary_id: str,
        update_request: SupportsModelDump | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Update mutable itinerary fields."""
        payload = self._normalize_payload(update_request, exclude_none=True)
        if not payload:
            return await self.get_itinerary(user_id, itinerary_id)

        raw = await self._get_owned_itinerary_row(user_id, itinerary_id)
        itinerary = self._build_itinerary_from_row(raw)

        if "start_date" in payload or "end_date" in payload:
            start = payload.get("start_date", itinerary.start_date)
            end = payload.get("end_date", itinerary.end_date)
            self._assert_valid_date_range(start, end)

        payload["updated_at"] = datetime.now(UTC).isoformat()
        await self._safe_update(
            ITINERARIES_TABLE, data=payload, filters={"id": itinerary_id}
        )
        return await self.get_itinerary(user_id, itinerary_id)

    async def delete_itinerary(self, user_id: str, itinerary_id: str) -> None:
        """Delete an itinerary and its items."""
        await self._get_owned_itinerary_row(user_id, itinerary_id)
        await self._safe_delete(ITINERARY_ITEMS_TABLE, {"itinerary_id": itinerary_id})
        await self._safe_delete(ITINERARIES_TABLE, {"id": itinerary_id})

    async def add_item_to_itinerary(
        self,
        user_id: str,
        itinerary_id: str,
        item_request: SupportsModelDump | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Add an item to an owned itinerary."""
        await self._get_owned_itinerary_row(user_id, itinerary_id)
        payload = self._normalize_payload(item_request)
        self._ensure_required_fields(payload, {"item_type", "title", "item_date"})
        now = datetime.now(UTC)
        item = ItineraryItemRecord(
            id=str(uuid4()),
            itinerary_id=itinerary_id,
            item_type=str(payload["item_type"]),
            title=payload["title"],
            description=payload.get("description"),
            item_date=payload["item_date"],
            start_time=self._extract_time(payload.get("time_slot"), "start_time"),
            end_time=self._extract_time(payload.get("time_slot"), "end_time"),
            cost=payload.get("cost"),
            currency=payload.get("currency"),
            booking_reference=payload.get("booking_reference"),
            notes=payload.get("notes"),
            is_flexible=bool(payload.get("is_flexible", False)),
            created_at=now,
            updated_at=now,
        )
        await self._insert_item(item, user_id)
        return self._serialize_item(item)

    async def get_item(
        self, user_id: str, itinerary_id: str, item_id: str
    ) -> dict[str, Any]:
        """Return an itinerary item ensuring the itinerary is owned by the caller."""
        await self._get_owned_itinerary_row(user_id, itinerary_id)
        row = await self._safe_select(
            ITINERARY_ITEMS_TABLE,
            filters={"id": item_id, "itinerary_id": itinerary_id},
            limit=1,
        )
        if not row:
            raise CoreResourceNotFoundError(
                message="Itinerary item not found", code="ITEM_NOT_FOUND"
            )
        return self._serialize_item(self._build_item_from_row(row[0]))

    async def update_item(
        self,
        user_id: str,
        itinerary_id: str,
        item_id: str,
        update_request: SupportsModelDump | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Update an itinerary item owned by the user."""
        await self._get_owned_itinerary_row(user_id, itinerary_id)
        payload = self._normalize_payload(update_request, exclude_none=True)
        if not payload:
            return await self.get_item(user_id, itinerary_id, item_id)

        if "time_slot" in payload:
            time_slot = payload.pop("time_slot")
            payload["start_time"] = self._extract_time(time_slot, "start_time")
            payload["end_time"] = self._extract_time(time_slot, "end_time")

        payload["updated_at"] = datetime.now(UTC).isoformat()
        await self._safe_update(
            ITINERARY_ITEMS_TABLE,
            data=payload,
            filters={"id": item_id, "itinerary_id": itinerary_id},
        )
        return await self.get_item(user_id, itinerary_id, item_id)

    async def delete_item(self, user_id: str, itinerary_id: str, item_id: str) -> None:
        """Delete an itinerary item when the user owns the itinerary."""
        await self._get_owned_itinerary_row(user_id, itinerary_id)
        await self._safe_delete(
            ITINERARY_ITEMS_TABLE, {"id": item_id, "itinerary_id": itinerary_id}
        )

    async def check_conflicts(self, user_id: str, itinerary_id: str) -> dict[str, Any]:
        """Detect simple overlapping time conflicts for an itinerary."""
        itinerary = await self.get_itinerary(user_id, itinerary_id)
        conflicts: list[dict[str, Any]] = []
        items_by_date: dict[date, list[dict[str, Any]]] = {}
        for item in itinerary["items"]:
            items_by_date.setdefault(item["item_date"], []).append(item)

        for item_date, items in items_by_date.items():
            sorted_items = sorted(
                (i for i in items if i.get("start_time") and i.get("end_time")),
                key=lambda x: cast(str, x["start_time"]),
            )
            for first, second in pairwise(sorted_items):
                if cast(str, second["start_time"]) < cast(str, first["end_time"]):
                    conflicts.append(
                        {
                            "date": item_date.isoformat(),
                            "items": [first["id"], second["id"]],
                            "reason": "time_overlap",
                        }
                    )

        return {"has_conflicts": bool(conflicts), "conflicts": conflicts}

    async def optimize_itinerary(
        self,
        user_id: str,
        optimize_request: SupportsModelDump | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return a no-op optimisation result retaining the existing itinerary."""
        payload = self._normalize_payload(optimize_request)
        itinerary_id_value = payload.get("itinerary_id")
        if not isinstance(itinerary_id_value, str) or not itinerary_id_value:
            raise CoreValidationError(
                message="itinerary_id is required",
                code="MISSING_ITINERARY_ID",
            )
        itinerary = await self.get_itinerary(user_id, itinerary_id_value)
        return {
            "original_itinerary": itinerary,
            "optimized_itinerary": itinerary,
            "changes": [],
            "optimization_score": 0.0,
        }

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _normalize_payload(
        data: SupportsModelDump | Mapping[str, Any],
        *,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """Convert request objects to dictionaries."""
        if hasattr(data, "model_dump"):
            return cast(SupportsModelDump, data).model_dump(exclude_none=exclude_none)
        return {
            key: value
            for key, value in cast(Mapping[str, Any], data).items()
            if not (exclude_none and value is None)
        }

    @staticmethod
    def _ensure_required_fields(payload: Mapping[str, Any], required: set[str]) -> None:
        """Assert that required fields are present."""
        missing = [field for field in required if field not in payload]
        if missing:
            raise CoreValidationError(
                message=f"Missing required fields: {', '.join(sorted(missing))}",
                code="MISSING_FIELDS",
            )

    @staticmethod
    def _assert_valid_date_range(start: date, end: date) -> None:
        """Validate date bounds."""
        if end < start:
            raise CoreValidationError(
                message="End date must be on or after start date",
                code="INVALID_DATE_RANGE",
            )

    def _build_itinerary_record(
        self, user_id: str, payload: Mapping[str, Any]
    ) -> ItineraryRecord:
        """Construct an itinerary record from payload data."""
        start_date = cast(date, payload["start_date"])
        end_date = cast(date, payload["end_date"])
        self._assert_valid_date_range(start_date, end_date)
        now = datetime.now(UTC)
        return ItineraryRecord(
            id=str(uuid4()),
            user_id=user_id,
            title=cast(str, payload["title"]),
            description=cast(str | None, payload.get("description")),
            start_date=start_date,
            end_date=end_date,
            status=ItineraryStatus(payload.get("status", ItineraryStatus.DRAFT)),
            total_budget=cast(float | None, payload.get("total_budget")),
            currency=cast(str | None, payload.get("currency")),
            destinations=list(payload.get("destinations", [])),
            tags=list(payload.get("tags", [])),
            created_at=now,
            updated_at=now,
        )

    async def _insert_itinerary(self, itinerary: ItineraryRecord) -> None:
        """Persist an itinerary record."""
        await self._safe_insert(
            ITINERARIES_TABLE,
            itinerary.model_dump(mode="json", exclude_none=True),
            user_id=itinerary.user_id,
        )

    async def _insert_item(
        self, item: ItineraryItemRecord, user_id: str | None
    ) -> None:
        """Persist an itinerary item record."""
        await self._safe_insert(
            ITINERARY_ITEMS_TABLE,
            item.model_dump(mode="json", exclude_none=True),
            user_id=user_id,
        )

    def _serialize_itinerary(
        self, itinerary: ItineraryRecord, items: list[ItineraryItemRecord]
    ) -> dict[str, Any]:
        """Convert itinerary data to an API-friendly payload."""
        return {
            "id": itinerary.id,
            "title": itinerary.title,
            "description": itinerary.description,
            "start_date": itinerary.start_date,
            "end_date": itinerary.end_date,
            "status": itinerary.status.value,
            "total_budget": itinerary.total_budget,
            "currency": itinerary.currency,
            "tags": itinerary.tags,
            "items": [self._serialize_item(item) for item in items],
            "created_at": itinerary.created_at.isoformat(),
            "updated_at": itinerary.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_item(item: ItineraryItemRecord) -> dict[str, Any]:
        """Convert an itinerary item into a response dictionary."""
        return {
            "id": item.id,
            "item_type": item.item_type,
            "title": item.title,
            "description": item.description,
            "item_date": item.item_date,
            "start_time": item.start_time,
            "end_time": item.end_time,
            "cost": item.cost,
            "currency": item.currency,
            "booking_reference": item.booking_reference,
            "notes": item.notes,
            "is_flexible": item.is_flexible,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    async def _load_items_for_itinerary(
        self, itinerary_id: str
    ) -> list[ItineraryItemRecord]:
        """Load itinerary items ordered by date and start time."""
        rows = await self._safe_select(
            ITINERARY_ITEMS_TABLE,
            filters={"itinerary_id": itinerary_id},
            order_by="item_date",
        )
        return [self._build_item_from_row(row) for row in rows]

    @staticmethod
    def _build_itinerary_from_row(row: Mapping[str, Any]) -> ItineraryRecord:
        """Instantiate an itinerary record from a database row."""
        return ItineraryRecord.model_validate(row)

    @staticmethod
    def _build_item_from_row(row: Mapping[str, Any]) -> ItineraryItemRecord:
        """Instantiate an itinerary item record from a database row."""
        return ItineraryItemRecord.model_validate(row)

    async def _get_owned_itinerary_row(
        self, user_id: str, itinerary_id: str
    ) -> Mapping[str, Any]:
        """Fetch an itinerary row ensuring ownership."""
        rows = await self._safe_select(
            ITINERARIES_TABLE,
            filters={"id": itinerary_id, "user_id": user_id},
            limit=1,
        )
        if not rows:
            raise CoreResourceNotFoundError(
                message="Itinerary not found",
                code="ITINERARY_NOT_FOUND",
            )
        return rows[0]

    @staticmethod
    def _extract_time(
        slot: Mapping[str, Any] | None,
        field_name: str,
    ) -> str | None:
        """Extract a HH:MM string from a nested time slot mapping."""
        if slot is None:
            return None
        value = slot.get(field_name)
        if isinstance(value, time):
            return value.strftime("%H:%M")
        if isinstance(value, str):
            return value
        return None

    # --------------- Safe database wrappers ------------------------------ #

    async def _safe_insert(
        self,
        table: str,
        data: dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """Insert a record into the database."""
        try:
            await self._db.insert(table, data, user_id=user_id)
        except CoreDatabaseError as exc:
            LOGGER.exception("Insert failed for table %s", table)
            raise CoreServiceError(
                message=f"Failed to insert into {table}",
                code="INSERT_FAILED",
            ) from exc

    async def _safe_select(
        self,
        table: str,
        *,
        filters: Mapping[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Mapping[str, Any]]:
        """Select records from the database."""
        try:
            return cast(
                list[Mapping[str, Any]],
                await self._db.select(
                    table,
                    filters=dict(filters) if filters else None,
                    order_by=order_by,
                    limit=limit,
                ),
            )
        except CoreDatabaseError as exc:
            LOGGER.exception("Select failed for table %s", table)
            raise CoreServiceError(
                message=f"Failed to load data from {table}",
                code="SELECT_FAILED",
            ) from exc

    async def _safe_update(
        self,
        table: str,
        *,
        data: Mapping[str, Any],
        filters: Mapping[str, Any],
    ) -> None:
        """Update a record in the database."""
        try:
            await self._db.update(table, dict(data), dict(filters))
        except CoreDatabaseError as exc:
            LOGGER.exception("Update failed for table %s", table)
            raise CoreServiceError(
                message=f"Failed to update {table}",
                code="UPDATE_FAILED",
            ) from exc

    async def _safe_delete(
        self,
        table: str,
        filters: Mapping[str, Any],
    ) -> None:
        """Delete a record from the database."""
        try:
            await self._db.delete(table, dict(filters))
        except CoreDatabaseError as exc:
            LOGGER.exception("Delete failed for table %s", table)
            raise CoreServiceError(
                message=f"Failed to delete from {table}",
                code="DELETE_FAILED",
            ) from exc


async def get_itinerary_service() -> ItineraryService:
    """Factory for dependency injection within FastAPI routers."""
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    database_service = await get_database_service()
    return ItineraryService(database_service)
