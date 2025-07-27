"""
Unit tests for BrowserManager class.

Tests all command execution methods, session management,
error handling, and browser lifecycle management.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from aux.browser.manager import BrowserManager, BrowserSession
from aux.schema.commands import (
    NavigateCommand, ClickCommand, FillCommand, 
    ExtractCommand, WaitCommand, ErrorCodes
)
from aux.config import Config
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


@pytest.mark.unit
class TestBrowserManager:
    """Test cases for BrowserManager class."""

    @pytest.fixture
    def mock_config(self) -> Config:
        """Provide mock configuration for testing."""
        return Config(
            browser_config={
                "headless": True,
                "timeout": 30000,
                "viewport": {"width": 1280, "height": 720},
                "user_agent": "AUX-Test-Agent/1.0",
            }
        )

    @pytest.fixture
    def browser_manager(self, mock_config: Config) -> BrowserManager:
        """Provide BrowserManager instance for testing."""
        return BrowserManager(mock_config)

    @pytest.fixture
    def mock_browser_session(self) -> Mock:
        """Provide mock browser session."""
        session = Mock(spec=BrowserSession)
        session.session_id = "test-session-123"
        session.page = AsyncMock()
        session.context = AsyncMock()
        session.created_at = asyncio.get_event_loop().time()
        session.last_activity = asyncio.get_event_loop().time()
        session.security_manager = Mock()
        return session

    async def test_start_browser_manager(self, browser_manager: BrowserManager):
        """Test starting browser manager initializes Playwright."""
        with patch("aux.browser.manager.async_playwright") as mock_playwright:
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock()
            await browser_manager.start()
            assert browser_manager.playwright is not None
            assert browser_manager.browser is not None

    async def test_stop_browser_manager(self, browser_manager: BrowserManager):
        """Test stopping browser manager cleans up resources."""
        # Setup mock browser
        browser_manager.browser = AsyncMock()
        browser_manager.playwright = AsyncMock()
        browser_manager.sessions = {"test": Mock()}

        await browser_manager.stop()
        
        browser_manager.browser.close.assert_called_once()
        assert len(browser_manager.sessions) == 0

    async def test_create_session_success(self, browser_manager: BrowserManager):
        """Test successful session creation."""
        browser_manager.browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        browser_manager.browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        session_id = "test-session"
        session = await browser_manager.create_session(session_id)

        assert session.session_id == session_id
        assert session in browser_manager.sessions.values()
        browser_manager.browser.new_context.assert_called_once()

    async def test_create_session_duplicate_id(self, browser_manager: BrowserManager):
        """Test creating session with duplicate ID raises error."""
        session_id = "duplicate-session"
        browser_manager.sessions[session_id] = Mock()

        with pytest.raises(ValueError, match="Session .* already exists"):
            await browser_manager.create_session(session_id)

    async def test_get_session_exists(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test getting existing session returns session."""
        session_id = "existing-session"
        browser_manager.sessions[session_id] = mock_browser_session

        session = browser_manager.get_session(session_id)
        assert session == mock_browser_session

    async def test_get_session_not_exists(self, browser_manager: BrowserManager):
        """Test getting non-existing session raises error."""
        with pytest.raises(ValueError, match="Session .* not found"):
            browser_manager.get_session("non-existing")

    async def test_close_session_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful session closure."""
        session_id = "test-session"
        browser_manager.sessions[session_id] = mock_browser_session

        await browser_manager.close_session(session_id)
        
        mock_browser_session.context.close.assert_called_once()
        assert session_id not in browser_manager.sessions

    async def test_close_session_not_exists(self, browser_manager: BrowserManager):
        """Test closing non-existing session raises error."""
        with pytest.raises(ValueError, match="Session .* not found"):
            await browser_manager.close_session("non-existing")

    async def test_execute_navigate_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful navigate command execution."""
        command = NavigateCommand(
            method="navigate",
            url="https://example.com",
            wait_until="load"
        )
        
        mock_browser_session.page.goto = AsyncMock()
        mock_browser_session.page.url = "https://example.com"
        mock_browser_session.page.title.return_value = "Example"

        response = await browser_manager.execute_navigate(mock_browser_session, command)

        assert response.status == "success"
        assert response.url == "https://example.com"
        mock_browser_session.page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="load",
            timeout=30000
        )

    async def test_execute_navigate_timeout(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test navigate command with timeout error."""
        command = NavigateCommand(
            method="navigate",
            url="https://example.com"
        )
        
        mock_browser_session.page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))

        response = await browser_manager.execute_navigate(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == ErrorCodes.TIMEOUT

    async def test_execute_click_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful click command execution."""
        command = ClickCommand(
            method="click",
            selector="#button"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.click = AsyncMock()
        mock_element.is_visible.return_value = True

        response = await browser_manager.execute_click(mock_browser_session, command)

        assert response.status == "success"
        assert response.selector == "#button"
        mock_element.click.assert_called_once()

    async def test_execute_click_element_not_found(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test click command with element not found error."""
        command = ClickCommand(
            method="click",
            selector="#missing"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.click = AsyncMock(side_effect=PlaywrightTimeoutError("Element not found"))

        response = await browser_manager.execute_click(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == ErrorCodes.ELEMENT_NOT_FOUND

    async def test_execute_fill_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful fill command execution."""
        command = FillCommand(
            method="fill",
            selector="#input",
            value="test value"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.fill = AsyncMock()
        mock_element.input_value.return_value = "test value"

        response = await browser_manager.execute_fill(mock_browser_session, command)

        assert response.status == "success"
        assert response.selector == "#input"
        mock_element.fill.assert_called_once_with("test value")

    async def test_execute_fill_validation_error(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test fill command with validation error."""
        command = FillCommand(
            method="fill",
            selector="#input",
            value="<script>alert('xss')</script>"
        )
        
        mock_browser_session.security_manager.sanitize_input.side_effect = ValueError("Malicious input")

        response = await browser_manager.execute_fill(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == ErrorCodes.VALIDATION_ERROR

    async def test_execute_extract_text_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful extract text command execution."""
        command = ExtractCommand(
            method="extract",
            selector="h1",
            extract_type="text"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.text_content.return_value = "Heading Text"

        response = await browser_manager.execute_extract(mock_browser_session, command)

        assert response.status == "success"
        assert response.data == "Heading Text"

    async def test_execute_extract_multiple_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful extract multiple elements command execution."""
        command = ExtractCommand(
            method="extract",
            selector="li",
            extract_type="multiple"
        )
        
        mock_elements = [AsyncMock(), AsyncMock()]
        mock_elements[0].text_content.return_value = "Item 1"
        mock_elements[1].text_content.return_value = "Item 2"
        mock_browser_session.page.locator.return_value.all.return_value = mock_elements

        response = await browser_manager.execute_extract(mock_browser_session, command)

        assert response.status == "success"
        assert response.data == ["Item 1", "Item 2"]

    async def test_execute_wait_visible_success(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test successful wait for visible command execution."""
        command = WaitCommand(
            method="wait",
            condition="visible",
            selector="#element"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.wait_for.return_value = None

        response = await browser_manager.execute_wait(mock_browser_session, command)

        assert response.status == "success"
        mock_element.wait_for.assert_called_once_with(state="visible", timeout=30000)

    async def test_execute_wait_timeout(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test wait command with timeout error."""
        command = WaitCommand(
            method="wait",
            condition="visible",
            selector="#element"
        )
        
        mock_element = AsyncMock()
        mock_browser_session.page.locator.return_value = mock_element
        mock_element.wait_for.side_effect = PlaywrightTimeoutError("Wait timeout")

        response = await browser_manager.execute_wait(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == ErrorCodes.TIMEOUT

    async def test_session_cleanup_on_timeout(self, browser_manager: BrowserManager):
        """Test automatic session cleanup on timeout."""
        # Create expired session
        expired_session = Mock()
        expired_session.session_id = "expired"
        expired_session.last_activity = asyncio.get_event_loop().time() - 7200  # 2 hours ago
        expired_session.context.close = AsyncMock()
        
        browser_manager.sessions["expired"] = expired_session
        browser_manager.max_session_age = 3600  # 1 hour

        await browser_manager.cleanup_expired_sessions()

        assert "expired" not in browser_manager.sessions
        expired_session.context.close.assert_called_once()

    async def test_concurrent_session_limit(self, browser_manager: BrowserManager):
        """Test enforcement of concurrent session limits."""
        browser_manager.max_sessions = 2
        browser_manager.browser = AsyncMock()
        
        # Create mock context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        browser_manager.browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Create first two sessions (should succeed)
        await browser_manager.create_session("session1")
        await browser_manager.create_session("session2")

        # Third session should fail
        with pytest.raises(RuntimeError, match="Maximum sessions reached"):
            await browser_manager.create_session("session3")

    async def test_invalid_url_handling(self, browser_manager: BrowserManager, mock_browser_session: Mock):
        """Test handling of invalid URLs in navigate command."""
        command = NavigateCommand(
            method="navigate",
            url="not-a-valid-url"
        )
        
        response = await browser_manager.execute_navigate(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == ErrorCodes.INVALID_URL

    @pytest.mark.parametrize("selector,expected_error", [
        ("", ErrorCodes.INVALID_SELECTOR),
        ("javascript:alert('xss')", ErrorCodes.SECURITY_VIOLATION),
        ("eval(malicious)", ErrorCodes.SECURITY_VIOLATION),
    ])
    async def test_malicious_selector_handling(
        self, 
        browser_manager: BrowserManager, 
        mock_browser_session: Mock,
        selector: str,
        expected_error: str
    ):
        """Test handling of malicious selectors."""
        mock_browser_session.security_manager.validate_selector.side_effect = ValueError("Invalid selector")
        
        command = ClickCommand(method="click", selector=selector)
        response = await browser_manager.execute_click(mock_browser_session, command)

        assert response.status == "error"
        assert response.error_code == expected_error