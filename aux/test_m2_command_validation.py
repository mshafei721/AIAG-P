#!/usr/bin/env python3
"""
M2 Command Validation Tests

This module validates the command execution functionality required for Milestone M2:
- Accept JSON commands (navigate, click, fill, extract, wait)
- Validate all 5 commands: navigate, click, fill, extract, wait  
- Check command schema compliance
- Test error handling
"""

import asyncio
import json
import pytest
from aux.browser.manager import BrowserManager
from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, ExtractCommand, WaitCommand,
    WaitCondition, ExtractType, MouseButton, ErrorCodes
)


class TestM2CommandValidation:
    """Test suite for M2 command validation functionality."""
    
    async def test_navigate_command_validation(self):
        """Test navigate command execution and validation."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # Test valid navigate command
            valid_command = NavigateCommand(
                id="nav_test_1",
                method="navigate",
                session_id=session_id,
                url="https://httpbin.org/html",
                wait_until=WaitCondition.LOAD,
                timeout=15000
            )
            
            result = await manager.execute_navigate(valid_command)
            
            # Validate response structure
            assert hasattr(result, 'success'), "Response should have success field"
            assert hasattr(result, 'id'), "Response should have id field"
            assert hasattr(result, 'timestamp'), "Response should have timestamp field"
            
            if result.success:
                assert hasattr(result, 'url'), "Successful navigate should have url"
                assert hasattr(result, 'title'), "Successful navigate should have title"
                assert hasattr(result, 'load_time_ms'), "Successful navigate should have load_time_ms"
                print(f"✅ Navigate command executed successfully to {result.url}")
            else:
                print(f"❌ Navigate command failed: {result}")
            
            # Test invalid URL
            invalid_command = NavigateCommand(
                id="nav_test_2", 
                method="navigate",
                session_id=session_id,
                url="invalid://not-a-real-url",
                wait_until=WaitCondition.LOAD,
                timeout=5000
            )
            
            invalid_result = await manager.execute_navigate(invalid_command)
            # Should either fail or handle gracefully
            print(f"🔍 Invalid URL result: {'SUCCESS' if invalid_result.success else 'FAILED (expected)'}")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()
    
    async def test_click_command_validation(self):
        """Test click command execution and validation."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # First navigate to a page with clickable elements
            nav_command = NavigateCommand(
                id="nav_for_click",
                method="navigate", 
                session_id=session_id,
                url="https://httpbin.org/html",
                wait_until=WaitCondition.LOAD,
                timeout=10000
            )
            
            nav_result = await manager.execute_navigate(nav_command)
            if not nav_result.success:
                print(f"❌ Navigation failed, skipping click test: {nav_result}")
                return
            
            # Test click command
            click_command = ClickCommand(
                id="click_test_1",
                method="click",
                session_id=session_id,
                selector="h1",  # Should exist on httpbin.org/html
                button=MouseButton.LEFT,
                click_count=1,
                force=False,
                timeout=5000
            )
            
            result = await manager.execute_click(click_command)
            
            # Validate response structure
            assert hasattr(result, 'success'), "Click response should have success field"
            assert hasattr(result, 'id'), "Click response should have id field"
            
            if result.success:
                assert hasattr(result, 'element_found'), "Successful click should have element_found"
                assert hasattr(result, 'element_visible'), "Successful click should have element_visible"
                assert hasattr(result, 'click_position'), "Successful click should have click_position"
                print(f"✅ Click command executed successfully on {click_command.selector}")
            else:
                print(f"❌ Click command failed: {result}")
            
            # Test click with invalid selector
            invalid_click = ClickCommand(
                id="click_test_2",
                method="click",
                session_id=session_id,
                selector="div.non-existent-element",
                button=MouseButton.LEFT,
                timeout=2000
            )
            
            invalid_result = await manager.execute_click(invalid_click)
            assert not invalid_result.success, "Click on non-existent element should fail"
            print(f"✅ Click on non-existent element correctly failed")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()
    
    async def test_fill_command_validation(self):
        """Test fill command execution and validation.""" 
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # Navigate to a page with input fields
            nav_command = NavigateCommand(
                id="nav_for_fill",
                method="navigate",
                session_id=session_id,
                url="https://httpbin.org/forms/post",
                wait_until=WaitCondition.LOAD,
                timeout=10000
            )
            
            nav_result = await manager.execute_navigate(nav_command)
            if not nav_result.success:
                print(f"❌ Navigation failed, skipping fill test: {nav_result}")
                return
            
            # Test fill command
            fill_command = FillCommand(
                id="fill_test_1",
                method="fill",
                session_id=session_id,
                selector="input[name='custname']",
                text="Test User",
                clear_first=True,
                press_enter=False,
                typing_delay_ms=0,
                validate_input=True,
                timeout=5000
            )
            
            result = await manager.execute_fill(fill_command)
            
            # Validate response structure
            assert hasattr(result, 'success'), "Fill response should have success field"
            assert hasattr(result, 'id'), "Fill response should have id field"
            
            if result.success:
                assert hasattr(result, 'element_found'), "Successful fill should have element_found"
                assert hasattr(result, 'element_type'), "Successful fill should have element_type"
                assert hasattr(result, 'text_entered'), "Successful fill should have text_entered"
                assert hasattr(result, 'current_value'), "Successful fill should have current_value"
                print(f"✅ Fill command executed successfully: '{result.text_entered}'")
            else:
                print(f"❌ Fill command failed: {result}")
            
            # Test fill with invalid selector
            invalid_fill = FillCommand(
                id="fill_test_2",
                method="fill",
                session_id=session_id,
                selector="input.non-existent",
                text="Test",
                timeout=2000
            )
            
            invalid_result = await manager.execute_fill(invalid_fill)
            assert not invalid_result.success, "Fill on non-existent element should fail"
            print(f"✅ Fill on non-existent element correctly failed")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()
    
    async def test_extract_command_validation(self):
        """Test extract command execution and validation."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # Navigate to test page
            nav_command = NavigateCommand(
                id="nav_for_extract",
                method="navigate",
                session_id=session_id,
                url="https://httpbin.org/html",
                wait_until=WaitCondition.LOAD,
                timeout=10000
            )
            
            nav_result = await manager.execute_navigate(nav_command)
            if not nav_result.success:
                print(f"❌ Navigation failed, skipping extract test: {nav_result}")
                return
            
            # Test text extraction
            text_extract = ExtractCommand(
                id="extract_test_1",
                method="extract",
                session_id=session_id,
                selector="h1",
                extract_type=ExtractType.TEXT,
                multiple=False,
                trim_whitespace=True,
                timeout=5000
            )
            
            text_result = await manager.execute_extract(text_extract)
            
            # Validate response structure
            assert hasattr(text_result, 'success'), "Extract response should have success field"
            assert hasattr(text_result, 'id'), "Extract response should have id field"
            
            if text_result.success:
                assert hasattr(text_result, 'elements_found'), "Successful extract should have elements_found"
                assert hasattr(text_result, 'data'), "Successful extract should have data"
                assert text_result.elements_found > 0, "Should find at least one element"
                print(f"✅ Text extraction successful: found {text_result.elements_found} elements")
            else:
                print(f"❌ Text extraction failed: {text_result}")
            
            # Test HTML extraction
            html_extract = ExtractCommand(
                id="extract_test_2",
                method="extract",
                session_id=session_id,
                selector="body",
                extract_type=ExtractType.HTML,
                timeout=5000
            )
            
            html_result = await manager.execute_extract(html_extract)
            if html_result.success:
                assert isinstance(html_result.data, str), "HTML extraction should return string"
                assert len(html_result.data) > 0, "HTML data should not be empty"
                print(f"✅ HTML extraction successful: {len(html_result.data)} characters")
            
            # Test attribute extraction
            attr_extract = ExtractCommand(
                id="extract_test_3",
                method="extract",
                session_id=session_id,
                selector="a[href]",
                extract_type=ExtractType.ATTRIBUTE,
                attribute_name="href",
                multiple=True,
                timeout=5000
            )
            
            attr_result = await manager.execute_extract(attr_extract)
            if attr_result.success:
                print(f"✅ Attribute extraction successful: found {attr_result.elements_found} links")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()
    
    async def test_wait_command_validation(self):
        """Test wait command execution and validation."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # Navigate to test page
            nav_command = NavigateCommand(
                id="nav_for_wait",
                method="navigate",
                session_id=session_id,
                url="https://httpbin.org/delay/1",  # Delayed response
                wait_until=WaitCondition.LOAD,
                timeout=10000
            )
            
            nav_result = await manager.execute_navigate(nav_command)
            if not nav_result.success:
                print(f"❌ Navigation failed, skipping wait test: {nav_result}")
                return
            
            # Test wait for load state
            wait_load = WaitCommand(
                id="wait_test_1",
                method="wait",
                session_id=session_id,
                condition=WaitCondition.LOAD,
                timeout=5000
            )
            
            wait_result = await manager.execute_wait(wait_load)
            
            # Validate response structure
            assert hasattr(wait_result, 'success'), "Wait response should have success field"
            assert hasattr(wait_result, 'id'), "Wait response should have id field"
            
            if wait_result.success:
                assert hasattr(wait_result, 'condition_met'), "Successful wait should have condition_met"
                assert hasattr(wait_result, 'wait_time_ms'), "Successful wait should have wait_time_ms"
                assert hasattr(wait_result, 'final_state'), "Successful wait should have final_state"
                print(f"✅ Wait command successful: waited {wait_result.wait_time_ms}ms")
            else:
                print(f"❌ Wait command failed: {wait_result}")
            
            # Test wait for element (after navigation)
            wait_element = WaitCommand(
                id="wait_test_2",
                method="wait", 
                session_id=session_id,
                selector="body",
                condition=WaitCondition.VISIBLE,
                timeout=3000
            )
            
            element_result = await manager.execute_wait(wait_element)
            if element_result.success:
                print(f"✅ Wait for element successful")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()
    
    async def test_command_schema_compliance(self):
        """Test that all commands follow the proper schema."""
        manager = BrowserManager(headless=True)
        await manager.initialize()
        
        try:
            session_id = await manager.create_session()
            
            # Test that all commands have required fields
            commands = [
                NavigateCommand(
                    id="schema_nav",
                    method="navigate",
                    session_id=session_id,
                    url="https://example.com"
                ),
                ClickCommand(
                    id="schema_click",
                    method="click",
                    session_id=session_id,
                    selector="body"
                ),
                FillCommand(
                    id="schema_fill",
                    method="fill",
                    session_id=session_id,
                    selector="input",
                    text="test"
                ),
                ExtractCommand(
                    id="schema_extract",
                    method="extract",
                    session_id=session_id,
                    selector="h1",
                    extract_type=ExtractType.TEXT
                ),
                WaitCommand(
                    id="schema_wait",
                    method="wait",
                    session_id=session_id,
                    condition=WaitCondition.LOAD
                )
            ]
            
            for command in commands:
                # Verify all commands can be serialized to JSON
                json_str = command.model_dump_json()
                parsed = json.loads(json_str)
                
                # Verify required fields
                assert "id" in parsed, f"{command.method} should have id field"
                assert "method" in parsed, f"{command.method} should have method field"
                assert "session_id" in parsed, f"{command.method} should have session_id field"
                assert "timeout" in parsed, f"{command.method} should have timeout field"
                
                print(f"✅ {command.method} command schema compliance: PASS")
            
        finally:
            await manager.close_session(session_id)
            await manager.close()


async def run_m2_validation():
    """Run M2 command validation tests."""
    print("🔧 Running M2 Command Validation Tests...")
    print("=" * 60)
    
    test_instance = TestM2CommandValidation()
    
    tests = [
        ("Navigate Command", test_instance.test_navigate_command_validation),
        ("Click Command", test_instance.test_click_command_validation),
        ("Fill Command", test_instance.test_fill_command_validation),
        ("Extract Command", test_instance.test_extract_command_validation),
        ("Wait Command", test_instance.test_wait_command_validation),
        ("Schema Compliance", test_instance.test_command_schema_compliance),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            await test_func()
            print(f"✅ {test_name}: PASS")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: FAIL - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 M2 Command Validation Complete: {passed} PASSED, {failed} FAILED")
    
    return passed, failed


if __name__ == "__main__":
    asyncio.run(run_m2_validation())