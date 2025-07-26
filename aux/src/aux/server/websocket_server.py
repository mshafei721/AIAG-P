"""
WebSocket Server for AUX Protocol.

This module implements the main WebSocket server that handles client connections,
manages browser sessions, and processes AUX protocol commands with comprehensive
routing, session management, authentication, and error handling.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Set, Optional, Any, Callable
import websockets
from websockets.server import WebSocketServerProtocol
from pydantic import ValidationError

from ..schema.commands import (
    AnyCommand, AnyResponse, ErrorResponse,
    CommandMethod, validate_command, create_error_response, ErrorCodes,
    NavigateCommand, NavigateResponse,
    ClickCommand, ClickResponse, 
    FillCommand, FillResponse,
    ExtractCommand, ExtractResponse,
    WaitCommand, WaitResponse
)
from ..browser.manager import BrowserManager
from ..config import get_config, ServerConfig
from ..security import SecurityManager, SecureAuthenticator, RateLimiter
from ..logging_utils import init_session_logging, get_session_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClientSession:
    """Represents a client session with browser context."""
    
    def __init__(self, session_id: str, websocket: WebSocketServerProtocol, browser_session_id: str):
        self.session_id = session_id
        self.websocket = websocket
        self.browser_session_id = browser_session_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.command_count = 0
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()
        self.command_count += 1


class WebSocketServer:
    """
    AUX Protocol WebSocket Server.
    
    Provides comprehensive WebSocket-based command routing with session management,
    authentication, and structured error handling for browser automation.
    """
    
    def __init__(
        self, 
        config: Optional[ServerConfig] = None,
        host: Optional[str] = None, 
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        session_timeout_seconds: Optional[int] = None,
        browser_manager: Optional[BrowserManager] = None
    ):
        """
        Initialize the WebSocket server.
        
        Args:
            config: Server configuration object (takes precedence)
            host: Server host address
            port: Server port number
            api_key: Optional API key for authentication
            session_timeout_seconds: Session timeout in seconds
            browser_manager: Optional browser manager instance
        """
        # Use provided config or get global config
        if config is None:
            full_config = get_config()
            self.config = full_config.server
            self.security_config = full_config.security
            self.logging_config = full_config.logging
        else:
            self.config = config
            full_config = get_config()
            self.security_config = full_config.security
            self.logging_config = full_config.logging
            
        # Override with explicit parameters if provided
        self.host = host if host is not None else self.config.host
        self.port = port if port is not None else self.config.port
        self.api_key = api_key if api_key is not None else self.config.api_key
        self.session_timeout = session_timeout_seconds if session_timeout_seconds is not None else 3600
        
        # Browser manager
        self.browser_manager = browser_manager or BrowserManager()
        
        # Connection and session management
        self.clients: Set[WebSocketServerProtocol] = set()
        self.sessions: Dict[str, ClientSession] = {}
        self.websocket_to_session: Dict[WebSocketServerProtocol, str] = {}
        
        # Security components
        self.security_manager = SecurityManager(self.security_config)
        self.authenticator = SecureAuthenticator(self.api_key)
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.config.rate_limit_requests_per_minute
        )
        
        # Initialize session logging
        if self.logging_config.enable_session_log:
            init_session_logging(
                log_file_path=self.logging_config.session_log_path,
                max_file_size_mb=self.logging_config.max_log_file_size_mb
            )
        
        self.session_logger = get_session_logger()
        
        # Server instance
        self._server: Optional[websockets.WebSocketServer] = None
        
        # Command handlers
        self.command_handlers: Dict[CommandMethod, Callable] = {
            CommandMethod.NAVIGATE: self._handle_navigate,
            CommandMethod.CLICK: self._handle_click,
            CommandMethod.FILL: self._handle_fill,
            CommandMethod.EXTRACT: self._handle_extract,
            CommandMethod.WAIT: self._handle_wait,
        }
        
    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting AUX Protocol WebSocket server on {self.host}:{self.port}")
        
        # Initialize browser manager
        await self.browser_manager.initialize()
        
        # Configure security
        self.security_manager.configure_auth(self.api_key)
        self.security_manager.configure_rate_limiting(self.config.rate_limit_requests_per_minute)
        
        if self.config.enable_auth and self.api_key:
            logger.info("API key authentication enabled")
        elif not self.config.enable_auth:
            logger.warning("Authentication disabled - server is open to all connections")
        else:
            logger.warning("No API key provided - authentication disabled")
            
        self._server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout,
            max_size=self.config.max_message_size,
            max_queue=self.config.max_concurrent_connections
        )
        
        # Start session cleanup task
        asyncio.create_task(self._cleanup_sessions())
        
        logger.info("AUX Protocol WebSocket server started successfully")
        
    async def stop(self) -> None:
        """Stop the WebSocket server and cleanup resources."""
        logger.info("Stopping AUX Protocol WebSocket server...")
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            
        # Cleanup all sessions
        for session in list(self.sessions.values()):
            await self._cleanup_session(session.session_id)
            
        # Close browser manager
        await self.browser_manager.close()
            
        logger.info("AUX Protocol WebSocket server stopped")
            
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle a new client connection.
        
        Args:
            websocket: WebSocket connection
        """
        client_addr = websocket.remote_address
        client_ip = client_addr[0] if client_addr else "unknown"
        logger.info(f"New client connection from {client_addr}")
        
        # Check concurrent connection limit
        if len(self.clients) >= self.config.max_concurrent_connections:
            logger.warning(f"Connection limit exceeded, rejecting {client_ip}")
            await websocket.close(4001, "Connection limit exceeded")
            return
        
        self.clients.add(websocket)
        session_id = None
        
        try:
            # Wait for initial message with potential authentication
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Check rate limiting
                    if not self.rate_limiter.is_allowed(client_ip):
                        if self.session_logger:
                            self.session_logger.log_rate_limit_exceeded(client_ip, session_id)
                        
                        error_resp = create_error_response(
                            error_message="Rate limit exceeded",
                            error_code=ErrorCodes.INVALID_PARAMS,
                            error_type="rate_limit"
                        )
                        await websocket.send(error_resp.model_dump_json())
                        continue
                    
                    # Handle authentication if required
                    if self.config.enable_auth and not session_id:
                        if not self._authenticate_client(data, client_ip):
                            error_resp = create_error_response(
                                error_message="Authentication failed",
                                error_code=ErrorCodes.INVALID_PARAMS,
                                error_type="authentication"
                            )
                            await websocket.send(error_resp.model_dump_json())
                            break
                    
                    # Create session if not exists
                    if not session_id:
                        session_id = await self._create_session(websocket, client_ip)
                        logger.info(f"Created session {session_id} for client {client_addr}")
                    
                    # Process the command
                    await self._process_message(websocket, message, session_id, client_ip)
                    
                except json.JSONDecodeError:
                    error_resp = create_error_response(
                        error_message="Invalid JSON format",
                        error_code=ErrorCodes.INVALID_COMMAND,
                        error_type="parsing"
                    )
                    await websocket.send(error_resp.model_dump_json())
                    
                except Exception as e:
                    logger.error(f"Error processing message from {client_addr}: {e}")
                    error_resp = create_error_response(
                        error_message=f"Internal server error: {str(e)}",
                        error_code=ErrorCodes.UNKNOWN_ERROR,
                        error_type="internal"
                    )
                    await websocket.send(error_resp.model_dump_json())
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Unexpected error handling client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            if session_id:
                await self._cleanup_session(session_id)
                
    def _authenticate_client(self, data: Dict[str, Any], client_ip: str) -> bool:
        """
        Authenticate client using API key with secure comparison.
        
        Args:
            data: First message data which should contain auth info
            client_ip: Client IP address for logging
            
        Returns:
            True if authenticated, False otherwise
        """
        if not self.config.enable_auth:
            return True
            
        provided_key = data.get("api_key")
        authenticated = self.authenticator.authenticate(provided_key)
        
        if not authenticated and self.session_logger:
            self.session_logger.log_security_violation(
                "unknown", client_ip, "authentication_failure",
                f"Invalid API key provided: {provided_key[:8] if provided_key else 'None'}..."
            )
        
        return authenticated
        
    async def _create_session(self, websocket: WebSocketServerProtocol, client_ip: str) -> str:
        """
        Create a new client session.
        
        Args:
            websocket: Client WebSocket connection
            client_ip: Client IP address
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        # Create browser session
        browser_session_id = await self.browser_manager.create_session()
        
        session = ClientSession(session_id, websocket, browser_session_id)
        
        self.sessions[session_id] = session
        self.websocket_to_session[websocket] = session_id
        
        # Log session creation
        if self.session_logger:
            self.session_logger.log_session_start(session_id, client_ip)
        
        return session_id
        
    async def _cleanup_session(self, session_id: str) -> None:
        """
        Clean up a session and its resources.
        
        Args:
            session_id: Session to cleanup
        """
        if session_id not in self.sessions:
            return
            
        session = self.sessions[session_id]
        
        # Log session end
        if self.session_logger:
            self.session_logger.log_session_end(session_id, 
                command_count=session.command_count,
                duration=time.time() - session.created_at
            )
        
        # Cleanup browser session
        try:
            await self.browser_manager.close_session(session.browser_session_id)
            logger.info(f"Closed browser session {session.browser_session_id} for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing browser session for session {session_id}: {e}")
        
        # Remove from tracking
        del self.sessions[session_id]
        if session.websocket in self.websocket_to_session:
            del self.websocket_to_session[session.websocket]
            
        logger.info(f"Cleaned up session {session_id}")
        
    async def _cleanup_sessions(self) -> None:
        """Periodic cleanup of expired sessions."""
        while True:
            try:
                current_time = time.time()
                expired_sessions = []
                
                for session_id, session in self.sessions.items():
                    if current_time - session.last_activity > self.session_timeout:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    logger.info(f"Session {session_id} expired, cleaning up")
                    await self._cleanup_session(session_id)
                    
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)
                
    async def _process_message(
        self, 
        websocket: WebSocketServerProtocol, 
        message: str, 
        session_id: str,
        client_ip: str
    ) -> None:
        """
        Process an incoming command message.
        
        Args:
            websocket: Client WebSocket connection
            message: JSON message string
            session_id: Client session ID
            client_ip: Client IP address
        """
        start_time = time.time()
        command_id = None
        
        try:
            # Parse message
            data = json.loads(message)
            command_id = data.get("id")
            method = data.get("method", "unknown")
            
            # Log incoming command
            logger.info(f"Processing command {command_id} from session {session_id}: {method}")
            
            # Security validation
            try:
                self.security_manager.validate_command_security(data)
            except ValueError as e:
                if self.session_logger:
                    self.session_logger.log_security_violation(
                        session_id, client_ip, "input_validation", str(e), command_id
                    )
                
                error_resp = create_error_response(
                    command_id=command_id,
                    error_message=f"Security validation failed: {str(e)}",
                    error_code=ErrorCodes.INVALID_PARAMS,
                    error_type="security"
                )
                await websocket.send(error_resp.model_dump_json())
                return
            
            # Log command received in session log
            if self.session_logger:
                self.session_logger.log_command_received(
                    session_id, command_id, method, data, client_ip
                )
            
            # Validate command structure
            if "method" not in data:
                raise ValueError("Missing 'method' field in command")
                
            # Validate and parse command
            command = validate_command(data["method"], data)
            
            # Update session activity
            if session_id in self.sessions:
                self.sessions[session_id].update_activity()
            
            # Execute command
            response = await self._execute_command(command, session_id)
            
            # Add execution timing
            execution_time = int((time.time() - start_time) * 1000)
            if hasattr(response, 'execution_time_ms'):
                response.execution_time_ms = execution_time
            
            # Log successful execution
            if self.session_logger and hasattr(response, 'success') and response.success:
                self.session_logger.log_command_executed(
                    session_id, command_id, method, execution_time,
                    response.model_dump() if hasattr(response, 'model_dump') else {}
                )
            elif self.session_logger and hasattr(response, 'success') and not response.success:
                self.session_logger.log_command_failed(
                    session_id, command_id, method, 
                    getattr(response, 'error', 'Unknown error'),
                    getattr(response, 'error_code', 'UNKNOWN'),
                    execution_time
                )
            
            # Send response
            await websocket.send(response.model_dump_json())
            
            logger.info(f"Command {command_id} completed in {execution_time}ms")
            
        except ValidationError as e:
            error_resp = create_error_response(
                command_id=command_id,
                error_message=f"Command validation failed: {str(e)}",
                error_code=ErrorCodes.INVALID_PARAMS,
                error_type="validation",
                details={"validation_errors": e.errors()}
            )
            
            # Log validation failure
            if self.session_logger:
                self.session_logger.log_command_failed(
                    session_id, command_id, data.get('method', 'unknown'),
                    error_resp.error, error_resp.error_code,
                    int((time.time() - start_time) * 1000)
                )
            
            await websocket.send(error_resp.model_dump_json())
            
        except ValueError as e:
            error_resp = create_error_response(
                command_id=command_id,
                error_message=str(e),
                error_code=ErrorCodes.INVALID_COMMAND,
                error_type="command_error"
            )
            
            # Log command error
            if self.session_logger:
                self.session_logger.log_command_failed(
                    session_id, command_id, data.get('method', 'unknown'),
                    error_resp.error, error_resp.error_code,
                    int((time.time() - start_time) * 1000)
                )
            
            await websocket.send(error_resp.model_dump_json())
            
        except Exception as e:
            logger.error(f"Error executing command {command_id}: {e}")
            error_resp = create_error_response(
                command_id=command_id,
                error_message=f"Command execution failed: {str(e)}",
                error_code=ErrorCodes.UNKNOWN_ERROR,
                error_type="execution"
            )
            
            # Log execution error
            if self.session_logger:
                self.session_logger.log_command_failed(
                    session_id, command_id, data.get('method', 'unknown'),
                    error_resp.error, error_resp.error_code,
                    int((time.time() - start_time) * 1000)
                )
            
            await websocket.send(error_resp.model_dump_json())
            
    async def _execute_command(self, command: AnyCommand, session_id: str) -> AnyResponse:
        """
        Execute a validated command.
        
        Args:
            command: Validated command instance
            session_id: Client session ID
            
        Returns:
            Command response
        """
        # Verify session exists
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
            
        # Route to appropriate handler
        handler = self.command_handlers.get(command.method)
        if not handler:
            raise ValueError(f"No handler for command method: {command.method}")
            
        return await handler(command, session_id)
        
    # Command Handlers - Integrated with Browser Manager
    
    async def _handle_navigate(self, command: NavigateCommand, session_id: str) -> AnyResponse:
        """Handle navigate command using browser manager."""
        session = self.sessions.get(session_id)
        if not session:
            return create_error_response(
                command.id, f"Session {session_id} not found", 
                ErrorCodes.SESSION_NOT_FOUND, "session_error"
            )
            
        # Update command to use browser session ID
        browser_command = NavigateCommand(
            id=command.id,
            method=command.method,
            session_id=session.browser_session_id,
            timeout=command.timeout,
            url=command.url,
            wait_until=command.wait_until,
            referer=command.referer
        )
        
        return await self.browser_manager.execute_navigate(browser_command)
        
    async def _handle_click(self, command: ClickCommand, session_id: str) -> AnyResponse:
        """Handle click command using browser manager."""
        session = self.sessions.get(session_id)
        if not session:
            return create_error_response(
                command.id, f"Session {session_id} not found", 
                ErrorCodes.SESSION_NOT_FOUND, "session_error"
            )
            
        # Update command to use browser session ID
        browser_command = ClickCommand(
            id=command.id,
            method=command.method,
            session_id=session.browser_session_id,
            timeout=command.timeout,
            selector=command.selector,
            button=command.button,
            click_count=command.click_count,
            force=command.force,
            position=command.position
        )
        
        return await self.browser_manager.execute_click(browser_command)
        
    async def _handle_fill(self, command: FillCommand, session_id: str) -> AnyResponse:
        """Handle fill command using browser manager."""
        session = self.sessions.get(session_id)
        if not session:
            return create_error_response(
                command.id, f"Session {session_id} not found", 
                ErrorCodes.SESSION_NOT_FOUND, "session_error"
            )
            
        # Update command to use browser session ID
        browser_command = FillCommand(
            id=command.id,
            method=command.method,
            session_id=session.browser_session_id,
            timeout=command.timeout,
            selector=command.selector,
            text=command.text,
            clear_first=command.clear_first,
            press_enter=command.press_enter,
            typing_delay_ms=command.typing_delay_ms,
            validate_input=command.validate_input
        )
        
        return await self.browser_manager.execute_fill(browser_command)
        
    async def _handle_extract(self, command: ExtractCommand, session_id: str) -> AnyResponse:
        """Handle extract command using browser manager."""
        session = self.sessions.get(session_id)
        if not session:
            return create_error_response(
                command.id, f"Session {session_id} not found", 
                ErrorCodes.SESSION_NOT_FOUND, "session_error"
            )
            
        # Update command to use browser session ID
        browser_command = ExtractCommand(
            id=command.id,
            method=command.method,
            session_id=session.browser_session_id,
            timeout=command.timeout,
            selector=command.selector,
            extract_type=command.extract_type,
            attribute_name=command.attribute_name,
            property_name=command.property_name,
            multiple=command.multiple,
            trim_whitespace=command.trim_whitespace
        )
        
        return await self.browser_manager.execute_extract(browser_command)
        
    async def _handle_wait(self, command: WaitCommand, session_id: str) -> AnyResponse:
        """Handle wait command using browser manager."""
        session = self.sessions.get(session_id)
        if not session:
            return create_error_response(
                command.id, f"Session {session_id} not found", 
                ErrorCodes.SESSION_NOT_FOUND, "session_error"
            )
            
        # Update command to use browser session ID
        browser_command = WaitCommand(
            id=command.id,
            method=command.method,
            session_id=session.browser_session_id,
            timeout=command.timeout,
            selector=command.selector,
            condition=command.condition,
            text_content=command.text_content,
            attribute_value=command.attribute_value,
            custom_js=command.custom_js,
            poll_interval_ms=command.poll_interval_ms
        )
        
        return await self.browser_manager.execute_wait(browser_command)


def main() -> None:
    """Main entry point for the AUX server."""
    import argparse
    import os
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AUX Protocol WebSocket Server")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--api-key", help="API key for authentication (optional)")
    parser.add_argument("--session-timeout", type=int, default=3600, 
                       help="Session timeout in seconds (default: 3600)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Log level (default: INFO)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get API key from environment if not provided
    api_key = args.api_key or os.getenv("AUX_API_KEY")
    
    # Create server instance
    server = WebSocketServer(
        host=args.host,
        port=args.port,
        api_key=api_key,
        session_timeout_seconds=args.session_timeout
    )
    
    async def run_server():
        """Run the WebSocket server with proper lifecycle management."""
        try:
            await server.start()
            logger.info("Server is running. Press Ctrl+C to stop.")
            
            # Keep server running
            await asyncio.Future()  # Run forever
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await server.stop()
    
    # Run the server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shutdown complete")


def create_test_server(host: str = "localhost", port: int = 8080) -> WebSocketServer:
    """
    Create a test server instance for development and testing.
    
    Args:
        host: Server host
        port: Server port
        
    Returns:
        WebSocketServer instance
    """
    return WebSocketServer(host=host, port=port, api_key=None)


async def run_test_server(host: str = "localhost", port: int = 8080):
    """
    Run a test server for development and testing.
    
    Args:
        host: Server host
        port: Server port
    """
    server = create_test_server(host, port)
    
    try:
        await server.start()
        logger.info(f"Test server running on {host}:{port}")
        logger.info("Send WebSocket commands to test the server")
        logger.info("Example command: {'id': '1', 'method': 'navigate', 'session_id': 'test', 'url': 'https://example.com'}")
        
        # Keep running
        await asyncio.Future()
        
    except KeyboardInterrupt:
        logger.info("Stopping test server...")
    finally:
        await server.stop()


if __name__ == "__main__":
    main()