"""
Configuration Management System for AUX Protocol.

This module provides centralized configuration management with validation,
security settings, and environment variable support.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class SecurityLevel(str, Enum):
    """Security configuration levels."""
    DEVELOPMENT = "development"  # Relaxed security for testing
    PRODUCTION = "production"    # Full security enabled
    TESTING = "testing"         # Minimal security for automated tests


class BrowserConfig(BaseModel):
    """Browser-specific configuration settings."""
    
    headless: bool = Field(True, description="Run browser in headless mode")
    viewport_width: int = Field(1280, ge=800, le=3840, description="Browser viewport width")
    viewport_height: int = Field(720, ge=600, le=2160, description="Browser viewport height")
    user_agent: Optional[str] = Field(None, description="Custom user agent string")
    timeout_ms: int = Field(30000, ge=5000, le=300000, description="Default timeout in milliseconds")
    slow_mo_ms: int = Field(0, ge=0, le=5000, description="Slow motion delay for debugging")
    
    # Security settings
    disable_web_security: bool = Field(False, description="Disable web security (dangerous, use only for testing)")
    disable_dev_shm: bool = Field(True, description="Disable /dev/shm usage")
    no_sandbox: bool = Field(False, description="Run without sandbox (dangerous)")
    ignore_https_errors: bool = Field(False, description="Ignore HTTPS certificate errors")
    
    # Resource management
    max_sessions: int = Field(10, ge=1, le=100, description="Maximum concurrent browser sessions")
    session_timeout_seconds: int = Field(3600, ge=300, le=86400, description="Session timeout in seconds")
    cleanup_interval_seconds: int = Field(300, ge=60, le=3600, description="Session cleanup check interval")
    
    @validator('user_agent')
    def validate_user_agent(cls, v):
        if v and len(v) > 1000:
            raise ValueError("User agent string too long")
        return v


class ServerConfig(BaseModel):
    """WebSocket server configuration settings."""
    
    host: str = Field("localhost", description="Server host address")
    port: int = Field(8080, ge=1024, le=65535, description="Server port number")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    
    # Security settings
    enable_auth: bool = Field(True, description="Enable API key authentication")
    rate_limit_requests_per_minute: int = Field(60, ge=1, le=1000, description="Rate limit per client")
    max_concurrent_connections: int = Field(50, ge=1, le=1000, description="Maximum concurrent connections")
    
    # WebSocket settings
    ping_interval: int = Field(20, ge=5, le=300, description="WebSocket ping interval in seconds")
    ping_timeout: int = Field(10, ge=5, le=60, description="WebSocket ping timeout in seconds")
    max_message_size: int = Field(1048576, ge=1024, le=10485760, description="Maximum message size in bytes")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if v and len(v) < 16:
            raise ValueError("API key must be at least 16 characters long")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    
    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    enable_session_log: bool = Field(True, description="Enable session.log structured logging")
    session_log_path: str = Field("session.log", description="Path to session log file")
    enable_file_logging: bool = Field(True, description="Enable file logging")
    log_file_path: str = Field("aux.log", description="Path to general log file")
    max_log_file_size_mb: int = Field(100, ge=1, le=1000, description="Maximum log file size in MB")
    log_retention_days: int = Field(7, ge=1, le=30, description="Log file retention period")
    
    # Structured logging format
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    @validator('session_log_path', 'log_file_path')
    def validate_log_paths(cls, v):
        if not v or '..' in v or v.startswith('/'):
            raise ValueError("Invalid log file path")
        return v


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    
    security_level: SecurityLevel = Field(SecurityLevel.PRODUCTION, description="Overall security level")
    
    # Input validation
    enable_input_sanitization: bool = Field(True, description="Enable input sanitization")
    max_selector_length: int = Field(1000, ge=100, le=10000, description="Maximum CSS selector length")
    max_text_input_length: int = Field(10000, ge=100, le=100000, description="Maximum text input length")
    max_url_length: int = Field(2048, ge=100, le=10000, description="Maximum URL length")
    
    # JavaScript execution
    allow_custom_js: bool = Field(False, description="Allow custom JavaScript execution")
    js_timeout_ms: int = Field(5000, ge=1000, le=30000, description="JavaScript execution timeout")
    
    # Content Security
    allowed_domains: Optional[List[str]] = Field(None, description="Whitelist of allowed domains")
    blocked_domains: Optional[List[str]] = Field(None, description="Blacklist of blocked domains")
    
    @validator('allowed_domains', 'blocked_domains')
    def validate_domains(cls, v):
        if v:
            for domain in v:
                if not domain or '..' in domain or domain.startswith('.'):
                    raise ValueError(f"Invalid domain: {domain}")
        return v


class AUXConfig(BaseModel):
    """Main AUX Protocol configuration."""
    
    browser: BrowserConfig = Field(default_factory=BrowserConfig, description="Browser configuration")
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    
    # Environment
    environment: str = Field("production", description="Environment name")
    debug: bool = Field(False, description="Enable debug mode")
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'testing', 'production']:
            raise ValueError("Environment must be development, testing, or production")
        return v


class ConfigManager:
    """
    Configuration manager for AUX Protocol.
    
    Provides centralized configuration management with environment variable
    support, validation, and security-aware defaults.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path
        self._config: Optional[AUXConfig] = None
        self.logger = logging.getLogger(__name__)
        
    def load_config(self) -> AUXConfig:
        """
        Load configuration from environment variables and config file.
        
        Returns:
            Loaded configuration
        """
        if self._config is not None:
            return self._config
            
        # Start with default config
        config_data = {}
        
        # Load from config file if provided
        if self.config_path and os.path.exists(self.config_path):
            try:
                import json
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                config_data.update(file_config)
                self.logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Override with environment variables
        env_config = self._load_from_environment()
        self._merge_config(config_data, env_config)
        
        # Validate and create config object
        try:
            self._config = AUXConfig(**config_data)
            self.logger.info("Configuration loaded and validated successfully")
            return self._config
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            # Fallback to default config
            self._config = AUXConfig()
            return self._config
    
    def get_config(self) -> AUXConfig:
        """Get current configuration, loading if not already loaded."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Server settings
        if os.getenv('AUX_HOST'):
            env_config.setdefault('server', {})['host'] = os.getenv('AUX_HOST')
        if os.getenv('AUX_PORT'):
            env_config.setdefault('server', {})['port'] = int(os.getenv('AUX_PORT'))
        if os.getenv('AUX_API_KEY'):
            env_config.setdefault('server', {})['api_key'] = os.getenv('AUX_API_KEY')
            
        # Browser settings
        if os.getenv('AUX_HEADLESS'):
            env_config.setdefault('browser', {})['headless'] = os.getenv('AUX_HEADLESS').lower() == 'true'
        if os.getenv('AUX_DISABLE_WEB_SECURITY'):
            env_config.setdefault('browser', {})['disable_web_security'] = os.getenv('AUX_DISABLE_WEB_SECURITY').lower() == 'true'
        if os.getenv('AUX_NO_SANDBOX'):
            env_config.setdefault('browser', {})['no_sandbox'] = os.getenv('AUX_NO_SANDBOX').lower() == 'true'
            
        # Logging settings
        if os.getenv('AUX_LOG_LEVEL'):
            env_config.setdefault('logging', {})['level'] = os.getenv('AUX_LOG_LEVEL')
        if os.getenv('AUX_SESSION_LOG_PATH'):
            env_config.setdefault('logging', {})['session_log_path'] = os.getenv('AUX_SESSION_LOG_PATH')
            
        # Security settings
        if os.getenv('AUX_SECURITY_LEVEL'):
            env_config.setdefault('security', {})['security_level'] = os.getenv('AUX_SECURITY_LEVEL')
        if os.getenv('AUX_ALLOW_CUSTOM_JS'):
            env_config.setdefault('security', {})['allow_custom_js'] = os.getenv('AUX_ALLOW_CUSTOM_JS').lower() == 'true'
            
        # Environment
        if os.getenv('AUX_ENVIRONMENT'):
            env_config['environment'] = os.getenv('AUX_ENVIRONMENT')
        if os.getenv('AUX_DEBUG'):
            env_config['debug'] = os.getenv('AUX_DEBUG').lower() == 'true'
            
        return env_config
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Merge configuration dictionaries recursively."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get_browser_launch_args(self) -> List[str]:
        """
        Get browser launch arguments based on configuration.
        
        Returns:
            List of browser launch arguments
        """
        config = self.get_config()
        args = []
        
        # Security-related arguments
        if config.browser.disable_dev_shm:
            args.append("--disable-dev-shm-usage")
            
        if config.browser.no_sandbox:
            self.logger.warning("Running browser without sandbox - security risk!")
            args.append("--no-sandbox")
            
        if config.browser.disable_web_security:
            self.logger.warning("Running browser with disabled web security - security risk!")
            args.append("--disable-web-security")
            
        if config.browser.ignore_https_errors:
            args.append("--ignore-certificate-errors")
            args.append("--ignore-ssl-errors")
            
        # Performance arguments
        args.extend([
            "--disable-blink-features=AutomationControlled",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
        ])
        
        return args
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        config = self.get_config()
        return config.environment == "development" or config.debug
    
    def is_secure_mode(self) -> bool:
        """Check if running in secure mode."""
        config = self.get_config()
        return config.security.security_level == SecurityLevel.PRODUCTION


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> AUXConfig:
    """Get global AUX configuration."""
    return config_manager.get_config()


def init_config(config_path: Optional[str] = None) -> AUXConfig:
    """
    Initialize global configuration.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized configuration
    """
    global config_manager
    config_manager = ConfigManager(config_path)
    return config_manager.load_config()