#!/bin/bash
#
# AUX Browser Manager - Comprehensive Test Runner
#
# This script runs the complete test suite for the AUX browser manager,
# including unit tests, integration tests, and validation tests.

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PYTHONPATH="${PWD}/src"
export PYTHONPATH

echo -e "${BLUE}🧪 AUX Browser Manager - Comprehensive Test Suite${NC}"
echo "=================================================================="
echo "Python Path: $PYTHONPATH"
echo "Working Directory: $(pwd)"
echo ""

# Function to run tests with proper error handling
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}Running $test_name...${NC}"
    echo "Command: $test_command"
    echo ""
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        echo "Test command was: $test_command"
        return 1
    fi
    echo ""
}

# Parse command line arguments
QUICK_MODE=false
VERBOSE=false
SKIP_INTEGRATION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick              Run only essential tests"
            echo "  --verbose, -v        Enable verbose output"  
            echo "  --skip-integration   Skip integration tests (unit tests only)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                   # Run all tests"
            echo "  $0 --quick           # Run essential tests only"
            echo "  $0 --verbose         # Run with verbose output"
            echo "  $0 --skip-integration # Run unit tests only"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set verbose flags
PYTEST_VERBOSE=""
RUNNER_VERBOSE=""
if [ "$VERBOSE" = true ]; then
    PYTEST_VERBOSE="-v"
    RUNNER_VERBOSE="--verbose"
fi

# Set quick mode flags
RUNNER_QUICK=""
if [ "$QUICK_MODE" = true ]; then
    RUNNER_QUICK="--quick"
    echo -e "${YELLOW}⚡ Quick mode enabled - running essential tests only${NC}"
    echo ""
fi

echo -e "${BLUE}Step 1: Unit Tests${NC}"
echo "=================================================================="

# Run unit tests for browser session
run_test "Browser Session Unit Tests" \
    "python -m pytest tests/test_browser_manager.py::TestBrowserSession $PYTEST_VERBOSE"

# Run unit tests for browser manager
run_test "Browser Manager Unit Tests" \
    "python -m pytest tests/test_browser_manager.py::TestBrowserManager $PYTEST_VERBOSE"

# Run browser command tests
if [ "$QUICK_MODE" = false ]; then
    run_test "Navigate Command Tests" \
        "python -m pytest tests/test_browser_manager.py::TestNavigateCommand $PYTEST_VERBOSE"
    
    run_test "Click Command Tests" \
        "python -m pytest tests/test_browser_manager.py::TestClickCommand $PYTEST_VERBOSE"
    
    run_test "Fill Command Tests" \
        "python -m pytest tests/test_browser_manager.py::TestFillCommand $PYTEST_VERBOSE"
    
    run_test "Extract Command Tests" \
        "python -m pytest tests/test_browser_manager.py::TestExtractCommand $PYTEST_VERBOSE"
    
    run_test "Wait Command Tests" \
        "python -m pytest tests/test_browser_manager.py::TestWaitCommand $PYTEST_VERBOSE"
fi

# Run error handling and performance tests
run_test "Error Handling Tests" \
    "python -m pytest tests/test_browser_manager.py::TestErrorHandling $PYTEST_VERBOSE"

if [ "$QUICK_MODE" = false ]; then
    run_test "Performance & Cleanup Tests" \
        "python -m pytest tests/test_browser_manager.py::TestPerformanceAndCleanup $PYTEST_VERBOSE"
    
    run_test "Command Validation Tests" \
        "python -m pytest tests/test_browser_manager.py::TestCommandValidation $PYTEST_VERBOSE"
fi

# Integration tests (if not skipped)
if [ "$SKIP_INTEGRATION" = false ]; then
    echo -e "${BLUE}Step 2: Integration Tests${NC}"
    echo "=================================================================="
    
    echo -e "${YELLOW}Note: Integration tests require Playwright browser installation${NC}"
    echo -e "${YELLOW}Run 'playwright install chromium' if tests fail${NC}"
    echo ""
    
    # Check if Playwright is available
    if command -v playwright >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Playwright CLI found${NC}"
    else
        echo -e "${YELLOW}⚠️  Playwright CLI not found - integration tests may fail${NC}"
    fi
    echo ""
    
    # Run standalone test runner validation
    run_test "Standalone Test Runner Validation" \
        "python tests/run_browser_tests.py $RUNNER_QUICK $RUNNER_VERBOSE"
    
    # Run pytest integration tests (if not quick mode)
    if [ "$QUICK_MODE" = false ]; then
        run_test "Pytest Integration Tests" \
            "python -m pytest tests/test_integration_live.py $PYTEST_VERBOSE"
    fi
else
    echo -e "${YELLOW}⏭️  Skipping integration tests as requested${NC}"
    echo ""
fi

# Final summary
echo -e "${BLUE}Step 3: Test Summary${NC}"
echo "=================================================================="

# Run a summary command to show overall results
if [ "$QUICK_MODE" = false ] && [ "$SKIP_INTEGRATION" = false ]; then
    echo -e "${GREEN}✅ All test categories completed successfully!${NC}"
    echo ""
    echo "Test Coverage:"
    echo "  ✅ Unit Tests (BrowserSession, BrowserManager)"
    echo "  ✅ Command Tests (Navigate, Click, Fill, Extract, Wait)"
    echo "  ✅ Error Handling Tests"
    echo "  ✅ Performance Tests"
    echo "  ✅ Integration Tests"
    echo "  ✅ Validation Tests"
elif [ "$QUICK_MODE" = true ]; then
    echo -e "${GREEN}✅ Quick test suite completed successfully!${NC}"
    echo ""
    echo "Quick Test Coverage:"
    echo "  ✅ Essential Unit Tests"
    echo "  ✅ Error Handling Tests"
    echo "  ✅ Basic Integration Tests"
elif [ "$SKIP_INTEGRATION" = true ]; then
    echo -e "${GREEN}✅ Unit test suite completed successfully!${NC}"
    echo ""
    echo "Unit Test Coverage:"
    echo "  ✅ All Unit Tests"
    echo "  ✅ All Command Tests"
    echo "  ✅ Error Handling Tests"
    echo "  ✅ Performance Tests"
fi

echo ""
echo -e "${BLUE}🎉 AUX Browser Manager test suite execution completed!${NC}"
echo ""

# Usage examples
echo "Next Steps:"
echo "  • Run with coverage: pytest tests/ --cov=aux.browser --cov-report=html"
echo "  • Debug specific test: pytest tests/test_browser_manager.py::TestName::test_method -v -s"
echo "  • Run visual debugging: python tests/run_browser_tests.py --no-headless --no-cleanup"
echo ""