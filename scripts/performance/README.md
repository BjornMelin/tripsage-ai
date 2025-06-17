# PGVector Performance Benchmark Suite

A comprehensive performance benchmarking and regression detection system for TripSage's pgvector database optimizations. This suite validates the claimed performance improvements and provides automated CI/CD integration for continuous performance monitoring.

## 🎯 Performance Targets

This benchmark suite validates the following optimization claims:

- **30x pgvector query performance improvement**
- **<10ms average query latency**
- **30% memory usage reduction**
- **Reproducible baseline metrics**
- **Automated regression detection**

## 📁 Project Structure

```
scripts/performance/
├── README.md                     # This file
├── pgvector_benchmark.py         # Main benchmark framework
├── regression_detector.py        # Regression detection system
├── ci_performance_check.py       # CI/CD integration script
├── requirements.txt              # Python dependencies
└── examples/                     # Usage examples
    ├── basic_benchmark.py
    ├── ci_integration.py
    └── regression_analysis.py
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
cd scripts/performance
pip install -r requirements.txt

# Or using uv (recommended)
uv pip install -r requirements.txt
```

### 2. Basic Benchmark

Run a comprehensive performance benchmark:

```bash
# Full benchmark (takes 15-30 minutes)
python pgvector_benchmark.py

# Quick benchmark for development (takes 2-5 minutes)
python pgvector_benchmark.py --quick --verbose

# Custom output directory
python pgvector_benchmark.py --output ./my_results
```

### 3. CI/CD Integration

For continuous integration pipelines:

```bash
# Complete CI pipeline (benchmark + validation)
python ci_performance_check.py full-pipeline --git-commit $GIT_COMMIT

# Just run benchmark
python ci_performance_check.py benchmark --quick

# Just validate against baselines
python ci_performance_check.py validate --update-baseline
```

## 📊 Benchmark Components

### Core Framework (`pgvector_benchmark.py`)

The main benchmarking framework that provides:

- **Index Creation Benchmarks**: Test HNSW index creation performance across different data sizes
- **Query Performance Tests**: Measure query latency and throughput with various ef_search values
- **Memory Usage Profiling**: Track memory consumption before/after optimizations
- **Performance Comparison**: Calculate improvement ratios and validate targets
- **Comprehensive Reporting**: Generate detailed HTML and markdown reports

#### Configuration Options

```python
config = BenchmarkConfig(
    # Test data configuration
    vector_dimensions=384,           # Embedding dimensions
    small_dataset_size=1000,         # Small test dataset
    medium_dataset_size=10000,       # Medium test dataset  
    large_dataset_size=50000,        # Large test dataset
    
    # Performance test parameters
    warmup_queries=50,               # Warmup iterations
    benchmark_queries=200,           # Benchmark iterations
    concurrent_connections=10,       # Concurrent connections
    query_timeout_seconds=30,        # Query timeout
    
    # Index configuration
    ef_search_values=[40, 100, 200, 400],  # ef_search values to test
    optimization_profiles=[...],     # Profiles to test
    distance_functions=[...],        # Distance functions to test
    
    # Performance targets
    target_query_latency_ms=10.0,    # Target: <10ms average latency
    target_memory_reduction_pct=30.0, # Target: 30% memory reduction
    target_performance_improvement_x=30.0, # Target: 30x improvement
    
    # Output configuration
    output_directory="./benchmark_results",
    generate_detailed_report=True,
    export_raw_data=True
)
```

### Regression Detection (`regression_detector.py`)

Automated regression detection system that provides:

- **Baseline Management**: Store and version performance baselines
- **Statistical Analysis**: Statistical significance testing for performance changes
- **Threshold Validation**: Configurable regression detection thresholds
- **Trend Analysis**: Historical performance trend tracking
- **Automated Alerting**: Generate alerts for performance regressions

#### Regression Thresholds

```python
thresholds = RegressionThresholds(
    # Performance degradation thresholds
    max_latency_degradation_pct=20.0,     # 20% latency increase = regression
    min_throughput_degradation_pct=15.0,  # 15% throughput decrease = regression
    max_memory_increase_pct=25.0,         # 25% memory increase = regression
    
    # Absolute thresholds
    max_acceptable_latency_ms=15.0,       # Never exceed 15ms average
    min_acceptable_qps=50.0,              # Never drop below 50 QPS
    
    # Statistical significance
    confidence_level=0.95,                # 95% confidence for tests
    min_samples_for_stats=5               # Minimum samples for analysis
)
```

### CI/CD Integration (`ci_performance_check.py`)

Streamlined CI/CD integration with:

- **Fast Execution**: Optimized for CI pipeline speed
- **Clear Exit Codes**: Pass/fail status for pipeline integration
- **Artifact Generation**: Performance reports and dashboards
- **Baseline Management**: Automatic baseline updates for main branch
- **Notification Support**: Integration with CI/CD notification systems

## 🔧 Usage Examples

### Development Testing

Quick performance validation during development:

```python
import asyncio
from pgvector_benchmark import run_benchmark

# Run quick benchmark
results = await run_benchmark(
    output_dir="./dev_results",
    quick_test=True,
    verbose=True
)

print(f"Average latency: {results.optimized_query_metrics[0].avg_latency_ms:.2f}ms")
print(f"Queries per second: {results.optimized_query_metrics[0].queries_per_second:.1f}")
```

### Baseline Management

Set up and manage performance baselines:

```python
from regression_detector import BaselineManager

# Initialize baseline manager
manager = BaselineManager("./my_baselines")

# Save a baseline
performance_data = {
    "avg_latency_ms": 8.5,
    "p95_latency_ms": 12.0,
    "queries_per_second": 180.0,
    "memory_usage_mb": 350.0,
    "success_rate": 1.0
}

manager.save_baseline("optimized_queries", performance_data, "v2.1.0")

# Load latest baseline
baseline = manager.get_latest_baseline("optimized_queries")
print(f"Baseline version: {baseline.test_version}")
print(f"Baseline latency: {baseline.avg_latency_ms}ms")
```

### Regression Analysis

Analyze performance for regressions:

```python
from regression_detector import RegressionDetector, BaselineManager

# Setup
manager = BaselineManager("./baselines")
detector = RegressionDetector(manager)

# Analyze current performance
current_results = {
    "avg_latency_ms": 12.0,      # Higher than baseline
    "queries_per_second": 150.0,  # Lower than baseline
    "memory_usage_mb": 380.0,    # Higher than baseline
    "success_rate": 1.0
}

analysis = detector.analyze_performance("optimized_queries", current_results)

if analysis.overall_regression:
    print(f"⚠️ Regression detected! Severity: {analysis.severity}")
    for recommendation in analysis.recommendations:
        print(f"- {recommendation}")
else:
    print("✅ No regression detected")
```

### CI/CD Pipeline Integration

#### GitHub Actions Example

```yaml
name: Performance Validation
on: [push, pull_request]

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd scripts/performance
          pip install -r requirements.txt
      
      - name: Run performance benchmark
        run: |
          cd scripts/performance
          python ci_performance_check.py full-pipeline \
            --git-commit ${{ github.sha }} \
            --update-baseline ${{ github.ref == 'refs/heads/main' && 'true' || 'false' }} \
            --quick
      
      - name: Upload performance reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: performance-reports
          path: scripts/performance/ci_performance_results/artifacts/
```

#### GitLab CI Example

```yaml
performance-test:
  stage: test
  image: python:3.11
  before_script:
    - cd scripts/performance
    - pip install -r requirements.txt
  script:
    - |
      python ci_performance_check.py full-pipeline \
        --git-commit $CI_COMMIT_SHA \
        --update-baseline $(if [ "$CI_COMMIT_REF_NAME" = "main" ]; then echo "true"; else echo "false"; fi) \
        --quick
  artifacts:
    when: always
    paths:
      - scripts/performance/ci_performance_results/artifacts/
    reports:
      junit: scripts/performance/ci_performance_results/artifacts/test_results.xml
  only:
    - merge_requests
    - main
```

## 📈 Understanding Results

### Performance Reports

The benchmark suite generates several types of reports:

#### 1. Executive Summary

High-level overview of performance validation:

```markdown
## Executive Summary

✅ **Performance Target Met:** 30x improvement achieved
✅ **Latency Target Met:** <10ms query latency achieved  
✅ **Memory Target Met:** 35% reduction achieved

## Performance Improvements

- **Query Latency Improvement:** 32.5x
- **Throughput Improvement:** 28.7x
- **Memory Reduction:** 35%
```

#### 2. Detailed Metrics

Comprehensive performance data:

| Test | ef_search | Avg Latency (ms) | P95 Latency (ms) | QPS | Memory (MB) |
|------|-----------|------------------|------------------|-----|-------------|
| Baseline | 40 | 150.2 | 280.5 | 6.7 | 512 |
| Optimized (ef=40) | 40 | 4.6 | 8.2 | 217 | 334 |
| Optimized (ef=100) | 100 | 6.8 | 12.1 | 147 | 345 |
| Optimized (ef=200) | 200 | 9.2 | 16.4 | 108 | 358 |

#### 3. Regression Analysis

Performance change analysis:

```markdown
### Performance Changes:
- Latency: -96.9% (150.2ms → 4.6ms)
- Throughput: +3140% (6.7 → 217 QPS)  
- Memory: -34.8% (512 → 334 MB)

### Validation Results:
✅ Query latency target (4.6ms < 10ms)
✅ Performance improvement target (32.5x > 30x)
✅ Memory reduction target (34.8% > 30%)
```

### Performance Artifacts

Generated artifacts for CI/CD integration:

- `benchmark_raw_data.json` - Complete raw performance data
- `benchmark_summary.md` - Human-readable summary report
- `regression_report.md` - Detailed regression analysis
- `ci_summary.md` - CI-optimized summary for dashboards
- `benchmark.log` - Detailed execution logs

## ⚙️ Configuration Guide

### Environment Variables

```bash
# Database configuration
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-key"

# Performance tuning
export BENCHMARK_QUICK_MODE="true"           # Enable quick mode
export BENCHMARK_TIMEOUT="1800"             # 30 minute timeout
export BENCHMARK_CONNECTIONS="10"           # Concurrent connections
export BENCHMARK_MEMORY_PROFILING="true"    # Enable memory profiling

# CI/CD integration
export CI_BASELINE_DIR="./ci_baselines"     # Baseline storage
export CI_OUTPUT_DIR="./ci_results"         # Results output
export CI_UPDATE_BASELINE="false"           # Update baseline flag
```

### Advanced Configuration

#### Custom Benchmark Scenarios

```python
from pgvector_benchmark import BenchmarkConfig, PGVectorBenchmark
from tripsage_core.services.infrastructure.pgvector_service import OptimizationProfile

# Create custom configuration
config = BenchmarkConfig(
    # Focus on high-performance scenario
    ef_search_values=[200, 400, 800],
    optimization_profiles=[OptimizationProfile.QUALITY],
    benchmark_queries=500,
    concurrent_connections=20,
    
    # Strict performance targets
    target_query_latency_ms=5.0,
    target_performance_improvement_x=50.0,
    
    # Custom dataset sizes for large-scale testing
    small_dataset_size=5000,
    medium_dataset_size=50000,
    large_dataset_size=200000
)

# Run custom benchmark
benchmark = PGVectorBenchmark(config)
results = await benchmark.run_full_benchmark()
```

#### Custom Regression Thresholds

```python
from regression_detector import RegressionThresholds, RegressionDetector

# Create strict regression thresholds
thresholds = RegressionThresholds(
    max_latency_degradation_pct=10.0,     # Very sensitive to latency changes
    min_throughput_degradation_pct=5.0,   # Very sensitive to throughput changes
    max_memory_increase_pct=15.0,         # Strict memory monitoring
    max_acceptable_latency_ms=8.0,        # Stricter absolute limit
    confidence_level=0.99                 # Higher statistical confidence
)

detector = RegressionDetector(baseline_manager, thresholds)
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Database Connection Failures

```bash
# Check database connectivity
python -c "
from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService
import asyncio

async def test_connection():
    db = DatabaseService(get_settings())
    await db.connect()
    print('✅ Database connection successful')
    await db.disconnect()

asyncio.run(test_connection())
"
```

#### 2. Memory Issues During Testing

```python
# Reduce test parameters for memory-constrained environments
config = BenchmarkConfig(
    small_dataset_size=100,      # Reduce dataset sizes
    medium_dataset_size=1000,
    large_dataset_size=5000,
    concurrent_connections=5,     # Reduce concurrency
    enable_memory_profiling=False # Disable memory profiling
)
```

#### 3. Timeout Errors

```bash
# Increase timeout for slow environments
export BENCHMARK_TIMEOUT="3600"  # 1 hour timeout

# Or use quick mode
python pgvector_benchmark.py --quick
```

#### 4. Missing Baselines

```bash
# Setup initial baseline
python regression_detector.py setup-baseline results.json ./baselines initial

# Or run with baseline update
python ci_performance_check.py validate --update-baseline
```

### Debug Mode

Enable detailed debugging:

```bash
# Maximum verbosity
PYTHONPATH=. python pgvector_benchmark.py --verbose 2>&1 | tee debug.log

# Check execution logs
tail -f ./benchmark_results/benchmark.log

# Analyze memory usage
python -c "
import psutil
import time
process = psutil.Process()
while True:
    print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    time.sleep(5)
"
```

### Performance Optimization

#### Optimize Database Settings

```sql
-- Increase work_mem for large vector operations
SET work_mem = '256MB';

-- Increase maintenance_work_mem for index creation
SET maintenance_work_mem = '1GB';

-- Optimize for vector operations
SET shared_preload_libraries = 'vector';
SET max_parallel_workers_per_gather = 4;
```

#### Optimize System Resources

```bash
# Increase file descriptor limits
ulimit -n 65536

# Increase memory limits
ulimit -m unlimited

# Set CPU affinity for consistent performance
taskset -c 0-3 python pgvector_benchmark.py
```

## 📚 API Reference

### Main Classes

#### BenchmarkConfig

Configuration class for benchmark execution.

```python
class BenchmarkConfig:
    vector_dimensions: int = 384
    small_dataset_size: int = 1000
    medium_dataset_size: int = 10000
    large_dataset_size: int = 50000
    warmup_queries: int = 50
    benchmark_queries: int = 200
    concurrent_connections: int = 10
    query_timeout_seconds: int = 30
    target_query_latency_ms: float = 10.0
    target_memory_reduction_pct: float = 30.0
    target_performance_improvement_x: float = 30.0
    output_directory: str = "./benchmark_results"
    generate_detailed_report: bool = True
    export_raw_data: bool = True
```

#### PGVectorBenchmark

Main benchmark execution class.

```python
class PGVectorBenchmark:
    def __init__(self, config: Optional[BenchmarkConfig] = None)
    async def setup(self) -> None
    async def cleanup(self) -> None
    async def benchmark_index_creation(self) -> None
    async def benchmark_query_performance(self) -> None
    async def run_full_benchmark(self) -> BenchmarkResults
```

#### RegressionDetector

Regression detection and analysis.

```python
class RegressionDetector:
    def __init__(self, baseline_manager: BaselineManager, thresholds: Optional[RegressionThresholds] = None)
    def analyze_performance(self, test_name: str, current_results: Dict[str, Any]) -> RegressionAnalysisResult
```

### Utility Functions

```python
# Run complete benchmark
async def run_benchmark(output_dir: str = "./benchmark_results", quick_test: bool = False, verbose: bool = False) -> BenchmarkResults

# Setup baseline from results
def setup_baseline_from_benchmark_results(benchmark_results_file: str, baseline_dir: str = "./baselines", version: str = "unknown") -> None

# Check for regressions
def check_for_regressions(benchmark_results_file: str, baseline_dir: str = "./baselines", output_file: Optional[str] = None) -> bool
```

## 🤝 Contributing

### Adding New Benchmarks

1. Extend `BenchmarkConfig` with new parameters
2. Add benchmark method to `PGVectorBenchmark`
3. Update metrics collection and reporting
4. Add corresponding tests

### Custom Metrics

1. Create new metrics dataclass
2. Implement collection logic
3. Add to performance calculations
4. Update regression detection

### Integration Extensions

1. Add notification providers (Slack, Teams, etc.)
2. Extend CI/CD artifact generation
3. Add custom report formats
4. Implement performance dashboards

## 📄 License

This benchmark suite is part of the TripSage project and follows the same license terms.

## 🔗 Related Documentation

- [TripSage Database Architecture](../../docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)
- [PGVector Service Documentation](../../tripsage_core/services/infrastructure/pgvector_service.py)
- [Performance Profiling Guide](../../docs/04_DEVELOPMENT_GUIDE/PERFORMANCE_PROFILING.md)
- [CI/CD Integration Guide](../../docs/03_ARCHITECTURE/DEPLOYMENT_STRATEGY.md)