# AUX Protocol

AUX (Automated User eXperience) Protocol is a modern browser automation protocol designed for AI-driven web interactions. It provides a WebSocket-based interface for controlling browsers with advanced capabilities for AI agents and automated testing.

## Features

- **WebSocket-based Communication**: Real-time bidirectional communication between clients and browser instances
- **AI-Optimized**: Designed specifically for AI agents with structured command schemas
- **Browser Management**: Advanced browser instance management with isolation and resource control
- **Extensible Architecture**: Modular design supporting custom commands and extensions
- **Type Safety**: Full TypeScript/Python type definitions with Pydantic models

## Installation

```bash
pip install aux-protocol
```

For development:

```bash
pip install aux-protocol[dev]
```

## Quick Start

### Starting the AUX Server

```python
from aux.server import WebSocketServer

server = WebSocketServer(host="localhost", port=8080)
server.start()
```

### Using the Client SDK

```python
from aux.client import AUXClient

async def main():
    client = AUXClient("ws://localhost:8080")
    await client.connect()
    
    # Create a browser session
    session = await client.create_session()
    
    # Navigate to a page
    await session.navigate("https://example.com")
    
    # Interact with elements
    await session.click("#my-button")
    
    await client.disconnect()
```

## Architecture

The AUX Protocol consists of four main components:

- **Server**: WebSocket server managing browser instances and client connections
- **Browser Manager**: Handles browser lifecycle, isolation, and resource management
- **Client SDK**: Python/JavaScript SDKs for easy integration
- **Schema**: Command and event definitions using Pydantic models

## Development

### Setup

```bash
git clone https://github.com/aux-protocol/aux-python
cd aux-python
pip install -e .[dev]
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our GitHub repository.

## Support

- **Documentation**: [https://aux-protocol.readthedocs.io](https://aux-protocol.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/aux-protocol/aux-python/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aux-protocol/aux-python/discussions)