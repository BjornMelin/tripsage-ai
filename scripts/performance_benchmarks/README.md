# TripSage Database Performance Benchmarking Suite

This comprehensive benchmarking suite validates the performance improvements achieved by TripSage's database optimization framework. It provides automated testing, measurement, and validation of the claimed performance improvements:

- **3x general query performance improvement**
- **30x pgvector performance improvement** 
- **50% memory reduction**
- **Improved connection pool efficiency**
- **High cache hit ratios**

## 🚀 Quick Start

### Complete Validation Suite

Run the full validation suite to verify all optimization claims:

```bash
# Navigate to the benchmarks directory
cd scripts/performance_benchmarks

# Run complete validation (recommended)
python run_benchmarks.py full-validation --output-dir ./results --verbose

# Quick test for development
python run_benchmarks.py quick-test --scenario vector_search --optimization full --duration 300
```

### CI/CD Integration

For continuous integration pipelines:

```bash
# CI-optimized validation (shorter duration, focused metrics)
python run_benchmarks.py ci-validation --output-dir ./ci_results

# Check exit code for CI success/failure
echo "CI validation result: $?"
```

## 📊 Benchmark Components

### 1. Benchmark Runner (`benchmark_runner.py`)
Main orchestration engine with CLI interface for executing different benchmark types:

- **Baseline benchmarks**: Test performance without optimizations
- **Optimized benchmarks**: Test performance with full optimizations
- **Comparison benchmarks**: Side-by-side performance comparison
- **High-concurrency benchmarks**: Test under load
- **Custom scenarios**: Flexible scenario execution
- **Claims validation**: Validate specific optimization claims

### 2. Scenario Manager (`scenario_manager.py`) 
Manages benchmark scenario execution including:

- **Test data generation**: Realistic travel destination and search query data
- **Environment setup**: Baseline vs optimized database configurations
- **Workload execution**: Read-heavy, vector search, and mixed workloads
- **Database operations**: Realistic CRUD and vector search operations

### 3. Metrics Collector (`metrics_collector.py`)
Comprehensive performance metrics collection:

- **Timing metrics**: Query execution times with percentile analysis
- **Memory metrics**: Process and system memory usage tracking
- **Connection metrics**: Pool utilization and efficiency monitoring
- **Vector search metrics**: HNSW vs baseline performance comparison
- **Cache metrics**: Hit ratios and response time analysis

### 4. Report Generator (`report_generator.py`)
Generates detailed performance reports:

- **HTML reports**: Interactive visualizations with Plotly charts
- **CSV exports**: Raw data for further analysis
- **Performance comparisons**: Before/after optimization metrics
- **Validation summaries**: Claims verification results

### 5. Configuration (`config.py`)
Flexible configuration system:

- **Performance thresholds**: Expected improvement targets
- **Benchmark scenarios**: Predefined and custom test scenarios
- **Optimization levels**: None, Basic, Advanced, Full
- **Workload types**: Read-heavy, Vector search, Mixed operations

## 🎯 Performance Claims Validation

The suite validates these specific optimization claims:

### 1. General Query Performance (3x improvement)
```bash
# Test query performance improvements
python benchmark_runner.py comparison --verbose
```

**Validation criteria:**
- P95 latency reduction of 3x or better
- Throughput improvement of 3x or better
- Error rate remains low (<1%)

### 2. pgvector Performance (30x improvement)
```bash
# Test vector search optimizations
python benchmark_runner.py custom --workload vector_search --optimization full
```

**Validation criteria:**
- Vector search query time improvement of 30x
- HNSW index performance vs linear scan
- Memory-efficient halfvec compression

### 3. Memory Reduction (50% improvement)
```bash
# Test memory optimization with profiling enabled
python run_benchmarks.py full-validation --verbose
```

**Validation criteria:**
- Peak memory usage reduction of 50%
- Sustained memory efficiency
- Reduced memory growth over time

### 4. Connection Pool Efficiency
```bash
# Test connection optimization
python benchmark_runner.py concurrency
```

**Validation criteria:**
- Connection reuse ratio >90%
- Pool utilization >85%
- Reduced connection wait times

### 5. Cache Effectiveness
```bash
# Test cache performance
python benchmark_runner.py comparison --verbose
```

**Validation criteria:**
- Cache hit ratio >80%
- Cache response time <5ms
- Effective cache invalidation

## 📈 Understanding Results

### HTML Reports

The suite generates comprehensive HTML reports with:

- **Performance Overview**: Key metrics and improvement ratios
- **Detailed Comparisons**: Baseline vs optimized performance
- **Visualizations**: Interactive charts showing performance trends
- **Validation Summary**: Claims verification with pass/fail status

### CSV Exports

Raw data exports include:
- Individual operation timings
- Memory usage over time
- Connection pool metrics
- Vector search performance data

### Validation Results

Claims validation provides:
- **Improvement ratios**: Measured vs claimed improvements
- **Threshold compliance**: Pass/fail for each claim
- **Confidence levels**: High/medium/low confidence in measurements
- **Recommendations**: Actions for failed validations

## 🔧 Advanced Usage

### Custom Scenarios

Create custom benchmark scenarios:

```python
from config import BenchmarkScenario, WorkloadType, OptimizationLevel

scenario = BenchmarkScenario(
    name="custom_high_load",
    description="High-load vector search test",
    workload_type=WorkloadType.VECTOR_SEARCH,
    optimization_level=OptimizationLevel.FULL,
    duration_seconds=600,
    concurrent_users=50,
    operations_per_user=200,
    data_size=50000,
)

runner = BenchmarkRunner()
results = await runner.execute_scenario(scenario)
```

### Configuration Customization

```python
from config import BenchmarkConfig, PerformanceThresholds

config = BenchmarkConfig(
    test_duration_seconds=900,  # 15 minutes
    concurrent_connections=25,
    test_data_size=100000,
    performance_thresholds=PerformanceThresholds(
        query_performance_improvement=5.0,  # Expect 5x improvement
        vector_performance_improvement=50.0,  # Expect 50x improvement
    )
)
```

### Geographic Distribution Testing

Enable geographic routing performance testing:

```python
config = BenchmarkConfig(
    simulate_geographic_distribution=True,
    test_regions=["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
)
```

## 🛠️ CLI Reference

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
```

### Options

```bash
--output-dir, -o     Output directory for reports (default: ./benchmark_results)
--verbose, -v        Enable verbose logging
--timeout, -t        Total timeout in seconds
--config-file, -c    Custom configuration file
```

### Custom Scenario Options

```bash
--name, -n           Scenario name
--workload, -w       Workload type (read_heavy|vector_search|mixed)
--optimization       Optimization level (none|basic|advanced|full)
--duration, -d       Test duration in seconds
--users, -u          Concurrent users
--operations         Operations per user
```

## 📋 Example Workflows

### Development Testing

```bash
# Quick vector search performance test
python run_benchmarks.py quick-test \
  --scenario vector_search \
  --optimization full \
  --duration 180 \
  --users 10

# Validate specific optimization after code changes
python benchmark_runner.py custom \
  --name "post_optimization_test" \
  --workload mixed \
  --optimization full \
  --duration 300
```

### Pre-Production Validation

```bash
# Complete validation before deployment
python run_benchmarks.py full-validation \
  --output-dir ./production_validation \
  --timeout 7200 \
  --verbose

# Check all claims are met
python benchmark_runner.py validate
```

### CI/CD Pipeline Integration

```bash
# In CI pipeline
python run_benchmarks.py ci-validation --output-dir ./ci_results

# Check results
if [ $? -eq 0 ]; then
  echo "✅ Performance validation passed"
else
  echo "❌ Performance validation failed"
  exit 1
fi
```

### Performance Monitoring

```bash
# Regular performance monitoring
python benchmark_runner.py comparison \
  --output-dir "./monitoring/$(date +%Y%m%d_%H%M%S)" \
  --verbose

# Generate trending reports
python benchmark_runner.py baseline --output-dir ./baseline_$(date +%Y%m%d)
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
   - Reduce test duration for CI environments
   - Check system resources

4. **Claims Validation Failures**
   - Review performance reports for bottlenecks
   - Check if optimizations are properly applied
   - Validate test environment matches production

### Debug Mode

Enable detailed debugging:

```bash
# Maximum verbosity
PYTHONPATH=. python run_benchmarks.py full-validation \
  --verbose \
  --output-dir ./debug_results

# Check logs
tail -f ./debug_results/benchmark.log
```

## 📊 Performance Targets

The benchmarking suite validates against these specific targets:

| Metric | Baseline | Optimized | Target Improvement |
|--------|----------|-----------|-------------------|
| Query P95 Latency | ~150ms | ~50ms | 3x faster |
| Vector Search QPS | ~10 qps | ~300 qps | 30x faster |
| Memory Usage | ~500MB | ~250MB | 50% reduction |
| Connection Efficiency | ~60% reuse | ~90% reuse | 85% target |
| Cache Hit Ratio | ~40% | ~80% | 80% target |

## 🔗 Integration Points

The benchmarking suite integrates with:

- **Database Service**: Primary database with read replicas
- **pgvector Optimizer**: HNSW index and compression optimizations
- **Cache Service**: DragonflyDB caching layer
- **Connection Manager**: Optimized connection pooling
- **Monitoring System**: Performance metrics collection

## 📝 Report Examples

See the generated reports for detailed examples:
- `./results/comparison_report.html` - Complete performance comparison
- `./results/validation_report.html` - Claims validation summary
- `./results/performance_data.csv` - Raw performance data

## 🤝 Contributing

To extend the benchmarking suite:

1. Add new scenarios in `config.py`
2. Implement custom workloads in `scenario_manager.py`
3. Add metrics in `metrics_collector.py`
4. Extend reporting in `report_generator.py`

## 📄 License

This benchmarking suite is part of the TripSage project and follows the same license terms.