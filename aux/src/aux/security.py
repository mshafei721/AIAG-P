"""
Security utilities for AUX Protocol.

This module provides input sanitization, secure authentication,
rate limiting, and other security features.
"""

import re
import time
import hmac
import hashlib
import secrets
import logging
from typing import Dict, Optional, Set, List, Any
from urllib.parse import urlparse
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class InputSanitizer:
    """
    Input sanitization for AUX protocol commands.
    
    Provides protection against injection attacks and validates input lengths.
    """
    
    # Dangerous JavaScript patterns
    JS_INJECTION_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'data:text/html',
        r'vbscript:',
        r'on\w+\s*=',
        r'eval\s*\(',
        r'Function\s*\(',
        r'setTimeout\s*\(',
        r'setInterval\s*\(',
        r'document\s*\.',
        r'window\s*\.',
        r'location\s*\.',
        r'alert\s*\(',
        r'confirm\s*\(',
        r'prompt\s*\(',
    ]
    
    # Dangerous CSS selector patterns
    CSS_INJECTION_PATTERNS = [
        r'javascript:',
        r'data:',
        r'expression\s*\(',
        r'@import',
        r'url\s*\(',
        r'on\w+\s*=',  # Event handlers like onclick, onload, etc.
        r'<script',
        r'</script>',
    ]
    
    # Allowed URL schemes
    ALLOWED_URL_SCHEMES = {'http', 'https'}
    
    def __init__(self, max_selector_length: int = 1000, max_text_length: int = 10000, max_url_length: int = 2048):
        """
        Initialize input sanitizer.
        
        Args:
            max_selector_length: Maximum CSS selector length
            max_text_length: Maximum text input length
            max_url_length: Maximum URL length
        """
        self.max_selector_length = max_selector_length
        self.max_text_length = max_text_length
        self.max_url_length = max_url_length
        
        # Compile regex patterns for performance
        self.js_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.JS_INJECTION_PATTERNS]
        self.css_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CSS_INJECTION_PATTERNS]
    
    def sanitize_selector(self, selector: str) -> str:
        """
        Sanitize CSS selector input.
        
        Args:
            selector: CSS selector string
            
        Returns:
            Sanitized selector
            
        Raises:
            ValueError: If selector is invalid or potentially dangerous
        """
        if not selector:
            raise ValueError("Selector cannot be empty")
            
        if len(selector) > self.max_selector_length:
            raise ValueError(f"Selector too long (max {self.max_selector_length} characters)")
        
        # Check for dangerous patterns
        for pattern in self.css_patterns:
            if pattern.search(selector):
                raise ValueError(f"Potentially dangerous selector pattern detected")
        
        # Basic selector validation
        if not self._is_valid_css_selector(selector):
            raise ValueError("Invalid CSS selector syntax")
        
        return selector.strip()
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text input.
        
        Args:
            text: Text input string
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If text contains dangerous patterns
        """
        if len(text) > self.max_text_length:
            raise ValueError(f"Text too long (max {self.max_text_length} characters)")
        
        # Check for JavaScript injection patterns
        for pattern in self.js_patterns:
            if pattern.search(text):
                raise ValueError("Potentially dangerous script content detected")
        
        return text
    
    def sanitize_url(self, url: str) -> str:
        """
        Sanitize URL input.
        
        Args:
            url: URL string
            
        Returns:
            Sanitized URL
            
        Raises:
            ValueError: If URL is invalid or dangerous
        """
        if not url:
            raise ValueError("URL cannot be empty")
            
        if len(url) > self.max_url_length:
            raise ValueError(f"URL too long (max {self.max_url_length} characters)")
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme.lower() not in self.ALLOWED_URL_SCHEMES:
                raise ValueError(f"URL scheme '{parsed.scheme}' not allowed")
            
            # Check for dangerous patterns
            for pattern in self.js_patterns:
                if pattern.search(url):
                    raise ValueError("Potentially dangerous URL content detected")
            
            return url.strip()
            
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")
    
    def sanitize_javascript(self, js_code: str) -> str:
        """
        Sanitize JavaScript code input.
        
        Args:
            js_code: JavaScript code string
            
        Returns:
            Sanitized JavaScript code
            
        Raises:
            ValueError: If code contains dangerous patterns
        """
        if not js_code:
            raise ValueError("JavaScript code cannot be empty")
            
        if len(js_code) > 5000:  # Reasonable limit for custom JS
            raise ValueError("JavaScript code too long")
        
        # Check for dangerous patterns
        dangerous_functions = [
            'eval', 'Function', 'setTimeout', 'setInterval',
            'XMLHttpRequest', 'fetch', 'import', 'require'
        ]
        
        for func in dangerous_functions:
            if re.search(rf'\b{func}\s*\(', js_code, re.IGNORECASE):
                raise ValueError(f"Dangerous function '{func}' not allowed")
        
        return js_code.strip()
    
    def _is_valid_css_selector(self, selector: str) -> bool:
        """
        Basic CSS selector validation.
        
        Args:
            selector: CSS selector string
            
        Returns:
            True if selector appears valid
        """
        # Very basic validation - could be enhanced
        if not selector:
            return False
            
        # Check for balanced brackets and quotes
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        in_quote = False
        quote_char = None
        
        for char in selector:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif not in_quote:
                if char in brackets:
                    stack.append(brackets[char])
                elif char in brackets.values():
                    if not stack or stack.pop() != char:
                        return False
        
        return len(stack) == 0 and not in_quote


class SecureAuthenticator:
    """
    Secure authentication handler for API keys.
    
    Uses constant-time comparison to prevent timing attacks.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize authenticator.
        
        Args:
            api_key: Expected API key for authentication
        """
        self.api_key = api_key
        self.auth_enabled = api_key is not None
        
    def authenticate(self, provided_key: Optional[str]) -> bool:
        """
        Authenticate using API key with timing-safe comparison.
        
        Args:
            provided_key: API key provided by client
            
        Returns:
            True if authentication succeeds
        """
        if not self.auth_enabled:
            return True
            
        if not provided_key or not self.api_key:
            return False
        
        # Use secrets.compare_digest for timing-safe comparison
        try:
            return secrets.compare_digest(self.api_key, provided_key)
        except TypeError:
            # Handle case where inputs are not strings
            return False
    
    def generate_api_key(self) -> str:
        """
        Generate a secure API key.
        
        Returns:
            Cryptographically secure API key
        """
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key for storage.
        
        Args:
            api_key: API key to hash
            
        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()


class RateLimiter:
    """
    Rate limiter for WebSocket connections.
    
    Implements sliding window rate limiting per client IP.
    """
    
    def __init__(self, requests_per_minute: int = 60, window_size: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per client
            window_size: Sliding window size in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size
        self.client_requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_clients: Dict[str, float] = {}
        
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if client is allowed to make a request.
        
        Args:
            client_id: Client identifier (IP address)
            
        Returns:
            True if request is allowed
        """
        current_time = time.time()
        
        # Check if client is temporarily blocked
        if client_id in self.blocked_clients:
            if current_time < self.blocked_clients[client_id]:
                return False
            else:
                del self.blocked_clients[client_id]
        
        # Clean old requests
        requests = self.client_requests[client_id]
        while requests and requests[0] < current_time - self.window_size:
            requests.popleft()
        
        # Check rate limit
        if len(requests) >= self.requests_per_minute:
            # Block client for a short period
            self.blocked_clients[client_id] = current_time + 60  # Block for 1 minute
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return False
        
        # Record this request
        requests.append(current_time)
        return True
    
    def cleanup_old_entries(self) -> None:
        """Clean up old entries to prevent memory leaks."""
        current_time = time.time()
        
        # Clean request history
        for client_id in list(self.client_requests.keys()):
            requests = self.client_requests[client_id]
            while requests and requests[0] < current_time - self.window_size * 2:
                requests.popleft()
            
            # Remove empty entries
            if not requests:
                del self.client_requests[client_id]
        
        # Clean blocked clients
        for client_id in list(self.blocked_clients.keys()):
            if current_time >= self.blocked_clients[client_id]:
                del self.blocked_clients[client_id]


class DomainValidator:
    """
    Domain validation for navigation security.
    
    Manages allowed and blocked domain lists.
    """
    
    def __init__(self, allowed_domains: Optional[List[str]] = None, blocked_domains: Optional[List[str]] = None):
        """
        Initialize domain validator.
        
        Args:
            allowed_domains: Whitelist of allowed domains (None means all allowed)
            blocked_domains: Blacklist of blocked domains
        """
        self.allowed_domains = set(allowed_domains) if allowed_domains else None
        self.blocked_domains = set(blocked_domains) if blocked_domains else set()
        
    def is_domain_allowed(self, url: str) -> bool:
        """
        Check if domain is allowed for navigation.
        
        Args:
            url: URL to validate
            
        Returns:
            True if domain is allowed
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Check blocked domains first
            if domain in self.blocked_domains:
                return False
            
            # Check wildcard blocked domains
            for blocked in self.blocked_domains:
                if blocked.startswith('*.') and domain.endswith(blocked[2:]):
                    return False
            
            # If allowed domains is set, check whitelist
            if self.allowed_domains is not None:
                if domain in self.allowed_domains:
                    return True
                
                # Check wildcard allowed domains
                for allowed in self.allowed_domains:
                    if allowed.startswith('*.') and domain.endswith(allowed[2:]):
                        return True
                
                return False  # Not in whitelist
            
            return True  # No whitelist, not blocked
            
        except Exception:
            return False  # Invalid URL


class SecurityManager:
    """
    Main security manager that coordinates all security features.
    """
    
    def __init__(self, config):
        """
        Initialize security manager with configuration.
        
        Args:
            config: Security configuration object
        """
        self.config = config
        self.sanitizer = InputSanitizer(
            max_selector_length=config.max_selector_length,
            max_text_length=config.max_text_input_length,
            max_url_length=config.max_url_length
        )
        self.authenticator = SecureAuthenticator()
        self.rate_limiter = RateLimiter(requests_per_minute=60)  # Will be configured from server config
        self.domain_validator = DomainValidator(
            allowed_domains=config.allowed_domains,
            blocked_domains=config.blocked_domains
        )
        
    def configure_auth(self, api_key: Optional[str]) -> None:
        """Configure authentication with API key."""
        self.authenticator = SecureAuthenticator(api_key)
        
    def configure_rate_limiting(self, requests_per_minute: int) -> None:
        """Configure rate limiting."""
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        
    def validate_command_security(self, command_data: Dict[str, Any]) -> None:
        """
        Validate command for security issues.
        
        Args:
            command_data: Command data to validate
            
        Raises:
            ValueError: If security validation fails
        """
        if not self.config.enable_input_sanitization:
            return
        
        method = command_data.get('method', '')
        
        # Validate selector if present
        if 'selector' in command_data:
            self.sanitizer.sanitize_selector(command_data['selector'])
        
        # Validate text input
        if 'text' in command_data:
            self.sanitizer.sanitize_text(command_data['text'])
        
        # Validate URL for navigate commands
        if method == 'navigate' and 'url' in command_data:
            url = command_data['url']
            self.sanitizer.sanitize_url(url)
            
            if not self.domain_validator.is_domain_allowed(url):
                raise ValueError("Navigation to this domain is not allowed")
        
        # Validate custom JavaScript
        if 'custom_js' in command_data and command_data['custom_js']:
            if not self.config.allow_custom_js:
                raise ValueError("Custom JavaScript execution is disabled")
            self.sanitizer.sanitize_javascript(command_data['custom_js'])