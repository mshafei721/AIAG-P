"""
Browser Pool Manager for AUX Protocol.

This module provides efficient browser instance pooling and reuse
to improve performance and resource management.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from playwright.async_api import Browser, BrowserContext, Page, Playwright

from ..config import get_config
from ..logging_utils import get_session_logger

logger = logging.getLogger(__name__)


@dataclass
class PooledBrowser:
    """Represents a browser instance in the pool."""
    
    browser: Browser
    created_at: float
    last_used: float
    active_contexts: int = 0
    total_contexts_created: int = 0
    is_healthy: bool = True


@dataclass 
class PooledContext:
    """Represents a browser context that can be reused."""
    
    context: BrowserContext
    browser_id: str
    created_at: float
    last_used: float
    active_pages: int = 0
    total_pages_created: int = 0
    is_healthy: bool = True


class BrowserPool:
    """
    Browser pool manager for efficient resource utilization.
    
    Manages a pool of browser instances and contexts to reduce
    startup overhead and improve performance.
    """
    
    def __init__(self, 
                 min_browsers: int = 2, 
                 max_browsers: int = 10,
                 max_contexts_per_browser: int = 10,
                 browser_idle_timeout: int = 300,
                 context_idle_timeout: int = 180):
        """
        Initialize browser pool.
        
        Args:
            min_browsers: Minimum number of browsers to keep warm
            max_browsers: Maximum number of browsers in pool
            max_contexts_per_browser: Maximum contexts per browser
            browser_idle_timeout: Browser idle timeout in seconds
            context_idle_timeout: Context idle timeout in seconds
        """
        self.min_browsers = min_browsers
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.browser_idle_timeout = browser_idle_timeout
        self.context_idle_timeout = context_idle_timeout
        
        # Pool storage
        self.browsers: Dict[str, PooledBrowser] = {}
        self.contexts: Dict[str, PooledContext] = {}
        self.available_contexts: List[str] = []
        
        # Pool state
        self.playwright: Optional[Playwright] = None
        self.is_initialized = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = get_config()
        self.session_logger = get_session_logger()
        
        # Statistics
        self.stats = {
            'browsers_created': 0,
            'browsers_destroyed': 0,
            'contexts_created': 0,
            'contexts_destroyed': 0,
            'contexts_reused': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
    async def initialize(self) -> None:
        """Initialize the browser pool."""
        if self.is_initialized:
            return
            
        logger.info("Initializing browser pool...")
        
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            
            # Pre-warm the pool
            await self._warm_pool()
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            self.is_initialized = True
            logger.info(f"Browser pool initialized with {len(self.browsers)} browsers")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser pool: {e}")
            await self._cleanup_on_error()
            raise
    
    async def get_context(self, session_config: Optional[Dict] = None) -> tuple[str, BrowserContext]:
        """
        Get a browser context from the pool or create a new one.
        
        Args:
            session_config: Optional session configuration
            
        Returns:
            Tuple of (context_id, context)
        """
        if not self.is_initialized:
            await self.initialize()
        
        # Try to reuse an available context
        context_id = await self._get_available_context(session_config)
        if context_id:
            context_info = self.contexts[context_id]
            context_info.last_used = time.time()
            context_info.active_pages += 1
            self.stats['pool_hits'] += 1
            self.stats['contexts_reused'] += 1
            
            logger.debug(f"Reusing context {context_id}")
            return context_id, context_info.context
        
        # Create new context
        self.stats['pool_misses'] += 1
        return await self._create_new_context(session_config)
    
    async def return_context(self, context_id: str) -> None:
        """
        Return a context to the pool for reuse.
        
        Args:
            context_id: Context identifier
        """
        if context_id not in self.contexts:
            return
            
        context_info = self.contexts[context_id]
        context_info.active_pages = max(0, context_info.active_pages - 1)
        context_info.last_used = time.time()
        
        # Add to available contexts if not in use
        if context_info.active_pages == 0 and context_id not in self.available_contexts:
            # Check if context is still healthy
            try:
                # Simple health check - try to create a new page
                test_page = await context_info.context.new_page()
                await test_page.close()
                context_info.is_healthy = True
                self.available_contexts.append(context_id)
                logger.debug(f"Returned context {context_id} to pool")
            except Exception as e:
                logger.warning(f"Context {context_id} failed health check: {e}")
                context_info.is_healthy = False
                await self._destroy_context(context_id)
    
    async def destroy_context(self, context_id: str) -> None:
        """
        Destroy a specific context.
        
        Args:
            context_id: Context identifier
        """
        await self._destroy_context(context_id)
    
    async def _get_available_context(self, session_config: Optional[Dict] = None) -> Optional[str]:
        """Get an available context that matches the session config."""
        if not self.available_contexts:
            return None
            
        # For now, return the first available context
        # In the future, could match based on session_config
        context_id = self.available_contexts.pop(0)
        
        # Verify context is still healthy
        if context_id in self.contexts and self.contexts[context_id].is_healthy:
            return context_id
        else:
            # Context is unhealthy, destroy it
            if context_id in self.contexts:
                await self._destroy_context(context_id)
            return None
    
    async def _create_new_context(self, session_config: Optional[Dict] = None) -> tuple[str, BrowserContext]:
        """Create a new browser context."""
        # Find a browser with available capacity
        browser_id = await self._get_available_browser()
        if not browser_id:
            # Create new browser if under limit
            if len(self.browsers) < self.max_browsers:
                browser_id = await self._create_browser()
            else:
                # Use least loaded browser
                browser_id = min(self.browsers.keys(), 
                               key=lambda bid: self.browsers[bid].active_contexts)
        
        browser_info = self.browsers[browser_id]
        
        # Create context
        context_options = {
            "viewport": {
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height
            },
            "ignore_https_errors": self.config.browser.ignore_https_errors,
            "java_script_enabled": True,
            "accept_downloads": True,
        }
        
        if self.config.browser.user_agent:
            context_options["user_agent"] = self.config.browser.user_agent
            
        if session_config:
            context_options.update(session_config)
        
        context = await browser_info.browser.new_context(**context_options)
        context.set_default_timeout(self.config.browser.timeout_ms)
        
        # Create context tracking
        context_id = f"{browser_id}_{int(time.time() * 1000)}"
        context_info = PooledContext(
            context=context,
            browser_id=browser_id,
            created_at=time.time(),
            last_used=time.time(),
            active_pages=1
        )
        
        self.contexts[context_id] = context_info
        browser_info.active_contexts += 1
        browser_info.total_contexts_created += 1
        browser_info.last_used = time.time()
        
        self.stats['contexts_created'] += 1
        
        logger.debug(f"Created new context {context_id} in browser {browser_id}")
        return context_id, context
    
    async def _get_available_browser(self) -> Optional[str]:
        """Get a browser with available capacity."""
        for browser_id, browser_info in self.browsers.items():
            if (browser_info.is_healthy and 
                browser_info.active_contexts < self.max_contexts_per_browser):
                return browser_id
        return None
    
    async def _create_browser(self) -> str:
        """Create a new browser instance."""
        try:
            from ..config import config_manager
            launch_args = config_manager.get_browser_launch_args()
            
            launch_options = {
                "headless": self.config.browser.headless,
                "slow_mo": self.config.browser.slow_mo_ms,
                "args": launch_args
            }
            
            browser = await self.playwright.chromium.launch(**launch_options)
            
            browser_id = f"browser_{int(time.time() * 1000)}"
            browser_info = PooledBrowser(
                browser=browser,
                created_at=time.time(),
                last_used=time.time()
            )
            
            self.browsers[browser_id] = browser_info
            self.stats['browsers_created'] += 1
            
            logger.info(f"Created new browser {browser_id}")
            return browser_id
            
        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            raise
    
    async def _destroy_context(self, context_id: str) -> None:
        """Destroy a browser context."""
        if context_id not in self.contexts:
            return
            
        context_info = self.contexts[context_id]
        
        try:
            await context_info.context.close()
        except Exception as e:
            logger.warning(f"Error closing context {context_id}: {e}")
        
        # Update browser tracking
        if context_info.browser_id in self.browsers:
            browser_info = self.browsers[context_info.browser_id]
            browser_info.active_contexts = max(0, browser_info.active_contexts - 1)
        
        # Remove from tracking
        del self.contexts[context_id]
        if context_id in self.available_contexts:
            self.available_contexts.remove(context_id)
        
        self.stats['contexts_destroyed'] += 1
        logger.debug(f"Destroyed context {context_id}")
    
    async def _destroy_browser(self, browser_id: str) -> None:
        """Destroy a browser instance."""
        if browser_id not in self.browsers:
            return
            
        browser_info = self.browsers[browser_id]
        
        # Close all contexts in this browser
        contexts_to_destroy = [
            cid for cid, cinfo in self.contexts.items() 
            if cinfo.browser_id == browser_id
        ]
        
        for context_id in contexts_to_destroy:
            await self._destroy_context(context_id)
        
        # Close browser
        try:
            await browser_info.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser {browser_id}: {e}")
        
        del self.browsers[browser_id]
        self.stats['browsers_destroyed'] += 1
        logger.info(f"Destroyed browser {browser_id}")
    
    async def _warm_pool(self) -> None:
        """Pre-warm the browser pool."""
        for _ in range(self.min_browsers):
            try:
                await self._create_browser()
            except Exception as e:
                logger.warning(f"Failed to warm browser pool: {e}")
                break
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of idle browsers and contexts."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                current_time = time.time()
                
                # Clean up idle contexts
                idle_contexts = [
                    cid for cid, cinfo in self.contexts.items()
                    if (current_time - cinfo.last_used > self.context_idle_timeout and
                        cinfo.active_pages == 0)
                ]
                
                for context_id in idle_contexts:
                    await self._destroy_context(context_id)
                
                # Clean up idle browsers
                idle_browsers = [
                    bid for bid, binfo in self.browsers.items()
                    if (current_time - binfo.last_used > self.browser_idle_timeout and
                        binfo.active_contexts == 0 and
                        len(self.browsers) > self.min_browsers)
                ]
                
                for browser_id in idle_browsers:
                    await self._destroy_browser(browser_id)
                
                # Ensure minimum browsers
                while len(self.browsers) < self.min_browsers:
                    try:
                        await self._create_browser()
                    except Exception as e:
                        logger.error(f"Failed to maintain minimum browsers: {e}")
                        break
                
                if idle_contexts or idle_browsers:
                    logger.info(f"Cleaned up {len(idle_contexts)} contexts and {len(idle_browsers)} browsers")
                
            except asyncio.CancelledError:
                logger.info("Browser pool cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in browser pool cleanup: {e}")
    
    async def get_stats(self) -> Dict:
        """Get browser pool statistics."""
        return {
            **self.stats,
            'active_browsers': len(self.browsers),
            'active_contexts': len(self.contexts),
            'available_contexts': len(self.available_contexts),
            'total_browser_contexts': sum(b.active_contexts for b in self.browsers.values()),
            'healthy_browsers': sum(1 for b in self.browsers.values() if b.is_healthy),
            'healthy_contexts': sum(1 for c in self.contexts.values() if c.is_healthy)
        }
    
    async def _cleanup_on_error(self) -> None:
        """Cleanup resources on initialization error."""
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
        self.is_initialized = False
    
    async def close(self) -> None:
        """Close the browser pool and all resources."""
        logger.info("Closing browser pool...")
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all contexts
        context_ids = list(self.contexts.keys())
        for context_id in context_ids:
            await self._destroy_context(context_id)
        
        # Close all browsers
        browser_ids = list(self.browsers.keys())
        for browser_id in browser_ids:
            await self._destroy_browser(browser_id)
        
        # Stop playwright
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")
        
        self.is_initialized = False
        
        final_stats = await self.get_stats()
        logger.info(f"Browser pool closed. Final stats: {final_stats}")


# Global browser pool instance
_browser_pool: Optional[BrowserPool] = None


def get_browser_pool() -> BrowserPool:
    """Get global browser pool instance."""
    global _browser_pool
    if _browser_pool is None:
        config = get_config()
        _browser_pool = BrowserPool(
            min_browsers=2,
            max_browsers=config.browser.max_sessions,
            max_contexts_per_browser=5,
            browser_idle_timeout=config.browser.session_timeout_seconds,
            context_idle_timeout=config.browser.session_timeout_seconds // 2
        )
    return _browser_pool


async def init_browser_pool() -> BrowserPool:
    """Initialize global browser pool."""
    pool = get_browser_pool()
    await pool.initialize()
    return pool