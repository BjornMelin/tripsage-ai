#!/usr/bin/env python3
"""
Simple metrics collection and reporting for TripSage benchmarks.

Focused on essential metrics without over-engineering:
- Query performance (latency, throughput)
- Memory usage tracking
- Connection efficiency
- Simple JSON/CSV reports
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from config import BenchmarkConfig

logger = logging.getLogger(__name__)


@dataclass
class TimingResult:
    """Simple timing result for operations."""
    
    operation_type: str
    duration_seconds: float
    success: bool
    timestamp: float


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    
    timestamp: float
    process_mb: float
    system_percent: float


class MetricsCollector:
    """Simple metrics collector focused on core performance indicators."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize metrics collector."""
        self.config = config or BenchmarkConfig()
        
        # Simple storage
        self._timings: List[TimingResult] = []
        self._memory_snapshots: List[MemorySnapshot] = []
        self._connection_stats = {"reuses": 0, "creations": 0}
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        
        logger.info("Metrics collector initialized")

    async def start_monitoring(self) -> None:
        """Start background metrics collection."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._start_time = time.time()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Metrics monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background metrics collection."""
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        logger.info("Metrics monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        try:
            while self._monitoring:
                # Collect memory snapshot
                snapshot = MemorySnapshot(
                    timestamp=time.time(),
                    process_mb=self._get_process_memory_mb(),
                    system_percent=psutil.virtual_memory().percent
                )
                self._memory_snapshots.append(snapshot)
                
                # Sleep for collection interval
                await asyncio.sleep(1.0)  # Simple 1-second interval
                
        except asyncio.CancelledError:
            logger.debug("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

    def _get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def record_timing(self, operation_type: str, duration_seconds: float, success: bool = True) -> None:
        """Record a timing result."""
        timing = TimingResult(
            operation_type=operation_type,
            duration_seconds=duration_seconds,
            success=success,
            timestamp=time.time()
        )
        self._timings.append(timing)

    def record_connection_reuse(self) -> None:
        """Record a connection reuse."""
        self._connection_stats["reuses"] += 1

    def record_connection_creation(self) -> None:
        """Record a new connection creation."""
        self._connection_stats["creations"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "query_performance": self._get_query_summary(),
            "memory_usage": self._get_memory_summary(),
            "connection_efficiency": self._get_connection_summary(),
            "collection_period": {
                "start_time": self._start_time,
                "duration_seconds": time.time() - self._start_time,
                "total_timings": len(self._timings),
                "total_memory_snapshots": len(self._memory_snapshots)
            }
        }

    def _get_query_summary(self) -> Dict[str, Any]:
        """Get query performance summary."""
        if not self._timings:
            return {"error": "No timing data available"}
        
        successful_timings = [t for t in self._timings if t.success]
        if not successful_timings:
            return {"error": "No successful operations"}
        
        durations = [t.duration_seconds for t in successful_timings]
        durations.sort()
        
        total_duration = time.time() - self._start_time
        
        return {
            "total_operations": len(self._timings),
            "successful_operations": len(successful_timings),
            "error_rate": (len(self._timings) - len(successful_timings)) / len(self._timings),
            "avg_duration_ms": (sum(durations) / len(durations)) * 1000,
            "p95_duration_ms": durations[int(len(durations) * 0.95)] * 1000 if durations else 0,
            "operations_per_second": len(successful_timings) / total_duration if total_duration > 0 else 0,
            "by_operation_type": self._get_by_operation_type(successful_timings)
        }

    def _get_by_operation_type(self, timings: List[TimingResult]) -> Dict[str, Any]:
        """Get performance breakdown by operation type."""
        by_type = {}
        
        # Group by operation type
        type_groups = {}
        for timing in timings:
            if timing.operation_type not in type_groups:
                type_groups[timing.operation_type] = []
            type_groups[timing.operation_type].append(timing.duration_seconds)
        
        # Calculate stats for each type
        for op_type, durations in type_groups.items():
            durations.sort()
            by_type[op_type] = {
                "count": len(durations),
                "avg_duration_ms": (sum(durations) / len(durations)) * 1000,
                "p95_duration_ms": durations[int(len(durations) * 0.95)] * 1000 if durations else 0
            }
        
        return by_type

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get memory usage summary."""
        if not self._memory_snapshots:
            return {"error": "No memory data available"}
        
        process_mbs = [s.process_mb for s in self._memory_snapshots]
        
        return {
            "current_mb": process_mbs[-1],
            "peak_mb": max(process_mbs),
            "avg_mb": sum(process_mbs) / len(process_mbs),
            "min_mb": min(process_mbs),
            "memory_growth_mb": process_mbs[-1] - process_mbs[0] if len(process_mbs) > 1 else 0
        }

    def get_connection_summary(self) -> Dict[str, Any]:
        """Get connection efficiency summary."""
        total_ops = self._connection_stats["reuses"] + self._connection_stats["creations"]
        
        if total_ops == 0:
            efficiency_ratio = 0.0
        else:
            efficiency_ratio = self._connection_stats["reuses"] / total_ops
        
        return {
            "total_operations": total_ops,
            "connection_reuses": self._connection_stats["reuses"],
            "connection_creations": self._connection_stats["creations"],
            "efficiency_ratio": efficiency_ratio
        }

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._timings.clear()
        self._memory_snapshots.clear()
        self._connection_stats = {"reuses": 0, "creations": 0}
        self._start_time = time.time()
        logger.info("Metrics reset")


class ReportGenerator:
    """Simple report generator for benchmark results."""

    def __init__(self, output_dir: Path):
        """Initialize report generator."""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Report generator initialized with output dir: {output_dir}")

    async def generate_simple_report(self, data: Dict[str, Any], report_type: str) -> Path:
        """Generate simple JSON report with key metrics."""
        timestamp = int(time.time())
        
        # Create simple report data
        report_data = {
            "report_type": report_type,
            "timestamp": timestamp,
            "execution_time_seconds": data.get("execution_time", 0),
            "summary": self._create_summary(data),
            "detailed_metrics": data.get("metrics", {}),
            "validation": data.get("validation", {}),
            "raw_results": data.get("results", {})
        }
        
        # Save JSON report
        json_path = self.output_dir / f"benchmark_{report_type}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Save CSV summary for easy analysis
        csv_path = await self._generate_csv_summary(report_data, report_type, timestamp)
        
        # Generate simple HTML summary
        html_path = await self._generate_html_summary(report_data, report_type, timestamp)
        
        logger.info(f"Reports generated:")
        logger.info(f"  JSON: {json_path}")
        logger.info(f"  CSV:  {csv_path}")
        logger.info(f"  HTML: {html_path}")
        
        return html_path  # Return main report path

    def _create_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create high-level summary of results."""
        summary = {
            "test_completed": True,
            "execution_time_formatted": self._format_duration(data.get("execution_time", 0))
        }
        
        # Extract key metrics
        metrics = data.get("metrics", {})
        
        if "query_performance" in metrics:
            query_perf = metrics["query_performance"]
            if "operations_per_second" in query_perf:
                summary["query_ops_per_sec"] = f"{query_perf['operations_per_second']:.1f}"
            if "avg_duration_ms" in query_perf:
                summary["avg_query_latency_ms"] = f"{query_perf['avg_duration_ms']:.2f}"
        
        if "memory_usage" in metrics:
            memory = metrics["memory_usage"]
            if "peak_mb" in memory:
                summary["peak_memory_mb"] = f"{memory['peak_mb']:.1f}"
        
        if "connection_efficiency" in metrics:
            conn = metrics["connection_efficiency"]
            if "efficiency_ratio" in conn:
                summary["connection_efficiency"] = f"{conn['efficiency_ratio']:.1%}"
        
        # Validation summary
        validation = data.get("validation", {})
        if validation:
            claims_met = validation.get("claims_validated", 0)
            total_claims = validation.get("total_claims", 4)
            summary["validation_success"] = validation.get("overall_success", False)
            summary["claims_validated"] = f"{claims_met}/{total_claims}"
        
        return summary

    async def _generate_csv_summary(self, data: Dict[str, Any], report_type: str, timestamp: int) -> Path:
        """Generate CSV summary for easy analysis."""
        csv_path = self.output_dir / f"benchmark_{report_type}_{timestamp}.csv"
        
        # Create simple CSV with key metrics
        metrics = data.get("detailed_metrics", {})
        
        csv_lines = ["metric_name,value,unit"]
        
        # Query performance metrics
        if "query_performance" in metrics:
            qp = metrics["query_performance"]
            csv_lines.append(f"operations_per_second,{qp.get('operations_per_second', 0):.2f},ops/sec")
            csv_lines.append(f"avg_duration_ms,{qp.get('avg_duration_ms', 0):.2f},milliseconds")
            csv_lines.append(f"p95_duration_ms,{qp.get('p95_duration_ms', 0):.2f},milliseconds")
            csv_lines.append(f"error_rate,{qp.get('error_rate', 0):.3f},ratio")
        
        # Memory metrics
        if "memory_usage" in metrics:
            mem = metrics["memory_usage"]
            csv_lines.append(f"peak_memory_mb,{mem.get('peak_mb', 0):.2f},MB")
            csv_lines.append(f"avg_memory_mb,{mem.get('avg_mb', 0):.2f},MB")
            csv_lines.append(f"memory_growth_mb,{mem.get('memory_growth_mb', 0):.2f},MB")
        
        # Connection metrics
        if "connection_efficiency" in metrics:
            conn = metrics["connection_efficiency"]
            csv_lines.append(f"connection_efficiency,{conn.get('efficiency_ratio', 0):.3f},ratio")
            csv_lines.append(f"connection_reuses,{conn.get('connection_reuses', 0)},count")
            csv_lines.append(f"connection_creations,{conn.get('connection_creations', 0)},count")
        
        # Execution metrics
        csv_lines.append(f"execution_time_seconds,{data.get('execution_time_seconds', 0):.2f},seconds")
        
        # Write CSV
        with open(csv_path, 'w') as f:
            f.write('\n'.join(csv_lines))
        
        return csv_path

    async def _generate_html_summary(self, data: Dict[str, Any], report_type: str, timestamp: int) -> Path:
        """Generate simple HTML summary report."""
        html_path = self.output_dir / f"benchmark_{report_type}_{timestamp}.html"
        
        summary = data.get("summary", {})
        validation = data.get("validation", {})
        
        # Simple HTML template
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>TripSage Benchmark Report - {report_type.title()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
        .metric {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        .metric-label {{ font-weight: bold; color: #495057; }}
        .metric-value {{ font-size: 1.2em; color: #007bff; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .error {{ color: #dc3545; }}
        .validation {{ margin: 20px 0; padding: 20px; border-radius: 8px; }}
        .validation.success {{ background: #d4edda; border: 1px solid #c3e6cb; }}
        .validation.warning {{ background: #fff3cd; border: 1px solid #ffeaa7; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 TripSage Benchmark Report</h1>
            <h2>{report_type.replace('_', ' ').title()}</h2>
            <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(timestamp))}</p>
            <p>Execution time: {summary.get('execution_time_formatted', 'Unknown')}</p>
        </div>
        
        <div class="metrics">
            <h3>📊 Performance Metrics</h3>
"""
        
        # Add key metrics
        if 'query_ops_per_sec' in summary:
            html_content += f"""
            <div class="metric">
                <div class="metric-label">Query Operations per Second</div>
                <div class="metric-value">{summary['query_ops_per_sec']} ops/sec</div>
            </div>"""
        
        if 'avg_query_latency_ms' in summary:
            html_content += f"""
            <div class="metric">
                <div class="metric-label">Average Query Latency</div>
                <div class="metric-value">{summary['avg_query_latency_ms']} ms</div>
            </div>"""
        
        if 'peak_memory_mb' in summary:
            html_content += f"""
            <div class="metric">
                <div class="metric-label">Peak Memory Usage</div>
                <div class="metric-value">{summary['peak_memory_mb']} MB</div>
            </div>"""
        
        if 'connection_efficiency' in summary:
            html_content += f"""
            <div class="metric">
                <div class="metric-label">Connection Pool Efficiency</div>
                <div class="metric-value">{summary['connection_efficiency']}</div>
            </div>"""
        
        # Add validation results if available
        if validation:
            success_class = "success" if validation.get("overall_success", False) else "warning"
            status_text = "PASSED" if validation.get("overall_success", False) else "NEEDS ATTENTION"
            
            html_content += f"""
        </div>
        
        <div class="validation {success_class}">
            <h3>🎯 Optimization Claims Validation: {status_text}</h3>
            <p><strong>Claims Validated:</strong> {summary.get('claims_validated', '0/4')}</p>
"""
            
            # Add individual claim details
            details = validation.get("details", {})
            for claim_key, claim_data in details.items():
                status_icon = "✅" if claim_data.get("target_met", False) else "❌"
                html_content += f"""
            <p>{status_icon} {claim_data.get('claimed', claim_key)}</p>"""
            
            html_content += "</div>"
        
        html_content += """
        </div>
        
        <div style="margin-top: 40px; text-align: center; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 20px;">
            <p>TripSage Database Performance Benchmarking Suite</p>
            <p>Simplified reporting focused on core optimization claims</p>
        </div>
    </div>
</body>
</html>"""
        
        # Write HTML file
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        return html_path

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"