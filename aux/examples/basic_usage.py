"""
Basic Usage Example for AUX Protocol.

This example demonstrates how to use the AUX protocol for basic
browser automation tasks including server setup and client usage.
"""

import asyncio
import logging

from aux import AUXClient, WebSocketServer


async def run_server_example():
    """Example of running an AUX protocol server."""
    print("Starting AUX Protocol Server Example...")
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create and start server
    server = WebSocketServer(host="localhost", port=8080)
    await server.start()
    
    print("Server started on ws://localhost:8080")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Keep server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        await server.stop()
        print("Server stopped")


async def run_client_example():
    """Example of using the AUX protocol client."""
    print("Starting AUX Protocol Client Example...")
    
    # Create client
    client = AUXClient("ws://localhost:8080")
    
    try:
        # Connect to server
        print("Connecting to AUX server...")
        await client.connect()
        print("Connected successfully!")
        
        # Perform health check
        print("Performing health check...")
        health = await client.health_check()
        print(f"Server health: {health}")
        
        # Create a browser session
        print("Creating browser session...")
        session = await client.create_session({
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "AUX-Protocol-Example/1.0"
        })
        print(f"Session created: {session.session_id}")
        
        # Navigate to a website
        print("Navigating to example.com...")
        await session.navigate("https://example.com")
        print("Navigation completed")
        
        # Take a screenshot
        print("Taking screenshot...")
        screenshot_result = await session.screenshot()
        print(f"Screenshot result: {screenshot_result}")
        
        # Get page title (example of text extraction)
        try:
            title = await session.get_text("h1")
            print(f"Page heading: {title}")
        except Exception as e:
            print(f"Could not get page title: {e}")
        
        # Close the session
        print("Closing session...")
        await session.close()
        print("Session closed")
        
    except Exception as e:
        print(f"Error during client operations: {e}")
    finally:
        # Disconnect from server
        await client.disconnect()
        print("Disconnected from server")


async def run_automation_example():
    """Example of more complex browser automation."""
    print("Starting AUX Protocol Automation Example...")
    
    client = AUXClient("ws://localhost:8080")
    
    try:
        await client.connect()
        print("Connected to AUX server")
        
        # Create session with custom configuration
        session = await client.create_session({
            "viewport": {"width": 1920, "height": 1080},
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9"
            }
        })
        
        print(f"Created session: {session.session_id}")
        
        # Navigate to a search engine
        await session.navigate("https://www.google.com")
        print("Navigated to Google")
        
        # Search for something
        search_box_selector = "input[name='q']"
        await session.type_text(search_box_selector, "AUX Protocol browser automation")
        print("Typed search query")
        
        # Submit search (press Enter)
        await session.click("input[name='btnK']")
        print("Clicked search button")
        
        # Wait a moment for results to load
        await asyncio.sleep(2)
        
        # Take a screenshot of the results
        await session.screenshot("/tmp/search_results.png")
        print("Screenshot saved to /tmp/search_results.png")
        
        # Get some search result titles
        try:
            first_result = await session.get_text("h3")
            print(f"First search result: {first_result}")
        except Exception as e:
            print(f"Could not get search results: {e}")
        
        # Close session
        await session.close()
        print("Automation completed successfully")
        
    except Exception as e:
        print(f"Automation error: {e}")
    finally:
        await client.disconnect()


def main():
    """Main function to run examples."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python basic_usage.py [server|client|automation]")
        print("\nExamples:")
        print("  python basic_usage.py server      # Run server")
        print("  python basic_usage.py client      # Run client example")
        print("  python basic_usage.py automation  # Run automation example")
        return
    
    example_type = sys.argv[1].lower()
    
    if example_type == "server":
        asyncio.run(run_server_example())
    elif example_type == "client":
        asyncio.run(run_client_example())
    elif example_type == "automation":
        asyncio.run(run_automation_example())
    else:
        print(f"Unknown example type: {example_type}")
        print("Available types: server, client, automation")


if __name__ == "__main__":
    main()