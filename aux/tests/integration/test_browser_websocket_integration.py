"""
Comprehensive integration tests for browser-WebSocket integration.

Tests cover the interaction between browser automation and WebSocket
communication, including state synchronization, error propagation,
and concurrent operations.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

from aux.browser.manager import BrowserManager
from aux.server.websocket_server import AUXWebSocketServer
from aux.client.sdk import AUXClient
from aux.config import Config
from aux.schema.commands import CommandRequest, CommandResponse


@pytest.mark.integration
class TestBrowserWebSocketIntegration:
    """Test browser and WebSocket integration scenarios."""
    
    @pytest.fixture
    async def integrated_setup(self, test_config):
        """Set up integrated browser and WebSocket components."""
        browser_manager = BrowserManager(test_config)
        server = AUXWebSocketServer(test_config, browser_manager=browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        client = AUXClient(
            url=f"ws://{server.host}:{server.port}",
            api_key="test-integration-key"
        )
        
        yield {
            "browser_manager": browser_manager,
            "server": server,
            "client": client,
            "config": test_config
        }
        
        # Cleanup
        if client.connected:
            await client.disconnect()
        await server.stop()
        await browser_manager.stop()
        
    async def test_command_flow_through_stack(self, integrated_setup):
        """Test command flow from WebSocket through to browser execution."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        
        # Create session
        session_response = await client.create_session()
        assert session_response["status"] == "success"
        session_id = session_response["session_id"]
        
        # Verify session exists in browser manager
        browser_manager = setup["browser_manager"]
        assert session_id in browser_manager._sessions
        
        # Execute navigate command
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<h1 id='title'>Integration Test</h1>",
                "wait_until": "load"
            }
        )
        
        assert nav_response["status"] == "success"
        assert "command_id" in nav_response
        assert "execution_time" in nav_response
        
        # Verify browser state changed
        session = browser_manager._sessions[session_id]
        current_url = await session.page.url
        assert "data:text/html" in current_url
        
        # Execute extract command to verify page content
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#title",
                "extract_type": "text"
            }
        )
        
        assert extract_response["status"] == "success"
        assert extract_response["result"]["extracted_text"] == "Integration Test"
        
        await client.close_session(session_id)
        
        # Verify session cleaned up
        assert session_id not in browser_manager._sessions
        
    async def test_error_propagation(self, integrated_setup):
        """Test error propagation from browser to WebSocket client."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='content'>Test Page</div>"
            }
        )
        
        # Test element not found error
        error_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#nonexistent",
                "timeout": 1000
            }
        )
        
        assert error_response["status"] == "error"
        assert "error" in error_response
        assert "error_code" in error_response["error"]
        assert "ELEMENT_NOT_FOUND" in error_response["error"]["error_code"]
        assert "message" in error_response["error"]
        
        # Test timeout error
        timeout_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#never-appears",
                "timeout": 100
            }
        )
        
        assert timeout_response["status"] == "error"
        assert "TIMEOUT" in timeout_response["error"]["error_code"]
        
        # Test invalid selector error
        invalid_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "invalid]]selector[[syntax",
                "timeout": 1000
            }
        )
        
        assert invalid_response["status"] == "error"
        assert "INVALID_SELECTOR" in invalid_response["error"]["error_code"]
        
        await client.close_session(session_id)
        
    async def test_concurrent_browser_operations(self, integrated_setup):
        """Test concurrent browser operations through WebSocket."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_response = await client.create_session()
            assert session_response["status"] == "success"
            sessions.append(session_response["session_id"])
            
        # Execute concurrent navigation commands
        async def navigate_session(session_id, page_num):
            return await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<h1 id='title'>Page {page_num}</h1>"
                }
            )
            
        nav_tasks = [
            navigate_session(sessions[i], i+1)
            for i in range(3)
        ]
        nav_results = await asyncio.gather(*nav_tasks)
        
        # Verify all navigations succeeded
        assert all(r["status"] == "success" for r in nav_results)
        
        # Execute concurrent extract commands
        async def extract_from_session(session_id, expected_num):
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "#title",
                    "extract_type": "text"
                }
            )
            assert response["status"] == "success"
            assert f"Page {expected_num}" in response["result"]["extracted_text"]
            return response
            
        extract_tasks = [
            extract_from_session(sessions[i], i+1)
            for i in range(3)
        ]
        extract_results = await asyncio.gather(*extract_tasks)
        
        # Verify all extractions succeeded and returned correct data
        assert all(r["status"] == "success" for r in extract_results)
        
        # Cleanup sessions
        for session_id in sessions:
            await client.close_session(session_id)
            
    async def test_state_synchronization(self, integrated_setup):
        """Test state synchronization between browser and WebSocket."""
        setup = integrated_setup
        client = setup["client"]
        browser_manager = setup["browser_manager"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to interactive page
        interactive_html = """
        <html>
        <body>
            <input type="text" id="input" value="">
            <button id="btn" onclick="updateDisplay()">Update</button>
            <div id="display">Initial Content</div>
            <script>
                function updateDisplay() {
                    const input = document.getElementById('input');
                    const display = document.getElementById('display');
                    display.textContent = 'Updated: ' + input.value;
                }
            </script>
        </body>
        </html>
        """
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{interactive_html}"
            }
        )
        
        # Fill input field
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#input",
                "value": "Test Input"
            }
        )
        
        # Verify input state in browser
        session = browser_manager._sessions[session_id]
        input_value = await session.page.input_value("#input")
        assert input_value == "Test Input"
        
        # Click button to trigger page change
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#btn"
            }
        )
        
        # Verify state changed in browser
        display_text = await session.page.text_content("#display")
        assert "Updated: Test Input" in display_text
        
        # Verify state change reflected in WebSocket response
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#display",
                "extract_type": "text"
            }
        )
        
        assert extract_response["status"] == "success"
        assert "Updated: Test Input" in extract_response["result"]["extracted_text"]
        
        await client.close_session(session_id)
        
    async def test_browser_session_lifecycle(self, integrated_setup):
        """Test browser session lifecycle through WebSocket."""
        setup = integrated_setup
        client = setup["client"]
        browser_manager = setup["browser_manager"]
        
        await client.connect()
        
        # Verify no sessions initially
        assert len(browser_manager._sessions) == 0
        
        # Create session
        session_response = await client.create_session()
        assert session_response["status"] == "success"
        session_id = session_response["session_id"]
        
        # Verify session created in browser manager
        assert len(browser_manager._sessions) == 1
        assert session_id in browser_manager._sessions
        
        session = browser_manager._sessions[session_id]
        assert session.page is not None
        assert session.context is not None
        
        # Use session
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Session Active</div>"
            }
        )
        
        # Verify session is active
        current_url = await session.page.url
        assert "data:text/html" in current_url
        
        # Close session via WebSocket
        close_response = await client.close_session(session_id)
        assert close_response["status"] == "success"
        
        # Verify session cleaned up in browser manager
        assert len(browser_manager._sessions) == 0
        assert session_id not in browser_manager._sessions
        
        # Verify session resources are closed
        assert session.page.is_closed()
        
    async def test_command_timeout_handling(self, integrated_setup):
        """Test command timeout handling across the stack."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to page with slow-loading content
        slow_html = """
        <html>
        <body>
            <div id="immediate">Immediate Content</div>
            <script>
                setTimeout(() => {
                    const div = document.createElement('div');
                    div.id = 'delayed';
                    div.textContent = 'Delayed Content';
                    document.body.appendChild(div);
                }, 5000);  // 5 second delay
            </script>
        </body>
        </html>
        """
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{slow_html}"
            }
        )
        
        # Test successful command within timeout
        quick_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#immediate",
                "extract_type": "text",
                "timeout": 1000
            }
        )
        assert quick_response["status"] == "success"
        
        # Test command that times out
        timeout_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#delayed",
                "timeout": 1000  # Will timeout before 5 second delay
            }
        )
        assert timeout_response["status"] == "error"
        assert "TIMEOUT" in timeout_response["error"]["error_code"]
        
        # Verify session still functional after timeout
        recovery_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#immediate",
                "extract_type": "text"
            }
        )
        assert recovery_response["status"] == "success"
        
        await client.close_session(session_id)
        
    async def test_large_response_handling(self, integrated_setup):
        """Test handling of large responses through WebSocket."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create page with large content
        large_items = [f"<li>Item {i}: {' '.join(['data'] * 50)}</li>" for i in range(500)]
        large_content = f"<ul>{''.join(large_items)}</ul>"
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
        
        # Verify large content was transferred correctly
        assert len(extracted_html) > 100000  # Should be substantial
        assert "Item 0:" in extracted_html
        assert "Item 499:" in extracted_html
        
        # Test text extraction of large content
        text_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content",
                "extract_type": "text"
            }
        )
        
        assert text_response["status"] == "success"
        extracted_text = text_response["result"]["extracted_text"]
        assert len(extracted_text) > 50000
        assert "Item 0:" in extracted_text
        assert "Item 499:" in extracted_text
        
        await client.close_session(session_id)
        
    async def test_websocket_message_ordering(self, integrated_setup):
        """Test WebSocket message ordering with rapid commands."""
        setup = integrated_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='counter'>0</div>"
            }
        )
        
        # Send rapid sequence of commands
        command_ids = []
        tasks = []
        
        for i in range(10):
            # Each command updates a counter to track execution order
            command_id = f"cmd-{i}"
            command_ids.append(command_id)
            
            task = client.execute_command(
                session_id=session_id,
                command={
                    "command_id": command_id,
                    "method": "evaluate",
                    "script": f"document.getElementById('counter').textContent = '{i}'"
                }
            )
            tasks.append(task)
            
        # Wait for all commands to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all commands succeeded
        assert all(r["status"] == "success" for r in results)
        
        # Verify final state reflects last command
        final_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#counter",
                "extract_type": "text"
            }
        )
        
        assert final_response["status"] == "success"
        final_value = final_response["result"]["extracted_text"]
        assert final_value == "9"  # Last command should have executed
        
        await client.close_session(session_id)
        
    async def test_browser_crash_recovery(self, integrated_setup):
        """Test recovery from browser crashes."""
        setup = integrated_setup
        client = setup["client"]
        browser_manager = setup["browser_manager"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Execute normal command
        normal_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Normal Page</div>"
            }
        )
        assert normal_response["status"] == "success"
        
        # Simulate browser crash by closing the page
        session = browser_manager._sessions[session_id]
        await session.page.close()
        
        # Try to execute command on crashed session
        crash_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "div",
                "extract_type": "text"
            }
        )
        
        # Should get error response
        assert crash_response["status"] == "error"
        assert "SESSION_ERROR" in crash_response["error"]["error_code"]
        
        # Create new session to verify system recovery
        new_session_response = await client.create_session()
        assert new_session_response["status"] == "success"
        new_session_id = new_session_response["session_id"]
        
        # Verify new session works
        recovery_response = await client.execute_command(
            session_id=new_session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Recovery Page</div>"
            }
        )
        assert recovery_response["status"] == "success"
        
        await client.close_session(new_session_id)
        
    async def test_memory_cleanup_integration(self, integrated_setup):
        """Test memory cleanup across browser and WebSocket components."""
        setup = integrated_setup
        client = setup["client"]
        browser_manager = setup["browser_manager"]
        
        await client.connect()
        
        # Track initial state
        initial_session_count = len(browser_manager._sessions)
        
        # Create and use multiple sessions
        session_ids = []
        for i in range(5):
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            session_ids.append(session_id)
            
            # Use each session
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Session {i}</div>"
                }
            )
            
        # Verify sessions were created
        assert len(browser_manager._sessions) == initial_session_count + 5
        
        # Close sessions
        for session_id in session_ids:
            close_response = await client.close_session(session_id)
            assert close_response["status"] == "success"
            
        # Verify cleanup
        assert len(browser_manager._sessions) == initial_session_count
        
        # Verify all session resources were properly cleaned up
        for session_id in session_ids:
            assert session_id not in browser_manager._sessions
            
        # Test that system is still functional
        test_session_response = await client.create_session()
        assert test_session_response["status"] == "success"
        await client.close_session(test_session_response["session_id"])
