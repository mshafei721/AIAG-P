"""
AUX Mock Agent Implementation.

This module provides a sophisticated mock agent that simulates realistic AI agent
behavior for testing the AUX protocol. It includes human-like timing delays,
error recovery, and comprehensive validation capabilities.
"""

import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum

from ..client.sdk import AUXClient, AUXSession
from ..schema.commands import (
    AnyCommand, AnyResponse, ErrorResponse,
    NavigateCommand, ClickCommand, FillCommand, ExtractCommand, WaitCommand
)
# Using standard logging


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    VALIDATING = "validating"
    ERROR_RECOVERY = "error_recovery"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentBehavior:
    """Configuration for agent behavior simulation."""
    
    # Timing behavior
    thinking_delay_range: tuple[float, float] = (0.5, 2.0)  # seconds
    typing_speed_range: tuple[int, int] = (50, 120)  # characters per minute
    action_delay_range: tuple[float, float] = (0.2, 0.8)  # seconds between actions
    
    # Error handling
    retry_attempts: int = 3
    retry_delay_range: tuple[float, float] = (1.0, 3.0)  # seconds
    error_recovery_enabled: bool = True
    
    # Validation behavior  
    validate_responses: bool = True
    strict_validation: bool = False
    validation_timeout: float = 5.0  # seconds
    
    # Human-like variation
    add_natural_delays: bool = True
    variation_factor: float = 0.3  # 30% random variation in timing
    simulate_mistakes: bool = False
    mistake_probability: float = 0.05  # 5% chance of simulated mistakes


@dataclass
class ValidationRule:
    """Rule for validating agent actions and responses."""
    
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    error_message: str
    severity: str = "error"  # error, warning, info


class MockAgent:
    """
    Mock AI agent that simulates realistic behavior for testing AUX protocol.
    
    Features:
    - Realistic timing delays and human-like behavior
    - Error recovery and retry mechanisms
    - Comprehensive response validation
    - Detailed execution logging and metrics
    - Customizable behavior patterns
    """
    
    def __init__(
        self,
        agent_id: str,
        server_url: str,
        behavior: Optional[AgentBehavior] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the mock agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            server_url: AUX server WebSocket URL
            behavior: Behavior configuration (uses defaults if None)
            logger: Optional logger instance
        """
        self.agent_id = agent_id
        self.server_url = server_url
        self.behavior = behavior or AgentBehavior()
        self.logger = logger or logging.getLogger(__name__)
        
        # State management
        self.state = AgentState.IDLE
        self.current_scenario: Optional[str] = None
        self.execution_start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}
        
        # Client and session
        self.client: Optional[AUXClient] = None
        self.session: Optional[AUXSession] = None
        
        # Validation
        self.validation_rules: List[ValidationRule] = []
        self.validation_results: List[Dict[str, Any]] = []
        
        # Error tracking
        self.errors: List[Dict[str, Any]] = []
        self.retry_counts: Dict[str, int] = {}
        
        self.logger.info(f"MockAgent {agent_id} initialized with server {server_url}")
    
    async def connect(self) -> bool:
        """
        Connect to the AUX server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Agent {self.agent_id} connecting to server...")
            
            self.client = AUXClient(self.server_url)
            await self.client.connect()
            
            self.session = await self.client.create_session()
            
            self.logger.info(f"Agent {self.agent_id} connected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Agent {self.agent_id} connection failed: {e}")
            self.state = AgentState.FAILED
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the AUX server."""
        if self.client and self.client.connected:
            await self.client.disconnect()
            self.logger.info(f"Agent {self.agent_id} disconnected")
    
    def add_validation_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule for response checking."""
        self.validation_rules.append(rule)
        self.logger.debug(f"Added validation rule: {rule.name}")
    
    async def simulate_thinking(self, context: str = "") -> None:
        """
        Simulate agent thinking time with realistic delays.
        
        Args:
            context: Context for the thinking (for logging)
        """
        if not self.behavior.add_natural_delays:
            return
            
        self.state = AgentState.THINKING
        
        # Calculate thinking time with variation
        base_delay = random.uniform(*self.behavior.thinking_delay_range)
        variation = base_delay * self.behavior.variation_factor * random.uniform(-1, 1)
        think_time = max(0.1, base_delay + variation)
        
        self.logger.debug(f"Agent {self.agent_id} thinking for {think_time:.2f}s ({context})")
        await asyncio.sleep(think_time)
    
    async def simulate_typing(self, text: str) -> float:
        """
        Simulate realistic typing delays based on text length.
        
        Args:
            text: Text being typed
            
        Returns:
            Total typing time in seconds
        """
        if not self.behavior.add_natural_delays:
            return 0.0
            
        # Calculate typing speed (characters per minute to seconds per character)
        chars_per_minute = random.uniform(*self.behavior.typing_speed_range)
        chars_per_second = chars_per_minute / 60.0
        
        # Base typing time
        base_time = len(text) / chars_per_second
        
        # Add variation and pauses for longer text
        variation = base_time * self.behavior.variation_factor * random.uniform(-1, 1)
        pause_time = len(text) * 0.01 if len(text) > 20 else 0  # Thinking pauses
        
        total_time = max(0.1, base_time + variation + pause_time)
        
        self.logger.debug(f"Simulating typing '{text[:30]}...' for {total_time:.2f}s")
        await asyncio.sleep(total_time)
        
        return total_time
    
    async def execute_command(
        self,
        command: AnyCommand,
        context: Optional[str] = None,
        expected_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command with realistic behavior simulation.
        
        Args:
            command: Command to execute
            context: Context description for logging
            expected_result: Expected result for validation
            
        Returns:
            Command execution result with metadata
        """
        self.state = AgentState.EXECUTING
        start_time = time.time()
        
        context_str = f" ({context})" if context else ""
        self.logger.info(f"Executing {command.method} command{context_str}")
        
        # Simulate pre-action thinking
        await self.simulate_thinking(f"before {command.method}")
        
        # Add typing simulation for fill commands
        if isinstance(command, FillCommand):
            typing_time = await self.simulate_typing(command.text)
            self.metrics[f"typing_time_{command.id}"] = typing_time
        
        # Add natural delay before action
        if self.behavior.add_natural_delays:
            delay = random.uniform(*self.behavior.action_delay_range)
            await asyncio.sleep(delay)
        
        try:
            # Execute the command
            result = await self.session.send_command(command)
            execution_time = time.time() - start_time
            
            # Create execution result
            execution_result = {
                "command_id": command.id,
                "command_method": command.method,
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "context": context,
                "timestamp": time.time()
            }
            
            # Validate response if enabled
            if self.behavior.validate_responses:
                await self.validate_response(execution_result, expected_result)
            
            self.logger.info(f"Command {command.method} completed in {execution_time:.2f}s")
            return execution_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_result = {
                "command_id": command.id,
                "command_method": command.method,
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "context": context,
                "timestamp": time.time()
            }
            
            self.errors.append(error_result)
            self.logger.error(f"Command {command.method} failed: {e}")
            
            # Attempt error recovery if enabled
            if self.behavior.error_recovery_enabled:
                recovery_result = await self.attempt_error_recovery(command, str(e))
                if recovery_result["success"]:
                    return recovery_result
            
            return error_result
    
    async def attempt_error_recovery(
        self,
        failed_command: AnyCommand,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Attempt to recover from command execution errors.
        
        Args:
            failed_command: Command that failed
            error_message: Error message from failure
            
        Returns:
            Recovery attempt result
        """
        self.state = AgentState.ERROR_RECOVERY
        
        command_key = f"{failed_command.method}_{failed_command.id}"
        retry_count = self.retry_counts.get(command_key, 0)
        
        if retry_count >= self.behavior.retry_attempts:
            self.logger.warning(f"Max retry attempts reached for {failed_command.method}")
            return {
                "success": False,
                "error": f"Max retries exceeded: {error_message}",
                "retry_count": retry_count
            }
        
        self.retry_counts[command_key] = retry_count + 1
        
        # Wait before retry with exponential backoff
        base_delay = random.uniform(*self.behavior.retry_delay_range)
        retry_delay = base_delay * (2 ** retry_count)
        
        self.logger.info(f"Attempting recovery for {failed_command.method} (retry {retry_count + 1})")
        await asyncio.sleep(retry_delay)
        
        # Simulate thinking about the error
        await self.simulate_thinking("error recovery")
        
        try:
            # Retry the command
            result = await self.session.send_command(failed_command)
            
            self.logger.info(f"Recovery successful for {failed_command.method}")
            return {
                "success": True,
                "result": result,
                "retry_count": retry_count + 1,
                "recovered": True
            }
            
        except Exception as e:
            self.logger.warning(f"Recovery failed for {failed_command.method}: {e}")
            return await self.attempt_error_recovery(failed_command, str(e))
    
    async def validate_response(
        self,
        execution_result: Dict[str, Any],
        expected_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate command execution response.
        
        Args:
            execution_result: Result from command execution
            expected_result: Expected result for comparison
            
        Returns:
            Validation results
        """
        self.state = AgentState.VALIDATING
        validation_start = time.time()
        
        validation_result = {
            "command_id": execution_result["command_id"],
            "validations_passed": 0,
            "validations_failed": 0,
            "warnings": [],
            "errors": [],
            "validation_time": 0.0
        }
        
        # Run custom validation rules
        for rule in self.validation_rules:
            try:
                if rule.condition(execution_result):
                    validation_result["validations_passed"] += 1
                    self.logger.debug(f"Validation passed: {rule.name}")
                else:
                    validation_result["validations_failed"] += 1
                    
                    if rule.severity == "error":
                        validation_result["errors"].append({
                            "rule": rule.name,
                            "message": rule.error_message
                        })
                        self.logger.error(f"Validation failed: {rule.name} - {rule.error_message}")
                    else:
                        validation_result["warnings"].append({
                            "rule": rule.name,
                            "message": rule.error_message
                        })
                        self.logger.warning(f"Validation warning: {rule.name} - {rule.error_message}")
                        
            except Exception as e:
                validation_result["errors"].append({
                    "rule": rule.name,
                    "message": f"Validation rule error: {e}"
                })
                self.logger.error(f"Validation rule {rule.name} threw exception: {e}")
        
        # Compare with expected result if provided
        if expected_result:
            await self._validate_expected_result(execution_result, expected_result, validation_result)
        
        validation_result["validation_time"] = time.time() - validation_start
        self.validation_results.append(validation_result)
        
        return validation_result
    
    async def _validate_expected_result(
        self,
        execution_result: Dict[str, Any],
        expected_result: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> None:
        """Validate execution result against expected result."""
        
        # Check success status
        expected_success = expected_result.get("success", True)
        actual_success = execution_result.get("success", False)
        
        if expected_success != actual_success:
            validation_result["errors"].append({
                "rule": "success_status",
                "message": f"Expected success={expected_success}, got {actual_success}"
            })
            validation_result["validations_failed"] += 1
        else:
            validation_result["validations_passed"] += 1
        
        # Check specific result fields if specified
        if "result_checks" in expected_result:
            for field, expected_value in expected_result["result_checks"].items():
                actual_value = execution_result.get("result", {}).get(field)
                
                if actual_value != expected_value:
                    validation_result["errors"].append({
                        "rule": f"result_field_{field}",
                        "message": f"Expected {field}={expected_value}, got {actual_value}"
                    })
                    validation_result["validations_failed"] += 1
                else:
                    validation_result["validations_passed"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics about agent performance.
        
        Returns:
            Dictionary containing performance metrics
        """
        total_commands = len([r for r in self.validation_results])
        successful_commands = len([r for r in self.validation_results if not r["errors"]])
        
        total_errors = len(self.errors)
        total_retries = sum(self.retry_counts.values())
        
        execution_times = [r.get("execution_time", 0) for r in self.validation_results]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        validation_times = [r.get("validation_time", 0) for r in self.validation_results]
        avg_validation_time = sum(validation_times) / len(validation_times) if validation_times else 0
        
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "total_commands": total_commands,
            "successful_commands": successful_commands,
            "failed_commands": total_commands - successful_commands,
            "success_rate": successful_commands / total_commands if total_commands > 0 else 0,
            "total_errors": total_errors,
            "total_retries": total_retries,
            "avg_execution_time": avg_execution_time,
            "avg_validation_time": avg_validation_time,
            "total_validations_passed": sum(r["validations_passed"] for r in self.validation_results),
            "total_validations_failed": sum(r["validations_failed"] for r in self.validation_results),
            "scenario": self.current_scenario,
            "uptime": time.time() - self.execution_start_time if self.execution_start_time else 0
        }
    
    async def execute_scenario_step(
        self,
        step: Dict[str, Any],
        step_number: int,
        total_steps: int
    ) -> Dict[str, Any]:
        """
        Execute a single scenario step with full behavior simulation.
        
        Args:
            step: Step definition from scenario
            step_number: Current step number (1-based)
            total_steps: Total number of steps
            
        Returns:
            Step execution result
        """
        step_name = step.get("name", f"Step {step_number}")
        self.logger.info(f"Executing step {step_number}/{total_steps}: {step_name}")
        
        # Simulate thinking about the step
        await self.simulate_thinking(f"step {step_number}: {step_name}")
        
        # Build command from step definition
        command_data = step["command"]
        command_method = command_data["method"]
        
        # Create command with unique ID
        command_data["id"] = str(uuid.uuid4())
        command_data["session_id"] = self.session.session_id
        
        # Create appropriate command object
        from ..schema.commands import COMMAND_MODELS
        command_class = COMMAND_MODELS[command_method]
        command = command_class(**command_data)
        
        # Execute command with context
        result = await self.execute_command(
            command,
            context=step_name,
            expected_result=step.get("expected_result")
        )
        
        # Add step-specific metadata
        result.update({
            "step_number": step_number,
            "step_name": step_name,
            "total_steps": total_steps
        })
        
        return result
    
    def reset_state(self) -> None:
        """Reset agent state for new scenario execution."""
        self.state = AgentState.IDLE
        self.current_scenario = None
        self.execution_start_time = None
        self.metrics.clear()
        self.validation_results.clear()
        self.errors.clear()
        self.retry_counts.clear()
        
        self.logger.info(f"Agent {self.agent_id} state reset")


# Common validation rules for testing
def create_success_validation() -> ValidationRule:
    """Validation rule to check command success."""
    return ValidationRule(
        name="command_success",
        condition=lambda result: result.get("success", False),
        error_message="Command did not complete successfully"
    )


def create_timing_validation(max_time: float) -> ValidationRule:
    """Validation rule to check execution time."""
    return ValidationRule(
        name="execution_timing",
        condition=lambda result: result.get("execution_time", float('inf')) <= max_time,
        error_message=f"Command took longer than {max_time} seconds",
        severity="warning"
    )


def create_response_field_validation(field: str, expected_value: Any) -> ValidationRule:
    """Validation rule to check specific response field."""
    return ValidationRule(
        name=f"response_field_{field}",
        condition=lambda result: result.get("result", {}).get(field) == expected_value,
        error_message=f"Response field {field} did not match expected value {expected_value}"
    )