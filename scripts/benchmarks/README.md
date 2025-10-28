# TripSage Benchmarking Suite

A consolidated performance benchmarking suite for database and caching.

## Performance Targets

Validates optimization claims such as:

- Vector search performance improvements
- General query performance improvements
- Average query latency targets
- Memory usage reductions
- Cache hit ratios and connection pool efficiency

## Structure

```text
scripts/benchmarks/
├── README.md
├── benchmark.py                 # Unified benchmark entry point
├── benchmark_runner.py          # Orchestration
├── scenario_service.py          # Scenario definitions
├── metrics_collector.py         # Metrics collection
├── report_generator.py          # Reports (HTML/CSV)
├── config.py                    # Config and thresholds
├── cache_performance.py         # Cache-specific tests (Redis)
├── Makefile                     # Automation helpers
```

## Quick Start

```bash
cd scripts/benchmarks
uv sync --group benchmark
python benchmark.py --quick
```

## Components

- Database benchmarking: `benchmark.py`, `benchmark_runner.py`, `scenario_service.py`
- Cache benchmarking: `cache_performance.py`
- Metrics and reports: `metrics_collector.py`, `report_generator.py`

## Validation Examples

```bash
# Database comparison
python benchmark.py --full-suite

# Cache tests
python cache_performance.py --quick
```

## CLI Reference

```bash
# Unified benchmark
python benchmark.py [OPTIONS]

# Cache-specific
python cache_performance.py [OPTIONS]
```

Common options:

```bash
--output-dir  Output directory for reports (default: ./benchmark_results)
--verbose     Enable verbose logging
--timeout     Total timeout in seconds
--config-file Custom configuration file
--quick       Reduced iterations for quick runs
```

## Understanding Results

Reports include:

- Executive summary of results
- Database and vector search metrics
- Cache metrics and connection efficiency
- Memory analysis and regressions (if configured)

Example snippet:

```markdown
# Performance Validation Summary

## Overall Results
- Database Performance: 3.2x improvement (Target: 3x)
- Vector Search Performance: 32.5x improvement (Target: 30x)
- Memory Usage: 52% reduction (Target: 50%)
- Cache Hit Ratio: 87% (Target: 80%)
- Connection Efficiency: 94% (Target: 90%)
```

## Troubleshooting

- Verify database connectivity and credentials
- Reduce `test_data_size` or `concurrent_connections`
- Increase `--timeout` or use `--quick`
- Ensure the environment matches expected hardware/resources

## Related Documentation

- TripSage Database Architecture: `docs/03_ARCHITECTURE/DATABASE_ARCHITECTURE.md`
- Performance Profiling Guide: `docs/04_DEVELOPMENT_GUIDE/PERFORMANCE_PROFILING.md`
