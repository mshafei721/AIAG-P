"""
Integration tests for Client SDK + Server.

Tests end-to-end communication using the client SDK
with the WebSocket server and browser manager.
"""

import asyncio
import pytest
from typing import Dict, Any

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.integration
@pytest.mark.network
class TestClientSDKIntegration:
    """Integration tests for client SDK with server."""

    @pytest.fixture
    async def server_with_sdk_client(
        self, 
        test_config: Config, 
        security_manager: SecurityManager,
        api_key: str
    ):
        """Provide server and connected client SDK."""
        # Start server
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        
        # Create and connect client
        client = AUXClient(
            url=f"ws://localhost:{server.port}",
            api_key=api_key
        )
        await client.connect()
        
        yield server, client
        
        # Cleanup
        await client.disconnect()
        await server.stop()

    async def test_sdk_navigate_command(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test navigate command via SDK."""
        server, client = server_with_sdk_client
        
        response = await client.navigate(
            url=test_websites["simple"],
            wait_until="load"
        )
        
        assert response.status == "success"
        assert response.url == test_websites["simple"]
        assert response.session_id is not None

    async def test_sdk_click_command(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test click command via SDK."""
        server, client = server_with_sdk_client
        
        # First navigate to a page with clickable elements
        nav_response = await client.navigate(test_websites["form"])
        session_id = nav_response.session_id
        
        # Then click the submit button
        click_response = await client.click(
            selector="button[type='submit']",
            session_id=session_id
        )
        
        assert click_response.status == "success"
        assert click_response.selector == "button[type='submit']"
        assert click_response.session_id == session_id

    async def test_sdk_fill_command(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test fill command via SDK."""
        server, client = server_with_sdk_client
        
        # Navigate to form page
        nav_response = await client.navigate(test_websites["form"])
        session_id = nav_response.session_id
        
        # Fill the input field
        fill_response = await client.fill(
            selector="#test",
            value="SDK integration test",
            session_id=session_id
        )
        
        assert fill_response.status == "success"
        assert fill_response.value == "SDK integration test"
        assert fill_response.session_id == session_id

    async def test_sdk_extract_command(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test extract command via SDK."""
        server, client = server_with_sdk_client
        
        # Navigate to simple page
        nav_response = await client.navigate(test_websites["simple"])
        session_id = nav_response.session_id
        
        # Extract heading text
        extract_response = await client.extract(
            selector="h1",
            extract_type="text",
            session_id=session_id
        )
        
        assert extract_response.status == "success"
        assert extract_response.data == "Simple Test"
        assert extract_response.session_id == session_id

    async def test_sdk_wait_command(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test wait command via SDK."""
        server, client = server_with_sdk_client
        
        # Navigate to page with delayed content
        nav_response = await client.navigate(test_websites["slow"])
        session_id = nav_response.session_id
        
        # Wait for delayed element
        wait_response = await client.wait(
            condition="visible",
            selector="#delayed",
            timeout=5000,
            session_id=session_id
        )
        
        assert wait_response.status == "success"
        assert wait_response.condition == "visible"
        assert wait_response.session_id == session_id

    async def test_sdk_command_chaining(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test chaining multiple commands via SDK."""
        server, client = server_with_sdk_client
        
        # 1. Navigate
        nav_response = await client.navigate(test_websites["form"])
        session_id = nav_response.session_id
        
        # 2. Fill input
        await client.fill(
            selector="#test",
            value="chained command test",
            session_id=session_id
        )
        
        # 3. Extract to verify
        extract_response = await client.extract(
            selector="#test",
            extract_type="property",
            property="value",
            session_id=session_id
        )
        
        assert extract_response.data == "chained command test"
        
        # 4. Click submit
        click_response = await client.click(
            selector="button[type='submit']",
            session_id=session_id
        )
        
        assert click_response.status == "success"

    async def test_sdk_session_management(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test session management via SDK."""
        server, client = server_with_sdk_client
        
        # Create first session
        response1 = await client.navigate(test_websites["simple"])
        session1 = response1.session_id
        
        # Create second session (should get different session ID)
        response2 = await client.navigate(test_websites["form"])
        session2 = response2.session_id
        
        assert session1 != session2
        
        # Use specific session
        fill_response = await client.fill(
            selector="#test",
            value="session test",
            session_id=session2
        )
        
        assert fill_response.session_id == session2

    async def test_sdk_error_handling(self, server_with_sdk_client):
        """Test error handling via SDK."""
        server, client = server_with_sdk_client
        
        # Try to click non-existent element
        response = await client.click(selector="#non-existent")
        
        assert response.status == "error"
        assert response.error.error_code == "ELEMENT_NOT_FOUND"

    async def test_sdk_timeout_handling(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test timeout handling via SDK."""
        server, client = server_with_sdk_client
        
        # Navigate first
        nav_response = await client.navigate(test_websites["simple"])
        session_id = nav_response.session_id
        
        # Try to wait for non-existent element with short timeout
        response = await client.wait(
            condition="visible",
            selector="#never-appears",
            timeout=1000,  # 1 second
            session_id=session_id
        )
        
        assert response.status == "error"
        assert response.error.error_code == "TIMEOUT"

    async def test_sdk_concurrent_requests(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test concurrent requests via SDK."""
        server, client = server_with_sdk_client
        
        async def navigate_task(url: str):
            """Individual navigate task."""
            return await client.navigate(url)
        
        # Send multiple concurrent navigate requests
        tasks = [
            navigate_task(test_websites["simple"]),
            navigate_task(test_websites["form"]),
            navigate_task(test_websites["javascript"])
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(resp.status == "success" for resp in responses)
        
        # Should get different session IDs
        session_ids = [resp.session_id for resp in responses]
        assert len(set(session_ids)) == len(session_ids)

    async def test_sdk_connection_resilience(
        self,
        test_config: Config,
        security_manager: SecurityManager,
        api_key: str,
        test_websites: Dict[str, str]
    ):
        """Test SDK connection resilience."""
        # Start server
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        
        # Create client with auto-reconnect
        client = AUXClient(
            url=f"ws://localhost:{server.port}",
            api_key=api_key,
            auto_reconnect=True,
            reconnect_delay=0.1
        )
        await client.connect()
        
        try:
            # Send command
            response1 = await client.navigate(test_websites["simple"])
            assert response1.status == "success"
            
            # Simulate server restart
            await server.stop()
            await asyncio.sleep(0.1)
            
            server = AUXWebSocketServer(
                config=test_config,
                security_manager=security_manager
            )
            await server.start()
            
            # Wait for reconnection
            await asyncio.sleep(0.5)
            
            # Send another command
            response2 = await client.navigate(test_websites["form"])
            assert response2.status == "success"
            
        finally:
            await client.disconnect()
            await server.stop()

    async def test_sdk_batch_commands(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test batch command execution via SDK."""
        server, client = server_with_sdk_client
        
        # Create batch of commands
        commands = [
            {"method": "navigate", "url": test_websites["form"]},
            {"method": "fill", "selector": "#test", "value": "batch test"},
            {"method": "extract", "selector": "#test", "extract_type": "property", "property": "value"},
            {"method": "click", "selector": "button[type='submit']"}
        ]
        
        responses = await client.execute_batch(commands)
        
        assert len(responses) == 4
        assert all(resp.status == "success" for resp in responses)
        
        # All should use the same session (created by first command)
        session_id = responses[0].session_id
        assert all(resp.session_id == session_id for resp in responses)
        
        # Verify extract result
        assert responses[2].data == "batch test"

    async def test_sdk_custom_headers(
        self,
        test_config: Config,
        security_manager: SecurityManager,
        api_key: str
    ):
        """Test SDK with custom headers."""
        # Start server
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        
        # Create client with custom headers
        client = AUXClient(
            url=f"ws://localhost:{server.port}",
            api_key=api_key,
            custom_headers={
                "User-Agent": "AUX-SDK-Test/1.0",
                "X-Client-Version": "1.0.0"
            }
        )
        
        try:
            await client.connect()
            
            # Should be able to send commands
            response = await client.navigate("data:text/html,<h1>Custom Headers Test</h1>")
            assert response.status == "success"
            
        finally:
            await client.disconnect()
            await server.stop()

    async def test_sdk_callback_handling(
        self,
        server_with_sdk_client,
        test_websites: Dict[str, str]
    ):
        """Test SDK callback handling for events."""
        server, client = server_with_sdk_client
        
        events = []
        
        def on_response(response):
            """Response callback."""
            events.append(("response", response))
        
        def on_error(error):
            """Error callback."""
            events.append(("error", error))
        
        # Set callbacks
        client.set_response_callback(on_response)
        client.set_error_callback(on_error)
        
        # Send command
        await client.navigate(test_websites["simple"])
        
        # Check that callback was called
        assert len(events) > 0
        assert events[0][0] == "response"
        assert events[0][1].status == "success"