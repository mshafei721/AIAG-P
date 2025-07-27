"""
Comprehensive unit tests for AUX Protocol batch operations.

Tests cover batch command processing, validation, execution,
error handling, and performance characteristics.
"""

import asyncio
import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from aux.batch import (
    BatchProcessor,
    BatchRequest,
    BatchResponse,
    BatchCommand,
    BatchConfig,
    BatchExecutor,
    BatchValidator,
    BatchError,
    CommandDependency,
    DependencyResolver,
    batch_command_decorator,
    validate_batch_request,
    execute_batch_commands,
)


class TestBatchConfig:
    """Test BatchConfig validation and functionality."""
    
    def test_valid_batch_config(self):
        """Test creation of valid batch configuration."""
        config = BatchConfig(
            max_batch_size=50,
            max_parallel_commands=10,
            timeout_per_command=30,
            total_timeout=300,
            fail_fast=True,
            enable_dependencies=True
        )
        assert config.max_batch_size == 50
        assert config.max_parallel_commands == 10
        assert config.timeout_per_command == 30
        assert config.total_timeout == 300
        assert config.fail_fast is True
        assert config.enable_dependencies is True
        
    def test_batch_config_defaults(self):
        """Test batch configuration with default values."""
        config = BatchConfig()
        assert config.max_batch_size == 100
        assert config.max_parallel_commands == 5
        assert config.timeout_per_command == 30
        assert config.total_timeout == 600
        assert config.fail_fast is False
        assert config.enable_dependencies is False
        
    def test_batch_config_invalid_values(self):
        """Test batch configuration with invalid values."""
        with pytest.raises(ValueError):
            BatchConfig(max_batch_size=0)
            
        with pytest.raises(ValueError):
            BatchConfig(max_parallel_commands=0)
            
        with pytest.raises(ValueError):
            BatchConfig(timeout_per_command=-1)
            
        with pytest.raises(ValueError):
            BatchConfig(total_timeout=0)


class TestBatchCommand:
    """Test BatchCommand validation and functionality."""
    
    def test_valid_batch_command(self):
        """Test creation of valid batch command."""
        command = BatchCommand(
            command_id="cmd-1",
            method="navigate",
            url="https://example.com",
            timeout=30,
            retry_count=3,
            depends_on=["cmd-0"]
        )
        assert command.command_id == "cmd-1"
        assert command.method == "navigate"
        assert command.url == "https://example.com"
        assert command.timeout == 30
        assert command.retry_count == 3
        assert "cmd-0" in command.depends_on
        
    def test_batch_command_defaults(self):
        """Test batch command with default values."""
        command = BatchCommand(
            command_id="cmd-1",
            method="click",
            selector="#button"
        )
        assert command.timeout == 30
        assert command.retry_count == 0
        assert command.depends_on == []
        assert command.continue_on_error is False
        
    def test_batch_command_validation(self):
        """Test batch command validation."""
        # Missing required fields
        with pytest.raises(ValueError):
            BatchCommand(
                command_id="",  # Empty command ID
                method="click"
            )
            
        # Invalid method
        with pytest.raises(ValueError):
            BatchCommand(
                command_id="cmd-1",
                method="invalid_method"
            )
            
        # Invalid timeout
        with pytest.raises(ValueError):
            BatchCommand(
                command_id="cmd-1",
                method="wait",
                timeout=-1
            )


class TestCommandDependency:
    """Test CommandDependency functionality."""
    
    def test_command_dependency_creation(self):
        """Test creation of command dependency."""
        dependency = CommandDependency(
            command_id="cmd-2",
            depends_on="cmd-1",
            condition="success",
            wait_for_completion=True
        )
        assert dependency.command_id == "cmd-2"
        assert dependency.depends_on == "cmd-1"
        assert dependency.condition == "success"
        assert dependency.wait_for_completion is True
        
    def test_command_dependency_validation(self):
        """Test command dependency validation."""
        # Circular dependency
        with pytest.raises(ValueError):
            CommandDependency(
                command_id="cmd-1",
                depends_on="cmd-1"  # Self-dependency
            )
            
        # Invalid condition
        with pytest.raises(ValueError):
            CommandDependency(
                command_id="cmd-2",
                depends_on="cmd-1",
                condition="invalid_condition"
            )


class TestDependencyResolver:
    """Test DependencyResolver functionality."""
    
    @pytest.fixture
    def sample_commands(self):
        """Provide sample commands with dependencies."""
        return [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#login", depends_on=["cmd-1"]),
            BatchCommand(command_id="cmd-3", method="fill", selector="#username", value="test", depends_on=["cmd-2"]),
            BatchCommand(command_id="cmd-4", method="fill", selector="#password", value="pass", depends_on=["cmd-2"]),
            BatchCommand(command_id="cmd-5", method="click", selector="#submit", depends_on=["cmd-3", "cmd-4"])
        ]
        
    def test_dependency_resolver_creation(self):
        """Test creation of dependency resolver."""
        resolver = DependencyResolver()
        assert resolver is not None
        
    def test_dependency_resolution_order(self, sample_commands):
        """Test dependency resolution and execution order."""
        resolver = DependencyResolver()
        execution_order = resolver.resolve_dependencies(sample_commands)
        
        # cmd-1 should be first (no dependencies)
        assert execution_order[0].command_id == "cmd-1"
        
        # cmd-2 should come after cmd-1
        cmd_1_index = next(i for i, cmd in enumerate(execution_order) if cmd.command_id == "cmd-1")
        cmd_2_index = next(i for i, cmd in enumerate(execution_order) if cmd.command_id == "cmd-2")
        assert cmd_2_index > cmd_1_index
        
        # cmd-5 should be last (depends on cmd-3 and cmd-4)
        assert execution_order[-1].command_id == "cmd-5"
        
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com", depends_on=["cmd-3"]),
            BatchCommand(command_id="cmd-2", method="click", selector="#button", depends_on=["cmd-1"]),
            BatchCommand(command_id="cmd-3", method="wait", condition="visible", depends_on=["cmd-2"])
        ]
        
        resolver = DependencyResolver()
        with pytest.raises(ValueError, match="circular dependency"):
            resolver.resolve_dependencies(commands)
            
    def test_missing_dependency_detection(self):
        """Test missing dependency detection."""
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#button", depends_on=["cmd-missing"])
        ]
        
        resolver = DependencyResolver()
        with pytest.raises(ValueError, match="missing dependency"):
            resolver.resolve_dependencies(commands)
            
    def test_parallel_execution_groups(self, sample_commands):
        """Test parallel execution group identification."""
        resolver = DependencyResolver()
        execution_groups = resolver.get_parallel_groups(sample_commands)
        
        # cmd-3 and cmd-4 can run in parallel (both depend only on cmd-2)
        parallel_group = None
        for group in execution_groups:
            cmd_ids = [cmd.command_id for cmd in group]
            if "cmd-3" in cmd_ids and "cmd-4" in cmd_ids:
                parallel_group = group
                break
                
        assert parallel_group is not None
        assert len(parallel_group) == 2


class TestBatchValidator:
    """Test BatchValidator functionality."""
    
    def test_batch_validator_creation(self):
        """Test creation of batch validator."""
        validator = BatchValidator(BatchConfig())
        assert validator is not None
        
    def test_validate_batch_size(self):
        """Test batch size validation."""
        config = BatchConfig(max_batch_size=3)
        validator = BatchValidator(config)
        
        # Valid batch size
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#button")
        ]
        validator.validate_batch_size(commands)  # Should not raise
        
        # Invalid batch size
        large_commands = [
            BatchCommand(command_id=f"cmd-{i}", method="wait", condition="load")
            for i in range(5)
        ]
        with pytest.raises(ValueError, match="batch size exceeds maximum"):
            validator.validate_batch_size(large_commands)
            
    def test_validate_command_ids_unique(self):
        """Test command ID uniqueness validation."""
        validator = BatchValidator(BatchConfig())
        
        # Duplicate command IDs
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-1", method="click", selector="#button")  # Duplicate ID
        ]
        
        with pytest.raises(ValueError, match="duplicate command ID"):
            validator.validate_command_ids(commands)
            
    def test_validate_command_structure(self):
        """Test command structure validation."""
        validator = BatchValidator(BatchConfig())
        
        # Valid commands
        valid_commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#button")
        ]
        validator.validate_command_structure(valid_commands)  # Should not raise
        
        # Invalid command - missing required field
        invalid_commands = [
            BatchCommand(command_id="cmd-1", method="click")  # Missing selector
        ]
        
        with pytest.raises(ValueError, match="missing required field"):
            validator.validate_command_structure(invalid_commands)


class TestBatchExecutor:
    """Test BatchExecutor functionality."""
    
    @pytest.fixture
    def mock_browser_session(self):
        """Provide a mock browser session."""
        session = AsyncMock()
        session.execute_command = AsyncMock()
        return session
        
    @pytest.fixture
    def batch_executor(self, mock_browser_session):
        """Provide a batch executor with mock browser session."""
        config = BatchConfig(max_parallel_commands=3)
        return BatchExecutor(config, mock_browser_session)
        
    async def test_execute_single_command(self, batch_executor, mock_browser_session):
        """Test execution of single command."""
        command = BatchCommand(
            command_id="cmd-1",
            method="navigate",
            url="https://example.com"
        )
        
        # Mock successful execution
        mock_browser_session.execute_command.return_value = {
            "status": "success",
            "result": {"navigated": True}
        }
        
        result = await batch_executor.execute_command(command)
        
        assert result["status"] == "success"
        assert result["command_id"] == "cmd-1"
        mock_browser_session.execute_command.assert_called_once()
        
    async def test_execute_command_with_retry(self, batch_executor, mock_browser_session):
        """Test command execution with retry logic."""
        command = BatchCommand(
            command_id="cmd-1",
            method="click",
            selector="#button",
            retry_count=2
        )
        
        # Mock failure then success
        mock_browser_session.execute_command.side_effect = [
            {"status": "error", "error": {"error_code": "ELEMENT_NOT_FOUND"}},
            {"status": "success", "result": {"clicked": True}}
        ]
        
        result = await batch_executor.execute_command(command)
        
        assert result["status"] == "success"
        assert mock_browser_session.execute_command.call_count == 2
        
    async def test_execute_command_timeout(self, batch_executor, mock_browser_session):
        """Test command execution timeout."""
        command = BatchCommand(
            command_id="cmd-1",
            method="wait",
            condition="visible",
            selector="#element",
            timeout=0.1  # Very short timeout
        )
        
        # Mock slow execution
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.2)
            return {"status": "success"}
            
        mock_browser_session.execute_command.side_effect = slow_execute
        
        result = await batch_executor.execute_command(command)
        
        assert result["status"] == "error"
        assert "timeout" in result["error"]["error_code"].lower()
        
    async def test_execute_batch_sequential(self, batch_executor, mock_browser_session):
        """Test sequential batch execution."""
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#button", depends_on=["cmd-1"])
        ]
        
        # Mock successful executions
        mock_browser_session.execute_command.side_effect = [
            {"status": "success", "result": {"navigated": True}},
            {"status": "success", "result": {"clicked": True}}
        ]
        
        results = await batch_executor.execute_batch(commands)
        
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
        assert mock_browser_session.execute_command.call_count == 2
        
    async def test_execute_batch_parallel(self, batch_executor, mock_browser_session):
        """Test parallel batch execution."""
        commands = [
            BatchCommand(command_id="cmd-1", method="fill", selector="#input1", value="value1"),
            BatchCommand(command_id="cmd-2", method="fill", selector="#input2", value="value2"),
            BatchCommand(command_id="cmd-3", method="fill", selector="#input3", value="value3")
        ]
        
        # Mock successful executions with delays to test parallelism
        async def delayed_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"status": "success", "result": {"filled": True}}
            
        mock_browser_session.execute_command.side_effect = delayed_execute
        
        start_time = asyncio.get_event_loop().time()
        results = await batch_executor.execute_batch(commands)
        execution_time = asyncio.get_event_loop().time() - start_time
        
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        # Parallel execution should be faster than sequential
        assert execution_time < 0.25  # Less than 3 * 0.1 seconds
        
    async def test_execute_batch_fail_fast(self, mock_browser_session):
        """Test batch execution with fail-fast enabled."""
        config = BatchConfig(fail_fast=True)
        executor = BatchExecutor(config, mock_browser_session)
        
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#missing"),
            BatchCommand(command_id="cmd-3", method="wait", condition="load")
        ]
        
        # Mock first success, second failure
        mock_browser_session.execute_command.side_effect = [
            {"status": "success", "result": {"navigated": True}},
            {"status": "error", "error": {"error_code": "ELEMENT_NOT_FOUND"}},
            {"status": "success", "result": {"waited": True}}  # Should not be called
        ]
        
        results = await executor.execute_batch(commands)
        
        # Should stop after first error
        executed_results = [r for r in results if "status" in r]
        assert len(executed_results) == 2
        assert executed_results[0]["status"] == "success"
        assert executed_results[1]["status"] == "error"
        # Third command should not have been executed
        assert mock_browser_session.execute_command.call_count == 2


class TestBatchProcessor:
    """Test BatchProcessor high-level functionality."""
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Provide a mock browser manager."""
        manager = AsyncMock()
        manager.get_session = AsyncMock()
        return manager
        
    @pytest.fixture
    def batch_processor(self, mock_browser_manager):
        """Provide a batch processor with dependencies."""
        config = BatchConfig()
        return BatchProcessor(config, mock_browser_manager)
        
    async def test_process_batch_request(self, batch_processor, mock_browser_manager):
        """Test processing of batch request."""
        # Mock browser session
        mock_session = AsyncMock()
        mock_session.execute_command = AsyncMock(return_value={
            "status": "success",
            "result": {"executed": True}
        })
        mock_browser_manager.get_session.return_value = mock_session
        
        batch_request = BatchRequest(
            batch_id="batch-123",
            session_id="session-456",
            commands=[
                {
                    "command_id": "cmd-1",
                    "method": "navigate",
                    "url": "https://example.com"
                },
                {
                    "command_id": "cmd-2",
                    "method": "click",
                    "selector": "#button"
                }
            ]
        )
        
        response = await batch_processor.process_batch(batch_request)
        
        assert response.batch_id == "batch-123"
        assert response.session_id == "session-456"
        assert response.status == "success"
        assert len(response.responses) == 2
        assert all(r["status"] == "success" for r in response.responses)
        
    async def test_process_batch_with_dependencies(self, batch_processor, mock_browser_manager):
        """Test batch processing with command dependencies."""
        # Mock browser session
        mock_session = AsyncMock()
        execution_order = []
        
        async def track_execution(command_data):
            execution_order.append(command_data["command_id"])
            return {"status": "success", "result": {"executed": True}}
            
        mock_session.execute_command.side_effect = track_execution
        mock_browser_manager.get_session.return_value = mock_session
        
        batch_request = BatchRequest(
            batch_id="batch-123",
            session_id="session-456",
            commands=[
                {
                    "command_id": "cmd-2",
                    "method": "click",
                    "selector": "#button",
                    "depends_on": ["cmd-1"]
                },
                {
                    "command_id": "cmd-1",
                    "method": "navigate",
                    "url": "https://example.com"
                }
            ]
        )
        
        # Enable dependency processing
        batch_processor.config.enable_dependencies = True
        
        response = await batch_processor.process_batch(batch_request)
        
        assert response.status == "success"
        # cmd-1 should execute before cmd-2
        assert execution_order == ["cmd-1", "cmd-2"]
        
    async def test_process_batch_validation_error(self, batch_processor):
        """Test batch processing with validation errors."""
        batch_request = BatchRequest(
            batch_id="batch-123",
            session_id="session-456",
            commands=[
                {
                    "command_id": "cmd-1",
                    "method": "click"
                    # Missing required selector field
                }
            ]
        )
        
        response = await batch_processor.process_batch(batch_request)
        
        assert response.status == "error"
        assert "validation" in response.error["error_code"].lower()


class TestBatchUtilities:
    """Test batch utility functions and decorators."""
    
    def test_batch_command_decorator(self):
        """Test batch command decorator functionality."""
        
        @batch_command_decorator
        async def sample_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "status": "success",
                "result": {"processed": command_data["method"]}
            }
            
        # Decorator should add metadata
        assert hasattr(sample_command, "_is_batch_command")
        assert sample_command._is_batch_command is True
        
    async def test_validate_batch_request_function(self):
        """Test standalone batch request validation function."""
        valid_request = BatchRequest(
            batch_id="batch-123",
            session_id="session-456",
            commands=[
                {
                    "command_id": "cmd-1",
                    "method": "navigate",
                    "url": "https://example.com"
                }
            ]
        )
        
        # Should not raise for valid request
        validate_batch_request(valid_request)
        
        # Test invalid request
        invalid_request = BatchRequest(
            batch_id="",  # Empty batch ID
            session_id="session-456",
            commands=[]
        )
        
        with pytest.raises(ValueError):
            validate_batch_request(invalid_request)
            
    async def test_execute_batch_commands_function(self):
        """Test standalone batch command execution function."""
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="wait", condition="load")
        ]
        
        # Mock executor function
        async def mock_executor(command):
            return {
                "command_id": command.command_id,
                "status": "success",
                "result": {"executed": True}
            }
            
        results = await execute_batch_commands(commands, mock_executor)
        
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
        assert all(r["command_id"] in ["cmd-1", "cmd-2"] for r in results)


class TestBatchErrorHandling:
    """Test batch error handling and edge cases."""
    
    def test_batch_error_creation(self):
        """Test creation of batch errors."""
        error = BatchError(
            batch_id="batch-123",
            error_code="VALIDATION_ERROR",
            message="Invalid command structure",
            failed_commands=["cmd-1", "cmd-2"]
        )
        
        assert error.batch_id == "batch-123"
        assert error.error_code == "VALIDATION_ERROR"
        assert "Invalid command" in error.message
        assert len(error.failed_commands) == 2
        
    async def test_batch_partial_failure_handling(self):
        """Test handling of partial batch failures."""
        config = BatchConfig(fail_fast=False)
        
        # Mock executor that fails on specific commands
        async def mock_executor(command):
            if command.command_id == "cmd-2":
                return {
                    "command_id": command.command_id,
                    "status": "error",
                    "error": {"error_code": "ELEMENT_NOT_FOUND"}
                }
            return {
                "command_id": command.command_id,
                "status": "success",
                "result": {"executed": True}
            }
            
        commands = [
            BatchCommand(command_id="cmd-1", method="navigate", url="https://example.com"),
            BatchCommand(command_id="cmd-2", method="click", selector="#missing"),
            BatchCommand(command_id="cmd-3", method="wait", condition="load")
        ]
        
        results = await execute_batch_commands(commands, mock_executor)
        
        # All commands should have been attempted
        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "success"
        
    async def test_batch_timeout_handling(self):
        """Test batch-level timeout handling."""
        config = BatchConfig(total_timeout=0.1)  # Very short timeout
        
        # Mock slow executor
        async def slow_executor(command):
            await asyncio.sleep(0.2)  # Longer than batch timeout
            return {
                "command_id": command.command_id,
                "status": "success",
                "result": {"executed": True}
            }
            
        commands = [
            BatchCommand(command_id="cmd-1", method="wait", condition="load")
        ]
        
        # Should handle timeout gracefully
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                execute_batch_commands(commands, slow_executor),
                timeout=config.total_timeout
            )


class TestBatchPerformance:
    """Test batch processing performance characteristics."""
    
    @pytest.mark.performance
    async def test_batch_processing_performance(self):
        """Test batch processing performance with large batches."""
        # Create a large batch of commands
        commands = [
            BatchCommand(command_id=f"cmd-{i}", method="wait", condition="load")
            for i in range(50)
        ]
        
        # Mock fast executor
        async def fast_executor(command):
            await asyncio.sleep(0.01)  # Small delay
            return {
                "command_id": command.command_id,
                "status": "success",
                "result": {"executed": True}
            }
            
        start_time = asyncio.get_event_loop().time()
        results = await execute_batch_commands(commands, fast_executor)
        execution_time = asyncio.get_event_loop().time() - start_time
        
        assert len(results) == 50
        assert all(r["status"] == "success" for r in results)
        # Should complete within reasonable time (parallel execution)
        assert execution_time < 2.0  # Adjust threshold as needed
        
    @pytest.mark.performance
    async def test_dependency_resolution_performance(self):
        """Test dependency resolution performance with complex graphs."""
        # Create commands with complex dependency chain
        commands = []
        for i in range(20):
            depends_on = [f"cmd-{j}" for j in range(max(0, i-3), i)] if i > 0 else []
            commands.append(
                BatchCommand(
                    command_id=f"cmd-{i}",
                    method="wait",
                    condition="load",
                    depends_on=depends_on
                )
            )
            
        resolver = DependencyResolver()
        
        start_time = asyncio.get_event_loop().time()
        execution_order = resolver.resolve_dependencies(commands)
        resolution_time = asyncio.get_event_loop().time() - start_time
        
        assert len(execution_order) == 20
        # Dependency resolution should be fast
        assert resolution_time < 0.1  # Should resolve in less than 100ms
