"""
Comprehensive unit tests for AUX Protocol configuration management.

Tests cover configuration loading, validation, defaults, environment
variables, and edge cases for the configuration system.
"""

import os
import tempfile
import yaml
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, mock_open

from aux.config import (
    Config,
    BrowserConfig,
    SecurityConfig,
    ServerConfig,
    LoggingConfig,
    get_config,
    load_config_from_file,
    validate_config,
)


class TestBrowserConfig:
    """Test BrowserConfig validation and functionality."""
    
    def test_valid_browser_config(self):
        """Test creation of valid browser configuration."""
        config = BrowserConfig(
            headless=True,
            timeout=30000,
            viewport={"width": 1920, "height": 1080},
            user_agent="AUX-Agent/1.0",
            executable_path="/usr/bin/chromium"
        )
        assert config.headless is True
        assert config.timeout == 30000
        assert config.viewport["width"] == 1920
        assert config.user_agent == "AUX-Agent/1.0"
        
    def test_browser_config_defaults(self):
        """Test browser configuration with default values."""
        config = BrowserConfig()
        assert config.headless is True
        assert config.timeout == 30000
        assert config.viewport["width"] == 1280
        assert config.viewport["height"] == 720
        assert "AUX" in config.user_agent
        
    def test_browser_config_invalid_timeout(self):
        """Test browser configuration with invalid timeout."""
        with pytest.raises(ValueError):
            BrowserConfig(timeout=-1000)
            
    def test_browser_config_invalid_viewport(self):
        """Test browser configuration with invalid viewport."""
        with pytest.raises(ValueError):
            BrowserConfig(viewport={"width": -100, "height": 720})
            
    def test_browser_config_custom_args(self):
        """Test browser configuration with custom launch arguments."""
        config = BrowserConfig(
            launch_args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        assert "--no-sandbox" in config.launch_args
        assert "--disable-dev-shm-usage" in config.launch_args


class TestSecurityConfig:
    """Test SecurityConfig validation and functionality."""
    
    def test_valid_security_config(self):
        """Test creation of valid security configuration."""
        config = SecurityConfig(
            enable_auth=True,
            api_keys=["key1", "key2"],
            rate_limit_per_minute=100,
            max_session_duration=3600,
            allowed_origins=["https://example.com"],
            csrf_protection=True
        )
        assert config.enable_auth is True
        assert len(config.api_keys) == 2
        assert config.rate_limit_per_minute == 100
        assert config.csrf_protection is True
        
    def test_security_config_defaults(self):
        """Test security configuration with default values."""
        config = SecurityConfig()
        assert config.enable_auth is True
        assert config.rate_limit_per_minute == 60
        assert config.max_session_duration == 1800
        assert config.csrf_protection is True
        
    def test_security_config_disabled_auth(self):
        """Test security configuration with disabled authentication."""
        config = SecurityConfig(enable_auth=False)
        assert config.enable_auth is False
        assert config.api_keys == []
        
    def test_security_config_invalid_rate_limit(self):
        """Test security configuration with invalid rate limit."""
        with pytest.raises(ValueError):
            SecurityConfig(rate_limit_per_minute=-1)
            
    def test_security_config_invalid_session_duration(self):
        """Test security configuration with invalid session duration."""
        with pytest.raises(ValueError):
            SecurityConfig(max_session_duration=0)


class TestServerConfig:
    """Test ServerConfig validation and functionality."""
    
    def test_valid_server_config(self):
        """Test creation of valid server configuration."""
        config = ServerConfig(
            host="0.0.0.0",
            port=8080,
            max_connections=200,
            heartbeat_interval=30,
            compression=True
        )
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.max_connections == 200
        assert config.compression is True
        
    def test_server_config_defaults(self):
        """Test server configuration with default values."""
        config = ServerConfig()
        assert config.host == "localhost"
        assert config.port == 8765
        assert config.max_connections == 100
        assert config.heartbeat_interval == 60
        
    def test_server_config_invalid_port(self):
        """Test server configuration with invalid port."""
        with pytest.raises(ValueError):
            ServerConfig(port=0)
            
        with pytest.raises(ValueError):
            ServerConfig(port=65536)
            
    def test_server_config_invalid_host(self):
        """Test server configuration with invalid host."""
        with pytest.raises(ValueError):
            ServerConfig(host="")
            
    def test_server_config_ssl(self):
        """Test server configuration with SSL settings."""
        config = ServerConfig(
            ssl_cert_path="/path/to/cert.pem",
            ssl_key_path="/path/to/key.pem"
        )
        assert config.ssl_cert_path == "/path/to/cert.pem"
        assert config.ssl_key_path == "/path/to/key.pem"


class TestLoggingConfig:
    """Test LoggingConfig validation and functionality."""
    
    def test_valid_logging_config(self):
        """Test creation of valid logging configuration."""
        config = LoggingConfig(
            level="DEBUG",
            format="json",
            file="aux.log",
            max_file_size=10485760,
            backup_count=5
        )
        assert config.level == "DEBUG"
        assert config.format == "json"
        assert config.file == "aux.log"
        assert config.max_file_size == 10485760
        
    def test_logging_config_defaults(self):
        """Test logging configuration with default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "text"
        assert config.file == "session.log"
        
    def test_logging_config_invalid_level(self):
        """Test logging configuration with invalid level."""
        with pytest.raises(ValueError):
            LoggingConfig(level="INVALID")
            
    def test_logging_config_invalid_format(self):
        """Test logging configuration with invalid format."""
        with pytest.raises(ValueError):
            LoggingConfig(format="invalid")


class TestMainConfig:
    """Test main Config class validation and functionality."""
    
    def test_valid_main_config(self):
        """Test creation of valid main configuration."""
        config = Config(
            browser_config=BrowserConfig(headless=False),
            security_config=SecurityConfig(enable_auth=True),
            server_config=ServerConfig(port=9000),
            logging_config=LoggingConfig(level="DEBUG")
        )
        assert config.browser_config.headless is False
        assert config.security_config.enable_auth is True
        assert config.server_config.port == 9000
        assert config.logging_config.level == "DEBUG"
        
    def test_main_config_defaults(self):
        """Test main configuration with default values."""
        config = Config()
        assert isinstance(config.browser_config, BrowserConfig)
        assert isinstance(config.security_config, SecurityConfig)
        assert isinstance(config.server_config, ServerConfig)
        assert isinstance(config.logging_config, LoggingConfig)
        
    def test_main_config_partial_override(self):
        """Test main configuration with partial overrides."""
        config = Config(
            browser_config=BrowserConfig(timeout=60000),
            server_config=ServerConfig(host="0.0.0.0")
        )
        assert config.browser_config.timeout == 60000
        assert config.server_config.host == "0.0.0.0"
        # Defaults should still be present
        assert config.security_config.enable_auth is True
        assert config.logging_config.level == "INFO"


class TestConfigFileLoading:
    """Test configuration file loading functionality."""
    
    def test_load_config_from_yaml_file(self, temp_dir):
        """Test loading configuration from YAML file."""
        config_data = {
            "browser_config": {
                "headless": False,
                "timeout": 45000
            },
            "server_config": {
                "port": 8080,
                "host": "0.0.0.0"
            }
        }
        
        config_file = temp_dir / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
            
        config = load_config_from_file(str(config_file))
        assert config.browser_config.headless is False
        assert config.browser_config.timeout == 45000
        assert config.server_config.port == 8080
        assert config.server_config.host == "0.0.0.0"
        
    def test_load_config_from_json_file(self, temp_dir):
        """Test loading configuration from JSON file."""
        import json
        
        config_data = {
            "security_config": {
                "enable_auth": False,
                "rate_limit_per_minute": 200
            },
            "logging_config": {
                "level": "WARNING",
                "format": "json"
            }
        }
        
        config_file = temp_dir / "test_config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)
            
        config = load_config_from_file(str(config_file))
        assert config.security_config.enable_auth is False
        assert config.security_config.rate_limit_per_minute == 200
        assert config.logging_config.level == "WARNING"
        assert config.logging_config.format == "json"
        
    def test_load_config_nonexistent_file(self):
        """Test loading configuration from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/config.yaml")
            
    def test_load_config_invalid_yaml(self, temp_dir):
        """Test loading configuration from invalid YAML file."""
        config_file = temp_dir / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")
            
        with pytest.raises(yaml.YAMLError):
            load_config_from_file(str(config_file))


class TestEnvironmentVariables:
    """Test configuration loading from environment variables."""
    
    def test_config_from_environment_variables(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "AUX_BROWSER_HEADLESS": "false",
            "AUX_BROWSER_TIMEOUT": "60000",
            "AUX_SERVER_PORT": "9000",
            "AUX_SERVER_HOST": "0.0.0.0",
            "AUX_SECURITY_ENABLE_AUTH": "false",
            "AUX_LOGGING_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_config()
            assert config.browser_config.headless is False
            assert config.browser_config.timeout == 60000
            assert config.server_config.port == 9000
            assert config.server_config.host == "0.0.0.0"
            assert config.security_config.enable_auth is False
            assert config.logging_config.level == "DEBUG"
            
    def test_config_env_var_type_conversion(self):
        """Test environment variable type conversion."""
        env_vars = {
            "AUX_BROWSER_HEADLESS": "true",
            "AUX_SECURITY_RATE_LIMIT_PER_MINUTE": "150",
            "AUX_SERVER_MAX_CONNECTIONS": "250"
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_config()
            assert config.browser_config.headless is True
            assert config.security_config.rate_limit_per_minute == 150
            assert config.server_config.max_connections == 250
            
    def test_config_env_var_invalid_values(self):
        """Test environment variables with invalid values."""
        env_vars = {
            "AUX_BROWSER_TIMEOUT": "not_a_number",
            "AUX_SERVER_PORT": "invalid_port"
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises((ValueError, TypeError)):
                get_config()


class TestConfigValidation:
    """Test configuration validation functionality."""
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = Config(
            browser_config=BrowserConfig(timeout=30000),
            server_config=ServerConfig(port=8765)
        )
        
        # Should not raise any exceptions
        validate_config(config)
        
    def test_validate_config_conflicting_settings(self):
        """Test validation of configuration with conflicting settings."""
        config = Config(
            security_config=SecurityConfig(
                enable_auth=True,
                api_keys=[]  # Auth enabled but no keys
            )
        )
        
        with pytest.raises(ValueError, match="authentication.*enabled.*no API keys"):
            validate_config(config)
            
    def test_validate_config_ssl_incomplete(self):
        """Test validation of configuration with incomplete SSL settings."""
        config = Config(
            server_config=ServerConfig(
                ssl_cert_path="/path/to/cert.pem"
                # Missing ssl_key_path
            )
        )
        
        with pytest.raises(ValueError, match="SSL.*both.*certificate.*key"):
            validate_config(config)
            
    def test_validate_config_performance_warnings(self):
        """Test validation warnings for performance settings."""
        config = Config(
            browser_config=BrowserConfig(timeout=300000),  # 5 minutes
            server_config=ServerConfig(max_connections=1000)
        )
        
        # Should validate but may log warnings
        validate_config(config)


class TestConfigMerging:
    """Test configuration merging and precedence."""
    
    def test_config_precedence_file_over_defaults(self, temp_dir):
        """Test that file configuration overrides defaults."""
        config_data = {
            "browser_config": {
                "headless": False,
                "timeout": 45000
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
            
        config = load_config_from_file(str(config_file))
        
        # File settings should override defaults
        assert config.browser_config.headless is False
        assert config.browser_config.timeout == 45000
        
        # Defaults should still be present for unspecified settings
        assert config.server_config.port == 8765  # Default port
        
    def test_config_precedence_env_over_file(self, temp_dir):
        """Test that environment variables override file configuration."""
        config_data = {
            "browser_config": {
                "headless": True,
                "timeout": 30000
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
            
        env_vars = {
            "AUX_BROWSER_HEADLESS": "false",
            "AUX_CONFIG_FILE": str(config_file)
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_config()
            
            # Environment should override file
            assert config.browser_config.headless is False
            
            # File should override defaults for unspecified env vars
            assert config.browser_config.timeout == 30000


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_config_with_none_values(self):
        """Test configuration with None values."""
        config = Config(
            browser_config=BrowserConfig(
                executable_path=None,
                user_agent=None
            )
        )
        assert config.browser_config.executable_path is None
        # user_agent should have a default even if None is passed
        assert config.browser_config.user_agent is not None
        
    def test_config_with_empty_lists(self):
        """Test configuration with empty lists."""
        config = Config(
            security_config=SecurityConfig(
                api_keys=[],
                allowed_origins=[]
            )
        )
        assert config.security_config.api_keys == []
        assert config.security_config.allowed_origins == []
        
    def test_config_with_extreme_values(self):
        """Test configuration with extreme but valid values."""
        config = Config(
            browser_config=BrowserConfig(
                timeout=1,  # Minimum timeout
                viewport={"width": 100, "height": 100}  # Minimum viewport
            ),
            server_config=ServerConfig(
                port=1024,  # Minimum non-privileged port
                max_connections=1  # Minimum connections
            )
        )
        assert config.browser_config.timeout == 1
        assert config.server_config.max_connections == 1
        
    def test_config_unicode_values(self):
        """Test configuration with unicode values."""
        config = Config(
            browser_config=BrowserConfig(
                user_agent="AUX-Agent/1.0 (测试)"
            ),
            logging_config=LoggingConfig(
                file="aux_日志.log"
            )
        )
        assert "测试" in config.browser_config.user_agent
        assert "日志" in config.logging_config.file
