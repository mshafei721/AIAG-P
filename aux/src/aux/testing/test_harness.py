"""
AUX Test Harness.

This module provides the TestHarness class for coordinating test execution,
managing multiple agents, and providing comprehensive test orchestration
with parallel and sequential execution modes.
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
import logging

from .mock_agent import MockAgent, AgentBehavior
from .scenario_runner import ScenarioRunner, TestScenario, ScenarioResult
from .reporting import TestReporter, TestMetrics
# Using standard logging


@dataclass
class TestConfiguration:
    """Test execution configuration."""
    
    # Execution settings
    max_parallel_agents: int = 3
    execution_timeout: Optional[float] = None  # seconds
    stop_on_first_failure: bool = False
    
    # Agent settings
    default_behavior: Optional[AgentBehavior] = None
    agent_pool_size: int = 5
    
    # Scenario settings
    scenario_filter_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None
    
    # Reporting settings
    save_detailed_logs: bool = True
    generate_html_report: bool = True
    save_metrics_json: bool = True
    
    # Performance settings
    performance_benchmarking: bool = False
    benchmark_iterations: int = 1
    
    # Server settings
    server_url: str = "ws://localhost:8765"
    
    # Retry settings
    retry_failed_scenarios: bool = False
    max_scenario_retries: int = 2


@dataclass 
class TestResults:
    """Comprehensive test execution results."""
    
    # Overall results
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    skipped_scenarios: int = 0
    
    # Timing
    start_time: float = 0.0
    end_time: float = 0.0
    total_execution_time: float = 0.0
    
    # Detailed results
    scenario_results: List[ScenarioResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    metrics: Optional[TestMetrics] = None
    
    # Agent performance
    agent_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        return self.passed_scenarios / self.total_scenarios if self.total_scenarios > 0 else 0.0
    
    @property
    def summary(self) -> str:
        """Get summary string of results."""
        return (
            f"Test Results: {self.passed_scenarios}/{self.total_scenarios} passed "
            f"({self.success_rate:.1%} success rate) in {self.total_execution_time:.2f}s"
        )


class TestHarness:
    """
    Comprehensive test harness for AUX protocol testing.
    
    Features:
    - Multiple scenario execution modes (sequential/parallel)
    - Agent pool management for concurrent testing
    - Comprehensive result collection and reporting
    - Performance benchmarking capabilities
    - Test filtering and configuration management
    """
    
    def __init__(
        self,
        config: Optional[TestConfiguration] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the test harness.
        
        Args:
            config: Test configuration (uses defaults if None)
            logger: Optional logger instance
        """
        self.config = config or TestConfiguration()
        self.logger = logger or logging.getLogger(__name__)
        
        # Test execution state
        self.running = False
        self.current_results: Optional[TestResults] = None
        self.scenario_runners: List[ScenarioRunner] = []
        self.agent_pool: List[MockAgent] = []
        
        # Reporting
        self.reporter = TestReporter(logger=self.logger)
        
        self.logger.info("TestHarness initialized")
    
    async def load_scenarios(
        self,
        scenario_paths: Union[str, Path, List[Union[str, Path]]]
    ) -> List[TestScenario]:
        """
        Load test scenarios from files or directories.
        
        Args:
            scenario_paths: Path(s) to scenario files or directories
            
        Returns:
            List of loaded test scenarios
        """
        if isinstance(scenario_paths, (str, Path)):
            scenario_paths = [scenario_paths]
        
        scenarios = []
        
        for path in scenario_paths:
            path = Path(path)
            
            if path.is_file():
                # Load single scenario file
                try:
                    runner = ScenarioRunner(
                        self.config.server_url,
                        self.config.default_behavior,
                        self.logger
                    )
                    scenario = runner.load_scenario_file(path)
                    scenarios.append(scenario)
                    self.logger.debug(f"Loaded scenario: {scenario.name}")
                except Exception as e:
                    self.logger.error(f"Failed to load scenario {path}: {e}")
                    
            elif path.is_dir():
                # Load all scenario files in directory
                for file_path in path.glob("**/*.yaml"):
                    try:
                        runner = ScenarioRunner(
                            self.config.server_url,
                            self.config.default_behavior,
                            self.logger
                        )
                        scenario = runner.load_scenario_file(file_path)
                        scenarios.append(scenario)
                        self.logger.debug(f"Loaded scenario: {scenario.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to load scenario {file_path}: {e}")
                
                for file_path in path.glob("**/*.json"):
                    try:
                        runner = ScenarioRunner(
                            self.config.server_url,
                            self.config.default_behavior,
                            self.logger
                        )
                        scenario = runner.load_scenario_file(file_path)
                        scenarios.append(scenario)
                        self.logger.debug(f"Loaded scenario: {scenario.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to load scenario {file_path}: {e}")
            else:
                self.logger.warning(f"Path does not exist: {path}")
        
        # Apply filtering if configured
        scenarios = self._filter_scenarios(scenarios)
        
        self.logger.info(f"Loaded {len(scenarios)} scenarios for execution")
        return scenarios
    
    def _filter_scenarios(self, scenarios: List[TestScenario]) -> List[TestScenario]:
        """Filter scenarios based on configuration tags."""
        
        if not self.config.scenario_filter_tags and not self.config.exclude_tags:
            return scenarios
        
        filtered = []
        
        for scenario in scenarios:
            scenario_tags = scenario.tags or []
            
            # Check include filters
            if self.config.scenario_filter_tags:
                if not any(tag in scenario_tags for tag in self.config.scenario_filter_tags):
                    self.logger.debug(f"Scenario {scenario.name} filtered out (missing required tags)")
                    continue
            
            # Check exclude filters
            if self.config.exclude_tags:
                if any(tag in scenario_tags for tag in self.config.exclude_tags):
                    self.logger.debug(f"Scenario {scenario.name} filtered out (has excluded tag)")
                    continue
            
            filtered.append(scenario)
        
        return filtered
    
    async def run_scenarios(
        self,
        scenarios: List[TestScenario],
        execution_mode: str = "sequential"
    ) -> TestResults:
        """
        Execute a list of test scenarios.
        
        Args:
            scenarios: List of scenarios to execute
            execution_mode: "sequential" or "parallel"
            
        Returns:
            Comprehensive test results
        """
        if self.running:
            raise RuntimeError("Test harness is already running")
        
        self.running = True
        start_time = time.time()
        
        self.logger.info(f"Starting test execution: {len(scenarios)} scenarios in {execution_mode} mode")
        
        # Initialize results
        self.current_results = TestResults(
            total_scenarios=len(scenarios),
            start_time=start_time
        )
        
        try:
            if execution_mode == "parallel":
                await self._run_scenarios_parallel(scenarios)
            else:
                await self._run_scenarios_sequential(scenarios)
                
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            self.current_results.errors.append({
                'type': 'execution_error',
                'message': str(e),
                'timestamp': time.time()
            })
        
        finally:
            self.running = False
            end_time = time.time()
            
            self.current_results.end_time = end_time
            self.current_results.total_execution_time = end_time - start_time
            
            # Calculate final counts
            self._calculate_final_results()
            
            # Generate metrics
            self.current_results.metrics = self._generate_test_metrics()
            
            self.logger.info(f"Test execution completed: {self.current_results.summary}")
        
        return self.current_results
    
    async def _run_scenarios_sequential(self, scenarios: List[TestScenario]) -> None:
        """Execute scenarios sequentially."""
        
        for i, scenario in enumerate(scenarios):
            self.logger.info(f"Executing scenario {i+1}/{len(scenarios)}: {scenario.name}")
            
            try:
                # Create dedicated runner for this scenario
                runner = ScenarioRunner(
                    self.config.server_url,
                    self.config.default_behavior,
                    self.logger
                )
                
                # Execute scenario with timeout if configured
                if self.config.execution_timeout:
                    result = await asyncio.wait_for(
                        runner.execute_scenario(scenario),
                        timeout=self.config.execution_timeout
                    )
                else:
                    result = await runner.execute_scenario(scenario)
                
                self.current_results.scenario_results.append(result)
                
                # Stop on first failure if configured
                if not result.success and self.config.stop_on_first_failure:
                    self.logger.warning("Stopping execution due to first failure")
                    break
                    
            except asyncio.TimeoutError:
                error_result = ScenarioResult(
                    scenario_name=scenario.name,
                    success=False,
                    total_steps=len(scenario.steps),
                    passed_steps=0,
                    failed_steps=len(scenario.steps),
                    execution_time=self.config.execution_timeout,
                    start_time=time.time(),
                    end_time=time.time(),
                    step_results=[],
                    errors=[{'error': 'Scenario execution timeout'}],
                    metrics={},
                    agent_metrics={}
                )
                self.current_results.scenario_results.append(error_result)
                self.logger.error(f"Scenario {scenario.name} timed out")
                
            except Exception as e:
                error_result = ScenarioResult(
                    scenario_name=scenario.name,
                    success=False,
                    total_steps=len(scenario.steps),
                    passed_steps=0,
                    failed_steps=len(scenario.steps),
                    execution_time=0.0,
                    start_time=time.time(),
                    end_time=time.time(),
                    step_results=[],
                    errors=[{'error': str(e)}],
                    metrics={},
                    agent_metrics={}
                )
                self.current_results.scenario_results.append(error_result)
                self.logger.error(f"Scenario {scenario.name} failed with exception: {e}")
    
    async def _run_scenarios_parallel(self, scenarios: List[TestScenario]) -> None:
        """Execute scenarios in parallel with controlled concurrency."""
        
        semaphore = asyncio.Semaphore(self.config.max_parallel_agents)
        
        async def run_single_scenario(scenario: TestScenario) -> ScenarioResult:
            async with semaphore:
                runner = ScenarioRunner(
                    self.config.server_url,
                    self.config.default_behavior,
                    self.logger
                )
                
                if self.config.execution_timeout:
                    return await asyncio.wait_for(
                        runner.execute_scenario(scenario),
                        timeout=self.config.execution_timeout
                    )
                else:
                    return await runner.execute_scenario(scenario)
        
        # Create tasks for all scenarios
        tasks = [run_single_scenario(scenario) for scenario in scenarios]
        
        # Execute with progress tracking
        completed = 0
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                self.current_results.scenario_results.append(result)
                completed += 1
                
                self.logger.info(
                    f"Completed scenario {completed}/{len(scenarios)}: "
                    f"{result.scenario_name} ({'PASS' if result.success else 'FAIL'})"
                )
                
            except Exception as e:
                completed += 1
                self.logger.error(f"Scenario failed with exception: {e}")
                # Add error scenario result
                error_result = ScenarioResult(
                    scenario_name="Unknown",
                    success=False,
                    total_steps=0,
                    passed_steps=0,
                    failed_steps=1,
                    execution_time=0.0,
                    start_time=time.time(),
                    end_time=time.time(),
                    step_results=[],
                    errors=[{'error': str(e)}],
                    metrics={},
                    agent_metrics={}
                )
                self.current_results.scenario_results.append(error_result)
    
    def _calculate_final_results(self) -> None:
        """Calculate final result counts."""
        
        for result in self.current_results.scenario_results:
            if result.success:
                self.current_results.passed_scenarios += 1
            else:
                self.current_results.failed_scenarios += 1
    
    def _generate_test_metrics(self) -> TestMetrics:
        """Generate comprehensive test metrics."""
        
        if not self.current_results.scenario_results:
            return TestMetrics()
        
        # Collect timing data
        execution_times = [r.execution_time for r in self.current_results.scenario_results]
        
        # Collect step data
        total_steps = sum(r.total_steps for r in self.current_results.scenario_results)
        passed_steps = sum(r.passed_steps for r in self.current_results.scenario_results)
        failed_steps = sum(r.failed_steps for r in self.current_results.scenario_results)
        
        # Collect agent metrics
        agent_data = {}
        for result in self.current_results.scenario_results:
            if result.agent_metrics:
                for key, value in result.agent_metrics.items():
                    if key not in agent_data:
                        agent_data[key] = []
                    agent_data[key].append(value)
        
        return TestMetrics(
            total_scenarios=self.current_results.total_scenarios,
            passed_scenarios=self.current_results.passed_scenarios,
            failed_scenarios=self.current_results.failed_scenarios,
            success_rate=self.current_results.success_rate,
            total_execution_time=self.current_results.total_execution_time,
            average_scenario_time=sum(execution_times) / len(execution_times) if execution_times else 0,
            min_scenario_time=min(execution_times) if execution_times else 0,
            max_scenario_time=max(execution_times) if execution_times else 0,
            total_steps=total_steps,
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            step_success_rate=passed_steps / total_steps if total_steps > 0 else 0,
            agent_metrics=agent_data
        )
    
    async def run_performance_benchmark(
        self,
        scenarios: List[TestScenario],
        iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run performance benchmarking on scenarios.
        
        Args:
            scenarios: Scenarios to benchmark
            iterations: Number of iterations (uses config default if None)
            
        Returns:
            Benchmark results with performance statistics
        """
        iterations = iterations or self.config.benchmark_iterations
        
        self.logger.info(f"Starting performance benchmark: {iterations} iterations")
        
        benchmark_results = {
            'iterations': iterations,
            'scenario_count': len(scenarios),
            'results': [],
            'summary': {}
        }
        
        for i in range(iterations):
            self.logger.info(f"Benchmark iteration {i+1}/{iterations}")
            
            iteration_start = time.time()
            results = await self.run_scenarios(scenarios, "sequential")
            iteration_time = time.time() - iteration_start
            
            benchmark_results['results'].append({
                'iteration': i + 1,
                'execution_time': iteration_time,
                'success_rate': results.success_rate,
                'scenarios_passed': results.passed_scenarios,
                'scenarios_failed': results.failed_scenarios,
                'metrics': results.metrics.__dict__ if results.metrics else {}
            })
        
        # Calculate summary statistics
        execution_times = [r['execution_time'] for r in benchmark_results['results']]
        success_rates = [r['success_rate'] for r in benchmark_results['results']]
        
        benchmark_results['summary'] = {
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'avg_success_rate': sum(success_rates) / len(success_rates),
            'min_success_rate': min(success_rates),
            'max_success_rate': max(success_rates),
            'total_benchmark_time': sum(execution_times)
        }
        
        self.logger.info(f"Performance benchmark completed: {benchmark_results['summary']}")
        
        return benchmark_results
    
    async def generate_reports(
        self,
        output_dir: Union[str, Path],
        results: Optional[TestResults] = None
    ) -> Dict[str, str]:
        """
        Generate comprehensive test reports.
        
        Args:
            output_dir: Directory to save reports
            results: Test results (uses current if None)
            
        Returns:
            Dictionary mapping report types to file paths
        """
        results = results or self.current_results
        if not results:
            raise ValueError("No test results available for reporting")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_files = {}
        
        # Generate HTML report if configured
        if self.config.generate_html_report:
            html_path = output_dir / "test_report.html"
            await self.reporter.generate_html_report(results, html_path)
            report_files['html'] = str(html_path)
            self.logger.info(f"Generated HTML report: {html_path}")
        
        # Generate JSON metrics if configured
        if self.config.save_metrics_json:
            json_path = output_dir / "test_metrics.json"
            await self.reporter.save_metrics_json(results, json_path)
            report_files['json'] = str(json_path)
            self.logger.info(f"Generated JSON metrics: {json_path}")
        
        # Generate detailed logs if configured
        if self.config.save_detailed_logs:
            log_path = output_dir / "detailed_logs.txt"
            await self.reporter.save_detailed_logs(results, log_path)
            report_files['logs'] = str(log_path)
            self.logger.info(f"Generated detailed logs: {log_path}")
        
        return report_files
    
    def get_current_results(self) -> Optional[TestResults]:
        """Get current test results."""
        return self.current_results
    
    def is_running(self) -> bool:
        """Check if test harness is currently running."""
        return self.running