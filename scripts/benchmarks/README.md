# TripSage Comprehensive Benchmarking Suite

A unified performance benchmarking suite that validates all optimization improvements across TripSage's database and caching infrastructure. This consolidates pgvector, general database, and cache performance testing into a single comprehensive framework.

## 🎯 Performance Targets

This benchmark suite validates the following optimization claims:

- **30x pgvector query performance improvement**
- **3x general query performance improvement**
- **<10ms average query latency**
- **50% memory usage reduction**
- **High cache hit ratios (>80%)**
- **Improved connection pool efficiency**

## 📁 Consolidated Structure

```
scripts/benchmarks/
├── README.md                     # This comprehensive guide
├── run_benchmarks.py             # Main CLI for comprehensive validation
├── benchmark_runner.py           # Core benchmark orchestration
├── scenario_manager.py           # Test scenario management
├── metrics_collector.py          # Performance metrics collection
├── report_generator.py           # Report generation and visualization
├── config.py                     # Configuration management
├── Makefile                      # Build and automation
├── pgvector_benchmark.py         # Specialized pgvector benchmarking
├── regression_detector.py        # Regression detection system
├── ci_performance_check.py       # CI/CD integration script
├── dragonfly_performance.py      # Cache performance benchmarking
├── example_usage.py              # Usage examples
# Dependencies managed in main pyproject.toml
```

## 🚀 Quick Start

### Complete Validation Suite

Run the full validation suite to verify all optimization claims:

```bash
# Navigate to the benchmarks directory
cd scripts/benchmarks

# Install benchmark dependencies
uv sync --group benchmark

# Run complete validation (recommended)
python run_benchmarks.py full-validation --output-dir ./results --verbose

# Quick test for development
python run_benchmarks.py quick-test --duration 300
```

### Specialized Testing

Run specific performance tests:

```bash
# Database performance testing
python benchmark_runner.py comparison --verbose

# PGVector-specific testing (30x improvement validation)
python pgvector_benchmark.py --quick --verbose

# Cache performance testing
python dragonfly_performance.py --quick

# CI/CD integration
python ci_performance_check.py full-pipeline --git-commit $GIT_COMMIT
```

## 📊 Benchmark Components

### 1. Comprehensive Database Benchmarking (`benchmark_runner.py`, `scenario_manager.py`)

Main orchestration engine with CLI interface for executing different benchmark types:

- **Baseline vs optimized benchmarks**: Compare performance improvements
- **High-concurrency benchmarks**: Test under load
- **Mixed workload scenarios**: Realistic usage patterns
- **Claims validation**: Validate specific optimization targets

### 2. Specialized PGVector Benchmarking (`pgvector_benchmark.py`)

Dedicated pgvector optimization validation:

- **Index creation benchmarks**: HNSW index performance across data sizes
- **Vector search optimization**: Validate 30x improvement claims
- **Memory profiling**: Track halfvec compression benefits
- **ef_search optimization**: Test various search parameters

### 3. Cache Performance Testing (`dragonfly_performance.py`)

DragonflyDB cache optimization validation:

- **Operation latency**: SET, GET, DELETE performance
- **Throughput testing**: Operations per second
- **Connection pool efficiency**: Pool utilization metrics
- **JSON operation overhead**: Complex data structure performance

### 4. Metrics Collection (`metrics_collector.py`)

Comprehensive performance metrics:

- **Timing metrics**: Query execution with percentile analysis
- **Memory metrics**: Process and system memory tracking
- **Connection metrics**: Pool utilization and efficiency
- **Cache metrics**: Hit ratios and response times

### 5. Regression Detection (`regression_detector.py`)

Automated performance regression detection:

- **Baseline management**: Store and version performance baselines
- **Statistical analysis**: Significance testing for changes
- **Threshold validation**: Configurable regression detection
- **Trend analysis**: Historical performance tracking

### 6. Report Generation (`report_generator.py`)

Detailed performance reporting:

- **HTML reports**: Interactive visualizations with Plotly
- **CSV exports**: Raw data for analysis
- **Performance comparisons**: Before/after metrics
- **Validation summaries**: Claims verification results

## 🎯 Performance Claims Validation

### 1. General Query Performance (3x improvement)
```bash
# Test query performance improvements
python benchmark_runner.py comparison --verbose
```

**Validation criteria:**
- P95 latency reduction of 3x or better
- Throughput improvement of 3x or better
- Error rate remains low (<1%)

### 2. PGVector Performance (30x improvement)
```bash
# Test vector search optimizations
python pgvector_benchmark.py --verbose
```

**Validation criteria:**
- Vector search query time improvement of 30x
- HNSW index performance vs linear scan
- Memory-efficient halfvec compression

### 3. Memory Reduction (50% improvement)
```bash
# Test memory optimization with profiling
python run_benchmarks.py full-validation --verbose
```

**Validation criteria:**
- Peak memory usage reduction of 50%
- Sustained memory efficiency over time
- Reduced memory growth patterns

### 4. Cache Performance
```bash
# Test cache optimization
python dragonfly_performance.py --suites basic,json,connection
```

**Validation criteria:**
- Cache hit ratio >80%
- Cache response time <5ms
- Connection pool efficiency >90%

## 🔧 CLI Reference

### Main Commands

```bash
# Complete validation suite
python run_benchmarks.py full-validation [OPTIONS]

# Quick development testing  
python run_benchmarks.py quick-test [OPTIONS]

# CI/CD integration
python run_benchmarks.py ci-validation [OPTIONS]

# Individual benchmark types
python benchmark_runner.py baseline      # Baseline only
python benchmark_runner.py optimized     # Optimized only
python benchmark_runner.py comparison    # Full comparison
python benchmark_runner.py concurrency   # High concurrency
python benchmark_runner.py validate      # Claims validation

# Specialized benchmarks
python pgvector_benchmark.py [OPTIONS]   # PGVector-specific
python dragonfly_performance.py [OPTIONS] # Cache-specific
python ci_performance_check.py [COMMAND] # CI integration
```

### Common Options

```bash
--output-dir, -o     Output directory for reports (default: ./benchmark_results)
--verbose, -v        Enable verbose logging
--timeout, -t        Total timeout in seconds
--config-file, -c    Custom configuration file
--quick             Enable quick mode (reduced iterations)
```

## 📈 Understanding Results

### Consolidated Reports

The suite generates comprehensive reports combining all performance aspects:

- **Executive Summary**: High-level performance validation overview
- **Database Performance**: Query latency, throughput, and efficiency metrics
- **Vector Search Performance**: HNSW vs baseline comparison
- **Cache Performance**: Hit ratios, latency, and connection efficiency
- **Memory Analysis**: Usage patterns and optimization benefits
- **Regression Analysis**: Performance change detection and trends

### Example Output

```markdown
# TripSage Performance Validation Summary

## Overall Results ✅
- **Database Performance**: 3.2x improvement (Target: 3x) ✅
- **Vector Search Performance**: 32.5x improvement (Target: 30x) ✅  
- **Memory Usage**: 52% reduction (Target: 50%) ✅
- **Cache Hit Ratio**: 87% (Target: 80%) ✅
- **Connection Efficiency**: 94% (Target: 90%) ✅

## Detailed Metrics
| Component | Baseline | Optimized | Improvement | Target Met |
|-----------|----------|-----------|-------------|------------|
| Query P95 Latency | 150ms | 47ms | 3.2x | ✅ |
| Vector Search QPS | 8.5 | 275 | 32.4x | ✅ |
| Memory Usage | 512MB | 245MB | 52% reduction | ✅ |
| Cache Hit Ratio | 45% | 87% | 93% improvement | ✅ |
```

## 🛠️ Advanced Usage

### Custom Configuration

```python
from config import BenchmarkConfig, PerformanceThresholds

config = BenchmarkConfig(
    test_duration_seconds=900,  # 15 minutes
    concurrent_connections=25,
    test_data_size=100000,
    performance_thresholds=PerformanceThresholds(
        query_performance_improvement=5.0,    # Expect 5x improvement
        vector_performance_improvement=50.0,  # Expect 50x improvement
        memory_reduction_target=60.0,         # Expect 60% reduction
        cache_hit_ratio_target=85.0          # Expect 85% hit ratio
    )
)
```

### Custom Scenarios

```python
from config import BenchmarkScenario, WorkloadType, OptimizationLevel

scenario = BenchmarkScenario(
    name="high_load_vector_search",
    workload_type=WorkloadType.VECTOR_SEARCH,
    optimization_level=OptimizationLevel.FULL,
    duration_seconds=600,
    concurrent_users=50,
    operations_per_user=200,
    data_size=100000,
)
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Ensure database service is running
   - Check connection credentials in settings
   - Verify network connectivity

2. **Memory Issues During Testing**
   - Reduce `test_data_size` in configuration
   - Lower `concurrent_connections`
   - Enable memory profiling to identify leaks

3. **Timeout Errors**
   - Increase `timeout` parameter
   - Use `--quick` mode for CI environments
   - Check system resources

4. **Claims Validation Failures**
   - Review performance reports for bottlenecks
   - Check if optimizations are properly applied
   - Validate test environment matches production

### Debug Mode

```bash
# Maximum verbosity with debugging
PYTHONPATH=. python run_benchmarks.py full-validation \
  --verbose \
  --output-dir ./debug_results

# Check specific component logs
tail -f ./debug_results/benchmark.log
tail -f ./debug_results/pgvector.log
tail -f ./debug_results/cache.log
```

## 📊 Integration Points

The consolidated benchmarking suite integrates with:

- **Database Service**: Primary database with read replicas
- **PGVector Optimizer**: HNSW index and compression optimizations
- **DragonflyDB Cache**: Caching layer performance
- **Connection Manager**: Optimized connection pooling
- **Monitoring System**: Performance metrics collection
- **CI/CD Pipelines**: Automated performance validation

## 🤝 Contributing

To extend the benchmarking suite:

1. Add new scenarios in `config.py`
2. Implement custom workloads in `scenario_manager.py`
3. Add metrics in `metrics_collector.py`
4. Extend reporting in `report_generator.py`
5. Update regression thresholds in `regression_detector.py`

## 📄 License

This benchmarking suite is part of the TripSage project and follows the same license terms.

## 🔗 Related Documentation

- [TripSage Database Architecture](../../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)
- [PGVector Service Documentation](../../tripsage_core/services/infrastructure/pgvector_service.py)
- [Performance Profiling Guide](../../docs/04_DEVELOPMENT_GUIDE/PERFORMANCE_PROFILING.md)
- [CI/CD Integration Guide](../../docs/03_ARCHITECTURE/DEPLOYMENT_STRATEGY.md)