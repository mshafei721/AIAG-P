"""
AUX Protocol Command Schema.

This module defines comprehensive Pydantic models for the 5 core AUX 
protocol commands, including request/response schemas, validation,
and error handling.
"""

from typing import Any, Dict, Optional, Union, List, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from enum import Enum


# Enums for command validation
class CommandMethod(str, Enum):
    """Supported AUX command methods."""
    NAVIGATE = "navigate"
    CLICK = "click" 
    FILL = "fill"
    EXTRACT = "extract"
    WAIT = "wait"


class WaitCondition(str, Enum):
    """Wait conditions for elements and navigation."""
    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded" 
    NETWORKIDLE = "networkidle"
    VISIBLE = "visible"
    HIDDEN = "hidden"
    ATTACHED = "attached"
    DETACHED = "detached"


class MouseButton(str, Enum):
    """Mouse button options for click commands."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ExtractType(str, Enum):
    """Data extraction types."""
    TEXT = "text"
    HTML = "html"
    ATTRIBUTE = "attribute"
    PROPERTY = "property"
    MULTIPLE = "multiple"


# Base command and response models
class BaseCommand(BaseModel):
    """
    Base class for all AUX protocol commands.
    
    Provides common fields and validation for command requests.
    """
    
    id: str = Field(..., description="Unique command identifier for tracking")
    method: CommandMethod = Field(..., description="Command method name")
    session_id: str = Field(..., description="Target browser session ID")
    timeout: Optional[int] = Field(
        30000, 
        ge=1000, 
        le=300000, 
        description="Command timeout in milliseconds (1s-5min)"
    )
    
    model_config = ConfigDict(use_enum_values=True)


class BaseResponse(BaseModel):
    """
    Base class for successful command responses.
    
    Contains common fields for all successful operations.
    """
    
    id: str = Field(..., description="Command ID this response corresponds to")
    success: bool = Field(True, description="Indicates successful execution")
    timestamp: float = Field(..., description="Response timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Command execution time in milliseconds")


class ErrorResponse(BaseModel):
    """
    Error response for failed commands.
    
    Provides detailed error information for debugging and handling.
    """
    
    id: Optional[str] = Field(None, description="Command ID that caused the error")
    success: bool = Field(False, description="Indicates failed execution")
    error: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    error_type: str = Field(..., description="Error category (timeout, element_not_found, etc.)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    timestamp: float = Field(..., description="Error timestamp")


# 1. NAVIGATE Command
class NavigateCommand(BaseCommand):
    """
    Navigate to a URL in the browser session.
    
    Loads the specified URL and waits for the page to reach the specified state.
    Supports various wait conditions for different loading requirements.
    """
    
    method: Literal[CommandMethod.NAVIGATE] = CommandMethod.NAVIGATE
    url: HttpUrl = Field(..., description="URL to navigate to")
    wait_until: WaitCondition = Field(
        WaitCondition.LOAD, 
        description="Condition to wait for after navigation"
    )
    referer: Optional[str] = Field(None, description="Referer header value")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class NavigateResponse(BaseResponse):
    """
    Response from navigate command.
    
    Contains the final URL (after redirects) and page metadata.
    """
    
    url: str = Field(..., description="Final URL after navigation and redirects")
    title: Optional[str] = Field(None, description="Page title")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    redirected: bool = Field(False, description="Whether the navigation was redirected")
    load_time_ms: Optional[int] = Field(None, description="Page load time in milliseconds")


# 2. CLICK Command
class ClickCommand(BaseCommand):
    """
    Click on an element in the browser.
    
    Locates an element using CSS selector and performs a click action.
    Supports different mouse buttons and multiple clicks.
    """
    
    method: Literal[CommandMethod.CLICK] = CommandMethod.CLICK
    selector: str = Field(..., min_length=1, description="CSS selector for target element")
    button: MouseButton = Field(MouseButton.LEFT, description="Mouse button to use")
    click_count: int = Field(1, ge=1, le=10, description="Number of clicks (1-10)")
    force: bool = Field(False, description="Force click even if element is not visible")
    position: Optional[Dict[str, float]] = Field(
        None, 
        description="Relative position within element (x, y from 0.0 to 1.0)"
    )
    
    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        if v is not None:
            if 'x' not in v or 'y' not in v:
                raise ValueError('Position must contain x and y coordinates')
            if not (0.0 <= v['x'] <= 1.0) or not (0.0 <= v['y'] <= 1.0):
                raise ValueError('Position coordinates must be between 0.0 and 1.0')
        return v


class ClickResponse(BaseResponse):
    """
    Response from click command.
    
    Confirms the click was performed and provides element information.
    """
    
    element_found: bool = Field(..., description="Whether the target element was found")
    element_visible: bool = Field(..., description="Whether the element was visible")
    click_position: Dict[str, int] = Field(..., description="Actual click coordinates (x, y)")
    element_text: Optional[str] = Field(None, description="Text content of clicked element")
    element_tag: Optional[str] = Field(None, description="Tag name of clicked element")


# 3. FILL Command
class FillCommand(BaseCommand):
    """
    Fill input fields with text.
    
    Locates form elements and enters text, supporting various input types
    and options for clearing existing content.
    """
    
    method: Literal[CommandMethod.FILL] = CommandMethod.FILL
    selector: str = Field(..., min_length=1, description="CSS selector for input element")
    text: str = Field(..., description="Text to enter in the field")
    clear_first: bool = Field(True, description="Clear existing content before filling")
    press_enter: bool = Field(False, description="Press Enter after filling")
    typing_delay_ms: int = Field(
        0, 
        ge=0, 
        le=1000, 
        description="Delay between keystrokes in milliseconds (0-1000)"
    )
    validate_input: bool = Field(True, description="Validate that text was actually entered")


class FillResponse(BaseResponse):
    """
    Response from fill command.
    
    Confirms the text was entered and provides validation information.
    """
    
    element_found: bool = Field(..., description="Whether the target element was found")
    element_type: str = Field(..., description="Type of input element (input, textarea, etc.)")
    text_entered: str = Field(..., description="Text that was actually entered")
    previous_value: Optional[str] = Field(None, description="Previous value before filling")
    current_value: str = Field(..., description="Current value after filling")
    validation_passed: bool = Field(..., description="Whether input validation passed")


# 4. EXTRACT Command
class ExtractCommand(BaseCommand):
    """
    Extract data from page elements.
    
    Supports extracting text, HTML, attributes, or properties from elements.
    Can extract from single or multiple elements.
    """
    
    method: Literal[CommandMethod.EXTRACT] = CommandMethod.EXTRACT
    selector: str = Field(..., min_length=1, description="CSS selector for target element(s)")
    extract_type: ExtractType = Field(ExtractType.TEXT, description="Type of data to extract")
    attribute_name: Optional[str] = Field(
        None, 
        description="Attribute name (required for attribute extraction)"
    )
    property_name: Optional[str] = Field(
        None, 
        description="Property name (required for property extraction)"
    )
    multiple: bool = Field(False, description="Extract from all matching elements")
    trim_whitespace: bool = Field(True, description="Trim whitespace from extracted text")
    
    @field_validator('attribute_name')
    @classmethod
    def validate_attribute_name(cls, v, info):
        if info.data.get('extract_type') == ExtractType.ATTRIBUTE and not v:
            raise ValueError('attribute_name is required for attribute extraction')
        return v
    
    @field_validator('property_name')
    @classmethod
    def validate_property_name(cls, v, info):
        if info.data.get('extract_type') == ExtractType.PROPERTY and not v:
            raise ValueError('property_name is required for property extraction')
        return v


class ExtractResponse(BaseResponse):
    """
    Response from extract command.
    
    Contains the extracted data and metadata about the extraction.
    """
    
    elements_found: int = Field(..., ge=0, description="Number of elements found")
    data: Union[str, List[str], Dict[str, Any]] = Field(
        ..., 
        description="Extracted data (string for single, list for multiple)"
    )
    element_info: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Additional information about each element"
    )


# 5. WAIT Command
class WaitCommand(BaseCommand):
    """
    Wait for elements or conditions.
    
    Provides flexible waiting capabilities for elements to appear, disappear,
    or meet specific conditions.
    """
    
    method: Literal[CommandMethod.WAIT] = CommandMethod.WAIT
    selector: Optional[str] = Field(None, description="CSS selector for element to wait for")
    condition: WaitCondition = Field(
        WaitCondition.VISIBLE, 
        description="Condition to wait for"
    )
    text_content: Optional[str] = Field(
        None, 
        description="Wait for element to contain specific text"
    )
    attribute_value: Optional[Dict[str, str]] = Field(
        None, 
        description="Wait for element to have specific attribute value"
    )
    custom_js: Optional[str] = Field(
        None, 
        description="Custom JavaScript condition to wait for (returns boolean)"
    )
    poll_interval_ms: int = Field(
        100, 
        ge=50, 
        le=5000, 
        description="Polling interval in milliseconds (50-5000)"
    )
    
    @field_validator('selector')
    @classmethod
    def validate_selector_required(cls, v, info):
        condition = info.data.get('condition')
        if condition in [WaitCondition.VISIBLE, WaitCondition.HIDDEN, 
                        WaitCondition.ATTACHED, WaitCondition.DETACHED] and not v:
            raise ValueError(f'selector is required for condition: {condition}')
        return v


class WaitResponse(BaseResponse):
    """
    Response from wait command.
    
    Indicates whether the wait condition was met and provides timing information.
    """
    
    condition_met: bool = Field(..., description="Whether the wait condition was satisfied")
    wait_time_ms: int = Field(..., description="Actual time waited in milliseconds")
    final_state: str = Field(..., description="Final state when wait completed or timed out")
    element_count: Optional[int] = Field(None, description="Number of matching elements found")
    condition_details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional details about the condition check"
    )


# Type unions for flexible handling
AnyCommand = Union[
    NavigateCommand,
    ClickCommand, 
    FillCommand,
    ExtractCommand,
    WaitCommand
]

AnyResponse = Union[
    NavigateResponse,
    ClickResponse,
    FillResponse, 
    ExtractResponse,
    WaitResponse,
    ErrorResponse
]

# Command mapping for validation and dispatch
COMMAND_MODELS = {
    CommandMethod.NAVIGATE: NavigateCommand,
    CommandMethod.CLICK: ClickCommand,
    CommandMethod.FILL: FillCommand,
    CommandMethod.EXTRACT: ExtractCommand, 
    CommandMethod.WAIT: WaitCommand,
}

RESPONSE_MODELS = {
    CommandMethod.NAVIGATE: NavigateResponse,
    CommandMethod.CLICK: ClickResponse,
    CommandMethod.FILL: FillResponse,
    CommandMethod.EXTRACT: ExtractResponse,
    CommandMethod.WAIT: WaitResponse,
}


def validate_command(method: str, data: Dict[str, Any]) -> AnyCommand:
    """
    Validate and parse command data into appropriate command model.
    
    Args:
        method: Command method name
        data: Raw command data dictionary
        
    Returns:
        Validated command model instance
        
    Raises:
        ValueError: If method is unknown or data is invalid
    """
    try:
        command_method = CommandMethod(method)
    except ValueError:
        raise ValueError(f"Unknown command method: {method}")
        
    command_model = COMMAND_MODELS[command_method]
    return command_model.model_validate(data)


def create_response(method: str, data: Dict[str, Any]) -> AnyResponse:
    """
    Create appropriate response model for command method.
    
    Args:
        method: Command method name
        data: Response data dictionary
        
    Returns:
        Validated response model instance
        
    Raises:
        ValueError: If method is unknown or data is invalid
    """
    try:
        command_method = CommandMethod(method)
    except ValueError:
        raise ValueError(f"Unknown command method: {method}")
        
    response_model = RESPONSE_MODELS[command_method]
    return response_model.model_validate(data)


def create_error_response(
    command_id: Optional[str] = None,
    error_message: str = "Unknown error",
    error_code: str = "UNKNOWN_ERROR", 
    error_type: str = "general",
    details: Optional[Dict[str, Any]] = None,
    timestamp: Optional[float] = None
) -> ErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        command_id: ID of the command that failed
        error_message: Human-readable error description
        error_code: Machine-readable error code
        error_type: Error category
        details: Additional error context
        timestamp: Error timestamp (defaults to current time)
        
    Returns:
        ErrorResponse instance
    """
    import time
    
    return ErrorResponse(
        id=command_id,
        error=error_message,
        error_code=error_code,
        error_type=error_type,
        details=details or {},
        timestamp=timestamp or time.time()
    )


# Common error codes for standardized error handling
class ErrorCodes:
    """Standard error codes for AUX protocol."""
    
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_COMMAND = "INVALID_COMMAND" 
    INVALID_PARAMS = "INVALID_PARAMS"
    
    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_CLOSED = "SESSION_CLOSED"
    
    # Navigation errors
    NAVIGATION_FAILED = "NAVIGATION_FAILED"
    INVALID_URL = "INVALID_URL"
    
    # Element errors
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_VISIBLE = "ELEMENT_NOT_VISIBLE"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    
    # Timeout errors
    TIMEOUT = "TIMEOUT"
    WAIT_TIMEOUT = "WAIT_TIMEOUT"
    
    # Extract errors
    EXTRACTION_FAILED = "EXTRACTION_FAILED"