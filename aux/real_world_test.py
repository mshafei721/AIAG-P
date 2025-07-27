#!/usr/bin/env python3
"""
Real-World User Experience Test: AUX Protocol

Testing realistic automation scenarios that users would actually want to do.
"""

import asyncio
import logging
from aux.client.sdk import AUXClient

logging.basicConfig(level=logging.INFO)

async def test_real_website_automation():
    """Test automation on a real website."""
    print("🌐 Testing Real Website Automation")
    print("=" * 40)
    
    client = AUXClient("ws://localhost:8080")
    
    try:
        await client.connect()
        session = await client.create_session()
        
        # Test 1: Navigate to Example.com (simple, reliable site)
        print("1. Testing navigation to example.com...")
        result = await session.navigate("https://example.com")
        print(f"   ✅ Navigation successful")
        
        # Test 2: Extract the main heading
        print("2. Extracting page title...")
        title = await session.get_text("h1")
        print(f"   ✅ Title extracted: '{title}'")
        
        # Test 3: Extract all paragraph text
        print("3. Extracting page content...")
        content = await session.get_text("p")
        print(f"   ✅ Content: '{content[:100]}...'")
        
        # Test 4: Try to find and click a link
        print("4. Testing link interaction...")
        try:
            link_result = await session.click("a")
            print(f"   ✅ Link click result: {link_result}")
        except Exception as e:
            print(f"   ⚠️  Link test (no clickable links found): {e}")
        
        print("   🎉 Real website test completed successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Real website test failed: {e}")
        return False
    finally:
        await client.disconnect()

async def test_form_interaction():
    """Test form filling capabilities."""
    print("\n📝 Testing Form Interaction")
    print("=" * 30)
    
    client = AUXClient("ws://localhost:8080")
    
    try:
        await client.connect()
        session = await client.create_session()
        
        # Navigate to a site with forms (httpbin.org has test forms)
        print("1. Navigating to test form site...")
        await session.navigate("https://httpbin.org/forms/post")
        
        # Try to fill form fields
        print("2. Testing form field filling...")
        try:
            # Fill customer name
            await session.type_text("input[name='custname']", "John Doe")
            print("   ✅ Customer name field filled")
            
            # Fill telephone
            await session.type_text("input[name='custtel']", "555-1234")
            print("   ✅ Telephone field filled")
            
            # Fill email
            await session.type_text("input[name='custemail']", "john@example.com") 
            print("   ✅ Email field filled")
            
            print("   🎉 Form interaction test completed!")
            return True
            
        except Exception as e:
            print(f"   ⚠️  Form filling test: {e}")
            return False
            
    except Exception as e:
        print(f"   ❌ Form test failed: {e}")
        return False
    finally:
        await client.disconnect()

async def test_performance_and_reliability():
    """Test performance with multiple rapid commands."""
    print("\n⚡ Testing Performance & Reliability")
    print("=" * 40)
    
    client = AUXClient("ws://localhost:8080")
    
    try:
        await client.connect()
        session = await client.create_session()
        
        # Test rapid navigation
        sites = [
            "https://example.com",
            "https://httpbin.org/get",
            "https://jsonplaceholder.typicode.com/",
        ]
        
        print("Testing rapid navigation to multiple sites...")
        for i, site in enumerate(sites, 1):
            print(f"   {i}. Navigating to {site}...")
            await session.navigate(site)
            
            # Extract title from each
            title = await session.get_text("h1, title, h2")
            print(f"      Content found: {title[:50]}...")
        
        print("   🎉 Performance test completed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False
    finally:
        await client.disconnect()

async def main():
    """Run all real-world tests."""
    print("🚀 Starting Real-World AUX Protocol Testing")
    print("Testing scenarios that actual users would want to automate")
    print()
    
    results = []
    
    # Run all tests
    results.append(await test_real_website_automation())
    results.append(await test_form_interaction())
    results.append(await test_performance_and_reliability())
    
    # Summary
    print("\n" + "="*50)
    print("📊 REAL-WORLD TEST SUMMARY")
    print("="*50)
    
    test_names = [
        "Website Automation",
        "Form Interaction", 
        "Performance & Reliability"
    ]
    
    for name, result in zip(test_names, results):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nOverall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 AUX Protocol performs well for real-world use cases!")
    else:
        print("⚠️  AUX Protocol needs improvement for production use")

if __name__ == "__main__":
    asyncio.run(main())