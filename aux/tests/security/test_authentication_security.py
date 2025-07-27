"""
Security tests for authentication and authorization.

Tests API key security, session hijacking protection,
rate limiting bypass attempts, and privilege escalation.
"""

import asyncio
import json
import time
import hashlib
import hmac
import pytest
import websockets
from typing import Dict, Any, List
from unittest.mock import patch

from aux.server.websocket_server import AUXWebSocketServer
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.security
@pytest.mark.auth
class TestAuthenticationSecurity:
    """Security tests for authentication mechanisms."""

    @pytest.fixture
    async def auth_security_server(self, test_config: Config):
        """Provide server with strict authentication for testing."""
        security_manager = SecurityManager({
            "enable_auth": True,
            "rate_limit_per_minute": 10,  # Low limit for testing
            "max_session_duration": 300,  # 5 minutes
            "allowed_origins": ["http://localhost"],
            "max_failed_attempts": 3,
            "lockout_duration": 300,
            "require_https": False,  # For testing
            "api_key_length": 32,
        })
        
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        yield server
        await server.stop()

    async def test_missing_authentication(self, auth_security_server: AUXWebSocketServer):
        """Test access without authentication is denied."""
        uri = f"ws://localhost:{auth_security_server.port}"
        
        try:
            async with websockets.connect(uri) as websocket:
                command = {
                    "method": "navigate",
                    "url": "https://example.com"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                assert response["status"] == "error"
                assert "AUTHENTICATION_REQUIRED" in response["error"]["error_code"]
                
        except websockets.exceptions.ConnectionClosedError:
            # Server may close connection immediately
            pass

    async def test_invalid_api_key(self, auth_security_server: AUXWebSocketServer):
        """Test access with invalid API key is denied."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": "Bearer invalid-api-key-123"}
        
        try:
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                command = {
                    "method": "navigate",
                    "url": "https://example.com"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                assert response["status"] == "error"
                assert "INVALID_API_KEY" in response["error"]["error_code"] or \
                       "AUTHENTICATION_FAILED" in response["error"]["error_code"]
                
        except websockets.exceptions.ConnectionClosedError:
            # Server may close connection for invalid auth
            pass

    async def test_malformed_auth_header(self, auth_security_server: AUXWebSocketServer):
        """Test malformed authentication headers are rejected."""
        uri = f"ws://localhost:{auth_security_server.port}"
        
        malformed_headers = [
            {"Authorization": "invalid-format"},
            {"Authorization": "Bearer"},  # Missing key
            {"Authorization": "Basic dGVzdDp0ZXN0"},  # Wrong auth type
            {"Authorization": "Bearer " + "A" * 1000},  # Oversized key
            {"Authorization": "Bearer key with spaces"},  # Invalid characters
            {"Authorization": "Bearer key\x00with\x00nulls"},  # Null bytes
        ]
        
        for headers in malformed_headers:
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    command = {"method": "navigate", "url": "https://example.com"}
                    
                    await websocket.send(json.dumps(command))
                    response = json.loads(await websocket.recv())
                    
                    assert response["status"] == "error"
                    assert "AUTHENTICATION" in response["error"]["error_code"]
                    
            except websockets.exceptions.ConnectionClosedError:
                # Expected for malformed auth
                pass

    async def test_api_key_brute_force_protection(self, auth_security_server: AUXWebSocketServer):
        """Test protection against API key brute force attacks."""
        uri = f"ws://localhost:{auth_security_server.port}"
        
        # Attempt multiple invalid API keys rapidly
        for i in range(10):
            headers = {"Authorization": f"Bearer fake-key-{i:03d}"}
            
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    command = {"method": "navigate", "url": "https://example.com"}
                    
                    await websocket.send(json.dumps(command))
                    response = json.loads(await websocket.recv())
                    
                    # Should be blocked
                    assert response["status"] == "error"
                    
            except websockets.exceptions.ConnectionClosedError:
                # Expected behavior
                pass
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.1)

    async def test_session_hijacking_protection(
        self, 
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test protection against session hijacking."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Create a session
        async with websockets.connect(uri, extra_headers=headers) as websocket1:
            command = {"method": "navigate", "url": "data:text/html,<h1>Test</h1>"}
            
            await websocket1.send(json.dumps(command))
            response = json.loads(await websocket1.recv())
            session_id = response["session_id"]
        
        # Try to use session from different connection with different IP
        # (simulated by using different headers)
        hijack_headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Forwarded-For": "192.168.1.100",  # Different IP
            "User-Agent": "Different Browser"
        }
        
        async with websockets.connect(uri, extra_headers=hijack_headers) as websocket2:
            hijack_command = {
                "method": "click",
                "selector": "h1",
                "session_id": session_id  # Try to use hijacked session
            }
            
            await websocket2.send(json.dumps(hijack_command))
            response = json.loads(await websocket2.recv())
            
            # Should be blocked or create new session
            assert response["status"] == "error" or \
                   response.get("session_id") != session_id

    async def test_session_timeout_security(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test session timeout enforcement."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Create a session
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            command = {"method": "navigate", "url": "data:text/html,<h1>Test</h1>"}
            
            await websocket.send(json.dumps(command))
            response = json.loads(await websocket.recv())
            session_id = response["session_id"]
            
            # Wait for session to timeout (accelerated for testing)
            with patch("time.time", return_value=time.time() + 3600):  # 1 hour later
                expired_command = {
                    "method": "click",
                    "selector": "h1",
                    "session_id": session_id
                }
                
                await websocket.send(json.dumps(expired_command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked due to expired session
                assert response["status"] == "error"
                assert "SESSION_EXPIRED" in response["error"]["error_code"] or \
                       "INVALID_SESSION" in response["error"]["error_code"]

    async def test_rate_limiting_bypass_attempts(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test attempts to bypass rate limiting."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Attempt rapid requests to trigger rate limiting
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            blocked = False
            
            for i in range(20):  # Send more than rate limit
                command = {
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Test {i}</h1>"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                if response["status"] == "error" and "RATE_LIMIT" in response.get("error", {}).get("error_code", ""):
                    blocked = True
                    break
            
            # Should eventually be rate limited
            assert blocked

    async def test_concurrent_session_limit_bypass(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test attempts to bypass concurrent session limits."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Try to create many concurrent sessions
        connections = []
        session_ids = []
        
        try:
            for i in range(10):  # Try to create 10 concurrent sessions
                websocket = await websockets.connect(uri, extra_headers=headers)
                connections.append(websocket)
                
                command = {
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Session {i}</h1>"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                if response["status"] == "success":
                    session_ids.append(response["session_id"])
                else:
                    # Should eventually hit session limit
                    assert "SESSION_LIMIT" in response["error"]["error_code"] or \
                           "MAX_SESSIONS" in response["error"]["error_code"]
                    break
        
        finally:
            # Clean up connections
            for websocket in connections:
                await websocket.close()

    async def test_privilege_escalation_attempts(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test attempts to escalate privileges."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # Try admin-level commands (if any exist)
            escalation_attempts = [
                {"method": "admin_shutdown"},
                {"method": "admin_create_user", "username": "hacker", "admin": True},
                {"method": "admin_list_users"},
                {"method": "admin_access_logs"},
                {"method": "system_command", "command": "ls -la"},
                {"method": "debug_mode", "enabled": True},
            ]
            
            for command in escalation_attempts:
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"
                assert "UNAUTHORIZED" in response["error"]["error_code"] or \
                       "INVALID_COMMAND" in response["error"]["error_code"]

    async def test_token_manipulation_attacks(
        self,
        auth_security_server: AUXWebSocketServer
    ):
        """Test various token manipulation attacks."""
        uri = f"ws://localhost:{auth_security_server.port}"
        
        # Test various token manipulation techniques
        manipulated_tokens = [
            "Bearer " + "A" * 64,  # Valid length but fake
            "Bearer " + "a" * 64,  # Lowercase
            "Bearer " + "1" * 64,  # All numbers
            "Bearer " + "0" * 64,  # All zeros
            "Bearer " + "f" * 64,  # All 'f's
            "Bearer " + hashlib.sha256(b"predictable").hexdigest(),  # Predictable hash
        ]
        
        for token in manipulated_tokens:
            headers = {"Authorization": token}
            
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    command = {"method": "navigate", "url": "https://example.com"}
                    
                    await websocket.send(json.dumps(command))
                    response = json.loads(await websocket.recv())
                    
                    # Should be rejected
                    assert response["status"] == "error"
                    assert "AUTHENTICATION" in response["error"]["error_code"]
                    
            except websockets.exceptions.ConnectionClosedError:
                # Expected for invalid tokens
                pass

    async def test_timing_attack_on_authentication(
        self,
        auth_security_server: AUXWebSocketServer
    ):
        """Test timing attacks on authentication."""
        uri = f"ws://localhost:{auth_security_server.port}"
        
        # Test with various key lengths to detect timing differences
        test_keys = [
            "short",
            "medium_length_key",
            "very_long_key_that_might_cause_timing_differences" * 10,
            "A" * 32,  # Correct length
            "B" * 64,  # Double length
        ]
        
        timings = []
        
        for test_key in test_keys:
            headers = {"Authorization": f"Bearer {test_key}"}
            
            start_time = time.perf_counter()
            
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    command = {"method": "navigate", "url": "https://example.com"}
                    
                    await websocket.send(json.dumps(command))
                    response = json.loads(await websocket.recv())
                    
            except websockets.exceptions.ConnectionClosedError:
                pass
            
            end_time = time.perf_counter()
            timings.append(end_time - start_time)
        
        # Check that timing differences are not significant
        # (indicating constant-time comparison)
        avg_time = sum(timings) / len(timings)
        for timing in timings:
            # Allow reasonable variance
            assert abs(timing - avg_time) / avg_time < 2.0

    async def test_cross_session_data_leakage(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test for data leakage between sessions."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Session 1: Navigate and fill data
        async with websockets.connect(uri, extra_headers=headers) as websocket1:
            nav_command = {
                "method": "navigate",
                "url": "data:text/html,<input id='secret' type='password'>"
            }
            await websocket1.send(json.dumps(nav_command))
            nav_response = json.loads(await websocket1.recv())
            session1_id = nav_response["session_id"]
            
            fill_command = {
                "method": "fill",
                "selector": "#secret",
                "value": "secret_password_123",
                "session_id": session1_id
            }
            await websocket1.send(json.dumps(fill_command))
            await websocket1.recv()
        
        # Session 2: Try to access data from session 1
        async with websockets.connect(uri, extra_headers=headers) as websocket2:
            nav_command = {
                "method": "navigate", 
                "url": "data:text/html,<input id='secret' type='password'>"
            }
            await websocket2.send(json.dumps(nav_command))
            nav_response = json.loads(await websocket2.recv())
            session2_id = nav_response["session_id"]
            
            # Try to extract data (should not see session1's data)
            extract_command = {
                "method": "extract",
                "selector": "#secret",
                "extract_type": "property",
                "property": "value",
                "session_id": session2_id
            }
            await websocket2.send(json.dumps(extract_command))
            extract_response = json.loads(await websocket2.recv())
            
            # Should not contain session1's data
            assert extract_response["status"] == "success"
            assert extract_response["data"] != "secret_password_123"

    async def test_authentication_replay_attacks(
        self,
        auth_security_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test protection against replay attacks."""
        uri = f"ws://localhost:{auth_security_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Capture a valid request
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            original_command = {
                "method": "navigate",
                "url": "data:text/html,<h1>Original</h1>",
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(original_command))
            original_response = json.loads(await websocket.recv())
            
            # Try to replay the exact same command
            await websocket.send(json.dumps(original_command))
            replay_response = json.loads(await websocket.recv())
            
            # Should either be blocked or create new session
            # (depending on implementation)
            if "session_id" in replay_response:
                # If allowed, should get different session ID
                assert replay_response["session_id"] != original_response["session_id"]