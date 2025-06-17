"""
Performance Benchmarking Suite for Database Optimization Framework.

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

from .benchmark_runner import BenchmarkRunner
from .metrics_collector import PerformanceMetricsCollector
from .report_generator import BenchmarkReportGenerator
from .scenario_manager import BenchmarkScenarioManager

__all__ = [
    "BenchmarkRunner",
    "PerformanceMetricsCollector",
    "BenchmarkReportGenerator",
    "BenchmarkScenarioManager",
]
