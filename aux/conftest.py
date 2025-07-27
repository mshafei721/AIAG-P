"""
Root conftest.py for AUX Protocol test suite.

Provides global configuration, fixtures, and utilities for all tests.
This file is automatically loaded by pytest for all test sessions.
"""

import os
import sys
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
import pytest

# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import test configuration and utilities
from tests.conftest import *  # Import existing test fixtures


# Global test configuration
TEST_CONFIG = {
    "timeout": 300,
    "slow_test_threshold": 30,
    "parallel_workers": 4,
    "retry_attempts": 2,
    "cleanup_on_exit": True
}


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/pytest.log'),
            logging.StreamHandler()
        ]
    )
    
    # Suppress verbose browser logs during testing
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    # Create necessary directories
    directories = ['logs', 'reports', 'htmlcov', 'test_data', 'temp']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Configure asyncio for testing
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Register custom markers
    for marker_name, marker_description in {
        'unit': 'Unit tests for individual components',
        'integration': 'Integration tests for component interactions',
        'security': 'Security vulnerability and penetration tests',
        'performance': 'Performance benchmarking and load tests',
        'e2e': 'End-to-end workflow tests',
        'regression': 'Backward compatibility and regression tests',
        'slow': 'Slow running tests (>30 seconds)',
        'fast': 'Fast running tests (<5 seconds)',
        'browser': 'Tests requiring browser automation',
        'network': 'Tests requiring network access',
        'auth': 'Authentication and authorization tests',
        'smoke': 'Smoke tests for basic functionality',
        'critical': 'Critical path tests that must pass',
        'flaky': 'Tests that may fail intermittently',
        'wip': 'Work in progress tests'
    }.items():
        config.addinivalue_line('markers', f'{marker_name}: {marker_description}')


def pytest_collection_modifyitems(config, items):
    """Modify test collection with custom logic."""
    # Skip slow tests if --fast-only option is used
    if config.getoption('--fast-only', default=False):
        skip_slow = pytest.mark.skip(reason="Skipping slow tests (--fast-only)")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    # Mark browser tests
    for item in items:
        if "browser" in item.nodeid or "e2e" in item.keywords:
            item.add_marker(pytest.mark.browser)
    
    # Auto-mark performance tests as slow
    for item in items:
        if "performance" in item.keywords or "benchmark" in item.keywords:
            item.add_marker(pytest.mark.slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--fast-only",
        action="store_true",
        default=False,
        help="Run only fast tests (skip slow tests)"
    )
    
    parser.addoption(
        "--security-only",
        action="store_true",
        default=False,
        help="Run only security tests"
    )
    
    parser.addoption(
        "--no-browser",
        action="store_true",
        default=False,
        help="Skip tests that require browser automation"
    )
    
    parser.addoption(
        "--performance-only",
        action="store_true",
        default=False,
        help="Run only performance and benchmark tests"
    )
    
    parser.addoption(
        "--smoke-only",
        action="store_true",
        default=False,
        help="Run only smoke tests"
    )
    
    parser.addoption(
        "--repeat-count",
        type=int,
        default=1,
        help="Number of times to repeat each test"
    )
    
    parser.addoption(
        "--stress-test",
        action="store_true",
        default=False,
        help="Enable stress testing mode"
    )


def pytest_runtest_setup(item):
    """Setup for individual test runs."""
    # Skip browser tests if --no-browser is specified
    if item.config.getoption('--no-browser') and "browser" in item.keywords:
        pytest.skip("Browser tests disabled (--no-browser)")
    
    # Skip non-security tests if --security-only is specified
    if item.config.getoption('--security-only') and "security" not in item.keywords:
        pytest.skip("Only running security tests (--security-only)")
    
    # Skip non-performance tests if --performance-only is specified
    if item.config.getoption('--performance-only') and "performance" not in item.keywords:
        pytest.skip("Only running performance tests (--performance-only)")
    
    # Skip non-smoke tests if --smoke-only is specified
    if item.config.getoption('--smoke-only') and "smoke" not in item.keywords:
        pytest.skip("Only running smoke tests (--smoke-only)")


def pytest_runtest_teardown(item, nextitem):
    """Cleanup after individual test runs."""
    # Clean up any test artifacts
    cleanup_test_artifacts()


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    logger = logging.getLogger('pytest')
    logger.info("Starting AUX Protocol test session")
    
    # Display test configuration
    config_info = [
        f"Python version: {sys.version}",
        f"Platform: {sys.platform}",
        f"Test directory: {Path.cwd()}",
        f"Parallel workers: {session.config.option.numprocesses or 1}",
        f"Timeout: {session.config.option.timeout or 'None'}"
    ]
    
    for info in config_info:
        logger.info(info)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    logger = logging.getLogger('pytest')
    
    # Report test summary
    if hasattr(session, 'testscollected'):
        logger.info(f"Test session completed. Collected: {session.testscollected} tests")
    
    # Cleanup if configured
    if TEST_CONFIG["cleanup_on_exit"]:
        cleanup_session_artifacts()
    
    logger.info(f"Test session finished with exit status: {exitstatus}")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom terminal summary information."""
    if exitstatus == 0:
        terminalreporter.write_sep("=", "AUX Protocol Test Suite - ALL TESTS PASSED", green=True)
    else:
        terminalreporter.write_sep("=", "AUX Protocol Test Suite - SOME TESTS FAILED", red=True)
    
    # Add custom summary sections
    terminalreporter.write_sep("-", "Test Configuration")
    terminalreporter.write_line(f"Coverage threshold: 90%")
    terminalreporter.write_line(f"Timeout per test: {config.option.timeout or 'Default'}s")
    terminalreporter.write_line(f"Parallel workers: {config.option.numprocesses or 1}")
    
    # Coverage information
    if hasattr(terminalreporter.config, '_cov'):
        terminalreporter.write_sep("-", "Coverage Information")
        terminalreporter.write_line("Detailed coverage report: htmlcov/index.html")
        terminalreporter.write_line("Coverage XML: coverage.xml")
        terminalreporter.write_line("Coverage JSON: coverage.json")


def pytest_html_report_title(report):
    """Customize HTML report title."""
    report.title = "AUX Protocol Test Suite Report"


def pytest_html_results_summary(prefix, summary, postfix):
    """Customize HTML report summary."""
    prefix.extend([
        '<h2>AUX Protocol Test Suite</h2>',
        '<p>Comprehensive test coverage for browser automation protocol</p>'
    ])


@pytest.fixture(scope="session", autouse=True)
def test_session_setup():
    """Set up test session environment."""
    # Create test environment
    test_env = {
        'AUX_TEST_MODE': 'true',
        'AUX_LOG_LEVEL': 'DEBUG',
        'AUX_TEST_TIMEOUT': str(TEST_CONFIG["timeout"]),
        'PYTHONPATH': str(Path(__file__).parent / "src")
    }
    
    # Apply environment variables
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory."""
    data_dir = Path("test_data")
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def temp_dir_session():
    """Provide session-scoped temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="aux_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def isolated_temp_dir():
    """Provide isolated temporary directory for each test."""
    temp_dir = tempfile.mkdtemp(prefix="aux_test_isolated_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def test_isolation():
    """Ensure test isolation."""
    # Setup
    original_cwd = Path.cwd()
    
    yield
    
    # Cleanup
    os.chdir(original_cwd)
    
    # Reset any global state if needed
    # (Add any global state resets here)


@pytest.fixture
def mock_time():
    """Provide time mocking utilities."""
    with patch('time.time') as mock_time_func:
        mock_time_func.return_value = 1640995200.0  # Fixed timestamp
        yield mock_time_func


@pytest.fixture
def capture_logs():
    """Capture logs during test execution."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to aux logger
    aux_logger = logging.getLogger('aux')
    aux_logger.addHandler(handler)
    aux_logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Remove handler
    aux_logger.removeHandler(handler)


def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    # Clean up temporary files
    temp_patterns = [
        'test_*.tmp',
        '*.test',
        'aux_test_*'
    ]
    
    for pattern in temp_patterns:
        for file_path in Path.cwd().glob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except Exception:
                pass  # Ignore cleanup errors


def cleanup_session_artifacts():
    """Clean up session artifacts."""
    # Clean up logs directory
    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            if log_file.stat().st_size > 100 * 1024 * 1024:  # > 100MB
                log_file.unlink()
    
    # Clean up temporary directories
    temp_dirs = Path("/tmp").glob("aux_test_*") if Path("/tmp").exists() else []
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


# Performance testing utilities
class PerformanceTracker:
    """Track performance metrics during testing."""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, name: str):
        """Start timing an operation."""
        self.start_times[name] = asyncio.get_event_loop().time()
    
    def end_timer(self, name: str) -> float:
        """End timing and return duration."""
        if name not in self.start_times:
            return 0.0
        
        duration = asyncio.get_event_loop().time() - self.start_times[name]
        self.metrics[name] = duration
        return duration
    
    def get_metrics(self) -> Dict[str, float]:
        """Get all collected metrics."""
        return self.metrics.copy()


@pytest.fixture
def performance_tracker():
    """Provide performance tracking utilities."""
    return PerformanceTracker()


# Error handling utilities
class TestErrorCollector:
    """Collect and categorize test errors."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def add_error(self, error: Exception, context: str = ""):
        """Add an error with context."""
        self.errors.append({
            'error': error,
            'context': context,
            'type': type(error).__name__
        })
    
    def add_warning(self, message: str, context: str = ""):
        """Add a warning with context."""
        self.warnings.append({
            'message': message,
            'context': context
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }


@pytest.fixture
def error_collector():
    """Provide error collection utilities."""
    return TestErrorCollector()
