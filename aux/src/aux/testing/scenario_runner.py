"""
AUX Test Scenario Runner.

This module provides the ScenarioRunner class for executing test scenarios
defined in YAML/JSON format. It handles scenario loading, execution,
and result collection with comprehensive error handling.
"""

import asyncio
import json
import time
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

from .mock_agent import MockAgent, AgentState, AgentBehavior
# Using standard logging


@dataclass
class TestStep:
    """Represents a single test step in a scenario."""
    
    name: str
    command: Dict[str, Any]
    expected_result: Optional[Dict[str, Any]] = None
    assertions: Optional[List[Dict[str, Any]]] = None
    behavior: Optional[Dict[str, Any]] = None
    retry_on_failure: bool = False
    timeout: Optional[float] = None


@dataclass
class TestScenario:
    """Represents a complete test scenario."""
    
    name: str
    description: str
    steps: List[TestStep]
    setup: Optional[Dict[str, Any]] = None
    teardown: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    timeout: Optional[float] = None
    parallel_execution: bool = False


@dataclass
class ScenarioResult:
    """Results from scenario execution."""
    
    scenario_name: str
    success: bool
    total_steps: int
    passed_steps: int
    failed_steps: int
    execution_time: float
    start_time: float
    end_time: float
    step_results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    agent_metrics: Dict[str, Any]


class ScenarioRunner:
    """
    Executes test scenarios with mock agents.
    
    Features:
    - YAML/JSON scenario loading
    - Step-by-step execution with validation
    - Comprehensive result collection
    - Error handling and recovery
    - Performance metrics tracking
    """
    
    def __init__(
        self,
        server_url: str,
        default_behavior: Optional[AgentBehavior] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the scenario runner.
        
        Args:
            server_url: AUX server WebSocket URL
            default_behavior: Default agent behavior configuration
            logger: Optional logger instance
        """
        self.server_url = server_url
        self.default_behavior = default_behavior or AgentBehavior()
        self.logger = logger or logging.getLogger(__name__)
        
        # Execution state
        self.current_scenario: Optional[TestScenario] = None
        self.current_agent: Optional[MockAgent] = None
        self.execution_results: List[ScenarioResult] = []
        
        self.logger.info(f"ScenarioRunner initialized with server {server_url}")
    
    def load_scenario_file(self, file_path: Union[str, Path]) -> TestScenario:
        """
        Load a test scenario from YAML or JSON file.
        
        Args:
            file_path: Path to scenario file
            
        Returns:
            Loaded test scenario
            
        Raises:
            FileNotFoundError: If scenario file doesn't exist
            ValueError: If scenario format is invalid
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        
        self.logger.info(f"Loading scenario from {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            return self._parse_scenario_data(data)
            
        except Exception as e:
            self.logger.error(f"Failed to load scenario {file_path}: {e}")
            raise ValueError(f"Invalid scenario file: {e}") from e
    
    def _parse_scenario_data(self, data: Dict[str, Any]) -> TestScenario:
        """Parse scenario data into TestScenario object."""
        
        # Validate required fields
        required_fields = ['name', 'description', 'steps']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Parse steps
        steps = []
        for i, step_data in enumerate(data['steps']):
            try:
                step = TestStep(
                    name=step_data.get('name', f'Step {i+1}'),
                    command=step_data['command'],
                    expected_result=step_data.get('expected_result'),
                    assertions=step_data.get('assertions'),
                    behavior=step_data.get('behavior'),
                    retry_on_failure=step_data.get('retry_on_failure', False),
                    timeout=step_data.get('timeout')
                )
                steps.append(step)
            except KeyError as e:
                raise ValueError(f"Invalid step {i+1}: missing {e}")
        
        return TestScenario(
            name=data['name'],
            description=data['description'],
            steps=steps,
            setup=data.get('setup'),
            teardown=data.get('teardown'),
            config=data.get('config'),
            tags=data.get('tags'),
            timeout=data.get('timeout'),
            parallel_execution=data.get('parallel_execution', False)
        )
    
    async def execute_scenario(
        self,
        scenario: TestScenario,
        agent_id: Optional[str] = None,
        custom_behavior: Optional[AgentBehavior] = None
    ) -> ScenarioResult:
        """
        Execute a test scenario with a mock agent.
        
        Args:
            scenario: Test scenario to execute
            agent_id: Optional custom agent ID
            custom_behavior: Optional custom agent behavior
            
        Returns:
            Scenario execution results
        """
        start_time = time.time()
        self.current_scenario = scenario
        
        # Create agent with appropriate behavior
        behavior = custom_behavior or self.default_behavior
        if scenario.config and 'behavior' in scenario.config:
            behavior = self._merge_behavior(behavior, scenario.config['behavior'])
        
        agent_id = agent_id or f"test_agent_{int(start_time)}"
        self.current_agent = MockAgent(agent_id, self.server_url, behavior, self.logger)
        
        self.logger.info(f"Starting scenario execution: {scenario.name}")
        
        # Initialize result tracking
        step_results = []
        errors = []
        passed_steps = 0
        failed_steps = 0
        
        try:
            # Connect agent
            if not await self.current_agent.connect():
                raise Exception("Failed to connect agent to server")
            
            # Run setup if specified
            if scenario.setup:
                await self._run_setup(scenario.setup)
            
            # Execute steps
            if scenario.parallel_execution:
                step_results = await self._execute_steps_parallel(scenario.steps)
            else:
                step_results = await self._execute_steps_sequential(scenario.steps)
            
            # Count results
            for result in step_results:
                if result.get('success', False):
                    passed_steps += 1
                else:
                    failed_steps += 1
                    errors.append({
                        'step': result.get('step_name', 'Unknown'),
                        'error': result.get('error', 'Unknown error')
                    })
            
            # Run teardown if specified
            if scenario.teardown:
                await self._run_teardown(scenario.teardown)
                
        except Exception as e:
            self.logger.error(f"Scenario execution failed: {e}")
            errors.append({
                'step': 'scenario_execution',
                'error': str(e)
            })
            failed_steps += 1
            
        finally:
            # Disconnect agent
            if self.current_agent:
                await self.current_agent.disconnect()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Create result
        result = ScenarioResult(
            scenario_name=scenario.name,
            success=failed_steps == 0,
            total_steps=len(scenario.steps),
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            execution_time=execution_time,
            start_time=start_time,
            end_time=end_time,
            step_results=step_results,
            errors=errors,
            metrics=self._calculate_metrics(step_results),
            agent_metrics=self.current_agent.get_metrics() if self.current_agent else {}
        )
        
        self.execution_results.append(result)
        
        self.logger.info(
            f"Scenario '{scenario.name}' completed in {execution_time:.2f}s: "
            f"{passed_steps} passed, {failed_steps} failed"
        )
        
        return result
    
    async def _execute_steps_sequential(self, steps: List[TestStep]) -> List[Dict[str, Any]]:
        """Execute scenario steps sequentially."""
        results = []
        
        for i, step in enumerate(steps):
            self.logger.debug(f"Executing step {i+1}/{len(steps)}: {step.name}")
            
            try:
                # Apply step-specific timeout if specified
                if step.timeout:
                    result = await asyncio.wait_for(
                        self.current_agent.execute_scenario_step(
                            step.__dict__, i + 1, len(steps)
                        ),
                        timeout=step.timeout
                    )
                else:
                    result = await self.current_agent.execute_scenario_step(
                        step.__dict__, i + 1, len(steps)
                    )
                
                # Run assertions if specified
                if step.assertions:
                    assertion_results = await self._run_assertions(step.assertions, result)
                    result['assertion_results'] = assertion_results
                
                results.append(result)
                
                # Stop on failure unless retry is enabled
                if not result.get('success', False) and not step.retry_on_failure:
                    self.logger.warning(f"Step {step.name} failed, stopping execution")
                    break
                    
            except asyncio.TimeoutError:
                error_result = {
                    'step_name': step.name,
                    'success': False,
                    'error': f'Step timed out after {step.timeout} seconds',
                    'timestamp': time.time()
                }
                results.append(error_result)
                self.logger.error(f"Step {step.name} timed out")
                break
                
            except Exception as e:
                error_result = {
                    'step_name': step.name,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
                results.append(error_result)
                self.logger.error(f"Step {step.name} failed with exception: {e}")
                break
        
        return results
    
    async def _execute_steps_parallel(self, steps: List[TestStep]) -> List[Dict[str, Any]]:
        """Execute scenario steps in parallel (where possible)."""
        # For now, implement as sequential since most browser operations are sequential
        # This could be extended to support parallel execution for independent operations
        self.logger.warning("Parallel execution not fully implemented, falling back to sequential")
        return await self._execute_steps_sequential(steps)
    
    async def _run_setup(self, setup_config: Dict[str, Any]) -> None:
        """Run scenario setup operations."""
        self.logger.debug("Running scenario setup")
        
        # Add setup operations like clearing browser cache, setting initial state, etc.
        if 'clear_cache' in setup_config and setup_config['clear_cache']:
            self.logger.debug("Setup: Clearing browser cache")
        
        if 'initial_url' in setup_config:
            initial_url = setup_config['initial_url']
            self.logger.debug(f"Setup: Navigating to initial URL: {initial_url}")
            # Could navigate to initial URL here
        
        if 'wait_time' in setup_config:
            wait_time = setup_config['wait_time']
            self.logger.debug(f"Setup: Waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
    
    async def _run_teardown(self, teardown_config: Dict[str, Any]) -> None:
        """Run scenario teardown operations."""
        self.logger.debug("Running scenario teardown")
        
        if 'cleanup_downloads' in teardown_config and teardown_config['cleanup_downloads']:
            self.logger.debug("Teardown: Cleaning up downloads")
        
        if 'reset_browser' in teardown_config and teardown_config['reset_browser']:
            self.logger.debug("Teardown: Resetting browser state")
        
        if 'wait_time' in teardown_config:
            wait_time = teardown_config['wait_time']
            self.logger.debug(f"Teardown: Waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
    
    async def _run_assertions(
        self,
        assertions: List[Dict[str, Any]],
        step_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run assertions on step results."""
        assertion_results = []
        
        for assertion in assertions:
            assertion_type = assertion.get('type', 'equals')
            field = assertion.get('field', '')
            expected = assertion.get('expected')
            
            result = {
                'assertion_type': assertion_type,
                'field': field,
                'expected': expected,
                'success': False,
                'message': ''
            }
            
            try:
                # Get actual value from step result
                actual = self._get_nested_value(step_result, field)
                result['actual'] = actual
                
                # Run assertion based on type
                if assertion_type == 'equals':
                    result['success'] = actual == expected
                    result['message'] = f"Expected {field} to equal {expected}, got {actual}"
                
                elif assertion_type == 'contains':
                    result['success'] = expected in str(actual)
                    result['message'] = f"Expected {field} to contain {expected}, got {actual}"
                
                elif assertion_type == 'not_empty':
                    result['success'] = actual is not None and str(actual).strip() != ''
                    result['message'] = f"Expected {field} to not be empty, got {actual}"
                
                elif assertion_type == 'greater_than':
                    result['success'] = float(actual) > float(expected)
                    result['message'] = f"Expected {field} > {expected}, got {actual}"
                
                elif assertion_type == 'less_than':
                    result['success'] = float(actual) < float(expected)
                    result['message'] = f"Expected {field} < {expected}, got {actual}"
                
                else:
                    result['message'] = f"Unknown assertion type: {assertion_type}"
                
            except Exception as e:
                result['message'] = f"Assertion error: {e}"
            
            assertion_results.append(result)
            
            if result['success']:
                self.logger.debug(f"Assertion passed: {result['message']}")
            else:
                self.logger.warning(f"Assertion failed: {result['message']}")
        
        return assertion_results
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        if not field_path:
            return data
        
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _merge_behavior(
        self,
        base_behavior: AgentBehavior,
        behavior_config: Dict[str, Any]
    ) -> AgentBehavior:
        """Merge behavior configuration with base behavior."""
        
        # Create a copy of base behavior
        merged = AgentBehavior(
            thinking_delay_range=base_behavior.thinking_delay_range,
            typing_speed_range=base_behavior.typing_speed_range,
            action_delay_range=base_behavior.action_delay_range,
            retry_attempts=base_behavior.retry_attempts,
            retry_delay_range=base_behavior.retry_delay_range,
            error_recovery_enabled=base_behavior.error_recovery_enabled,
            validate_responses=base_behavior.validate_responses,
            strict_validation=base_behavior.strict_validation,
            validation_timeout=base_behavior.validation_timeout,
            add_natural_delays=base_behavior.add_natural_delays,
            variation_factor=base_behavior.variation_factor,
            simulate_mistakes=base_behavior.simulate_mistakes,
            mistake_probability=base_behavior.mistake_probability
        )
        
        # Apply overrides from config
        for key, value in behavior_config.items():
            if hasattr(merged, key):
                setattr(merged, key, value)
        
        return merged
    
    def _calculate_metrics(self, step_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics from step results."""
        
        if not step_results:
            return {}
        
        execution_times = [r.get('execution_time', 0) for r in step_results if 'execution_time' in r]
        
        return {
            'total_execution_time': sum(execution_times),
            'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'successful_steps': len([r for r in step_results if r.get('success', False)]),
            'failed_steps': len([r for r in step_results if not r.get('success', False)]),
            'commands_executed': len(step_results),
            'assertions_run': sum(
                len(r.get('assertion_results', [])) for r in step_results
            ),
            'assertions_passed': sum(
                len([a for a in r.get('assertion_results', []) if a.get('success', False)])
                for r in step_results
            )
        }
    
    def get_all_results(self) -> List[ScenarioResult]:
        """Get all scenario execution results."""
        return self.execution_results.copy()
    
    def clear_results(self) -> None:
        """Clear all execution results."""
        self.execution_results.clear()
        self.logger.info("Execution results cleared")