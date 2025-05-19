"""Tests for MCP Service Registry."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.service_registry import (
    MCPServiceInfo,
    MCPServiceRegistry,
    ServiceStatus,
)


class TestMCPServiceRegistry:
    """Test suite for MCPServiceRegistry"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock MCP settings"""
        with patch("tripsage.mcp_abstraction.service_registry.MCPSettings") as mock:
            settings = MagicMock()
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def mock_registry(self):
        """Create mock client registry"""
        with patch(
            "tripsage.mcp_abstraction.service_registry.MCPClientRegistry"
        ) as mock:
            registry = MagicMock()
            mock.return_value = registry
            yield registry

    @pytest.fixture
    async def service_registry(self, mock_settings, mock_registry):
        """Create service registry instance"""
        registry = MCPServiceRegistry(mock_settings)
        yield registry
        # Clean up
        if registry._health_check_task:
            registry._health_check_task.cancel()
            try:
                await registry._health_check_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_initialize(self, service_registry):
        """Test registry initialization"""
        with patch.object(
            service_registry, "discover_services", new_callable=AsyncMock
        ):
            await service_registry.initialize()

            assert service_registry._health_check_task is not None
            service_registry.discover_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown(self, service_registry):
        """Test registry shutdown"""
        mock_task = MagicMock()
        service_registry._health_check_task = mock_task

        await service_registry.shutdown()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_service(self, service_registry):
        """Test registering a new service"""
        with patch.object(service_registry, "health_check", new_callable=AsyncMock):
            service = await service_registry.register_service(
                "test_service", "TestWrapper"
            )

            assert service.name == "test_service"
            assert service.wrapper_class == "TestWrapper"
            assert service.status == ServiceStatus.UNKNOWN
            assert "test_service" in service_registry.services
            service_registry.health_check.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    async def test_register_service_already_exists(self, service_registry):
        """Test registering a service that already exists"""
        existing = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = existing

        with patch.object(service_registry, "health_check", new_callable=AsyncMock):
            service = await service_registry.register_service(
                "test_service", "TestWrapper"
            )

            assert service == existing
            service_registry.health_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_unregister_service(self, service_registry):
        """Test unregistering a service"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        result = await service_registry.unregister_service("test_service")

        assert result is True
        assert "test_service" not in service_registry.services

    @pytest.mark.asyncio
    async def test_unregister_service_not_found(self, service_registry):
        """Test unregistering a non-existent service"""
        result = await service_registry.unregister_service("unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_discover_services(self, service_registry):
        """Test service discovery"""
        mock_wrapper = MagicMock()
        mock_wrapper.__name__ = "MockWrapper"
        service_registry._registry.registry = {"mock_service": mock_wrapper}

        with patch.object(service_registry, "register_service", new_callable=AsyncMock):
            discovered = await service_registry.discover_services()

            assert discovered == ["mock_service"]
            service_registry.register_service.assert_called_once_with(
                "mock_service", "MockWrapper"
            )

    @pytest.mark.asyncio
    async def test_health_check_success(self, service_registry):
        """Test successful health check"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        mock_wrapper = MagicMock()
        mock_wrapper.ping = AsyncMock()
        service_registry._registry.get_wrapper.return_value = mock_wrapper

        result = await service_registry.health_check("test_service")

        assert result is True
        assert service.status == ServiceStatus.HEALTHY
        assert service.error_count == 0
        assert service.last_health_check is not None
        mock_wrapper.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_list_tools_fallback(self, service_registry):
        """Test health check with list_tools fallback"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        mock_wrapper = MagicMock()
        del mock_wrapper.ping  # No ping method
        mock_wrapper.list_tools = AsyncMock()
        service_registry._registry.get_wrapper.return_value = mock_wrapper

        result = await service_registry.health_check("test_service")

        assert result is True
        assert service.status == ServiceStatus.HEALTHY
        mock_wrapper.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_registry_fallback(self, service_registry):
        """Test health check with registry fallback"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        mock_wrapper = MagicMock()
        del mock_wrapper.ping  # No ping method
        del mock_wrapper.list_tools  # No list_tools method
        service_registry._registry.get_wrapper.return_value = mock_wrapper
        service_registry._registry.registry = {"test_service": mock_wrapper}

        result = await service_registry.health_check("test_service")

        assert result is True
        assert service.status == ServiceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service_registry):
        """Test failed health check"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        mock_wrapper = MagicMock()
        mock_wrapper.ping = AsyncMock(side_effect=Exception("Connection failed"))
        service_registry._registry.get_wrapper.return_value = mock_wrapper

        result = await service_registry.health_check("test_service")

        assert result is False
        assert service.error_count == 1
        assert service.status == ServiceStatus.ERROR
        assert service.last_health_check is not None

    @pytest.mark.asyncio
    async def test_health_check_max_errors(self, service_registry):
        """Test health check reaching max errors"""
        service = MCPServiceInfo(
            name="test_service",
            wrapper_class="TestWrapper",
            error_count=2,
        )
        service_registry.services["test_service"] = service

        mock_wrapper = MagicMock()
        mock_wrapper.ping = AsyncMock(side_effect=Exception("Connection failed"))
        service_registry._registry.get_wrapper.return_value = mock_wrapper

        result = await service_registry.health_check("test_service")

        assert result is False
        assert service.error_count == 3
        assert service.status == ServiceStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unknown_service(self, service_registry):
        """Test health check for unknown service"""
        result = await service_registry.health_check("unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_healthy_services(self, service_registry):
        """Test getting healthy services"""
        service1 = MCPServiceInfo(
            name="service1", wrapper_class="Wrapper1", status=ServiceStatus.HEALTHY
        )
        service2 = MCPServiceInfo(
            name="service2", wrapper_class="Wrapper2", status=ServiceStatus.UNHEALTHY
        )
        service3 = MCPServiceInfo(
            name="service3", wrapper_class="Wrapper3", status=ServiceStatus.HEALTHY
        )

        service_registry.services = {
            "service1": service1,
            "service2": service2,
            "service3": service3,
        }

        healthy = await service_registry.get_healthy_services()

        assert healthy == ["service1", "service3"]

    @pytest.mark.asyncio
    async def test_get_service_status(self, service_registry):
        """Test getting service status"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        status = await service_registry.get_service_status("test_service")

        assert status == service

    @pytest.mark.asyncio
    async def test_get_service_status_unknown(self, service_registry):
        """Test getting status for unknown service"""
        status = await service_registry.get_service_status("unknown")

        assert status is None

    @pytest.mark.asyncio
    async def test_get_all_statuses(self, service_registry):
        """Test getting all service statuses"""
        service1 = MCPServiceInfo(name="service1", wrapper_class="Wrapper1")
        service2 = MCPServiceInfo(name="service2", wrapper_class="Wrapper2")

        service_registry.services = {"service1": service1, "service2": service2}

        statuses = await service_registry.get_all_statuses()

        assert statuses == {"service1": service1, "service2": service2}

    def test_to_dict(self, service_registry):
        """Test exporting registry state as dictionary"""
        service = MCPServiceInfo(
            name="test_service",
            wrapper_class="TestWrapper",
            status=ServiceStatus.HEALTHY,
            last_health_check=datetime.now(),
            error_count=1,
            metadata={"key": "value"},
        )
        service_registry.services["test_service"] = service

        data = service_registry.to_dict()

        assert "test_service" in data
        assert data["test_service"]["wrapper_class"] == "TestWrapper"
        assert data["test_service"]["status"] == ServiceStatus.HEALTHY
        assert data["test_service"]["error_count"] == "1"
        assert data["test_service"]["key"] == "value"

    def test_to_json(self, service_registry):
        """Test exporting registry state as JSON"""
        service = MCPServiceInfo(
            name="test_service",
            wrapper_class="TestWrapper",
            status=ServiceStatus.HEALTHY,
            last_health_check=datetime.now(),
        )
        service_registry.services["test_service"] = service

        json_str = service_registry.to_json()
        data = json.loads(json_str)

        assert "test_service" in data
        assert data["test_service"]["wrapper_class"] == "TestWrapper"

    def test_save_state(self, service_registry, tmp_path):
        """Test saving registry state to file"""
        service = MCPServiceInfo(name="test_service", wrapper_class="TestWrapper")
        service_registry.services["test_service"] = service

        filepath = tmp_path / "state.json"
        service_registry.save_state(filepath)

        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert "test_service" in data

    def test_load_state(self, service_registry, tmp_path):
        """Test loading registry state from file"""
        state_data = {
            "test_service": {
                "wrapper_class": "TestWrapper",
                "status": "healthy",
                "last_health_check": datetime.now().isoformat(),
                "error_count": "2",
                "metadata_key": "metadata_value",
            }
        }

        filepath = tmp_path / "state.json"
        with open(filepath, "w") as f:
            json.dump(state_data, f)

        service_registry.load_state(filepath)

        assert "test_service" in service_registry.services
        service = service_registry.services["test_service"]
        assert service.wrapper_class == "TestWrapper"
        assert service.status == ServiceStatus.HEALTHY
        assert service.error_count == 2
        assert service.metadata["metadata_key"] == "metadata_value"

    def test_load_state_file_not_found(self, service_registry, tmp_path):
        """Test loading state from non-existent file"""
        filepath = tmp_path / "nonexistent.json"
        service_registry.load_state(filepath)

        assert len(service_registry.services) == 0

    def test_load_state_invalid_json(self, service_registry, tmp_path):
        """Test loading state from invalid JSON file"""
        filepath = tmp_path / "invalid.json"
        with open(filepath, "w") as f:
            f.write("invalid json content")

        service_registry.load_state(filepath)

        assert len(service_registry.services) == 0
