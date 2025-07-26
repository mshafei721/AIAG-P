"""
AUX Protocol Schema Definitions.

This module contains Pydantic models for AUX protocol commands,
responses, and data structures.
"""

from .commands import (
    # Base models
    BaseCommand, BaseResponse, ErrorResponse,
    # Command enums
    CommandMethod, WaitCondition, MouseButton, ExtractType,
    # Specific commands  
    NavigateCommand, ClickCommand, FillCommand, ExtractCommand, WaitCommand,
    # Specific responses
    NavigateResponse, ClickResponse, FillResponse, ExtractResponse, WaitResponse,
    # Type unions
    AnyCommand, AnyResponse,
    # Utility functions
    validate_command, create_response, create_error_response,
    # Error codes
    ErrorCodes
)

__all__ = [
    # Base models (backwards compatibility)
    "BaseCommand", "BaseResponse", "ErrorResponse",
    # Command enums
    "CommandMethod", "WaitCondition", "MouseButton", "ExtractType", 
    # Specific commands
    "NavigateCommand", "ClickCommand", "FillCommand", "ExtractCommand", "WaitCommand",
    # Specific responses  
    "NavigateResponse", "ClickResponse", "FillResponse", "ExtractResponse", "WaitResponse",
    # Type unions
    "AnyCommand", "AnyResponse",
    # Utility functions
    "validate_command", "create_response", "create_error_response",
    # Error codes
    "ErrorCodes"
]