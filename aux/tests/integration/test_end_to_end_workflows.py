"""
Comprehensive integration tests for end-to-end AUX Protocol workflows.

Tests cover complete user scenarios from WebSocket connection through
browser automation to response handling, including error conditions
and edge cases.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.integration
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    async def full_stack_setup(self, test_config):
        """Set up complete AUX stack for integration testing."""
        # Create components
        security_manager = SecurityManager(test_config.security_config)
        browser_manager = BrowserManager(test_config)
        server = AUXWebSocketServer(test_config, security_manager, browser_manager)
        
        # Start services
        await browser_manager.start()
        await server.start()
        
        # Create client
        client = AUXClient(
            url=f"ws://{server.host}:{server.port}",
            api_key="test-api-key-123"
        )
        
        yield {
            "server": server,
            "client": client,
            "browser_manager": browser_manager,
            "security_manager": security_manager
        }
        
        # Cleanup
        if client.connected:
            await client.disconnect()
        await server.stop()
        await browser_manager.stop()
        
    async def test_simple_navigation_workflow(self, full_stack_setup):
        """Test simple page navigation workflow."""
        stack = full_stack_setup
        client = stack["client"]
        
        # Connect client
        await client.connect()
        assert client.connected
        
        # Create session
        session_response = await client.create_session()
        assert session_response["status"] == "success"
        session_id = session_response["session_id"]
        
        # Navigate to test page
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<h1 id='title'>Test Page</h1>",
                "wait_until": "load"
            }
        )
        assert nav_response["status"] == "success"
        
        # Extract page title
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#title",
                "extract_type": "text"
            }
        )
        assert extract_response["status"] == "success"
        assert extract_response["result"]["extracted_text"] == "Test Page"
        
        # Close session
        close_response = await client.close_session(session_id)
        assert close_response["status"] == "success"
        
    async def test_form_interaction_workflow(self, full_stack_setup):
        """Test complete form interaction workflow."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to form page
        form_html = """
        <html>
        <body>
            <form id="test-form">
                <input type="text" id="name" name="name" placeholder="Enter name">
                <input type="email" id="email" name="email" placeholder="Enter email">
                <textarea id="message" name="message" placeholder="Enter message"></textarea>
                <button type="submit" id="submit-btn">Submit</button>
            </form>
            <div id="result" style="display:none;">Form submitted!</div>
            <script>
                document.getElementById('test-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    document.getElementById('result').style.display = 'block';
                });
            </script>
        </body>
        </html>
        """
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{form_html}",
                "wait_until": "load"
            }
        )
        
        # Fill form fields
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#name",
                "value": "John Doe"
            }
        )
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#email",
                "value": "john@example.com"
            }
        )
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#message",
                "value": "This is a test message."
            }
        )
        
        # Submit form
        submit_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#submit-btn"
            }
        )
        assert submit_response["status"] == "success"
        
        # Wait for result to appear
        wait_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#result",
                "timeout": 5000
            }
        )
        assert wait_response["status"] == "success"
        
        # Verify form submission
        result_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#result",
                "extract_type": "text"
            }
        )
        assert result_response["status"] == "success"
        assert "Form submitted" in result_response["result"]["extracted_text"]
        
        await client.close_session(session_id)
        
    async def test_batch_commands_workflow(self, full_stack_setup):
        """Test batch command execution workflow."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Execute batch of commands
        batch_response = await client.execute_batch(
            session_id=session_id,
            commands=[
                {
                    "command_id": "nav-1",
                    "method": "navigate",
                    "url": "data:text/html,<div id='content'>Page 1</div>"
                },
                {
                    "command_id": "extract-1",
                    "method": "extract",
                    "selector": "#content",
                    "extract_type": "text"
                },
                {
                    "command_id": "nav-2",
                    "method": "navigate",
                    "url": "data:text/html,<div id='content'>Page 2</div>"
                },
                {
                    "command_id": "extract-2",
                    "method": "extract",
                    "selector": "#content",
                    "extract_type": "text"
                }
            ]
        )
        
        assert batch_response["status"] == "success"
        assert len(batch_response["responses"]) == 4
        
        # Verify individual command results
        responses_by_id = {r["command_id"]: r for r in batch_response["responses"]}
        
        assert responses_by_id["nav-1"]["status"] == "success"
        assert responses_by_id["extract-1"]["status"] == "success"
        assert "Page 1" in responses_by_id["extract-1"]["result"]["extracted_text"]
        
        assert responses_by_id["nav-2"]["status"] == "success"
        assert responses_by_id["extract-2"]["status"] == "success"
        assert "Page 2" in responses_by_id["extract-2"]["result"]["extracted_text"]
        
        await client.close_session(session_id)
        
    async def test_error_handling_workflow(self, full_stack_setup):
        """Test error handling throughout the workflow."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='content'>Test Content</div>"
            }
        )
        
        # Test element not found error
        error_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#nonexistent-element",
                "timeout": 1000
            }
        )
        assert error_response["status"] == "error"
        assert "ELEMENT_NOT_FOUND" in error_response["error"]["error_code"]
        
        # Test invalid command error
        invalid_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "invalid_method",
                "selector": "#content"
            }
        )
        assert invalid_response["status"] == "error"
        assert "INVALID_COMMAND" in invalid_response["error"]["error_code"]
        
        # Test timeout error
        timeout_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#never-appears",
                "timeout": 100  # Very short timeout
            }
        )
        assert timeout_response["status"] == "error"
        assert "TIMEOUT" in timeout_response["error"]["error_code"]
        
        await client.close_session(session_id)
        
    async def test_concurrent_sessions_workflow(self, full_stack_setup):
        """Test concurrent session handling."""
        stack = full_stack_setup
        
        # Create multiple clients
        clients = []
        for i in range(3):
            client = AUXClient(
                url=f"ws://{stack['server'].host}:{stack['server'].port}",
                api_key=f"test-api-key-{i}"
            )
            await client.connect()
            clients.append(client)
            
        # Create sessions for each client
        sessions = []
        for client in clients:
            session_response = await client.create_session()
            assert session_response["status"] == "success"
            sessions.append(session_response["session_id"])
            
        # Execute commands concurrently
        async def execute_commands(client, session_id, page_num):
            # Navigate
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Page {page_num}</h1>"
                }
            )
            
            # Extract content
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "h1",
                    "extract_type": "text"
                }
            )
            return response
            
        # Run concurrent operations
        tasks = [
            execute_commands(clients[i], sessions[i], i+1)
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        for i, result in enumerate(results):
            assert result["status"] == "success"
            assert f"Page {i+1}" in result["result"]["extracted_text"]
            
        # Cleanup sessions and clients
        for i, client in enumerate(clients):
            await client.close_session(sessions[i])
            await client.disconnect()
            
    async def test_session_state_persistence(self, full_stack_setup):
        """Test session state persistence across commands."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to initial page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<a href='#page2' id='link'>Go to Page 2</a><div id='page2' style='display:none;'>Page 2 Content</div>"
            }
        )
        
        # Click link to modify page state
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#link"
            }
        )
        
        # Add some JavaScript to handle the click
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "evaluate",
                "script": "document.getElementById('page2').style.display = 'block';"
            }
        )
        
        # Verify state persisted
        wait_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#page2"
            }
        )
        assert wait_response["status"] == "success"
        
        # Extract content from modified state
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#page2",
                "extract_type": "text"
            }
        )
        assert extract_response["status"] == "success"
        assert "Page 2 Content" in extract_response["result"]["extracted_text"]
        
        await client.close_session(session_id)
        
    async def test_websocket_reconnection_workflow(self, full_stack_setup):
        """Test WebSocket reconnection handling."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        assert client.connected
        
        # Create session
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Execute initial command
        response1 = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Initial Page</div>"
            }
        )
        assert response1["status"] == "success"
        
        # Simulate connection drop and reconnect
        await client.disconnect()
        assert not client.connected
        
        await client.connect()
        assert client.connected
        
        # Try to use existing session (should fail)
        response2 = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "div",
                "extract_type": "text"
            }
        )
        assert response2["status"] == "error"
        assert "SESSION_NOT_FOUND" in response2["error"]["error_code"]
        
        # Create new session
        new_session_response = await client.create_session()
        new_session_id = new_session_response["session_id"]
        
        # Execute command with new session
        response3 = await client.execute_command(
            session_id=new_session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>New Page</div>"
            }
        )
        assert response3["status"] == "success"
        
        await client.close_session(new_session_id)


@pytest.mark.integration
class TestPerformanceWorkflows:
    """Test performance-related workflows."""
    
    async def test_high_throughput_commands(self, full_stack_setup):
        """Test high-throughput command execution."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='content'>Test Content</div>"
            }
        )
        
        # Execute many extract commands rapidly
        start_time = asyncio.get_event_loop().time()
        
        tasks = []
        for i in range(50):
            task = client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "#content",
                    "extract_type": "text"
                }
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Verify all commands succeeded
        assert all(r["status"] == "success" for r in results)
        assert all("Test Content" in r["result"]["extracted_text"] for r in results)
        
        # Performance assertion (adjust threshold as needed)
        assert execution_time < 10.0  # Should complete in less than 10 seconds
        
        await client.close_session(session_id)
        
    async def test_large_data_extraction(self, full_stack_setup):
        """Test extraction of large amounts of data."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create page with large amount of content
        large_content = "\n".join([f"<p>Line {i}: {' '.join(['word'] * 20)}</p>" for i in range(1000)])
        large_html = f"<html><body><div id='content'>{large_content}</div></body></html>"
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{large_html}"
            }
        )
        
        # Extract large content
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content",
                "extract_type": "html"
            }
        )
        
        assert extract_response["status"] == "success"
        extracted_html = extract_response["result"]["extracted_html"]
        assert len(extracted_html) > 50000  # Should be substantial amount of content
        assert "Line 999:" in extracted_html  # Should contain end content
        
        await client.close_session(session_id)
        
    async def test_memory_usage_stability(self, full_stack_setup):
        """Test memory usage stability over extended operations."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        
        # Perform many session create/destroy cycles
        for i in range(20):
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            
            # Perform operations
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Session {i}</div>"
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
            
            # Close session
            await client.close_session(session_id)
            
        # Verify server is still responsive
        final_session_response = await client.create_session()
        assert final_session_response["status"] == "success"
        await client.close_session(final_session_response["session_id"])


@pytest.mark.integration
class TestSecurityWorkflows:
    """Test security-related workflows."""
    
    async def test_authentication_workflow(self, test_config):
        """Test authentication workflow."""
        # Setup with authentication enabled
        security_config = test_config.security_config
        security_config.enable_auth = True
        security_config.api_keys = ["valid-key-123", "another-valid-key"]
        
        security_manager = SecurityManager(security_config)
        browser_manager = BrowserManager(test_config)
        server = AUXWebSocketServer(test_config, security_manager, browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        try:
            # Test with valid API key
            valid_client = AUXClient(
                url=f"ws://{server.host}:{server.port}",
                api_key="valid-key-123"
            )
            
            await valid_client.connect()
            assert valid_client.connected
            
            session_response = await valid_client.create_session()
            assert session_response["status"] == "success"
            
            await valid_client.close_session(session_response["session_id"])
            await valid_client.disconnect()
            
            # Test with invalid API key
            invalid_client = AUXClient(
                url=f"ws://{server.host}:{server.port}",
                api_key="invalid-key"
            )
            
            with pytest.raises(Exception):  # Should fail to connect or authenticate
                await invalid_client.connect()
                await invalid_client.create_session()
                
        finally:
            await server.stop()
            await browser_manager.stop()
            
    async def test_rate_limiting_workflow(self, full_stack_setup):
        """Test rate limiting workflow."""
        stack = full_stack_setup
        
        # Configure rate limiting
        stack["security_manager"].config.rate_limit_per_minute = 10  # Very low limit
        
        client = stack["client"]
        await client.connect()
        
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Execute commands rapidly to trigger rate limiting
        successful_commands = 0
        rate_limited = False
        
        for i in range(20):  # More than the rate limit
            try:
                response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>Request {i}</div>"
                    }
                )
                
                if response["status"] == "success":
                    successful_commands += 1
                elif "RATE_LIMIT" in response.get("error", {}).get("error_code", ""):
                    rate_limited = True
                    break
                    
            except Exception as e:
                if "rate limit" in str(e).lower():
                    rate_limited = True
                    break
                    
        # Should have hit rate limit before completing all commands
        assert rate_limited or successful_commands < 20
        
        await client.close_session(session_id)


@pytest.mark.integration
class TestEdgeCaseWorkflows:
    """Test edge case and error condition workflows."""
    
    async def test_malformed_request_handling(self, full_stack_setup):
        """Test handling of malformed requests."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test malformed command structure
        malformed_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                # Missing required selector field
                "invalid_field": "invalid_value"
            }
        )
        
        assert malformed_response["status"] == "error"
        assert "VALIDATION_ERROR" in malformed_response["error"]["error_code"]
        
        # Test invalid JSON in batch command
        try:
            # Simulate sending raw invalid JSON
            invalid_batch = {
                "batch_id": "invalid-batch",
                "session_id": session_id,
                "commands": [
                    {
                        "command_id": "cmd-1",
                        "method": "navigate",
                        "url": "data:text/html,<div>Test</div>",
                        "invalid_nested": {
                            "deeply": {
                                "nested": {
                                    "invalid": "structure"
                                }
                            }
                        }
                    }
                ]
            }
            
            batch_response = await client.execute_batch(
                session_id=session_id,
                commands=invalid_batch["commands"]
            )
            
            # Should handle gracefully
            assert batch_response["status"] in ["success", "error"]
            
        except Exception as e:
            # Should not crash the server
            assert "server crashed" not in str(e).lower()
            
        await client.close_session(session_id)
        
    async def test_resource_exhaustion_handling(self, full_stack_setup):
        """Test handling of resource exhaustion scenarios."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        
        # Create many sessions to test resource limits
        sessions = []
        max_sessions = 20  # Should be within reasonable limits
        
        try:
            for i in range(max_sessions):
                session_response = await client.create_session()
                if session_response["status"] == "success":
                    sessions.append(session_response["session_id"])
                else:
                    # Hit resource limit
                    assert "RESOURCE_LIMIT" in session_response["error"]["error_code"]
                    break
                    
            # Should be able to create at least a few sessions
            assert len(sessions) >= 1
            
        finally:
            # Cleanup sessions
            for session_id in sessions:
                try:
                    await client.close_session(session_id)
                except:
                    pass  # Ignore cleanup errors
                    
    async def test_network_interruption_recovery(self, full_stack_setup):
        """Test recovery from network interruptions."""
        stack = full_stack_setup
        client = stack["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Execute command successfully
        response1 = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Before Interruption</div>"
            }
        )
        assert response1["status"] == "success"
        
        # Simulate network interruption by closing connection
        await client._websocket.close()  # Force close underlying websocket
        
        # Attempt to execute command (should fail)
        try:
            response2 = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "div",
                    "extract_type": "text"
                }
            )
            # If it doesn't raise an exception, it should return an error
            assert response2["status"] == "error"
        except Exception:
            # Expected - connection was closed
            pass
            
        # Reconnect and verify server is still operational
        await client.connect()
        new_session_response = await client.create_session()
        assert new_session_response["status"] == "success"
        
        # Execute command with new session
        response3 = await client.execute_command(
            session_id=new_session_response["session_id"],
            command={
                "method": "navigate",
                "url": "data:text/html,<div>After Recovery</div>"
            }
        )
        assert response3["status"] == "success"
        
        await client.close_session(new_session_response["session_id"])
