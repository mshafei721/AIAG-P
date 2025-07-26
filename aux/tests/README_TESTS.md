# AUX Browser Manager Test Suite

This directory contains a comprehensive test suite for the AUX browser manager functionality, providing thorough testing of all browser automation capabilities.

## Test Files Overview

### Core Test Files

- **`test_browser_manager.py`** - Comprehensive unit and integration tests for the browser manager
- **`test_integration_live.py`** - Live integration tests using real browser instances  
- **`test_pages.py`** - Mock HTML pages for isolated testing without external dependencies
- **`run_browser_tests.py`** - Standalone test runner script for validation

### Test Categories

#### 1. Unit Tests (`test_browser_manager.py`)
- **BrowserSession Tests**: Session lifecycle, activity tracking, cleanup
- **BrowserManager Tests**: Initialization, session management, statistics
- **Command Tests**: All 5 browser commands (navigate, click, fill, extract, wait)
- **Error Handling Tests**: Timeout, element not found, validation errors
- **Performance Tests**: Concurrent sessions, cleanup performance

#### 2. Integration Tests (`test_integration_live.py`)
- **Live Browser Tests**: Real browser automation with self-contained HTML
- **Workflow Tests**: Complete automation workflows  
- **Cross-Command Tests**: Testing command interactions

#### 3. Mock Test Pages (`test_pages.py`)
- **Basic Test Page**: Simple elements for basic automation
- **Form Test Page**: Complex forms for input testing
- **Dynamic Content Page**: Dynamic elements for wait condition testing

## Running the Tests

### Using pytest (Recommended)

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/test_browser_manager.py

# Run only integration tests  
pytest tests/test_integration_live.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=aux.browser --cov-report=html
```

### Using the Standalone Test Runner

```bash
# Run validation tests
python tests/run_browser_tests.py

# Run in visible browser mode (for debugging)
python tests/run_browser_tests.py --no-headless

# Run with verbose output
python tests/run_browser_tests.py --verbose

# Quick test mode (skip longer tests)
python tests/run_browser_tests.py --quick

# Keep browser open for debugging
python tests/run_browser_tests.py --no-cleanup
```

### Manual Integration Test

```bash
# Run integration tests manually
python tests/test_integration_live.py
```

## Test Structure

### Unit Tests Architecture

The unit tests use extensive mocking to isolate components:

```python
# Example test structure
class TestBrowserManager:
    @pytest.fixture
    def manager(self):
        return BrowserManager(headless=True)
    
    @pytest.mark.asyncio
    async def test_feature(self, manager):
        # Test implementation
        pass
```

### Integration Tests Architecture

Integration tests use real browser instances with data URLs:

```python
# Example integration test
async def test_navigation_integration(self, test_runner):
    await test_runner.test_navigation()
    # Validate results
```

## Test Coverage

### Browser Commands Tested

1. **Navigate Command**
   - Basic navigation
   - Wait conditions (load, domcontentloaded, networkidle)
   - Redirects and final URLs
   - Timeout handling
   - Referer headers

2. **Click Command**
   - Element clicking
   - Mouse buttons (left, right, middle)
   - Multiple clicks
   - Force clicking hidden elements
   - Relative positioning
   - Element visibility checks

3. **Fill Command**
   - Text input filling
   - Form field clearing
   - Typing with delays
   - Enter key pressing
   - Input validation
   - Different input types

4. **Extract Command**
   - Text content extraction
   - HTML content extraction
   - Attribute extraction
   - Property extraction
   - Multiple element extraction
   - Whitespace trimming

5. **Wait Command**
   - Load state waiting
   - Element visibility waiting
   - Element attachment waiting
   - Custom JavaScript conditions
   - Text content waiting
   - Timeout handling

### Error Scenarios Tested

- Session not found
- Element not found
- Element not visible/interactable
- Timeout errors
- Navigation failures
- Validation failures
- Browser initialization errors

### Performance Scenarios Tested

- Concurrent session creation
- Session cleanup performance
- Inactive session cleanup
- Resource management
- Memory usage patterns

## Mock Test Pages

The test suite includes self-contained HTML pages for isolated testing:

### Basic Test Page
- Simple buttons and inputs
- Text extraction elements
- Basic interactions

### Form Test Page  
- Complex form elements
- Validation scenarios
- Different input types
- Form submission handling

### Dynamic Content Page
- Timed content appearance
- Loading indicators
- Progress bars
- AJAX simulation

## Debugging Tests

### Verbose Mode
Enable verbose logging to see detailed test execution:

```bash
pytest tests/ -v -s
python tests/run_browser_tests.py --verbose
```

### Visual Debugging
Run tests with visible browser for debugging:

```bash
python tests/run_browser_tests.py --no-headless --no-cleanup
```

### Test Isolation
Run specific test categories:

```bash
# Run only navigation tests
pytest tests/test_browser_manager.py::TestNavigateCommand

# Run only error handling tests
pytest tests/test_browser_manager.py::TestErrorHandling
```

## Continuous Integration

For CI/CD pipelines, use headless mode with timeout controls:

```bash
# CI-friendly test execution
pytest tests/ --tb=short --maxfail=5 --timeout=300
```

## Test Data and Fixtures

### Shared Fixtures
- `manager`: Basic browser manager instance
- `mock_session`: Mock browser session for unit tests
- `test_runner`: Integration test runner

### Test Data
- Self-contained HTML pages as data URLs
- Mock browser responses
- Test command objects
- Expected result patterns

## Dependencies

### Required Packages
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `playwright` - Browser automation
- `pydantic` - Data validation

### Optional Packages
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel test execution
- `pytest-timeout` - Test timeout handling

## Troubleshooting

### Common Issues

1. **Browser fails to start**
   - Install Playwright browsers: `playwright install chromium`
   - Check system dependencies
   - Verify headless mode compatibility

2. **Tests timeout**
   - Increase timeout values in test configuration
   - Check system resources
   - Run with verbose mode to identify slow tests

3. **Element not found errors**
   - Verify test page HTML structure
   - Check CSS selectors
   - Add wait conditions before interactions

4. **Session management errors**
   - Ensure proper test cleanup
   - Check session isolation
   - Verify browser resource management

### Performance Tips

1. **Faster Test Execution**
   - Use headless mode
   - Enable parallel execution with pytest-xdist
   - Use quick mode for validation

2. **Resource Management**
   - Ensure proper cleanup in test fixtures
   - Monitor browser memory usage
   - Use session timeouts appropriately

## Contributing

When adding new tests:

1. Follow existing test patterns and naming conventions
2. Include both success and failure scenarios
3. Add proper documentation and comments
4. Ensure tests are isolated and repeatable
5. Update this README with new test categories

## Test Results

The test suite provides detailed reporting:

- Individual test results with timing
- Category summaries  
- Pass/fail rates
- Error details and debugging information
- Performance metrics

Example output:
```
BROWSER AUTOMATION TEST SUMMARY
============================================================
Total Tests: 25
Passed: 24
Failed: 1
Pass Rate: 96.0%
============================================================
```