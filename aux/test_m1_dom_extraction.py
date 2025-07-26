#!/usr/bin/env python3
"""
M1 DOM Extraction Validation Tests

This module validates the DOM extraction functionality required for Milestone M1:
- Build aux_browser.py to load webpage and return DOM as JSON
- Check if DOM extraction is implemented
- Verify JSON structure is correct
- Test with multiple websites
"""

import asyncio
import json
import time
import pytest
from typing import Dict, Any, List
from aux.browser.manager import BrowserManager
from aux.schema.commands import NavigateCommand, ExtractCommand, ExtractType, WaitCondition


class TestM1DOMExtraction:
    """Test suite for M1 DOM extraction functionality."""
    
    @pytest.fixture
    async def browser_manager(self):
        """Create browser manager for testing."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        yield manager
        await manager.close()
    
    @pytest.fixture
    async def browser_session(self, browser_manager):
        """Create browser session for testing."""
        session_id = await browser_manager.create_session()
        yield session_id, browser_manager
        await browser_manager.close_session(session_id)
    
    async def test_basic_dom_extraction(self, browser_session):
        """Test basic DOM extraction from a simple webpage."""
        session_id, manager = browser_session
        
        # Navigate to a simple page
        nav_command = NavigateCommand(
            id="nav_1",
            method="navigate",
            session_id=session_id,
            url="https://example.com",
            wait_until=WaitCondition.LOAD
        )
        
        nav_result = await manager.execute_navigate(nav_command)
        assert nav_result.success, f"Navigation failed: {nav_result}"
        
        # Extract DOM structure
        extract_command = ExtractCommand(
            id="extract_1",
            method="extract",
            session_id=session_id,
            selector="html",
            extract_type=ExtractType.HTML
        )
        
        extract_result = await manager.execute_extract(extract_command)
        assert extract_result.success, f"DOM extraction failed: {extract_result}"
        assert extract_result.elements_found > 0, "No HTML elements found"
        assert isinstance(extract_result.data, str), "DOM data should be string"
        assert len(extract_result.data) > 0, "DOM data should not be empty"
        
        # Verify it contains valid HTML structure
        assert "<body" in extract_result.data.lower(), "DOM should contain body element"
        assert "<head" in extract_result.data.lower(), "DOM should contain head element"
    
    async def test_structured_dom_as_json(self, browser_session):
        """Test extraction of DOM elements as structured data."""
        session_id, manager = browser_session
        
        # Navigate to example.com
        nav_command = NavigateCommand(
            id="nav_2",
            method="navigate", 
            session_id=session_id,
            url="https://example.com",
            wait_until=WaitCondition.LOAD
        )
        
        await manager.execute_navigate(nav_command)
        
        # Extract all headings
        headings_command = ExtractCommand(
            id="extract_headings",
            method="extract",
            session_id=session_id,
            selector="h1, h2, h3, h4, h5, h6",
            extract_type=ExtractType.TEXT,
            multiple=True
        )
        
        headings_result = await manager.execute_extract(headings_command)
        assert headings_result.success, "Headings extraction failed"
        
        # Extract all links with URLs
        links_command = ExtractCommand(
            id="extract_links",
            method="extract", 
            session_id=session_id,
            selector="a[href]",
            extract_type=ExtractType.ATTRIBUTE,
            attribute_name="href",
            multiple=True
        )
        
        links_result = await manager.execute_extract(links_command)
        assert links_result.success, "Links extraction failed"
        
        # Verify structured data
        dom_structure = {
            "headings": headings_result.data if isinstance(headings_result.data, list) else [headings_result.data],
            "links": links_result.data if isinstance(links_result.data, list) else [links_result.data],
            "element_info": {
                "headings_count": headings_result.elements_found,
                "links_count": links_result.elements_found
            }
        }
        
        # Verify JSON serializable
        json_str = json.dumps(dom_structure)
        assert len(json_str) > 0, "DOM structure should be JSON serializable"
        
        # Verify structure
        parsed = json.loads(json_str)
        assert "headings" in parsed, "Should contain headings"
        assert "links" in parsed, "Should contain links"
        assert "element_info" in parsed, "Should contain element info"
    
    async def test_multiple_websites_dom_extraction(self, browser_session):
        """Test DOM extraction across multiple different websites."""
        session_id, manager = browser_session
        
        test_sites = [
            "https://httpbin.org/html",
            "https://jsonplaceholder.typicode.com/",
            "https://www.w3.org/",
        ]
        
        results = []
        
        for site_url in test_sites:
            try:
                # Navigate to site
                nav_command = NavigateCommand(
                    id=f"nav_{len(results)}",
                    method="navigate",
                    session_id=session_id, 
                    url=site_url,
                    wait_until=WaitCondition.LOAD,
                    timeout=15000
                )
                
                nav_result = await manager.execute_navigate(nav_command)
                if not nav_result.success:
                    results.append({"url": site_url, "status": "navigation_failed", "error": str(nav_result)})
                    continue
                
                # Extract page title
                title_command = ExtractCommand(
                    id=f"title_{len(results)}",
                    method="extract",
                    session_id=session_id,
                    selector="title",
                    extract_type=ExtractType.TEXT
                )
                
                title_result = await manager.execute_extract(title_command)
                
                # Extract all paragraphs
                para_command = ExtractCommand(
                    id=f"para_{len(results)}",
                    method="extract", 
                    session_id=session_id,
                    selector="p",
                    extract_type=ExtractType.TEXT,
                    multiple=True
                )
                
                para_result = await manager.execute_extract(para_command)
                
                # Extract meta tags
                meta_command = ExtractCommand(
                    id=f"meta_{len(results)}",
                    method="extract",
                    session_id=session_id,
                    selector="meta[name]",
                    extract_type=ExtractType.ATTRIBUTE,
                    attribute_name="content", 
                    multiple=True
                )
                
                meta_result = await manager.execute_extract(meta_command)
                
                site_data = {
                    "url": site_url,
                    "status": "success",
                    "title": title_result.data if title_result.success else None,
                    "paragraphs_count": para_result.elements_found if para_result.success else 0,
                    "meta_tags_count": meta_result.elements_found if meta_result.success else 0,
                    "load_time_ms": nav_result.load_time_ms
                }
                
                results.append(site_data)
                
            except Exception as e:
                results.append({"url": site_url, "status": "error", "error": str(e)})
        
        # Validate results
        assert len(results) == len(test_sites), "Should have results for all test sites"
        
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count >= 2, f"At least 2 sites should load successfully, got {success_count}"
        
        # Verify DOM data structure is consistent
        for result in results:
            if result["status"] == "success":
                assert "title" in result, "Should extract title"
                assert "paragraphs_count" in result, "Should count paragraphs"
                assert "meta_tags_count" in result, "Should count meta tags"
                assert "load_time_ms" in result, "Should track load time"
    
    async def test_dom_extraction_performance(self, browser_session):
        """Test DOM extraction performance and response times."""
        session_id, manager = browser_session
        
        # Navigate to test page
        nav_command = NavigateCommand(
            id="perf_nav",
            method="navigate",
            session_id=session_id,
            url="https://httpbin.org/html",
            wait_until=WaitCondition.LOAD
        )
        
        await manager.execute_navigate(nav_command)
        
        # Time multiple extraction operations
        extraction_tests = [
            {"selector": "body", "type": ExtractType.HTML, "name": "full_body"},
            {"selector": "h1", "type": ExtractType.TEXT, "name": "heading"},
            {"selector": "p", "type": ExtractType.TEXT, "name": "paragraphs", "multiple": True},
            {"selector": "a", "type": ExtractType.ATTRIBUTE, "attr": "href", "name": "links", "multiple": True},
        ]
        
        performance_results = []
        
        for test in extraction_tests:
            start_time = time.time()
            
            command = ExtractCommand(
                id=f"perf_{test['name']}",
                method="extract",
                session_id=session_id,
                selector=test["selector"],
                extract_type=test["type"],
                multiple=test.get("multiple", False)
            )
            
            if test["type"] == ExtractType.ATTRIBUTE:
                command.attribute_name = test["attr"]
            
            result = await manager.execute_extract(command)
            
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            performance_results.append({
                "test_name": test["name"],
                "execution_time_ms": execution_time,
                "success": result.success,
                "elements_found": result.elements_found if result.success else 0,
                "data_size": len(str(result.data)) if result.success else 0
            })
        
        # Validate performance
        for perf in performance_results:
            assert perf["success"], f"Extraction {perf['test_name']} should succeed"
            assert perf["execution_time_ms"] < 5000, f"Extraction {perf['test_name']} took too long: {perf['execution_time_ms']}ms"
            assert perf["elements_found"] >= 0, f"Should find valid element count for {perf['test_name']}"
    
    async def test_dom_extraction_error_handling(self, browser_session):
        """Test DOM extraction error handling."""
        session_id, manager = browser_session
        
        # Navigate to test page first
        nav_command = NavigateCommand(
            id="error_nav",
            method="navigate", 
            session_id=session_id,
            url="https://example.com",
            wait_until=WaitCondition.LOAD
        )
        
        await manager.execute_navigate(nav_command)
        
        # Test invalid selector
        invalid_selector_command = ExtractCommand(
            id="invalid_selector",
            method="extract",
            session_id=session_id,
            selector="invalid[[[selector",
            extract_type=ExtractType.TEXT
        )
        
        invalid_result = await manager.execute_extract(invalid_selector_command)
        # Should either succeed with 0 elements or return an error
        assert not invalid_result.success or invalid_result.elements_found == 0
        
        # Test non-existent element
        missing_element_command = ExtractCommand(
            id="missing_element",
            method="extract",
            session_id=session_id,
            selector="div.non-existent-class-xyz",
            extract_type=ExtractType.TEXT
        )
        
        missing_result = await manager.execute_extract(missing_element_command)
        # Should return error for missing elements
        assert not missing_result.success, "Should fail when no elements found"
        
        # Test invalid session
        invalid_session_command = ExtractCommand(
            id="invalid_session",
            method="extract",
            session_id="non-existent-session",
            selector="body",
            extract_type=ExtractType.TEXT
        )
        
        session_result = await manager.execute_extract(invalid_session_command)
        assert not session_result.success, "Should fail with invalid session"


async def run_m1_validation():
    """Run M1 DOM extraction validation tests."""
    print("🔍 Running M1 DOM Extraction Validation Tests...")
    print("=" * 60)
    
    # Run tests
    test_instance = TestM1DOMExtraction()
    
    try:
        # Create browser manager
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        # Create session
        session_id = await manager.create_session()
        
        print(f"✅ Browser session created: {session_id}")
        
        # Run basic DOM extraction test
        print("\n📋 Testing basic DOM extraction...")
        try:
            await test_instance.test_basic_dom_extraction((session_id, manager))
            print("✅ Basic DOM extraction: PASS")
        except Exception as e:
            print(f"❌ Basic DOM extraction: FAIL - {e}")
        
        # Run structured DOM test 
        print("\n📋 Testing structured DOM as JSON...")
        try:
            await test_instance.test_structured_dom_as_json((session_id, manager))
            print("✅ Structured DOM as JSON: PASS")
        except Exception as e:
            print(f"❌ Structured DOM as JSON: FAIL - {e}")
        
        # Run multiple websites test
        print("\n📋 Testing multiple websites...")
        try:
            await test_instance.test_multiple_websites_dom_extraction((session_id, manager))
            print("✅ Multiple websites DOM extraction: PASS")
        except Exception as e:
            print(f"❌ Multiple websites DOM extraction: FAIL - {e}")
        
        # Run performance test
        print("\n📋 Testing DOM extraction performance...")
        try:
            await test_instance.test_dom_extraction_performance((session_id, manager))
            print("✅ DOM extraction performance: PASS")
        except Exception as e:
            print(f"❌ DOM extraction performance: FAIL - {e}")
        
        # Run error handling test
        print("\n📋 Testing error handling...")
        try:
            await test_instance.test_dom_extraction_error_handling((session_id, manager))
            print("✅ DOM extraction error handling: PASS")
        except Exception as e:
            print(f"❌ DOM extraction error handling: FAIL - {e}")
        
        # Cleanup
        await manager.close_session(session_id)
        await manager.close()
        
        print("\n" + "=" * 60)
        print("🎯 M1 DOM Extraction Validation Complete")
        
    except Exception as e:
        print(f"❌ Critical error during M1 validation: {e}")
        if 'manager' in locals():
            await manager.close()


if __name__ == "__main__":
    asyncio.run(run_m1_validation())