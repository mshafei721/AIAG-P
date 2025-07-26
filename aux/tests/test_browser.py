"""
Tests for AUX Protocol Browser Manager.

This module contains unit tests for browser management functionality
including session creation, lifecycle management, and cleanup.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aux.browser.manager import BrowserManager, BrowserSession


class TestBrowserSession:
    """Test cases for browser session functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock browser context."""
        context = AsyncMock()
        return context
    
    @pytest.fixture
    def mock_page(self):
        """Create a mock page."""
        page = AsyncMock()
        return page
    
    def test_session_initialization(self, mock_context, mock_page):
        """Test browser session initialization."""
        session_id = "test-session-123"
        session = BrowserSession(session_id, mock_context, mock_page)
        
        assert session.session_id == session_id
        assert session.context == mock_context
        assert session.page == mock_page
        assert session.created_at > 0
        assert session.last_activity == session.created_at
    
    @pytest.mark.asyncio
    async def test_session_close(self, mock_context, mock_page):
        """Test browser session closing."""
        session = BrowserSession("test-session", mock_context, mock_page)
        
        await session.close()
        
        mock_context.close.assert_called_once()


class TestBrowserManager:
    """Test cases for browser manager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a test browser manager."""
        return BrowserManager(browser_type="chromium", headless=True)
    
    def test_manager_initialization(self, manager):
        """Test browser manager initialization."""
        assert manager.browser_type == "chromium"
        assert manager.headless is True
        assert len(manager.sessions) == 0
        assert manager.browser is None
        assert manager.playwright is None
        assert manager._initialized is False
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_manager_initialize(self, mock_playwright_class, manager):
        """Test browser manager initialization."""
        # Setup mocks
        mock_playwright = AsyncMock()
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        
        mock_browser_launcher = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser_launcher.launch.return_value = mock_browser
        
        mock_playwright.chromium = mock_browser_launcher
        
        # Initialize manager
        await manager.initialize()
        
        # Verify initialization
        assert manager._initialized is True
        assert manager.playwright == mock_playwright
        assert manager.browser == mock_browser
        mock_browser_launcher.launch.assert_called_once_with(headless=True)
    
    @pytest.mark.asyncio
    @patch('aux.browser.manager.async_playwright')
    async def test_create_session(self, mock_playwright_class, manager):
        """Test session creation."""
        # Setup mocks
        mock_playwright = AsyncMock()
        mock_playwright_class.return_value.start = AsyncMock(return_value=mock_playwright)
        
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_playwright.chromium.launch.return_value = mock_browser
        manager.browser = mock_browser
        manager.playwright = mock_playwright
        manager._initialized = True
        
        # Create session
        session_id = await manager.create_session()
        
        # Verify session creation
        assert session_id in manager.sessions
        session = manager.sessions[session_id]
        assert isinstance(session, BrowserSession)
        assert session.session_id == session_id
        assert session.context == mock_context
        assert session.page == mock_page
    
    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        """Test getting a session."""
        # Add a mock session
        session_id = "test-session"
        mock_session = MagicMock()
        manager.sessions[session_id] = mock_session
        
        # Get session
        result = await manager.get_session(session_id)
        
        # Verify result
        assert result == mock_session
        assert mock_session.last_activity > 0
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, manager):
        """Test getting a non-existent session."""
        result = await manager.get_session("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_close_session(self, manager):
        """Test closing a session."""
        # Add a mock session
        session_id = "test-session"
        mock_session = AsyncMock()
        manager.sessions[session_id] = mock_session
        
        # Close session
        result = await manager.close_session(session_id)
        
        # Verify session was closed
        assert result is True
        assert session_id not in manager.sessions
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self, manager):
        """Test closing a non-existent session."""
        result = await manager.close_session("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        """Test listing sessions."""
        # Add mock sessions
        session_ids = ["session1", "session2", "session3"]
        for session_id in session_ids:
            manager.sessions[session_id] = MagicMock()
        
        # List sessions
        result = await manager.list_sessions()
        
        # Verify result
        assert set(result) == set(session_ids)
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, manager):
        """Test cleanup of inactive sessions."""
        # Add mock sessions with different activity times
        import time
        current_time = time.time()
        
        # Active session
        active_session = MagicMock()
        active_session.last_activity = current_time - 100  # 100 seconds ago
        manager.sessions["active"] = active_session
        
        # Inactive session
        inactive_session = AsyncMock()
        inactive_session.last_activity = current_time - 4000  # 4000 seconds ago
        manager.sessions["inactive"] = inactive_session
        
        # Cleanup with 3600 second timeout
        cleanup_count = await manager.cleanup_inactive_sessions(timeout=3600)
        
        # Verify cleanup
        assert cleanup_count == 1
        assert "active" in manager.sessions
        assert "inactive" not in manager.sessions
        inactive_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manager_close(self, manager):
        """Test browser manager closing."""
        # Setup mocks
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        mock_session = AsyncMock()
        
        manager.browser = mock_browser
        manager.playwright = mock_playwright
        manager.sessions["test"] = mock_session
        manager._initialized = True
        
        # Close manager
        await manager.close()
        
        # Verify cleanup
        assert len(manager.sessions) == 0
        assert manager._initialized is False
        mock_session.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()