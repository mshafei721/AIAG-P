#!/usr/bin/env python3
"""
Simple WebSocket client for testing the AUX Protocol server.

This script demonstrates how to connect to the WebSocket server and send
various commands to test the routing and response functionality.
"""

import asyncio
import json
import websockets
import uuid
from typing import Dict, Any


class AUXTestClient:
    """Simple test client for AUX Protocol WebSocket server."""
    
    def __init__(self, uri: str = "ws://localhost:8080"):
        self.uri = uri
        self.websocket = None
        self.session_id = str(uuid.uuid4())
        
    async def connect(self):
        """Connect to the WebSocket server."""
        print(f"Connecting to {self.uri}...")
        self.websocket = await websockets.connect(self.uri)
        print("Connected successfully!")
        
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            print("Disconnected.")
            
    async def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a command and wait for response.
        
        Args:
            command: Command dictionary
            
        Returns:
            Response dictionary
        """
        if not self.websocket:
            raise RuntimeError("Not connected to server")
            
        # Add session_id if not present
        if "session_id" not in command:
            command["session_id"] = self.session_id
            
        # Send command
        command_json = json.dumps(command)
        print(f"Sending: {command_json}")
        await self.websocket.send(command_json)
        
        # Wait for response
        response_json = await self.websocket.recv()
        response = json.loads(response_json)
        
        print(f"Received: {json.dumps(response, indent=2)}")
        return response
        
    async def test_navigate(self):
        """Test navigate command."""
        print("\n=== Testing NAVIGATE command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "navigate",
            "url": "https://example.com",
            "wait_until": "load"
        }
        return await self.send_command(command)
        
    async def test_click(self):
        """Test click command."""
        print("\n=== Testing CLICK command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "click",
            "selector": "button.submit",
            "button": "left",
            "click_count": 1
        }
        return await self.send_command(command)
        
    async def test_fill(self):
        """Test fill command."""
        print("\n=== Testing FILL command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "fill",
            "selector": "input[name='username']",
            "text": "test_user",
            "clear_first": True
        }
        return await self.send_command(command)
        
    async def test_extract(self):
        """Test extract command."""
        print("\n=== Testing EXTRACT command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "extract",
            "selector": "h1",
            "extract_type": "text",
            "multiple": False
        }
        return await self.send_command(command)
        
    async def test_wait(self):
        """Test wait command."""
        print("\n=== Testing WAIT command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "wait",
            "selector": ".loading",
            "condition": "hidden",
            "timeout": 5000
        }
        return await self.send_command(command)
        
    async def test_invalid_command(self):
        """Test invalid command handling."""
        print("\n=== Testing INVALID command ===")
        command = {
            "id": str(uuid.uuid4()),
            "method": "invalid_method",
            "some_param": "value"
        }
        return await self.send_command(command)
        
    async def test_malformed_json(self):
        """Test malformed JSON handling."""
        print("\n=== Testing malformed JSON ===")
        if not self.websocket:
            raise RuntimeError("Not connected to server")
            
        malformed_json = '{"id": "test", "method": "navigate", "url": "https://example.com"'
        print(f"Sending malformed JSON: {malformed_json}")
        await self.websocket.send(malformed_json)
        
        response_json = await self.websocket.recv()
        response = json.loads(response_json)
        print(f"Received: {json.dumps(response, indent=2)}")
        return response


async def run_tests():
    """Run all test cases."""
    client = AUXTestClient()
    
    try:
        await client.connect()
        
        # Test all commands
        await client.test_navigate()
        await client.test_click()
        await client.test_fill()
        await client.test_extract()
        await client.test_wait()
        
        # Test error handling
        await client.test_invalid_command()
        await client.test_malformed_json()
        
        print("\n=== All tests completed ===")
        
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        await client.disconnect()


async def run_tests_with_uri(uri: str):
    """Run all test cases with custom URI."""
    client = AUXTestClient(uri)
    
    try:
        await client.connect()
        
        # Test all commands
        await client.test_navigate()
        await client.test_click()
        await client.test_fill()
        await client.test_extract()
        await client.test_wait()
        
        # Test error handling
        await client.test_invalid_command()
        await client.test_malformed_json()
        
        print("\n=== All tests completed ===")
        
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        await client.disconnect()


async def interactive_mode():
    """Run in interactive mode for manual testing."""
    client = AUXTestClient()
    
    try:
        await client.connect()
        
        print("\nInteractive mode - Enter commands as JSON:")
        print("Example: {\"id\": \"1\", \"method\": \"navigate\", \"url\": \"https://example.com\"}")
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("Command: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if not user_input:
                    continue
                    
                command = json.loads(user_input)
                await client.send_command(command)
                
            except json.JSONDecodeError:
                print("Invalid JSON format")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Interactive mode error: {e}")
    finally:
        await client.disconnect()


async def interactive_mode_with_uri(uri: str):
    """Run in interactive mode with custom URI."""
    client = AUXTestClient(uri)
    
    try:
        await client.connect()
        
        print(f"\nInteractive mode connected to {uri}")
        print("Enter commands as JSON:")
        print("Example: {\"id\": \"1\", \"method\": \"navigate\", \"url\": \"https://example.com\"}")
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("Command: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if not user_input:
                    continue
                    
                command = json.loads(user_input)
                await client.send_command(command)
                
            except json.JSONDecodeError:
                print("Invalid JSON format")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Interactive mode error: {e}")
    finally:
        await client.disconnect()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AUX Protocol WebSocket Test Client")
    parser.add_argument("--uri", default="ws://localhost:8080", 
                       help="WebSocket server URI (default: ws://localhost:8080)")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        print("Starting AUX Protocol WebSocket Test Client (Interactive Mode)")
        asyncio.run(interactive_mode_with_uri(args.uri))
    else:
        print("Starting AUX Protocol WebSocket Test Client (Automated Tests)")
        asyncio.run(run_tests_with_uri(args.uri))


if __name__ == "__main__":
    main()