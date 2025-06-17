"""
Example usage of the pgvector HNSW optimizer for TripSage.

This script demonstrates all major functionality of the pgvector optimizer:
- Auto-tuning HNSW parameters based on data characteristics
- Creating optimized indexes with different profiles
- Implementing halfvec compression for memory reduction
- Parallel index building with progress monitoring
- Query optimization and performance analysis
- Benchmarking different configurations

Run this script to see optimization recommendations and performance improvements.
"""

import asyncio
import logging
import random

from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.pgvector_optimizer import (
    DistanceFunction,
    HNSWParameters,
    OptimizationProfile,
    ParallelIndexConfig,
    PGVectorOptimizer,
    VectorCompressionConfig,
    quick_optimize_table,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_auto_tuning():
    """Demonstrate automatic parameter tuning based on data characteristics."""
    logger.info("=== Demo: Auto-tuning HNSW Parameters ===")

    try:
        # Initialize database service and optimizer
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        # Example: Auto-tune for a memory table (embeddings from user memories)
        print("\n1. Auto-tuning parameters for memory embeddings...")

        try:
            params = await optimizer.auto_tune_parameters(
                table_name="memories",
                vector_column="embedding",
                sample_size=500,
                target_recall=0.95,
            )

            print("   Recommended parameters:")
            print(f"   - m: {params.m}")
            print(f"   - ef_construction: {params.ef_construction}")
            print(f"   - ef_search: {params.ef_search}")

        except Exception as e:
            print(f"   Note: Auto-tuning requires existing data. Error: {e}")
            print("   Using default balanced parameters for demo...")
            params = HNSWParameters(m=24, ef_construction=100, ef_search=100)

        # Compare with predefined profiles
        print("\n2. Comparing with predefined optimization profiles:")

        profiles = [
            (OptimizationProfile.SPEED, "Optimized for query speed"),
            (OptimizationProfile.BALANCED, "Balanced speed and accuracy"),
            (OptimizationProfile.ACCURACY, "Optimized for accuracy/recall"),
            (OptimizationProfile.MEMORY_EFFICIENT, "Minimizes memory usage"),
            (OptimizationProfile.HIGH_THROUGHPUT, "Optimized for concurrent queries"),
        ]

        for profile, description in profiles:
            profile_params = optimizer.get_optimization_profile(profile)
            print(f"   {profile.value.upper()}: {description}")
            print(
                f"     m={profile_params.m}, "
                f"ef_construction={profile_params.ef_construction}, "
                f"ef_search={profile_params.ef_search}"
            )

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Auto-tuning demo failed: {e}")


async def demo_index_creation():
    """Demonstrate creating optimized HNSW indexes with different configurations."""
    logger.info("=== Demo: Creating Optimized HNSW Indexes ===")

    try:
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        print("\n1. Creating HNSW index with balanced profile...")

        try:
            # Example: Create index for destination embeddings with balanced profile
            index_name = await optimizer.create_optimized_hnsw_index(
                table_name="destinations",  # This table might exist in TripSage
                vector_column="embedding",
                profile=OptimizationProfile.BALANCED,
                distance_function=DistanceFunction.COSINE,
                parallel_config=ParallelIndexConfig(
                    max_parallel_workers=4,
                    maintenance_work_mem="1GB",
                    enable_progress_monitoring=True,
                ),
            )
            print(f"   ✅ Created index: {index_name}")

        except Exception as e:
            print(f"   Note: Index creation requires existing table. Error: {e}")

        print("\n2. Creating index with custom parameters...")

        # Custom parameters for high-accuracy scenario
        custom_params = HNSWParameters(
            m=32,  # Higher connectivity for better accuracy
            ef_construction=200,  # More thorough building process
            ef_search=150,  # More candidates during search
        )

        try:
            index_name = await optimizer.create_optimized_hnsw_index(
                table_name="accommodations",  # Another potential TripSage table
                vector_column="description_embedding",
                parameters=custom_params,
                distance_function=DistanceFunction.L2,
            )
            print(f"   ✅ Created custom index: {index_name}")

        except Exception as e:
            print(f"   Note: Custom index creation requires existing table. Error: {e}")

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Index creation demo failed: {e}")


async def demo_halfvec_compression():
    """Demonstrate halfvec compression for 50% memory reduction."""
    logger.info("=== Demo: halfvec Compression for Memory Optimization ===")

    try:
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        print("\n1. Setting up halfvec compression configuration...")

        # Configuration for converting memory embeddings to halfvec
        compression_config = VectorCompressionConfig(
            enable_compression=True,
            source_column="embedding",
            target_column="embedding_halfvec",
            dimensions=1536,  # OpenAI text-embedding-3-small dimensions
            preserve_original=False,  # Replace original to save space
        )

        print(f"   Source: {compression_config.source_column}")
        print(f"   Target: {compression_config.target_column}")
        print(f"   Dimensions: {compression_config.dimensions}")
        print("   Expected memory reduction: ~50%")

        print("\n2. Compression benefits analysis:")

        # Calculate potential savings
        vector_count = 100000  # Example: 100K memories
        original_size_per_vector = (
            compression_config.dimensions * 4 + 4
        )  # 4 bytes per float + overhead
        halfvec_size_per_vector = (
            compression_config.dimensions * 2 + 4
        )  # 2 bytes per half-float + overhead

        total_original_mb = (vector_count * original_size_per_vector) / (1024 * 1024)
        total_halfvec_mb = (vector_count * halfvec_size_per_vector) / (1024 * 1024)
        savings_mb = total_original_mb - total_halfvec_mb
        savings_percent = (savings_mb / total_original_mb) * 100

        print(
            f"   For {vector_count:,} vectors of {compression_config.dimensions} "
            f"dimensions:"
        )
        print(f"   - Original storage: {total_original_mb:.1f} MB")
        print(f"   - halfvec storage: {total_halfvec_mb:.1f} MB")
        print(f"   - Memory saved: {savings_mb:.1f} MB ({savings_percent:.1f}%)")

        try:
            # Attempt compression (will fail if table doesn't exist)
            success = await optimizer.create_halfvec_compressed_column(
                compression_config
            )
            if success:
                print("   ✅ halfvec compression completed successfully")

        except Exception as e:
            print(
                f"   Note: Compression requires existing table with vector data. "
                f"Error: {e}"
            )

        print("\n3. Creating halfvec-optimized index...")

        try:
            # Create index using halfvec distance function
            index_name = await optimizer.create_optimized_hnsw_index(
                table_name="memories",
                vector_column="embedding_halfvec",
                distance_function=DistanceFunction.HALFVEC_COSINE,
                profile=OptimizationProfile.BALANCED,
            )
            print(f"   ✅ Created halfvec index: {index_name}")

        except Exception as e:
            print(
                f"   Note: halfvec index creation requires existing halfvec column. "
                f"Error: {e}"
            )

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Compression demo failed: {e}")


async def demo_query_optimization():
    """Demonstrate query optimization and performance analysis."""
    logger.info("=== Demo: Query Optimization and Performance Analysis ===")

    try:
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        print("\n1. Simulating query optimization...")

        # Generate a sample query vector (1536 dimensions for OpenAI embeddings)
        query_vector = [random.uniform(-1, 1) for _ in range(1536)]

        print(f"   Query vector dimensions: {len(query_vector)}")
        print(f"   Sample values: {query_vector[:5]}...")

        # Different ef_search values to test
        ef_search_values = [40, 100, 200, 400]

        print("\n2. Testing different ef_search values:")

        for ef_search in ef_search_values:
            try:
                stats = await optimizer.optimize_query_performance(
                    table_name="memories",
                    vector_column="embedding",
                    query_vector=query_vector,
                    ef_search=ef_search,
                    distance_function=DistanceFunction.COSINE,
                )

                print(f"   ef_search={ef_search}:")
                print(f"     - Query time: {stats.avg_query_time:.2f}ms")
                print(f"     - Index hit ratio: {stats.index_hit_ratio:.2%}")
                print(f"     - Memory usage: {stats.memory_usage_mb:.1f}MB")

            except Exception as e:
                print(
                    f"   ef_search={ef_search}: Requires existing table and index. "
                    f"Error: {e}"
                )

        print("\n3. Distance function comparison:")

        distance_functions = [
            (DistanceFunction.L2, "Euclidean (L2) distance"),
            (DistanceFunction.COSINE, "Cosine similarity"),
            (DistanceFunction.IP, "Inner product"),
        ]

        for func, description in distance_functions:
            print(f"   {func.value}: {description}")
            # In real usage, you'd benchmark each distance function

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Query optimization demo failed: {e}")


async def demo_benchmarking():
    """Demonstrate benchmarking different HNSW configurations."""
    logger.info("=== Demo: Benchmarking HNSW Configurations ===")

    try:
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        print("\n1. Setting up benchmark configurations...")

        # Define different configurations to test
        test_configs = [
            HNSWParameters(m=16, ef_construction=64, ef_search=40),  # Speed-optimized
            HNSWParameters(m=24, ef_construction=100, ef_search=100),  # Balanced
            HNSWParameters(
                m=32, ef_construction=200, ef_search=200
            ),  # Accuracy-optimized
        ]

        print(f"   Testing {len(test_configs)} configurations:")
        for i, config in enumerate(test_configs, 1):
            print(
                f"   {i}. m={config.m}, ef_construction={config.ef_construction}, "
                f"ef_search={config.ef_search}"
            )

        # Generate test queries
        test_queries = [
            [random.uniform(-1, 1) for _ in range(1536)]
            for _ in range(5)  # 5 test queries
        ]

        print(f"\n2. Generated {len(test_queries)} test queries for benchmarking")

        try:
            # Run benchmark
            results = await optimizer.benchmark_configurations(
                table_name="memories",
                vector_column="embedding",
                test_queries=test_queries,
                configurations=test_configs,
            )

            print("\n3. Benchmark results (sorted by performance):")

            for i, result in enumerate(results, 1):
                config = result["configuration"]
                print(f"   Rank {i}:")
                print(
                    f"     Parameters: m={config['m']}, "
                    f"ef_construction={config['ef_construction']}, "
                    f"ef_search={config['ef_search']}"
                )
                print(f"     Avg query time: {result['avg_query_time_ms']:.2f}ms")
                print(f"     Queries per second: {result['queries_per_second']:.1f}")
                print(f"     Index size: {result['index_size']}")
                print()

            # Show the winner
            best_config = results[0]["configuration"]
            print("🏆 Best performing configuration:")
            print(
                f"   m={best_config['m']}, "
                f"ef_construction={best_config['ef_construction']}, "
                f"ef_search={best_config['ef_search']}"
            )

        except Exception as e:
            print(
                f"   Note: Benchmarking requires existing table with vector data. "
                f"Error: {e}"
            )

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Benchmarking demo failed: {e}")


async def demo_optimization_recommendations():
    """Demonstrate getting optimization recommendations for existing tables."""
    logger.info("=== Demo: Optimization Recommendations ===")

    try:
        db_service = DatabaseService()
        await db_service.connect()

        optimizer = PGVectorOptimizer(database_service=db_service)

        print("\n1. Analyzing table for optimization opportunities...")

        try:
            recommendations = await optimizer.get_optimization_recommendations(
                table_name="memories", vector_column="embedding"
            )

            print(
                f"\n2. Analysis results for {recommendations['table']}."
                f"{recommendations['column']}:"
            )
            print(f"   Total suggestions: {recommendations['total_suggestions']}")
            print(f"   High priority: {recommendations['high_priority_count']}")

            if recommendations["suggestions"]:
                print("\n3. Recommendations:")

                for i, suggestion in enumerate(recommendations["suggestions"], 1):
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        suggestion["priority"], "⚪"
                    )

                    print(
                        f"   {i}. {priority_icon} {suggestion['type'].upper()} "
                        f"({suggestion['priority']} priority)"
                    )
                    print(f"      Description: {suggestion['description']}")
                    print(
                        f"      Expected improvement: "
                        f"{suggestion['estimated_improvement']}"
                    )
                    print()
            else:
                print(
                    "   ✅ No optimization recommendations - table appears "
                    "well-optimized!"
                )

        except Exception as e:
            print(
                f"   Note: Analysis requires existing table with vector data. "
                f"Error: {e}"
            )

        print("\n4. Current index analysis:")
        try:
            # This would show current index status in real usage
            print("   Checking existing indexes...")
            print("   (Would show HNSW/IVF indexes, parameters, sizes, etc.)")

        except Exception as e:
            print(f"   Note: Index analysis requires existing indexes. Error: {e}")

        await optimizer.cleanup_resources()
        await db_service.close()

    except Exception as e:
        logger.error(f"Recommendations demo failed: {e}")


async def demo_quick_optimization():
    """Demonstrate the quick optimization utility function."""
    logger.info("=== Demo: Quick Table Optimization ===")

    try:
        print("\n1. Running complete optimization workflow...")
        print("   This is the easiest way to optimize a table with sensible defaults:")

        # The quick_optimize_table function does everything automatically
        try:
            results = await quick_optimize_table(
                table_name="memories",
                vector_column="embedding",
                profile=OptimizationProfile.BALANCED,
                enable_compression=True,
            )

            print(
                f"\n2. Optimization completed for {results['table']}."
                f"{results['column']}:"
            )

            for optimization in results["optimizations"]:
                status_icon = "✅" if optimization["status"] == "completed" else "❌"
                print(
                    f"   {status_icon} {optimization['type'].upper()}: "
                    f"{optimization['status']}"
                )

                if "index_name" in optimization:
                    print(f"      Index created: {optimization['index_name']}")
                if "memory_savings" in optimization:
                    print(f"      Memory savings: {optimization['memory_savings']}")

            if results.get("additional_recommendations"):
                print(
                    f"\n3. Additional recommendations: "
                    f"{len(results['additional_recommendations'])} items"
                )
                for rec in results["additional_recommendations"][:3]:  # Show first 3
                    print(f"   - {rec['description']}")

                if len(results["additional_recommendations"]) > 3:
                    print(
                        f"   ... and {len(results['additional_recommendations']) - 3} "
                        f"more"
                    )

        except Exception as e:
            print(
                f"   Note: Quick optimization requires existing table with vector "
                f"data. Error: {e}"
            )

        print("\n🎯 Quick optimization provides:")
        print("   - Automatic parameter tuning based on your data")
        print("   - HNSW index creation with optimal settings")
        print("   - halfvec compression for 50% memory reduction")
        print("   - Additional optimization recommendations")
        print("   - All with a single function call!")

    except Exception as e:
        logger.error(f"Quick optimization demo failed: {e}")


async def main():
    """Run all pgvector optimization demos."""
    print("🚀 TripSage pgvector HNSW Optimizer Demo")
    print("=" * 50)
    print()
    print("This demo showcases advanced pgvector optimization techniques:")
    print("- Automatic HNSW parameter tuning based on data characteristics")
    print("- halfvec compression for 50% memory reduction")
    print("- Parallel index building with progress monitoring")
    print("- Query performance optimization")
    print("- Configuration benchmarking")
    print("- Intelligent optimization recommendations")
    print()
    print("Note: Some demos require existing tables with vector data.")
    print(
        "In a real TripSage environment, these would work with actual "
        "memory/embedding tables."
    )
    print()

    # Run all demos
    demos = [
        ("Auto-tuning Parameters", demo_auto_tuning),
        ("Index Creation", demo_index_creation),
        ("halfvec Compression", demo_halfvec_compression),
        ("Query Optimization", demo_query_optimization),
        ("Configuration Benchmarking", demo_benchmarking),
        ("Optimization Recommendations", demo_optimization_recommendations),
        ("Quick Optimization", demo_quick_optimization),
    ]

    for demo_name, demo_func in demos:
        try:
            print(f"\n{'=' * 20} {demo_name} {'=' * 20}")
            await demo_func()
            print("✅ Demo completed successfully")
        except Exception as e:
            print(f"❌ Demo failed: {e}")

        print("\n" + "-" * 60)

    print("\n🎉 All demos completed!")
    print("\nTo use pgvector optimization in your TripSage application:")
    print(
        "1. Import: from tripsage_core.services.infrastructure.pgvector_optimizer "
        "import PGVectorOptimizer"
    )
    print("2. Initialize: optimizer = PGVectorOptimizer(database_service)")
    print("3. Optimize: await optimizer.create_optimized_hnsw_index(...)")
    print("4. Or use quick optimization: await quick_optimize_table(...)")


if __name__ == "__main__":
    asyncio.run(main())
