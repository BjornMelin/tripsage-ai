# TripSage Database Performance Benchmarking Suite
# Simplified to 8 essential targets following ULTRATHINK principles

.PHONY: help install test full-suite vector database clean format lint

# Variables for customization
SCENARIO ?= mixed
DURATION ?= 300
USERS ?= 10
VERBOSE ?= 
OUTPUT_DIR ?= ./results

# Default target
help:
	@echo "TripSage Benchmark Suite (8 Essential Targets)"
	@echo "=============================================="
	@echo ""
	@echo "Essential targets:"
	@echo "  help        Show this help"
	@echo "  install     Install dependencies"
	@echo "  test        Quick test (2-3 min)"
	@echo "  full-suite  Complete benchmark suite (30+ min)"
	@echo "  vector      Vector search benchmarks"
	@echo "  database    Database-only benchmarks"
	@echo "  clean       Remove all results"
	@echo "  format      Format and lint code"
	@echo ""
	@echo "Variables:"
	@echo "  SCENARIO=[mixed|read_heavy|vector_search]"
	@echo "  DURATION=<seconds> USERS=<count> VERBOSE=1"
	@echo ""
	@echo "Examples:"
	@echo "  make test                           # Quick 2-min test"
	@echo "  make test SCENARIO=vector VERBOSE=1 # Verbose vector test"
	@echo "  make full-suite                     # Production validation"

# Install dependencies
install:
	@echo "Installing dependencies..."
	cd ../../ && uv sync
	@echo "✅ Dependencies installed"

# Quick test (replaces quick-test, ci-test, dev-validate)
test:
	@echo "Running quick test ($(SCENARIO), $(DURATION)s, $(USERS) users)..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python benchmark.py quick \
		--iterations $(shell echo $$(($(DURATION)/3))) \
		--concurrent $(USERS) \
		--output-dir $(OUTPUT_DIR) \
		$(if $(VERBOSE),&& echo "✅ Quick test completed")

# Complete benchmark suite (replaces validate, prod-validate, claims)
full-suite:
	@echo "Running full benchmark suite..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python benchmark.py full-suite \
		--output-dir $(OUTPUT_DIR) \
		--timeout 3600 \
		&& echo "✅ Full suite completed - check $(OUTPUT_DIR)/"

# Vector search benchmarks (replaces vector-test)
vector:
	@echo "Running vector search benchmarks..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python benchmark.py vector-only \
		--output-dir $(OUTPUT_DIR) \
		&& echo "✅ Vector benchmarks completed"

# Database benchmarks (replaces baseline, optimized, comparison, concurrency)
database:
	@echo "Running database benchmarks..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python benchmark.py database-only \
		--output-dir $(OUTPUT_DIR) \
		&& echo "✅ Database benchmarks completed"

# Clean results (simplified from multiple clean targets)
clean:
	@echo "Cleaning benchmark results..."
	rm -rf results/ ci_results/ monitoring/ *.log benchmark_results_*.json
	@echo "✅ Cleanup completed"

# Format and lint (replaces multiple dev targets)
format:
	@echo "Formatting and linting code..."
	cd ../../ && ruff check scripts/benchmarks/ --fix
	cd ../../ && ruff format scripts/benchmarks/
	@echo "✅ Code formatted and linted"