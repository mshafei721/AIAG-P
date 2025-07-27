"""
Shared pytest configuration and fixtures for AUX Protocol test suite.

This module provides common fixtures, test configuration, and utilities
used across all test categories (unit, integration, security, performance, e2e).
"""

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
import pytest
import yaml
from faker import Faker

# AUX Protocol imports
from aux.browser.manager import BrowserManager
from aux.client.sdk import AUXClient
from aux.config import Config, get_config
from aux.logging_utils import get_session_logger
from aux.security import SecurityManager
from aux.server.websocket_server import AUXWebSocketServer
from aux.testing.mock_agent import MockAgent
from aux.testing.test_harness import TestHarness


# Configure logging for tests
logging.getLogger("aux").setLevel(logging.DEBUG)
fake = Faker()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> Config:
    """Provide test configuration with secure defaults."""
    return Config(
        browser_config={
            "headless": True,
            "timeout": 30000,
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "AUX-Test-Agent/1.0",
        },
        security_config={
            "enable_auth": True,
            "rate_limit_per_minute": 1000,
            "max_session_duration": 3600,
            "allowed_origins": ["http://localhost", "https://example.com"],
        },
        server_config={
            "host": "localhost",
            "port": 8765,
            "max_connections": 100,
        },
        logging_config={
            "level": "DEBUG",
            "format": "json",
            "file": "test_session.log",
        }
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def session_id() -> str:
    """Generate a unique session ID for tests."""
    return f"test-session-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def api_key() -> str:
    """Generate a test API key."""
    return f"test-key-{uuid.uuid4().hex}"


@pytest.fixture
def security_manager(test_config: Config) -> SecurityManager:
    """Provide a configured SecurityManager for testing."""
    return SecurityManager(test_config.security_config)


@pytest.fixture
async def browser_manager(test_config: Config) -> AsyncGenerator[BrowserManager, None]:
    """Provide a configured BrowserManager for testing."""
    manager = BrowserManager(test_config)
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()


@pytest.fixture
async def mock_browser_session():
    """Provide a mock browser session for unit tests."""
    session = Mock()
    session.session_id = f"mock-{uuid.uuid4().hex[:8]}"
    session.page = AsyncMock()
    session.context = AsyncMock()
    session.created_at = asyncio.get_event_loop().time()
    session.last_activity = asyncio.get_event_loop().time()
    return session


@pytest.fixture
async def websocket_server(
    test_config: Config, 
    security_manager: SecurityManager
) -> AsyncGenerator[AUXWebSocketServer, None]:
    """Provide a running WebSocket server for integration tests."""
    server = AUXWebSocketServer(
        config=test_config,
        security_manager=security_manager
    )
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@pytest.fixture
async def aux_client(websocket_server: AUXWebSocketServer, api_key: str) -> AsyncGenerator[AUXClient, None]:
    """Provide a connected AUX client for integration tests."""
    client = AUXClient(
        url=f"ws://{websocket_server.host}:{websocket_server.port}",
        api_key=api_key
    )
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()


@pytest.fixture
def mock_agent(test_config: Config) -> MockAgent:
    """Provide a MockAgent for testing scenarios."""
    return MockAgent(config=test_config)


@pytest.fixture
def test_harness(test_config: Config) -> TestHarness:
    """Provide a TestHarness for comprehensive testing."""
    return TestHarness(config=test_config)


@pytest.fixture
def sample_html() -> str:
    """Provide sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <div id="main">
            <h1>Test Title</h1>
            <form id="test-form">
                <input type="text" id="name" name="name" placeholder="Enter name">
                <input type="email" id="email" name="email" placeholder="Enter email">
                <button type="submit" id="submit-btn">Submit</button>
            </form>
            <div class="content">
                <p>Sample paragraph text</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                    <li>Item 3</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_commands() -> Dict[str, Any]:
    """Provide sample command data for testing."""
    return {
        "navigate": {
            "method": "navigate",
            "url": "https://example.com",
            "wait_until": "load"
        },
        "click": {
            "method": "click",
            "selector": "#submit-btn",
            "timeout": 5000
        },
        "fill": {
            "method": "fill",
            "selector": "#name",
            "value": "John Doe"
        },
        "extract": {
            "method": "extract",
            "selector": "h1",
            "extract_type": "text"
        },
        "wait": {
            "method": "wait",
            "condition": "visible",
            "selector": "#main"
        }
    }


@pytest.fixture
def malicious_inputs() -> Dict[str, list]:
    """Provide malicious input samples for security testing."""
    return {
        "javascript_injection": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "onload=alert('xss')",
            "eval('alert(1)')",
            "Function('alert(1)')()",
        ],
        "css_injection": [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "expression(alert('xss'))",
        ],
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM passwords --",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
        ],
        "oversized_input": [
            "A" * 10000,
            "B" * 100000,
            "C" * 1000000,
        ]
    }


@pytest.fixture
def performance_scenarios() -> Dict[str, Any]:
    """Provide performance testing scenarios."""
    return {
        "light_load": {
            "concurrent_sessions": 10,
            "commands_per_session": 50,
            "duration": 60
        },
        "medium_load": {
            "concurrent_sessions": 50,
            "commands_per_session": 100,
            "duration": 120
        },
        "heavy_load": {
            "concurrent_sessions": 100,
            "commands_per_session": 200,
            "duration": 300
        },
        "stress_test": {
            "concurrent_sessions": 200,
            "commands_per_session": 500,
            "duration": 600
        }
    }


@pytest.fixture
def test_websites() -> Dict[str, str]:
    """Provide test website URLs for E2E testing."""
    return {
        "simple": "data:text/html,<h1>Simple Test</h1>",
        "form": "data:text/html,<form><input id='test' type='text'><button type='submit'>Submit</button></form>",
        "javascript": "data:text/html,<script>document.body.innerHTML='<p id=\"loaded\">JS Loaded</p>'</script>",
        "iframe": "data:text/html,<iframe src='data:text/html,<p>Frame content</p>'></iframe>",
        "slow": "data:text/html,<script>setTimeout(() => document.body.innerHTML='<p id=\"delayed\">Loaded</p>', 1000)</script>"
    }


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Automatically cleanup test sessions after each test."""
    yield
    # Cleanup logic here if needed


@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        "min_rounds": 5,
        "max_time": 10.0,
        "warmup_rounds": 2,
    }


# Utility functions for tests
def create_test_scenario(name: str, commands: list) -> Dict[str, Any]:
    """Create a test scenario structure."""
    return {
        "name": name,
        "description": f"Test scenario for {name}",
        "commands": commands,
        "expected_results": []
    }


def assert_command_response(response: Dict[str, Any], expected_status: str = "success") -> None:
    """Assert that a command response has the expected structure."""
    assert "status" in response
    assert response["status"] == expected_status
    assert "timestamp" in response
    assert "session_id" in response


def assert_error_response(response: Dict[str, Any], expected_error_code: str = None) -> None:
    """Assert that an error response has the expected structure."""
    assert "status" in response
    assert response["status"] == "error"
    assert "error" in response
    assert "error_code" in response["error"]
    if expected_error_code:
        assert response["error"]["error_code"] == expected_error_code


# Markers for test categorization
pytestmark = [
    pytest.mark.asyncio,
]