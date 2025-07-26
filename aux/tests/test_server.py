"""
Tests for AUX Protocol WebSocket Server.

This module contains unit tests for the WebSocket server functionality
including connection handling, command processing, and error handling.
"""

import asyncio
import json
import pytest
import websockets
from unittest.mock import AsyncMock, MagicMock, patch

from aux.server.websocket_server import WebSocketServer
from aux.schema.commands import Command, Response, ErrorResponse


class TestWebSocketServer:
    """Test cases for WebSocket server functionality."""
    
    @pytest.fixture
    async def server(self):
        """Create a test server instance."""
        server = WebSocketServer(host="localhost", port=0)  # Use random port
        yield server
        if server._server:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.host == "localhost"
        assert server.port == 0
        assert len(server.clients) == 0
        assert len(server.sessions) == 0
        assert server.browser_manager is not None
        assert server._server is None
    
    @pytest.mark.asyncio
    async def test_server_start_stop(self, server):
        """Test server start and stop functionality."""
        # Test start
        await server.start()
        assert server._server is not None
        
        # Test stop
        await server.stop()
        # Server should be closed after stop
    
    @pytest.mark.asyncio
    async def test_command_processing(self, server):
        """Test command processing functionality."""
        # Create test command
        command = Command(
            id="test-123",
            method="test_method",
            params={"param1": "value1"}
        )
        
        # Process command
        response = await server.execute_command(command)
        
        # Verify response
        assert isinstance(response, Response)
        assert response.id == command.id
        assert response.result["status"] == "not_implemented"
        assert response.result["command"] == "test_method"
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, server):
        """Test handling of invalid JSON messages."""
        # Mock websocket
        mock_websocket = AsyncMock()
        
        # Process invalid JSON
        await server.process_message(mock_websocket, "invalid json")
        
        # Verify error response was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert "error" in sent_message
        assert sent_message["error"] == "Invalid JSON format"
    
    @pytest.mark.asyncio
    async def test_client_connection_handling(self, server):
        """Test client connection and disconnection handling."""
        # Mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)
        
        # Mock websocket to raise ConnectionClosed
        mock_websocket.__aiter__.return_value = iter([])
        
        # Handle client connection
        await server.handle_client(mock_websocket, "/")
        
        # Verify client was handled (would be added and removed from clients set)
        assert mock_websocket not in server.clients
    
    def test_main_function_import(self):
        """Test that main function can be imported."""
        from aux.server.websocket_server import main
        assert callable(main)