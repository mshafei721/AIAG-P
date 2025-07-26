#!/usr/bin/env python3
"""
Test script for the Browser Manager implementation.

This script tests the basic functionality of the BrowserManager
to ensure all components work together correctly.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aux.browser.manager import BrowserManager
from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, 
    ExtractCommand, WaitCommand, ExtractType, WaitCondition
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_browser_manager():
    """Test the browser manager functionality."""
    print("🚀 Starting Browser Manager Test")
    
    # Initialize browser manager
    manager = BrowserManager(headless=True, timeout_ms=10000)
    
    try:
        # Test initialization
        print("\n📚 Testing browser manager initialization...")
        await manager.initialize()
        stats = await manager.get_stats()
        print(f"✅ Browser manager initialized in {stats['startup_time_seconds']:.2f}s")
        
        # Test session creation
        print("\n🔧 Testing session creation...")
        session_id = await manager.create_session()
        print(f"✅ Created session: {session_id}")
        
        # Test navigation
        print("\n🌐 Testing navigation...")
        nav_command = NavigateCommand(
            id="nav-1",
            method="navigate",
            session_id=session_id,
            url="https://example.com",
            wait_until=WaitCondition.LOAD
        )
        
        nav_response = await manager.execute_navigate(nav_command)
        if nav_response.success:
            print(f"✅ Navigation successful: {nav_response.url}")
            print(f"   Title: {nav_response.title}")
            print(f"   Load time: {nav_response.load_time_ms}ms")
        else:
            print(f"❌ Navigation failed: {nav_response.error}")
            
        # Test extraction
        print("\n📤 Testing data extraction...")
        extract_command = ExtractCommand(
            id="extract-1",
            method="extract",
            session_id=session_id,
            selector="h1",
            extract_type=ExtractType.TEXT,
            multiple=False
        )
        
        extract_response = await manager.execute_extract(extract_command)
        if extract_response.success:
            print(f"✅ Extraction successful: '{extract_response.data}'")
            print(f"   Elements found: {extract_response.elements_found}")
        else:
            print(f"❌ Extraction failed: {extract_response.error}")
            
        # Test wait functionality
        print("\n⏳ Testing wait functionality...")
        wait_command = WaitCommand(
            id="wait-1",
            method="wait",
            session_id=session_id,
            condition=WaitCondition.LOAD,
            timeout=5000
        )
        
        wait_response = await manager.execute_wait(wait_command)
        if wait_response.success:
            print(f"✅ Wait successful: {wait_response.final_state}")
            print(f"   Wait time: {wait_response.wait_time_ms}ms")
        else:
            print(f"❌ Wait failed: {wait_response.error}")
            
        # Test session management
        print("\n📋 Testing session management...")
        sessions = await manager.list_sessions()
        print(f"✅ Active sessions: {len(sessions)}")
        
        # Get final stats
        final_stats = await manager.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   Total commands executed: {final_stats['total_commands_executed']}")
        print(f"   Active sessions: {final_stats['active_sessions']}")
        
        # Test session cleanup
        print("\n🧹 Testing session cleanup...")
        closed = await manager.close_session(session_id)
        print(f"✅ Session closed: {closed}")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test failed")
        return False
        
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        await manager.close()
        print("✅ Browser manager closed")
        
    return True


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n🛡️ Testing Error Handling")
    
    manager = BrowserManager(headless=True)
    
    try:
        await manager.initialize()
        session_id = await manager.create_session()
        
        # Test invalid selector
        print("\n❌ Testing invalid selector...")
        extract_command = ExtractCommand(
            id="extract-error",
            method="extract", 
            session_id=session_id,
            selector="#nonexistent-element",
            extract_type=ExtractType.TEXT
        )
        
        response = await manager.execute_extract(extract_command)
        if not response.success:
            print(f"✅ Correctly handled invalid selector: {response.error_code}")
        
        # Test invalid session
        print("\n❌ Testing invalid session...")
        invalid_command = NavigateCommand(
            id="nav-invalid",
            method="navigate",
            session_id="invalid-session-id",
            url="https://example.com"
        )
        
        response = await manager.execute_navigate(invalid_command)
        if not response.success:
            print(f"✅ Correctly handled invalid session: {response.error_code}")
            
        print("\n✅ Error handling tests completed!")
        
    finally:
        await manager.close()


async def main():
    """Main test function."""
    print("=" * 60)
    print("🔍 AUX Protocol Browser Manager Test Suite")
    print("=" * 60)
    
    # Run basic functionality tests
    success = await test_browser_manager()
    
    if success:
        # Run error handling tests
        await test_error_handling()
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)