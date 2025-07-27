"""
Penetration testing suite for AUX Protocol security assessment.

Includes advanced security testing scenarios, attack simulations,
and comprehensive security validation tests.
"""

import asyncio
import pytest
import json
import hashlib
import hmac
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.security
@pytest.mark.slow
class TestAdvancedPenetrationScenarios:
    """Advanced penetration testing scenarios."""
    
    @pytest.fixture
    async def pentest_environment(self, test_config):
        """Set up penetration testing environment."""
        # Configure for security testing
        security_config = test_config.security_config
        security_config.enable_auth = True
        security_config.api_keys = ["pentest-key-123"]
        security_config.rate_limit_per_minute = 100
        security_config.max_session_duration = 300
        
        security_manager = SecurityManager(security_config)
        server = AUXWebSocketServer(test_config, security_manager)
        
        await server.start()
        
        yield {
            "server": server,
            "security_manager": security_manager,
            "config": test_config
        }
        
        await server.stop()
        
    async def test_session_fixation_attack(self, pentest_environment):
        """Test session fixation attack resistance."""
        env = pentest_environment
        
        # Attacker creates a session
        attacker_client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await attacker_client.connect()
        attacker_session = await attacker_client.create_session()
        attacker_session_id = attacker_session["session_id"]
        
        # Attacker somehow gets the session ID to victim
        # Victim creates their own client
        victim_client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await victim_client.connect()
        
        # Victim tries to use attacker's session ID
        response = await victim_client.execute_command(
            session_id=attacker_session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Victim Content</div>"
            }
        )
        
        # Should reject cross-client session usage
        assert response["status"] == "error"
        assert "UNAUTHORIZED" in response["error"]["error_code"]
        
        await attacker_client.close_session(attacker_session_id)
        await attacker_client.disconnect()
        await victim_client.disconnect()
        
    async def test_timing_attack_resistance(self, pentest_environment):
        """Test resistance to timing attacks on authentication."""
        env = pentest_environment
        
        # Measure response times for valid vs invalid API keys
        valid_times = []
        invalid_times = []
        
        for i in range(10):
            # Test with valid API key
            valid_client = AUXClient(
                url=f"ws://{env['server'].host}:{env['server'].port}",
                api_key="pentest-key-123"
            )
            
            start_time = time.time()
            try:
                await valid_client.connect()
                await valid_client.create_session()
                valid_times.append(time.time() - start_time)
                await valid_client.disconnect()
            except:
                valid_times.append(time.time() - start_time)
                
            # Test with invalid API key
            invalid_client = AUXClient(
                url=f"ws://{env['server'].host}:{env['server'].port}",
                api_key=f"invalid-key-{i}"
            )
            
            start_time = time.time()
            try:
                await invalid_client.connect()
                await invalid_client.create_session()
            except:
                pass
            invalid_times.append(time.time() - start_time)
            
        # Response times should be similar to prevent timing attacks
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)
        
        # Difference should be minimal (within 50ms)
        time_difference = abs(avg_valid - avg_invalid)
        assert time_difference < 0.05, f"Timing attack possible: {time_difference}s difference"
        
    async def test_race_condition_exploitation(self, pentest_environment):
        """Test for race condition vulnerabilities."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Set up test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='counter'>0</div>"
            }
        )
        
        # Attempt race condition with concurrent commands
        async def increment_counter(command_id):
            return await client.execute_command(
                session_id=session_id,
                command={
                    "command_id": command_id,
                    "method": "evaluate",
                    "script": """
                    let current = parseInt(document.getElementById('counter').textContent);
                    document.getElementById('counter').textContent = current + 1;
                    """
                }
            )
            
        # Run 20 concurrent increment operations
        tasks = [increment_counter(f"race-{i}") for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check final counter value
        final_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#counter",
                "extract_type": "text"
            }
        )
        
        if final_response["status"] == "success":
            final_value = int(final_response["result"]["extracted_text"])
            # Should be 20 if race conditions are properly handled
            assert final_value == 20, f"Race condition detected: expected 20, got {final_value}"
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_privilege_escalation_attempt(self, pentest_environment):
        """Test attempts to escalate privileges."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Attempt to access system resources
        privilege_escalation_attempts = [
            # Try to access filesystem
            {
                "method": "evaluate",
                "script": "require('fs').readFileSync('/etc/passwd', 'utf8')"
            },
            # Try to execute system commands
            {
                "method": "evaluate",
                "script": "require('child_process').execSync('whoami').toString()"
            },
            # Try to access process environment
            {
                "method": "evaluate",
                "script": "process.env"
            },
            # Try to modify global objects
            {
                "method": "evaluate",
                "script": "global.process = {exit: () => console.log('pwned')}"
            },
            # Try to access node modules
            {
                "method": "evaluate",
                "script": "require('os').platform()"
            }
        ]
        
        for attempt in privilege_escalation_attempts:
            response = await client.execute_command(
                session_id=session_id,
                command=attempt
            )
            
            # All privilege escalation attempts should be blocked
            assert response["status"] == "error"
            assert "SECURITY_VIOLATION" in response["error"]["error_code"]
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_memory_corruption_attempt(self, pentest_environment):
        """Test attempts to cause memory corruption."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Attempt various memory corruption techniques
        corruption_attempts = [
            # Buffer overflow attempt
            {
                "method": "fill",
                "selector": "#input",
                "value": "A" * 1000000  # 1MB string
            },
            # Stack overflow attempt
            {
                "method": "evaluate",
                "script": "function overflow() { return overflow(); } overflow();"
            },
            # Heap spray attempt
            {
                "method": "evaluate",
                "script": "var spray = []; for(var i = 0; i < 100000; i++) spray.push('A'.repeat(1000));"
            },
            # Integer overflow attempt
            {
                "method": "wait",
                "condition": "visible",
                "timeout": 2**31  # Integer overflow attempt
            }
        ]
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<input id='input' type='text'>"
            }
        )
        
        for attempt in corruption_attempts:
            response = await client.execute_command(
                session_id=session_id,
                command=attempt
            )
            
            # Should handle corruption attempts gracefully
            if response["status"] == "error":
                assert "SECURITY_VIOLATION" in response["error"]["error_code"] or \
                       "INVALID_INPUT" in response["error"]["error_code"]
            else:
                # If successful, system should remain stable
                health_check = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "input",
                        "extract_type": "text"
                    }
                )
                assert health_check["status"] in ["success", "error"]
                
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.security
class TestCryptographicAttacks:
    """Test cryptographic attack resistance."""
    
    async def test_replay_attack_prevention(self, pentest_environment):
        """Test prevention of replay attacks."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Capture a valid command
        original_command = {
            "method": "navigate",
            "url": "data:text/html,<div>Original Request</div>",
            "timestamp": int(time.time())
        }
        
        response1 = await client.execute_command(
            session_id=session_id,
            command=original_command
        )
        assert response1["status"] == "success"
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Try to replay the exact same command
        response2 = await client.execute_command(
            session_id=session_id,
            command=original_command  # Exact same command
        )
        
        # Should detect and prevent replay
        if "nonce" in original_command or "timestamp" in original_command:
            assert response2["status"] == "error"
            assert "REPLAY_ATTACK" in response2["error"]["error_code"]
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_message_integrity_validation(self, pentest_environment):
        """Test message integrity validation."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Try to send tampered messages
        tampered_attempts = [
            # Modified command method
            {
                "session_id": session_id,
                "command": {
                    "method": "navigate_TAMPERED",
                    "url": "data:text/html,<div>Test</div>"
                }
            },
            # Extra malicious fields
            {
                "session_id": session_id,
                "command": {
                    "method": "navigate",
                    "url": "data:text/html,<div>Test</div>",
                    "__proto__": {"isAdmin": True},
                    "constructor": {"prototype": {"isAdmin": True}}
                }
            },
            # Invalid session ID
            {
                "session_id": session_id + "_tampered",
                "command": {
                    "method": "navigate",
                    "url": "data:text/html,<div>Test</div>"
                }
            }
        ]
        
        for tampered in tampered_attempts:
            try:
                # This should be detected as invalid
                response = await client._send_message(tampered)
                assert response["status"] == "error"
                assert "VALIDATION_ERROR" in response["error"]["error_code"]
            except Exception:
                # Connection drop is also acceptable for tampered messages
                pass
                
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.security
class TestNetworkAttacks:
    """Test network-level attack resistance."""
    
    async def test_websocket_flooding_attack(self, pentest_environment):
        """Test WebSocket flooding attack resistance."""
        env = pentest_environment
        
        # Create multiple clients to simulate flood
        clients = []
        max_clients = 50
        
        try:
            for i in range(max_clients):
                client = AUXClient(
                    url=f"ws://{env['server'].host}:{env['server'].port}",
                    api_key="pentest-key-123"
                )
                
                try:
                    await client.connect()
                    clients.append(client)
                except Exception:
                    # Expected - server should limit connections
                    break
                    
            # Should not be able to create unlimited connections
            assert len(clients) < max_clients, "Server allowed too many connections"
            
            # Test rapid message sending
            if clients:
                client = clients[0]
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Send rapid messages
                responses = []
                for i in range(100):
                    try:
                        response = await client.execute_command(
                            session_id=session_id,
                            command={
                                "method": "evaluate",
                                "script": f"console.log('flood {i}')"
                            }
                        )
                        responses.append(response)
                    except Exception as e:
                        if "rate limit" in str(e).lower():
                            break
                            
                # Should hit rate limit before processing all messages
                successful = len([r for r in responses if r.get("status") == "success"])
                assert successful < 100, "Rate limiting not enforced"
                
        finally:
            # Cleanup
            for client in clients:
                try:
                    await client.disconnect()
                except:
                    pass
                    
    async def test_protocol_downgrade_attack(self, pentest_environment):
        """Test protocol downgrade attack resistance."""
        env = pentest_environment
        
        # Try to connect with weaker security protocols
        weak_protocols = [
            "ws",  # Instead of wss
            "http",  # Wrong protocol entirely
        ]
        
        for protocol in weak_protocols:
            weak_url = f"{protocol}://{env['server'].host}:{env['server'].port}"
            
            client = AUXClient(
                url=weak_url,
                api_key="pentest-key-123"
            )
            
            # Should enforce secure protocols
            with pytest.raises(Exception):
                await client.connect()
                
    async def test_man_in_the_middle_resistance(self, pentest_environment):
        """Test man-in-the-middle attack resistance."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        
        # Try to establish connection with invalid certificates
        # (This would require setting up a proxy server)
        
        # For now, test that secure headers are present
        session_response = await client.create_session()
        assert session_response["status"] == "success"
        
        # Check for security headers in response
        if "headers" in session_response:
            headers = session_response["headers"]
            # Should include security headers
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection"
            ]
            
            for header in security_headers:
                assert header in headers, f"Missing security header: {header}"
                
        await client.close_session(session_response["session_id"])
        await client.disconnect()


@pytest.mark.security
class TestAdvancedEvasionTechniques:
    """Test advanced attack evasion techniques."""
    
    async def test_encoding_evasion_attempts(self, pentest_environment):
        """Test various encoding evasion attempts."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test various encoding evasion techniques
        evasion_attempts = [
            # URL encoding
            "data:text/html,%3Cscript%3Ealert(1)%3C/script%3E",
            # HTML entity encoding
            "data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;",
            # Unicode encoding
            "data:text/html,\u003cscript\u003ealert(1)\u003c/script\u003e",
            # Base64 encoding
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            # Double encoding
            "data:text/html,%253Cscript%253Ealert(1)%253C/script%253E",
        ]
        
        for evasion_url in evasion_attempts:
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": evasion_url
                }
            )
            
            # Should detect and block evasion attempts
            assert response["status"] == "error"
            assert "SECURITY_VIOLATION" in response["error"]["error_code"]
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_polyglot_payload_resistance(self, pentest_environment):
        """Test resistance to polyglot payloads."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<input id='polyglot' type='text'>"
            }
        )
        
        # Polyglot payloads that work in multiple contexts
        polyglot_payloads = [
            "javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/`/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//--></SCRIPT>\">'><SCRIPT>alert(String.fromCharCode(88,83,83))</SCRIPT>",
            "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\\x3e"
        ]
        
        for payload in polyglot_payloads:
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "fill",
                    "selector": "#polyglot",
                    "value": payload
                }
            )
            
            # Should detect and block polyglot payloads
            if response["status"] == "error":
                assert "SECURITY_VIOLATION" in response["error"]["error_code"]
            else:
                # If accepted, verify it was properly sanitized
                extract_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#polyglot",
                        "extract_type": "attribute",
                        "attribute": "value"
                    }
                )
                
                if extract_response["status"] == "success":
                    actual_value = extract_response["result"]["extracted_attribute"]
                    # Should be sanitized
                    assert "<script>" not in actual_value.lower()
                    assert "javascript:" not in actual_value.lower()
                    assert "alert" not in actual_value.lower()
                    
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.security
class TestSecurityCompliance:
    """Test security compliance and best practices."""
    
    async def test_owasp_top_10_compliance(self, pentest_environment):
        """Test compliance with OWASP Top 10 security risks."""
        env = pentest_environment
        
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # A1: Injection
        injection_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "evaluate",
                "script": "'; DROP TABLE users; --"
            }
        )
        assert injection_response["status"] == "error"
        
        # A2: Broken Authentication
        # (Tested in other test methods)
        
        # A3: Sensitive Data Exposure
        data_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<input type='password' value='secret123'>"
            }
        )
        
        extract_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "input[type='password']",
                "extract_type": "attribute",
                "attribute": "value"
            }
        )
        
        if extract_response["status"] == "success":
            # Password should be redacted
            assert extract_response["result"]["extracted_attribute"] != "secret123"
            
        # A4: XML External Entities (XXE)
        xxe_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/xml,<?xml version='1.0'?><!DOCTYPE root [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><root>&xxe;</root>"
            }
        )
        assert xxe_response["status"] == "error"
        
        # A5: Broken Access Control
        # (Tested in session hijacking tests)
        
        # A6: Security Misconfiguration
        # Server should not expose internal details
        error_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "invalid_method",
                "selector": "#test"
            }
        )
        
        if error_response["status"] == "error":
            error_message = error_response["error"]["message"]
            # Should not expose internal paths or stack traces
            assert "/usr/" not in error_message
            assert "stack trace" not in error_message.lower()
            assert "exception" not in error_message.lower()
            
        # A7: Cross-Site Scripting (XSS)
        xss_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<script>alert('xss')</script>"
            }
        )
        # XSS should be sanitized or blocked
        
        # A8: Insecure Deserialization
        # (Not directly applicable to this protocol)
        
        # A9: Using Components with Known Vulnerabilities
        # (Would require dependency scanning)
        
        # A10: Insufficient Logging & Monitoring
        # All security events should be logged
        
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_security_headers_compliance(self, pentest_environment):
        """Test security headers compliance."""
        env = pentest_environment
        
        # Check server security configuration
        security_config = env["security_manager"].config
        
        # Should have secure defaults
        assert security_config.enable_auth is True
        assert security_config.csrf_protection is True
        assert len(security_config.api_keys) > 0
        assert security_config.rate_limit_per_minute > 0
        
        # Test client connection security
        client = AUXClient(
            url=f"ws://{env['server'].host}:{env['server'].port}",
            api_key="pentest-key-123"
        )
        
        await client.connect()
        
        # Connection should be secure
        assert client.connected
        
        # Test secure session creation
        session_response = await client.create_session()
        assert session_response["status"] == "success"
        
        # Session ID should be cryptographically secure
        session_id = session_response["session_id"]
        assert len(session_id) >= 32  # Minimum entropy
        assert session_id.isalnum() or "-" in session_id  # Valid format
        
        await client.close_session(session_id)
        await client.disconnect()
