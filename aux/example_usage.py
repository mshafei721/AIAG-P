#!/usr/bin/env python3
"""
Example usage of the AUX Protocol Browser Manager.

This script demonstrates how to use the comprehensive browser manager
to perform common web automation tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aux.browser.manager import BrowserManager
from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, 
    ExtractCommand, WaitCommand, ExtractType, WaitCondition
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def web_scraping_example():
    """Example: Web scraping with the browser manager."""
    print("🕷️ Web Scraping Example")
    print("=" * 40)
    
    # Initialize browser manager
    manager = BrowserManager(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        timeout_ms=10000
    )
    
    try:
        await manager.initialize()
        session_id = await manager.create_session()
        
        # Navigate to a news website
        print("📰 Navigating to news website...")
        nav_response = await manager.execute_navigate(
            NavigateCommand(
                id="nav-1",
                method="navigate",
                session_id=session_id,
                url="https://example.com",
                wait_until=WaitCondition.LOAD
            )
        )
        
        if nav_response.success:
            print(f"✅ Loaded: {nav_response.title}")
        
        # Extract the main heading
        print("\n📤 Extracting page content...")
        extract_response = await manager.execute_extract(
            ExtractCommand(
                id="extract-1",
                method="extract",
                session_id=session_id,
                selector="h1",
                extract_type=ExtractType.TEXT
            )
        )
        
        if extract_response.success:
            print(f"🏷️  Main heading: {extract_response.data}")
        
        # Extract all paragraphs
        paragraphs_response = await manager.execute_extract(
            ExtractCommand(
                id="extract-2",
                method="extract",
                session_id=session_id,
                selector="p",
                extract_type=ExtractType.TEXT,
                multiple=True
            )
        )
        
        if paragraphs_response.success:
            print(f"📝 Found {len(paragraphs_response.data)} paragraphs")
            for i, paragraph in enumerate(paragraphs_response.data[:3]):  # First 3
                print(f"   {i+1}. {paragraph[:100]}...")
        
    finally:
        await manager.close()


async def form_automation_example():
    """Example: Form filling automation."""
    print("\n📝 Form Automation Example")
    print("=" * 40)
    
    manager = BrowserManager(headless=True)
    
    try:
        await manager.initialize()
        session_id = await manager.create_session()
        
        # Navigate to a form page (using httpbin for demo)
        print("🌐 Navigating to form page...")
        nav_response = await manager.execute_navigate(
            NavigateCommand(
                id="nav-form",
                method="navigate", 
                session_id=session_id,
                url="https://httpbin.org/forms/post"
            )
        )
        
        if nav_response.success:
            print("✅ Form page loaded")
        
        # Fill form fields
        print("\n✏️ Filling form fields...")
        
        # Fill customer name
        await manager.execute_fill(
            FillCommand(
                id="fill-1",
                method="fill",
                session_id=session_id,
                selector="input[name='custname']",
                text="John Doe",
                clear_first=True
            )
        )
        
        # Fill telephone
        await manager.execute_fill(
            FillCommand(
                id="fill-2", 
                method="fill",
                session_id=session_id,
                selector="input[name='custtel']",
                text="+1-555-123-4567"
            )
        )
        
        # Fill email
        await manager.execute_fill(
            FillCommand(
                id="fill-3",
                method="fill",
                session_id=session_id,
                selector="input[name='custemail']", 
                text="john.doe@example.com"
            )
        )
        
        print("✅ Form fields filled")
        
        # Extract form values to verify
        print("\n🔍 Verifying form data...")
        name_value = await manager.execute_extract(
            ExtractCommand(
                id="verify-1",
                method="extract",
                session_id=session_id,
                selector="input[name='custname']",
                extract_type=ExtractType.PROPERTY,
                property_name="value"
            )
        )
        
        if name_value.success:
            print(f"✅ Name field: {name_value.data}")
        
        # Click submit button (comment out to avoid actually submitting)
        # print("\n🚀 Submitting form...")
        # submit_response = await manager.execute_click(
        #     ClickCommand(
        #         id="submit-1",
        #         method="click",
        #         session_id=session_id,
        #         selector="input[type='submit']"
        #     )
        # )
        
        print("✅ Form automation completed")
        
    finally:
        await manager.close()


async def dynamic_content_example():
    """Example: Handling dynamic content with waits.""" 
    print("\n⏳ Dynamic Content Example")
    print("=" * 40)
    
    manager = BrowserManager(headless=True)
    
    try:
        await manager.initialize()
        session_id = await manager.create_session()
        
        # Navigate to a page with dynamic content
        print("🌐 Loading dynamic content page...")
        await manager.execute_navigate(
            NavigateCommand(
                id="nav-dynamic",
                method="navigate",
                session_id=session_id,
                url="https://httpbin.org/delay/2"  # Simulates 2-second delay
            )
        )
        
        # Wait for page to fully load
        print("⏳ Waiting for page load...")
        wait_response = await manager.execute_wait(
            WaitCommand(
                id="wait-1",
                method="wait",
                session_id=session_id,
                condition=WaitCondition.LOAD,
                timeout=10000
            )
        )
        
        if wait_response.success:
            print(f"✅ Page loaded in {wait_response.wait_time_ms}ms")
            print(f"   Final state: {wait_response.final_state}")
        
        # Wait for network to be idle
        print("🌐 Waiting for network idle...")
        network_wait = await manager.execute_wait(
            WaitCommand(
                id="wait-2",
                method="wait", 
                session_id=session_id,
                condition=WaitCondition.NETWORKIDLE,
                timeout=15000
            )
        )
        
        if network_wait.success:
            print(f"✅ Network idle after {network_wait.wait_time_ms}ms")
        
        # Extract the delayed content
        content_response = await manager.execute_extract(
            ExtractCommand(
                id="extract-delayed",
                method="extract",
                session_id=session_id,
                selector="body",
                extract_type=ExtractType.TEXT
            )
        )
        
        if content_response.success:
            print(f"📄 Content loaded: {len(content_response.data)} characters")
        
    finally:
        await manager.close()


async def error_handling_example():
    """Example: Proper error handling."""
    print("\n🛡️ Error Handling Example")
    print("=" * 40)
    
    manager = BrowserManager(headless=True)
    
    try:
        await manager.initialize()
        session_id = await manager.create_session()
        
        # Navigate to a valid page first
        await manager.execute_navigate(
            NavigateCommand(
                id="nav-valid",
                method="navigate",
                session_id=session_id,
                url="https://example.com"
            )
        )
        
        # Try to extract from non-existent element
        print("❌ Attempting to extract from non-existent element...")
        error_response = await manager.execute_extract(
            ExtractCommand(
                id="extract-error",
                method="extract",
                session_id=session_id,
                selector="#non-existent-element",
                extract_type=ExtractType.TEXT
            )
        )
        
        if not error_response.success:
            print(f"✅ Properly handled error:")
            print(f"   Code: {error_response.error_code}")
            print(f"   Type: {error_response.error_type}")
            print(f"   Message: {error_response.error}")
        
        # Try to navigate to invalid URL
        print("\n❌ Attempting to navigate to invalid URL...")
        nav_error = await manager.execute_navigate(
            NavigateCommand(
                id="nav-error",
                method="navigate",
                session_id=session_id,
                url="https://this-domain-does-not-exist-12345.com",
                timeout=5000  # Short timeout
            )
        )
        
        if not nav_error.success:
            print(f"✅ Properly handled navigation error:")
            print(f"   Code: {nav_error.error_code}")
            print(f"   Type: {nav_error.error_type}")
        
        # Try to use invalid session
        print("\n❌ Attempting to use invalid session...")
        invalid_session_response = await manager.execute_extract(
            ExtractCommand(
                id="extract-invalid-session",
                method="extract",
                session_id="invalid-session-id",
                selector="body",
                extract_type=ExtractType.TEXT
            )
        )
        
        if not invalid_session_response.success:
            print(f"✅ Properly handled invalid session:")
            print(f"   Code: {invalid_session_response.error_code}")
        
    finally:
        await manager.close()


async def main():
    """Run all examples."""
    print("🚀 AUX Protocol Browser Manager Examples")
    print("=" * 50)
    
    try:
        # Run all examples
        await web_scraping_example()
        await form_automation_example() 
        await dynamic_content_example()
        await error_handling_example()
        
        print("\n🎉 All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Examples interrupted by user")
    except Exception as e:
        print(f"\n💥 Example failed: {e}")
        logger.exception("Example failed")


if __name__ == "__main__":
    asyncio.run(main())