"""Configuration Change Audit Service.

This service tracks and audits all configuration changes across the TripSage
application, providing comprehensive audit trails for compliance and security.
It monitors configuration files, environment variables, database settings,
and runtime configuration changes.

Features:
- Real-time configuration change detection
- Detailed audit logging with before/after values
- Integration with the main audit logging system
- Configuration versioning and rollback capabilities
- Security-focused change monitoring
- Compliance-ready audit trails
"""

import asyncio
import enum
import hashlib
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_config_change,
    audit_security_event,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ConfigChangeType(str, enum.Enum):
    """Types of configuration changes."""

    FILE_MODIFIED = "file_modified"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    ENV_VARIABLE_CHANGED = "env_variable_changed"
    DATABASE_SETTING_CHANGED = "database_setting_changed"
    RUNTIME_CONFIG_CHANGED = "runtime_config_changed"
    SECURITY_SETTING_CHANGED = "security_setting_changed"
    API_CONFIG_CHANGED = "api_config_changed"


class ConfigChange(TripSageModel):
    """Represents a single configuration change event."""

    change_id: str = Field(default_factory=lambda: f"cfg-{int(time.time() * 1000)}")
    change_type: ConfigChangeType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # What changed
    config_path: str  # File path, env var name, etc.
    config_key: str | None = None  # Specific key within config

    # Change details
    old_value: str | None = None
    new_value: str | None = None
    old_hash: str | None = None
    new_hash: str | None = None

    # Context
    changed_by: str = "system"  # User ID or system process
    change_reason: str | None = None
    change_source: str = "file_watcher"  # file_watcher, api, manual, etc.

    # Security context
    is_security_relevant: bool = False
    risk_level: str = "low"  # low, medium, high, critical
    requires_approval: bool = False

    # Metadata
    file_size: int | None = None
    file_permissions: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfigurationAuditService:
    """Service for monitoring and auditing configuration changes.

    This service provides comprehensive tracking of configuration changes
    across the entire application stack, with special focus on security-
    relevant configurations.
    """

    def __init__(self, config_paths: list[str] | None = None):
        """Initialize the configuration audit service."""
        self.config_paths = config_paths or self._get_default_config_paths()
        self._is_running = False
        self._file_observer: Observer | None = None
        self._file_handler: ConfigFileHandler | None = None

        # State tracking
        self._file_hashes: dict[str, str] = {}
        self._env_vars: dict[str, str] = {}
        self._last_scan_time: datetime | None = None

        # Statistics
        self.stats = {
            "changes_detected": 0,
            "files_monitored": 0,
            "security_changes": 0,
            "high_risk_changes": 0,
        }

        # Security-relevant patterns
        self._security_patterns = {
            "secret",
            "password",
            "token",
            "key",
            "auth",
            "credential",
            "private",
            "secure",
            "ssl",
            "tls",
            "cert",
            "encryption",
            "database_url",
            "api_key",
            "jwt_secret",
            "oauth",
        }

        # High-risk configuration keys
        self._high_risk_keys = {
            "DEBUG",
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "API_KEYS",
            "CORS_ORIGINS",
            "ALLOWED_HOSTS",
            "RATE_LIMITS",
            "MAX_CONNECTIONS",
            "SECURITY_HEADERS",
        }

    def _get_default_config_paths(self) -> list[str]:
        """Get default configuration paths to monitor."""
        base_path = Path(__file__).parent.parent.parent.parent

        paths = [
            str(base_path / "tripsage" / "api" / "core" / "config.py"),
            str(base_path / "tripsage_core" / "config.py"),
            str(base_path / ".env"),
            str(base_path / ".env.local"),
            str(base_path / ".env.production"),
            str(base_path / "docker-compose.yml"),
            str(base_path / "docker-compose.prod.yml"),
            str(base_path / "pyproject.toml"),
            str(base_path / "uv.lock"),
        ]

        # Only return paths that exist
        return [p for p in paths if Path(p).exists()]

    async def start(self):
        """Start the configuration audit service."""
        if self._is_running:
            return

        self._is_running = True

        # Initialize file monitoring
        await self._initialize_file_monitoring()

        # Take initial snapshot
        await self._take_initial_snapshot()

        # Start periodic scanning
        asyncio.create_task(self._periodic_scan_loop())

        logger.info(
            f"Configuration audit service started, monitoring "
            f"{len(self.config_paths)} paths"
        )

        # Log service startup
        await audit_config_change(
            config_key="configuration_audit_service",
            old_value="stopped",
            new_value="started",
            changed_by="system",
            ip_address="127.0.0.1",
            service_status="started",
            monitored_paths=len(self.config_paths),
        )

    async def stop(self):
        """Stop the configuration audit service."""
        if not self._is_running:
            return

        self._is_running = False

        # Stop file watcher
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()

        logger.info("Configuration audit service stopped")

        # Log service shutdown
        await audit_config_change(
            config_key="configuration_audit_service",
            old_value="started",
            new_value="stopped",
            changed_by="system",
            ip_address="127.0.0.1",
            service_status="stopped",
        )

    async def _initialize_file_monitoring(self):
        """Initialize file system monitoring."""
        from watchdog.observers import Observer

        self._file_handler = ConfigFileHandler(self)
        self._file_observer = Observer()

        # Watch each configuration directory
        watched_dirs = set()
        for config_path in self.config_paths:
            dir_path = Path(config_path).parent
            if dir_path not in watched_dirs:
                self._file_observer.schedule(
                    self._file_handler, str(dir_path), recursive=False
                )
                watched_dirs.add(dir_path)

        self._file_observer.start()
        self.stats["files_monitored"] = len(self.config_paths)

    async def _take_initial_snapshot(self):
        """Take initial snapshot of all configuration files."""
        for config_path in self.config_paths:
            try:
                if Path(config_path).exists():
                    file_hash = await self._calculate_file_hash(config_path)
                    self._file_hashes[config_path] = file_hash
            except Exception as e:
                logger.warning(f"Failed to hash file {config_path}: {e}")

        # Snapshot environment variables
        self._env_vars = dict(os.environ)
        self._last_scan_time = datetime.now(UTC)

    async def _periodic_scan_loop(self):
        """Periodic scanning for changes not caught by file watcher."""
        while self._is_running:
            try:
                await asyncio.sleep(300)  # Scan every 5 minutes
                await self._scan_for_changes()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in periodic scan")

    async def _scan_for_changes(self):
        """Scan for configuration changes."""
        # Check environment variables
        await self._check_env_var_changes()

        # Check file hashes
        await self._check_file_changes()

        self._last_scan_time = datetime.now(UTC)

    async def _check_env_var_changes(self):
        """Check for environment variable changes."""
        current_env = dict(os.environ)

        # Find added/changed variables
        for key, value in current_env.items():
            if key not in self._env_vars:
                # New environment variable
                await self._handle_config_change(
                    ConfigChange(
                        change_type=ConfigChangeType.ENV_VARIABLE_CHANGED,
                        config_path=f"ENV:{key}",
                        config_key=key,
                        old_value=None,
                        new_value=value,
                        change_source="env_scanner",
                        is_security_relevant=self._is_security_relevant(key, value),
                        risk_level=self._assess_risk_level(key, value),
                    )
                )
            elif self._env_vars[key] != value:
                # Changed environment variable
                await self._handle_config_change(
                    ConfigChange(
                        change_type=ConfigChangeType.ENV_VARIABLE_CHANGED,
                        config_path=f"ENV:{key}",
                        config_key=key,
                        old_value=self._env_vars[key],
                        new_value=value,
                        change_source="env_scanner",
                        is_security_relevant=self._is_security_relevant(key, value),
                        risk_level=self._assess_risk_level(key, value),
                    )
                )

        # Find removed variables
        for key, value in self._env_vars.items():
            if key not in current_env:
                await self._handle_config_change(
                    ConfigChange(
                        change_type=ConfigChangeType.ENV_VARIABLE_CHANGED,
                        config_path=f"ENV:{key}",
                        config_key=key,
                        old_value=value,
                        new_value=None,
                        change_source="env_scanner",
                        is_security_relevant=self._is_security_relevant(key, ""),
                        risk_level=self._assess_risk_level(key, ""),
                    )
                )

        self._env_vars = current_env

    async def _check_file_changes(self):
        """Check for file changes that might have been missed."""
        for config_path in self.config_paths:
            try:
                if Path(config_path).exists():
                    current_hash = await self._calculate_file_hash(config_path)
                    stored_hash = self._file_hashes.get(config_path)

                    if stored_hash and stored_hash != current_hash:
                        # File changed
                        await self._handle_file_change(config_path, "modified")
                        self._file_hashes[config_path] = current_hash
                    elif not stored_hash:
                        # New file
                        await self._handle_file_change(config_path, "created")
                        self._file_hashes[config_path] = current_hash
                elif config_path in self._file_hashes:
                    # File was deleted
                    await self._handle_file_change(config_path, "deleted")
                    del self._file_hashes[config_path]

            except Exception as e:
                logger.warning(f"Failed to check file {config_path}: {e}")

    async def _handle_file_change(self, file_path: str, change_type: str):
        """Handle a file system change."""
        file_path_obj = Path(file_path)

        # Determine change type
        if change_type == "modified":
            config_change_type = ConfigChangeType.FILE_MODIFIED
        elif change_type == "created":
            config_change_type = ConfigChangeType.FILE_CREATED
        else:  # deleted
            config_change_type = ConfigChangeType.FILE_DELETED

        # Get file info
        file_size = None
        file_permissions = None
        if file_path_obj.exists():
            try:
                stat = file_path_obj.stat()
                file_size = stat.st_size
                file_permissions = oct(stat.st_mode)[-3:]
            except Exception:
                pass

        change = ConfigChange(
            change_type=config_change_type,
            config_path=file_path,
            old_hash=self._file_hashes.get(file_path),
            new_hash=await self._calculate_file_hash(file_path)
            if file_path_obj.exists()
            else None,
            change_source="file_watcher",
            is_security_relevant=self._is_file_security_relevant(file_path),
            risk_level=self._assess_file_risk_level(file_path),
            file_size=file_size,
            file_permissions=file_permissions,
        )

        await self._handle_config_change(change)

    async def _handle_config_change(self, change: ConfigChange):
        """Handle a configuration change event."""
        self.stats["changes_detected"] += 1

        if change.is_security_relevant:
            self.stats["security_changes"] += 1

        if change.risk_level in ["high", "critical"]:
            self.stats["high_risk_changes"] += 1

        # Log the change to audit system
        await self._audit_config_change(change)

        # Log high-risk changes as security events
        if change.risk_level in ["high", "critical"]:
            await self._log_security_event(change)

        # Log to application logger
        log_level = (
            logging.WARNING
            if change.risk_level in ["high", "critical"]
            else logging.INFO
        )
        logger.log(
            log_level,
            f"Configuration change detected: {change.config_path}",
            extra={
                "change_id": change.change_id,
                "change_type": change.change_type.value,
                "config_path": change.config_path,
                "config_key": change.config_key,
                "changed_by": change.changed_by,
                "is_security_relevant": change.is_security_relevant,
                "risk_level": change.risk_level,
            },
        )

    async def _audit_config_change(self, change: ConfigChange):
        """Log configuration change to audit system."""
        # Sanitize sensitive values for logging
        old_value = self._sanitize_value(change.old_value) if change.old_value else None
        new_value = self._sanitize_value(change.new_value) if change.new_value else None

        await audit_config_change(
            config_key=change.config_key or change.config_path,
            old_value=old_value,
            new_value=new_value,
            changed_by=change.changed_by,
            ip_address="127.0.0.1",  # Local system change
            change_id=change.change_id,
            change_type=change.change_type.value,
            config_path=change.config_path,
            change_source=change.change_source,
            is_security_relevant=change.is_security_relevant,
            risk_level=change.risk_level,
            file_size=change.file_size,
            file_permissions=change.file_permissions,
            old_hash=change.old_hash,
            new_hash=change.new_hash,
        )

    async def _log_security_event(self, change: ConfigChange):
        """Log high-risk configuration changes as security events."""
        severity = (
            AuditSeverity.HIGH
            if change.risk_level == "critical"
            else AuditSeverity.MEDIUM
        )
        risk_score = 80 if change.risk_level == "critical" else 60

        await audit_security_event(
            event_type=AuditEventType.SECURITY_POLICY_CHANGED,
            severity=severity,
            message=f"High-risk configuration change: {change.config_path}",
            actor_id=change.changed_by,
            ip_address="127.0.0.1",
            target_resource=change.config_path,
            risk_score=risk_score,
            change_id=change.change_id,
            change_type=change.change_type.value,
            config_key=change.config_key,
            is_security_relevant=change.is_security_relevant,
            risk_level=change.risk_level,
        )

    def _is_security_relevant(self, key: str, value: str) -> bool:
        """Check if a configuration key/value is security-relevant."""
        key_lower = key.lower()
        value_lower = value.lower() if value else ""

        # Check key patterns
        for pattern in self._security_patterns:
            if pattern in key_lower:
                return True

        # Check value patterns (but be careful not to log actual secrets)
        return bool(
            any(pattern in value_lower for pattern in ["bearer", "basic", "token"])
        )

    def _is_file_security_relevant(self, file_path: str) -> bool:
        """Check if a file is security-relevant."""
        file_name = Path(file_path).name.lower()

        security_files = {
            ".env",
            ".env.local",
            ".env.production",
            ".env.development",
            "config.py",
            "settings.py",
            "secrets.json",
            "credentials.json",
            "docker-compose.yml",
            "docker-compose.prod.yml",
            "nginx.conf",
            "ssl.conf",
            "tls.conf",
        }

        if file_name in security_files:
            return True

        # Check for security-related patterns in path
        path_lower = file_path.lower()
        return any(pattern in path_lower for pattern in self._security_patterns)

    def _assess_risk_level(self, key: str, value: str) -> str:
        """Assess the risk level of a configuration change."""
        key_upper = key.upper()

        # Critical risk keys
        if key_upper in self._high_risk_keys:
            return "critical"

        # High risk patterns
        if any(
            pattern in key.upper()
            for pattern in ["SECRET", "PASSWORD", "TOKEN", "KEY", "PRIVATE"]
        ):
            return "high"

        # Medium risk patterns
        if any(
            pattern in key.upper()
            for pattern in ["AUTH", "SSL", "TLS", "CERT", "SECURITY"]
        ):
            return "medium"

        # Check if it's a security-relevant change
        if self._is_security_relevant(key, value):
            return "medium"

        return "low"

    def _assess_file_risk_level(self, file_path: str) -> str:
        """Assess the risk level of a file change."""
        file_name = Path(file_path).name.lower()

        # Critical files
        critical_files = {".env", ".env.production", "secrets.json", "credentials.json"}
        if file_name in critical_files:
            return "critical"

        # High risk files
        high_risk_files = {
            "config.py",
            "settings.py",
            "docker-compose.yml",
            "nginx.conf",
        }
        if file_name in high_risk_files:
            return "high"

        # Medium risk files
        medium_risk_files = {
            ".env.local",
            ".env.development",
            "uv.lock",
            "pyproject.toml",
        }
        if file_name in medium_risk_files:
            return "medium"

        return "low"

    def _sanitize_value(self, value: str) -> str:
        """Sanitize sensitive values for logging."""
        if not value:
            return value

        # If it looks like a secret, hash it
        alphanumeric_chars = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        )
        if (
            len(value) > 20
            and any(char in value for char in alphanumeric_chars)
            and not value.startswith(("http://", "https://", "/", "."))
        ):
            return f"<hash:{hashlib.sha256(value.encode()).hexdigest()[:16]}>"

        # If it contains secret patterns, mask it
        if any(
            pattern in value.lower()
            for pattern in ["password", "secret", "token", "key"]
        ):
            return f"<masked:{len(value)} chars>"

        # Truncate very long values
        if len(value) > 200:
            return f"{value[:100]}...<truncated:{len(value)} chars>"

        return value

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""

    async def record_manual_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        change_reason: str | None = None,
        requires_approval: bool = False,
    ):
        """Record a manual configuration change."""
        change = ConfigChange(
            change_type=ConfigChangeType.RUNTIME_CONFIG_CHANGED,
            config_path="runtime_config",
            config_key=config_key,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=changed_by,
            change_reason=change_reason,
            change_source="manual",
            is_security_relevant=self._is_security_relevant(
                config_key, str(new_value or "")
            ),
            risk_level=self._assess_risk_level(config_key, str(new_value or "")),
            requires_approval=requires_approval,
        )

        await self._handle_config_change(change)
        return change.change_id

    def get_statistics(self) -> dict[str, Any]:
        """Get configuration audit statistics."""
        return {
            **self.stats,
            "is_running": self._is_running,
            "monitored_files": len(self.config_paths),
            "tracked_files": len(self._file_hashes),
            "tracked_env_vars": len(self._env_vars),
            "last_scan": self._last_scan_time.isoformat()
            if self._last_scan_time
            else None,
        }


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration changes."""

    def __init__(self, audit_service: ConfigurationAuditService):
        self.audit_service = audit_service

    def on_modified(self, event):
        if not event.is_directory and event.src_path in self.audit_service.config_paths:
            asyncio.create_task(
                self.audit_service._handle_file_change(event.src_path, "modified")
            )

    def on_created(self, event):
        if not event.is_directory and event.src_path in self.audit_service.config_paths:
            asyncio.create_task(
                self.audit_service._handle_file_change(event.src_path, "created")
            )

    def on_deleted(self, event):
        if not event.is_directory and event.src_path in self.audit_service.config_paths:
            asyncio.create_task(
                self.audit_service._handle_file_change(event.src_path, "deleted")
            )


# Global configuration audit service instance
_config_audit_service: ConfigurationAuditService | None = None


async def get_config_audit_service() -> ConfigurationAuditService:
    """Get or create the global configuration audit service instance."""
    global _config_audit_service

    if _config_audit_service is None:
        _config_audit_service = ConfigurationAuditService()
        await _config_audit_service.start()

    return _config_audit_service


async def shutdown_config_audit_service():
    """Shutdown the global configuration audit service instance."""
    global _config_audit_service

    if _config_audit_service is not None:
        await _config_audit_service.stop()
        _config_audit_service = None


# Convenience function for manual configuration changes
async def record_config_change(
    config_key: str,
    old_value: Any,
    new_value: Any,
    changed_by: str,
    change_reason: str | None = None,
    requires_approval: bool = False,
) -> str:
    """Record a manual configuration change."""
    service = await get_config_audit_service()
    return await service.record_manual_change(
        config_key, old_value, new_value, changed_by, change_reason, requires_approval
    )
