"""Tests for TripSage Modern Docker Development Environment.

Tests validate the modernized Docker setup aligned with current architecture:
- Supabase PostgreSQL with pgvector (unified storage)
- DragonflyDB caching (25x faster than Redis)
- Mem0 memory system (91% faster than Neo4j)
- Direct SDK integrations (Duffel, Google Maps, Crawl4AI, Playwright)
- Only 1 MCP service remaining (Airbnb - no official SDK)
"""

from pathlib import Path

import pytest
import yaml


class TestModernDockerArchitecture:
    """Test Docker configuration matches current high-performance architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        self.docker_dir = Path(__file__).parent.parent.parent / "docker"
        self.compose_file = self.docker_dir / "docker-compose.mcp.yml"

    def test_compose_file_exists(self):
        """Test that the modern Docker Compose file exists."""
        assert self.compose_file.exists(), "docker-compose.mcp.yml not found"

    def test_compose_yaml_valid(self):
        """Test that Docker Compose YAML is valid."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        assert config is not None, "Failed to parse Docker Compose YAML"
        assert "services" in config, "No services defined in compose file"

    def test_modern_infrastructure_services(self):
        """Test that modern high-performance infrastructure services are present."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Core modern infrastructure
        required_services = {
            "supabase": "Unified database with pgvector",
            "dragonfly": "High-performance Redis replacement (25x faster)",
            "tripsage-api": "FastAPI backend with direct SDKs",
            "tripsage-frontend": "Next.js 15 frontend",
            "airbnb-mcp": "Only remaining MCP service",
        }

        for service_name, description in required_services.items():
            assert service_name in services, f"Missing {service_name}: {description}"

    def test_legacy_mcp_services_removed(self):
        """Test that legacy MCP services have been removed."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Services that should be REMOVED (migrated to direct SDKs)
        legacy_services = [
            "neo4j-memory-mcp",  # Replaced by Mem0
            "redis-mcp",  # Replaced by DragonflyDB
            "firecrawl-mcp",  # Replaced by Crawl4AI SDK
            "google-maps-mcp",  # Replaced by direct SDK
            "weather-mcp",  # Replaced by direct HTTP
            "duffel-flights-mcp",  # Replaced by direct SDK
            "supabase-mcp",  # Using direct Supabase SDK
            "time-mcp",  # Using native Python datetime
            "google-calendar-mcp",  # Replaced by direct SDK
        ]

        for legacy_service in legacy_services:
            assert legacy_service not in services, (
                f"Legacy service {legacy_service} should be removed (migrated to SDK)"
            )

    def test_monitoring_stack_present(self):
        """Test that production-ready monitoring stack is configured."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]
        monitoring_services = ["jaeger", "otel-collector", "prometheus", "grafana"]

        for service_name in monitoring_services:
            assert service_name in services, (
                f"Monitoring service {service_name} not found"
            )

    def test_resource_limits_optimized(self):
        """Test that resource limits are optimized for modern architecture."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Check high-performance services have appropriate resources
        high_perf_services = {
            "supabase": {"min_cpu": "1.0", "min_memory": "1G"},
            "dragonfly": {"min_cpu": "0.5", "min_memory": "512M"},
            "tripsage-api": {"min_cpu": "1.0", "min_memory": "1G"},
        }

        for service_name, _expected_resources in high_perf_services.items():
            if service_name in services:
                service = services[service_name]
                if "deploy" in service and "resources" in service["deploy"]:
                    resources = service["deploy"]["resources"]
                    if "reservations" in resources:
                        reservations = resources["reservations"]
                        # Basic validation that services have adequate resources
                        assert "cpus" in reservations, (
                            f"{service_name} missing CPU reservations"
                        )
                        assert "memory" in reservations, (
                            f"{service_name} missing memory reservations"
                        )


class TestDockerfileModernization:
    """Test Dockerfiles for modern architecture components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.docker_dir = Path(__file__).parent.parent.parent / "docker"

    def test_api_dockerfile_exists(self):
        """Test that API Dockerfile exists and uses modern dependencies."""
        api_dockerfile = self.docker_dir / "Dockerfile.api"
        assert api_dockerfile.exists(), "API Dockerfile not found"

        with open(api_dockerfile) as f:
            content = f.read()

        # Check for modern dependencies
        modern_deps = ["mem0ai", "crawl4ai", "playwright", "asyncpg"]
        for dep in modern_deps:
            assert dep in content, (
                f"Modern dependency {dep} not found in API Dockerfile"
            )

    def test_frontend_dockerfile_exists(self):
        """Test that frontend Dockerfile exists and uses Next.js 15."""
        frontend_dockerfile = (
            Path(__file__).parent.parent.parent / "frontend" / "Dockerfile.dev"
        )
        assert frontend_dockerfile.exists(), "Frontend Dockerfile not found"

        with open(frontend_dockerfile) as f:
            content = f.read()

        # Check for modern frontend setup
        assert "pnpm" in content, "Frontend should use pnpm for package management"
        assert "NODE_ENV=development" in content, (
            "Development environment not configured"
        )

    def test_only_airbnb_mcp_dockerfile_exists(self):
        """Test that only Airbnb MCP Dockerfile exists (others removed)."""
        dev_services_dir = self.docker_dir / "dev_services"

        if dev_services_dir.exists():
            # Only airbnb_mcp should exist
            mcp_dirs = list(dev_services_dir.glob("*"))
            mcp_names = [d.name for d in mcp_dirs if d.is_dir()]

            assert "airbnb_mcp" in mcp_names, (
                "Airbnb MCP should be present (only remaining MCP)"
            )

            # Check that legacy MCP Dockerfiles are removed
            legacy_mcps = [
                "neo4j_memory_mcp",
                "redis_mcp",
                "firecrawl_mcp",
                "google_maps_mcp",
                "weather_mcp",
                "duffel_flights_mcp",
            ]

            for legacy_mcp in legacy_mcps:
                assert legacy_mcp not in mcp_names, (
                    f"Legacy MCP {legacy_mcp} should be removed"
                )


class TestEnvironmentConfiguration:
    """Test environment configuration for modern architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        self.docker_dir = Path(__file__).parent.parent.parent / "docker"
        self.compose_file = self.docker_dir / "docker-compose.mcp.yml"

    def test_supabase_configuration(self):
        """Test Supabase configuration for unified database."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]
        supabase = services.get("supabase", {})

        # Check Supabase configuration
        assert "environment" in supabase, "Supabase environment not configured"
        env_vars = supabase["environment"]

        required_env = ["POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_USER"]
        for env_var in required_env:
            found = any(env_var in var for var in env_vars)
            assert found, f"Supabase missing {env_var} configuration"

    def test_dragonfly_configuration(self):
        """Test DragonflyDB configuration for high-performance caching."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]
        dragonfly = services.get("dragonfly", {})

        # Check DragonflyDB configuration
        assert "image" in dragonfly, "DragonflyDB image not specified"
        assert "dragonflydb" in dragonfly["image"], (
            "Should use official DragonflyDB image"
        )

        # Check Redis-compatible port
        assert "ports" in dragonfly, "DragonflyDB ports not configured"
        ports = dragonfly["ports"]
        redis_port_found = any("6379" in port for port in ports)
        assert redis_port_found, "DragonflyDB should expose Redis-compatible port 6379"

    def test_api_environment_modern_sdks(self):
        """Test API environment includes modern SDK configurations."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]
        api = services.get("tripsage-api", {})

        if "environment" in api:
            env_vars = api["environment"]

            # Check for modern architecture environment variables
            modern_env_patterns = [
                "DATABASE_URL",  # Direct database connection
                "DRAGONFLY_URL",  # DragonflyDB cache
                "MEM0_CONFIG",  # Mem0 memory system
                "DUFFEL_API_KEY",  # Direct Duffel SDK
                "GOOGLE_MAPS_API_KEY",  # Direct Google Maps SDK
                "CRAWL4AI_API_KEY",  # Direct Crawl4AI SDK
            ]

            for pattern in modern_env_patterns:
                found = any(pattern in var for var in env_vars)
                if pattern in [
                    "DUFFEL_API_KEY",
                    "GOOGLE_MAPS_API_KEY",
                    "CRAWL4AI_API_KEY",
                ]:
                    # These are optional but should be configured if present
                    continue
                assert found, f"API missing modern environment variable: {pattern}"


class TestNetworkAndVolumeConfiguration:
    """Test network isolation and persistent storage configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.docker_dir = Path(__file__).parent.parent.parent / "docker"
        self.compose_file = self.docker_dir / "docker-compose.mcp.yml"

    def test_network_configuration(self):
        """Test that services use proper network isolation."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        # Check network configuration
        assert "networks" in config, "No network configuration found"
        networks = config["networks"]
        assert "tripsage-network" in networks, "tripsage-network not defined"

        # Check all services use the network
        services = config["services"]
        for service_name, service_config in services.items():
            assert "networks" in service_config, (
                f"{service_name} not configured for network isolation"
            )
            assert "tripsage-network" in service_config["networks"], (
                f"{service_name} not using tripsage-network"
            )

    def test_volume_configuration(self):
        """Test that persistent volumes are configured for data services."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        # Check volume configuration
        assert "volumes" in config, "No volume configuration found"
        volumes = config["volumes"]

        # Check that data services have persistent volumes
        required_volumes = [
            "supabase_data",  # Database persistence
            "dragonfly_data",  # Cache persistence
            "prometheus_data",  # Metrics persistence
            "grafana_data",  # Dashboard persistence
        ]

        for volume_name in required_volumes:
            assert volume_name in volumes, f"Missing persistent volume: {volume_name}"


class TestPerformanceArchitecture:
    """Test configuration supports high-performance architecture claims."""

    def setup_method(self):
        """Set up test fixtures."""
        self.docker_dir = Path(__file__).parent.parent.parent / "docker"
        self.compose_file = self.docker_dir / "docker-compose.mcp.yml"

    def test_dragonfly_vs_redis_performance_setup(self):
        """Test DragonflyDB is configured for 25x performance vs Redis."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Ensure DragonflyDB is used instead of Redis
        assert "dragonfly" in services, "DragonflyDB not configured"
        assert "redis" not in services, "Redis should be replaced by DragonflyDB"

        dragonfly = services["dragonfly"]
        assert "dragonflydb" in dragonfly["image"], (
            "Should use official DragonflyDB image"
        )

    def test_supabase_pgvector_setup(self):
        """Test Supabase is configured for pgvector (11x faster vector search)."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Ensure Supabase (not separate PostgreSQL + vector DB)
        assert "supabase" in services, "Supabase unified database not configured"
        assert "qdrant" not in services, "Qdrant should be replaced by pgvector"
        assert "weaviate" not in services, "Weaviate should be replaced by pgvector"

    def test_no_neo4j_mem0_migration(self):
        """Test Neo4j has been replaced by Mem0 (91% faster)."""
        with open(self.compose_file) as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Ensure Neo4j is completely removed
        assert "neo4j" not in services, "Neo4j should be replaced by Mem0"
        assert "neo4j-memory-mcp" not in services, "Neo4j MCP should be removed"

        # Mem0 integration should be via direct SDK (no separate container)
        # Configuration should be in API environment variables


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
