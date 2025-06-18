# DatabaseService Comprehensive Test Suite

This directory contains a comprehensive, multi-layer test suite for the `DatabaseService` using modern pytest patterns, property-based testing, and advanced testing techniques.

## 🎯 Overview

The test suite ensures the `DatabaseService` meets high standards for:
- **Reliability**: 90%+ test coverage with mutation testing validation
- **Performance**: Sub-10ms CRUD operations, LIFO pooling efficiency
- **Resilience**: Circuit breaker, rate limiting, error recovery
- **Security**: SQL injection prevention, audit logging
- **Scalability**: Connection pool management, concurrent access

## 📁 Test Architecture

### Core Test Files

| File | Purpose | Test Types |
|------|---------|------------|
| `conftest.py` | Advanced fixtures, service factories, property strategies | Setup |
| `test_database_service_comprehensive.py` | Core functionality, CRUD, configuration | Unit, Property |
| `test_database_service_performance.py` | Performance benchmarks, regression detection | Performance |
| `test_database_service_stateful.py` | State machine testing, complex scenarios | Stateful |
| `test_database_service_chaos.py` | Chaos engineering, load testing, resilience | Chaos, Load |
| `test_runner.py` | Centralized test execution, reporting | Runner |

### Test Categories

#### 🧪 Unit Tests (`test_database_service_comprehensive.py`)
- **Configuration validation** with property-based testing
- **Connection lifecycle** management
- **CRUD operations** with comprehensive mocking
- **Circuit breaker and rate limiting** functionality
- **Security features** (SQL injection prevention, audit logging)
- **Query monitoring** and metrics collection
- **Vector search** operations
- **Error handling** and exception scenarios

#### 🎲 Property-Based Tests (Hypothesis)
- **Configuration parameter space** validation
- **Edge case testing** with automatic test case generation  
- **Invariant checking** across operation sequences
- **Data consistency** verification

#### ⚡ Performance Tests (`test_database_service_performance.py`)
- **Connection pool** performance and LIFO behavior
- **CRUD operation** throughput and latency
- **Vector search** performance scaling
- **Query monitoring** overhead measurement
- **Memory usage** patterns
- **Concurrent access** performance
- **Regression detection** benchmarks

#### 🤖 Stateful Tests (`test_database_service_stateful.py`)
- **State machine testing** with Hypothesis
- **Connection lifecycle** state transitions
- **CRUD operation** sequences with invariants
- **Rate limiting** state management
- **Circuit breaker** state machine
- **Metrics collection** lifecycle
- **Concurrent operations** safety

#### 💥 Chaos Engineering Tests (`test_database_service_chaos.py`)
- **Network failure** scenarios and recovery
- **Resource exhaustion** handling
- **Concurrent access** stress testing
- **Error injection** and recovery
- **Performance degradation** scenarios
- **Load testing** with realistic workloads

#### 🔌 Integration Tests (`../../integration/test_database_service_integration.py`)
- **Real database** connection testing
- **End-to-end** CRUD workflows
- **Transaction** integrity
- **Security features** in production scenarios
- **Performance** under realistic conditions

## 🚀 Quick Start

### Running Tests

```bash
# Run all tests with coverage
python test_runner.py --all

# Run specific test categories
python test_runner.py --unit           # Unit tests only
python test_runner.py --performance    # Performance benchmarks
python test_runner.py --integration    # Integration tests (requires --run-integration)
python test_runner.py --chaos          # Chaos engineering tests

# Generate coverage report
python test_runner.py --coverage

# Run with specific options
python test_runner.py --unit --skip-slow
python test_runner.py --performance --benchmark-save=results
```

### Using pytest directly

```bash
# Unit tests with coverage
pytest test_database_service_comprehensive.py -v --cov=tripsage_core.services.infrastructure.database_service --cov-report=html

# Performance benchmarks
pytest test_database_service_performance.py -m performance --benchmark-only

# Property-based tests
pytest test_database_service_comprehensive.py -m property

# Stateful tests
pytest test_database_service_stateful.py -m stateful

# Integration tests (requires setup)
pytest ../../integration/test_database_service_integration.py --run-integration

# Chaos tests
pytest test_database_service_chaos.py -m chaos --run-load-tests
```

## 🔧 Configuration

### Test Markers

```python
@pytest.mark.unit           # Unit tests
@pytest.mark.property       # Property-based tests with Hypothesis
@pytest.mark.stateful       # Stateful testing scenarios
@pytest.mark.performance    # Performance benchmarks
@pytest.mark.integration    # Integration tests with real database
@pytest.mark.chaos          # Chaos engineering tests
@pytest.mark.load           # Load testing scenarios
@pytest.mark.slow           # Long-running tests
```

### Command Line Options

```bash
--run-integration     # Enable integration tests
--run-load-tests      # Enable load testing scenarios
--run-slow            # Include slow tests
--benchmark-save=FILE # Save benchmark results
```

## 📊 Coverage Requirements

- **Minimum coverage**: 90% line coverage
- **Branch coverage**: Enabled
- **Mutation testing**: Quality validation with mutmut
- **Coverage reports**: HTML, XML, JSON formats

### Coverage Exclusions

- Test files (`test_*.py`)
- Configuration files (`config.py`)
- Abstract methods
- Import error handlers
- Development-only code

## 🏗️ Test Fixtures and Factories

### Service Factory (`database_service_factory`)
Creates `DatabaseService` instances with configurable parameters:

```python
def test_custom_configuration(database_service_factory):
    service = database_service_factory(
        pool_size=50,
        enable_monitoring=True,
        enable_security=True,
    )
    assert service.pool_size == 50
```

### Mock Service (`mock_database_service`)
Fully mocked service for unit testing:

```python
async def test_crud_operations(mock_database_service):
    service = mock_database_service
    result = await service.insert("users", {"name": "Test"})
    assert result == [{"id": mock.ANY}]
```

### Property Strategies
Hypothesis strategies for configuration testing:

```python
@given(valid_database_configs())
def test_configuration_validation(config, mock_settings_factory):
    service = DatabaseService(mock_settings_factory(), **config)
    assert service.pool_size >= 1
```

## 🎯 Performance Benchmarks

### Key Metrics
- **Connection establishment**: < 100ms
- **CRUD operations**: < 10ms average
- **Vector search**: < 500ms for 1000 vectors
- **Pool utilization**: > 95% under load
- **Memory overhead**: < 10% baseline increase

### Benchmark Categories
- Connection pool performance
- CRUD operation throughput
- Vector search scaling
- Query monitoring overhead
- Memory usage patterns
- Concurrent access performance

## 🔬 Property-Based Testing

Using Hypothesis for comprehensive test coverage:

### Configuration Testing
```python
@given(valid_database_configs())
def test_valid_configurations(config):
    # Tests all valid configuration combinations
    service = DatabaseService(**config)
    assert service.pool_size >= 1
```

### Data Strategies
```python
@given(query_data_strategies())
async def test_crud_with_various_data(query_data):
    # Tests CRUD operations with generated data
    table, data, filters = query_data
    await service.insert(table, data)
```

### Stateful Testing
```python
class DatabaseStateMachine(RuleBasedStateMachine):
    @rule()
    def connect(self):
        # State machine rules for complex scenarios
```

## 🌪️ Chaos Engineering

### Failure Scenarios
- Network connection drops
- Resource exhaustion (memory, connections)
- Slow query cascading effects
- Random error injection
- Circuit breaker activation
- Rate limiting enforcement

### Load Testing
- High concurrency mixed operations
- Burst traffic patterns
- Sustained load endurance
- Resource contention scenarios

## 📈 Test Reports

### Coverage Reports
- **HTML Report**: `coverage/html/index.html`
- **XML Report**: `coverage/coverage.xml`
- **JSON Report**: `coverage/coverage.json`

### Benchmark Reports
- **Performance Data**: `test_reports/benchmark_data.json`
- **Regression Analysis**: Automatic comparison with baselines

### Test Summary
```bash
📋 TEST SUITE SUMMARY
================================
Total duration: 45.23s
Successful suites: 5/5
Success rate: 100.0%
================================
✅ unit: 12.34s
✅ property: 8.56s
✅ performance: 15.78s
✅ integration: 6.23s
✅ chaos: 2.32s
```

## 🛠️ Development Workflow

### TDD (Test-Driven Development)
1. **Write failing test** for new feature
2. **Implement minimal code** to pass test
3. **Refactor** while maintaining tests
4. **Run full suite** before commit

### Adding New Tests
1. **Choose appropriate test file** based on test type
2. **Use existing fixtures** and factories
3. **Follow naming conventions** (`test_*`)
4. **Add appropriate markers** (`@pytest.mark.*`)
5. **Update coverage** requirements if needed

### Performance Testing
1. **Add benchmark** to `test_database_service_performance.py`
2. **Set performance baselines** with `--benchmark-save`
3. **Monitor regressions** in CI/CD pipeline
4. **Document performance requirements**

## 🚨 Troubleshooting

### Common Issues

#### Test Discovery Issues
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/unit/tripsage_core/services/infrastructure/
```

#### Coverage Not Working
```bash
# Install coverage dependencies
pip install pytest-cov coverage[toml]

# Run with explicit coverage config
pytest --cov-config=pyproject.toml --cov=tripsage_core
```

#### Integration Tests Failing
```bash
# Enable integration tests
pytest --run-integration

# Check database connection settings
# Ensure test database is available
```

#### Performance Tests Slow
```bash
# Skip slow tests during development
pytest -m "not slow"

# Reduce benchmark iterations
pytest --benchmark-min-rounds=1
```

### Debugging Tests
```bash
# Verbose output with print statements
pytest -v -s test_file.py::test_function

# Drop into debugger on failure
pytest --pdb test_file.py

# Run single test with full traceback
pytest --tb=full test_file.py::test_function
```

## 📚 References

- [pytest documentation](https://docs.pytest.org/)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

## 🎉 Summary

This comprehensive test suite provides:

✅ **90%+ test coverage** with branch coverage  
✅ **Property-based testing** for robustness  
✅ **Performance benchmarking** with regression detection  
✅ **Stateful testing** for complex scenarios  
✅ **Chaos engineering** for resilience validation  
✅ **Integration testing** with real database scenarios  
✅ **Mutation testing** for test quality validation  
✅ **Comprehensive reporting** and metrics  

The test suite ensures the `DatabaseService` is production-ready with high reliability, performance, and maintainability standards.