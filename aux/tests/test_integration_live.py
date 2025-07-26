"""
Live integration tests for AUX browser manager.

This module provides pytest-compatible integration tests that use the 
test runner functionality for live browser testing with self-contained
HTML pages. These tests validate the complete browser automation workflow.
"""

import pytest
import asyncio
from run_browser_tests import BrowserTestRunner


class TestLiveBrowserIntegration:
    """Live integration tests using the browser test runner."""
    
    @pytest.fixture(scope="class")
    async def test_runner(self):
        """Create and setup a test runner for the class."""
        runner = BrowserTestRunner(headless=True, verbose=False)
        
        setup_success = await runner.setup()
        if not setup_success:
            pytest.fail("Failed to setup browser for integration tests")
        
        yield runner
        
        # Cleanup
        await runner.cleanup()
    
    @pytest.mark.asyncio
    async def test_navigation_integration(self, test_runner):
        """Test navigation integration with real browser."""
        await test_runner.test_navigation()
        
        # Check that navigation test passed
        nav_results = [r for r in test_runner.test_results if "Navigation" in r["test"]]
        assert len(nav_results) > 0
        assert all(r["status"] == "PASS" for r in nav_results), "Navigation tests failed"
    
    @pytest.mark.asyncio
    async def test_click_integration(self, test_runner):
        """Test click integration with real browser."""
        await test_runner.test_click_functionality()
        
        click_results = [r for r in test_runner.test_results if "Click" in r["test"]]
        assert len(click_results) > 0
        assert all(r["status"] == "PASS" for r in click_results), "Click tests failed"
    
    @pytest.mark.asyncio
    async def test_fill_integration(self, test_runner):
        """Test form filling integration with real browser."""
        await test_runner.test_fill_functionality()
        
        fill_results = [r for r in test_runner.test_results if "Fill" in r["test"]]
        assert len(fill_results) > 0
        assert all(r["status"] == "PASS" for r in fill_results), "Fill tests failed"
    
    @pytest.mark.asyncio
    async def test_extract_integration(self, test_runner):
        """Test data extraction integration with real browser."""
        await test_runner.test_extract_functionality()
        
        extract_results = [r for r in test_runner.test_results if "Extract" in r["test"]]
        assert len(extract_results) > 0
        assert all(r["status"] == "PASS" for r in extract_results), "Extract tests failed"
    
    @pytest.mark.asyncio
    async def test_wait_integration(self, test_runner):
        """Test wait conditions integration with real browser."""
        await test_runner.test_wait_functionality()
        
        wait_results = [r for r in test_runner.test_results if "Wait" in r["test"]]
        assert len(wait_results) > 0
        assert all(r["status"] == "PASS" for r in wait_results), "Wait tests failed"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, test_runner):
        """Test error handling integration with real browser."""
        await test_runner.test_error_handling()
        
        error_results = [r for r in test_runner.test_results if "Error Handling" in r["test"]]
        assert len(error_results) > 0
        assert all(r["status"] == "PASS" for r in error_results), "Error handling tests failed"
    
    @pytest.mark.asyncio
    async def test_session_management_integration(self, test_runner):
        """Test session management integration with real browser."""
        await test_runner.test_session_management()
        
        session_results = [r for r in test_runner.test_results if "Session Management" in r["test"]]
        assert len(session_results) > 0
        assert all(r["status"] == "PASS" for r in session_results), "Session management tests failed"
    
    @pytest.mark.asyncio 
    async def test_complete_workflow(self, test_runner):
        """Test complete browser automation workflow."""
        # Run all tests in sequence to validate complete workflow
        success = await test_runner.run_all_tests(quick_mode=False)
        
        assert success, f"Complete workflow failed. {test_runner.failed_tests} tests failed."
        assert test_runner.passed_tests > 0, "No tests were executed"
        
        # Validate that all major command types were tested
        test_categories = {r["test"].split(" - ")[0] for r in test_runner.test_results}
        expected_categories = {"Navigation", "Click", "Fill", "Extract", "Wait", "Error Handling"}
        
        missing_categories = expected_categories - test_categories
        assert not missing_categories, f"Missing test categories: {missing_categories}"


# Standalone test runner for manual execution
if __name__ == "__main__":
    async def run_manual_test():
        """Run integration tests manually without pytest."""
        print("🧪 Running AUX Browser Manager Integration Tests")
        print("=" * 50)
        
        runner = BrowserTestRunner(headless=True, verbose=True)
        
        try:
            # Setup
            if not await runner.setup():
                print("❌ Setup failed!")
                return False
            
            # Run all tests
            success = await runner.run_all_tests(quick_mode=False)
            
            # Print summary
            runner.print_summary()
            
            return success
            
        finally:
            await runner.cleanup()
    
    # Run the manual test
    result = asyncio.run(run_manual_test())
    exit(0 if result else 1)