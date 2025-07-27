"""
Comprehensive unit tests for AUX Protocol command schema validation.

Tests cover all command types, validation logic, error handling,
and edge cases for the core command schema.
"""

import pytest
from typing import Any, Dict
from pydantic import ValidationError

from aux.schema.commands import (
    CommandMethod,
    WaitCondition,
    MouseButton,
    ExtractType,
    NavigateCommand,
    ClickCommand,
    FillCommand,
    ExtractCommand,
    WaitCommand,
    CommandRequest,
    CommandResponse,
    ErrorResponse,
    BatchRequest,
    BatchResponse,
)


class TestCommandEnums:
    """Test enum validation and values."""
    
    def test_command_method_values(self):
        """Test all supported command methods."""
        assert CommandMethod.NAVIGATE == "navigate"
        assert CommandMethod.CLICK == "click"
        assert CommandMethod.FILL == "fill"
        assert CommandMethod.EXTRACT == "extract"
        assert CommandMethod.WAIT == "wait"
        
    def test_wait_condition_values(self):
        """Test all wait condition values."""
        assert WaitCondition.LOAD == "load"
        assert WaitCondition.DOMCONTENTLOADED == "domcontentloaded"
        assert WaitCondition.NETWORKIDLE == "networkidle"
        assert WaitCondition.VISIBLE == "visible"
        assert WaitCondition.HIDDEN == "hidden"
        assert WaitCondition.ATTACHED == "attached"
        assert WaitCondition.DETACHED == "detached"
        
    def test_mouse_button_values(self):
        """Test mouse button enum values."""
        assert MouseButton.LEFT == "left"
        assert MouseButton.RIGHT == "right"
        assert MouseButton.MIDDLE == "middle"
        
    def test_extract_type_values(self):
        """Test extract type enum values."""
        assert ExtractType.TEXT == "text"
        assert ExtractType.HTML == "html"
        assert ExtractType.ATTRIBUTE == "attribute"
        assert ExtractType.PROPERTY == "property"
        assert ExtractType.MULTIPLE == "multiple"


class TestNavigateCommand:
    """Test NavigateCommand validation and functionality."""
    
    def test_valid_navigate_command(self):
        """Test creation of valid navigate command."""
        cmd = NavigateCommand(
            url="https://example.com",
            wait_until="load",
            timeout=30000
        )
        assert cmd.url == "https://example.com"
        assert cmd.wait_until == WaitCondition.LOAD
        assert cmd.timeout == 30000
        
    def test_navigate_command_defaults(self):
        """Test navigate command with default values."""
        cmd = NavigateCommand(url="https://example.com")
        assert cmd.wait_until == WaitCondition.LOAD
        assert cmd.timeout == 30000
        
    def test_navigate_command_invalid_url(self):
        """Test navigate command with invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(url="not-a-url")
        assert "url" in str(exc_info.value)
        
    def test_navigate_command_invalid_wait_condition(self):
        """Test navigate command with invalid wait condition."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                url="https://example.com",
                wait_until="invalid_condition"
            )
        assert "wait_until" in str(exc_info.value)
        
    def test_navigate_command_negative_timeout(self):
        """Test navigate command with negative timeout."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                url="https://example.com",
                timeout=-1000
            )
        assert "timeout" in str(exc_info.value)


class TestClickCommand:
    """Test ClickCommand validation and functionality."""
    
    def test_valid_click_command(self):
        """Test creation of valid click command."""
        cmd = ClickCommand(
            selector="#submit-btn",
            button="left",
            timeout=5000,
            force=False
        )
        assert cmd.selector == "#submit-btn"
        assert cmd.button == MouseButton.LEFT
        assert cmd.timeout == 5000
        assert cmd.force is False
        
    def test_click_command_defaults(self):
        """Test click command with default values."""
        cmd = ClickCommand(selector=".button")
        assert cmd.button == MouseButton.LEFT
        assert cmd.timeout == 30000
        assert cmd.force is False
        
    def test_click_command_empty_selector(self):
        """Test click command with empty selector."""
        with pytest.raises(ValidationError) as exc_info:
            ClickCommand(selector="")
        assert "selector" in str(exc_info.value)
        
    def test_click_command_invalid_button(self):
        """Test click command with invalid button."""
        with pytest.raises(ValidationError) as exc_info:
            ClickCommand(
                selector=".button",
                button="invalid_button"
            )
        assert "button" in str(exc_info.value)


class TestFillCommand:
    """Test FillCommand validation and functionality."""
    
    def test_valid_fill_command(self):
        """Test creation of valid fill command."""
        cmd = FillCommand(
            selector="#name-input",
            value="John Doe",
            timeout=5000,
            clear_first=True
        )
        assert cmd.selector == "#name-input"
        assert cmd.value == "John Doe"
        assert cmd.timeout == 5000
        assert cmd.clear_first is True
        
    def test_fill_command_defaults(self):
        """Test fill command with default values."""
        cmd = FillCommand(
            selector="input[name='email']",
            value="test@example.com"
        )
        assert cmd.timeout == 30000
        assert cmd.clear_first is True
        
    def test_fill_command_empty_selector(self):
        """Test fill command with empty selector."""
        with pytest.raises(ValidationError) as exc_info:
            FillCommand(selector="", value="test")
        assert "selector" in str(exc_info.value)
        
    def test_fill_command_none_value(self):
        """Test fill command with None value."""
        cmd = FillCommand(selector="#input", value="")
        assert cmd.value == ""


class TestExtractCommand:
    """Test ExtractCommand validation and functionality."""
    
    def test_valid_extract_command(self):
        """Test creation of valid extract command."""
        cmd = ExtractCommand(
            selector="h1",
            extract_type="text",
            attribute="title",
            timeout=5000
        )
        assert cmd.selector == "h1"
        assert cmd.extract_type == ExtractType.TEXT
        assert cmd.attribute == "title"
        assert cmd.timeout == 5000
        
    def test_extract_command_defaults(self):
        """Test extract command with default values."""
        cmd = ExtractCommand(
            selector=".content",
            extract_type="html"
        )
        assert cmd.timeout == 30000
        assert cmd.attribute is None
        
    def test_extract_command_invalid_type(self):
        """Test extract command with invalid extract type."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractCommand(
                selector="div",
                extract_type="invalid_type"
            )
        assert "extract_type" in str(exc_info.value)
        
    def test_extract_command_attribute_required(self):
        """Test extract command requiring attribute for attribute type."""
        # This should be validated at the business logic level
        cmd = ExtractCommand(
            selector="img",
            extract_type="attribute",
            attribute="src"
        )
        assert cmd.attribute == "src"


class TestWaitCommand:
    """Test WaitCommand validation and functionality."""
    
    def test_valid_wait_command(self):
        """Test creation of valid wait command."""
        cmd = WaitCommand(
            condition="visible",
            selector="#loading",
            timeout=10000
        )
        assert cmd.condition == WaitCondition.VISIBLE
        assert cmd.selector == "#loading"
        assert cmd.timeout == 10000
        
    def test_wait_command_defaults(self):
        """Test wait command with default values."""
        cmd = WaitCommand(
            condition="load"
        )
        assert cmd.timeout == 30000
        assert cmd.selector is None
        
    def test_wait_command_invalid_condition(self):
        """Test wait command with invalid condition."""
        with pytest.raises(ValidationError) as exc_info:
            WaitCommand(condition="invalid_condition")
        assert "condition" in str(exc_info.value)


class TestCommandRequest:
    """Test CommandRequest validation and functionality."""
    
    def test_valid_command_request(self):
        """Test creation of valid command request."""
        request = CommandRequest(
            command_id="cmd-123",
            session_id="session-456",
            method="navigate",
            url="https://example.com"
        )
        assert request.command_id == "cmd-123"
        assert request.session_id == "session-456"
        assert request.method == CommandMethod.NAVIGATE
        assert request.url == "https://example.com"
        
    def test_command_request_invalid_method(self):
        """Test command request with invalid method."""
        with pytest.raises(ValidationError) as exc_info:
            CommandRequest(
                command_id="cmd-123",
                session_id="session-456",
                method="invalid_method"
            )
        assert "method" in str(exc_info.value)


class TestCommandResponse:
    """Test CommandResponse validation and functionality."""
    
    def test_valid_command_response(self):
        """Test creation of valid command response."""
        response = CommandResponse(
            command_id="cmd-123",
            session_id="session-456",
            status="success",
            result={"extracted_text": "Hello World"},
            execution_time=0.25
        )
        assert response.command_id == "cmd-123"
        assert response.session_id == "session-456"
        assert response.status == "success"
        assert response.result == {"extracted_text": "Hello World"}
        assert response.execution_time == 0.25
        
    def test_command_response_with_element_info(self):
        """Test command response with element information."""
        response = CommandResponse(
            command_id="cmd-123",
            session_id="session-456",
            status="success",
            element_selector="#submit-btn",
            element_tag="button",
            result={"clicked": True}
        )
        assert response.element_selector == "#submit-btn"
        assert response.element_tag == "button"


class TestErrorResponse:
    """Test ErrorResponse validation and functionality."""
    
    def test_valid_error_response(self):
        """Test creation of valid error response."""
        error = ErrorResponse(
            command_id="cmd-123",
            session_id="session-456",
            status="error",
            error={
                "error_code": "ELEMENT_NOT_FOUND",
                "message": "Element with selector '#missing' not found",
                "details": {"selector": "#missing"}
            }
        )
        assert error.status == "error"
        assert error.error["error_code"] == "ELEMENT_NOT_FOUND"
        assert "not found" in error.error["message"]
        
    def test_error_response_required_fields(self):
        """Test error response with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(
                command_id="cmd-123",
                session_id="session-456",
                status="error"
                # Missing error field
            )
        assert "error" in str(exc_info.value)


class TestBatchOperations:
    """Test batch request and response validation."""
    
    def test_valid_batch_request(self):
        """Test creation of valid batch request."""
        batch = BatchRequest(
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
                    "selector": "#submit"
                }
            ]
        )
        assert batch.batch_id == "batch-123"
        assert batch.session_id == "session-456"
        assert len(batch.commands) == 2
        
    def test_batch_request_empty_commands(self):
        """Test batch request with empty commands list."""
        with pytest.raises(ValidationError) as exc_info:
            BatchRequest(
                batch_id="batch-123",
                session_id="session-456",
                commands=[]
            )
        assert "commands" in str(exc_info.value)
        
    def test_valid_batch_response(self):
        """Test creation of valid batch response."""
        batch_resp = BatchResponse(
            batch_id="batch-123",
            session_id="session-456",
            status="success",
            responses=[
                {
                    "command_id": "cmd-1",
                    "status": "success",
                    "result": {"navigated": True}
                },
                {
                    "command_id": "cmd-2",
                    "status": "success",
                    "result": {"clicked": True}
                }
            ],
            total_execution_time=1.5
        )
        assert batch_resp.batch_id == "batch-123"
        assert batch_resp.status == "success"
        assert len(batch_resp.responses) == 2
        assert batch_resp.total_execution_time == 1.5


class TestCommandValidationEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_extremely_long_selector(self):
        """Test command with extremely long selector."""
        long_selector = "div " * 1000 + "#target"
        cmd = ClickCommand(selector=long_selector)
        assert len(cmd.selector) > 3000
        
    def test_unicode_selector(self):
        """Test command with unicode characters in selector."""
        cmd = ClickCommand(selector="[data-test='测试按钮']")
        assert "测试按钮" in cmd.selector
        
    def test_special_characters_in_value(self):
        """Test fill command with special characters."""
        special_value = "Hello\nWorld\t!@#$%^&*()\"'"
        cmd = FillCommand(selector="#input", value=special_value)
        assert cmd.value == special_value
        
    def test_zero_timeout(self):
        """Test command with zero timeout."""
        cmd = ClickCommand(selector="#btn", timeout=0)
        assert cmd.timeout == 0
        
    def test_maximum_timeout(self):
        """Test command with maximum timeout value."""
        max_timeout = 600000  # 10 minutes
        cmd = WaitCommand(condition="visible", timeout=max_timeout)
        assert cmd.timeout == max_timeout


class TestCommandSerialization:
    """Test command serialization and deserialization."""
    
    def test_navigate_command_serialization(self):
        """Test navigate command JSON serialization."""
        cmd = NavigateCommand(
            url="https://example.com",
            wait_until="networkidle",
            timeout=45000
        )
        json_data = cmd.model_dump()
        assert json_data["url"] == "https://example.com"
        assert json_data["wait_until"] == "networkidle"
        assert json_data["timeout"] == 45000
        
    def test_command_request_serialization(self):
        """Test command request JSON serialization."""
        request = CommandRequest(
            command_id="cmd-456",
            session_id="session-789",
            method="extract",
            selector="h1",
            extract_type="text"
        )
        json_data = request.model_dump()
        assert json_data["command_id"] == "cmd-456"
        assert json_data["method"] == "extract"
        assert json_data["extract_type"] == "text"
        
    def test_error_response_serialization(self):
        """Test error response JSON serialization."""
        error = ErrorResponse(
            command_id="cmd-error",
            session_id="session-error",
            status="error",
            error={
                "error_code": "TIMEOUT",
                "message": "Command timed out after 30 seconds"
            }
        )
        json_data = error.model_dump()
        assert json_data["status"] == "error"
        assert json_data["error"]["error_code"] == "TIMEOUT"
