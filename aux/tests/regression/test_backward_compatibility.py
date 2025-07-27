"""
Regression tests for backward compatibility in AUX Protocol.

Tests ensure that protocol changes maintain compatibility with existing
clients and that deprecated features continue to work as expected.
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from packaging import version

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config
from aux.schema.commands import CommandRequest, CommandResponse


@pytest.mark.regression
class TestProtocolVersionCompatibility:
    """Test compatibility across different protocol versions."""
    
    @pytest.fixture
    async def versioned_setup(self, test_config):
        """Set up environment for version compatibility testing."""
        regression_config = test_config
        regression_config.server_config.enable_legacy_support = True
        
        security_manager = SecurityManager(regression_config.security_config)
        browser_manager = BrowserManager(regression_config)
        server = AUXWebSocketServer(regression_config, security_manager, browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        yield {
            "server": server,
            "browser_manager": browser_manager,
            "security_manager": security_manager,
            "config": regression_config
        }
        
        await server.stop()
        await browser_manager.stop()
        
    async def test_legacy_command_format_support(self, versioned_setup):
        """Test support for legacy command formats."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="legacy-test-key",
            protocol_version="1.0"  # Legacy version
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test legacy command formats that should still work
        legacy_commands = [
            # Old navigate format (without wait_until parameter)
            {
                "method": "navigate",
                "url": "data:text/html,<h1>Legacy Test</h1>"
            },
            # Old click format (without force parameter)
            {
                "method": "click",
                "selector": "h1"
            },
            # Old extract format (without multiple type)
            {
                "method": "extract",
                "selector": "h1",
                "type": "text"  # Old field name
            }
        ]
        
        for i, legacy_command in enumerate(legacy_commands):
            response = await client.execute_command(
                session_id=session_id,
                command=legacy_command
            )
            
            # Legacy commands should still work
            assert response["status"] == "success", f"Legacy command {i} failed: {response}"
            
            # Response should include compatibility fields
            assert "command_id" in response
            assert "timestamp" in response
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_deprecated_field_handling(self, versioned_setup):
        """Test handling of deprecated fields in commands."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="deprecated-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Commands with deprecated fields that should be ignored gracefully
        deprecated_commands = [
            {
                "method": "navigate",
                "url": "data:text/html,<div id='test'>Deprecated Test</div>",
                "legacy_wait": True,  # Deprecated field
                "old_timeout": 5000   # Deprecated field
            },
            {
                "method": "extract",
                "selector": "#test",
                "extract_type": "text",
                "return_format": "legacy",  # Deprecated field
                "include_metadata": True    # Deprecated field
            }
        ]
        
        for deprecated_command in deprecated_commands:
            response = await client.execute_command(
                session_id=session_id,
                command=deprecated_command
            )
            
            # Should work despite deprecated fields
            assert response["status"] == "success"
            
            # Should not return deprecated response fields
            assert "legacy_result" not in response
            assert "old_format" not in response
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_version_negotiation(self, versioned_setup):
        """Test protocol version negotiation."""
        setup = versioned_setup
        
        # Test different client versions
        client_versions = [
            {"version": "1.0", "expected_features": ["basic_commands"]},
            {"version": "1.1", "expected_features": ["basic_commands", "batch_commands"]},
            {"version": "2.0", "expected_features": ["basic_commands", "batch_commands", "async_commands"]}
        ]
        
        for version_test in client_versions:
            client_version = version_test["version"]
            expected_features = version_test["expected_features"]
            
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key=f"version-test-{client_version.replace('.', '-')}",
                protocol_version=client_version
            )
            
            await client.connect()
            
            # Get server capabilities for this client version
            capabilities_response = await client.get_capabilities()
            assert capabilities_response["status"] == "success"
            
            server_features = capabilities_response["capabilities"]["features"]
            
            # Verify expected features are available
            for feature in expected_features:
                assert feature in server_features, f"Feature {feature} not available for version {client_version}"
                
            # Test basic functionality
            session_response = await client.create_session()
            assert session_response["status"] == "success"
            
            session_id = session_response["session_id"]
            
            # Basic command should work for all versions
            nav_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Version {client_version} Test</div>"
                }
            )
            assert nav_response["status"] == "success"
            
            await client.close_session(session_id)
            await client.disconnect()
            
    async def test_response_format_evolution(self, versioned_setup):
        """Test evolution of response formats."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="response-format-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='content'>Response Format Test</div>"
            }
        )
        
        # Test extract command response format
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content",
                "extract_type": "text"
            }
        )
        
        # Modern response format
        assert extract_response["status"] == "success"
        assert "result" in extract_response
        assert "extracted_text" in extract_response["result"]
        assert "timestamp" in extract_response
        assert "execution_time" in extract_response
        
        # Should maintain backward compatible fields
        assert "command_id" in extract_response
        assert "session_id" in extract_response
        
        # Should not include legacy fields unless specifically requested
        assert "legacy_format" not in extract_response
        assert "old_result" not in extract_response
        
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.regression
class TestAPIBreakingChanges:
    """Test handling of potential API breaking changes."""
    
    async def test_removed_command_handling(self, versioned_setup):
        """Test handling of removed or renamed commands."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="removed-command-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Commands that might have been removed or renamed
        potentially_removed_commands = [
            {
                "method": "old_navigate",  # Hypothetical old command
                "url": "https://example.com"
            },
            {
                "method": "get_text",      # Hypothetical old extract variant
                "selector": "body"
            },
            {
                "method": "click_element", # Hypothetical old click variant
                "selector": "button"
            }
        ]
        
        for old_command in potentially_removed_commands:
            response = await client.execute_command(
                session_id=session_id,
                command=old_command
            )
            
            # Should gracefully handle unknown commands
            assert response["status"] == "error"
            assert "UNKNOWN_COMMAND" in response["error"]["error_code"]
            
            # Should provide helpful error message
            assert "not supported" in response["error"]["message"].lower() or \
                   "unknown" in response["error"]["message"].lower()
                   
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_parameter_schema_changes(self, versioned_setup):
        """Test handling of parameter schema changes."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="schema-change-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test parameter changes that should be handled gracefully
        schema_change_tests = [
            {
                "name": "missing_required_parameter",
                "command": {
                    "method": "click"
                    # Missing required 'selector' parameter
                },
                "expected_error": "MISSING_PARAMETER"
            },
            {
                "name": "extra_unknown_parameter",
                "command": {
                    "method": "navigate",
                    "url": "data:text/html,<div>Test</div>",
                    "unknown_param": "should_be_ignored"
                },
                "expected_error": None  # Should succeed, ignoring unknown param
            },
            {
                "name": "type_mismatch",
                "command": {
                    "method": "wait",
                    "condition": "visible",
                    "timeout": "not_a_number"  # Should be integer
                },
                "expected_error": "INVALID_PARAMETER"
            }
        ]
        
        for test_case in schema_change_tests:
            response = await client.execute_command(
                session_id=session_id,
                command=test_case["command"]
            )
            
            if test_case["expected_error"]:
                assert response["status"] == "error"
                assert test_case["expected_error"] in response["error"]["error_code"]
            else:
                assert response["status"] == "success"
                
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_error_code_stability(self, versioned_setup):
        """Test that error codes remain stable across versions."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="error-code-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Standard error scenarios that should have stable error codes
        error_scenarios = [
            {
                "name": "element_not_found",
                "command": {
                    "method": "click",
                    "selector": "#nonexistent-element"
                },
                "expected_codes": ["ELEMENT_NOT_FOUND", "SELECTOR_NOT_FOUND"]
            },
            {
                "name": "invalid_selector",
                "command": {
                    "method": "click",
                    "selector": "invalid]]selector[[syntax"
                },
                "expected_codes": ["INVALID_SELECTOR", "SELECTOR_ERROR"]
            },
            {
                "name": "timeout_error",
                "command": {
                    "method": "wait",
                    "condition": "visible",
                    "selector": "#never-appears",
                    "timeout": 100  # Very short timeout
                },
                "expected_codes": ["TIMEOUT", "WAIT_TIMEOUT"]
            }
        ]
        
        # Navigate to test page first
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Error Test Page</div>"
            }
        )
        
        for scenario in error_scenarios:
            response = await client.execute_command(
                session_id=session_id,
                command=scenario["command"]
            )
            
            assert response["status"] == "error"
            error_code = response["error"]["error_code"]
            
            # Error code should be one of the expected stable codes
            assert error_code in scenario["expected_codes"], \
                f"Unexpected error code for {scenario['name']}: {error_code}"
                
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.regression
class TestDataFormatCompatibility:
    """Test compatibility of data formats and serialization."""
    
    async def test_json_response_format_stability(self, versioned_setup):
        """Test that JSON response formats remain stable."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="json-format-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test various response types for format stability
        format_tests = [
            {
                "name": "navigate_response",
                "command": {
                    "method": "navigate",
                    "url": "data:text/html,<h1>Format Test</h1>"
                },
                "required_fields": ["status", "command_id", "session_id", "timestamp"]
            },
            {
                "name": "extract_response",
                "command": {
                    "method": "extract",
                    "selector": "h1",
                    "extract_type": "text"
                },
                "required_fields": ["status", "result", "command_id", "session_id"]
            },
            {
                "name": "click_response",
                "command": {
                    "method": "click",
                    "selector": "h1"
                },
                "required_fields": ["status", "command_id", "session_id"]
            }
        ]
        
        for test in format_tests:
            response = await client.execute_command(
                session_id=session_id,
                command=test["command"]
            )
            
            assert response["status"] == "success"
            
            # Check required fields are present
            for field in test["required_fields"]:
                assert field in response, f"Missing required field '{field}' in {test['name']}"
                
            # Check field types are as expected
            assert isinstance(response["status"], str)
            assert isinstance(response["command_id"], str)
            assert isinstance(response["session_id"], str)
            
            if "timestamp" in response:
                assert isinstance(response["timestamp"], (int, float, str))
                
            if "result" in response:
                assert isinstance(response["result"], dict)
                
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_unicode_handling_compatibility(self, versioned_setup):
        """Test Unicode handling across versions."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="unicode-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Unicode test cases
        unicode_tests = [
            {
                "name": "basic_unicode",
                "text": "Hello 世界",  # Chinese characters
                "expected": "Hello 世界"
            },
            {
                "name": "emoji",
                "text": "Test 🚀🌍",  # Rocket and Earth emojis
                "expected": "Test 🚀🌍"
            },
            {
                "name": "mixed_scripts",
                "text": "English عربي 日本語 русский",  # Arabic, Japanese, Russian
                "expected": "English عربي 日本語 русский"
            },
            {
                "name": "special_chars",
                "text": "Symbols: ©®™°±½",
                "expected": "Symbols: ©®™°±½"
            }
        ]
        
        for test in unicode_tests:
            # Create page with Unicode content
            unicode_html = f'<div id="unicode-test">{test["text"]}</div>'
            
            nav_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,{unicode_html}"
                }
            )
            assert nav_response["status"] == "success"
            
            # Extract Unicode content
            extract_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "#unicode-test",
                    "extract_type": "text"
                }
            )
            
            assert extract_response["status"] == "success"
            extracted_text = extract_response["result"]["extracted_text"]
            
            # Unicode should be preserved exactly
            assert extracted_text == test["expected"], \
                f"Unicode mismatch in {test['name']}: got '{extracted_text}', expected '{test['expected']}'"
                
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_large_data_handling(self, versioned_setup):
        """Test handling of large data payloads."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="large-data-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test large data scenarios
        large_data_tests = [
            {
                "name": "large_text_content",
                "size": 50000,  # 50KB
                "content_type": "text"
            },
            {
                "name": "many_elements",
                "size": 1000,   # 1000 elements
                "content_type": "elements"
            }
        ]
        
        for test in large_data_tests:
            if test["content_type"] == "text":
                # Create large text content
                large_text = "Large content test. " * (test["size"] // 20)
                html_content = f'<div id="large-content">{large_text}</div>'
                
            elif test["content_type"] == "elements":
                # Create many elements
                elements = [f'<div class="item" id="item-{i}">Item {i}</div>' for i in range(test["size"])]
                html_content = f'<div id="container">{"".join(elements)}</div>'
                
            # Navigate to large content page
            nav_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,{html_content}"
                }
            )
            assert nav_response["status"] == "success"
            
            if test["content_type"] == "text":
                # Extract large text
                extract_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#large-content",
                        "extract_type": "text"
                    }
                )
                assert extract_response["status"] == "success"
                assert len(extract_response["result"]["extracted_text"]) > test["size"] // 2
                
            elif test["content_type"] == "elements":
                # Extract multiple elements
                extract_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": ".item",
                        "extract_type": "multiple"
                    }
                )
                assert extract_response["status"] == "success"
                assert len(extract_response["result"]["extracted_elements"]) == test["size"]
                
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.regression
class TestFeatureDeprecationHandling:
    """Test handling of deprecated features and migration paths."""
    
    async def test_deprecated_feature_warnings(self, versioned_setup):
        """Test that deprecated features generate appropriate warnings."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="deprecation-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Hypothetical deprecated features
        deprecated_features = [
            {
                "name": "old_extract_format",
                "command": {
                    "method": "extract",
                    "selector": "body",
                    "type": "text",  # Old parameter name
                    "format": "legacy"  # Deprecated format
                },
                "should_work": True,
                "should_warn": True
            }
        ]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<body>Deprecation Test</body>"
            }
        )
        
        for feature_test in deprecated_features:
            response = await client.execute_command(
                session_id=session_id,
                command=feature_test["command"]
            )
            
            if feature_test["should_work"]:
                assert response["status"] == "success"
                
            if feature_test["should_warn"]:
                # Check for deprecation warning
                assert "warnings" in response or "deprecated" in response.get("message", "").lower()
                
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_migration_guidance(self, versioned_setup):
        """Test that migration guidance is provided for deprecated features."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="migration-test-key"
        )
        
        await client.connect()
        
        # Request server capabilities to check migration info
        capabilities_response = await client.get_capabilities()
        assert capabilities_response["status"] == "success"
        
        capabilities = capabilities_response["capabilities"]
        
        # Check for deprecation information
        if "deprecated_features" in capabilities:
            deprecated_features = capabilities["deprecated_features"]
            
            for feature in deprecated_features:
                # Each deprecated feature should have migration info
                assert "feature_name" in feature
                assert "deprecated_version" in feature
                assert "removal_version" in feature
                assert "migration_guide" in feature
                
                migration_guide = feature["migration_guide"]
                assert "replacement" in migration_guide
                assert "example" in migration_guide
                
        await client.disconnect()


@pytest.mark.regression
class TestPerformanceRegression:
    """Test for performance regressions across versions."""
    
    async def test_command_execution_time_regression(self, versioned_setup):
        """Test that command execution times haven't regressed."""
        setup = versioned_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="performance-regression-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Baseline performance benchmarks (adjust based on actual system performance)
        performance_benchmarks = {
            "navigate": 2.0,  # Max 2 seconds
            "extract": 0.5,   # Max 0.5 seconds
            "click": 0.3,     # Max 0.3 seconds
            "fill": 0.2,      # Max 0.2 seconds
            "wait": 1.0       # Max 1 second (for immediate conditions)
        }
        
        # Test performance of core commands
        performance_commands = [
            {
                "type": "navigate",
                "command": {
                    "method": "navigate",
                    "url": "data:text/html,<div id='perf-test'>Performance Test</div>"
                }
            },
            {
                "type": "extract",
                "command": {
                    "method": "extract",
                    "selector": "#perf-test",
                    "extract_type": "text"
                }
            },
            {
                "type": "click",
                "command": {
                    "method": "click",
                    "selector": "#perf-test"
                }
            }
        ]
        
        for perf_test in performance_commands:
            command_type = perf_test["type"]
            command = perf_test["command"]
            
            # Measure execution time
            start_time = asyncio.get_event_loop().time()
            response = await client.execute_command(
                session_id=session_id,
                command=command
            )
            execution_time = asyncio.get_event_loop().time() - start_time
            
            assert response["status"] == "success"
            
            # Check against benchmark
            benchmark_time = performance_benchmarks[command_type]
            assert execution_time < benchmark_time, \
                f"Performance regression in {command_type}: {execution_time:.3f}s > {benchmark_time}s"
                
            print(f"Performance check {command_type}: {execution_time:.3f}s (benchmark: {benchmark_time}s)")
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_memory_usage_regression(self, versioned_setup):
        """Test for memory usage regressions."""
        import psutil
        
        setup = versioned_setup
        process = psutil.Process()
        
        # Measure initial memory
        initial_memory = process.memory_info().rss
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="memory-regression-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Perform memory-intensive operations
        for i in range(20):
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Memory test {i}</div>"
                }
            )
            
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "div",
                    "extract_type": "text"
                }
            )
            
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        max_memory_increase = 50 * 1024 * 1024  # 50MB
        assert memory_increase < max_memory_increase, \
            f"Memory regression detected: {memory_increase / 1024 / 1024:.2f}MB increase"
            
        print(f"Memory usage: {memory_increase / 1024 / 1024:.2f}MB increase (max: {max_memory_increase / 1024 / 1024:.2f}MB)")
        
        await client.close_session(session_id)
        await client.disconnect()
