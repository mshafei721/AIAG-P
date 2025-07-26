#!/usr/bin/env python3
"""
Integration test for WebSocket server with Browser Manager.

This script tests the full integration between the WebSocket server
and the Browser Manager to ensure end-to-end functionality.
"""

import asyncio
import json
import logging
import sys
import websockets
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aux.server.websocket_server import WebSocketServer
from aux.browser.manager import BrowserManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_websocket_integration():
    """Test WebSocket server integration with browser manager."""
    print("🚀 Starting WebSocket Integration Test")
    
    # Create browser manager with test settings
    browser_manager = BrowserManager(headless=True, timeout_ms=10000)
    
    # Create WebSocket server with browser manager
    server = WebSocketServer(
        host="localhost",
        port=8081,  # Use different port for testing
        browser_manager=browser_manager
    )
    
    try:
        # Start the server
        print("\n🌐 Starting WebSocket server...")
        await server.start()
        print("✅ WebSocket server started")
        
        # Give server a moment to fully start
        await asyncio.sleep(1)
        
        # Test client connection and commands
        print("\n🔌 Testing client connection...")
        
        async with websockets.connect("ws://localhost:8081") as websocket:
            print("✅ Connected to WebSocket server")
            
            # Test navigation command
            print("\n🌐 Testing navigation command...")
            nav_command = {
                "id": "test-nav-1",
                "method": "navigate",
                "session_id": "test-session",  # Will be ignored, server creates its own
                "url": "https://example.com",
                "wait_until": "load"
            }
            
            await websocket.send(json.dumps(nav_command))
            response = await websocket.recv()
            nav_result = json.loads(response)
            
            if nav_result.get("success"):
                print(f"✅ Navigation successful: {nav_result.get('url')}")
                print(f"   Title: {nav_result.get('title')}")
            else:
                print(f"❌ Navigation failed: {nav_result.get('error')}")
            
            # Test extraction command
            print("\n📤 Testing extraction command...")
            extract_command = {
                "id": "test-extract-1", 
                "method": "extract",
                "session_id": "test-session",
                "selector": "h1",
                "extract_type": "text"
            }
            
            await websocket.send(json.dumps(extract_command))
            response = await websocket.recv()
            extract_result = json.loads(response)
            
            if extract_result.get("success"):
                print(f"✅ Extraction successful: '{extract_result.get('data')}'")
            else:
                print(f"❌ Extraction failed: {extract_result.get('error')}")
            
            # Test wait command
            print("\n⏳ Testing wait command...")
            wait_command = {
                "id": "test-wait-1",
                "method": "wait", 
                "session_id": "test-session",
                "condition": "load",
                "timeout": 5000
            }
            
            await websocket.send(json.dumps(wait_command))
            response = await websocket.recv()
            wait_result = json.loads(response)
            
            if wait_result.get("success"):
                print(f"✅ Wait successful: {wait_result.get('final_state')}")
            else:
                print(f"❌ Wait failed: {wait_result.get('error')}")
            
            print("\n🎉 All WebSocket commands completed!")
        
        # Test server statistics
        print("\n📊 Checking server statistics...")
        stats = await browser_manager.get_stats()
        print(f"   Commands executed: {stats['total_commands_executed']}")
        print(f"   Active sessions: {stats['active_sessions']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        logger.exception("Integration test failed")
        return False
        
    finally:
        # Clean up
        print("\n🧹 Stopping server...")
        await server.stop()
        print("✅ Server stopped")


async def test_error_scenarios():
    """Test error handling in WebSocket integration."""
    print("\n🛡️ Testing Error Scenarios")
    
    server = WebSocketServer(host="localhost", port=8082)
    
    try:
        await server.start()
        await asyncio.sleep(1)
        
        async with websockets.connect("ws://localhost:8082") as websocket:
            # Test invalid command
            print("\n❌ Testing invalid command...")
            invalid_command = {
                "id": "invalid-1",
                "method": "nonexistent_command", 
                "session_id": "test"
            }
            
            await websocket.send(json.dumps(invalid_command))
            response = await websocket.recv()
            result = json.loads(response)
            
            if not result.get("success"):
                print(f"✅ Correctly handled invalid command: {result.get('error_code')}")
            
            # Test malformed JSON
            print("\n❌ Testing malformed JSON...")
            await websocket.send("{ invalid json }")
            response = await websocket.recv()
            result = json.loads(response)
            
            if not result.get("success"):
                print(f"✅ Correctly handled malformed JSON: {result.get('error_code')}")
        
        print("\n✅ Error scenario tests completed!")
        
    finally:
        await server.stop()


async def main():
    """Main test function."""
    print("=" * 70)
    print("🔍 AUX Protocol WebSocket Integration Test Suite")
    print("=" * 70)
    
    try:
        # Run integration tests
        success = await test_websocket_integration()
        
        if success:
            # Run error scenario tests
            await test_error_scenarios()
            print("\n🎉 All integration tests passed!")
            return 0
        else:
            print("\n💥 Integration tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.exception("Unexpected error in tests")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)