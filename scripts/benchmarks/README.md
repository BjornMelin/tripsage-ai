# Benchmark Scripts

Performance testing and benchmarking utilities for measuring system performance.

## Overview

Benchmark scripts help identify performance bottlenecks, validate optimization efforts, and ensure the system meets performance requirements. These scripts measure key metrics like throughput, latency, and resource utilization.

## Scripts

### dragonfly_performance.py

Comprehensive performance testing for DragonflyDB cache operations.

**What it measures**:

- Operation latency (GET, SET, DELETE)
- Throughput (operations per second)
- Memory usage patterns
- Connection pool performance
- JSON operation overhead
- Pub/Sub message latency

**Usage**:

```bash
# Run all benchmarks
python scripts/benchmarks/dragonfly_performance.py

# Quick benchmark (reduced iterations)
python scripts/benchmarks/dragonfly_performance.py --quick

# Specific test suites
python scripts/benchmarks/dragonfly_performance.py --suites basic,json

# Custom parameters
python scripts/benchmarks/dragonfly_performance.py \
  --iterations 10000 \
  --connections 50 \
  --data-size 1024
```

**Output Format**:

```text
DragonflyDB Performance Benchmark Results
========================================
Environment: Production
Date: 2025-06-17 10:30:00

Basic Operations:
  SET: 45,230 ops/sec (avg: 0.022ms)
  GET: 52,100 ops/sec (avg: 0.019ms)
  DEL: 48,500 ops/sec (avg: 0.021ms)

JSON Operations:
  JSON.SET: 38,400 ops/sec (avg: 0.026ms)
  JSON.GET: 41,200 ops/sec (avg: 0.024ms)

Connection Pool:
  Pool Efficiency: 94.2%
  Connection Reuse: 1,247 times
  Avg Wait Time: 0.8ms
```

## Benchmark Categories

### 1. Basic Operations

Tests fundamental cache operations:

- Simple key-value operations
- Batch operations
- Pipeline performance
- Transaction overhead

### 2. Data Structure Performance

Measures complex data type operations:

- JSON document operations
- List operations
- Set operations
- Sorted set operations

### 3. Concurrency Testing

Evaluates multi-client performance:

- Concurrent reads
- Concurrent writes
- Read/write mix
- Connection pool saturation

### 4. Memory Efficiency

Analyzes memory usage patterns:

- Memory per key
- Fragmentation over time
- Eviction performance
- Memory reclamation

### 5. Network Overhead

Tests network-related performance:

- Latency vs payload size
- Compression benefits
- Protocol overhead
- Keep-alive efficiency

## Running Benchmarks

### Prerequisites

1. **System Preparation**:

   ```bash
   # Ensure system is idle
   systemctl stop unnecessary-services
   
   # Set CPU governor to performance
   sudo cpupower frequency-set -g performance
   
   # Disable swap to avoid variability
   sudo swapoff -a
   ```

2. **Cache Preparation**:

   ```bash
   # Clear cache before benchmarking
   redis-cli FLUSHALL
   
   # Warm up connection pool
   python scripts/verification/verify_dragonfly.py
   ```

### Best Practices

1. **Consistent Environment**:
   - Run on dedicated hardware
   - Minimize background processes
   - Use same network conditions
   - Control for temperature/throttling

2. **Multiple Runs**:

   ```bash
   # Run multiple times and average
   for i in {1..5}; do
     python scripts/benchmarks/dragonfly_performance.py >> results.txt
     sleep 60  # Cool down between runs
   done
   ```

3. **Baseline Comparison**:

   ```bash
   # Save baseline results
   python scripts/benchmarks/dragonfly_performance.py \
     --output baseline_$(date +%Y%m%d).json
   
   # Compare with baseline
   python scripts/benchmarks/dragonfly_performance.py \
     --compare baseline_20250617.json
   ```

## Performance Targets

### Minimum Requirements

- Basic operations: > 10,000 ops/sec
- P99 latency: < 5ms
- Connection pool efficiency: > 80%
- Memory overhead: < 2x raw data size

### Recommended Targets

- Basic operations: > 50,000 ops/sec
- P99 latency: < 1ms
- Connection pool efficiency: > 95%
- Memory overhead: < 1.5x raw data size

## Analyzing Results

### Key Metrics to Watch

1. **Latency Distribution**:

   ```python
   # Look for:
   - P50 (median): General performance
   - P95: Most requests
   - P99: Tail latency
   - P99.9: Worst case
   ```

2. **Throughput Variance**:

   ```python
   # Calculate coefficient of variation
   CV = (std_dev / mean) * 100
   # CV < 10% is good, < 5% is excellent
   ```

3. **Error Rates**:

   ```python
   # Any errors indicate problems
   - Connection errors: Network/config issues
   - Timeout errors: Performance problems
   - Memory errors: Capacity issues
   ```

### Visualization

Generate performance graphs:

```bash
# Generate HTML report with graphs
python scripts/benchmarks/dragonfly_performance.py \
  --output-format html \
  --output-file performance_report.html

# Generate CSV for further analysis
python scripts/benchmarks/dragonfly_performance.py \
  --output-format csv \
  --output-file performance_data.csv
```

## Troubleshooting Performance Issues

### Common Bottlenecks

1. **Network Latency**:

   ```bash
   # Test network RTT
   ping -c 100 cache.host | grep avg
   
   # If RTT > 1ms, consider:
   - Moving cache closer to application
   - Using connection pooling
   - Batching operations
   ```

2. **CPU Bottleneck**:

   ```bash
   # Monitor during benchmark
   top -p $(pgrep dragonfly)
   
   # If CPU > 80%, consider:
   - Sharding across multiple instances
   - Optimizing data structures
   - Reducing operation complexity
   ```

3. **Memory Pressure**:

   ```bash
   # Check memory stats
   redis-cli INFO memory
   
   # If used_memory > 80% of max, consider:
   - Increasing memory limits
   - Implementing eviction policies
   - Optimizing data formats
   ```

## Integration with CI/CD

### Automated Performance Testing

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  pull_request:
    paths:
      - 'src/cache/**'
      - 'scripts/benchmarks/**'

jobs:
  benchmark:
    runs-on: [self-hosted, performance]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Environment
        run: |
          docker-compose -f docker-compose.bench.yml up -d
          sleep 10  # Wait for services
          
      - name: Run Benchmarks
        run: |
          python scripts/benchmarks/dragonfly_performance.py \
            --output-format json \
            --output-file results.json
            
      - name: Compare with Baseline
        run: |
          python scripts/benchmarks/compare_results.py \
            --baseline baseline.json \
            --current results.json \
            --threshold 5  # Allow 5% degradation
            
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: results.json
```

## Creating New Benchmarks

### Template Structure

```python
#!/usr/bin/env python3
"""
Benchmark script for [component name].

Measures:
- Metric 1
- Metric 2
- Metric 3
"""

import argparse
import time
import statistics
from typing import Dict, List
import json

class ComponentBenchmark:
    def __init__(self, config: Dict):
        self.config = config
        self.results = {}
        
    def setup(self):
        """Prepare environment for benchmarking."""
        pass
        
    def teardown(self):
        """Clean up after benchmarking."""
        pass
        
    def benchmark_operation_1(self) -> Dict:
        """Benchmark specific operation."""
        latencies = []
        
        for _ in range(self.config['iterations']):
            start = time.perf_counter()
            # Perform operation
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms
            
        return {
            'mean': statistics.mean(latencies),
            'median': statistics.median(latencies),
            'p95': statistics.quantiles(latencies, n=20)[18],
            'p99': statistics.quantiles(latencies, n=100)[98],
        }
        
    def run(self) -> Dict:
        """Run all benchmarks."""
        self.setup()
        
        try:
            self.results['operation_1'] = self.benchmark_operation_1()
            # Add more benchmarks
        finally:
            self.teardown()
            
        return self.results
        
    def report(self):
        """Generate human-readable report."""
        print(f"Benchmark Results")
        print("=" * 50)
        for op, metrics in self.results.items():
            print(f"\n{op}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value:.3f}ms")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--output-format', choices=['text', 'json'], default='text')
    parser.add_argument('--output-file', help='Save results to file')
    
    args = parser.parse_args()
    
    config = {
        'iterations': args.iterations,
    }
    
    benchmark = ComponentBenchmark(config)
    results = benchmark.run()
    
    if args.output_format == 'text':
        benchmark.report()
    else:
        output = json.dumps(results, indent=2)
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
        else:
            print(output)

if __name__ == '__main__':
    main()
```

## Related Documentation

- [Performance Tuning Guide](../../docs/performance/tuning.md)
- [Monitoring Setup](../../docs/monitoring/setup.md)
- [Capacity Planning](../../docs/infrastructure/capacity-planning.md)
