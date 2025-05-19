"""Test GoogleCalendarMCPWrapper following the same pattern as other wrapper tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.clients.calendar import CalendarMCPClient
from tripsage.mcp_abstraction.wrappers.google_calendar_wrapper import (
    GoogleCalendarMCPWrapper,
)


@pytest.fixture
def mock_calendar_client():
    """Mock for CalendarMCPClient."""
    mock = MagicMock(spec=CalendarMCPClient)

    # Set up return values for all expected methods
    mock.list_calendars = AsyncMock(
        return_value=[{"id": "cal1", "summary": "Test Calendar"}]
    )
    mock.create_event = AsyncMock(
        return_value={"id": "event1", "summary": "Test Event"}
    )
    mock.list_events = AsyncMock(
        return_value=[{"id": "event1", "summary": "Test Event"}]
    )
    mock.search_events = AsyncMock(
        return_value=[{"id": "event1", "summary": "Test Event"}]
    )
    mock.update_event = AsyncMock(
        return_value={"id": "event1", "summary": "Updated Event"}
    )
    mock.delete_event = AsyncMock(return_value={"success": True})
    mock.create_itinerary_events = AsyncMock(
        return_value=[{"id": "event1", "summary": "Itinerary Event"}]
    )

    return mock


@pytest.fixture
def calendar_wrapper(mock_calendar_client):
    """Create GoogleCalendarMCPWrapper with mocked client."""
    with patch(
        "tripsage.mcp_abstraction.wrappers.google_calendar_wrapper.CalendarMCPClient",
        return_value=mock_calendar_client,
    ):
        return GoogleCalendarMCPWrapper()


class TestGoogleCalendarMCPWrapper:
    """Test suite for GoogleCalendarMCPWrapper."""

    def test_initialization(self, calendar_wrapper, mock_calendar_client):
        """Test that wrapper initializes properly."""
        assert calendar_wrapper.client == mock_calendar_client
        assert calendar_wrapper.method_map is not None
        assert len(calendar_wrapper.method_map) > 0

    def test_method_map_building(self, calendar_wrapper):
        """Test that method map is built correctly with all aliases."""
        expected_mappings = {
            # List calendars aliases
            "list_calendars": "list_calendars",
            "get_calendars": "list_calendars",
            # Create event aliases
            "create_event": "create_event",
            "add_event": "create_event",
            "new_event": "create_event",
            # List events aliases
            "list_events": "list_events",
            "get_events": "list_events",
            # Search events aliases
            "search_events": "search_events",
            "find_events": "search_events",
            "query_events": "search_events",
            # Update event aliases
            "update_event": "update_event",
            "edit_event": "update_event",
            "modify_event": "update_event",
            # Delete event aliases
            "delete_event": "delete_event",
            "remove_event": "delete_event",
            # Create itinerary aliases
            "create_itinerary_events": "create_itinerary_events",
            "add_itinerary": "create_itinerary_events",
            "schedule_itinerary": "create_itinerary_events",
        }

        for alias, method in expected_mappings.items():
            assert alias in calendar_wrapper.method_map
            assert calendar_wrapper.method_map[alias] == method

    @pytest.mark.asyncio
    async def test_list_calendars(self, calendar_wrapper, mock_calendar_client):
        """Test list calendars method invocation."""
        result = await calendar_wrapper.invoke("list_calendars")

        mock_calendar_client.list_calendars.assert_called_once_with()
        assert result == [{"id": "cal1", "summary": "Test Calendar"}]

    @pytest.mark.asyncio
    async def test_create_event(self, calendar_wrapper, mock_calendar_client):
        """Test create event method invocation."""
        result = await calendar_wrapper.invoke(
            "create_event",
            calendar_id="cal1",
            summary="Test Event",
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
        )

        mock_calendar_client.create_event.assert_called_once_with(
            calendar_id="cal1",
            summary="Test Event",
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
        )
        assert result == {"id": "event1", "summary": "Test Event"}

    @pytest.mark.asyncio
    async def test_list_events(self, calendar_wrapper, mock_calendar_client):
        """Test list events method invocation."""
        result = await calendar_wrapper.invoke("list_events", calendar_id="cal1")

        mock_calendar_client.list_events.assert_called_once_with(calendar_id="cal1")
        assert result == [{"id": "event1", "summary": "Test Event"}]

    @pytest.mark.asyncio
    async def test_search_events(self, calendar_wrapper, mock_calendar_client):
        """Test search events method invocation."""
        result = await calendar_wrapper.invoke(
            "search_events", calendar_id="cal1", query="Test"
        )

        mock_calendar_client.search_events.assert_called_once_with(
            calendar_id="cal1", query="Test"
        )
        assert result == [{"id": "event1", "summary": "Test Event"}]

    @pytest.mark.asyncio
    async def test_update_event(self, calendar_wrapper, mock_calendar_client):
        """Test update event method invocation."""
        result = await calendar_wrapper.invoke(
            "update_event",
            calendar_id="cal1",
            event_id="event1",
            summary="Updated Event",
        )

        mock_calendar_client.update_event.assert_called_once_with(
            calendar_id="cal1", event_id="event1", summary="Updated Event"
        )
        assert result == {"id": "event1", "summary": "Updated Event"}

    @pytest.mark.asyncio
    async def test_delete_event(self, calendar_wrapper, mock_calendar_client):
        """Test delete event method invocation."""
        result = await calendar_wrapper.invoke(
            "delete_event", calendar_id="cal1", event_id="event1"
        )

        mock_calendar_client.delete_event.assert_called_once_with(
            calendar_id="cal1", event_id="event1"
        )
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_create_itinerary_events(
        self, calendar_wrapper, mock_calendar_client
    ):
        """Test create itinerary events method invocation."""
        result = await calendar_wrapper.invoke(
            "create_itinerary_events",
            calendar_id="cal1",
            events=[
                {
                    "summary": "Itinerary Event",
                    "start": "2024-01-15T10:00:00",
                    "end": "2024-01-15T11:00:00",
                }
            ],
        )

        mock_calendar_client.create_itinerary_events.assert_called_once_with(
            calendar_id="cal1",
            events=[
                {
                    "summary": "Itinerary Event",
                    "start": "2024-01-15T10:00:00",
                    "end": "2024-01-15T11:00:00",
                }
            ],
        )
        assert result == [{"id": "event1", "summary": "Itinerary Event"}]

    @pytest.mark.asyncio
    async def test_method_aliases(self, calendar_wrapper):
        """Test that all method aliases work correctly."""
        # Test aliases that should call list_calendars
        for alias in ["get_calendars"]:
            result = await calendar_wrapper.invoke(alias)
            assert result == [{"id": "cal1", "summary": "Test Calendar"}]

        # Test aliases that should call create_event
        for alias in ["add_event", "new_event"]:
            result = await calendar_wrapper.invoke(
                alias,
                calendar_id="cal1",
                summary="Test Event",
                start="2024-01-15T10:00:00",
                end="2024-01-15T11:00:00",
            )
            assert result == {"id": "event1", "summary": "Test Event"}

        # Test aliases that should call list_events
        for alias in ["get_events"]:
            result = await calendar_wrapper.invoke(alias, calendar_id="cal1")
            assert result == [{"id": "event1", "summary": "Test Event"}]

        # Test aliases that should call search_events
        for alias in ["find_events", "query_events"]:
            result = await calendar_wrapper.invoke(
                alias, calendar_id="cal1", query="Test"
            )
            assert result == [{"id": "event1", "summary": "Test Event"}]

        # Test aliases that should call update_event
        for alias in ["edit_event", "modify_event"]:
            result = await calendar_wrapper.invoke(
                alias, calendar_id="cal1", event_id="event1", summary="Updated Event"
            )
            assert result == {"id": "event1", "summary": "Updated Event"}

        # Test aliases that should call delete_event
        for alias in ["remove_event"]:
            result = await calendar_wrapper.invoke(
                alias, calendar_id="cal1", event_id="event1"
            )
            assert result == {"success": True}

        # Test aliases that should call create_itinerary_events
        for alias in ["add_itinerary", "schedule_itinerary"]:
            result = await calendar_wrapper.invoke(
                alias,
                calendar_id="cal1",
                events=[
                    {
                        "summary": "Itinerary Event",
                        "start": "2024-01-15T10:00:00",
                        "end": "2024-01-15T11:00:00",
                    }
                ],
            )
            assert result == [{"id": "event1", "summary": "Itinerary Event"}]

    @pytest.mark.asyncio
    async def test_error_handling(self, calendar_wrapper, mock_calendar_client):
        """Test error handling for invalid method names."""
        with pytest.raises(ValueError, match="Unknown method: invalid_method"):
            await calendar_wrapper.invoke("invalid_method")

    @pytest.mark.asyncio
    async def test_async_compatibility(self, calendar_wrapper):
        """Test that all wrapper methods are async-compatible."""
        import inspect

        # Test that invoke returns a coroutine
        result = calendar_wrapper.invoke("list_calendars")
        assert inspect.iscoroutine(result)

        # Clean up the coroutine
        try:
            await result
        except Exception:
            pass

    def test_get_available_methods(self, calendar_wrapper):
        """Test that get_available_methods returns all unique methods."""
        methods = calendar_wrapper.get_available_methods()

        # Check that all standardized methods are present
        expected_methods = {
            "list_calendars",
            "create_event",
            "list_events",
            "search_events",
            "update_event",
            "delete_event",
            "create_itinerary_events",
        }

        assert expected_methods.issubset(set(methods))
        assert len(methods) == len(set(methods))  # No duplicates

    @pytest.mark.asyncio
    async def test_parameter_passing(self, calendar_wrapper, mock_calendar_client):
        """Test that all parameters are correctly passed to the underlying client."""
        # Test with various parameter combinations
        await calendar_wrapper.invoke(
            "create_event",
            calendar_id="cal1",
            summary="Test Event",
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
            description="Test Description",
            location="Test Location",
            reminders=[{"method": "email", "minutes": 30}],
        )

        # Verify all parameters were passed through
        mock_calendar_client.create_event.assert_called_with(
            calendar_id="cal1",
            summary="Test Event",
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
            description="Test Description",
            location="Test Location",
            reminders=[{"method": "email", "minutes": 30}],
        )

    @pytest.mark.asyncio
    async def test_client_initialization_error(self):
        """Test handling of client initialization errors."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.google_calendar_wrapper.CalendarMCPClient",
            side_effect=Exception("Initialization failed"),
        ):
            with pytest.raises(Exception, match="Initialization failed"):
                GoogleCalendarMCPWrapper()
