# AUX Protocol Testing Quick Reference Guide

## Essential Commands

```bash
# Quick smoke test (5 minutes)
./scripts/run_tests.sh --smoke-only

# Full test suite (15-30 minutes)
./scripts/run_tests.sh

# Fast development cycle (2-3 minutes)
./scripts/run_tests.sh -t unit --fast-only

# Pre-commit validation (8-10 minutes)
./scripts/run_tests.sh -t unit -t integration --coverage 90
```

## Test Categories

| Category | Duration | Purpose |
|----------|----------|---------|
| `smoke` | 2-5 min | Basic functionality verification |
| `unit` | 3-8 min | Component-level testing |
| `integration` | 5-12 min | Component interaction testing |
| `security` | 8-15 min | Vulnerability and attack testing |
| `performance` | 10-20 min | Benchmarking and load testing |
| `e2e` | 15-30 min | Real browser automation testing |
| `regression` | 10-25 min | Backward compatibility testing |

## Development Workflow

### 1. Before Starting Development
```bash
# Verify baseline - all tests should pass
./scripts/run_tests.sh --smoke-only
```

### 2. During Development (Test-Driven Development)
```bash
# Write test first, watch it fail
pytest tests/unit/test_new_feature.py::test_specific_case -v

# Implement feature, watch test pass
pytest tests/unit/test_new_feature.py::test_specific_case -v

# Run related tests
pytest tests/unit/test_new_feature.py -v
```

### 3. Before Committing
```bash
# Run comprehensive validation
./scripts/run_tests.sh -t unit -t integration --coverage 95

# Check specific areas you modified
pytest tests/unit/test_commands.py tests/integration/ -v
```

### 4. Before Pull Request
```bash
# Full test suite with strict validation
./scripts/run_tests.sh --strict --coverage 95

# Performance regression check
./scripts/run_tests.sh -t performance --verbose
```

## Writing Tests

### Test Function Template
```python
@pytest.mark.unit  # or integration, security, performance, e2e, regression
@pytest.mark.fast  # or slow
async def test_descriptive_name_of_what_youre_testing():
    """
    Brief description of what this test validates.
    
    This test ensures that [specific behavior] works correctly
    when [specific conditions] are met.
    """
    # Arrange: Set up test data and conditions
    test_data = create_test_data()
    
    # Act: Execute the code under test
    result = await function_under_test(test_data)
    
    # Assert: Verify the expected outcome
    assert result.status == "success"
    assert result.data.contains_expected_value()
```

### Common Test Patterns

**Testing Command Validation**
```python
@pytest.mark.unit
def test_command_validation_rejects_invalid_input():
    """Test that invalid command parameters are properly rejected."""
    invalid_command = {"method": "click"}  # Missing required selector
    
    with pytest.raises(ValidationError) as exc_info:
        validate_command(invalid_command)
    
    assert "selector" in str(exc_info.value)
```

**Testing Async Operations**
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_browser_operation():
    """Test async browser operation completes successfully."""
    browser_manager = BrowserManager(test_config)
    
    await browser_manager.start()
    result = await browser_manager.execute_command(test_command)
    await browser_manager.stop()
    
    assert result.success is True
```

**Testing with Mocks**
```python
@pytest.mark.unit
@patch('aux.browser.playwright')
def test_browser_with_mock(mock_playwright):
    """Test browser operations with mocked dependencies."""
    mock_playwright.chromium.launch.return_value = AsyncMock()
    
    manager = BrowserManager(test_config)
    # Test logic here
    
    mock_playwright.chromium.launch.assert_called_once()
```

## Debugging Failed Tests

### 1. Get Detailed Output
```bash
# Run with maximum verbosity
pytest tests/failing_test.py -vvv --tb=long

# Add debug logging
AUX_LOG_LEVEL=DEBUG pytest tests/failing_test.py -v -s
```

### 2. Isolate the Problem
```bash
# Run single test function
pytest tests/unit/test_commands.py::test_specific_function -v

# Run without parallel execution
pytest tests/failing_test.py -v --no-cov -x
```

### 3. Check Test Environment
```bash
# Verify browser installation
playwright install --dry-run chromium

# Check permissions and file access
ls -la tests/
ls -la reports/
```

### 4. Common Fixes

**Browser Launch Issues**
```bash
# Install browser dependencies
playwright install-deps

# Set headless mode
export AUX_TEST_HEADLESS=true
```

**Permission Issues**
```bash
# Fix script permissions
chmod +x scripts/run_tests.sh

# Check temp directory
ls -la /tmp/
```

**Timeout Issues**
```bash
# Increase timeout
export AUX_TEST_TIMEOUT=600

# Run specific slow tests
pytest -m slow --timeout=900
```

## Performance Testing

### Benchmark New Features
```python
@pytest.mark.performance
def test_new_feature_performance(benchmark):
    """Benchmark performance of new feature."""
    result = benchmark(new_feature_function, test_input)
    
    # Benchmark automatically compares against baseline
    assert result.success is True
```

### Memory Usage Testing
```python
@pytest.mark.performance
def test_memory_usage():
    """Test memory usage stays within acceptable limits."""
    import psutil
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Execute memory-intensive operation
    perform_operation()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Should not increase by more than 50MB
    assert memory_increase < 50 * 1024 * 1024
```

## Security Testing

### Input Validation Testing
```python
@pytest.mark.security
def test_xss_prevention():
    """Test that XSS attacks are properly prevented."""
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>"
    ]
    
    for malicious_input in malicious_inputs:
        with pytest.raises(SecurityError):
            process_user_input(malicious_input)
```

### Authentication Testing
```python
@pytest.mark.security
async def test_unauthorized_access_prevention():
    """Test that unauthorized access is properly prevented."""
    client = AUXClient(url=test_url, api_key="invalid_key")
    
    with pytest.raises(AuthenticationError):
        await client.connect()
```

## CI/CD Integration

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit tests..."
./scripts/run_tests.sh -t unit --fast-only --no-reports

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi

echo "✅ Tests passed. Proceeding with commit."
```

### GitHub Actions Integration
The test suite automatically runs on:
- Pull requests to main branch
- Pushes to main branch
- Scheduled nightly runs

## Troubleshooting

### Common Error Messages

**"Browser launch failed"**
```bash
# Solution: Install browser dependencies
playwright install chromium --with-deps
export AUX_TEST_HEADLESS=true
```

**"Permission denied"**
```bash
# Solution: Fix permissions
chmod +x scripts/run_tests.sh
sudo chown -R $USER:$USER reports/ logs/
```

**"Tests hanging/timeout"**
```bash
# Solution: Increase timeout and check for deadlocks
export AUX_TEST_TIMEOUT=600
pytest --timeout=300 --timeout-method=thread
```

**"Import errors"**
```bash
# Solution: Check PYTHONPATH and virtual environment
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
source venv/bin/activate
pip install -e .
```

### Getting Help

1. **Check the full README**: `tests/README.md`
2. **Review test examples**: Look at existing tests in the same category
3. **Check CI logs**: Review GitHub Actions output for failures
4. **Enable debug logging**: `AUX_LOG_LEVEL=DEBUG`
5. **Run with maximum verbosity**: `pytest -vvv --tb=long`

## Test Markers Reference

```python
# Test categories
@pytest.mark.unit           # Unit test
@pytest.mark.integration    # Integration test
@pytest.mark.security       # Security test
@pytest.mark.performance    # Performance test
@pytest.mark.e2e           # End-to-end test
@pytest.mark.regression     # Regression test

# Speed categories
@pytest.mark.fast          # Fast test (<5 seconds)
@pytest.mark.slow          # Slow test (>30 seconds)

# Requirements
@pytest.mark.browser       # Requires browser
@pytest.mark.network       # Requires network
@pytest.mark.auth          # Authentication test

# Special categories
@pytest.mark.smoke         # Smoke test
@pytest.mark.critical      # Critical path test
@pytest.mark.flaky         # May fail intermittently

# Platform specific
@pytest.mark.windows       # Windows only
@pytest.mark.linux         # Linux only
@pytest.mark.macos         # macOS only
```

## Example Test Execution Commands

```bash
# Development workflow examples
pytest -m "unit and fast" -v                    # Quick unit tests
pytest -m "unit or integration" --cov           # Core functionality with coverage
pytest -m "not slow" -x --tb=short             # All fast tests, stop on first failure
pytest tests/unit/ -k "command" --no-cov       # Unit tests matching "command" pattern

# Specific scenarios
pytest -m smoke --maxfail=1                     # Smoke tests, stop after 1 failure
pytest -m "security and not slow" -v           # Fast security tests only  
pytest -m performance --benchmark-only         # Performance benchmarks only
pytest -m "e2e and browser" --headed           # E2E tests in headed browser mode

# CI simulation
pytest --cov=src/aux --cov-fail-under=90       # Enforce coverage threshold
pytest --strict-markers --strict-config        # Strict validation mode
pytest -n auto --dist=loadscope                # Parallel execution
```

This quick reference should get you productive with the AUX Protocol test suite immediately!