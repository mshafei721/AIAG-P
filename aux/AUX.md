# AUX Protocol Specification v1.0

## Overview

The AUX (Agent UX Layer) Protocol is a cross-platform standard that enables AI agents to interact with desktop applications and web UIs through structured JSON commands. Unlike traditional automation approaches that rely on screenshots or HTML parsing, AUX provides a token-efficient, semantic control layer optimized for machine interaction.

## Core Principles

1. **Machine-First Design**: Optimize for AI agent interaction, not human UI
2. **Token Efficiency**: Minimize data transfer with structured JSON responses
3. **Semantic Control**: Use high-level selectors and actions instead of pixel coordinates
4. **State Tracking**: Provide delta feedback after every action
5. **Platform Agnostic**: Work across web, desktop, and mobile applications

## Architecture

```
┌─────────────────┐     JSON/WebSocket    ┌──────────────────┐
│                 │ ◄──────────────────► │                  │
│   AI Agent      │                      │   AUX Server     │
│                 │                      │                  │
└─────────────────┘                      └────────┬─────────┘
                                                  │
                                                  │ Commands
                                                  ▼
                                    ┌──────────────────────────┐
                                    │   Browser/App Manager    │
                                    │  - Chrome/Firefox/Safari │
                                    │  - Desktop Apps (future) │
                                    └──────────────────────────┘
```

## Protocol Specification

### Connection

AUX uses WebSocket connections for bi-directional communication:

```
ws://localhost:8080/aux
wss://aux-server.com/aux  (for secure connections)
```

### Authentication

Clients must authenticate using API keys:

```json
{
  "type": "auth",
  "api_key": "your-api-key-here"
}
```

### Session Management

Before executing commands, clients must create a session:

**Request:**
```json
{
  "id": "req-123",
  "method": "create_session",
  "params": {
    "viewport": {
      "width": 1280,
      "height": 720
    },
    "user_agent": "AUX-Agent/1.0"
  }
}
```

**Response:**
```json
{
  "id": "req-123",
  "result": {
    "session_id": "sess-abc123",
    "created_at": 1706371200.0,
    "browser": "chrome",
    "version": "120.0.6099.129"
  }
}
```

## Commands

AUX supports 5 core commands for browser/UI interaction:

### 1. Navigate

Navigate to a URL or application screen.

**Request:**
```json
{
  "id": "cmd-001",
  "method": "navigate",
  "session_id": "sess-abc123",
  "params": {
    "url": "https://example.com",
    "wait_until": "load",
    "timeout": 30000,
    "referer": "https://google.com"
  }
}
```

**Response:**
```json
{
  "id": "cmd-001",
  "result": {
    "url": "https://example.com",
    "title": "Example Domain",
    "status_code": 200,
    "load_time_ms": 523,
    "redirected": false,
    "state_diff": {
      "url_changed": true,
      "title_changed": true
    }
  }
}
```

**Parameters:**
- `url` (required): Target URL
- `wait_until`: When to consider navigation complete (`load`, `domcontentloaded`, `networkidle`)
- `timeout`: Maximum wait time in milliseconds
- `referer`: HTTP referer header

### 2. Click

Click on an element.

**Request:**
```json
{
  "id": "cmd-002",
  "method": "click",
  "session_id": "sess-abc123",
  "params": {
    "selector": "button#submit",
    "button": "left",
    "click_count": 1,
    "position": {
      "x": 0.5,
      "y": 0.5
    },
    "force": false,
    "timeout": 5000
  }
}
```

**Response:**
```json
{
  "id": "cmd-002",
  "result": {
    "element_found": true,
    "element_visible": true,
    "element_tag": "button",
    "element_text": "Submit",
    "click_position": {
      "x": 640,
      "y": 360
    },
    "state_diff": {
      "form_submitted": true,
      "url_changed": true
    }
  }
}
```

**Parameters:**
- `selector` (required): CSS selector, XPath, or semantic selector
- `button`: Mouse button (`left`, `right`, `middle`)
- `click_count`: Number of clicks (1 for single, 2 for double)
- `position`: Relative position within element (0-1 range)
- `force`: Click even if element is not visible
- `timeout`: Maximum wait time for element

### 3. Fill

Fill text into an input field.

**Request:**
```json
{
  "id": "cmd-003",
  "method": "fill",
  "session_id": "sess-abc123",
  "params": {
    "selector": "input#username",
    "text": "john.doe@example.com",
    "clear_first": true,
    "typing_delay_ms": 50,
    "press_enter": false,
    "validate_input": true,
    "timeout": 5000
  }
}
```

**Response:**
```json
{
  "id": "cmd-003",
  "result": {
    "element_found": true,
    "element_type": "email",
    "text_entered": "john.doe@example.com",
    "previous_value": "",
    "current_value": "john.doe@example.com",
    "validation_passed": true,
    "state_diff": {
      "input_filled": true,
      "form_valid": true
    }
  }
}
```

**Parameters:**
- `selector` (required): Target input element
- `text` (required): Text to enter
- `clear_first`: Clear existing text before filling
- `typing_delay_ms`: Delay between keystrokes (simulates human typing)
- `press_enter`: Press Enter after filling
- `validate_input`: Verify text was entered correctly
- `timeout`: Maximum wait time for element

### 4. Extract

Extract data from the page.

**Request:**
```json
{
  "id": "cmd-004",
  "method": "extract",
  "session_id": "sess-abc123",
  "params": {
    "selector": "div.product",
    "extract_type": "text",
    "attribute_name": null,
    "property_name": null,
    "multiple": true,
    "trim_whitespace": true,
    "timeout": 5000
  }
}
```

**Response:**
```json
{
  "id": "cmd-004",
  "result": {
    "elements_found": 3,
    "data": [
      "Product 1 - $29.99",
      "Product 2 - $39.99",
      "Product 3 - $49.99"
    ],
    "element_info": [
      {
        "tag": "div",
        "class": "product featured",
        "index": 0
      },
      {
        "tag": "div",
        "class": "product",
        "index": 1
      },
      {
        "tag": "div",
        "class": "product sale",
        "index": 2
      }
    ]
  }
}
```

**Parameters:**
- `selector` (required): Elements to extract from
- `extract_type`: What to extract (`text`, `html`, `attribute`, `property`)
- `attribute_name`: For attribute extraction (e.g., "href", "src")
- `property_name`: For property extraction (e.g., "value", "checked")
- `multiple`: Extract from all matching elements
- `trim_whitespace`: Remove leading/trailing whitespace
- `timeout`: Maximum wait time for elements

### 5. Wait

Wait for specific conditions.

**Request:**
```json
{
  "id": "cmd-005",
  "method": "wait",
  "session_id": "sess-abc123",
  "params": {
    "condition": "visible",
    "selector": "div#loading",
    "text_content": null,
    "custom_js": null,
    "poll_interval_ms": 100,
    "timeout": 10000
  }
}
```

**Response:**
```json
{
  "id": "cmd-005",
  "result": {
    "condition_met": true,
    "wait_time_ms": 2340,
    "final_state": "element_visible",
    "element_count": 1,
    "condition_details": {
      "condition": "visible",
      "selector": "div#loading",
      "timeout": 10000
    }
  }
}
```

**Parameters:**
- `condition` (required): Wait condition type
  - `load`: Wait for page load
  - `domcontentloaded`: Wait for DOM ready
  - `networkidle`: Wait for network idle
  - `visible`: Wait for element visible
  - `hidden`: Wait for element hidden
  - `attached`: Wait for element in DOM
  - `detached`: Wait for element removed
- `selector`: Element selector (required for element conditions)
- `text_content`: Wait for specific text content
- `custom_js`: Custom JavaScript condition
- `poll_interval_ms`: How often to check condition
- `timeout`: Maximum wait time

## Error Handling

All errors follow a consistent format:

```json
{
  "id": "cmd-001",
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element not found: button#submit",
    "type": "element_error",
    "details": {
      "selector": "button#submit",
      "timeout": 5000
    }
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `SESSION_NOT_FOUND` | Invalid or expired session ID |
| `ELEMENT_NOT_FOUND` | Target element doesn't exist |
| `ELEMENT_NOT_VISIBLE` | Element exists but not visible |
| `ELEMENT_NOT_INTERACTABLE` | Element cannot be interacted with |
| `TIMEOUT` | Operation timed out |
| `NAVIGATION_FAILED` | Failed to navigate to URL |
| `EXTRACTION_FAILED` | Failed to extract data |
| `WAIT_TIMEOUT` | Wait condition not met |
| `INVALID_SELECTOR` | Malformed selector syntax |
| `RATE_LIMITED` | Too many requests |
| `AUTH_FAILED` | Authentication failed |
| `UNKNOWN_ERROR` | Unexpected error occurred |

## State Tracking

Every command response includes state difference information:

```json
{
  "state_diff": {
    "url_changed": true,
    "title_changed": true,
    "elements_added": 5,
    "elements_removed": 2,
    "form_submitted": false,
    "ajax_complete": true
  }
}
```

This allows agents to understand the impact of their actions without parsing entire page states.

## Session Lifecycle

### Creating Sessions

```json
{
  "method": "create_session",
  "params": {
    "browser": "chrome",
    "headless": true,
    "viewport": {
      "width": 1920,
      "height": 1080
    }
  }
}
```

### Closing Sessions

```json
{
  "method": "close_session",
  "params": {
    "session_id": "sess-abc123"
  }
}
```

### Session Timeout

Sessions automatically close after 1 hour of inactivity. Agents should handle session expiration gracefully.

## Advanced Features

### Semantic Selectors

AUX supports semantic selectors for better reliability:

```json
{
  "selector": "button:contains('Submit')",
  "selector": "input[placeholder*='email']",
  "selector": "//button[text()='Next']"  // XPath
}
```

### Batch Commands

Execute multiple commands efficiently:

```json
{
  "method": "batch_execute",
  "session_id": "sess-abc123",
  "params": {
    "commands": [
      {
        "method": "fill",
        "params": { "selector": "#username", "text": "john" }
      },
      {
        "method": "fill",
        "params": { "selector": "#password", "text": "secret" }
      },
      {
        "method": "click",
        "params": { "selector": "#login" }
      }
    ]
  }
}
```

### Performance Metrics

Command responses include performance data:

```json
{
  "performance": {
    "command_time_ms": 234,
    "dom_query_time_ms": 45,
    "network_time_ms": 120,
    "memory_usage_mb": 145
  }
}
```

## Security Considerations

1. **Authentication**: Always use API keys or tokens
2. **Input Sanitization**: All selectors and text are sanitized
3. **Rate Limiting**: Default 100 requests/minute per session
4. **Secure Mode**: Disable dangerous browser features by default
5. **Session Isolation**: Each session runs in isolated context

## Client Libraries

Official SDKs available for:
- Python: `pip install aux-protocol`
- JavaScript: `npm install @aux-protocol/client`
- Go: `go get github.com/aux-protocol/go-client`

### Python Example

```python
from aux import AUXClient

async with AUXClient("ws://localhost:8080", api_key="...") as client:
    session = await client.create_session()
    
    # Navigate to page
    await client.navigate(session, "https://example.com")
    
    # Fill form
    await client.fill(session, "#email", "user@example.com")
    await client.fill(session, "#password", "secret")
    
    # Submit
    await client.click(session, "#submit")
    
    # Extract result
    result = await client.extract(session, ".success-message", "text")
    print(result.data)
```

## Best Practices

1. **Use Semantic Selectors**: Prefer text content over brittle CSS classes
2. **Handle Errors**: Always handle timeout and element not found errors
3. **Wait Appropriately**: Use wait commands instead of fixed delays
4. **Clean Up Sessions**: Close sessions when done to free resources
5. **Monitor State Changes**: Use state_diff to verify actions succeeded

## Versioning

AUX follows semantic versioning:
- **1.0.0**: Current stable release
- **1.1.0**: Added batch commands and performance metrics
- **2.0.0**: Desktop application support (planned)

## Contributing

AUX is an open protocol. Contributions welcome at:
https://github.com/aux-protocol/specification

## License

AUX Protocol Specification is licensed under MIT License.