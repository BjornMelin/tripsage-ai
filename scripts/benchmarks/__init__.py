"""Performance Benchmarking Suite for Database Optimization Framework.

This module provides comprehensive performance benchmarking tools to validate
the claimed performance improvements of the database optimization framework:
- 3x general query performance improvement
- 30x pgvector performance improvement
- 50% memory reduction with halfvec compression
- Connection pool efficiency gains
- Read replica load distribution effectiveness
"""

__version__ = "1.0.0"
__author__ = "TripSage Performance Team"


# Lazy imports to avoid import errors when dependencies aren't available
def _get_benchmark_runner():
    from .benchmark_runner import BenchmarkRunner

    return BenchmarkRunner


def _get_metrics_collector():
    from .metrics_collector import PerformanceMetricsCollector

    return PerformanceMetricsCollector


def _get_report_generator():
    from .report_generator import BenchmarkReportGenerator

    return BenchmarkReportGenerator


def _get_scenario_manager():
    from .scenario_manager import BenchmarkScenarioManager

    return BenchmarkScenarioManager


__all__ = [
    "BenchmarkReportGenerator",
    "BenchmarkRunner",
    "BenchmarkScenarioManager",
    "PerformanceMetricsCollector",
]
