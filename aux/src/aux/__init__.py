"""
AUX Protocol - Browser automation protocol with AI capabilities.

This package provides a WebSocket-based protocol for controlling browsers
with advanced capabilities designed for AI agents and automated testing.
"""

__version__ = "0.1.0"
__author__ = "AUX Protocol Team"
__email__ = "team@aux-protocol.dev"

from .client.sdk import AUXClient
from .server.websocket_server import WebSocketServer
from .browser.manager import BrowserManager
from .config import get_config, init_config, AUXConfig
from .security import SecurityManager, InputSanitizer
from .logging_utils import init_session_logging, get_session_logger

__all__ = [
    "AUXClient",
    "WebSocketServer", 
    "BrowserManager",
    "get_config",
    "init_config", 
    "AUXConfig",
    "SecurityManager",
    "InputSanitizer",
    "init_session_logging",
    "get_session_logger",
    "__version__",
]