# AUX Protocol Browser Manager

A comprehensive Playwright-based browser automation manager that implements all 5 core AUX protocol commands with Chrome browser support.

## Features

### 🚀 **Browser Management**
- Chrome browser launch with optimized automation settings
- Configurable headless/headed mode
- Proper resource cleanup and error handling
- Performance tracking and statistics

### 🔒 **Session Management**
- Isolated browser contexts for each client session
- Automatic session cleanup with configurable timeouts
- Activity tracking and command counting
- Multiple concurrent sessions support

### 🎯 **Command Implementation**
All 5 core AUX commands are fully implemented:

1. **NAVIGATE** - Navigate to URLs with wait conditions
2. **CLICK** - Click elements with position and button options
3. **FILL** - Fill input fields with typing simulation
4. **EXTRACT** - Extract text, HTML, attributes, or properties
5. **WAIT** - Wait for various conditions (load, elements, custom JS)

### 🛡️ **Error Handling**
- Comprehensive error responses with specific error codes
- Timeout handling for all operations
- Element not found and visibility checks
- Graceful session cleanup on errors

### 📊 **Monitoring & Debugging**
- Detailed logging for all browser interactions
- Performance metrics and execution statistics
- Session activity tracking
- Configurable debug options (slow motion, etc.)

## Installation

```bash
# Install Playwright
pip install playwright

# Install browser
playwright install chromium

# Install the AUX protocol package (from project root)
pip install -e .
```

## Quick Start

### Basic Browser Manager Usage

```python
import asyncio
from aux.browser.manager import BrowserManager
from aux.schema.commands import NavigateCommand, ExtractCommand

async def example():
    # Initialize browser manager
    manager = BrowserManager(headless=True)
    await manager.initialize()
    
    try:
        # Create a session
        session_id = await manager.create_session()
        
        # Navigate to a page
        nav_command = NavigateCommand(
            id="nav-1",
            method="navigate",
            session_id=session_id,
            url="https://example.com"
        )
        nav_response = await manager.execute_navigate(nav_command)
        print(f"Navigated to: {nav_response.url}")
        
        # Extract data
        extract_command = ExtractCommand(
            id="extract-1",
            method="extract",
            session_id=session_id,
            selector="h1",
            extract_type="text"
        )
        extract_response = await manager.execute_extract(extract_command)
        print(f"Page title: {extract_response.data}")
        
    finally:
        await manager.close()

# Run the example
asyncio.run(example())
```

### WebSocket Server Integration

```python
import asyncio
from aux.server.websocket_server import WebSocketServer
from aux.browser.manager import BrowserManager

async def start_server():
    # Create browser manager with custom settings
    browser_manager = BrowserManager(
        headless=False,  # Run in headed mode for debugging
        viewport_width=1920,
        viewport_height=1080,
        timeout_ms=30000
    )
    
    # Create WebSocket server with browser manager
    server = WebSocketServer(
        host="localhost",
        port=8080,
        browser_manager=browser_manager
    )
    
    try:
        await server.start()
        print("Server running on ws://localhost:8080")
        
        # Keep server running
        await asyncio.Future()  
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await server.stop()

asyncio.run(start_server())
```

## Configuration Options

### Browser Manager Configuration

```python
manager = BrowserManager(
    headless=True,              # Run in headless mode
    viewport_width=1280,        # Browser viewport width
    viewport_height=720,        # Browser viewport height
    user_agent=None,            # Custom user agent string
    timeout_ms=30000,           # Default timeout for operations
    slow_mo_ms=0               # Delay between operations (for debugging)
)
```

### Chrome Launch Arguments

The browser manager automatically configures Chrome with optimal settings:

```python
args = [
    "--no-sandbox",                                    # Required for containers
    "--disable-dev-shm-usage",                        # Overcome limited resource problems
    "--disable-blink-features=AutomationControlled",  # Hide automation
    "--disable-web-security",                         # Allow cross-origin requests
    "--disable-features=VizDisplayCompositor",        # Performance optimization
    "--disable-background-timer-throttling",          # Prevent throttling
    "--disable-renderer-backgrounding",               # Keep rendering active
    "--disable-backgrounding-occluded-windows",       # Prevent tab throttling
]
```

## Command Examples

### 1. Navigate Command

```python
command = NavigateCommand(
    id="nav-1",
    method="navigate",
    session_id=session_id,
    url="https://example.com",
    wait_until="load",           # load, domcontentloaded, networkidle
    referer="https://google.com" # Optional referer header
)
response = await manager.execute_navigate(command)
```

### 2. Click Command

```python
command = ClickCommand(
    id="click-1",
    method="click",
    session_id=session_id,
    selector="button#submit",
    button="left",               # left, right, middle
    click_count=1,               # Number of clicks
    force=False,                 # Force click even if not visible
    position={"x": 0.5, "y": 0.5}  # Relative position (optional)
)
response = await manager.execute_click(command)
```

### 3. Fill Command

```python
command = FillCommand(
    id="fill-1",
    method="fill",
    session_id=session_id,
    selector="input[name='username']",
    text="john_doe",
    clear_first=True,            # Clear field before filling
    press_enter=False,           # Press Enter after filling
    typing_delay_ms=50,          # Delay between keystrokes
    validate_input=True          # Verify text was entered
)
response = await manager.execute_fill(command)
```

### 4. Extract Command

```python
# Extract text
command = ExtractCommand(
    id="extract-1",
    method="extract",
    session_id=session_id,
    selector="h1",
    extract_type="text",         # text, html, attribute, property
    multiple=False,              # Extract from all matching elements
    trim_whitespace=True         # Remove leading/trailing whitespace
)

# Extract attribute
command = ExtractCommand(
    id="extract-2",
    method="extract", 
    session_id=session_id,
    selector="a",
    extract_type="attribute",
    attribute_name="href",       # Required for attribute extraction
    multiple=True               # Get all links
)

response = await manager.execute_extract(command)
```

### 5. Wait Command

```python
# Wait for page load
command = WaitCommand(
    id="wait-1",
    method="wait",
    session_id=session_id,
    condition="load",            # load, domcontentloaded, networkidle
    timeout=30000
)

# Wait for element
command = WaitCommand(
    id="wait-2", 
    method="wait",
    session_id=session_id,
    selector="#dynamic-content",
    condition="visible",         # visible, hidden, attached, detached
    timeout=10000
)

# Wait for custom condition
command = WaitCommand(
    id="wait-3",
    method="wait",
    session_id=session_id,
    custom_js="() => document.readyState === 'complete'",
    timeout=5000
)

response = await manager.execute_wait(command)
```

## Error Handling

All commands return either a success response or an error response:

```python
response = await manager.execute_navigate(command)

if response.success:
    print(f"Success: {response.url}")
else:
    print(f"Error: {response.error}")
    print(f"Error Code: {response.error_code}")
    print(f"Error Type: {response.error_type}")
```

### Common Error Codes

- `SESSION_NOT_FOUND` - Invalid session ID
- `ELEMENT_NOT_FOUND` - Selector didn't match any elements
- `ELEMENT_NOT_VISIBLE` - Element exists but not visible
- `ELEMENT_NOT_INTERACTABLE` - Element cannot be interacted with
- `TIMEOUT` - Operation timed out
- `NAVIGATION_FAILED` - Navigation failed
- `EXTRACTION_FAILED` - Data extraction failed

## WebSocket Client Example

```javascript
// Connect to WebSocket server
const ws = new WebSocket('ws://localhost:8080');

// Send navigation command
const navCommand = {
    id: 'nav-1',
    method: 'navigate',
    session_id: 'my-session',
    url: 'https://example.com',
    wait_until: 'load'
};

ws.send(JSON.stringify(navCommand));

// Handle response
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    if (response.success) {
        console.log('Navigation successful:', response.url);
    } else {
        console.error('Navigation failed:', response.error);
    }
};
```

## Monitoring and Statistics

Get browser manager statistics:

```python
stats = await manager.get_stats()
print(f"Total commands executed: {stats['total_commands_executed']}")
print(f"Active sessions: {stats['active_sessions']}")
print(f"Startup time: {stats['startup_time_seconds']}")

for session in stats['session_details']:
    print(f"Session {session['session_id']}: {session['command_count']} commands")
```

## Testing

Run the included test scripts:

```bash
# Test browser manager functionality
python test_browser_manager.py

# Test WebSocket integration
python test_websocket_integration.py
```

## Best Practices

### 1. Session Management
- Always close sessions when done to free resources
- Use session timeouts to prevent resource leaks
- Monitor active sessions in production

### 2. Error Handling
- Always check response.success before using response data
- Implement retry logic for transient errors
- Log errors with context for debugging

### 3. Performance
- Use headless mode in production
- Configure appropriate timeouts
- Clean up inactive sessions regularly

### 4. Selectors
- Use specific, stable selectors
- Prefer data attributes over class names
- Test selectors in browser dev tools first

### 5. Security
- Validate all input parameters
- Use proper authentication for WebSocket connections
- Run browsers in sandboxed environments

## Troubleshooting

### Common Issues

1. **Browser won't start**
   - Ensure Playwright browsers are installed: `playwright install chromium`
   - Check system dependencies for headless mode
   - Try running in headed mode for debugging

2. **Elements not found**
   - Wait for elements to load before interacting
   - Use specific selectors
   - Check if elements are in iframes

3. **Timeouts**
   - Increase timeout values for slow pages
   - Use appropriate wait conditions
   - Check network connectivity

4. **Memory issues**
   - Close sessions when done
   - Monitor browser processes
   - Implement session cleanup

### Debug Mode

Enable debug logging and run in headed mode:

```python
import logging
logging.getLogger('aux.browser.manager').setLevel(logging.DEBUG)

manager = BrowserManager(
    headless=False,     # See browser window
    slow_mo_ms=1000    # Slow down operations
)
```

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation
4. Ensure proper error handling
5. Test with multiple browsers if adding new features

## License

This project is part of the AUX Protocol implementation.