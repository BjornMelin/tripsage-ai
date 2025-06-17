"""
Performance Benchmark Report Generation.

This module generates comprehensive HTML and CSV reports from benchmark results,
including visualizations, performance comparisons, and optimization validation.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from jinja2 import DictLoader, Environment

logger = logging.getLogger(__name__)

# HTML template for comprehensive performance report
HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #007bff;
        }
        .header h1 {
            color: #007bff;
            margin-bottom: 10px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .metric-card h3 {
            margin-top: 0;
            color: #495057;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }
        .metric-improvement {
            font-size: 1.2em;
            margin-top: 10px;
        }
        .improvement-positive {
            color: #28a745;
        }
        .improvement-negative {
            color: #dc3545;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #495057;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 10px;
        }
        .chart-container {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .validation-status {
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .validation-passed {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .validation-failed {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .scenario-results {
            margin-bottom: 30px;
        }
        .scenario-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .scenario-header {
            background: #007bff;
            color: white;
            padding: 15px;
            font-weight: bold;
        }
        .scenario-content {
            padding: 20px;
        }
        .recommendation {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 10px;
            margin: 5px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #dee2e6;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ report_title }}</h1>
            <p>Generated on {{ generation_timestamp }}</p>
            <p>Execution time: {{ execution_time_formatted }}</p>
        </div>

        {% if validation_results %}
        <div class="section">
            <h2>🎯 Performance Validation</h2>
            {% if validation_results.validation_passed %}
            <div class="validation-status validation-passed">
            {% else %}
            <div class="validation-status validation-failed">
            {% endif %}
                <strong>
                    {% if validation_results.validation_passed %}
                        ✅ Performance validation PASSED
                    {% else %}
                        ❌ Performance validation FAILED
                    {% endif %}
                </strong>
                <p>{{ validation_summary }}</p>
            </div>
            
            {% if validation_results.recommendations %}
            <h3>Recommendations:</h3>
            {% for recommendation in validation_results.recommendations %}
            <div class="recommendation">{{ recommendation }}</div>
            {% endfor %}
            {% endif %}
        </div>
        {% endif %}

        {% if performance_summary %}
        <div class="section">
            <h2>📊 Performance Summary</h2>
            <div class="metrics-grid">
                {% for metric_name, metric_data in performance_summary.items() %}
                <div class="metric-card">
                    <h3>{{ metric_name | title }}</h3>
                    <div class="metric-value">{{ metric_data.current_value }}</div>
                    {% if metric_data.improvement %}
                    {% if metric_data.improvement > 0 %}
                    <div class="metric-improvement improvement-positive">
                    {% else %}
                    <div class="metric-improvement improvement-negative">
                    {% endif %}
                        {% if metric_data.improvement > 0 %}+{% endif %}{{ 
                        metric_data.improvement }}{{ metric_data.unit }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if charts %}
        <div class="section">
            <h2>📈 Performance Charts</h2>
            {% for chart in charts %}
            <div class="chart-container">
                <h3>{{ chart.title }}</h3>
                <div id="{{ chart.div_id }}"></div>
                <script>
                    Plotly.newPlot(
                        '{{ chart.div_id }}', 
                        {{ chart.data | safe }}, 
                        {{ chart.layout | safe }}
                    );
                </script>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if scenario_results %}
        <div class="section">
            <h2>🧪 Scenario Results</h2>
            <div class="scenario-results">
                {% for scenario in scenario_results %}
                <div class="scenario-card">
                    <div class="scenario-header">
                        {{ scenario.name }} - {{ scenario.workload_type }}
                    </div>
                    <div class="scenario-content">
                        <p><strong>Description:</strong> {{ scenario.description }}</p>
                        <p><strong>Optimization Level:</strong> 
                            {{ scenario.optimization_level }}</p>
                        <p><strong>Duration:</strong> 
                            {{ scenario.duration_seconds }}s</p>
                        <p><strong>Concurrent Users:</strong> 
                            {{ scenario.concurrent_users }}</p>
                        {% if scenario.metrics %}
                        <table>
                            <tr>
                                <th>Metric</th>
                                <th>Value</th>
                            </tr>
                            {% for metric, value in scenario.metrics.items() %}
                            <tr>
                                <td>{{ metric | title }}</td>
                                <td>{{ value }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if detailed_metrics %}
        <div class="section">
            <h2>🔍 Detailed Metrics</h2>
            {% for category, metrics in detailed_metrics.items() %}
            <h3>{{ category | title }}</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Target</th>
                    <th>Status</th>
                </tr>
                {% for metric, data in metrics.items() %}
                <tr>
                    <td>{{ metric | title }}</td>
                    <td>{{ data.value }}</td>
                    <td>{{ data.target or 'N/A' }}</td>
                    <td>{{ "✅" if data.meets_target else "❌" }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endfor %}
        </div>
        {% endif %}

        <div class="footer">
            <p>TripSage Database Performance Benchmarking Suite</p>
            <p>Report generated with Claude Code optimization framework validation</p>
        </div>
    </div>
</body>
</html>
"""


class BenchmarkReportGenerator:
    """Generate comprehensive performance benchmark reports."""

    def __init__(self, output_dir: Path):
        """Initialize report generator.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2 environment
        template_dict = {"report.html": HTML_REPORT_TEMPLATE}
        self.jinja_env = Environment(loader=DictLoader(template_dict))

        # Setup matplotlib style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

        logger.info(f"Report generator initialized with output dir: {output_dir}")

    async def generate_comparison_report(self, results: Dict[str, Any]) -> Path:
        """Generate comprehensive comparison report (baseline vs optimized).

        Args:
            results: Complete benchmark results

        Returns:
            Path to generated HTML report
        """
        logger.info("Generating comparison report...")

        # Extract key data
        baseline_metrics = results.get("baseline", {}).get("metrics", {})
        optimized_metrics = results.get("optimized", {}).get("metrics", {})
        validation_results = results.get("validation", {})

        # Generate performance summary
        performance_summary = self._create_performance_summary(
            baseline_metrics, optimized_metrics
        )

        # Generate charts
        charts = await self._create_performance_charts(
            baseline_metrics, optimized_metrics
        )

        # Prepare template data
        template_data = {
            "report_title": "Database Performance Comparison Report",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": self._format_duration(
                results.get("execution_time", 0)
            ),
            "validation_results": validation_results,
            "validation_summary": self._create_validation_summary(validation_results),
            "performance_summary": performance_summary,
            "charts": charts,
            "scenario_results": self._prepare_scenario_results(results),
            "detailed_metrics": self._prepare_detailed_metrics(
                baseline_metrics, optimized_metrics
            ),
        }

        # Generate HTML report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        # Save report
        report_path = self.output_dir / f"benchmark_comparison_{int(time.time())}.html"
        report_path.write_text(html_content, encoding="utf-8")

        # Also save raw results as JSON
        json_path = self.output_dir / f"benchmark_results_{int(time.time())}.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Comparison report generated: {report_path}")
        return report_path

    async def generate_baseline_report(self, results: Dict[str, Any]) -> Path:
        """Generate baseline-only performance report.

        Args:
            results: Baseline benchmark results

        Returns:
            Path to generated HTML report
        """
        logger.info("Generating baseline report...")

        baseline_metrics = results.get("baseline", {}).get("metrics", {})

        # Create simplified template data
        template_data = {
            "report_title": "Database Baseline Performance Report",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": self._format_duration(
                results.get("execution_time", 0)
            ),
            "performance_summary": self._create_baseline_summary(baseline_metrics),
            "scenario_results": self._prepare_scenario_results(results),
            "detailed_metrics": {
                "baseline": self._prepare_baseline_detailed_metrics(baseline_metrics)
            },
        }

        # Generate and save report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        report_path = self.output_dir / f"benchmark_baseline_{int(time.time())}.html"
        report_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Baseline report generated: {report_path}")
        return report_path

    async def generate_optimized_report(self, results: Dict[str, Any]) -> Path:
        """Generate optimized-only performance report.

        Args:
            results: Optimized benchmark results

        Returns:
            Path to generated HTML report
        """
        logger.info("Generating optimized report...")

        optimized_metrics = results.get("optimized", {}).get("metrics", {})

        # Create template data
        template_data = {
            "report_title": "Database Optimized Performance Report",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": self._format_duration(
                results.get("execution_time", 0)
            ),
            "performance_summary": self._create_optimized_summary(optimized_metrics),
            "scenario_results": self._prepare_scenario_results(results),
            "detailed_metrics": {
                "optimized": self._prepare_optimized_detailed_metrics(optimized_metrics)
            },
        }

        # Generate and save report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        report_path = self.output_dir / f"benchmark_optimized_{int(time.time())}.html"
        report_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Optimized report generated: {report_path}")
        return report_path

    async def generate_concurrency_report(self, results: Dict[str, Any]) -> Path:
        """Generate high-concurrency benchmark report.

        Args:
            results: High-concurrency benchmark results

        Returns:
            Path to generated HTML report
        """
        logger.info("Generating concurrency report...")

        concurrency_metrics = results.get("high_concurrency", {}).get("metrics", {})

        # Create template data
        template_data = {
            "report_title": "High-Concurrency Performance Report",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": self._format_duration(
                results.get("execution_time", 0)
            ),
            "performance_summary": self._create_concurrency_summary(
                concurrency_metrics
            ),
            "scenario_results": self._prepare_scenario_results(results),
            "detailed_metrics": {
                "concurrency": self._prepare_concurrency_detailed_metrics(
                    concurrency_metrics
                )
            },
        }

        # Generate and save report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        report_path = self.output_dir / f"benchmark_concurrency_{int(time.time())}.html"
        report_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Concurrency report generated: {report_path}")
        return report_path

    async def generate_custom_scenario_report(
        self, results: Dict[str, Any], scenario_name: str
    ) -> Path:
        """Generate custom scenario performance report.

        Args:
            results: Custom scenario results
            scenario_name: Name of the custom scenario

        Returns:
            Path to generated HTML report
        """
        logger.info(f"Generating custom scenario report for: {scenario_name}")

        scenario_metrics = results.get("custom_scenario", {}).get("metrics", {})

        # Create template data
        template_data = {
            "report_title": f"Custom Scenario Performance Report: {scenario_name}",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": self._format_duration(
                results.get("execution_time", 0)
            ),
            "performance_summary": self._create_custom_summary(scenario_metrics),
            "scenario_results": self._prepare_scenario_results(results),
            "detailed_metrics": {
                "custom": self._prepare_custom_detailed_metrics(scenario_metrics)
            },
        }

        # Generate and save report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        safe_scenario_name = "".join(
            c for c in scenario_name if c.isalnum() or c in ("-", "_")
        )
        report_path = (
            self.output_dir
            / f"benchmark_custom_{safe_scenario_name}_{int(time.time())}.html"
        )
        report_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Custom scenario report generated: {report_path}")
        return report_path

    async def generate_validation_report(
        self, validation_results: Dict[str, Any]
    ) -> Path:
        """Generate optimization claims validation report.

        Args:
            validation_results: Validation results

        Returns:
            Path to generated HTML report
        """
        logger.info("Generating validation report...")

        # Create template data focused on validation
        template_data = {
            "report_title": "Optimization Claims Validation Report",
            "generation_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "execution_time_formatted": "Validation Analysis",
            "validation_results": validation_results,
            "validation_summary": self._create_detailed_validation_summary(
                validation_results
            ),
            "detailed_metrics": {
                "validation": self._prepare_validation_detailed_metrics(
                    validation_results
                )
            },
        }

        # Generate and save report
        template = self.jinja_env.get_template("report.html")
        html_content = template.render(**template_data)

        report_path = (
            self.output_dir / f"optimization_validation_{int(time.time())}.html"
        )
        report_path.write_text(html_content, encoding="utf-8")

        # Also save validation results as JSON
        json_path = self.output_dir / f"validation_results_{int(time.time())}.json"
        with open(json_path, "w") as f:
            json.dump(validation_results, f, indent=2, default=str)

        logger.info(f"Validation report generated: {report_path}")
        return report_path

    async def export_to_csv(self, results: Dict[str, Any]) -> Path:
        """Export benchmark results to CSV format.

        Args:
            results: Benchmark results to export

        Returns:
            Path to generated CSV file
        """
        logger.info("Exporting results to CSV...")

        # Prepare data for CSV export
        csv_data = []

        # Extract metrics from baseline and optimized results
        for result_type in ["baseline", "optimized", "high_concurrency"]:
            if result_type not in results:
                continue

            metrics = results[result_type].get("metrics", {})

            # Query performance metrics
            query_metrics = metrics.get("query_performance", {})
            if "duration_stats" in query_metrics:
                duration_stats = query_metrics["duration_stats"]
                throughput = query_metrics.get("throughput", {})

                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "query_performance",
                        "metric_name": "mean_duration_ms",
                        "value": duration_stats.get("mean", 0) * 1000,
                        "unit": "milliseconds",
                    }
                )
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "query_performance",
                        "metric_name": "p95_duration_ms",
                        "value": duration_stats.get("p95", 0) * 1000,
                        "unit": "milliseconds",
                    }
                )
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "query_performance",
                        "metric_name": "operations_per_second",
                        "value": throughput.get("operations_per_second", 0),
                        "unit": "ops/sec",
                    }
                )

            # Vector search metrics
            vector_metrics = metrics.get("vector_search_performance", {})
            if "overall" in vector_metrics:
                overall = vector_metrics["overall"]
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "vector_search",
                        "metric_name": "mean_query_time_ms",
                        "value": overall.get("mean_query_time", 0) * 1000,
                        "unit": "milliseconds",
                    }
                )
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "vector_search",
                        "metric_name": "queries_per_second",
                        "value": overall.get("average_qps", 0),
                        "unit": "qps",
                    }
                )

            # Memory metrics
            memory_metrics = metrics.get("memory_performance", {})
            if "process_memory_mb" in memory_metrics:
                memory_data = memory_metrics["process_memory_mb"]
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "memory",
                        "metric_name": "peak_memory_mb",
                        "value": memory_data.get("peak", 0),
                        "unit": "MB",
                    }
                )
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "memory",
                        "metric_name": "average_memory_mb",
                        "value": memory_data.get("average", 0),
                        "unit": "MB",
                    }
                )

            # Connection metrics
            connection_metrics = metrics.get("connection_performance", {})
            if "pool_utilization" in connection_metrics:
                pool_data = connection_metrics["pool_utilization"]
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "connections",
                        "metric_name": "pool_utilization",
                        "value": pool_data.get("average", 0),
                        "unit": "ratio",
                    }
                )

            # Cache metrics
            cache_metrics = metrics.get("cache_performance", {})
            if "hit_ratio" in cache_metrics:
                hit_ratio_data = cache_metrics["hit_ratio"]
                csv_data.append(
                    {
                        "result_type": result_type,
                        "metric_category": "cache",
                        "metric_name": "hit_ratio",
                        "value": hit_ratio_data.get("average", 0),
                        "unit": "ratio",
                    }
                )

        # Create DataFrame and save to CSV
        df = pd.DataFrame(csv_data)
        csv_path = self.output_dir / f"benchmark_results_{int(time.time())}.csv"
        df.to_csv(csv_path, index=False)

        logger.info(f"Results exported to CSV: {csv_path}")
        return csv_path

    def _create_performance_summary(
        self, baseline_metrics: Dict[str, Any], optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create performance summary comparing baseline to optimized."""
        summary = {}

        # Query performance comparison
        baseline_query = baseline_metrics.get("query_performance", {})
        optimized_query = optimized_metrics.get("query_performance", {})

        if "duration_stats" in baseline_query and "duration_stats" in optimized_query:
            baseline_p95 = (
                baseline_query["duration_stats"]["p95"] * 1000
            )  # Convert to ms
            optimized_p95 = optimized_query["duration_stats"]["p95"] * 1000
            improvement = (
                ((baseline_p95 - optimized_p95) / baseline_p95 * 100)
                if baseline_p95 > 0
                else 0
            )

            summary["Query Latency (P95)"] = {
                "current_value": f"{optimized_p95:.2f}ms",
                "improvement": f"{improvement:.1f}%",
                "unit": " improvement",
            }

        # Throughput comparison
        baseline_throughput = baseline_query.get("throughput", {}).get(
            "operations_per_second", 0
        )
        optimized_throughput = optimized_query.get("throughput", {}).get(
            "operations_per_second", 0
        )

        if baseline_throughput > 0:
            throughput_improvement = (
                (optimized_throughput - baseline_throughput) / baseline_throughput * 100
            )
            summary["Query Throughput"] = {
                "current_value": f"{optimized_throughput:.0f} ops/sec",
                "improvement": f"{throughput_improvement:.1f}%",
                "unit": " improvement",
            }

        # Vector search performance
        baseline_vector = baseline_metrics.get("vector_search_performance", {})
        optimized_vector = optimized_metrics.get("vector_search_performance", {})

        if "overall" in baseline_vector and "overall" in optimized_vector:
            baseline_qps = baseline_vector["overall"]["average_qps"]
            optimized_qps = optimized_vector["overall"]["average_qps"]

            if baseline_qps > 0:
                vector_improvement = (optimized_qps - baseline_qps) / baseline_qps * 100
                summary["Vector Search QPS"] = {
                    "current_value": f"{optimized_qps:.1f} qps",
                    "improvement": f"{vector_improvement:.1f}%",
                    "unit": " improvement",
                }

        return summary

    def _create_baseline_summary(
        self, baseline_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary for baseline-only results."""
        summary = {}

        query_metrics = baseline_metrics.get("query_performance", {})
        if "duration_stats" in query_metrics:
            duration_stats = query_metrics["duration_stats"]
            summary["Average Query Time"] = {
                "current_value": f"{duration_stats['mean'] * 1000:.2f}ms",
            }
            summary["P95 Query Time"] = {
                "current_value": f"{duration_stats['p95'] * 1000:.2f}ms",
            }

        if "throughput" in query_metrics:
            throughput = query_metrics["throughput"]["operations_per_second"]
            summary["Query Throughput"] = {
                "current_value": f"{throughput:.0f} ops/sec",
            }

        return summary

    def _create_optimized_summary(
        self, optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary for optimized-only results."""
        return self._create_baseline_summary(optimized_metrics)  # Same structure

    def _create_concurrency_summary(
        self, concurrency_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary for high-concurrency results."""
        return self._create_baseline_summary(concurrency_metrics)  # Same structure

    def _create_custom_summary(
        self, scenario_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary for custom scenario results."""
        return self._create_baseline_summary(scenario_metrics)  # Same structure

    async def _create_performance_charts(
        self, baseline_metrics: Dict[str, Any], optimized_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create performance comparison charts."""
        charts = []

        # Query latency comparison chart
        baseline_query = baseline_metrics.get("query_performance", {})
        optimized_query = optimized_metrics.get("query_performance", {})

        if "duration_stats" in baseline_query and "duration_stats" in optimized_query:
            baseline_stats = baseline_query["duration_stats"]
            optimized_stats = optimized_query["duration_stats"]

            chart_data = [
                {
                    "x": ["Mean", "Median", "P95", "P99"],
                    "y": [
                        baseline_stats["mean"] * 1000,
                        baseline_stats["median"] * 1000,
                        baseline_stats["p95"] * 1000,
                        baseline_stats["p99"] * 1000,
                    ],
                    "name": "Baseline",
                    "type": "bar",
                },
                {
                    "x": ["Mean", "Median", "P95", "P99"],
                    "y": [
                        optimized_stats["mean"] * 1000,
                        optimized_stats["median"] * 1000,
                        optimized_stats["p95"] * 1000,
                        optimized_stats["p99"] * 1000,
                    ],
                    "name": "Optimized",
                    "type": "bar",
                },
            ]

            chart_layout = {
                "title": "Query Latency Comparison",
                "xaxis": {"title": "Percentile"},
                "yaxis": {"title": "Latency (ms)"},
                "barmode": "group",
            }

            charts.append(
                {
                    "title": "Query Latency Comparison",
                    "div_id": "query_latency_chart",
                    "data": json.dumps(chart_data),
                    "layout": json.dumps(chart_layout),
                }
            )

        # Throughput comparison chart
        baseline_throughput = baseline_query.get("throughput", {}).get(
            "operations_per_second", 0
        )
        optimized_throughput = optimized_query.get("throughput", {}).get(
            "operations_per_second", 0
        )

        if baseline_throughput > 0 and optimized_throughput > 0:
            chart_data = [
                {
                    "x": ["Baseline", "Optimized"],
                    "y": [baseline_throughput, optimized_throughput],
                    "type": "bar",
                    "marker": {"color": ["#ff7f0e", "#2ca02c"]},
                },
            ]

            chart_layout = {
                "title": "Query Throughput Comparison",
                "xaxis": {"title": "Configuration"},
                "yaxis": {"title": "Operations per Second"},
            }

            charts.append(
                {
                    "title": "Query Throughput Comparison",
                    "div_id": "throughput_chart",
                    "data": json.dumps(chart_data),
                    "layout": json.dumps(chart_layout),
                }
            )

        return charts

    def _create_validation_summary(self, validation_results: Dict[str, Any]) -> str:
        """Create a summary of validation results."""
        if not validation_results:
            return "No validation results available."

        passed = validation_results.get("validation_passed", False)
        improvements = validation_results.get("improvements", {})

        summary_parts = []

        if "query_performance" in improvements:
            ratio = improvements["query_performance"]["improvement_ratio"]
            summary_parts.append(f"Query performance improved by {ratio:.1f}x")

        if "vector_search" in improvements:
            ratio = improvements["vector_search"]["improvement_ratio"]
            summary_parts.append(f"Vector search improved by {ratio:.1f}x")

        if summary_parts:
            summary = f"Performance analysis shows: {', '.join(summary_parts)}"
        else:
            summary = "Performance analysis completed"

        if not passed:
            summary += ". Some optimization targets were not met."

        return summary

    def _create_detailed_validation_summary(
        self, validation_results: Dict[str, Any]
    ) -> str:
        """Create detailed validation summary for validation-specific report."""
        if not validation_results:
            return "No validation data available."

        claims = validation_results.get("claims_validation", {})
        total_claims = len(claims)
        met_claims = sum(
            1 for claim in claims.values() if claim.get("target_met", False)
        )

        summary = (
            f"Validated {total_claims} optimization claims. {met_claims} of "
            f"{total_claims} targets were met."
        )

        if validation_results.get("overall_success", False):
            summary += " All critical performance improvements have been validated."
        else:
            summary += " Some critical targets were not achieved and require attention."

        return summary

    def _prepare_scenario_results(
        self, results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prepare scenario results for template rendering."""
        scenario_results = []

        for result_type in [
            "baseline",
            "optimized",
            "high_concurrency",
            "custom_scenario",
        ]:
            if result_type not in results:
                continue

            scenarios = results[result_type].get("scenarios", [])
            for scenario in scenarios:
                if isinstance(scenario, dict):
                    scenario_data = {
                        "name": scenario.get("scenario", f"{result_type} scenario"),
                        "workload_type": scenario.get("workload_type", "unknown"),
                        "description": f"{result_type.title()} benchmark scenario",
                        "optimization_level": result_type,
                        "duration_seconds": scenario.get("duration", "N/A"),
                        "concurrent_users": scenario.get("concurrent_users", "N/A"),
                        "metrics": self._extract_scenario_metrics(scenario),
                    }
                    scenario_results.append(scenario_data)

        return scenario_results

    def _extract_scenario_metrics(self, scenario: Dict[str, Any]) -> Dict[str, str]:
        """Extract key metrics from scenario for display."""
        metrics = {}

        if "summary" in scenario:
            summary = scenario["summary"]
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    if "time" in key.lower() or "duration" in key.lower():
                        metrics[key] = f"{value:.3f}s"
                    elif "count" in key.lower() or "ops" in key.lower():
                        metrics[key] = f"{value:,}"
                    else:
                        metrics[key] = f"{value:.2f}"
                else:
                    metrics[key] = str(value)

        return metrics

    def _prepare_detailed_metrics(
        self, baseline_metrics: Dict[str, Any], optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Prepare detailed metrics for comparison table."""
        detailed = {}

        # Query performance metrics
        query_metrics = {}
        baseline_query = baseline_metrics.get("query_performance", {})
        optimized_query = optimized_metrics.get("query_performance", {})

        if "duration_stats" in baseline_query and "duration_stats" in optimized_query:
            baseline_p95 = baseline_query["duration_stats"]["p95"] * 1000
            optimized_p95 = optimized_query["duration_stats"]["p95"] * 1000

            query_metrics["P95 Latency"] = {
                "value": f"{optimized_p95:.2f}ms (vs {baseline_p95:.2f}ms)",
                "target": "<100ms",
                "meets_target": optimized_p95 < 100,
            }

        if query_metrics:
            detailed["Query Performance"] = query_metrics

        # Vector search metrics
        vector_metrics = {}
        baseline_vector = baseline_metrics.get("vector_search_performance", {})
        optimized_vector = optimized_metrics.get("vector_search_performance", {})

        if "overall" in baseline_vector and "overall" in optimized_vector:
            baseline_qps = baseline_vector["overall"]["average_qps"]
            optimized_qps = optimized_vector["overall"]["average_qps"]

            vector_metrics["Queries per Second"] = {
                "value": f"{optimized_qps:.1f} (vs {baseline_qps:.1f})",
                "target": ">100 QPS",
                "meets_target": optimized_qps > 100,
            }

        if vector_metrics:
            detailed["Vector Search"] = vector_metrics

        return detailed

    def _prepare_baseline_detailed_metrics(
        self, baseline_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare detailed metrics for baseline-only report."""
        metrics = {}

        query_metrics = baseline_metrics.get("query_performance", {})
        if "duration_stats" in query_metrics:
            duration_stats = query_metrics["duration_stats"]
            metrics["Mean Latency"] = {
                "value": f"{duration_stats['mean'] * 1000:.2f}ms",
                "target": None,
                "meets_target": None,
            }
            metrics["P95 Latency"] = {
                "value": f"{duration_stats['p95'] * 1000:.2f}ms",
                "target": None,
                "meets_target": None,
            }

        return metrics

    def _prepare_optimized_detailed_metrics(
        self, optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare detailed metrics for optimized-only report."""
        return self._prepare_baseline_detailed_metrics(optimized_metrics)

    def _prepare_concurrency_detailed_metrics(
        self, concurrency_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare detailed metrics for concurrency report."""
        return self._prepare_baseline_detailed_metrics(concurrency_metrics)

    def _prepare_custom_detailed_metrics(
        self, scenario_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare detailed metrics for custom scenario report."""
        return self._prepare_baseline_detailed_metrics(scenario_metrics)

    def _prepare_validation_detailed_metrics(
        self, validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare detailed metrics for validation report."""
        metrics = {}

        claims = validation_results.get("claims_validation", {})
        for claim_name, claim_data in claims.items():
            metrics[claim_data.get("claimed_improvement", claim_name)] = {
                "value": f"{claim_data.get('measured_improvement', 0):.2f}x",
                "target": claim_data.get("claimed_improvement", ""),
                "meets_target": claim_data.get("target_met", False),
            }

        return metrics

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
