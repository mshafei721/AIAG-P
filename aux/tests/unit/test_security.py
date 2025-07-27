"""
Unit tests for security components.

Tests input sanitization, authentication, rate limiting,
session security, and attack prevention mechanisms.
"""

import time
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from aux.security import (
    SecurityManager, InputSanitizer, AuthenticationManager, 
    RateLimiter, SessionSecurity
)
from aux.config import Config


@pytest.mark.unit
class TestInputSanitizer:
    """Test cases for input sanitization."""

    @pytest.fixture
    def sanitizer(self) -> InputSanitizer:
        """Provide InputSanitizer instance for testing."""
        return InputSanitizer()

    @pytest.mark.parametrize("malicious_input", [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "onload=alert('xss')",
        "eval('malicious')",
        "Function('alert(1)')()",
        "setTimeout('alert(1)', 0)",
        "document.location='evil.com'",
        "window.open('evil.com')",
    ])
    def test_javascript_injection_detection(self, sanitizer: InputSanitizer, malicious_input: str):
        """Test detection of JavaScript injection attempts."""
        with pytest.raises(ValueError, match="Malicious JavaScript pattern detected"):
            sanitizer.sanitize_input(malicious_input)

    @pytest.mark.parametrize("malicious_selector", [
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "expression(alert('xss'))",
        "url('javascript:alert(1)')",
    ])
    def test_css_injection_detection(self, sanitizer: InputSanitizer, malicious_selector: str):
        """Test detection of CSS injection attempts."""
        with pytest.raises(ValueError, match="Malicious CSS pattern detected"):
            sanitizer.validate_selector(malicious_selector)

    @pytest.mark.parametrize("sql_injection", [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM passwords --",
        "1; DELETE FROM sessions WHERE 1=1 --",
    ])
    def test_sql_injection_detection(self, sanitizer: InputSanitizer, sql_injection: str):
        """Test detection of SQL injection attempts."""
        with pytest.raises(ValueError, match="Potential SQL injection detected"):
            sanitizer.sanitize_input(sql_injection)

    @pytest.mark.parametrize("path_traversal", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
        "....//....//....//etc/passwd",
    ])
    def test_path_traversal_detection(self, sanitizer: InputSanitizer, path_traversal: str):
        """Test detection of path traversal attempts."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            sanitizer.validate_url(f"file://{path_traversal}")

    def test_oversized_input_rejection(self, sanitizer: InputSanitizer):
        """Test rejection of oversized inputs."""
        oversized_input = "A" * (sanitizer.MAX_INPUT_LENGTH + 1)
        
        with pytest.raises(ValueError, match="Input exceeds maximum length"):
            sanitizer.sanitize_input(oversized_input)

    @pytest.mark.parametrize("safe_input", [
        "normal text input",
        "user@example.com",
        "Valid CSS Selector #id.class",
        "https://legitimate-site.com",
        "Special chars: !@#$%^&*()",
    ])
    def test_safe_input_acceptance(self, sanitizer: InputSanitizer, safe_input: str):
        """Test acceptance of safe inputs."""
        # Should not raise any exceptions
        result = sanitizer.sanitize_input(safe_input)
        assert result == safe_input

    def test_url_validation_allowed_schemes(self, sanitizer: InputSanitizer):
        """Test URL validation with allowed schemes."""
        valid_urls = [
            "https://example.com",
            "http://localhost:8080",
            "data:text/html,<h1>Test</h1>",
            "about:blank",
        ]
        
        for url in valid_urls:
            # Should not raise exceptions
            sanitizer.validate_url(url)

    def test_url_validation_blocked_schemes(self, sanitizer: InputSanitizer):
        """Test URL validation blocks dangerous schemes."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd",
            "ftp://evil.com/malware",
        ]
        
        for url in dangerous_urls:
            with pytest.raises(ValueError, match="Dangerous URL scheme"):
                sanitizer.validate_url(url)

    def test_selector_validation_safe(self, sanitizer: InputSanitizer):
        """Test selector validation accepts safe selectors."""
        safe_selectors = [
            "#element-id",
            ".css-class",
            "div > p",
            "[data-test='value']",
            ":nth-child(1)",
            "text='Button Text'",
        ]
        
        for selector in safe_selectors:
            # Should not raise exceptions
            sanitizer.validate_selector(selector)

    def test_html_encoding(self, sanitizer: InputSanitizer):
        """Test HTML encoding of special characters."""
        input_with_html = "<div>test</div> & 'quotes' \"double\""
        encoded = sanitizer.encode_html(input_with_html)
        
        assert "&lt;div&gt;" in encoded
        assert "&amp;" in encoded
        assert "&#x27;" in encoded or "&apos;" in encoded
        assert "&quot;" in encoded


@pytest.mark.unit
class TestAuthenticationManager:
    """Test cases for authentication management."""

    @pytest.fixture
    def auth_config(self) -> Dict[str, Any]:
        """Provide authentication configuration for testing."""
        return {
            "enable_auth": True,
            "api_key_length": 32,
            "session_timeout": 3600,
            "max_failed_attempts": 5,
        }

    @pytest.fixture
    def auth_manager(self, auth_config: Dict[str, Any]) -> AuthenticationManager:
        """Provide AuthenticationManager instance for testing."""
        return AuthenticationManager(auth_config)

    def test_generate_api_key(self, auth_manager: AuthenticationManager):
        """Test API key generation."""
        api_key = auth_manager.generate_api_key()
        
        assert len(api_key) == 64  # 32 bytes = 64 hex chars
        assert all(c in "0123456789abcdef" for c in api_key)

    def test_validate_api_key_success(self, auth_manager: AuthenticationManager):
        """Test successful API key validation."""
        api_key = auth_manager.generate_api_key()
        auth_manager.register_api_key(api_key, "test-client")
        
        result = auth_manager.validate_api_key(api_key)
        assert result is True

    def test_validate_api_key_failure(self, auth_manager: AuthenticationManager):
        """Test failed API key validation."""
        invalid_key = "invalid-key-123"
        
        result = auth_manager.validate_api_key(invalid_key)
        assert result is False

    def test_api_key_revocation(self, auth_manager: AuthenticationManager):
        """Test API key revocation."""
        api_key = auth_manager.generate_api_key()
        auth_manager.register_api_key(api_key, "test-client")
        
        # Key should be valid initially
        assert auth_manager.validate_api_key(api_key) is True
        
        # Revoke the key
        auth_manager.revoke_api_key(api_key)
        
        # Key should be invalid after revocation
        assert auth_manager.validate_api_key(api_key) is False

    def test_session_timeout(self, auth_manager: AuthenticationManager):
        """Test session timeout handling."""
        session_id = "test-session"
        
        # Create session
        auth_manager.create_session(session_id, "test-api-key")
        
        # Session should be valid initially
        assert auth_manager.validate_session(session_id) is True
        
        # Mock time advancement
        with patch("time.time", return_value=time.time() + 7200):  # 2 hours later
            assert auth_manager.validate_session(session_id) is False

    def test_failed_login_attempts(self, auth_manager: AuthenticationManager):
        """Test failed login attempt tracking."""
        client_ip = "192.168.1.100"
        
        # Multiple failed attempts
        for _ in range(5):
            auth_manager.record_failed_attempt(client_ip)
        
        # Client should be blocked
        assert auth_manager.is_client_blocked(client_ip) is True

    def test_client_blocking_timeout(self, auth_manager: AuthenticationManager):
        """Test client blocking timeout."""
        client_ip = "192.168.1.100"
        
        # Block the client
        for _ in range(5):
            auth_manager.record_failed_attempt(client_ip)
        
        assert auth_manager.is_client_blocked(client_ip) is True
        
        # Mock time advancement
        with patch("time.time", return_value=time.time() + 3600):  # 1 hour later
            assert auth_manager.is_client_blocked(client_ip) is False


@pytest.mark.unit
class TestRateLimiter:
    """Test cases for rate limiting."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """Provide RateLimiter instance for testing."""
        return RateLimiter(requests_per_minute=60, burst_limit=10)

    def test_rate_limiting_within_limits(self, rate_limiter: RateLimiter):
        """Test requests within rate limits are allowed."""
        client_id = "test-client"
        
        # Make requests within limits
        for _ in range(5):
            assert rate_limiter.is_allowed(client_id) is True

    def test_rate_limiting_burst_protection(self, rate_limiter: RateLimiter):
        """Test burst protection limits."""
        client_id = "test-client"
        
        # Exhaust burst limit
        for _ in range(10):
            rate_limiter.is_allowed(client_id)
        
        # Next request should be denied
        assert rate_limiter.is_allowed(client_id) is False

    def test_rate_limiting_window_reset(self, rate_limiter: RateLimiter):
        """Test rate limiting window reset."""
        client_id = "test-client"
        
        # Exhaust rate limit
        for _ in range(60):
            rate_limiter.is_allowed(client_id)
        
        # Should be blocked
        assert rate_limiter.is_allowed(client_id) is False
        
        # Mock time advancement (1 minute)
        with patch("time.time", return_value=time.time() + 60):
            assert rate_limiter.is_allowed(client_id) is True

    def test_rate_limiting_per_client(self, rate_limiter: RateLimiter):
        """Test rate limiting is per-client."""
        client1 = "client-1"
        client2 = "client-2"
        
        # Exhaust limit for client1
        for _ in range(10):
            rate_limiter.is_allowed(client1)
        
        assert rate_limiter.is_allowed(client1) is False
        # Client2 should still be allowed
        assert rate_limiter.is_allowed(client2) is True

    def test_rate_limiter_cleanup(self, rate_limiter: RateLimiter):
        """Test cleanup of old rate limiting data."""
        client_id = "test-client"
        
        # Generate some activity
        rate_limiter.is_allowed(client_id)
        
        # Mock time advancement
        with patch("time.time", return_value=time.time() + 3600):  # 1 hour
            rate_limiter.cleanup_old_entries()
            
            # Old entries should be cleaned up
            assert len(rate_limiter.client_windows) == 0


@pytest.mark.unit
class TestSessionSecurity:
    """Test cases for session security."""

    @pytest.fixture
    def session_security(self) -> SessionSecurity:
        """Provide SessionSecurity instance for testing."""
        return SessionSecurity(
            session_timeout=3600,
            max_sessions_per_client=5
        )

    def test_secure_session_generation(self, session_security: SessionSecurity):
        """Test secure session ID generation."""
        session_id = session_security.generate_session_id()
        
        assert len(session_id) >= 32
        assert session_id.isalnum()  # Should be alphanumeric

    def test_session_validation(self, session_security: SessionSecurity):
        """Test session validation."""
        session_id = session_security.create_session("test-client")
        
        # Should be valid initially
        assert session_security.validate_session(session_id) is True
        
        # Should be invalid after timeout
        with patch("time.time", return_value=time.time() + 7200):
            assert session_security.validate_session(session_id) is False

    def test_session_hijacking_protection(self, session_security: SessionSecurity):
        """Test session hijacking protection."""
        client_info = {
            "ip_address": "192.168.1.100",
            "user_agent": "Test Browser 1.0"
        }
        
        session_id = session_security.create_session("test-client", client_info)
        
        # Valid with same client info
        assert session_security.validate_session(session_id, client_info) is True
        
        # Invalid with different client info
        different_info = {
            "ip_address": "192.168.1.200",
            "user_agent": "Different Browser"
        }
        assert session_security.validate_session(session_id, different_info) is False

    def test_max_sessions_per_client(self, session_security: SessionSecurity):
        """Test maximum sessions per client limit."""
        client_id = "test-client"
        
        # Create maximum allowed sessions
        sessions = []
        for i in range(5):
            session_id = session_security.create_session(f"{client_id}-{i}")
            sessions.append(session_id)
        
        # Sixth session should fail
        with pytest.raises(RuntimeError, match="Maximum sessions reached"):
            session_security.create_session(client_id)

    def test_session_termination(self, session_security: SessionSecurity):
        """Test session termination."""
        session_id = session_security.create_session("test-client")
        
        # Should be valid initially
        assert session_security.validate_session(session_id) is True
        
        # Terminate session
        session_security.terminate_session(session_id)
        
        # Should be invalid after termination
        assert session_security.validate_session(session_id) is False


@pytest.mark.unit
class TestSecurityManager:
    """Test cases for overall security manager."""

    @pytest.fixture
    def security_config(self) -> Dict[str, Any]:
        """Provide security configuration for testing."""
        return {
            "enable_auth": True,
            "rate_limit_per_minute": 60,
            "max_session_duration": 3600,
            "allowed_origins": ["http://localhost", "https://example.com"],
            "max_sessions_per_client": 5,
        }

    @pytest.fixture
    def security_manager(self, security_config: Dict[str, Any]) -> SecurityManager:
        """Provide SecurityManager instance for testing."""
        return SecurityManager(security_config)

    def test_comprehensive_input_validation(self, security_manager: SecurityManager):
        """Test comprehensive input validation."""
        # Test various malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError):
                security_manager.validate_command_input({
                    "method": "fill",
                    "selector": "#input",
                    "value": malicious_input
                })

    def test_origin_validation(self, security_manager: SecurityManager):
        """Test origin validation for CORS."""
        # Allowed origins should pass
        assert security_manager.validate_origin("http://localhost") is True
        assert security_manager.validate_origin("https://example.com") is True
        
        # Disallowed origins should fail
        assert security_manager.validate_origin("https://evil.com") is False
        assert security_manager.validate_origin("http://malicious.site") is False

    def test_security_audit_logging(self, security_manager: SecurityManager):
        """Test security audit logging."""
        with patch.object(security_manager.logger, "warning") as mock_warning:
            # Trigger a security violation
            try:
                security_manager.validate_command_input({
                    "method": "fill",
                    "selector": "javascript:alert('xss')",
                    "value": "test"
                })
            except ValueError:
                pass
            
            # Should log security violation
            mock_warning.assert_called()

    def test_threat_detection_aggregation(self, security_manager: SecurityManager):
        """Test threat detection and aggregation."""
        client_id = "suspicious-client"
        
        # Multiple security violations should escalate threat level
        for _ in range(3):
            try:
                security_manager.validate_command_input({
                    "method": "click",
                    "selector": "<script>alert('xss')</script>"
                })
            except ValueError:
                security_manager.record_security_violation(client_id, "malicious_selector")
        
        # Client should be flagged as high threat
        assert security_manager.get_threat_level(client_id) == "high"