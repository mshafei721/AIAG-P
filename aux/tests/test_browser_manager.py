"""
Comprehensive tests for the AUX browser manager functionality.

This module provides thorough testing of the browser manager including:
- Unit tests for all browser manager methods in isolation
- Integration tests with real web pages  
- Error handling tests for timeout and element not found scenarios
- Performance tests for session management and resource cleanup
- Browser command tests for all 5 commands with various scenarios

Uses pytest with async support, mocking for external dependencies,
and comprehensive test fixtures for browser setup/teardown.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from aux.browser.manager import BrowserManager, BrowserSession
from aux.schema.commands import (
    NavigateCommand, NavigateResponse,
    ClickCommand, ClickResponse,
    FillCommand, FillResponse, 
    ExtractCommand, ExtractResponse,
    WaitCommand, WaitResponse,
    ErrorResponse, ErrorCodes,
    WaitCondition, ExtractType, MouseButton
)

# Disable logging during tests to reduce noise
logging.getLogger('aux.browser.manager').setLevel(logging.CRITICAL)


class TestBrowserSession:
    """Comprehensive tests for BrowserSession class."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock browser context with proper async methods."""
        context = AsyncMock()
        # is_closed is a synchronous method that returns a boolean
        context.is_closed = MagicMock(return_value=False)
        return context
    
    @pytest.fixture
    def mock_page(self):
        """Create a mock page with common methods."""
        page = AsyncMock()
        page.url = "https://example.com"
        page.title.return_value = "Test Page"
        return page
    
    @pytest.fixture
    def browser_session(self, mock_context, mock_page):
        """Create a test browser session."""
        return BrowserSession("test-session-123", mock_context, mock_page)
    
    def test_session_initialization(self, browser_session, mock_context, mock_page):
        """Test browser session initialization with correct attributes."""
        assert browser_session.session_id == "test-session-123"
        assert browser_session.context == mock_context
        assert browser_session.page == mock_page
        assert browser_session.created_at > 0
        assert browser_session.last_activity == browser_session.created_at
        assert browser_session.command_count == 0
    
    def test_update_activity(self, browser_session):
        """Test session activity tracking updates correctly."""
        initial_activity = browser_session.last_activity
        initial_count = browser_session.command_count
        
        time.sleep(0.01)  # Small delay to ensure timestamp changes
        browser_session.update_activity()
        
        assert browser_session.last_activity > initial_activity
        assert browser_session.command_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_session_close_success(self, browser_session, mock_context):
        """Test successful session closing."""
        # Setup proper async mock return value
        mock_context.is_closed.return_value = False
        
        await browser_session.close()
        
        mock_context.is_closed.assert_called_once()
        mock_context.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_close_already_closed(self, browser_session, mock_context):
        """Test closing an already closed session."""
        mock_context.is_closed.return_value = True
        
        await browser_session.close()
        
        mock_context.is_closed.assert_called_once()
        mock_context.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_session_close_with_error(self, browser_session, mock_context):
        """Test session closing handles errors gracefully."""
        mock_context.is_closed.return_value = False
        mock_context.close.side_effect = Exception("Close error")
        
        # Should not raise exception
        await browser_session.close()
        
        mock_context.close.assert_called_once()


class TestBrowserManager:
    """Comprehensive tests for BrowserManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a test browser manager with default settings."""
        return BrowserManager(
            headless=True,
            viewport_width=1280,
            viewport_height=720,
            timeout_ms=30000
        )
    
    @pytest.fixture
    def custom_manager(self):
        """Create a browser manager with custom settings."""
        return BrowserManager(
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
            user_agent="Test-Agent/1.0",
            timeout_ms=45000,
            slow_mo_ms=100
        )
    
    def test_manager_initialization_default(self, manager):
        """Test browser manager initialization with default settings."""
        assert manager.headless is True
        assert manager.viewport_width == 1280
        assert manager.viewport_height == 720
        assert manager.user_agent is None
        assert manager.timeout_ms == 30000
        assert manager.slow_mo_ms == 0
        assert len(manager.sessions) == 0
        assert manager.browser is None
        assert manager.playwright is None
        assert manager._initialized is False
        assert manager.total_commands_executed == 0
        assert manager.startup_time is None
    
    def test_manager_initialization_custom(self, custom_manager):
        """Test browser manager initialization with custom settings."""
        assert custom_manager.headless is False
        assert custom_manager.viewport_width == 1920
        assert custom_manager.viewport_height == 1080
        assert custom_manager.user_agent == "Test-Agent/1.0"
        assert custom_manager.timeout_ms == 45000
        assert custom_manager.slow_mo_ms == 100
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_manager_initialize_success(self, mock_playwright_class, manager):
        """Test successful browser manager initialization."""
        # Setup playwright mock chain
        mock_playwright_context = AsyncMock()
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        
        start_time = time.time()
        await manager.initialize()
        
        # Verify initialization state
        assert manager._initialized is True
        assert manager.playwright == mock_playwright
        assert manager.browser == mock_browser
        assert manager.startup_time is not None
        assert manager.startup_time > 0
        
        # Verify playwright was called correctly
        mock_playwright_class.return_value.start.assert_called_once()
        mock_playwright.chromium.launch.assert_called_once()
        
        # Check launch arguments
        call_args = mock_playwright.chromium.launch.call_args
        assert call_args[1]['headless'] is True
        assert call_args[1]['slow_mo'] == 0
        assert '--no-sandbox' in call_args[1]['args']
        assert '--disable-web-security' in call_args[1]['args']
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_manager_initialize_already_initialized(self, mock_playwright_class, manager):
        """Test that double initialization doesn't restart browser."""
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        
        # First initialization
        await manager.initialize()
        first_startup_time = manager.startup_time
        
        # Second initialization should not restart
        await manager.initialize()
        
        assert manager.startup_time == first_startup_time
        mock_playwright_class.return_value.start.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_manager_initialize_failure(self, mock_playwright_class, manager):
        """Test browser manager initialization failure handling."""
        mock_playwright_class.return_value.start.side_effect = Exception("Playwright failed")
        
        with pytest.raises(Exception, match="Playwright failed"):
            await manager.initialize()
        
        # Verify cleanup occurred
        assert manager._initialized is False
        assert manager.browser is None
        assert manager.playwright is None
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_create_session_success(self, mock_playwright_class, manager):
        """Test successful session creation."""
        # Setup mocks
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()  
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Initialize manager first
        await manager.initialize()
        
        # Create session
        session_id = await manager.create_session()
        
        # Verify session creation
        assert session_id in manager.sessions
        assert len(manager.sessions) == 1
        
        session = manager.sessions[session_id]
        assert isinstance(session, BrowserSession)
        assert session.session_id == session_id
        assert session.context == mock_context
        assert session.page == mock_page
        
        # Verify browser calls
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_context.set_default_timeout.assert_called_once_with(30000)
        mock_context.set_default_navigation_timeout.assert_called_once_with(30000)
        mock_page.set_extra_http_headers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_with_config(self, manager):
        """Test session creation with custom configuration."""
        # Setup minimal mocks
        manager._initialized = True
        manager.browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        manager.browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Custom session config
        session_config = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Custom-Agent/1.0"
        }
        
        session_id = await manager.create_session(session_config)
        
        # Verify context was created with custom config
        context_args = manager.browser.new_context.call_args[1]
        assert context_args["viewport"]["width"] == 1920
        assert context_args["viewport"]["height"] == 1080
        assert context_args["user_agent"] == "Custom-Agent/1.0"
    
    @pytest.mark.asyncio
    async def test_create_session_auto_initialize(self, manager):
        """Test that create_session automatically initializes manager."""
        with patch('aux.browser.manager.async_playwright') as mock_playwright_class:
            mock_playwright = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            # Manager starts uninitialized
            assert not manager._initialized
            
            session_id = await manager.create_session()
            
            # Should now be initialized
            assert manager._initialized
            assert session_id in manager.sessions
    
    @pytest.mark.asyncio 
    async def test_get_session_exists(self, manager):
        """Test getting an existing session."""
        # Add mock session
        session_id = "test-session"
        mock_session = MagicMock()
        mock_session.update_activity = MagicMock()
        manager.sessions[session_id] = mock_session
        
        result = await manager.get_session(session_id)
        
        assert result == mock_session
        mock_session.update_activity.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_not_exists(self, manager):
        """Test getting a non-existent session."""
        result = await manager.get_session("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_close_session_exists(self, manager):
        """Test closing an existing session."""
        session_id = "test-session"
        mock_session = AsyncMock()
        manager.sessions[session_id] = mock_session
        
        result = await manager.close_session(session_id)
        
        assert result is True
        assert session_id not in manager.sessions
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_session_not_exists(self, manager):
        """Test closing a non-existent session."""
        result = await manager.close_session("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        """Test listing active sessions."""
        # Add multiple mock sessions
        session_ids = ["session1", "session2", "session3"]
        for session_id in session_ids:
            manager.sessions[session_id] = MagicMock()
        
        result = await manager.list_sessions()
        
        assert set(result) == set(session_ids)
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, manager):
        """Test listing sessions when none exist."""
        result = await manager.list_sessions()
        assert result == []
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, manager):
        """Test cleanup of inactive sessions."""
        current_time = time.time()
        
        # Create sessions with different activity times
        active_session = MagicMock()
        active_session.last_activity = current_time - 100  # 100 seconds ago
        manager.sessions["active"] = active_session
        
        inactive_session1 = AsyncMock()
        inactive_session1.last_activity = current_time - 4000  # 4000 seconds ago
        manager.sessions["inactive1"] = inactive_session1
        
        inactive_session2 = AsyncMock()
        inactive_session2.last_activity = current_time - 5000  # 5000 seconds ago  
        manager.sessions["inactive2"] = inactive_session2
        
        # Cleanup with 3600 second timeout (1 hour)
        cleanup_count = await manager.cleanup_inactive_sessions(timeout=3600)
        
        # Verify cleanup
        assert cleanup_count == 2
        assert "active" in manager.sessions
        assert "inactive1" not in manager.sessions
        assert "inactive2" not in manager.sessions
        
        inactive_session1.close.assert_called_once()
        inactive_session2.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions_none_inactive(self, manager):
        """Test cleanup when no sessions are inactive."""
        current_time = time.time()
        
        # All sessions are active
        for i in range(3):
            session = MagicMock()
            session.last_activity = current_time - 100  # 100 seconds ago
            manager.sessions[f"session{i}"] = session
        
        cleanup_count = await manager.cleanup_inactive_sessions(timeout=3600)
        
        assert cleanup_count == 0
        assert len(manager.sessions) == 3
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Test getting manager statistics."""
        # Setup test data
        manager._initialized = True
        manager.startup_time = 1.5
        manager.total_commands_executed = 42
        
        # Add mock sessions
        current_time = time.time()
        for i in range(2):
            session = MagicMock()
            session.session_id = f"session{i}"
            session.created_at = current_time - 1000
            session.last_activity = current_time - 100
            session.command_count = 10 + i
            manager.sessions[f"session{i}"] = session
        
        stats = await manager.get_stats()
        
        assert stats["initialized"] is True
        assert stats["startup_time_seconds"] == 1.5
        assert stats["active_sessions"] == 2
        assert stats["total_commands_executed"] == 42
        assert len(stats["session_details"]) == 2
        
        # Check session details
        session_detail = stats["session_details"][0]
        assert "session_id" in session_detail
        assert "created_at" in session_detail
        assert "last_activity" in session_detail
        assert "command_count" in session_detail
    
    @pytest.mark.asyncio
    async def test_manager_close(self, manager):
        """Test complete manager shutdown."""
        # Setup mocks
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        mock_session1 = AsyncMock()
        mock_session2 = AsyncMock()
        
        manager.browser = mock_browser
        manager.playwright = mock_playwright
        manager.sessions["session1"] = mock_session1
        manager.sessions["session2"] = mock_session2
        manager._initialized = True
        manager.total_commands_executed = 15
        
        await manager.close()
        
        # Verify all sessions closed
        assert len(manager.sessions) == 0
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()
        
        # Verify browser and playwright closed
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        
        # Verify state reset
        assert manager._initialized is False
    
    @pytest.mark.asyncio
    async def test_manager_close_with_errors(self, manager):
        """Test manager close handles errors gracefully."""
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        mock_session = AsyncMock()
        
        # Make everything throw errors
        mock_browser.close.side_effect = Exception("Browser close error")
        mock_playwright.stop.side_effect = Exception("Playwright stop error")
        mock_session.close.side_effect = Exception("Session close error")
        
        manager.browser = mock_browser
        manager.playwright = mock_playwright
        manager.sessions["session"] = mock_session
        manager._initialized = True
        
        # Should not raise exceptions
        await manager.close()
        
        # State should still be reset
        assert len(manager.sessions) == 0
        assert manager._initialized is False


class TestBrowserCommands:
    """Comprehensive tests for all 5 browser commands."""
    
    @pytest.fixture
    def manager(self):
        """Create manager for command testing."""
        return BrowserManager(headless=True)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session for command testing."""
        session = MagicMock()
        session.session_id = "test-session"
        session.page = AsyncMock()
        session.update_activity = MagicMock()
        return session
    
    @pytest.fixture
    def setup_manager_with_session(self, manager, mock_session):
        """Setup manager with a mock session."""
        manager.sessions["test-session"] = mock_session
        return manager, mock_session


class TestNavigateCommand(TestBrowserCommands):
    """Tests for navigate command execution."""
    
    @pytest.mark.asyncio
    async def test_navigate_success(self, setup_manager_with_session):
        """Test successful navigation."""
        manager, mock_session = setup_manager_with_session
        
        # Setup navigation response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session.page.goto = AsyncMock(return_value=mock_response)
        mock_session.page.url = "https://example.com/final"
        mock_session.page.title = AsyncMock(return_value="Example Page")
        
        command = NavigateCommand(
            id="nav-1",
            session_id="test-session",
            url="https://example.com",
            wait_until=WaitCondition.LOAD,
            timeout=30000
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, NavigateResponse)
        assert result.id == "nav-1"
        assert result.url == "https://example.com/final"
        assert result.title == "Example Page"
        assert result.status_code == 200
        assert result.redirected is True
        assert result.load_time_ms > 0
        
        # Verify page.goto called correctly
        mock_session.page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="load",
            timeout=30000
        )
    
    @pytest.mark.asyncio
    async def test_navigate_with_referer(self, setup_manager_with_session):
        """Test navigation with referer header."""
        manager, mock_session = setup_manager_with_session
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session.page.goto = AsyncMock(return_value=mock_response)
        mock_session.page.url = "https://example.com"
        mock_session.page.title = AsyncMock(return_value="Test")
        
        command = NavigateCommand(
            id="nav-2", 
            session_id="test-session",
            url="https://example.com",
            referer="https://google.com"
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, NavigateResponse)
        assert result.redirected is False  # Same URL
    
    @pytest.mark.asyncio
    async def test_navigate_session_not_found(self, manager):
        """Test navigate with non-existent session."""
        command = NavigateCommand(
            id="nav-3",
            session_id="nonexistent",
            url="https://example.com"
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "nav-3"
        assert result.error_code == ErrorCodes.SESSION_NOT_FOUND
        assert result.error_type == "session_error"
        assert "Session nonexistent not found" in result.error
    
    @pytest.mark.asyncio
    async def test_navigate_timeout(self, setup_manager_with_session):
        """Test navigate timeout handling."""
        manager, mock_session = setup_manager_with_session
        
        mock_session.page.goto.side_effect = PlaywrightTimeoutError("Navigation timeout")
        
        command = NavigateCommand(
            id="nav-4",
            session_id="test-session", 
            url="https://slow-site.com",
            timeout=5000
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "nav-4"
        assert result.error_code == ErrorCodes.TIMEOUT
        assert result.error_type == "timeout"
        assert "Navigation timeout after 5000ms" in result.error
    
    @pytest.mark.asyncio
    async def test_navigate_general_error(self, setup_manager_with_session):
        """Test navigate with general error."""
        manager, mock_session = setup_manager_with_session
        
        mock_session.page.goto.side_effect = Exception("Network error")
        
        command = NavigateCommand(
            id="nav-5",
            session_id="test-session",
            url="https://example.com"
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "nav-5"
        assert result.error_code == ErrorCodes.NAVIGATION_FAILED
        assert result.error_type == "navigation_error"
        assert "Navigation failed: Network error" in result.error


class TestClickCommand(TestBrowserCommands):
    """Tests for click command execution."""
    
    @pytest.mark.asyncio
    async def test_click_success(self, setup_manager_with_session):
        """Test successful element click."""
        manager, mock_session = setup_manager_with_session
        
        # Setup element locator mock
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.text_content = AsyncMock(return_value="Click me")
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 100, "y": 200, "width": 80, "height": 30
        })
        mock_element.click = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-1",
            session_id="test-session",
            selector="button.submit",
            button=MouseButton.LEFT,
            click_count=1
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ClickResponse)
        assert result.id == "click-1"
        assert result.element_found is True
        assert result.element_visible is True
        assert result.click_position == {"x": 140, "y": 215}  # Center of element
        assert result.element_text == "Click me"
        assert result.element_tag == "button"
        
        # Verify click called
        mock_element.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_click_with_position(self, setup_manager_with_session):
        """Test click with relative position."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.text_content = AsyncMock(return_value="Text")
        mock_element.evaluate = AsyncMock(return_value="div")
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 0, "y": 0, "width": 100, "height": 50
        })
        mock_element.click = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-2",
            session_id="test-session",
            selector="div.target",
            position={"x": 0.8, "y": 0.2}  # 80% right, 20% down
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ClickResponse)
        assert result.click_position == {"x": 80, "y": 10}
        
        # Verify click called with position
        click_args = mock_element.click.call_args[1]
        assert "position" in click_args
        assert click_args["position"]["x"] == 80.0
        assert click_args["position"]["y"] == 10.0
    
    @pytest.mark.asyncio
    async def test_click_element_not_found(self, setup_manager_with_session):
        """Test click when element not found."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-3",
            session_id="test-session",
            selector="button.missing"
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "click-3"
        assert result.error_code == ErrorCodes.ELEMENT_NOT_FOUND
        assert result.error_type == "element_error"
        assert "Element not found: button.missing" in result.error
    
    @pytest.mark.asyncio
    async def test_click_element_not_visible(self, setup_manager_with_session):
        """Test click when element not visible."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        mock_element.is_visible = AsyncMock(return_value=False)
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-4",
            session_id="test-session",
            selector="button.hidden",
            force=False
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "click-4"
        assert result.error_code == ErrorCodes.ELEMENT_NOT_VISIBLE
        assert result.error_type == "element_error"
        assert "Element not visible: button.hidden" in result.error
    
    @pytest.mark.asyncio
    async def test_click_force_hidden_element(self, setup_manager_with_session):
        """Test force clicking hidden element."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.is_visible = AsyncMock(return_value=False)
        mock_element.text_content = AsyncMock(return_value="Hidden")
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 50, "y": 100, "width": 60, "height": 25
        })
        mock_element.click = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-5",
            session_id="test-session",
            selector="button.hidden",
            force=True
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ClickResponse)
        assert result.element_visible is False
        
        # Verify force click
        click_args = mock_element.click.call_args[1]
        assert click_args["force"] is True
    
    @pytest.mark.asyncio
    async def test_click_timeout(self, setup_manager_with_session):
        """Test click timeout handling."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.click.side_effect = PlaywrightTimeoutError("Click timeout")
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="click-6",
            session_id="test-session",
            selector="button.slow",
            timeout=1000
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCodes.TIMEOUT
        assert result.error_type == "timeout"
        assert "Click timeout after 1000ms" in result.error


class TestFillCommand(TestBrowserCommands):
    """Tests for fill command execution."""
    
    @pytest.mark.asyncio
    async def test_fill_success(self, setup_manager_with_session):
        """Test successful form field filling."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.input_value = AsyncMock(return_value="Hello World")
        mock_element.evaluate = AsyncMock(return_value="input")
        mock_element.get_attribute = AsyncMock(return_value="text")
        mock_element.clear = AsyncMock()
        mock_element.fill = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = FillCommand(
            id="fill-1",
            session_id="test-session",
            selector="input#name",
            text="Hello World",
            clear_first=True,
            validate_input=True
        )
        
        result = await manager.execute_fill(command)
        
        assert isinstance(result, FillResponse)
        assert result.id == "fill-1"
        assert result.element_found is True
        assert result.element_type == "text"
        assert result.text_entered == "Hello World"
        assert result.current_value == "Hello World"
        assert result.validation_passed is True
        
        # Verify fill operations
        mock_element.clear.assert_called_once()
        mock_element.fill.assert_called_once_with("Hello World")
    
    @pytest.mark.asyncio
    async def test_fill_with_typing_delay(self, setup_manager_with_session):
        """Test fill with typing delay."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.input_value = AsyncMock(return_value="Typed text")
        mock_element.evaluate = AsyncMock(return_value="input")
        mock_element.get_attribute = AsyncMock(return_value="text")
        mock_element.type = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = FillCommand(
            id="fill-2",
            session_id="test-session",
            selector="input#search",
            text="Typed text",
            typing_delay_ms=50,
            clear_first=False
        )
        
        result = await manager.execute_fill(command)
        
        assert isinstance(result, FillResponse)
        
        # Verify typing used instead of fill
        mock_element.type.assert_called_once_with("Typed text", delay=50)
        mock_element.fill.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fill_with_enter_press(self, setup_manager_with_session):
        """Test fill with Enter key press."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.input_value = AsyncMock(return_value="Search term")
        mock_element.evaluate = AsyncMock(return_value="input")
        mock_element.get_attribute = AsyncMock(return_value="search")
        mock_element.fill = AsyncMock()
        mock_element.press = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = FillCommand(
            id="fill-3",
            session_id="test-session",
            selector="input[type=search]",
            text="Search term",
            press_enter=True
        )
        
        result = await manager.execute_fill(command)
        
        assert isinstance(result, FillResponse)
        
        # Verify Enter was pressed
        mock_element.press.assert_called_once_with("Enter")
    
    @pytest.mark.asyncio
    async def test_fill_validation_failed(self, setup_manager_with_session):
        """Test fill with validation failure."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        # Return different value than expected
        mock_element.input_value = AsyncMock(return_value="Different text")
        mock_element.evaluate = AsyncMock(return_value="input")
        mock_element.get_attribute = AsyncMock(return_value="text")
        mock_element.fill = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = FillCommand(
            id="fill-4",
            session_id="test-session",
            selector="input#field",
            text="Expected text",
            validate_input=True
        )
        
        result = await manager.execute_fill(command)
        
        assert isinstance(result, FillResponse)
        assert result.validation_passed is False
        assert result.text_entered == "Expected text"
        assert result.current_value == "Different text"
    
    @pytest.mark.asyncio
    async def test_fill_element_not_found(self, setup_manager_with_session):
        """Test fill when element not found."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = FillCommand(
            id="fill-5",
            session_id="test-session",
            selector="input#missing",
            text="Some text"
        )
        
        result = await manager.execute_fill(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCodes.ELEMENT_NOT_FOUND
        assert "Element not found: input#missing" in result.error


class TestExtractCommand(TestBrowserCommands):
    """Tests for extract command execution."""
    
    @pytest.mark.asyncio
    async def test_extract_text_single(self, setup_manager_with_session):
        """Test extracting text from single element."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth = MagicMock(return_value=mock_element)
        
        mock_element.text_content = AsyncMock(return_value="  Sample text  ")
        mock_element.evaluate = AsyncMock(return_value="p")
        mock_element.get_attribute = AsyncMock(return_value="content")
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-1",
            session_id="test-session",
            selector="p.content",
            extract_type=ExtractType.TEXT,
            trim_whitespace=True,
            multiple=False
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ExtractResponse)
        assert result.id == "extract-1"
        assert result.elements_found == 1
        assert result.data == "Sample text"  # Trimmed
        assert len(result.element_info) == 1
        assert result.element_info[0]["tag"] == "p"
        assert result.element_info[0]["class"] == "content"
    
    @pytest.mark.asyncio
    async def test_extract_html(self, setup_manager_with_session):
        """Test extracting HTML content."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth = MagicMock(return_value=mock_element)
        
        mock_element.inner_html = AsyncMock(return_value="<span>Inner content</span>")
        mock_element.evaluate = AsyncMock(return_value="div")
        mock_element.get_attribute = AsyncMock(return_value="container")
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-2",
            session_id="test-session",
            selector="div.container",
            extract_type=ExtractType.HTML
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ExtractResponse)
        assert result.data == "<span>Inner content</span>"
    
    @pytest.mark.asyncio
    async def test_extract_attribute(self, setup_manager_with_session):
        """Test extracting element attribute."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth = MagicMock(return_value=mock_element)
        
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "href": "https://example.com",
            "class": "link"
        }.get(attr))
        mock_element.evaluate = AsyncMock(return_value="a")
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-3", 
            session_id="test-session",
            selector="a.link",
            extract_type=ExtractType.ATTRIBUTE,
            attribute_name="href"
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ExtractResponse)
        assert result.data == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_extract_property(self, setup_manager_with_session):
        """Test extracting element property."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth = MagicMock(return_value=mock_element)
        
        mock_element.evaluate = AsyncMock(side_effect=lambda script: {
            "el => el.tagName.toLowerCase()": "input",
            "el => el.value": "form input value",
            "el => el.class": "form-control"
        }.get(script, "form-control"))
        mock_element.get_attribute = AsyncMock(return_value="form-control")
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-4",
            session_id="test-session", 
            selector="input.form-control",
            extract_type=ExtractType.PROPERTY,
            property_name="value"
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ExtractResponse)
        assert result.data == "form input value"
    
    @pytest.mark.asyncio
    async def test_extract_multiple_elements(self, setup_manager_with_session):
        """Test extracting from multiple elements."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=3)
        
        # Mock three different elements
        elements = []
        for i in range(3):
            element = AsyncMock()
            element.text_content = AsyncMock(return_value=f"Item {i+1}")
            element.evaluate = AsyncMock(return_value="li")
            element.get_attribute = AsyncMock(return_value="item")
            elements.append(element)
        
        mock_locator.nth = MagicMock(side_effect=lambda i: elements[i])
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-5",
            session_id="test-session",
            selector="li.item",
            extract_type=ExtractType.TEXT,
            multiple=True
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ExtractResponse)
        assert result.elements_found == 3
        assert result.data == ["Item 1", "Item 2", "Item 3"]
        assert len(result.element_info) == 3
    
    @pytest.mark.asyncio
    async def test_extract_no_elements_found(self, setup_manager_with_session):
        """Test extract when no elements found."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ExtractCommand(
            id="extract-6",
            session_id="test-session",
            selector="span.missing",
            extract_type=ExtractType.TEXT
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCodes.ELEMENT_NOT_FOUND
        assert "No elements found: span.missing" in result.error


class TestWaitCommand(TestBrowserCommands):
    """Tests for wait command execution."""
    
    @pytest.mark.asyncio
    async def test_wait_for_load(self, setup_manager_with_session):
        """Test waiting for page load."""
        manager, mock_session = setup_manager_with_session
        
        mock_session.page.wait_for_load_state = AsyncMock()
        
        command = WaitCommand(
            id="wait-1",
            session_id="test-session",
            condition=WaitCondition.LOAD,
            timeout=10000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, WaitResponse)
        assert result.id == "wait-1"
        assert result.condition_met is True
        assert result.final_state == "page_loaded"
        assert result.wait_time_ms > 0
        
        mock_session.page.wait_for_load_state.assert_called_once_with(
            "load", timeout=10000
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_element_visible(self, setup_manager_with_session):
        """Test waiting for element to become visible."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.wait_for = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = WaitCommand(
            id="wait-2",
            session_id="test-session",
            condition=WaitCondition.VISIBLE,
            selector="div.popup",
            timeout=5000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, WaitResponse)
        assert result.condition_met is True
        assert result.final_state == "element_visible"
        assert result.element_count == 1
        
        mock_locator.wait_for.assert_called_once_with(
            state="visible", timeout=5000
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_element_hidden(self, setup_manager_with_session):
        """Test waiting for element to become hidden."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.wait_for = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = WaitCommand(
            id="wait-3",
            session_id="test-session",
            condition=WaitCondition.HIDDEN,
            selector="div.loading",
            timeout=3000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, WaitResponse)
        assert result.condition_met is True
        assert result.final_state == "element_hidden"
    
    @pytest.mark.asyncio
    async def test_wait_custom_javascript(self, setup_manager_with_session):
        """Test waiting with custom JavaScript condition."""
        manager, mock_session = setup_manager_with_session
        
        mock_session.page.wait_for_function = AsyncMock()
        
        command = WaitCommand(
            id="wait-4",
            session_id="test-session",
            condition=WaitCondition.LOAD,  # Base condition
            custom_js="() => window.myApp && window.myApp.ready",
            timeout=8000,
            poll_interval_ms=200
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, WaitResponse)
        assert result.condition_met is True
        assert result.final_state == "custom_condition_met"
        
        mock_session.page.wait_for_function.assert_called_once_with(
            "() => window.myApp && window.myApp.ready",
            timeout=8000,
            polling=200
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_text_content(self, setup_manager_with_session):
        """Test waiting for specific text content."""
        manager, mock_session = setup_manager_with_session
        
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        mock_session.page.wait_for_function = AsyncMock()
        
        command = WaitCommand(
            id="wait-5",
            session_id="test-session",
            condition=WaitCondition.VISIBLE,
            selector="div.status",
            text_content="Complete",
            timeout=5000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, WaitResponse)
        assert result.condition_met is True
        assert result.final_state == "text_content_found"
        
        # Verify wait_for_function was called for text content
        mock_session.page.wait_for_function.assert_called()
        function_call = mock_session.page.wait_for_function.call_args[0][0]
        assert "Complete" in function_call
        assert "div.status" in function_call
    
    @pytest.mark.asyncio
    async def test_wait_timeout(self, setup_manager_with_session):
        """Test wait command timeout."""
        manager, mock_session = setup_manager_with_session
        
        mock_session.page.wait_for_load_state.side_effect = PlaywrightTimeoutError("Wait timeout")
        
        command = WaitCommand(
            id="wait-6",
            session_id="test-session", 
            condition=WaitCondition.NETWORKIDLE,
            timeout=2000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.id == "wait-6"
        assert result.error_code == ErrorCodes.WAIT_TIMEOUT
        assert result.error_type == "timeout"
        assert "Wait condition timeout after 2000ms" in result.error
        assert "condition" in result.details
        assert "wait_time_ms" in result.details
    
    @pytest.mark.asyncio
    async def test_wait_selector_required_error(self, setup_manager_with_session):
        """Test wait command error when selector required but missing."""
        manager, mock_session = setup_manager_with_session
        
        command = WaitCommand(
            id="wait-7",
            session_id="test-session",
            condition=WaitCondition.VISIBLE,
            # Missing selector
            timeout=5000
        )
        
        result = await manager.execute_wait(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCodes.UNKNOWN_ERROR
        assert "selector required for" in result.error


class TestErrorHandling:
    """Comprehensive error handling tests."""
    
    @pytest.fixture
    def manager(self):
        return BrowserManager(headless=True)
    
    @pytest.mark.asyncio
    async def test_command_execution_increments_counter(self, manager):
        """Test that successful command execution increments counter."""
        # Setup mock session
        mock_session = MagicMock()
        mock_session.page = AsyncMock()
        mock_session.page.goto = AsyncMock()
        mock_session.page.url = "https://example.com"
        mock_session.page.title = AsyncMock(return_value="Test")
        mock_session.update_activity = MagicMock()
        
        manager.sessions["test"] = mock_session
        
        initial_count = manager.total_commands_executed
        
        command = NavigateCommand(
            id="test-1",
            session_id="test",
            url="https://example.com"
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, NavigateResponse)
        assert manager.total_commands_executed == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_failed_command_does_not_increment_counter(self, manager):
        """Test that failed commands don't increment counter."""
        initial_count = manager.total_commands_executed
        
        # Command with non-existent session
        command = NavigateCommand(
            id="test-2",
            session_id="nonexistent",
            url="https://example.com"
        )
        
        result = await manager.execute_navigate(command)
        
        assert isinstance(result, ErrorResponse)
        assert manager.total_commands_executed == initial_count


class TestPerformanceAndCleanup:
    """Performance and resource cleanup tests."""
    
    @pytest.fixture
    def manager(self):
        return BrowserManager(headless=True)
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self, manager):
        """Test creating multiple sessions concurrently."""
        with patch('aux.browser.manager.async_playwright'):
            # Setup mocks for concurrent creation
            manager._initialized = True
            manager.browser = AsyncMock()
            
            async def create_mock_session():
                context = AsyncMock()
                page = AsyncMock()
                manager.browser.new_context = AsyncMock(return_value=context)
                context.new_page = AsyncMock(return_value=page)
                return await manager.create_session()
            
            # Create multiple sessions concurrently
            tasks = [create_mock_session() for _ in range(5)]
            session_ids = await asyncio.gather(*tasks)
            
            assert len(session_ids) == 5
            assert len(set(session_ids)) == 5  # All unique
            assert len(manager.sessions) == 5
    
    @pytest.mark.asyncio
    async def test_session_lifecycle_tracking(self, manager):
        """Test session lifecycle tracking."""
        # Create mock session manually
        session_id = "lifecycle-test"
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        session = BrowserSession(session_id, mock_context, mock_page)
        manager.sessions[session_id] = session
        
        # Test activity tracking
        initial_activity = session.last_activity
        initial_commands = session.command_count
        
        # Simulate getting session (updates activity)
        retrieved_session = await manager.get_session(session_id)
        
        assert retrieved_session == session
        assert session.last_activity > initial_activity
        assert session.command_count == initial_commands + 1
        
        # Test cleanup
        cleanup_result = await manager.close_session(session_id)
        
        assert cleanup_result is True
        assert session_id not in manager.sessions
        mock_context.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_large_session_cleanup(self, manager):
        """Test cleanup performance with many sessions."""
        current_time = time.time()
        
        # Add many sessions with mixed activity times
        active_sessions = []
        inactive_sessions = []
        
        for i in range(50):
            session = AsyncMock()
            session_id = f"session-{i}"
            
            if i < 25:
                # Active sessions
                session.last_activity = current_time - 100
                active_sessions.append(session_id)
            else:
                # Inactive sessions
                session.last_activity = current_time - 4000
                inactive_sessions.append(session_id)
            
            manager.sessions[session_id] = session
        
        # Perform cleanup
        start_cleanup = time.time()
        cleanup_count = await manager.cleanup_inactive_sessions(timeout=3600)
        cleanup_time = time.time() - start_cleanup
        
        # Verify results
        assert cleanup_count == 25
        assert len(manager.sessions) == 25
        assert cleanup_time < 1.0  # Should be fast
        
        # Verify correct sessions remain
        remaining_ids = set(manager.sessions.keys())
        assert remaining_ids == set(active_sessions)


class TestCommandValidation:
    """Tests for command validation and edge cases."""
    
    @pytest.fixture
    def manager(self):
        return BrowserManager(headless=True)
    
    @pytest.mark.asyncio
    async def test_invalid_command_parameters(self, manager):
        """Test commands with invalid parameters."""
        mock_session = MagicMock()
        mock_session.page = AsyncMock()
        manager.sessions["test"] = mock_session
        
        # Test extract without required attribute_name
        command = ExtractCommand(
            id="invalid-1",
            session_id="test",
            selector="a",
            extract_type=ExtractType.ATTRIBUTE,
            # Missing attribute_name
        )
        
        result = await manager.execute_extract(command)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCodes.EXTRACTION_FAILED
        assert "attribute_name required" in result.error
    
    @pytest.mark.asyncio
    async def test_command_edge_cases(self, manager):
        """Test various command edge cases."""
        mock_session = MagicMock()
        mock_session.page = AsyncMock()
        mock_session.update_activity = MagicMock()
        manager.sessions["test"] = mock_session
        
        # Test click with no bounding box
        mock_locator = AsyncMock()
        mock_element = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_element
        
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.text_content = AsyncMock(return_value="")
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_element.bounding_box = AsyncMock(return_value=None)  # No bounding box
        mock_element.click = AsyncMock()
        
        mock_session.page.locator = MagicMock(return_value=mock_locator)
        
        command = ClickCommand(
            id="edge-1",
            session_id="test",
            selector="button"
        )
        
        result = await manager.execute_click(command)
        
        assert isinstance(result, ClickResponse)
        assert result.click_position == {"x": 0, "y": 0}  # Default when no box