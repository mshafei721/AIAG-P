"""
AUX Protocol Client SDK.

This module provides a Python SDK for connecting to AUX protocol servers
and performing browser automation tasks.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Any, Dict, List
import websockets
from websockets.client import WebSocketClientProtocol

from ..schema.commands import (
    AnyCommand, AnyResponse, ErrorResponse, CommandMethod,
    NavigateCommand, ClickCommand, FillCommand, ExtractCommand, WaitCommand,
    validate_command
)

logger = logging.getLogger(__name__)


class AUXSession:
    """
    Represents a browser session from the client side.
    
    Provides high-level methods for browser automation within
    a specific session context.
    """
    
    def __init__(self, session_id: str, client: "AUXClient"):
        """
        Initialize an AUX session.
        
        Args:
            session_id: Server-side session identifier
            client: Parent AUX client instance
        """
        self.session_id = session_id
        self.client = client
        
    async def navigate(self, url: str, wait_until: str = "load") -> Dict[str, Any]:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: Condition to wait for after navigation
            
        Returns:
            Navigation result
        """
        command = NavigateCommand(
            id=str(uuid.uuid4()),
            session_id=self.session_id,
            url=url,
            wait_until=wait_until
        )
        return await self.client.send_command(command)
        
    async def click(self, selector: str, button: str = "left") -> Dict[str, Any]:
        """
        Click an element by selector.
        
        Args:
            selector: CSS selector for the element
            button: Mouse button to use
            
        Returns:
            Click result
        """
        command = ClickCommand(
            id=str(uuid.uuid4()),
            session_id=self.session_id,
            selector=selector,
            button=button
        )
        return await self.client.send_command(command)
        
    async def type_text(self, selector: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """
        Type text into an input element.
        
        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear_first: Clear existing content before filling
            
        Returns:
            Fill result
        """
        command = FillCommand(
            id=str(uuid.uuid4()),
            session_id=self.session_id,
            selector=selector,
            text=text,
            clear_first=clear_first
        )
        return await self.client.send_command(command)
        
    async def get_text(self, selector: str) -> str:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            Element text content
        """
        command = ExtractCommand(
            id=str(uuid.uuid4()),
            session_id=self.session_id,
            selector=selector,
            extract_type="text"
        )
        result = await self.client.send_command(command)
        return result.get("data", "")
        
    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Take a screenshot.
        
        Args:
            path: Optional file path to save screenshot
            
        Returns:
            Screenshot result
        """
        # Screenshot command not implemented in current schema
        raise NotImplementedError("Screenshot command not yet implemented")
        
    async def close(self) -> Dict[str, Any]:
        """
        Close the session.
        
        Returns:
            Close result
        """
        # Session management commands not implemented in current schema
        raise NotImplementedError("Session close command not yet implemented")


class AUXClient:
    """
    AUX Protocol Client SDK.
    
    Provides a high-level interface for connecting to AUX protocol servers
    and performing browser automation tasks.
    """
    
    def __init__(self, server_url: str):
        """
        Initialize the AUX client.
        
        Args:
            server_url: WebSocket URL of the AUX server
        """
        self.server_url = server_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
    async def connect(self) -> None:
        """Connect to the AUX server."""
        logger.info(f"Connecting to AUX server: {self.server_url}")
        
        self.websocket = await websockets.connect(self.server_url)
        self.connected = True
        
        # Start message handler task
        asyncio.create_task(self._handle_messages())
        
        logger.info("Connected to AUX server successfully")
        
    async def disconnect(self) -> None:
        """Disconnect from the AUX server."""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from AUX server")
            
    async def _handle_messages(self) -> None:
        """Handle incoming messages from the server."""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logger.info("Connection to AUX server closed")
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            self.connected = False
            
    async def _process_message(self, message: str) -> None:
        """
        Process an incoming message from the server.
        
        Args:
            message: JSON message string
        """
        try:
            data = json.loads(message)
            
            # Handle responses to pending requests
            if "id" in data and data["id"] in self.pending_requests:
                future = self.pending_requests.pop(data["id"])
                
                if "error" in data:
                    future.set_exception(Exception(data["error"]))
                else:
                    future.set_result(data.get("result", {}))
                    
        except json.JSONDecodeError:
            logger.error("Received invalid JSON from server")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    async def send_command(self, command: AnyCommand) -> Dict[str, Any]:
        """
        Send a command to the server and wait for response.
        
        Args:
            command: Command instance to send
            
        Returns:
            Command result
            
        Raises:
            Exception: If command fails or connection is lost
        """
        if not self.connected:
            raise Exception("Not connected to AUX server")
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[command.id] = future
        
        # Send command
        await self.websocket.send(command.model_dump_json())
        
        try:
            # Wait for response
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(command.id, None)
            raise Exception(f"Command {command.method} timed out")
        except Exception:
            self.pending_requests.pop(command.id, None)
            raise
            
    async def create_session(self, config: Optional[Dict[str, Any]] = None) -> AUXSession:
        """
        Create a new browser session.
        
        Args:
            config: Optional session configuration
            
        Returns:
            AUX session instance
        """
        # For now, just create a session ID locally since session management
        # commands are not implemented in the current schema
        session_id = str(uuid.uuid4())
        return AUXSession(session_id, self)
        
    async def list_sessions(self) -> List[str]:
        """
        Get list of active sessions.
        
        Returns:
            List of session IDs
        """
        # Session listing not implemented in current schema
        raise NotImplementedError("Session listing not yet implemented")
        
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the server.
        
        Returns:
            Server health status
        """
        # Health check not implemented in current schema
        raise NotImplementedError("Health check not yet implemented")