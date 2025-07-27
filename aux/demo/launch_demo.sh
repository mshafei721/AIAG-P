#!/bin/bash

# AUX Protocol Demo Launcher
# This script provides an easy way to launch the complete demo environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
HTTP_PORT=3000
WS_PORT=8080
AUTO_OPEN=true
START_AUX_SERVER=true
PYTHON_CMD="python3"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}"
    echo "🚀 AUX Protocol Interactive Demo Launcher"
    echo "========================================="
    echo -e "${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is available
port_available() {
    ! nc -z localhost "$1" 2>/dev/null
}

# Function to detect Python command
detect_python() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.7 or later."
        exit 1
    fi
    
    # Check Python version
    python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    python_major=$(echo $python_version | cut -d'.' -f1)
    python_minor=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 7 ]); then
        print_error "Python 3.7 or later is required. Found: $python_version"
        exit 1
    fi
    
    print_success "Using Python $python_version ($PYTHON_CMD)"
}

# Function to check dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python
    detect_python
    
    # Check if we can import required modules
    if $PYTHON_CMD -c "import asyncio, websockets, http.server" 2>/dev/null; then
        print_success "Python dependencies available"
    else
        print_warning "Some Python dependencies may be missing"
        print_info "Installing basic dependencies..."
        
        if command_exists pip; then
            pip install asyncio websockets 2>/dev/null || true
        elif command_exists pip3; then
            pip3 install asyncio websockets 2>/dev/null || true
        fi
    fi
    
    # Check for nc (netcat) for port checking
    if ! command_exists nc; then
        print_warning "netcat not available - port checking disabled"
    fi
}

# Function to check ports
check_ports() {
    print_info "Checking port availability..."
    
    if command_exists nc; then
        if ! port_available $HTTP_PORT; then
            print_warning "Port $HTTP_PORT is already in use"
            HTTP_PORT=$((HTTP_PORT + 1))
            print_info "Using alternative port: $HTTP_PORT"
        fi
        
        if ! port_available $WS_PORT; then
            print_warning "Port $WS_PORT is already in use"
            WS_PORT=$((WS_PORT + 1))
            print_info "Using alternative port: $WS_PORT"
        fi
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -p, --http-port PORT    HTTP server port (default: 3000)"
    echo "  -w, --ws-port PORT      WebSocket server port (default: 8080)"
    echo "  --no-browser            Don't open browser automatically"
    echo "  --no-aux-server         Start only HTTP server"
    echo "  --python COMMAND        Python command to use (default: auto-detect)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Start with defaults"
    echo "  $0 -p 8000 -w 9000      # Custom ports"
    echo "  $0 --no-browser         # Don't open browser"
    echo "  $0 --no-aux-server      # UI only mode"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -p|--http-port)
            HTTP_PORT="$2"
            shift 2
            ;;
        -w|--ws-port)
            WS_PORT="$2"
            shift 2
            ;;
        --no-browser)
            AUTO_OPEN=false
            shift
            ;;
        --no-aux-server)
            START_AUX_SERVER=false
            shift
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    # Check if we're in the right directory
    if [ ! -f "index.html" ] || [ ! -f "demo.js" ]; then
        print_error "Demo files not found. Please run this script from the demo directory."
        exit 1
    fi
    
    # Check dependencies
    check_dependencies
    
    # Check ports
    check_ports
    
    print_info "Configuration:"
    echo "  HTTP Port: $HTTP_PORT"
    echo "  WebSocket Port: $WS_PORT"
    echo "  Auto-open browser: $AUTO_OPEN"
    echo "  Start AUX server: $START_AUX_SERVER"
    echo "  Python command: $PYTHON_CMD"
    echo ""
    
    # Build Python command arguments
    PYTHON_ARGS=""
    if [ "$AUTO_OPEN" = false ]; then
        PYTHON_ARGS="$PYTHON_ARGS --no-browser"
    fi
    if [ "$START_AUX_SERVER" = false ]; then
        PYTHON_ARGS="$PYTHON_ARGS --no-aux-server"
    fi
    
    # Start the demo server
    print_info "Starting AUX Protocol Demo Server..."
    
    if [ -f "serve_demo.py" ]; then
        $PYTHON_CMD serve_demo.py --http-port $HTTP_PORT --ws-port $WS_PORT $PYTHON_ARGS
    else
        print_error "serve_demo.py not found!"
        exit 1
    fi
}

# Handle Ctrl+C gracefully
trap 'print_info "Demo stopped by user"; exit 0' INT

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi