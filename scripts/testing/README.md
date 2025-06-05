# Testing Utility Scripts

This directory contains utility scripts for running and analyzing tests.

## Scripts

### run_tests_with_coverage.py
Run the full test suite with coverage reporting and detailed failure information.

Usage:
```bash
python scripts/testing/run_tests_with_coverage.py
```

### test_summary.py
Generate a summary report of test results across different test directories.

Usage:
```bash
python scripts/testing/test_summary.py
```

### test_runner.py
Simple test runner for verifying imports and basic functionality without requiring full pytest installation. Useful for quick smoke tests.

Usage:
```bash
python scripts/testing/test_runner.py
```

## Notes

- All scripts should be run from the project root directory
- Test configuration is defined in `/pytest.ini`
- Test environment variables are loaded from `/.env.test`