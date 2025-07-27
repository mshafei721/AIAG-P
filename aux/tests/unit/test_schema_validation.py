"""
Unit tests for Pydantic schema validation.

Tests all command models, validation rules, error handling,
and schema compliance for the AUX protocol.
"""

import pytest
from typing import Dict, Any
from pydantic import ValidationError

from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, ExtractCommand, WaitCommand,
    NavigateResponse, ClickResponse, FillResponse, ExtractResponse, WaitResponse,
    ErrorResponse, create_error_response, ErrorCodes,
    CommandMethod, WaitCondition, MouseButton, ExtractType
)


@pytest.mark.unit
class TestCommandValidation:
    """Test cases for command schema validation."""

    def test_navigate_command_valid(self):
        """Test valid navigate command creation."""
        command = NavigateCommand(
            method="navigate",
            url="https://example.com",
            wait_until="load",
            timeout=30000
        )
        
        assert command.method == CommandMethod.NAVIGATE
        assert command.url == "https://example.com"
        assert command.wait_until == WaitCondition.LOAD
        assert command.timeout == 30000

    def test_navigate_command_invalid_url(self):
        """Test navigate command with invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                method="navigate",
                url="not-a-valid-url"
            )
        
        errors = exc_info.value.errors()
        assert any("url" in str(error) for error in errors)

    def test_navigate_command_invalid_method(self):
        """Test navigate command with invalid method."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                method="invalid_method",
                url="https://example.com"
            )
        
        errors = exc_info.value.errors()
        assert any("method" in str(error) for error in errors)

    @pytest.mark.parametrize("wait_until", ["load", "domcontentloaded", "networkidle"])
    def test_navigate_command_valid_wait_conditions(self, wait_until: str):
        """Test navigate command with various wait conditions."""
        command = NavigateCommand(
            method="navigate",
            url="https://example.com",
            wait_until=wait_until
        )
        
        assert command.wait_until == wait_until

    def test_navigate_command_invalid_wait_condition(self):
        """Test navigate command with invalid wait condition."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                method="navigate",
                url="https://example.com",
                wait_until="invalid_condition"
            )
        
        errors = exc_info.value.errors()
        assert any("wait_until" in str(error) for error in errors)

    def test_click_command_valid(self):
        """Test valid click command creation."""
        command = ClickCommand(
            method="click",
            selector="#button",
            button="left",
            modifiers=["shift"],
            timeout=5000
        )
        
        assert command.method == CommandMethod.CLICK
        assert command.selector == "#button"
        assert command.button == MouseButton.LEFT
        assert command.modifiers == ["shift"]
        assert command.timeout == 5000

    def test_click_command_missing_selector(self):
        """Test click command without selector."""
        with pytest.raises(ValidationError) as exc_info:
            ClickCommand(method="click")
        
        errors = exc_info.value.errors()
        assert any("selector" in str(error) for error in errors)

    @pytest.mark.parametrize("button", ["left", "right", "middle"])
    def test_click_command_valid_buttons(self, button: str):
        """Test click command with various mouse buttons."""
        command = ClickCommand(
            method="click",
            selector="#button",
            button=button
        )
        
        assert command.button == button

    def test_click_command_invalid_button(self):
        """Test click command with invalid mouse button."""
        with pytest.raises(ValidationError) as exc_info:
            ClickCommand(
                method="click",
                selector="#button",
                button="invalid_button"
            )
        
        errors = exc_info.value.errors()
        assert any("button" in str(error) for error in errors)

    def test_fill_command_valid(self):
        """Test valid fill command creation."""
        command = FillCommand(
            method="fill",
            selector="#input",
            value="test value",
            clear=True,
            timeout=5000
        )
        
        assert command.method == CommandMethod.FILL
        assert command.selector == "#input"
        assert command.value == "test value"
        assert command.clear is True
        assert command.timeout == 5000

    def test_fill_command_missing_required_fields(self):
        """Test fill command with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            FillCommand(method="fill")
        
        errors = exc_info.value.errors()
        assert any("selector" in str(error) for error in errors)
        assert any("value" in str(error) for error in errors)

    def test_fill_command_empty_value(self):
        """Test fill command with empty value (should be valid for clearing)."""
        command = FillCommand(
            method="fill",
            selector="#input",
            value=""
        )
        
        assert command.value == ""

    def test_extract_command_valid(self):
        """Test valid extract command creation."""
        command = ExtractCommand(
            method="extract",
            selector="h1",
            extract_type="text",
            attribute="data-value",
            timeout=5000
        )
        
        assert command.method == CommandMethod.EXTRACT
        assert command.selector == "h1"
        assert command.extract_type == ExtractType.TEXT
        assert command.attribute == "data-value"
        assert command.timeout == 5000

    @pytest.mark.parametrize("extract_type", ["text", "html", "attribute", "property", "multiple"])
    def test_extract_command_valid_types(self, extract_type: str):
        """Test extract command with various extract types."""
        command_data = {
            "method": "extract",
            "selector": "div",
            "extract_type": extract_type
        }
        
        if extract_type == "attribute":
            command_data["attribute"] = "class"
        elif extract_type == "property":
            command_data["property"] = "value"
            
        command = ExtractCommand(**command_data)
        assert command.extract_type == extract_type

    def test_extract_command_attribute_without_name(self):
        """Test extract command with attribute type but no attribute name."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractCommand(
                method="extract",
                selector="div",
                extract_type="attribute"
            )
        
        errors = exc_info.value.errors()
        assert any("attribute" in str(error) for error in errors)

    def test_wait_command_valid(self):
        """Test valid wait command creation."""
        command = WaitCommand(
            method="wait",
            condition="visible",
            selector="#element",
            timeout=10000
        )
        
        assert command.method == CommandMethod.WAIT
        assert command.condition == WaitCondition.VISIBLE
        assert command.selector == "#element"
        assert command.timeout == 10000

    @pytest.mark.parametrize("condition", ["load", "domcontentloaded", "networkidle", "visible", "hidden", "attached", "detached"])
    def test_wait_command_valid_conditions(self, condition: str):
        """Test wait command with various conditions."""
        command_data = {
            "method": "wait",
            "condition": condition
        }
        
        # Some conditions require a selector
        if condition in ["visible", "hidden", "attached", "detached"]:
            command_data["selector"] = "#element"
            
        command = WaitCommand(**command_data)
        assert command.condition == condition

    def test_wait_command_visible_without_selector(self):
        """Test wait command with visible condition but no selector."""
        with pytest.raises(ValidationError) as exc_info:
            WaitCommand(
                method="wait",
                condition="visible"
            )
        
        errors = exc_info.value.errors()
        assert any("selector" in str(error) for error in errors)

    def test_timeout_validation_negative(self):
        """Test that negative timeouts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                method="navigate",
                url="https://example.com",
                timeout=-1000
            )
        
        errors = exc_info.value.errors()
        assert any("timeout" in str(error) for error in errors)

    def test_timeout_validation_too_large(self):
        """Test that excessively large timeouts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateCommand(
                method="navigate",
                url="https://example.com",
                timeout=600000  # 10 minutes
            )
        
        errors = exc_info.value.errors()
        assert any("timeout" in str(error) for error in errors)


@pytest.mark.unit
class TestResponseValidation:
    """Test cases for response schema validation."""

    def test_navigate_response_valid(self):
        """Test valid navigate response creation."""
        response = NavigateResponse(
            status="success",
            url="https://example.com",
            title="Example",
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.url == "https://example.com"
        assert response.title == "Example"

    def test_click_response_valid(self):
        """Test valid click response creation."""
        response = ClickResponse(
            status="success",
            selector="#button",
            element_found=True,
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.selector == "#button"
        assert response.element_found is True

    def test_fill_response_valid(self):
        """Test valid fill response creation."""
        response = FillResponse(
            status="success",
            selector="#input",
            value="filled value",
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.selector == "#input"
        assert response.value == "filled value"

    def test_extract_response_valid_text(self):
        """Test valid extract response with text data."""
        response = ExtractResponse(
            status="success",
            selector="h1",
            extract_type="text",
            data="Heading Text",
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.data == "Heading Text"

    def test_extract_response_valid_multiple(self):
        """Test valid extract response with multiple data."""
        response = ExtractResponse(
            status="success",
            selector="li",
            extract_type="multiple",
            data=["Item 1", "Item 2", "Item 3"],
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.data == ["Item 1", "Item 2", "Item 3"]

    def test_wait_response_valid(self):
        """Test valid wait response creation."""
        response = WaitResponse(
            status="success",
            condition="visible",
            selector="#element",
            session_id="test-session",
            timestamp=1234567890.0
        )
        
        assert response.status == "success"
        assert response.condition == "visible"

    def test_error_response_creation(self):
        """Test error response creation helper."""
        error_response = create_error_response(
            error_code=ErrorCodes.ELEMENT_NOT_FOUND,
            message="Element not found",
            session_id="test-session"
        )
        
        assert error_response.status == "error"
        assert error_response.error.error_code == ErrorCodes.ELEMENT_NOT_FOUND
        assert error_response.error.message == "Element not found"

    def test_response_invalid_status(self):
        """Test response with invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateResponse(
                status="invalid_status",
                url="https://example.com",
                session_id="test-session",
                timestamp=1234567890.0
            )
        
        errors = exc_info.value.errors()
        assert any("status" in str(error) for error in errors)

    def test_response_missing_required_fields(self):
        """Test response with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            NavigateResponse(status="success")
        
        errors = exc_info.value.errors()
        assert any("session_id" in str(error) for error in errors)
        assert any("timestamp" in str(error) for error in errors)


@pytest.mark.unit
class TestSchemaEdgeCases:
    """Test edge cases and boundary conditions for schemas."""

    def test_url_edge_cases(self):
        """Test URL validation edge cases."""
        valid_urls = [
            "https://example.com",
            "http://localhost:8080",
            "https://sub.domain.com/path?param=value",
            "data:text/html,<h1>Test</h1>",
        ]
        
        for url in valid_urls:
            command = NavigateCommand(method="navigate", url=url)
            assert command.url == url

    def test_selector_edge_cases(self):
        """Test selector validation edge cases."""
        valid_selectors = [
            "#id",
            ".class",
            "tag",
            "div > p",
            "[data-test='value']",
            ":nth-child(1)",
            "text='Button Text'",
        ]
        
        for selector in valid_selectors:
            command = ClickCommand(method="click", selector=selector)
            assert command.selector == selector

    def test_large_string_values(self):
        """Test handling of large string values."""
        large_value = "A" * 10000  # 10KB string
        
        command = FillCommand(
            method="fill",
            selector="#input",
            value=large_value
        )
        
        assert len(command.value) == 10000

    def test_unicode_values(self):
        """Test handling of Unicode values."""
        unicode_value = "Hello 世界 🌍 Café naïve résumé"
        
        command = FillCommand(
            method="fill",
            selector="#input",
            value=unicode_value
        )
        
        assert command.value == unicode_value

    def test_empty_string_handling(self):
        """Test handling of empty strings where allowed."""
        # Empty value should be allowed for fill commands (clearing)
        command = FillCommand(
            method="fill",
            selector="#input",
            value=""
        )
        
        assert command.value == ""

    @pytest.mark.parametrize("timeout", [0, 1, 1000, 60000])
    def test_timeout_boundary_values(self, timeout: int):
        """Test timeout boundary values."""
        command = NavigateCommand(
            method="navigate",
            url="https://example.com",
            timeout=timeout
        )
        
        assert command.timeout == timeout