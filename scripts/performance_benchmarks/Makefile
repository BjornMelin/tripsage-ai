# TripSage Database Performance Benchmarking Suite
# Convenient make targets for running performance benchmarks

.PHONY: help install validate quick-test ci-test baseline optimized comparison concurrency clean

# Default target
help:
	@echo "TripSage Database Performance Benchmarking Suite"
	@echo "================================================"
	@echo ""
	@echo "Available targets:"
	@echo "  help          Show this help message"
	@echo "  install       Install dependencies"
	@echo "  validate      Run complete validation suite (recommended)"
	@echo "  quick-test    Run quick development test"
	@echo "  ci-test       Run CI/CD optimized validation"
	@echo "  baseline      Run baseline benchmarks only"
	@echo "  optimized     Run optimized benchmarks only" 
	@echo "  comparison    Run baseline vs optimized comparison"
	@echo "  concurrency   Run high-concurrency benchmarks"
	@echo "  claims        Validate optimization claims"
	@echo "  clean         Clean up benchmark results"
	@echo ""
	@echo "Examples:"
	@echo "  make validate              # Complete validation suite"
	@echo "  make quick-test SCENARIO=vector_search DURATION=300"
	@echo "  make ci-test               # For CI/CD pipelines"
	@echo "  make comparison VERBOSE=1  # Detailed comparison"

# Install dependencies
install:
	@echo "Installing benchmarking dependencies..."
	cd ../../ && uv sync
	@echo "Dependencies installed successfully"

# Complete validation suite (default for production validation)
validate:
	@echo "Running complete performance validation suite..."
	@mkdir -p results
	python run_benchmarks.py full-validation \
		--output-dir ./results \
		$(if $(VERBOSE),--verbose) \
		$(if $(TIMEOUT),--timeout $(TIMEOUT))

# Quick development test
SCENARIO ?= mixed
OPTIMIZATION ?= full
DURATION ?= 300
USERS ?= 10

quick-test:
	@echo "Running quick test: $(SCENARIO) workload with $(OPTIMIZATION) optimizations"
	@mkdir -p results
	python run_benchmarks.py quick-test \
		--scenario $(SCENARIO) \
		--optimization $(OPTIMIZATION) \
		--duration $(DURATION) \
		--users $(USERS) \
		--output-dir ./results

# CI/CD optimized validation
ci-test:
	@echo "Running CI/CD validation..."
	@mkdir -p ci_results
	python run_benchmarks.py ci-validation --output-dir ./ci_results
	@echo "CI validation completed. Check ci_results/ci_results.json for summary"

# Individual benchmark types
baseline:
	@echo "Running baseline benchmarks..."
	@mkdir -p results
	python benchmark_runner.py baseline \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

optimized:
	@echo "Running optimized benchmarks..."
	@mkdir -p results
	python benchmark_runner.py optimized \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

comparison:
	@echo "Running baseline vs optimized comparison..."
	@mkdir -p results
	python benchmark_runner.py comparison \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

concurrency:
	@echo "Running high-concurrency benchmarks..."
	@mkdir -p results
	python benchmark_runner.py concurrency \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

# Validate optimization claims
claims:
	@echo "Validating optimization claims..."
	@mkdir -p results
	python benchmark_runner.py validate \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

# Custom scenario (for advanced usage)
SCENARIO_NAME ?= custom_test
WORKLOAD ?= mixed
DURATION_CUSTOM ?= 600
USERS_CUSTOM ?= 20
OPS ?= 100

custom:
	@echo "Running custom scenario: $(SCENARIO_NAME)"
	@mkdir -p results
	python benchmark_runner.py custom \
		--name $(SCENARIO_NAME) \
		--workload $(WORKLOAD) \
		--optimization $(OPTIMIZATION) \
		--duration $(DURATION_CUSTOM) \
		--users $(USERS_CUSTOM) \
		--operations $(OPS) \
		$(if $(VERBOSE),-v) \
		--output-dir ./results

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	@mkdir -p results ci_results
	@echo "Development environment ready"

# View latest results
results:
	@echo "Opening latest benchmark results..."
	@find results -name "*.html" -type f -exec ls -lt {} + | head -1 | awk '{print $$NF}' | xargs open 2>/dev/null || echo "No HTML reports found"

# Quick status check
status:
	@echo "Benchmark Results Summary:"
	@echo "========================="
	@if [ -d "results" ]; then \
		echo "Results directory: $(shell ls -la results | wc -l) files"; \
		echo "Latest result: $(shell ls -t results/*.json 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo 'None')"; \
	else \
		echo "No results directory found"; \
	fi
	@if [ -d "ci_results" ]; then \
		echo "CI results: $(shell ls -la ci_results | wc -l) files"; \
	fi

# Clean up results
clean:
	@echo "Cleaning up benchmark results..."
	rm -rf results/* ci_results/* *.log
	@echo "Cleanup completed"

# Development workflow targets
dev-validate: dev-setup quick-test
	@echo "Development validation completed"

prod-validate: install validate
	@echo "Production validation completed"

# Performance monitoring workflow
monitor:
	@echo "Starting performance monitoring session..."
	@mkdir -p monitoring/$(shell date +%Y%m%d_%H%M%S)
	python benchmark_runner.py comparison \
		--output-dir ./monitoring/$(shell date +%Y%m%d_%H%M%S) \
		$(if $(VERBOSE),-v)

# Continuous monitoring (for automated setups)
continuous-monitor:
	@echo "Setting up continuous monitoring..."
	@while true; do \
		make monitor; \
		echo "Monitoring cycle completed. Waiting 1 hour..."; \
		sleep 3600; \
	done

# Benchmark different optimization levels
optimization-comparison:
	@echo "Comparing all optimization levels..."
	@mkdir -p results/optimization_comparison
	@for level in none basic advanced full; do \
		echo "Testing optimization level: $$level"; \
		python benchmark_runner.py custom \
			--name "opt_level_$$level" \
			--workload mixed \
			--optimization $$level \
			--duration 180 \
			--users 10 \
			--output-dir ./results/optimization_comparison; \
	done

# Memory-focused testing
memory-test:
	@echo "Running memory-focused benchmarks..."
	@mkdir -p results/memory_analysis
	PYTHONPATH=. python run_benchmarks.py quick-test \
		--scenario mixed \
		--optimization full \
		--duration 600 \
		--users 20 \
		--output-dir ./results/memory_analysis
	@echo "Memory analysis completed. Check results/memory_analysis/"

# Vector search focused testing
vector-test:
	@echo "Running vector search performance tests..."
	@mkdir -p results/vector_analysis
	python run_benchmarks.py quick-test \
		--scenario vector_search \
		--optimization full \
		--duration 300 \
		--users 15 \
		--output-dir ./results/vector_analysis

# Load testing
load-test:
	@echo "Running load testing with high concurrency..."
	@mkdir -p results/load_testing
	python benchmark_runner.py concurrency \
		$(if $(VERBOSE),-v) \
		--output-dir ./results/load_testing

# Generate summary report from existing results
summary:
	@echo "Generating summary from existing results..."
	@python -c "
import json
import glob
import os
from pathlib import Path

results_dir = Path('results')
if not results_dir.exists():
    print('No results directory found')
    exit(1)

json_files = list(results_dir.glob('**/*.json'))
if not json_files:
    print('No JSON result files found')
    exit(1)

print(f'Found {len(json_files)} result files:')
for f in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    print(f'  - {f.name} ({f.stat().st_mtime})')
"

# Help for make variables
vars:
	@echo "Available make variables:"
	@echo "  SCENARIO      Workload scenario (read_heavy|vector_search|mixed) [default: mixed]"
	@echo "  OPTIMIZATION  Optimization level (none|basic|advanced|full) [default: full]"
	@echo "  DURATION      Test duration in seconds [default: 300]"
	@echo "  USERS         Concurrent users [default: 10]"
	@echo "  VERBOSE       Enable verbose output (1 to enable)"
	@echo "  TIMEOUT       Total timeout in seconds"
	@echo ""
	@echo "Example usage:"
	@echo "  make quick-test SCENARIO=vector_search DURATION=600 VERBOSE=1"
	@echo "  make validate TIMEOUT=7200 VERBOSE=1"