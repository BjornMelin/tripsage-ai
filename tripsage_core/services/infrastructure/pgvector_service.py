"""
PGVector service for TripSage based on 2025 research findings.

This service provides production-ready pgvector optimization using proven defaults
and industry best practices. Replaces the complex PGVectorOptimizer with a focused,
maintainable approach.

Key principles:
- Use pgvector defaults (they're well-tuned)
- Focus on ef_search adjustment for query optimization
- Provide simple index creation and monitoring
- Follow PostgreSQL and pgvector best practices
- Integrate seamlessly with Mem0 memory service
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DistanceFunction(str, Enum):
    """Standard pgvector distance functions."""

    L2 = "vector_l2_ops"
    COSINE = "vector_cosine_ops"
    INNER_PRODUCT = "vector_ip_ops"


class OptimizationProfile(str, Enum):
    """Optimization profiles based on research."""

    SPEED = "speed"  # Use defaults: fast queries, good enough accuracy
    BALANCED = "balanced"  # Slightly better recall: ef_search=100
    QUALITY = "quality"  # Best recall: ef_construction=100, ef_search=200


class IndexConfig(BaseModel):
    """Configuration for HNSW index creation."""

    m: int = Field(default=16, description="HNSW connections per layer (keep default)")
    ef_construction: int = Field(
        default=64, description="Build quality (keep default unless quality profile)"
    )
    ef_search: int = Field(default=40, description="Query quality (adjust per query)")


class IndexStats(BaseModel):
    """Index performance statistics."""

    index_name: str
    index_size_bytes: int
    index_size_human: str
    row_count: int
    index_usage_count: int
    last_used: Optional[str] = None


class PGVectorService:
    """
    Production pgvector service focused on essential operations.

    Based on 2025 research findings that show pgvector defaults are well-tuned
    for most use cases. Provides the 20% of functionality that delivers 80% of
    the value with maximum maintainability.

    Integrates seamlessly with Mem0 memory service for AI conversation context.
    """

    def __init__(self, database_service):
        """Initialize with database service."""
        self.db = database_service
        self._profiles = self._create_profiles()

    def _create_profiles(self) -> Dict[OptimizationProfile, IndexConfig]:
        """Create optimization profiles based on research."""
        return {
            OptimizationProfile.SPEED: IndexConfig(
                m=16, ef_construction=64, ef_search=40
            ),
            OptimizationProfile.BALANCED: IndexConfig(
                m=16, ef_construction=64, ef_search=100
            ),
            OptimizationProfile.QUALITY: IndexConfig(
                m=16, ef_construction=100, ef_search=200
            ),
        }

    async def create_hnsw_index(
        self,
        table_name: str,
        column_name: str,
        distance_function: DistanceFunction = DistanceFunction.COSINE,
        profile: OptimizationProfile = OptimizationProfile.BALANCED,
        index_name: Optional[str] = None,
    ) -> str:
        """
        Create HNSW index with standard parameters.

        Args:
            table_name: Target table
            column_name: Vector column to index
            distance_function: Distance function to use
            profile: Optimization profile (speed/balanced/quality)
            index_name: Custom index name (auto-generated if None)

        Returns:
            Created index name
        """
        if not index_name:
            distance_suffix = distance_function.value.split("_")[1]  # l2, cosine, ip
            index_name = f"idx_{table_name}_{column_name}_{distance_suffix}_hnsw"

        config = self._profiles[profile]

        # Use CONCURRENTLY for production safety
        create_sql = f"""
            CREATE INDEX CONCURRENTLY {index_name}
            ON {table_name}
            USING hnsw ({column_name} {distance_function.value})
        """

        # Only specify non-default parameters to keep it simple
        if config.ef_construction != 64:  # Default is 64
            create_sql += f" WITH (ef_construction = {config.ef_construction})"

        logger.info(f"Creating HNSW index {index_name} on {table_name}.{column_name}")
        await self.db.execute_sql(create_sql)

        # Set default ef_search if not using default
        if config.ef_search != 40:  # Default is 40
            await self._set_default_ef_search(config.ef_search)

        logger.info(f"Successfully created HNSW index {index_name}")
        return index_name

    async def set_query_quality(self, ef_search: int = 100) -> None:
        """
        Set ef_search for better query recall.

        Use this to adjust query quality vs speed tradeoff:
        - 40 (default): Fast queries, good accuracy
        - 100: Slower queries, better accuracy
        - 200: Slowest queries, best accuracy

        Args:
            ef_search: Number of candidates to examine during search
        """
        await self.db.execute_sql(f"SET hnsw.ef_search = {ef_search}")
        logger.info(f"Set ef_search to {ef_search} for improved query quality")

    async def reset_query_settings(self) -> None:
        """Reset query settings to defaults."""
        await self.db.execute_sql("RESET hnsw.ef_search")
        logger.info("Reset query settings to defaults")

    async def get_index_stats(
        self, table_name: str, column_name: str
    ) -> Optional[IndexStats]:
        """
        Get index performance statistics.

        Args:
            table_name: Target table
            column_name: Vector column

        Returns:
            Index statistics or None if no index exists
        """
        stats_sql = """
            SELECT 
                i.relname as index_name,
                pg_relation_size(i.oid) as index_size_bytes,
                pg_size_pretty(pg_relation_size(i.oid)) as index_size_human,
                c.reltuples::bigint as row_count,
                COALESCE(s.idx_scan, 0) as index_usage_count,
                s.last_idx_scan::text as last_used
            FROM pg_class i
            JOIN pg_index idx ON idx.indexrelid = i.oid
            JOIN pg_class t ON t.oid = idx.indrelid
            JOIN pg_am am ON i.relam = am.oid
            LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = i.oid
            LEFT JOIN pg_attribute a ON a.attrelid = t.oid 
                AND a.attnum = ANY(idx.indkey)
            WHERE t.relname = $1 
              AND a.attname = $2
              AND am.amname = 'hnsw'
            LIMIT 1
        """

        result = await self.db.execute_sql(stats_sql, (table_name, column_name))

        if not result:
            return None

        row = result[0]
        return IndexStats(
            index_name=row["index_name"],
            index_size_bytes=row["index_size_bytes"],
            index_size_human=row["index_size_human"],
            row_count=row["row_count"],
            index_usage_count=row["index_usage_count"],
            last_used=row["last_used"],
        )

    async def check_index_health(
        self, table_name: str, column_name: str
    ) -> Dict[str, Any]:
        """
        Check index health and provide recommendations.

        Args:
            table_name: Target table
            column_name: Vector column

        Returns:
            Health report with status and recommendations
        """
        stats = await self.get_index_stats(table_name, column_name)

        if not stats:
            return {
                "status": "missing",
                "message": f"No HNSW index found on {table_name}.{column_name}",
                "recommendations": [
                    "Create HNSW index for better query performance",
                    f"Run: await service.create_hnsw_index("
                    f"'{table_name}', '{column_name}')",
                ],
            }

        recommendations = []

        # Check if index is being used
        if stats.index_usage_count == 0:
            recommendations.append("Index is not being used - check query patterns")

        # Check index size vs row count (rough heuristic)
        if stats.row_count > 0:
            bytes_per_row = stats.index_size_bytes / stats.row_count
            if bytes_per_row > 1000:  # More than 1KB per row might indicate issues
                recommendations.append(
                    "Index size seems large - consider data analysis"
                )

        # Size-based recommendations
        if stats.index_size_bytes > 1024 * 1024 * 1024:  # > 1GB
            recommendations.append(
                "Large index - consider ef_search adjustment for performance"
            )

        status = "healthy" if not recommendations else "needs_attention"

        return {
            "status": status,
            "index_name": stats.index_name,
            "size": stats.index_size_human,
            "rows": stats.row_count,
            "usage_count": stats.index_usage_count,
            "last_used": stats.last_used,
            "recommendations": recommendations,
        }

    async def optimize_for_table(
        self, table_name: str, column_name: str, expected_query_load: str = "medium"
    ) -> Dict[str, Any]:
        """
        One-click optimization for a table.

        Args:
            table_name: Target table
            column_name: Vector column
            expected_query_load: "low", "medium", or "high"

        Returns:
            Optimization results
        """
        results = {"table": table_name, "column": column_name, "actions": []}

        # Choose profile based on expected load
        profile_map = {
            "low": OptimizationProfile.SPEED,
            "medium": OptimizationProfile.BALANCED,
            "high": OptimizationProfile.QUALITY,
        }
        profile = profile_map.get(expected_query_load, OptimizationProfile.BALANCED)

        # Check if index exists
        stats = await self.get_index_stats(table_name, column_name)

        if not stats:
            # Create index
            index_name = await self.create_hnsw_index(
                table_name, column_name, profile=profile
            )
            results["actions"].append(
                {
                    "action": "created_index",
                    "index_name": index_name,
                    "profile": profile.value,
                }
            )
        else:
            results["actions"].append(
                {
                    "action": "index_exists",
                    "index_name": stats.index_name,
                    "size": stats.index_size_human,
                }
            )

        # Set appropriate ef_search for expected load
        config = self._profiles[profile]
        if config.ef_search != 40:  # Only if not default
            await self.set_query_quality(config.ef_search)
            results["actions"].append(
                {"action": "set_ef_search", "value": config.ef_search}
            )

        # Add recommendations
        health = await self.check_index_health(table_name, column_name)
        if health["recommendations"]:
            results["additional_recommendations"] = health["recommendations"]

        return results

    async def optimize_memory_tables(self) -> Dict[str, Any]:
        """
        Optimize all memory-related tables for Mem0 integration.

        This method identifies and optimizes vector tables commonly used
        by the memory service for conversation context and user preferences.

        Returns:
            Optimization results for all memory tables
        """
        results = {"memory_optimization": [], "errors": []}

        # Common memory table patterns
        memory_table_patterns = [
            ("memories", "embedding"),
            ("conversations", "embedding"),
            ("user_context", "embedding"),
            ("chat_history", "vector_content"),
            ("travel_preferences", "preference_vector"),
        ]

        for table_name, column_name in memory_table_patterns:
            try:
                # Check if table and column exist
                table_check_sql = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """
                table_exists = await self.db.execute_sql(table_check_sql, (table_name,))

                if not table_exists or not table_exists[0][0]:
                    continue

                column_check_sql = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = $1 
                        AND column_name = $2
                        AND data_type LIKE '%vector%'
                    )
                """
                column_exists = await self.db.execute_sql(
                    column_check_sql, (table_name, column_name)
                )

                if not column_exists or not column_exists[0][0]:
                    continue

                # Optimize for memory workloads (balanced profile)
                optimization_result = await self.optimize_for_table(
                    table_name, column_name, "medium"
                )
                optimization_result["table_type"] = "memory"
                results["memory_optimization"].append(optimization_result)

            except Exception as e:
                results["errors"].append(
                    {"table": table_name, "column": column_name, "error": str(e)}
                )
                logger.warning(f"Failed to optimize {table_name}.{column_name}: {e}")

        return results

    async def _set_default_ef_search(self, ef_search: int) -> None:
        """Set default ef_search for new connections."""
        try:
            # Set for current session
            await self.db.execute_sql(f"SET hnsw.ef_search = {ef_search}")
            logger.info(f"Set session ef_search to {ef_search}")
        except Exception as e:
            logger.warning(f"Could not set default ef_search: {e}")

    async def list_vector_tables(self) -> list[Dict[str, Any]]:
        """
        Find tables with vector columns that could benefit from HNSW indexes.

        Returns:
            List of tables with vector columns and their index status
        """
        tables_sql = """
            SELECT 
                t.table_name,
                c.column_name,
                CASE 
                    WHEN i.indexname IS NOT NULL THEN 'indexed'
                    ELSE 'no_index'
                END as index_status
            FROM information_schema.tables t
            JOIN information_schema.columns c ON c.table_name = t.table_name
            LEFT JOIN pg_indexes i ON i.tablename = t.table_name 
                AND i.indexdef LIKE '%hnsw%' 
                AND i.indexdef LIKE '%' || c.column_name || '%'
            WHERE t.table_schema = 'public'
              AND c.data_type LIKE '%vector%'
            ORDER BY t.table_name, c.column_name
        """

        result = await self.db.execute_sql(tables_sql)
        return [dict(row) for row in result] if result else []


# Utility function for quick optimization
async def optimize_vector_table(
    database_service, table_name: str, column_name: str, query_load: str = "medium"
) -> Dict[str, Any]:
    """
    Quick optimization utility - one function call to optimize a vector table.

    Args:
        database_service: Database service instance
        table_name: Target table
        column_name: Vector column
        query_load: Expected query load ("low", "medium", "high")

    Returns:
        Optimization results
    """
    service = PGVectorService(database_service)
    return await service.optimize_for_table(table_name, column_name, query_load)


# Export main classes and functions
__all__ = [
    "PGVectorService",
    "DistanceFunction",
    "OptimizationProfile",
    "IndexConfig",
    "IndexStats",
    "optimize_vector_table",
]
