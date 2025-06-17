"""
Tests for configuration feature flags and database hardening settings.

Tests cover feature flag behavior, configuration validation,
and proper integration with monitoring components.
"""

from unittest.mock import patch

from tripsage_core.config import Settings, get_settings


class TestConfigurationFeatureFlags:
    """Test configuration and feature flag functionality."""

    def test_default_feature_flags(self):
        """Test default values for feature flags."""
        settings = Settings()

        # Database monitoring flags
        assert settings.enable_database_monitoring is True
        assert settings.enable_prometheus_metrics is True
        assert settings.enable_security_monitoring is True
        assert settings.enable_auto_recovery is True

        # Monitoring configuration defaults
        assert settings.db_health_check_interval == 30.0
        assert settings.db_security_check_interval == 60.0
        assert settings.db_max_recovery_attempts == 3
        assert settings.db_recovery_delay == 5.0

        # Metrics configuration defaults
        assert settings.metrics_server_port == 8000
        assert settings.enable_metrics_server is False

    def test_feature_flags_from_environment(self):
        """Test feature flags can be set from environment variables."""
        env_vars = {
            "ENABLE_DATABASE_MONITORING": "false",
            "ENABLE_PROMETHEUS_METRICS": "false",
            "ENABLE_SECURITY_MONITORING": "false",
            "ENABLE_AUTO_RECOVERY": "false",
            "DB_HEALTH_CHECK_INTERVAL": "60.0",
            "DB_SECURITY_CHECK_INTERVAL": "120.0",
            "DB_MAX_RECOVERY_ATTEMPTS": "5",
            "DB_RECOVERY_DELAY": "10.0",
            "METRICS_SERVER_PORT": "9000",
            "ENABLE_METRICS_SERVER": "true",
        }

        with patch.dict("os.environ", env_vars):
            settings = Settings()

            # Verify flags were set from environment
            assert settings.enable_database_monitoring is False
            assert settings.enable_prometheus_metrics is False
            assert settings.enable_security_monitoring is False
            assert settings.enable_auto_recovery is False

            # Verify configuration values
            assert settings.db_health_check_interval == 60.0
            assert settings.db_security_check_interval == 120.0
            assert settings.db_max_recovery_attempts == 5
            assert settings.db_recovery_delay == 10.0
            assert settings.metrics_server_port == 9000
            assert settings.enable_metrics_server is True

    def test_feature_flags_explicit_values(self):
        """Test feature flags with explicit values."""
        settings = Settings(
            enable_database_monitoring=False,
            enable_prometheus_metrics=True,
            enable_security_monitoring=False,
            enable_auto_recovery=True,
            db_health_check_interval=15.0,
            db_security_check_interval=45.0,
            db_max_recovery_attempts=2,
            db_recovery_delay=7.5,
            metrics_server_port=8001,
            enable_metrics_server=True,
        )

        assert settings.enable_database_monitoring is False
        assert settings.enable_prometheus_metrics is True
        assert settings.enable_security_monitoring is False
        assert settings.enable_auto_recovery is True
        assert settings.db_health_check_interval == 15.0
        assert settings.db_security_check_interval == 45.0
        assert settings.db_max_recovery_attempts == 2
        assert settings.db_recovery_delay == 7.5
        assert settings.metrics_server_port == 8001
        assert settings.enable_metrics_server is True

    def test_monitoring_interval_validation(self):
        """Test monitoring interval validation."""
        # Test that intervals can be set to reasonable values
        settings = Settings(
            db_health_check_interval=1.0,  # 1 second minimum
            db_security_check_interval=5.0,  # 5 second minimum
        )

        assert settings.db_health_check_interval == 1.0
        assert settings.db_security_check_interval == 5.0

    def test_recovery_configuration_validation(self):
        """Test recovery configuration validation."""
        # Test recovery attempts and delay
        settings = Settings(
            db_max_recovery_attempts=1,  # Minimum 1 attempt
            db_recovery_delay=0.1,  # Fast recovery for testing
        )

        assert settings.db_max_recovery_attempts == 1
        assert settings.db_recovery_delay == 0.1

    def test_metrics_port_configuration(self):
        """Test metrics server port configuration."""
        # Test different port numbers
        settings = Settings(metrics_server_port=9090)
        assert settings.metrics_server_port == 9090

        settings = Settings(metrics_server_port=3000)
        assert settings.metrics_server_port == 3000

    def test_settings_singleton_behavior(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to lru_cache
        assert settings1 is settings2

    def test_environment_property_methods(self):
        """Test environment property methods work with new config."""
        # Test development environment
        settings = Settings(environment="development")
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

        # Test production environment
        settings = Settings(environment="production")
        assert settings.is_development is False
        assert settings.is_production is True
        assert settings.is_testing is False

        # Test testing environment
        settings = Settings(environment="test")
        assert settings.is_development is False
        assert settings.is_production is False
        assert settings.is_testing is True

    def test_database_configuration_still_works(self):
        """Test that existing database configuration still works."""
        settings = Settings(
            database_url="https://test.supabase.co",
            database_public_key="test-public-key",
            database_service_key="test-service-key",
        )

        assert settings.database_url == "https://test.supabase.co"
        assert settings.database_public_key.get_secret_value() == "test-public-key"
        assert settings.database_service_key.get_secret_value() == "test-service-key"

    def test_all_monitoring_flags_disabled(self):
        """Test behavior when all monitoring flags are disabled."""
        settings = Settings(
            enable_database_monitoring=False,
            enable_prometheus_metrics=False,
            enable_security_monitoring=False,
            enable_auto_recovery=False,
        )

        # All monitoring should be disabled
        assert settings.enable_database_monitoring is False
        assert settings.enable_prometheus_metrics is False
        assert settings.enable_security_monitoring is False
        assert settings.enable_auto_recovery is False

    def test_all_monitoring_flags_enabled(self):
        """Test behavior when all monitoring flags are enabled."""
        settings = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
            enable_security_monitoring=True,
            enable_auto_recovery=True,
            enable_metrics_server=True,
        )

        # All monitoring should be enabled
        assert settings.enable_database_monitoring is True
        assert settings.enable_prometheus_metrics is True
        assert settings.enable_security_monitoring is True
        assert settings.enable_auto_recovery is True
        assert settings.enable_metrics_server is True

    def test_partial_monitoring_enabled(self):
        """Test partial monitoring configuration."""
        # Only metrics enabled, no monitoring
        settings = Settings(
            enable_database_monitoring=False,
            enable_prometheus_metrics=True,
            enable_security_monitoring=False,
            enable_auto_recovery=False,
        )

        assert settings.enable_database_monitoring is False
        assert settings.enable_prometheus_metrics is True
        assert settings.enable_security_monitoring is False
        assert settings.enable_auto_recovery is False

    def test_development_vs_production_defaults(self):
        """Test that monitoring works in different environments."""
        # Development environment
        dev_settings = Settings(environment="development")
        assert dev_settings.is_development is True
        assert dev_settings.enable_database_monitoring is True  # Should work in dev

        # Production environment
        prod_settings = Settings(environment="production")
        assert prod_settings.is_production is True
        assert prod_settings.enable_database_monitoring is True  # Should work in prod

        # Test environment
        test_settings = Settings(environment="test")
        assert test_settings.is_testing is True
        assert test_settings.enable_database_monitoring is True  # Should work in test

    def test_feature_flag_field_descriptions(self):
        """Test that feature flag fields have proper descriptions."""
        settings = Settings()

        # Get field info from the model
        fields = settings.model_fields

        # Check that monitoring fields have descriptions
        monitoring_fields = [
            "enable_database_monitoring",
            "enable_prometheus_metrics",
            "enable_security_monitoring",
            "enable_auto_recovery",
            "db_health_check_interval",
            "db_security_check_interval",
            "db_max_recovery_attempts",
            "db_recovery_delay",
            "metrics_server_port",
            "enable_metrics_server",
        ]

        for field_name in monitoring_fields:
            assert field_name in fields
            field_info = fields[field_name]
            assert hasattr(field_info, "description")
            assert field_info.description is not None
            assert len(field_info.description) > 0

    def test_settings_validation_with_new_fields(self):
        """Test that settings validation works with new monitoring fields."""
        # Should not raise validation errors
        settings = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
            db_health_check_interval=10.0,
            db_max_recovery_attempts=3,
            metrics_server_port=8000,
        )

        # Validate that the settings object was created successfully
        assert isinstance(settings, Settings)
        assert settings.enable_database_monitoring is True

    def test_environment_variable_case_insensitive(self):
        """Test that environment variables are case insensitive."""
        env_vars = {
            "enable_database_monitoring": "false",  # lowercase
            "ENABLE_PROMETHEUS_METRICS": "false",  # uppercase
            "Enable_Security_Monitoring": "false",  # mixed case
        }

        with patch.dict("os.environ", env_vars):
            settings = Settings()

            # All should be parsed correctly due to case_sensitive=False
            assert settings.enable_database_monitoring is False
            assert settings.enable_prometheus_metrics is False
            assert settings.enable_security_monitoring is False


class TestSettingsIntegration:
    """Test settings integration with monitoring components."""

    def test_settings_with_wrapper_initialization(self):
        """Test settings work correctly with database wrapper."""
        from tripsage_core.services.infrastructure.database_wrapper import (
            DatabaseServiceWrapper,
        )

        # Test with monitoring enabled
        settings_enabled = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
        )

        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ),
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ),
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ),
        ):
            wrapper = DatabaseServiceWrapper(settings_enabled)
            assert wrapper.settings.enable_database_monitoring is True
            assert wrapper.settings.enable_prometheus_metrics is True

    def test_settings_with_monitor_configuration(self):
        """Test settings work correctly with monitor configuration."""
        from unittest.mock import Mock

        from tripsage_core.services.infrastructure.database_monitor import (
            ConsolidatedDatabaseMonitor,
        )

        settings = Settings(
            db_health_check_interval=25.0,
            db_security_check_interval=55.0,
            db_max_recovery_attempts=4,
            db_recovery_delay=8.0,
        )

        mock_db_service = Mock()
        mock_metrics = Mock()

        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_db_service,
            settings=settings,
            metrics=mock_metrics,
        )

        # Configure with settings values
        monitor.configure_monitoring(
            health_check_interval=settings.db_health_check_interval,
            security_check_interval=settings.db_security_check_interval,
            max_recovery_attempts=settings.db_max_recovery_attempts,
            recovery_delay=settings.db_recovery_delay,
        )

        # Verify configuration was applied
        assert monitor._health_check_interval == 25.0
        assert monitor._security_check_interval == 55.0
        assert monitor._max_recovery_attempts == 4
        assert monitor._recovery_delay == 8.0
