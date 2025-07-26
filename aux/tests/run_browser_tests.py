#!/usr/bin/env python3
"""
Test runner script for AUX browser manager validation.

This script provides a comprehensive validation of the browser automation
functionality without requiring external websites. It uses data URLs to
create self-contained test pages and validates all 5 core AUX commands.

Usage:
    python run_browser_tests.py [--headless] [--verbose] [--quick]
    
Options:
    --headless      Run browser in headless mode (default: True)
    --verbose       Enable verbose output
    --quick         Run only essential tests (faster)
    --no-cleanup    Keep browser open for debugging
"""

import asyncio
import argparse
import logging
import sys
import time
from typing import List, Dict, Any, Optional

from aux.browser.manager import BrowserManager
from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, 
    ExtractCommand, WaitCommand, ErrorResponse,
    WaitCondition, ExtractType, MouseButton
)
from test_pages import get_test_page_urls


class BrowserTestRunner:
    """Comprehensive browser automation test runner."""
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        """
        Initialize the test runner.
        
        Args:
            headless: Whether to run browser in headless mode
            verbose: Whether to enable verbose logging
        """
        self.headless = headless
        self.verbose = verbose
        self.manager: Optional[BrowserManager] = None
        self.session_id: Optional[str] = None
        self.test_urls = get_test_page_urls()
        
        # Test results tracking
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results: List[Dict[str, Any]] = []
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def setup(self) -> bool:
        """
        Setup browser manager and session.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            self.logger.info("Setting up browser manager...")
            
            self.manager = BrowserManager(
                headless=self.headless,
                viewport_width=1280,
                viewport_height=720,
                timeout_ms=15000
            )
            
            await self.manager.initialize()
            self.session_id = await self.manager.create_session()
            
            self.logger.info(f"Browser setup complete. Session ID: {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self.manager:
            try:
                self.logger.info("Cleaning up browser resources...")
                await self.manager.close()
                self.logger.info("Cleanup complete")
            except Exception as e:
                self.logger.warning(f"Cleanup error: {e}")
    
    def record_test(self, test_name: str, success: bool, details: str = "", duration: float = 0.0) -> None:
        """
        Record test result.
        
        Args:
            test_name: Name of the test
            success: Whether test passed
            details: Additional test details
            duration: Test execution time
        """
        if success:
            self.passed_tests += 1
            status = "PASS"
        else:
            self.failed_tests += 1
            status = "FAIL"
        
        result = {
            "test": test_name,
            "status": status,
            "duration": duration,
            "details": details
        }
        
        self.test_results.append(result)
        
        if self.verbose or not success:
            print(f"[{status}] {test_name} ({duration:.2f}s)")
            if details:
                print(f"    {details}")
    
    async def test_navigation(self) -> None:
        """Test basic navigation functionality."""
        test_name = "Navigation - Basic Page Load"
        start_time = time.time()
        
        try:
            command = NavigateCommand(
                id="nav-test-1",
                session_id=self.session_id,
                url=self.test_urls["basic"],
                wait_until=WaitCondition.LOAD,
                timeout=10000
            )
            
            result = await self.manager.execute_navigate(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Navigation failed: {result.error}", duration)
                return
            
            # Validate response
            success = (
                result.url.startswith("data:text/html") and
                result.title == "Basic Test Page" and
                result.load_time_ms > 0
            )
            
            details = f"Title: {result.title}, Load time: {result.load_time_ms}ms"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_click_functionality(self) -> None:
        """Test click command functionality."""
        # First navigate to test page
        await self.manager.execute_navigate(NavigateCommand(
            id="nav-for-click",
            session_id=self.session_id,
            url=self.test_urls["basic"]
        ))
        
        test_name = "Click - Basic Button Click"
        start_time = time.time()
        
        try:
            command = ClickCommand(
                id="click-test-1",
                session_id=self.session_id,
                selector="#test-button",
                button=MouseButton.LEFT,
                timeout=5000
            )
            
            result = await self.manager.execute_click(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Click failed: {result.error}", duration)
                return
            
            success = (
                result.element_found and
                result.element_visible and
                result.element_tag == "button"
            )
            
            details = f"Element: {result.element_tag}, Text: {result.element_text}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_fill_functionality(self) -> None:
        """Test form filling functionality."""
        # Navigate to forms test page
        await self.manager.execute_navigate(NavigateCommand(
            id="nav-for-fill",
            session_id=self.session_id,
            url=self.test_urls["forms"]
        ))
        
        test_name = "Fill - Text Input"
        start_time = time.time()
        
        try:
            test_text = "Test input value"
            command = FillCommand(
                id="fill-test-1",
                session_id=self.session_id,
                selector="#username",
                text=test_text,
                clear_first=True,
                validate_input=True,
                timeout=5000
            )
            
            result = await self.manager.execute_fill(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Fill failed: {result.error}", duration)  
                return
            
            success = (
                result.element_found and
                result.text_entered == test_text and
                result.validation_passed
            )
            
            details = f"Text: '{result.text_entered}', Validation: {result.validation_passed}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_extract_functionality(self) -> None:
        """Test data extraction functionality."""
        # Navigate to basic test page
        await self.manager.execute_navigate(NavigateCommand(
            id="nav-for-extract",
            session_id=self.session_id,
            url=self.test_urls["basic"]
        ))
        
        # Test text extraction
        test_name = "Extract - Text Content"
        start_time = time.time()
        
        try:
            command = ExtractCommand(
                id="extract-test-1",
                session_id=self.session_id,
                selector=".content-text",
                extract_type=ExtractType.TEXT,
                trim_whitespace=True,
                timeout=5000
            )
            
            result = await self.manager.execute_extract(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Extract failed: {result.error}", duration)
                return
            
            success = (
                result.elements_found > 0 and
                isinstance(result.data, str) and
                len(result.data) > 0
            )
            
            details = f"Elements: {result.elements_found}, Data: '{result.data[:50]}...'"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
        
        # Test attribute extraction
        test_name = "Extract - Attribute Value"
        start_time = time.time()
        
        try:
            command = ExtractCommand(
                id="extract-test-2",
                session_id=self.session_id,
                selector=".test-link",
                extract_type=ExtractType.ATTRIBUTE,
                attribute_name="href",
                timeout=5000
            )
            
            result = await self.manager.execute_extract(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Extract failed: {result.error}", duration)
                return
            
            success = (
                result.elements_found > 0 and
                isinstance(result.data, str) and
                result.data.startswith("http")
            )
            
            details = f"Href: {result.data}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_wait_functionality(self) -> None:
        """Test wait condition functionality."""
        # Navigate to dynamic content page
        await self.manager.execute_navigate(NavigateCommand(
            id="nav-for-wait",
            session_id=self.session_id,
            url=self.test_urls["dynamic"]
        ))
        
        test_name = "Wait - Element Visible"
        start_time = time.time()
        
        try:
            # Wait for timed content to appear (appears after 3 seconds)
            command = WaitCommand(
                id="wait-test-1",
                session_id=self.session_id,
                condition=WaitCondition.VISIBLE,
                selector="#timed-content",
                timeout=8000
            )
            
            result = await self.manager.execute_wait(command)
            duration = time.time() - start_time
            
            if isinstance(result, ErrorResponse):
                self.record_test(test_name, False, f"Wait failed: {result.error}", duration)
                return
            
            success = (
                result.condition_met and
                result.final_state == "element_visible" and
                result.wait_time_ms > 2000  # Should wait at least 2 seconds
            )
            
            details = f"Wait time: {result.wait_time_ms}ms, State: {result.final_state}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_error_handling(self) -> None:
        """Test error handling scenarios."""
        test_name = "Error Handling - Element Not Found"
        start_time = time.time()
        
        try:
            # Try to click non-existent element
            command = ClickCommand(
                id="error-test-1",
                session_id=self.session_id,
                selector="#nonexistent-element",
                timeout=2000
            )
            
            result = await self.manager.execute_click(command)
            duration = time.time() - start_time
            
            # Should return error response
            success = (
                isinstance(result, ErrorResponse) and
                "not found" in result.error.lower()
            )
            
            details = f"Error type: {getattr(result, 'error_type', 'N/A')}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_session_management(self) -> None:
        """Test session management functionality."""
        test_name = "Session Management - Multiple Sessions"
        start_time = time.time()
        
        try:
            # Create additional sessions
            session2 = await self.manager.create_session()
            session3 = await self.manager.create_session()
            
            # List sessions
            sessions = await self.manager.list_sessions()
            
            # Test session isolation by navigating to different pages
            await self.manager.execute_navigate(NavigateCommand(
                id="nav-session2",
                session_id=session2,
                url=self.test_urls["forms"]
            ))
            
            await self.manager.execute_navigate(NavigateCommand(
                id="nav-session3", 
                session_id=session3,
                url=self.test_urls["dynamic"]
            ))
            
            # Close extra sessions
            await self.manager.close_session(session2)
            await self.manager.close_session(session3)
            
            final_sessions = await self.manager.list_sessions()
            duration = time.time() - start_time
            
            success = (
                len(sessions) >= 3 and
                len(final_sessions) == 1 and
                self.session_id in final_sessions
            )
            
            details = f"Peak sessions: {len(sessions)}, Final sessions: {len(final_sessions)}"
            self.record_test(test_name, success, details, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.record_test(test_name, False, f"Exception: {str(e)}", duration)
    
    async def run_all_tests(self, quick_mode: bool = False) -> bool:
        """
        Run all browser automation tests.
        
        Args:
            quick_mode: If True, skip some longer tests
            
        Returns:
            True if all tests passed, False otherwise
        """
        self.logger.info("Starting browser automation tests...")
        
        tests = [
            ("Navigation", self.test_navigation),
            ("Click", self.test_click_functionality), 
            ("Fill", self.test_fill_functionality),
            ("Extract", self.test_extract_functionality),
            ("Wait", self.test_wait_functionality),
            ("Error Handling", self.test_error_handling),
        ]
        
        if not quick_mode:
            tests.append(("Session Management", self.test_session_management))
        
        for test_category, test_func in tests:
            self.logger.info(f"Running {test_category} tests...")
            try:
                await test_func()
            except Exception as e:
                self.logger.error(f"Test category {test_category} failed: {e}")
                self.record_test(f"{test_category} - CATEGORY FAILURE", False, str(e))
        
        return self.failed_tests == 0
    
    def print_summary(self) -> None:
        """Print test summary."""
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("BROWSER AUTOMATION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        print("="*60)


async def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="AUX Browser Manager Test Runner")
    parser.add_argument("--headless", action="store_true", default=True,
                       help="Run browser in headless mode")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--quick", action="store_true", 
                       help="Run only essential tests")
    parser.add_argument("--no-cleanup", action="store_true",
                       help="Keep browser open for debugging")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = BrowserTestRunner(
        headless=args.headless,
        verbose=args.verbose
    )
    
    success = False
    try:
        # Setup browser
        if not await runner.setup():
            print("❌ Browser setup failed!")
            return 1
        
        print(f"🚀 Running browser tests (headless={args.headless})")
        if args.quick:
            print("⚡ Quick mode enabled - skipping longer tests")
        
        # Run tests
        success = await runner.run_all_tests(quick_mode=args.quick)
        
        # Print results
        runner.print_summary()
        
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
    
    finally:
        # Cleanup unless requested not to
        if not args.no_cleanup:
            await runner.cleanup()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))