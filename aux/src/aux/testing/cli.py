"""
AUX Test Harness Command Line Interface.

This module provides a comprehensive CLI for running AUX protocol tests,
managing test scenarios, and generating reports.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List
import typer
import yaml

from .test_harness import TestHarness, TestConfiguration
from .mock_agent import AgentBehavior
from .reporting import TestReporter
from ..logging_utils import init_session_logging, get_session_logger


app = typer.Typer(
    name="aux-test",
    help="AUX Protocol Test Harness CLI",
    no_args_is_help=True,
    rich_markup_mode="rich"
)


def init_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Initialize logging for CLI operations."""
    if log_file:
        init_session_logging(Path(log_file))
    else:
        init_session_logging()
    
    logger = get_session_logger()
    if verbose:
        logger.setLevel("DEBUG")
    
    return logger


@app.command()
def run(
    scenarios: List[str] = typer.Argument(
        ..., 
        help="Scenario files or directories to run"
    ),
    server_url: str = typer.Option(
        "ws://localhost:8765",
        "--server", "-s",
        help="AUX server WebSocket URL"
    ),
    output_dir: str = typer.Option(
        "./test_results",
        "--output", "-o",
        help="Output directory for test results"
    ),
    execution_mode: str = typer.Option(
        "sequential",
        "--mode", "-m",
        help="Execution mode: sequential or parallel"
    ),
    max_parallel: int = typer.Option(
        3,
        "--parallel", "-p",
        help="Maximum parallel agents (for parallel mode)"
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout", "-t",
        help="Global timeout for test execution (seconds)"
    ),
    tags: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        help="Only run scenarios with these tags"
    ),
    exclude_tags: Optional[List[str]] = typer.Option(
        None,
        "--exclude-tag",
        help="Exclude scenarios with these tags"
    ),
    stop_on_failure: bool = typer.Option(
        False,
        "--stop-on-failure",
        help="Stop execution on first failure"
    ),
    retry_failed: bool = typer.Option(
        False,
        "--retry-failed",
        help="Retry failed scenarios"
    ),
    html_report: bool = typer.Option(
        True,
        "--html/--no-html",
        help="Generate HTML report"
    ),
    json_metrics: bool = typer.Option(
        True,
        "--json/--no-json",
        help="Save JSON metrics"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
    log_file: Optional[str] = typer.Option(
        None,
        "--log-file",
        help="Custom log file path"
    ),
    config_file: Optional[str] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file path"
    )
):
    """
    Run AUX protocol test scenarios.
    
    Examples:
        aux-test run scenario1.yaml scenario2.yaml
        aux-test run scenarios/ --mode parallel --parallel 5
        aux-test run scenarios/ --tag smoke --exclude-tag slow
    """
    logger = init_logging(verbose, log_file)
    
    typer.echo(f"🚀 [bold blue]AUX Protocol Test Harness[/bold blue]")
    typer.echo(f"Server: {server_url}")
    typer.echo(f"Mode: {execution_mode}")
    typer.echo(f"Output: {output_dir}")
    
    # Load configuration if provided
    config = TestConfiguration(
        server_url=server_url,
        max_parallel_agents=max_parallel,
        execution_timeout=timeout,
        stop_on_first_failure=stop_on_failure,
        scenario_filter_tags=tags,
        exclude_tags=exclude_tags,
        retry_failed_scenarios=retry_failed,
        generate_html_report=html_report,
        save_metrics_json=json_metrics
    )
    
    if config_file:
        config = load_config_file(config_file, config)
    
    # Run tests
    async def run_tests():
        harness = TestHarness(config, logger)
        
        try:
            # Load scenarios
            typer.echo("📁 Loading test scenarios...")
            test_scenarios = await harness.load_scenarios(scenarios)
            
            if not test_scenarios:
                typer.echo("❌ No test scenarios found!", err=True)
                return False
            
            typer.echo(f"✅ Loaded {len(test_scenarios)} scenarios")
            
            # Execute tests
            typer.echo(f"🧪 Executing tests in {execution_mode} mode...")
            results = await harness.run_scenarios(test_scenarios, execution_mode)
            
            # Generate reports
            typer.echo("📊 Generating reports...")
            report_files = await harness.generate_reports(Path(output_dir), results)
            
            # Print summary
            reporter = TestReporter(logger)
            reporter.print_summary(results)
            
            # Show report file locations
            typer.echo("\n📈 [bold]Generated Reports:[/bold]")
            for report_type, file_path in report_files.items():
                typer.echo(f"  {report_type}: {file_path}")
            
            return results.success_rate >= 1.0
            
        except Exception as e:
            typer.echo(f"❌ Test execution failed: {e}", err=True)
            logger.error(f"Test execution failed: {e}")
            return False
    
    # Run async main
    success = asyncio.run(run_tests())
    
    if success:
        typer.echo("\n🎉 [bold green]All tests passed![/bold green]")
        sys.exit(0)
    else:
        typer.echo("\n💥 [bold red]Some tests failed![/bold red]")
        sys.exit(1)


@app.command()
def benchmark(
    scenarios: List[str] = typer.Argument(
        ..., 
        help="Scenario files or directories to benchmark"
    ),
    iterations: int = typer.Option(
        3,
        "--iterations", "-i",
        help="Number of benchmark iterations"
    ),
    server_url: str = typer.Option(
        "ws://localhost:8765",
        "--server", "-s",
        help="AUX server WebSocket URL"
    ),
    output_dir: str = typer.Option(
        "./benchmark_results",
        "--output", "-o",
        help="Output directory for benchmark results"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """
    Run performance benchmarks on test scenarios.
    
    Examples:
        aux-test benchmark performance_scenario.yaml --iterations 5
        aux-test benchmark scenarios/ --iterations 10
    """
    logger = init_logging(verbose)
    
    typer.echo(f"⚡ [bold blue]AUX Protocol Performance Benchmark[/bold blue]")
    typer.echo(f"Iterations: {iterations}")
    typer.echo(f"Server: {server_url}")
    
    async def run_benchmark():
        config = TestConfiguration(
            server_url=server_url,
            performance_benchmarking=True,
            benchmark_iterations=iterations
        )
        
        harness = TestHarness(config, logger)
        
        try:
            # Load scenarios
            typer.echo("📁 Loading benchmark scenarios...")
            test_scenarios = await harness.load_scenarios(scenarios)
            
            if not test_scenarios:
                typer.echo("❌ No scenarios found for benchmarking!", err=True)
                return False
            
            typer.echo(f"✅ Loaded {len(test_scenarios)} scenarios")
            
            # Run benchmark
            typer.echo(f"🏃 Running benchmark with {iterations} iterations...")
            benchmark_results = await harness.run_performance_benchmark(
                test_scenarios, iterations
            )
            
            # Save benchmark results
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            benchmark_file = output_path / "benchmark_results.json"
            with open(benchmark_file, 'w') as f:
                json.dump(benchmark_results, f, indent=2, default=str)
            
            # Print summary
            summary = benchmark_results['summary']
            typer.echo("\n📊 [bold]Benchmark Results:[/bold]")
            typer.echo(f"  Average Execution Time: {summary['avg_execution_time']:.2f}s")
            typer.echo(f"  Min Execution Time: {summary['min_execution_time']:.2f}s")
            typer.echo(f"  Max Execution Time: {summary['max_execution_time']:.2f}s")
            typer.echo(f"  Average Success Rate: {summary['avg_success_rate']:.1%}")
            typer.echo(f"  Total Benchmark Time: {summary['total_benchmark_time']:.2f}s")
            typer.echo(f"\n📈 Results saved to: {benchmark_file}")
            
            return True
            
        except Exception as e:
            typer.echo(f"❌ Benchmark failed: {e}", err=True)
            logger.error(f"Benchmark failed: {e}")
            return False
    
    success = asyncio.run(run_benchmark())
    sys.exit(0 if success else 1)


@app.command()
def validate(
    scenarios: List[str] = typer.Argument(
        ..., 
        help="Scenario files to validate"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose validation output"
    )
):
    """
    Validate test scenario files without executing them.
    
    Examples:
        aux-test validate scenario1.yaml scenario2.yaml
        aux-test validate scenarios/*.yaml
    """
    logger = init_logging(verbose)
    
    typer.echo("🔍 [bold blue]Validating AUX Test Scenarios[/bold blue]")
    
    from .scenario_runner import ScenarioRunner
    
    valid_count = 0
    invalid_count = 0
    
    for scenario_path in scenarios:
        path = Path(scenario_path)
        
        if path.is_file():
            scenario_files = [path]
        elif path.is_dir():
            scenario_files = list(path.glob("**/*.yaml")) + list(path.glob("**/*.json"))
        else:
            typer.echo(f"❌ Path not found: {scenario_path}", err=True)
            invalid_count += 1
            continue
        
        for file_path in scenario_files:
            try:
                runner = ScenarioRunner("ws://dummy", logger=logging.getLogger(__name__))
                scenario = runner.load_scenario_file(file_path)
                
                typer.echo(f"✅ {file_path.name}: [green]Valid[/green]")
                if verbose:
                    typer.echo(f"   Name: {scenario.name}")
                    typer.echo(f"   Steps: {len(scenario.steps)}")
                    typer.echo(f"   Tags: {scenario.tags or 'None'}")
                
                valid_count += 1
                
            except Exception as e:
                typer.echo(f"❌ {file_path.name}: [red]Invalid[/red] - {e}")
                invalid_count += 1
    
    typer.echo(f"\n📊 [bold]Validation Summary:[/bold]")
    typer.echo(f"  Valid scenarios: {valid_count}")
    typer.echo(f"  Invalid scenarios: {invalid_count}")
    
    if invalid_count > 0:
        typer.echo("\n💡 [yellow]Fix validation errors before running tests[/yellow]")
        sys.exit(1)
    else:
        typer.echo("\n🎉 [green]All scenarios are valid![/green]")
        sys.exit(0)


@app.command()
def list_scenarios(
    directories: Optional[List[str]] = typer.Argument(
        None,
        help="Directories to search for scenarios"
    ),
    tags: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        help="Filter scenarios by tags"
    ),
    format: str = typer.Option(
        "table",
        "--format", "-f",
        help="Output format: table, json, yaml"
    )
):
    """
    List available test scenarios.
    
    Examples:
        aux-test list-scenarios
        aux-test list-scenarios scenarios/ --tag smoke
        aux-test list-scenarios --format json
    """
    logger = init_logging()
    
    async def list_scenarios_async():
        from .scenario_runner import ScenarioRunner
        
        # Use default directory if none provided
        search_dirs = directories or ["./scenarios"]
        
        all_scenarios = []
        
        for directory in search_dirs:
            dir_path = Path(directory)
            if not dir_path.exists():
                typer.echo(f"❌ Directory not found: {directory}", err=True)
                continue
            
            try:
                runner = ScenarioRunner("ws://dummy", logger=logging.getLogger(__name__))
                # Load scenarios from directory manually
                scenario_files = list(dir_path.glob("**/*.yaml")) + list(dir_path.glob("**/*.json"))
                for scenario_file in scenario_files:
                    scenario = runner.load_scenario_file(scenario_file)
                    all_scenarios.append(scenario)
            except Exception as e:
                typer.echo(f"❌ Error loading scenarios from {directory}: {e}", err=True)
        
        # Filter by tags if specified
        if tags:
            filtered_scenarios = []
            for scenario in all_scenarios:
                scenario_tags = scenario.tags or []
                if any(tag in scenario_tags for tag in tags):
                    filtered_scenarios.append(scenario)
            all_scenarios = filtered_scenarios
        
        # Output in requested format
        if format == "json":
            scenario_data = [
                {
                    "name": s.name,
                    "description": s.description,
                    "steps": len(s.steps),
                    "tags": s.tags or [],
                    "timeout": s.timeout
                }
                for s in all_scenarios
            ]
            typer.echo(json.dumps(scenario_data, indent=2))
            
        elif format == "yaml":
            scenario_data = [
                {
                    "name": s.name,
                    "description": s.description,
                    "steps": len(s.steps),
                    "tags": s.tags or [],
                    "timeout": s.timeout
                }
                for s in all_scenarios
            ]
            typer.echo(yaml.dump(scenario_data, default_flow_style=False))
            
        else:  # table format
            if not all_scenarios:
                typer.echo("No scenarios found.")
                return
            
            typer.echo(f"\n📋 [bold]Found {len(all_scenarios)} scenarios:[/bold]\n")
            
            # Print table header
            typer.echo(f"{'Name':<30} {'Steps':<6} {'Timeout':<8} {'Tags'}")
            typer.echo("-" * 70)
            
            for scenario in all_scenarios:
                tags_str = ", ".join(scenario.tags or [])
                timeout_str = f"{scenario.timeout}s" if scenario.timeout else "None"
                
                typer.echo(
                    f"{scenario.name[:29]:<30} "
                    f"{len(scenario.steps):<6} "
                    f"{timeout_str:<8} "
                    f"{tags_str}"
                )
    
    asyncio.run(list_scenarios_async())


@app.command()
def create_scenario(
    name: str = typer.Argument(..., help="Scenario name"),
    output_file: str = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (defaults to name-based filename)"
    ),
    template: str = typer.Option(
        "basic",
        "--template", "-t",
        help="Scenario template: basic, form, workflow, performance"
    )
):
    """
    Create a new test scenario from template.
    
    Examples:
        aux-test create-scenario "My Test" --template basic
        aux-test create-scenario "Form Test" --template form -o my_form_test.yaml
    """
    # Generate output filename if not provided
    if not output_file:
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        output_file = f"{safe_name}.yaml"
    
    output_path = Path(output_file)
    
    # Template scenarios
    templates = {
        "basic": {
            "name": name,
            "description": f"Basic test scenario: {name}",
            "tags": ["basic"],
            "timeout": 60,
            "steps": [
                {
                    "name": "Navigate to test page",
                    "command": {
                        "method": "navigate",
                        "url": "https://example.com",
                        "wait_until": "load",
                        "timeout": 10000
                    },
                    "expected_result": {"success": True},
                    "assertions": [
                        {"type": "equals", "field": "success", "expected": True}
                    ]
                }
            ]
        },
        "form": {
            "name": name,
            "description": f"Form interaction test: {name}",
            "tags": ["form", "interaction"],
            "timeout": 120,
            "steps": [
                {
                    "name": "Navigate to form",
                    "command": {
                        "method": "navigate",
                        "url": "https://httpbin.org/forms/post",
                        "wait_until": "domcontentloaded",
                        "timeout": 15000
                    }
                },
                {
                    "name": "Fill form field",
                    "command": {
                        "method": "fill",
                        "selector": "input[name='custname']",
                        "text": "Test User",
                        "timeout": 10000
                    }
                },
                {
                    "name": "Submit form",
                    "command": {
                        "method": "click",
                        "selector": "input[type='submit']",
                        "timeout": 10000
                    }
                }
            ]
        }
    }
    
    if template not in templates:
        typer.echo(f"❌ Unknown template: {template}", err=True)
        typer.echo(f"Available templates: {', '.join(templates.keys())}")
        sys.exit(1)
    
    try:
        with open(output_path, 'w') as f:
            yaml.dump(templates[template], f, default_flow_style=False, indent=2)
        
        typer.echo(f"✅ Created scenario: {output_path}")
        typer.echo(f"📝 Edit the file to customize your test scenario")
        
    except Exception as e:
        typer.echo(f"❌ Failed to create scenario: {e}", err=True)
        sys.exit(1)


def load_config_file(config_path: str, base_config: TestConfiguration) -> TestConfiguration:
    """Load configuration from file and merge with base config."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        typer.echo(f"❌ Config file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        with open(config_file) as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Update base config with file values
        for key, value in config_data.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)
        
        typer.echo(f"✅ Loaded configuration from: {config_path}")
        return base_config
        
    except Exception as e:
        typer.echo(f"❌ Failed to load config file: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()