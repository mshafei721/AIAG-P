"""
Integration tests for WebSocket Server + Browser Manager.

Tests the complete command flow from WebSocket message
reception through browser command execution and response.
"""

import asyncio
import json
import pytest
import websockets
from typing import Dict, Any
from unittest.mock import patch

from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.integration
@pytest.mark.browser
class TestWebSocketBrowserIntegration:
    """Integration tests for WebSocket server and browser manager."""

    @pytest.fixture
    async def integrated_server(self, test_config: Config, security_manager: SecurityManager):
        """Provide integrated server with browser manager."""
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    def valid_auth_headers(self, api_key: str) -> Dict[str, str]:
        """Provide valid authentication headers."""
        return {"Authorization": f"Bearer {api_key}"}

    async def test_complete_navigate_flow(
        self, 
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test complete navigate command flow."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Send navigate command
            command = {
                "method": "navigate",
                "url": test_websites["simple"],
                "wait_until": "load"
            }
            
            await websocket.send(json.dumps(command))
            response = json.loads(await websocket.recv())
            
            assert response["status"] == "success"
            assert "session_id" in response
            assert "timestamp" in response
            assert response["url"] == test_websites["simple"]

    async def test_complete_click_flow(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test complete click command flow."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # First navigate to a page with clickable elements
            navigate_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            
            await websocket.send(json.dumps(navigate_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # Then click the submit button
            click_command = {
                "method": "click",
                "selector": "button[type='submit']",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(click_command))
            click_response = json.loads(await websocket.recv())
            
            assert click_response["status"] == "success"
            assert click_response["session_id"] == session_id
            assert click_response["selector"] == "button[type='submit']"

    async def test_complete_fill_flow(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test complete fill command flow."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Navigate to form page
            navigate_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            
            await websocket.send(json.dumps(navigate_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # Fill the input field
            fill_command = {
                "method": "fill",
                "selector": "#test",
                "value": "integration test value",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(fill_command))
            fill_response = json.loads(await websocket.recv())
            
            assert fill_response["status"] == "success"
            assert fill_response["session_id"] == session_id
            assert fill_response["value"] == "integration test value"

    async def test_complete_extract_flow(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test complete extract command flow."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Navigate to simple page
            navigate_command = {
                "method": "navigate",
                "url": test_websites["simple"]
            }
            
            await websocket.send(json.dumps(navigate_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # Extract heading text
            extract_command = {
                "method": "extract",
                "selector": "h1",
                "extract_type": "text",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(extract_command))
            extract_response = json.loads(await websocket.recv())
            
            assert extract_response["status"] == "success"
            assert extract_response["session_id"] == session_id
            assert extract_response["data"] == "Simple Test"

    async def test_complete_wait_flow(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test complete wait command flow."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Navigate to page with delayed content
            navigate_command = {
                "method": "navigate",
                "url": test_websites["slow"]
            }
            
            await websocket.send(json.dumps(navigate_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # Wait for delayed element to appear
            wait_command = {
                "method": "wait",
                "condition": "visible",
                "selector": "#delayed",
                "timeout": 5000,
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(wait_command))
            wait_response = json.loads(await websocket.recv())
            
            assert wait_response["status"] == "success"
            assert wait_response["session_id"] == session_id
            assert wait_response["condition"] == "visible"

    async def test_multi_command_session_flow(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test multiple commands in single session."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # 1. Navigate
            navigate_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            
            await websocket.send(json.dumps(navigate_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # 2. Fill input
            fill_command = {
                "method": "fill",
                "selector": "#test",
                "value": "test data",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(fill_command))
            fill_response = json.loads(await websocket.recv())
            assert fill_response["status"] == "success"
            
            # 3. Extract filled value
            extract_command = {
                "method": "extract",
                "selector": "#test",
                "extract_type": "property",
                "property": "value",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(extract_command))
            extract_response = json.loads(await websocket.recv())
            assert extract_response["status"] == "success"
            assert extract_response["data"] == "test data"
            
            # 4. Click submit
            click_command = {
                "method": "click",
                "selector": "button[type='submit']",
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(click_command))
            click_response = json.loads(await websocket.recv())
            assert click_response["status"] == "success"
            
            # All commands should use the same session
            assert all(resp["session_id"] == session_id for resp in [
                nav_response, fill_response, extract_response, click_response
            ])

    async def test_error_handling_integration(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str]
    ):
        """Test error handling across the integration."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Send invalid command
            invalid_command = {
                "method": "invalid_method",
                "url": "https://example.com"
            }
            
            await websocket.send(json.dumps(invalid_command))
            response = json.loads(await websocket.recv())
            
            assert response["status"] == "error"
            assert "error" in response
            assert response["error"]["error_code"] == "INVALID_COMMAND"

    async def test_authentication_integration(
        self,
        integrated_server: AUXWebSocketServer
    ):
        """Test authentication integration."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        # Test without authentication
        try:
            async with websockets.connect(uri) as websocket:
                command = {
                    "method": "navigate",
                    "url": "https://example.com"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                assert response["status"] == "error"
                assert response["error"]["error_code"] == "AUTHENTICATION_REQUIRED"
        
        except websockets.exceptions.ConnectionClosedError:
            # Server may close connection immediately for unauthenticated requests
            pass

    async def test_rate_limiting_integration(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str]
    ):
        """Test rate limiting integration."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
            # Send many rapid requests to trigger rate limiting
            commands_sent = 0
            rate_limited = False
            
            for i in range(100):  # Send 100 rapid requests
                command = {
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Test {i}</h1>"
                }
                
                try:
                    await websocket.send(json.dumps(command))
                    response = json.loads(await websocket.recv())
                    commands_sent += 1
                    
                    if response["status"] == "error" and "RATE_LIMIT" in response.get("error", {}).get("error_code", ""):
                        rate_limited = True
                        break
                        
                except websockets.exceptions.ConnectionClosedError:
                    # Server may close connection due to rate limiting
                    rate_limited = True
                    break
            
            # Should eventually hit rate limit
            assert rate_limited or commands_sent < 100

    async def test_session_persistence_integration(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test session persistence across multiple connections."""
        uri = f"ws://localhost:{integrated_server.port}"
        session_id = None
        
        # First connection: create session and navigate
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket1:
            navigate_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            
            await websocket1.send(json.dumps(navigate_command))
            response = json.loads(await websocket1.recv())
            session_id = response["session_id"]
        
        # Second connection: use existing session
        async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket2:
            fill_command = {
                "method": "fill",
                "selector": "#test",
                "value": "persistent session test",
                "session_id": session_id
            }
            
            await websocket2.send(json.dumps(fill_command))
            response = json.loads(await websocket2.recv())
            
            # Session should still be valid
            assert response["status"] == "success"
            assert response["session_id"] == session_id

    async def test_concurrent_sessions_integration(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str],
        test_websites: Dict[str, str]
    ):
        """Test concurrent sessions don't interfere."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        async def session_workflow(session_num: int):
            """Individual session workflow."""
            async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
                # Navigate
                navigate_command = {
                    "method": "navigate",
                    "url": test_websites["form"]
                }
                
                await websocket.send(json.dumps(navigate_command))
                nav_response = json.loads(await websocket.recv())
                session_id = nav_response["session_id"]
                
                # Fill with session-specific data
                fill_command = {
                    "method": "fill",
                    "selector": "#test",
                    "value": f"session-{session_num}-data",
                    "session_id": session_id
                }
                
                await websocket.send(json.dumps(fill_command))
                fill_response = json.loads(await websocket.recv())
                
                # Extract to verify isolation
                extract_command = {
                    "method": "extract",
                    "selector": "#test",
                    "extract_type": "property",
                    "property": "value",
                    "session_id": session_id
                }
                
                await websocket.send(json.dumps(extract_command))
                extract_response = json.loads(await websocket.recv())
                
                return extract_response["data"]
        
        # Run 3 concurrent sessions
        tasks = [session_workflow(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Each session should have its own data
        expected_results = [f"session-{i}-data" for i in range(3)]
        assert sorted(results) == sorted(expected_results)

    async def test_browser_pool_integration(
        self,
        integrated_server: AUXWebSocketServer,
        valid_auth_headers: Dict[str, str]
    ):
        """Test browser pool management integration."""
        uri = f"ws://localhost:{integrated_server.port}"
        
        # Create multiple sessions to test pool management
        sessions = []
        
        for i in range(5):  # Create 5 sessions
            async with websockets.connect(uri, extra_headers=valid_auth_headers) as websocket:
                navigate_command = {
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Session {i}</h1>"
                }
                
                await websocket.send(json.dumps(navigate_command))
                response = json.loads(await websocket.recv())
                sessions.append(response["session_id"])
        
        # All sessions should be created successfully
        assert len(set(sessions)) == 5  # All unique session IDs