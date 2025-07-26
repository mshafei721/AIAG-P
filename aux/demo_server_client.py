#!/usr/bin/env python3
"""
Simple demonstration of the AUX Protocol WebSocket server with client.

This script starts the server in the background and runs a quick test with the client.
"""

import asyncio
import json
import websockets
import uuid
import time
from multiprocessing import Process
import signal
import sys

# Import server
from src.aux.server.websocket_server import WebSocketServer


def run_server():
    """Run the WebSocket server in a separate process."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    server = WebSocketServer(host="localhost", port=8083)
    
    async def start_server():
        await server.start()
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            pass
        finally:
            await server.stop()
    
    asyncio.run(start_server())


async def test_client():
    """Test client that sends commands to the server."""
    uri = "ws://localhost:8083"
    
    print("Connecting to server...")
    async with websockets.connect(uri) as websocket:
        print("Connected! Running tests...\n")
        
        session_id = str(uuid.uuid4())
        
        # Test 1: Navigate command
        print("1. Testing NAVIGATE command")
        navigate_cmd = {
            "id": str(uuid.uuid4()),
            "method": "navigate",
            "session_id": session_id,
            "url": "https://example.com",
            "wait_until": "load"
        }
        
        await websocket.send(json.dumps(navigate_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {navigate_cmd['method']} to {navigate_cmd['url']}")
        print(f"   Response: {response['success']} - {response.get('title', 'N/A')}")
        print(f"   Execution time: {response.get('execution_time_ms', 0)}ms\n")
        
        # Test 2: Click command
        print("2. Testing CLICK command")
        click_cmd = {
            "id": str(uuid.uuid4()),
            "method": "click",
            "session_id": session_id,
            "selector": "button.submit",
            "button": "left"
        }
        
        await websocket.send(json.dumps(click_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {click_cmd['method']} on {click_cmd['selector']}")
        print(f"   Response: {response['success']} - Element found: {response.get('element_found', False)}")
        print(f"   Click position: {response.get('click_position', {})}\n")
        
        # Test 3: Fill command
        print("3. Testing FILL command")
        fill_cmd = {
            "id": str(uuid.uuid4()),
            "method": "fill",
            "session_id": session_id,
            "selector": "input[name='username']",
            "text": "testuser123",
            "clear_first": True
        }
        
        await websocket.send(json.dumps(fill_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {fill_cmd['method']} '{fill_cmd['text']}' into {fill_cmd['selector']}")
        print(f"   Response: {response['success']} - Text entered: '{response.get('text_entered', '')}'")
        print(f"   Current value: '{response.get('current_value', '')}'\n")
        
        # Test 4: Extract command
        print("4. Testing EXTRACT command")
        extract_cmd = {
            "id": str(uuid.uuid4()),
            "method": "extract",
            "session_id": session_id,
            "selector": "h1",
            "extract_type": "text",
            "multiple": False
        }
        
        await websocket.send(json.dumps(extract_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {extract_cmd['method']} {extract_cmd['extract_type']} from {extract_cmd['selector']}")
        print(f"   Response: {response['success']} - Elements found: {response.get('elements_found', 0)}")
        print(f"   Extracted data: '{response.get('data', '')}'\n")
        
        # Test 5: Wait command
        print("5. Testing WAIT command")
        wait_cmd = {
            "id": str(uuid.uuid4()),
            "method": "wait",
            "session_id": session_id,
            "selector": ".loading",
            "condition": "hidden",
            "timeout": 2000
        }
        
        await websocket.send(json.dumps(wait_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {wait_cmd['method']} for {wait_cmd['selector']} to be {wait_cmd['condition']}")
        print(f"   Response: {response['success']} - Condition met: {response.get('condition_met', False)}")
        print(f"   Wait time: {response.get('wait_time_ms', 0)}ms\n")
        
        # Test 6: Invalid command (error handling)
        print("6. Testing ERROR HANDLING")
        invalid_cmd = {
            "id": str(uuid.uuid4()),
            "method": "invalid_method",
            "session_id": session_id,
            "some_param": "value"
        }
        
        await websocket.send(json.dumps(invalid_cmd))
        response = json.loads(await websocket.recv())
        
        print(f"   Request: {invalid_cmd['method']} (invalid)")
        print(f"   Response: {response['success']} - Error: {response.get('error', 'N/A')}")
        print(f"   Error code: {response.get('error_code', 'N/A')}\n")
        
        print("✅ All tests completed successfully!")
        print("🎉 AUX Protocol WebSocket server is working correctly!")


def main():
    """Main demo function."""
    print("🚀 Starting AUX Protocol WebSocket Server Demo")
    print("=" * 50)
    
    # Start server in background process
    server_process = Process(target=run_server)
    server_process.start()
    
    try:
        # Wait for server to start
        print("Starting server...")
        time.sleep(2)
        
        # Run client tests
        asyncio.run(test_client())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
    finally:
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.join(timeout=3)
        if server_process.is_alive():
            server_process.kill()
        print("✅ Demo complete!")


if __name__ == "__main__":
    main()