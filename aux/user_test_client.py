#!/usr/bin/env python3
"""
User Experience Test: AUX Client SDK

This script tests the AUX Python SDK from a user perspective,
following the examples in the README.
"""

import asyncio
import logging
from aux.client.sdk import AUXClient

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def test_basic_usage():
    """Test basic AUX client usage as shown in README."""
    print("🧪 Testing AUX Client SDK (User Experience)")
    print("=" * 50)
    
    # Step 1: Create client as shown in README
    print("1. Creating AUX client...")
    client = AUXClient("ws://localhost:8080")
    
    try:
        # Step 2: Connect
        print("2. Connecting to server...")
        await client.connect()
        print("✅ Connected successfully!")
        
        # Step 3: Create session as shown in README
        print("3. Creating browser session...")
        session = await client.create_session()
        print(f"✅ Session created: {session.session_id}")
        
        # Step 4: Navigate as shown in README  
        print("4. Navigating to https://example.com...")
        result = await session.navigate("https://example.com")
        print(f"✅ Navigation result: {result}")
        
        # Step 5: Try to get page title
        print("5. Extracting page title...")
        title = await session.get_text("h1")
        print(f"✅ Page title: '{title}'")
        
        # Step 6: Try clicking something
        print("6. Testing click functionality...")
        try:
            click_result = await session.click("a")  # Try to click any link
            print(f"✅ Click result: {click_result}")
        except Exception as e:
            print(f"⚠️  Click test failed (expected): {e}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        # Step 7: Disconnect as shown in README
        print("7. Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected successfully!")
    
    print("\n🎉 Basic SDK test completed!")
    return True

async def test_error_handling():
    """Test how the client handles errors and edge cases."""
    print("\n🧪 Testing Error Handling")
    print("=" * 30)
    
    client = AUXClient("ws://localhost:8080")
    
    try:
        await client.connect()
        session = await client.create_session()
        
        # Test invalid selector
        print("Testing invalid selector...")
        try:
            await session.get_text("invalid>>>selector")
        except Exception as e:
            print(f"✅ Invalid selector handled: {e}")
        
        # Test invalid URL
        print("Testing invalid URL...")
        try:
            await session.navigate("not-a-url")
        except Exception as e:
            print(f"✅ Invalid URL handled: {e}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    print("🚀 Starting AUX Protocol User Experience Test")
    print("Server should be running on ws://localhost:8080")
    print()
    
    # Run the tests
    asyncio.run(test_basic_usage())
    asyncio.run(test_error_handling())
    
    print("\n✨ User Experience Testing Complete!")