# AUX Protocol Test Suite

This comprehensive test suite provides extensive coverage for the AUX Protocol implementation, including unit tests, integration tests, security tests, performance benchmarks, end-to-end tests, and regression tests.

## Overview

The test suite is designed to ensure:
- 90%+ code coverage across all modules
- Security vulnerability detection and prevention
- Performance benchmarking and regression detection
- Cross-browser and cross-platform compatibility
- Backward compatibility validation
- Real-world scenario validation

## Test Structure

```
tests/
├── unit/                   # Component-level tests
│   ├── test_commands.py    # Command schema and validation tests
│   ├── test_config.py      # Configuration management tests
│   ├── test_cache.py       # Cache operations and memory management
│   └── test_batch.py       # Batch processing and dependency resolution
├── integration/            # Component interaction tests
│   ├── test_end_to_end_workflows.py      # Complete workflow tests
│   └── test_browser_websocket_integration.py  # Browser-WebSocket communication
├── security/               # Security and vulnerability tests
│   ├── test_vulnerability_scanning.py    # Input validation and injection tests
│   └── test_penetration_testing.py       # Advanced security scenarios
├── performance/            # Performance and load tests
│   ├── test_benchmarks.py               # Performance benchmarking
│   └── test_stress_testing.py           # Load and stress tests
├── e2e/                   # End-to-end browser automation tests
│   ├── test_real_world_scenarios.py     # Real-world use cases
│   └── test_browser_compatibility.py    # Cross-browser testing
└── regression/            # Backward compatibility tests
    └── test_backward_compatibility.py   # Protocol version compatibility
```

## Running Tests

### Quick Start

```bash
# Run all tests with default configuration
./scripts/run_tests.sh

# Run specific test categories
./scripts/run_tests.sh -t unit
./scripts/run_tests.sh -t integration
./scripts/run_tests.sh -t security
./scripts/run_tests.sh -t performance
./scripts/run_tests.sh -t e2e
./scripts/run_tests.sh -t regression

# Run smoke tests only
./scripts/run_tests.sh --smoke-only
```

### Advanced Usage

```bash
# Run with custom coverage threshold
./scripts/run_tests.sh --coverage 95

# Run in parallel with specific worker count
./scripts/run_tests.sh --jobs 4

# Run with verbose output
./scripts/run_tests.sh --verbose

# Clean artifacts and run fresh
./scripts/run_tests.sh --clean

# Run in strict mode (fail on warnings)
./scripts/run_tests.sh --strict

# Retry failed tests
./scripts/run_tests.sh --retry-failed
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_commands.py

# Run with coverage
pytest --cov=src/aux --cov-report=html

# Run specific test markers
pytest -m unit
pytest -m "security and not slow"
pytest -m "performance and fast"

# Run tests matching pattern
pytest -k "test_command_validation"
```

## Test Categories and Markers

### Test Categories
- `unit`: Unit tests for individual components
- `integration`: Integration tests for component interactions
- `security`: Security vulnerability and penetration tests
- `performance`: Performance benchmarking and load tests
- `e2e`: End-to-end workflow tests
- `regression`: Backward compatibility and regression tests

### Speed Categories
- `fast`: Tests that complete in under 5 seconds
- `slow`: Tests that take more than 30 seconds

### Environment Requirements
- `browser`: Tests requiring browser automation
- `network`: Tests requiring network access
- `auth`: Authentication and authorization tests

### Special Categories
- `smoke`: Basic functionality smoke tests
- `critical`: Critical path tests that must pass
- `flaky`: Tests that may fail intermittently

## Configuration

### Environment Variables

```bash
# Test mode configuration
export AUX_TEST_MODE=true
export AUX_LOG_LEVEL=DEBUG

# Browser configuration
export AUX_TEST_BROWSER=chromium  # chromium, firefox, webkit
export AUX_TEST_HEADLESS=true     # true for headless, false for headed

# Test timeouts
export AUX_TEST_TIMEOUT=300       # Test timeout in seconds

# Additional pytest arguments
export PYTEST_ARGS="--maxfail=5 --tb=short"
```

### pytest.ini Configuration

The test suite uses a comprehensive pytest configuration in `pytest.ini`:

- **Coverage**: Configured for 90% threshold with branch coverage
- **Parallel Execution**: Automatic worker scaling with pytest-xdist
- **Timeouts**: 300-second default timeout per test
- **Reporting**: HTML, XML, and JSON coverage reports
- **Benchmarking**: Automatic benchmark saving and comparison

## Test Data and Fixtures

### Global Fixtures

The test suite provides several global fixtures in `conftest.py`:

- `test_config`: Base configuration for all tests
- `mock_browser`: Mock browser manager for unit tests
- `temp_directory`: Temporary directory for test artifacts
- `cleanup_sessions`: Automatic session cleanup

### Test Data Generation

Tests use the Faker library for generating realistic test data:

```python
from faker import Faker
fake = Faker()

# Generate test data
test_url = fake.url()
test_text = fake.text(max_nb_chars=200)
test_email = fake.email()
```

## Performance Testing

### Benchmark Tests

Performance tests use pytest-benchmark for accurate measurements:

```python
def test_command_performance(benchmark):
    result = benchmark(execute_command, test_command)
    assert result.status == "success"
```

### Stress Testing

Stress tests verify system behavior under extreme conditions:

- High concurrent connection loads
- Large data payload processing
- Extended operation duration
- Memory usage validation

### Performance Baselines

Current performance baselines (adjust based on your system):

- **Navigate Command**: < 2.0 seconds
- **Extract Command**: < 0.5 seconds
- **Click Command**: < 0.3 seconds
- **Fill Command**: < 0.2 seconds
- **Wait Command**: < 1.0 seconds (immediate conditions)

## Security Testing

### Vulnerability Categories

Security tests cover multiple vulnerability categories:

- **Input Validation**: XSS, SQL injection, command injection
- **Authentication**: Session management, token validation
- **Authorization**: Permission checks, privilege escalation
- **Data Protection**: Encryption, data leakage prevention
- **Network Security**: SSL/TLS, connection security

### Penetration Testing

Advanced security tests simulate real attack scenarios:

- Session fixation attacks
- Timing attacks
- Brute force attempts
- Network eavesdropping
- Privilege escalation

## Browser Compatibility

### Supported Browsers

- **Chromium**: Primary test browser
- **Firefox**: Secondary compatibility testing
- **WebKit**: Safari compatibility testing

### Platform Testing

Cross-platform testing covers:

- **Windows**: Windows 10/11 compatibility
- **Linux**: Ubuntu, CentOS, Alpine Linux
- **macOS**: macOS 10.15+ compatibility

### Viewport Testing

Responsive design testing across multiple viewports:

- Desktop: 1920x1080, 1366x768
- Tablet: 1024x768, 768x1024
- Mobile: 375x812, 360x640

## Continuous Integration

### GitHub Actions

The test suite includes GitHub Actions configuration (`.github/workflows/test.yml`):

- **Matrix Testing**: Multiple OS and Python versions
- **Parallel Jobs**: Separate jobs for different test categories
- **Artifact Collection**: Test reports and coverage data
- **Failure Notifications**: Slack/email notifications on test failures

### Local CI Simulation

Simulate CI environment locally:

```bash
# Run CI-like test matrix
for python_version in 3.8 3.9 3.10 3.11 3.12; do
    ./scripts/run_tests.sh --python $python_version
done
```

## Test Development Guidelines

### Writing New Tests

1. **Follow Naming Conventions**: Use `test_` prefix for test functions
2. **Use Descriptive Names**: Test names should describe the scenario
3. **Apply Proper Markers**: Mark tests with appropriate categories
4. **Include Docstrings**: Document test purpose and expectations
5. **Use Fixtures**: Leverage existing fixtures for setup/teardown

### Test Structure Example

```python
@pytest.mark.unit
@pytest.mark.fast
async def test_command_validation_with_invalid_selector():
    """Test that invalid selectors are properly rejected."""
    command = CommandRequest(
        method="click",
        selector="invalid]]selector[[syntax"
    )
    
    with pytest.raises(ValidationError) as exc_info:
        await validate_command(command)
        
    assert "INVALID_SELECTOR" in str(exc_info.value)
    assert "syntax" in str(exc_info.value).lower()
```

### Async Test Guidelines

For async tests:

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test asynchronous operation."""
    result = await async_function()
    assert result.success is True
```

### Mock Usage

Use mocks for external dependencies:

```python
@patch('aux.browser.manager.playwright')
async def test_browser_startup(mock_playwright):
    """Test browser manager startup with mocked playwright."""
    mock_playwright.chromium.launch.return_value = AsyncMock()
    
    manager = BrowserManager(test_config)
    await manager.start()
    
    mock_playwright.chromium.launch.assert_called_once()
```

## Troubleshooting

### Common Issues

**Browser Launch Failures**
```bash
# Install browser dependencies
playwright install-deps chromium

# Check browser executable
which google-chrome
which chromium-browser
```

**Permission Errors**
```bash
# Fix file permissions
chmod +x scripts/run_tests.sh

# Check temporary directory access
ls -la /tmp
```

**Network Timeouts**
```bash
# Increase test timeout
export AUX_TEST_TIMEOUT=600

# Check network connectivity
ping google.com
```

**Memory Issues**
```bash
# Reduce parallel workers
./scripts/run_tests.sh --jobs 1

# Monitor memory usage
htop
```

### Debug Mode

Enable debug logging for detailed output:

```bash
export AUX_LOG_LEVEL=DEBUG
./scripts/run_tests.sh --verbose
```

### Test Isolation

If tests are interfering with each other:

```bash
# Run tests in isolation
pytest --forked

# Clear all cache between runs
./scripts/run_tests.sh --clean
```

## Coverage Reports

### Viewing Coverage

After running tests with coverage:

```bash
# Open HTML coverage report
open htmlcov/index.html

# View terminal coverage summary
coverage report

# Generate XML for CI integration
coverage xml
```

### Coverage Goals

- **Overall Coverage**: 90%+ target
- **Critical Modules**: 95%+ target
- **Branch Coverage**: 85%+ target
- **Security Modules**: 98%+ target

## Performance Monitoring

### Benchmark Reports

Performance benchmark results are saved automatically:

```bash
# View benchmark history
cat .benchmarks/Linux-CPython-3.11/benchmark_history.json

# Compare benchmark runs
pytest-benchmark compare
```

### Memory Profiling

For memory usage analysis:

```bash
# Install memory profiler
pip install memory-profiler

# Profile specific test
python -m memory_profiler tests/performance/test_memory_usage.py
```

## Contributing

### Adding New Tests

1. **Choose Appropriate Directory**: Place tests in the correct category
2. **Follow Existing Patterns**: Use similar structure to existing tests
3. **Add Documentation**: Include docstrings and comments
4. **Update Markers**: Add appropriate pytest markers
5. **Test Your Tests**: Ensure new tests pass and don't break existing ones

### Test Review Checklist

- [ ] Test has clear, descriptive name
- [ ] Test includes proper docstring
- [ ] Appropriate markers are applied
- [ ] Test follows DRY principles
- [ ] Mock objects are used appropriately
- [ ] Test is deterministic (no random failures)
- [ ] Test cleans up after itself
- [ ] Test covers both positive and negative cases

## Support

For questions or issues with the test suite:

1. Check this documentation first
2. Review existing test examples
3. Check the troubleshooting section
4. Open an issue with detailed information
5. Include test output and error messages

## Appendix

### Complete Test Command Reference

```bash
# Basic test execution
./scripts/run_tests.sh                    # All tests
./scripts/run_tests.sh -t unit           # Unit tests only
./scripts/run_tests.sh -t integration    # Integration tests only
./scripts/run_tests.sh -t security       # Security tests only
./scripts/run_tests.sh -t performance    # Performance tests only
./scripts/run_tests.sh -t e2e            # End-to-end tests only
./scripts/run_tests.sh -t regression     # Regression tests only
./scripts/run_tests.sh -t smoke          # Smoke tests only

# Test configuration options
./scripts/run_tests.sh --coverage 95     # Custom coverage threshold
./scripts/run_tests.sh --jobs 4          # Parallel execution
./scripts/run_tests.sh --timeout 600     # Custom timeout
./scripts/run_tests.sh --verbose         # Verbose output
./scripts/run_tests.sh --fast-only       # Fast tests only
./scripts/run_tests.sh --smoke-only      # Smoke tests only

# Maintenance and debugging
./scripts/run_tests.sh --clean           # Clean artifacts first
./scripts/run_tests.sh --no-reports      # Skip HTML reports
./scripts/run_tests.sh --retry-failed    # Retry failed tests
./scripts/run_tests.sh --strict          # Strict mode (fail on warnings)

# Python version specific
./scripts/run_tests.sh --python 3.11     # Specific Python version

# Combining options
./scripts/run_tests.sh -t unit --fast-only --coverage 95 --verbose
```

### Environment Variables Reference

```bash
# Core test configuration
AUX_TEST_MODE=true              # Enable test mode
AUX_LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)

# Browser configuration
AUX_TEST_BROWSER=chromium       # Browser engine (chromium, firefox, webkit)
AUX_TEST_HEADLESS=true          # Headless mode (true/false)
AUX_TEST_TIMEOUT=300            # Test timeout in seconds

# Advanced configuration
PYTEST_ARGS="--maxfail=5"       # Additional pytest arguments
FORCE_COLOR=1                   # Force colored output
PYTHONPATH=/path/to/src         # Python path configuration
```

This comprehensive test suite ensures the AUX Protocol maintains high quality, security, and performance standards across all supported platforms and use cases.