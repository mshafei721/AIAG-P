# AUX Protocol WebSocket Server

This document describes the WebSocket server implementation for the AUX Protocol, providing comprehensive command routing, session management, and error handling for browser automation.

## Features

- **WebSocket Server**: Built on the `websockets` library for reliable communication
- **Command Routing**: Handles 5 core commands (navigate, click, fill, extract, wait)
- **Session Management**: Tracks client sessions with unique IDs and browser contexts
- **Error Handling**: Comprehensive error responses using Pydantic schema validation
- **Async Support**: Full async/await support for concurrent operations
- **API Key Authentication**: Optional API key validation for security
- **Structured Logging**: Detailed logging for debugging and monitoring
- **Session Cleanup**: Automatic cleanup of expired sessions

## Quick Start

### Starting the Server

```bash
# Basic server (no authentication)
python -m src.aux.server.websocket_server

# Server with API key authentication
python -m src.aux.server.websocket_server --api-key your-secret-key

# Custom host and port
python -m src.aux.server.websocket_server --host 0.0.0.0 --port 9090

# Debug mode
python -m src.aux.server.websocket_server --log-level DEBUG
```

### Environment Variables

```bash
export AUX_API_KEY=your-secret-key
python -m src.aux.server.websocket_server
```

### Testing the Server

Use the included test client:

```bash
# Run automated tests
python test_websocket_client.py

# Interactive mode for manual testing
python test_websocket_client.py --interactive
```

## Supported Commands

The server supports all 5 core AUX Protocol commands:

### 1. Navigate Command

```json
{
  "id": "cmd-001",
  "method": "navigate", 
  "session_id": "session-123",
  "url": "https://example.com",
  "wait_until": "load",
  "timeout": 30000
}
```

**Response:**
```json
{
  "id": "cmd-001",
  "success": true,
  "timestamp": 1640995200.0,
  "execution_time_ms": 1250,
  "url": "https://example.com",
  "title": "Example Domain",
  "status_code": 200,
  "redirected": false,
  "load_time_ms": 1200
}
```

### 2. Click Command

```json
{
  "id": "cmd-002",
  "method": "click",
  "session_id": "session-123", 
  "selector": "button.submit",
  "button": "left",
  "click_count": 1,
  "timeout": 10000
}
```

**Response:**
```json
{
  "id": "cmd-002",
  "success": true,
  "timestamp": 1640995205.0,
  "execution_time_ms": 150,
  "element_found": true,
  "element_visible": true,
  "click_position": {"x": 100, "y": 50},
  "element_text": "Submit",
  "element_tag": "button"
}
```

### 3. Fill Command

```json
{
  "id": "cmd-003",
  "method": "fill",
  "session_id": "session-123",
  "selector": "input[name='username']",
  "text": "testuser",
  "clear_first": true,
  "timeout": 5000
}
```

**Response:**
```json
{
  "id": "cmd-003", 
  "success": true,
  "timestamp": 1640995210.0,
  "execution_time_ms": 80,
  "element_found": true,
  "element_type": "input",
  "text_entered": "testuser",
  "previous_value": "",
  "current_value": "testuser",
  "validation_passed": true
}
```

### 4. Extract Command

```json
{
  "id": "cmd-004",
  "method": "extract",
  "session_id": "session-123",
  "selector": "h1",
  "extract_type": "text",
  "multiple": false,
  "timeout": 5000
}
```

**Response:**
```json
{
  "id": "cmd-004",
  "success": true, 
  "timestamp": 1640995215.0,
  "execution_time_ms": 50,
  "elements_found": 1,
  "data": "Welcome to Example.com",
  "element_info": [
    {"tag": "h1", "class": "title", "index": 0}
  ]
}
```

### 5. Wait Command

```json
{
  "id": "cmd-005",
  "method": "wait",
  "session_id": "session-123",
  "selector": ".loading",
  "condition": "hidden",
  "timeout": 10000
}
```

**Response:**
```json
{
  "id": "cmd-005",
  "success": true,
  "timestamp": 1640995220.0,
  "execution_time_ms": 2000,
  "condition_met": true,
  "wait_time_ms": 1950,
  "final_state": "condition_hidden_met",
  "element_count": 1,
  "condition_details": {
    "selector": ".loading",
    "condition": "hidden"
  }
}
```

## Error Handling

The server provides comprehensive error responses:

```json
{
  "id": "cmd-006",
  "success": false,
  "error": "Element not found",
  "error_code": "ELEMENT_NOT_FOUND",
  "error_type": "element_error",
  "details": {
    "selector": "#nonexistent",
    "timeout": 5000
  },
  "timestamp": 1640995225.0
}
```

### Common Error Codes

- `INVALID_COMMAND`: Malformed command structure
- `INVALID_PARAMS`: Invalid command parameters
- `SESSION_NOT_FOUND`: Session ID doesn't exist
- `ELEMENT_NOT_FOUND`: Target element not found
- `TIMEOUT`: Command timed out
- `UNKNOWN_ERROR`: Unexpected server error

## Session Management

The server automatically manages client sessions:

- **Session Creation**: Automatic on first command
- **Session Tracking**: Unique UUID for each client
- **Activity Monitoring**: Tracks last activity timestamp
- **Automatic Cleanup**: Removes expired sessions (configurable timeout)
- **Browser Context**: Manages browser contexts per session (stub implementation)

## API Authentication

Optional API key authentication:

```bash
# Start server with API key
python -m src.aux.server.websocket_server --api-key your-secret-key

# Or via environment variable
export AUX_API_KEY=your-secret-key
python -m src.aux.server.websocket_server
```

Include API key in first message:

```json
{
  "api_key": "your-secret-key",
  "id": "cmd-001",
  "method": "navigate",
  "session_id": "session-123",
  "url": "https://example.com"
}
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | localhost | Server host address |
| `--port` | 8080 | Server port number |
| `--api-key` | None | API key for authentication |
| `--session-timeout` | 3600 | Session timeout in seconds |
| `--log-level` | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |

## Development

### Running Tests

```bash
# Install dependencies
pip install -e .

# Run the test client
python test_websocket_client.py

# Interactive testing
python test_websocket_client.py --interactive
```

### Server Architecture

The server consists of:

1. **WebSocketServer**: Main server class handling connections
2. **ClientSession**: Session management with browser context tracking
3. **Command Handlers**: Individual handlers for each command type
4. **Error Handling**: Comprehensive error responses with structured codes
5. **Session Cleanup**: Background task for expired session cleanup

### Extending the Server

To add new commands:

1. Define the command schema in `schema/commands.py`
2. Add handler method to `WebSocketServer` class
3. Register handler in `command_handlers` dictionary
4. Update tests and documentation

## Implementation Notes

- **Stub Handlers**: Current command handlers are stub implementations for testing
- **Browser Integration**: Browser context management is placeholder code
- **Production Ready**: Core infrastructure is production-ready
- **Extensible**: Easy to add new commands and features
- **Type Safe**: Full Pydantic validation for all commands and responses

## WebSocket Connection Example

```python
import asyncio
import json
import websockets

async def test_connection():
    uri = "ws://localhost:8080"
    async with websockets.connect(uri) as websocket:
        # Send navigate command
        command = {
            "id": "test-001",
            "method": "navigate",
            "session_id": "test-session",
            "url": "https://example.com"
        }
        
        await websocket.send(json.dumps(command))
        response = await websocket.recv()
        
        print("Response:", json.loads(response))

# Run the test
asyncio.run(test_connection())
```

This WebSocket server provides a solid foundation for browser automation with proper error handling, session management, and extensible command routing.