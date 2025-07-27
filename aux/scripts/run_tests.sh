#!/bin/bash
# AUX Protocol Test Suite Runner Script
# Comprehensive test execution with various options and configurations

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
REPORTS_DIR="$PROJECT_ROOT/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
TEST_TYPE="all"
PYTHON_VERSION=""
COVERAGE_THRESHOLD=90
PARALLEL_WORKERS="auto"
VERBOSE=false
FAST_ONLY=false
SMOKE_ONLY=false
CLEAN_BEFORE=false
GENERATE_REPORTS=true
TIMEOUT=300
RETRY_FAILED=false
STRICT_MODE=false

# Function to display usage
show_usage() {
    cat << EOF
AUX Protocol Test Suite Runner

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Test type to run (all, unit, integration, security, performance, e2e, regression, smoke)
    -p, --python VERSION    Python version to use (default: current)
    -c, --coverage PERCENT  Coverage threshold percentage (default: 90)
    -j, --jobs NUM          Number of parallel workers (default: auto)
    -v, --verbose           Enable verbose output
    -f, --fast-only         Run only fast tests
    -s, --smoke-only        Run only smoke tests
    --clean                 Clean previous test artifacts before running
    --no-reports            Skip generating HTML reports
    --timeout SECONDS       Timeout per test in seconds (default: 300)
    --retry-failed          Retry failed tests once
    --strict                Enable strict mode (fail on warnings)
    -h, --help              Show this help message

Examples:
    $0                                  # Run all tests
    $0 -t unit -f                      # Run only fast unit tests
    $0 -t security --verbose           # Run security tests with verbose output
    $0 -t performance -j 4             # Run performance tests with 4 workers
    $0 --smoke-only --clean             # Clean and run smoke tests only
    $0 -t all --coverage 95 --strict   # Run all tests with 95% coverage in strict mode

Test Types:
    all         - Run all test categories (default)
    unit        - Unit tests for individual components
    integration - Integration tests for component interactions
    security    - Security vulnerability and penetration tests
    performance - Performance benchmarking and load tests
    e2e         - End-to-end workflow tests
    regression  - Backward compatibility and regression tests
    smoke       - Quick smoke tests for basic functionality

Environment Variables:
    AUX_TEST_MODE          - Set to 'true' to enable test mode
    AUX_LOG_LEVEL          - Set logging level (DEBUG, INFO, WARNING, ERROR)
    AUX_TEST_BROWSER       - Browser to use for testing (chromium, firefox, webkit)
    AUX_TEST_HEADLESS      - Set to 'false' to run browser tests in headed mode
    AUX_TEST_TIMEOUT       - Override default test timeout
    PYTEST_ARGS            - Additional pytest arguments

EOF
}

# Function to log messages with colors
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${timestamp} [${BLUE}INFO${NC}] $message"
            ;;
        "SUCCESS")
            echo -e "${timestamp} [${GREEN}SUCCESS${NC}] $message"
            ;;
        "WARNING")
            echo -e "${timestamp} [${YELLOW}WARNING${NC}] $message"
            ;;
        "ERROR")
            echo -e "${timestamp} [${RED}ERROR${NC}] $message"
            ;;
        *)
            echo -e "${timestamp} $message"
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check Python version
    if [ -n "$PYTHON_VERSION" ]; then
        if ! command -v "python$PYTHON_VERSION" &> /dev/null; then
            log "ERROR" "Python $PYTHON_VERSION not found"
            exit 1
        fi
        PYTHON_CMD="python$PYTHON_VERSION"
    else
        PYTHON_CMD="python3"
    fi
    
    # Check Python version compatibility
    local python_version=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version 3.8" | awk '{print ($1 < $2)}') -eq 1 ]]; then
        log "ERROR" "Python version $python_version is not supported. Minimum required: 3.8"
        exit 1
    fi
    
    log "INFO" "Using Python $python_version"
    
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_DEFAULT_ENV" ]; then
        log "WARNING" "Not running in a virtual environment. Consider using a venv or conda environment."
    fi
    
    # Check if required packages are installed
    if ! $PYTHON_CMD -c "import pytest" &> /dev/null; then
        log "ERROR" "pytest is not installed. Run: pip install -e '[dev]'"
        exit 1
    fi
    
    log "SUCCESS" "Prerequisites check passed"
}

# Function to set up test environment
setup_environment() {
    log "INFO" "Setting up test environment..."
    
    # Create necessary directories
    mkdir -p "$LOGS_DIR" "$REPORTS_DIR" "htmlcov" "test_data" "temp"
    
    # Set environment variables
    export AUX_TEST_MODE="true"
    export AUX_LOG_LEVEL="${AUX_LOG_LEVEL:-INFO}"
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    export FORCE_COLOR=1
    
    # Browser configuration
    export AUX_TEST_BROWSER="${AUX_TEST_BROWSER:-chromium}"
    export AUX_TEST_HEADLESS="${AUX_TEST_HEADLESS:-true}"
    export AUX_TEST_TIMEOUT="${AUX_TEST_TIMEOUT:-$TIMEOUT}"
    
    # Install playwright browsers if needed
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "e2e" || "$TEST_TYPE" == "integration" ]]; then
        log "INFO" "Installing playwright browsers..."
        $PYTHON_CMD -m playwright install chromium --with-deps
    fi
    
    log "SUCCESS" "Test environment set up"
}

# Function to clean previous artifacts
clean_artifacts() {
    log "INFO" "Cleaning previous test artifacts..."
    
    # Remove old reports and coverage data
    rm -rf "$REPORTS_DIR"/* "htmlcov"/* ".coverage" "coverage.xml" "coverage.json"
    rm -rf ".pytest_cache" ".benchmarks" "test_data"/* "temp"/*
    rm -f "$LOGS_DIR"/pytest*.log
    
    # Remove temporary files
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name ".coverage.*" -delete 2>/dev/null || true
    
    log "SUCCESS" "Artifacts cleaned"
}

# Function to build pytest command
build_pytest_command() {
    local cmd="$PYTHON_CMD -m pytest"
    
    # Test selection based on type
    case $TEST_TYPE in
        "unit")
            cmd="$cmd tests/unit/"
            cmd="$cmd -m 'unit'"
            ;;
        "integration")
            cmd="$cmd tests/integration/"
            cmd="$cmd -m 'integration'"
            ;;
        "security")
            cmd="$cmd tests/security/"
            cmd="$cmd -m 'security'"
            ;;
        "performance")
            cmd="$cmd tests/performance/"
            cmd="$cmd -m 'performance'"
            ;;
        "e2e")
            cmd="$cmd tests/e2e/"
            cmd="$cmd -m 'e2e'"
            ;;
        "regression")
            cmd="$cmd tests/regression/"
            cmd="$cmd -m 'regression'"
            ;;
        "smoke")
            cmd="$cmd -m 'smoke or (unit and fast)'"
            ;;
        "all")
            cmd="$cmd tests/"
            ;;
        *)
            log "ERROR" "Unknown test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Coverage configuration
    if [[ "$TEST_TYPE" != "performance" && "$TEST_TYPE" != "smoke" ]]; then
        cmd="$cmd --cov=src/aux"
        cmd="$cmd --cov-branch"
        cmd="$cmd --cov-report=term-missing:skip-covered"
        cmd="$cmd --cov-fail-under=$COVERAGE_THRESHOLD"
        
        if [ "$GENERATE_REPORTS" = true ]; then
            cmd="$cmd --cov-report=html:htmlcov"
            cmd="$cmd --cov-report=xml:coverage.xml"
            cmd="$cmd --cov-report=json:coverage.json"
        fi
    fi
    
    # Parallel execution
    if [[ "$PARALLEL_WORKERS" != "1" ]]; then
        cmd="$cmd -n $PARALLEL_WORKERS"
    fi
    
    # Output and reporting
    cmd="$cmd --timeout=$TIMEOUT"
    cmd="$cmd --timeout-method=thread"
    
    if [ "$VERBOSE" = true ]; then
        cmd="$cmd -v"
    fi
    
    if [ "$FAST_ONLY" = true ]; then
        cmd="$cmd --fast-only"
    fi
    
    if [ "$SMOKE_ONLY" = true ]; then
        cmd="$cmd --smoke-only"
    fi
    
    if [ "$STRICT_MODE" = true ]; then
        cmd="$cmd --strict-markers --strict-config"
    fi
    
    if [ "$RETRY_FAILED" = true ]; then
        cmd="$cmd --lf --ff"
    fi
    
    # Report generation
    if [ "$GENERATE_REPORTS" = true ]; then
        cmd="$cmd --junit-xml=$REPORTS_DIR/junit-$TEST_TYPE.xml"
        cmd="$cmd --html=$REPORTS_DIR/$TEST_TYPE-report.html"
        cmd="$cmd --self-contained-html"
    fi
    
    # Performance-specific options
    if [[ "$TEST_TYPE" == "performance" || "$TEST_TYPE" == "all" ]]; then
        cmd="$cmd --benchmark-sort=mean"
        cmd="$cmd --benchmark-warmup=on"
        cmd="$cmd --benchmark-autosave"
        cmd="$cmd --benchmark-json=$REPORTS_DIR/benchmark-results.json"
    fi
    
    # Additional pytest arguments from environment
    if [ -n "$PYTEST_ARGS" ]; then
        cmd="$cmd $PYTEST_ARGS"
    fi
    
    echo "$cmd"
}

# Function to run tests
run_tests() {
    log "INFO" "Starting $TEST_TYPE tests..."
    
    local start_time=$(date +%s)
    local pytest_cmd=$(build_pytest_command)
    
    log "INFO" "Running command: $pytest_cmd"
    
    # Run the tests
    if eval "$pytest_cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "SUCCESS" "Tests completed successfully in ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "ERROR" "Tests failed after ${duration}s"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    log "INFO" "Generating test summary..."
    
    local summary_file="$REPORTS_DIR/test-summary.txt"
    
    cat > "$summary_file" << EOF
AUX Protocol Test Suite Summary
===============================

Test Configuration:
- Type: $TEST_TYPE
- Python: $(${PYTHON_CMD} --version)
- Coverage Threshold: $COVERAGE_THRESHOLD%
- Parallel Workers: $PARALLEL_WORKERS
- Timeout: ${TIMEOUT}s
- Fast Only: $FAST_ONLY
- Smoke Only: $SMOKE_ONLY
- Strict Mode: $STRICT_MODE

Environment:
- Test Mode: $AUX_TEST_MODE
- Log Level: $AUX_LOG_LEVEL
- Browser: $AUX_TEST_BROWSER
- Headless: $AUX_TEST_HEADLESS

Generated Reports:
EOF
    
    # List generated reports
    if [ -d "$REPORTS_DIR" ]; then
        echo "" >> "$summary_file"
        find "$REPORTS_DIR" -name "*.html" -o -name "*.xml" -o -name "*.json" | while read -r file; do
            echo "- $(basename "$file")" >> "$summary_file"
        done
    fi
    
    # Coverage information
    if [ -f "coverage.xml" ]; then
        echo "" >> "$summary_file"
        echo "Coverage Report: htmlcov/index.html" >> "$summary_file"
    fi
    
    log "SUCCESS" "Summary generated: $summary_file"
}

# Function to open reports
open_reports() {
    if [ "$GENERATE_REPORTS" = true ] && command -v xdg-open &> /dev/null; then
        log "INFO" "Opening test reports..."
        
        # Open HTML coverage report
        if [ -f "htmlcov/index.html" ]; then
            xdg-open "htmlcov/index.html" 2>/dev/null &
        fi
        
        # Open test report
        local test_report="$REPORTS_DIR/$TEST_TYPE-report.html"
        if [ -f "$test_report" ]; then
            xdg-open "$test_report" 2>/dev/null &
        fi
    fi
}

# Function to display quick stats
show_stats() {
    log "INFO" "Test Statistics:"
    
    # Count test files
    local unit_tests=$(find tests/unit -name "test_*.py" 2>/dev/null | wc -l)
    local integration_tests=$(find tests/integration -name "test_*.py" 2>/dev/null | wc -l)
    local security_tests=$(find tests/security -name "test_*.py" 2>/dev/null | wc -l)
    local performance_tests=$(find tests/performance -name "test_*.py" 2>/dev/null | wc -l)
    local e2e_tests=$(find tests/e2e -name "test_*.py" 2>/dev/null | wc -l)
    local regression_tests=$(find tests/regression -name "test_*.py" 2>/dev/null | wc -l)
    
    echo "  Unit Tests: $unit_tests files"
    echo "  Integration Tests: $integration_tests files"
    echo "  Security Tests: $security_tests files"
    echo "  Performance Tests: $performance_tests files"
    echo "  E2E Tests: $e2e_tests files"
    echo "  Regression Tests: $regression_tests files"
    
    # Show total test functions (approximate)
    local total_test_functions=$(find tests -name "test_*.py" -exec grep -l "def test_" {} \; | xargs grep "def test_" | wc -l)
    echo "  Total Test Functions: ~$total_test_functions"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -p|--python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -j|--jobs)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--fast-only)
            FAST_ONLY=true
            shift
            ;;
        -s|--smoke-only)
            SMOKE_ONLY=true
            TEST_TYPE="smoke"
            shift
            ;;
        --clean)
            CLEAN_BEFORE=true
            shift
            ;;
        --no-reports)
            GENERATE_REPORTS=false
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --retry-failed)
            RETRY_FAILED=true
            shift
            ;;
        --strict)
            STRICT_MODE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Show header
    echo -e "${BLUE}"
    echo "========================================"
    echo "    AUX Protocol Test Suite Runner"
    echo "========================================"
    echo -e "${NC}"
    
    # Show quick stats
    show_stats
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Clean artifacts if requested
    if [ "$CLEAN_BEFORE" = true ]; then
        clean_artifacts
    fi
    
    # Set up environment
    setup_environment
    
    # Run tests
    if run_tests; then
        # Generate summary
        if [ "$GENERATE_REPORTS" = true ]; then
            generate_summary
        fi
        
        # Open reports if in interactive mode
        if [ -t 1 ] && [ "$GENERATE_REPORTS" = true ]; then
            read -p "Open test reports? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open_reports
            fi
        fi
        
        log "SUCCESS" "All tests completed successfully!"
        exit 0
    else
        log "ERROR" "Test execution failed. Check the logs for details."
        
        if [ "$RETRY_FAILED" = true ]; then
            log "INFO" "Retrying failed tests..."
            if run_tests; then
                log "SUCCESS" "Tests passed on retry!"
                exit 0
            fi
        fi
        
        exit 1
    fi
}

# Run main function
main "$@"
