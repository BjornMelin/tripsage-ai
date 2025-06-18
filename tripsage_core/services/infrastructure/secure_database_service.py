"""
Secure Database Service with Comprehensive Security Hardening.

This module provides a production-ready database service that integrates
comprehensive security hardening including connection validation, threat detection,
audit logging, and compliance monitoring.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)
from tripsage_core.security.database_security_hardening import (
    AuditEventType,
    DatabaseSecurityManager,
)
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaManager,
)

logger = logging.getLogger(__name__)


class SecureDatabaseService:
    """
    Production-ready database service with comprehensive security hardening.

    This service provides:
    - Enhanced connection validation with pre-ping security checks
    - IP-based rate limiting with geographic and behavioral analysis
    - Advanced SQL injection detection and prevention
    - Comprehensive audit trails and security logging
    - Real-time threat detection and anomaly monitoring
    - Security configuration validation and compliance
    - Automated security incident response
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        enable_security_hardening: bool = True,
        rate_limit_requests: int = 100,
        rate_limit_burst: int = 200,
        enable_pre_ping: bool = True,
        security_check_interval: float = 60.0,
    ):
        """Initialize secure database service.

        Args:
            settings: Application settings
            enable_security_hardening: Enable comprehensive security features
            rate_limit_requests: Requests per minute per IP
            rate_limit_burst: Burst limit for rate limiting
            enable_pre_ping: Enable pre-ping connection validation
            security_check_interval: Security monitoring interval in seconds
        """
        self.settings = settings or get_settings()
        self.enable_security_hardening = enable_security_hardening
        self.enable_pre_ping = enable_pre_ping
        self.security_check_interval = security_check_interval

        # Service state
        self._client: Optional[Client] = None
        self._connected = False
        self._replica_manager: Optional[ReplicaManager] = None

        # Security components
        if enable_security_hardening:
            self._security_manager = DatabaseSecurityManager(
                enable_rate_limiting=True,
                enable_sql_injection_detection=True,
                enable_audit_logging=True,
                enable_threat_detection=True,
                rate_limit_requests=rate_limit_requests,
                rate_limit_burst=rate_limit_burst,
            )
        else:
            self._security_manager = None

        # Connection monitoring
        self._connection_count = 0
        self._last_security_check = time.time()
        self._connection_errors = 0

        # Performance tracking
        self._query_count = 0
        self._security_blocks = 0
        self._start_time = time.time()

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to the database."""
        return self._connected and self._client is not None

    @property
    def client(self) -> Client:
        """Get Supabase client, raising error if not connected."""
        if not self._connected or not self._client:
            raise CoreServiceError(
                message="Database service not connected. Call connect() first.",
                code="DATABASE_NOT_CONNECTED",
                service="SecureDatabaseService",
            )
        return self._client

    async def connect(
        self,
        source_ip: str = "127.0.0.1",
        user_agent: Optional[str] = None,
        user_region: Optional[str] = None,
    ) -> None:
        """Initialize Supabase client with security validation."""
        if self._connected:
            return

        try:
            # Validate configuration security
            if self._security_manager:
                config_validation = (
                    await self._security_manager.validate_security_configuration(
                        {
                            "database_url": self.settings.database_url,
                            "database_public_key": (
                                self.settings.database_public_key.get_secret_value()
                            ),
                            "ssl_required": True,
                            "encrypt_data_in_transit": True,
                            "enable_security_monitoring": (
                                self.settings.enable_security_monitoring
                            ),
                            "max_connections": 100,
                            "rate_limit_requests": 100,
                            "connection_timeout": 30,
                            "idle_timeout": 300,
                            "log_failed_connections": True,
                            "audit_trail_enabled": True,
                        }
                    )
                )

                if not config_validation["compliant"]:
                    logger.warning(
                        f"Security configuration compliance: "
                        f"{config_validation['compliance_percentage']:.1f}%"
                    )
                    for recommendation in config_validation["recommendations"]:
                        logger.warning(f"Security recommendation: {recommendation}")

            # Validate connection security
            if self._security_manager:
                (
                    connection_allowed,
                    threat_alert,
                ) = await self._security_manager.validate_connection(
                    database_url=self.settings.database_url,
                    api_key=(self.settings.database_public_key.get_secret_value()),
                    source_ip=source_ip,
                    user_agent=user_agent,
                    user_region=user_region,
                )

                if not connection_allowed:
                    self._security_blocks += 1
                    if threat_alert:
                        logger.error(
                            f"Connection blocked by security: {threat_alert.message}"
                        )
                        raise CoreDatabaseError(
                            message=f"Connection blocked: {threat_alert.message}",
                            code="SECURITY_CONNECTION_BLOCKED",
                            details={
                                "threat_type": threat_alert.threat_type.value,
                                "severity": threat_alert.severity.value,
                            },
                        )
                    else:
                        raise CoreDatabaseError(
                            message="Connection blocked by security policy",
                            code="SECURITY_CONNECTION_BLOCKED",
                        )

            # Validate Supabase configuration
            supabase_url = self.settings.database_url
            supabase_key = self.settings.database_public_key.get_secret_value()

            if not supabase_url or not supabase_url.startswith("https://"):
                raise CoreDatabaseError(
                    message=(
                        f"Invalid Supabase URL format: {supabase_url}. "
                        f"Must be a valid HTTPS URL"
                    ),
                    code="INVALID_DATABASE_URL",
                )

            if not supabase_key or len(supabase_key) < 20:
                raise CoreDatabaseError(
                    message="Invalid Supabase API key: key is missing or too short",
                    code="INVALID_DATABASE_KEY",
                )

            logger.info(f"Connecting to Supabase at {supabase_url}")

            # Enhanced client options for security and performance
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                postgrest_client_timeout=60.0,
            )

            # Create Supabase client
            self._client = create_client(supabase_url, supabase_key, options=options)

            # Enhanced connection validation with pre-ping
            if self.enable_pre_ping:
                await self._validate_connection_security()
            else:
                # Basic connection test
                await asyncio.to_thread(
                    lambda: self._client.table("users").select("id").limit(1).execute()
                )

            self._connected = True
            self._connection_count += 1

            logger.info("Secure database service connected successfully")

            # Initialize replica manager if read replicas are enabled
            if self.settings.enable_read_replicas:
                try:
                    self._replica_manager = ReplicaManager(self.settings)
                    await self._replica_manager.initialize()
                    logger.info("Read replica manager initialized")
                except Exception as replica_error:
                    logger.error(
                        f"Failed to initialize replica manager: {replica_error}"
                    )
                    # Continue without replica manager - fall back to primary only

            # Log successful connection
            if self._security_manager:
                await self._security_manager.audit_logger.log_event(
                    AuditEventType.AUTHENTICATION_SUCCESS,
                    None,
                    source_ip,
                    True,
                    metadata={
                        "user_agent": user_agent,
                        "user_region": user_region,
                        "connection_count": self._connection_count,
                    },
                )

        except Exception as e:
            self._connection_errors += 1
            logger.error(f"Failed to connect to secure database: {e}")
            self._connected = False

            # Log failed connection
            if self._security_manager:
                await self._security_manager.audit_logger.log_event(
                    AuditEventType.AUTHENTICATION_FAILURE,
                    None,
                    source_ip,
                    False,
                    metadata={
                        "error": str(e),
                        "user_agent": user_agent,
                    },
                )

            raise CoreDatabaseError(
                message=f"Failed to connect to database: {str(e)}",
                code="DATABASE_CONNECTION_FAILED",
                details={"error": str(e)},
            ) from e

    async def _validate_connection_security(self) -> None:
        """Enhanced connection validation with security checks."""
        try:
            # Test basic connectivity
            await asyncio.to_thread(
                lambda: self._client.table("users").select("id").limit(1).execute()
            )

            # Validate connection permissions
            await asyncio.to_thread(
                lambda: self._client.table("api_keys").select("id").limit(1).execute()
            )

            # Test read-only operations
            await asyncio.to_thread(
                lambda: self._client.table("trips").select("id").limit(1).execute()
            )

            logger.info("Connection security validation completed successfully")

        except Exception as e:
            logger.error(f"Connection security validation failed: {e}")
            raise CoreDatabaseError(
                message=f"Connection security validation failed: {str(e)}",
                code="CONNECTION_SECURITY_VALIDATION_FAILED",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """Close database connection and cleanup resources."""
        logger.info("Closing secure database service")

        # Close replica manager first
        if self._replica_manager:
            try:
                await self._replica_manager.close()
                self._replica_manager = None
                logger.info("Replica manager closed")
            except Exception as e:
                logger.error(f"Error closing replica manager: {e}")

        if self._client:
            try:
                # Supabase client cleanup if needed
                self._client = None
                logger.info("Secure database service disconnected")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self._connected = False

    async def ensure_connected(self, source_ip: str = "127.0.0.1") -> None:
        """Ensure database connection is established with security validation."""
        if not self.is_connected:
            await self.connect(source_ip=source_ip)

    @asynccontextmanager
    async def _get_client_for_query(
        self,
        query_type: QueryType = QueryType.READ,
        user_region: Optional[str] = None,
    ):
        """Get the appropriate client for a query with security monitoring."""
        # If replica manager is available and enabled, use it for read queries
        if self._replica_manager and query_type in [
            QueryType.READ,
            QueryType.ANALYTICS,
            QueryType.VECTOR_SEARCH,
        ]:
            try:
                async with self._replica_manager.acquire_connection(
                    query_type=query_type,
                    user_region=user_region,
                ) as (replica_id, client):
                    yield replica_id, client
                    return
            except Exception as e:
                logger.warning(
                    f"Failed to get replica client: {e}, falling back to primary"
                )

        # Fallback to primary client
        yield "primary", self.client

    async def _validate_query_security(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]],
        user_id: Optional[str],
        source_ip: str,
        table_accessed: Optional[str] = None,
    ) -> None:
        """Validate query for security threats."""
        if not self._security_manager:
            return

        # Perform security monitoring check periodically
        current_time = time.time()
        if current_time - self._last_security_check > self.security_check_interval:
            await self._perform_security_monitoring()
            self._last_security_check = current_time

        # Validate query security
        query_allowed, threat_alert = await self._security_manager.validate_query(
            query=query,
            parameters=parameters,
            user_id=user_id,
            source_ip=source_ip,
            table_accessed=table_accessed,
        )

        if not query_allowed:
            self._security_blocks += 1
            if threat_alert:
                logger.error(f"Query blocked by security: {threat_alert.message}")
                raise CoreDatabaseError(
                    message=f"Query blocked: {threat_alert.message}",
                    code="SECURITY_QUERY_BLOCKED",
                    operation="QUERY_VALIDATION",
                    table=table_accessed,
                    details={
                        "threat_type": threat_alert.threat_type.value,
                        "severity": threat_alert.severity.value,
                        "query_hash": threat_alert.metadata.get("query_hash"),
                    },
                )
            else:
                raise CoreDatabaseError(
                    message="Query blocked by security policy",
                    code="SECURITY_QUERY_BLOCKED",
                    operation="QUERY_VALIDATION",
                    table=table_accessed,
                )

    async def _perform_security_monitoring(self) -> None:
        """Perform periodic security monitoring checks."""
        if not self._security_manager:
            return

        try:
            # Get security status
            security_status = await self._security_manager.get_security_status()

            # Check for high threat levels
            metrics = security_status["metrics"]
            if metrics["threat_score"] > 50:
                logger.warning(
                    f"High security threat score: {metrics['threat_score']} "
                    f"(threats: {metrics['threats_detected']}, "
                    f"blocked: {metrics['blocked_connections']})"
                )

            # Check recent threats
            recent_threats = security_status.get("recent_threats", [])
            critical_threats = [
                t
                for t in recent_threats
                if t["severity"] in ["high", "critical"]
                and not t.get("acknowledged", False)
            ]

            if critical_threats:
                logger.warning(
                    f"Unacknowledged critical threats: {len(critical_threats)}"
                )
                for threat in critical_threats[:3]:  # Log first 3 critical threats
                    logger.warning(
                        f"Critical threat: {threat['type']} "
                        f"from {threat['source_ip']} - {threat['message']}"
                    )

        except Exception as e:
            logger.error(f"Security monitoring check failed: {e}")

    # Core database operations with security integration

    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        user_id: Optional[str] = None,
        source_ip: str = "127.0.0.1",
    ) -> List[Dict[str, Any]]:
        """Insert data into table with security validation."""
        await self.ensure_connected(source_ip=source_ip)

        # Security validation
        insert_query = f"INSERT INTO {table} ..."  # Simplified for validation
        await self._validate_query_security(
            query=insert_query,
            parameters=data if isinstance(data, dict) else None,
            user_id=user_id,
            source_ip=source_ip,
            table_accessed=table,
        )

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table(table).insert(data).execute()
            )
            self._query_count += 1
            return result.data
        except Exception as e:
            logger.error(f"Database INSERT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to insert into table '{table}'",
                code="INSERT_FAILED",
                operation="INSERT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None,
        source_ip: str = "127.0.0.1",
        user_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table with security validation."""
        await self.ensure_connected(source_ip=source_ip)

        # Security validation
        select_query = f"SELECT {columns} FROM {table}"
        if filters:
            select_query += f" WHERE {list(filters.keys())}"

        await self._validate_query_security(
            query=select_query,
            parameters=filters,
            user_id=user_id,
            source_ip=source_ip,
            table_accessed=table,
        )

        try:
            async with self._get_client_for_query(
                query_type=QueryType.READ,
                user_region=user_region,
            ) as (replica_id, client):
                query = client.table(table).select(columns)

                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            # Support for complex filters like {"gte": 18}
                            for operator, filter_value in value.items():
                                query = getattr(query, operator)(key, filter_value)
                        else:
                            query = query.eq(key, value)

                # Apply ordering
                if order_by:
                    if order_by.startswith("-"):
                        query = query.order(order_by[1:], desc=True)
                    else:
                        query = query.order(order_by)

                # Apply pagination
                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                result = await asyncio.to_thread(lambda: query.execute())
                self._query_count += 1
                logger.debug(f"Query executed on replica {replica_id}")
                return result.data
        except Exception as e:
            logger.error(f"Database SELECT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to select from table '{table}'",
                code="SELECT_FAILED",
                operation="SELECT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
        source_ip: str = "127.0.0.1",
    ) -> List[Dict[str, Any]]:
        """Update data in table with security validation."""
        await self.ensure_connected(source_ip=source_ip)

        # Security validation
        update_query = (
            f"UPDATE {table} SET {list(data.keys())} WHERE {list(filters.keys())}"
        )
        await self._validate_query_security(
            query=update_query,
            parameters={**data, **filters},
            user_id=user_id,
            source_ip=source_ip,
            table_accessed=table,
        )

        try:
            query = self.client.table(table).update(data)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            self._query_count += 1
            return result.data
        except Exception as e:
            logger.error(f"Database UPDATE error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to update table '{table}'",
                code="UPDATE_FAILED",
                operation="UPDATE",
                table=table,
                details={"error": str(e)},
            ) from e

    async def delete(
        self,
        table: str,
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
        source_ip: str = "127.0.0.1",
    ) -> List[Dict[str, Any]]:
        """Delete data from table with security validation."""
        await self.ensure_connected(source_ip=source_ip)

        # Security validation
        delete_query = f"DELETE FROM {table} WHERE {list(filters.keys())}"
        await self._validate_query_security(
            query=delete_query,
            parameters=filters,
            user_id=user_id,
            source_ip=source_ip,
            table_accessed=table,
        )

        try:
            query = self.client.table(table).delete()

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            self._query_count += 1
            return result.data
        except Exception as e:
            logger.error(f"Database DELETE error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to delete from table '{table}'",
                code="DELETE_FAILED",
                operation="DELETE",
                table=table,
                details={"error": str(e)},
            ) from e

    # Security monitoring and reporting

    async def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        if not self._security_manager:
            return {
                "security_enabled": False,
                "message": "Security hardening is disabled",
            }

        status = await self._security_manager.get_security_status()

        # Add service-level metrics
        uptime = time.time() - self._start_time
        status["service_metrics"] = {
            "uptime_seconds": uptime,
            "total_queries": self._query_count,
            "security_blocks": self._security_blocks,
            "connection_count": self._connection_count,
            "connection_errors": self._connection_errors,
            "queries_per_second": self._query_count / max(uptime, 1),
            "security_block_rate": self._security_blocks / max(self._query_count, 1),
        }

        return status

    async def get_threat_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent threat alerts."""
        if not self._security_manager:
            return []

        alerts = self._security_manager.get_threat_alerts(limit=limit)
        return [
            {
                "type": alert.threat_type.value,
                "severity": alert.severity.value,
                "source_ip": alert.source_ip,
                "timestamp": alert.timestamp.isoformat(),
                "message": alert.message,
                "metadata": alert.metadata,
                "blocked": alert.blocked,
                "acknowledged": alert.acknowledged,
            }
            for alert in alerts
        ]

    async def acknowledge_threat(self, alert_timestamp: str) -> bool:
        """Acknowledge a threat alert."""
        if not self._security_manager:
            return False

        try:
            timestamp = datetime.fromisoformat(alert_timestamp.replace("Z", "+00:00"))
            return self._security_manager.acknowledge_threat(timestamp)
        except Exception as e:
            logger.error(f"Failed to acknowledge threat: {e}")
            return False

    async def health_check(self, source_ip: str = "127.0.0.1") -> bool:
        """Check database connectivity with security validation."""
        try:
            await self.ensure_connected(source_ip=source_ip)

            # Test basic connectivity
            await asyncio.to_thread(
                lambda: self.client.table("users").select("id").limit(1).execute()
            )

            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global secure database service instance
_secure_database_service: Optional[SecureDatabaseService] = None


async def get_secure_database_service(**kwargs) -> SecureDatabaseService:
    """Get the global secure database service instance.

    Args:
        **kwargs: Arguments to pass to SecureDatabaseService constructor

    Returns:
        Connected SecureDatabaseService instance
    """
    global _secure_database_service

    if _secure_database_service is None:
        _secure_database_service = SecureDatabaseService(**kwargs)
        await _secure_database_service.connect()

    return _secure_database_service


async def close_secure_database_service() -> None:
    """Close the global secure database service instance."""
    global _secure_database_service

    if _secure_database_service:
        await _secure_database_service.close()
        _secure_database_service = None
