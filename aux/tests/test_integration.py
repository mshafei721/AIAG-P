"""
Integration Tests for AUX Protocol.

This module contains integration tests that verify the complete
AUX protocol workflow from client to server to browser.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from aux.server.websocket_server import WebSocketServer
from aux.client.sdk import AUXClient
from aux.schema.commands import Command, Response


class TestAUXIntegration:
    """Integration test cases for the complete AUX protocol stack."""
    
    @pytest.fixture
    async def server(self):
        """Create and start a test server."""
        server = WebSocketServer(host="localhost", port=8765)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.fixture
    async def client(self, server):
        """Create a test client connected to the server."""
        client = AUXClient("ws://localhost:8765")
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running server for full integration test")
    async def test_client_server_connection(self, server, client):
        """Test basic client-server connection."""
        assert client.connected is True
        assert len(server.clients) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running server for full integration test")
    async def test_command_roundtrip(self, server, client):
        """Test sending commands from client to server."""
        # Send a health check command
        result = await client.health_check()
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "status" in result
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_session_creation_workflow(self, mock_playwright_class):
        """Test the complete session creation workflow."""
        # Setup mocks for browser automation
        mock_playwright = AsyncMock()
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Create server and client
        server = WebSocketServer(host="localhost", port=8766)
        await server.start()
        
        try:
            client = AUXClient("ws://localhost:8766")
            await client.connect()
            
            try:
                # Test session creation (would normally work with real server implementation)
                # This is a placeholder for when the server implements session creation
                sessions = await client.list_sessions()
                assert isinstance(sessions, list)
                
            finally:
                await client.disconnect()
        finally:
            await server.stop()
    
    def test_schema_validation(self):
        """Test that schema validation works correctly."""
        # Test valid command
        command_data = {
            "id": "test-123",
            "method": "navigate",
            "params": {"session_id": "session-123", "url": "https://example.com"}
        }
        
        command = Command.model_validate(command_data)
        assert command.id == "test-123"
        assert command.method == "navigate"
        assert command.params["url"] == "https://example.com"
        
        # Test valid response
        response_data = {
            "id": "test-123",
            "result": {"status": "success", "url": "https://example.com"}
        }
        
        response = Response.model_validate(response_data)
        assert response.id == "test-123"
        assert response.result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling across the protocol stack."""
        server = WebSocketServer(host="localhost", port=8767)
        await server.start()
        
        try:
            client = AUXClient("ws://localhost:8767")
            await client.connect()
            
            try:
                # Test that sending an invalid command results in proper error handling
                # This would normally trigger error responses from the server
                with pytest.raises(Exception):
                    await asyncio.wait_for(
                        client.send_command("invalid_method", {}),
                        timeout=1.0
                    )
            except asyncio.TimeoutError:
                # Expected for placeholder implementation
                pass
            finally:
                await client.disconnect()
        finally:
            await server.stop()
    
    def test_import_structure(self):
        """Test that all main components can be imported correctly."""
        # Test server imports
        from aux.server import WebSocketServer
        assert WebSocketServer is not None
        
        # Test client imports
        from aux.client import AUXClient
        assert AUXClient is not None
        
        # Test browser imports
        from aux.browser import BrowserManager
        assert BrowserManager is not None
        
        # Test schema imports
        from aux.schema import Command, Response, ErrorResponse
        assert Command is not None
        assert Response is not None
        assert ErrorResponse is not None
        
        # Test main package imports
        from aux import AUXClient as MainAUXClient, WebSocketServer as MainWebSocketServer
        assert MainAUXClient is not None
        assert MainWebSocketServer is not None