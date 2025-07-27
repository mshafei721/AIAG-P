"""
AUX Test Reporting System.

This module provides comprehensive test reporting capabilities including
HTML reports, JSON metrics export, and detailed performance analysis.
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

from .scenario_runner import ScenarioResult


@dataclass
class TestMetrics:
    """Comprehensive test execution metrics."""
    
    # Scenario metrics
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    skipped_scenarios: int = 0
    success_rate: float = 0.0
    
    # Timing metrics
    total_execution_time: float = 0.0
    average_scenario_time: float = 0.0
    min_scenario_time: float = 0.0
    max_scenario_time: float = 0.0
    
    # Step metrics
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    step_success_rate: float = 0.0
    
    # Performance metrics
    agent_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.agent_metrics is None:
            self.agent_metrics = {}


class TestReporter:
    """
    Comprehensive test reporting system.
    
    Generates multiple report formats including HTML, JSON, and plain text
    with detailed metrics, charts, and analysis.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the test reporter.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def generate_html_report(
        self,
        results: 'TestResults',  # Forward reference to avoid circular import
        output_path: Union[str, Path]
    ) -> None:
        """
        Generate comprehensive HTML test report.
        
        Args:
            results: Test execution results
            output_path: Path to save HTML report
        """
        html_content = self._build_html_report(results)
        
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report generated: {output_path}")
    
    def _build_html_report(self, results: 'TestResults') -> str:
        """Build comprehensive HTML report content."""
        
        # Calculate additional metrics
        metrics = results.metrics or TestMetrics()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AUX Protocol Test Report</title>
    <style>
        {self._get_html_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AUX Protocol Test Report</h1>
            <div class="report-meta">
                <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results.end_time))}</p>
                <p>Total Duration: {results.total_execution_time:.2f} seconds</p>
            </div>
        </header>
        
        <section class="summary">
            <h2>Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card {'success' if results.success_rate >= 0.9 else 'warning' if results.success_rate >= 0.7 else 'error'}">
                    <h3>Success Rate</h3>
                    <div class="metric-value">{results.success_rate:.1%}</div>
                    <div class="metric-detail">{results.passed_scenarios}/{results.total_scenarios} scenarios passed</div>
                </div>
                <div class="metric-card">
                    <h3>Total Time</h3>
                    <div class="metric-value">{results.total_execution_time:.1f}s</div>
                    <div class="metric-detail">Average: {metrics.average_scenario_time:.1f}s per scenario</div>
                </div>
                <div class="metric-card">
                    <h3>Steps</h3>
                    <div class="metric-value">{metrics.total_steps}</div>
                    <div class="metric-detail">{metrics.passed_steps} passed, {metrics.failed_steps} failed</div>
                </div>
                <div class="metric-card">
                    <h3>Scenarios</h3>
                    <div class="metric-value">{results.total_scenarios}</div>
                    <div class="metric-detail">{results.failed_scenarios} failed</div>
                </div>
            </div>
        </section>
        
        <section class="scenarios">
            <h2>Scenario Results</h2>
            <div class="scenarios-table">
                <table>
                    <thead>
                        <tr>
                            <th>Scenario</th>
                            <th>Status</th>
                            <th>Steps</th>
                            <th>Duration</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._build_scenario_rows(results.scenario_results)}
                    </tbody>
                </table>
            </div>
        </section>
        
        <section class="performance">
            <h2>Performance Analysis</h2>
            <div class="performance-grid">
                <div class="perf-card">
                    <h4>Execution Times</h4>
                    <ul>
                        <li>Fastest: {metrics.min_scenario_time:.2f}s</li>
                        <li>Slowest: {metrics.max_scenario_time:.2f}s</li>
                        <li>Average: {metrics.average_scenario_time:.2f}s</li>
                    </ul>
                </div>
                <div class="perf-card">
                    <h4>Step Performance</h4>
                    <ul>
                        <li>Total Steps: {metrics.total_steps}</li>
                        <li>Step Success Rate: {metrics.step_success_rate:.1%}</li>
                        <li>Avg Steps/Scenario: {metrics.total_steps / results.total_scenarios if results.total_scenarios > 0 else 0:.1f}</li>
                    </ul>
                </div>
            </div>
        </section>
        
        {self._build_error_section(results)}
        
        <section class="details">
            <h2>Detailed Results</h2>
            {self._build_detailed_results(results.scenario_results)}
        </section>
        
        <footer>
            <p>Report generated by AUX Protocol Test Harness</p>
        </footer>
    </div>
    
    <script>
        {self._get_html_scripts()}
    </script>
</body>
</html>
"""
        return html
    
    def _get_html_styles(self) -> str:
        """Get CSS styles for HTML report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        header {
            border-bottom: 3px solid #007acc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #007acc;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .report-meta {
            color: #666;
            font-size: 0.9em;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: #f9f9f9;
            border-left: 4px solid #007acc;
            padding: 20px;
            border-radius: 4px;
        }
        
        .metric-card.success {
            border-left-color: #28a745;
        }
        
        .metric-card.warning {
            border-left-color: #ffc107;
        }
        
        .metric-card.error {
            border-left-color: #dc3545;
        }
        
        .metric-card h3 {
            color: #555;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007acc;
            margin-bottom: 5px;
        }
        
        .metric-detail {
            color: #666;
            font-size: 0.8em;
        }
        
        section {
            margin: 30px 0;
        }
        
        h2 {
            color: #007acc;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        
        .status-pass {
            color: #28a745;
            font-weight: bold;
        }
        
        .status-fail {
            color: #dc3545;
            font-weight: bold;
        }
        
        .performance-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .perf-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        
        .perf-card h4 {
            color: #007acc;
            margin-bottom: 15px;
        }
        
        .perf-card ul {
            list-style: none;
        }
        
        .perf-card li {
            padding: 5px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .perf-card li:last-child {
            border-bottom: none;
        }
        
        .error-section {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 4px;
            padding: 20px;
        }
        
        .error-item {
            background: white;
            border-left: 3px solid #dc3545;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 4px 4px 0;
        }
        
        .scenario-detail {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            margin: 15px 0;
            overflow: hidden;
        }
        
        .scenario-header {
            background: #e9ecef;
            padding: 15px;
            cursor: pointer;
            font-weight: 600;
        }
        
        .scenario-content {
            padding: 15px;
            display: none;
        }
        
        .scenario-content.active {
            display: block;
        }
        
        .step-list {
            list-style: none;
            margin: 10px 0;
        }
        
        .step-item {
            padding: 8px;
            margin: 5px 0;
            background: white;
            border-radius: 3px;
            border-left: 3px solid #28a745;
        }
        
        .step-item.failed {
            border-left-color: #dc3545;
        }
        
        footer {
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 40px;
        }
        
        .collapsible {
            cursor: pointer;
        }
        
        .collapsible:hover {
            background-color: #e9ecef;
        }
        """
    
    def _get_html_scripts(self) -> str:
        """Get JavaScript for HTML report interactivity."""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Make scenario details collapsible
            const headers = document.querySelectorAll('.scenario-header');
            headers.forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    content.classList.toggle('active');
                });
            });
        });
        """
    
    def _build_scenario_rows(self, scenario_results: List[ScenarioResult]) -> str:
        """Build table rows for scenario results."""
        rows = []
        
        for result in scenario_results:
            status_class = "status-pass" if result.success else "status-fail"
            status_text = "PASS" if result.success else "FAIL"
            
            rows.append(f"""
                <tr>
                    <td>{result.scenario_name}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td>{result.passed_steps}/{result.total_steps}</td>
                    <td>{result.execution_time:.2f}s</td>
                    <td>
                        <button onclick="toggleDetails('{result.scenario_name}')">View Details</button>
                    </td>
                </tr>
            """)
        
        return "".join(rows)
    
    def _build_error_section(self, results: 'TestResults') -> str:
        """Build error section if there are errors."""
        
        all_errors = results.errors.copy()
        
        # Collect errors from scenario results
        for scenario_result in results.scenario_results:
            for error in scenario_result.errors:
                all_errors.append({
                    'scenario': scenario_result.scenario_name,
                    'error': error
                })
        
        if not all_errors:
            return ""
        
        error_items = []
        for error in all_errors:
            scenario = error.get('scenario', 'System')
            error_msg = error.get('error', error.get('message', 'Unknown error'))
            
            error_items.append(f"""
                <div class="error-item">
                    <strong>{scenario}:</strong> {error_msg}
                </div>
            """)
        
        return f"""
        <section class="errors">
            <h2>Errors ({len(all_errors)})</h2>
            <div class="error-section">
                {"".join(error_items)}
            </div>
        </section>
        """
    
    def _build_detailed_results(self, scenario_results: List[ScenarioResult]) -> str:
        """Build detailed results section."""
        
        details = []
        
        for result in scenario_results:
            step_items = []
            
            for step_result in result.step_results:
                success = step_result.get('success', False)
                step_class = "" if success else "failed"
                step_name = step_result.get('step_name', 'Unknown Step')
                execution_time = step_result.get('execution_time', 0)
                
                step_items.append(f"""
                    <li class="step-item {step_class}">
                        <strong>{step_name}</strong> - {execution_time:.2f}s
                        {f"<br><span style='color: #dc3545;'>Error: {step_result.get('error', '')}</span>" if not success else ""}
                    </li>
                """)
            
            details.append(f"""
                <div class="scenario-detail">
                    <div class="scenario-header collapsible">
                        {result.scenario_name} 
                        <span style="float: right;">
                            {'✓' if result.success else '✗'} 
                            {result.execution_time:.2f}s
                        </span>
                    </div>
                    <div class="scenario-content">
                        <p><strong>Steps:</strong> {result.passed_steps}/{result.total_steps} passed</p>
                        <p><strong>Duration:</strong> {result.execution_time:.2f} seconds</p>
                        <ul class="step-list">
                            {"".join(step_items)}
                        </ul>
                    </div>
                </div>
            """)
        
        return "".join(details)
    
    async def save_metrics_json(
        self,
        results: 'TestResults',
        output_path: Union[str, Path]
    ) -> None:
        """
        Save test metrics as JSON file.
        
        Args:
            results: Test execution results
            output_path: Path to save JSON metrics
        """
        
        metrics_data = {
            'summary': {
                'total_scenarios': results.total_scenarios,
                'passed_scenarios': results.passed_scenarios,
                'failed_scenarios': results.failed_scenarios,
                'success_rate': results.success_rate,
                'total_execution_time': results.total_execution_time,
                'start_time': results.start_time,
                'end_time': results.end_time
            },
            'metrics': asdict(results.metrics) if results.metrics else {},
            'scenarios': [
                {
                    'name': r.scenario_name,
                    'success': r.success,
                    'total_steps': r.total_steps,
                    'passed_steps': r.passed_steps,
                    'failed_steps': r.failed_steps,
                    'execution_time': r.execution_time,
                    'errors': r.errors,
                    'metrics': r.metrics,
                    'agent_metrics': r.agent_metrics
                }
                for r in results.scenario_results
            ],
            'errors': results.errors
        }
        
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        
        self.logger.info(f"JSON metrics saved: {output_path}")
    
    async def save_detailed_logs(
        self,
        results: 'TestResults',
        output_path: Union[str, Path]
    ) -> None:
        """
        Save detailed execution logs as text file.
        
        Args:
            results: Test execution results
            output_path: Path to save detailed logs
        """
        
        lines = [
            "AUX Protocol Test Execution Log",
            "=" * 50,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Scenarios: {results.total_scenarios}",
            f"Passed: {results.passed_scenarios}",
            f"Failed: {results.failed_scenarios}",
            f"Success Rate: {results.success_rate:.1%}",
            f"Total Time: {results.total_execution_time:.2f}s",
            "",
            "SCENARIO DETAILS",
            "=" * 50
        ]
        
        for result in results.scenario_results:
            lines.extend([
                f"\nScenario: {result.scenario_name}",
                f"Status: {'PASS' if result.success else 'FAIL'}",
                f"Steps: {result.passed_steps}/{result.total_steps}",
                f"Duration: {result.execution_time:.2f}s",
                f"Start: {time.strftime('%H:%M:%S', time.localtime(result.start_time))}",
                f"End: {time.strftime('%H:%M:%S', time.localtime(result.end_time))}"
            ])
            
            if result.errors:
                lines.append("Errors:")
                for error in result.errors:
                    lines.append(f"  - {error}")
            
            if result.step_results:
                lines.append("Steps:")
                for step in result.step_results:
                    status = "PASS" if step.get('success', False) else "FAIL"
                    step_name = step.get('step_name', 'Unknown')
                    exec_time = step.get('execution_time', 0)
                    lines.append(f"  {status} {step_name} ({exec_time:.2f}s)")
                    
                    if not step.get('success', False) and 'error' in step:
                        lines.append(f"      Error: {step['error']}")
        
        if results.errors:
            lines.extend([
                "",
                "SYSTEM ERRORS",
                "=" * 50
            ])
            for error in results.errors:
                lines.append(f"- {error}")
        
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"Detailed logs saved: {output_path}")
    
    def print_summary(self, results: 'TestResults') -> None:
        """Print a summary of test results to console."""
        
        print("\n" + "=" * 60)
        print("AUX PROTOCOL TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Scenarios: {results.total_scenarios}")
        print(f"Passed: {results.passed_scenarios}")
        print(f"Failed: {results.failed_scenarios}")
        print(f"Success Rate: {results.success_rate:.1%}")
        print(f"Total Time: {results.total_execution_time:.2f} seconds")
        
        if results.metrics:
            print(f"Average Scenario Time: {results.metrics.average_scenario_time:.2f}s")
            print(f"Total Steps: {results.metrics.total_steps}")
            print(f"Step Success Rate: {results.metrics.step_success_rate:.1%}")
        
        print("=" * 60)
        
        # Print failed scenarios if any
        if results.failed_scenarios > 0:
            print("\nFAILED SCENARIOS:")
            for result in results.scenario_results:
                if not result.success:
                    print(f"  ✗ {result.scenario_name} ({result.execution_time:.2f}s)")
                    if result.errors:
                        for error in result.errors[:3]:  # Show first 3 errors
                            error_msg = error.get('error', error.get('message', str(error)))
                            print(f"    Error: {error_msg}")
        
        print("")