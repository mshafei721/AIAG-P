"""
Comprehensive Playwright Browser Manager for AUX Protocol.

This module implements a full-featured browser automation manager using Playwright
with Chrome browser support. Provides session management, command execution,
and robust error handling for all 5 core AUX commands.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, Any, List, Union
from playwright.async_api import (
    async_playwright, Browser, BrowserContext, Page, Playwright,
    TimeoutError as PlaywrightTimeoutError, Locator, ElementHandle
)

from ..schema.commands import (
    NavigateCommand, NavigateResponse,
    ClickCommand, ClickResponse, 
    FillCommand, FillResponse,
    ExtractCommand, ExtractResponse,
    WaitCommand, WaitResponse,
    ErrorResponse, create_error_response, ErrorCodes,
    WaitCondition, ExtractType, MouseButton
)
from ..config import get_config, BrowserConfig
from ..logging_utils import get_session_logger, get_state_tracker
from ..security import SecurityManager

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    Represents an isolated browser session with command execution capabilities.
    
    Each session maintains its own browser context and page, providing complete
    isolation between different client sessions.
    """
    
    def __init__(self, session_id: str, context: BrowserContext, page: Page):
        """
        Initialize a browser session.
        
        Args:
            session_id: Unique session identifier
            context: Playwright browser context
            page: Primary page for this session
        """
        self.session_id = session_id
        self.context = context
        self.page = page
        self.created_at = time.time()
        self.last_activity = self.created_at
        self.command_count = 0
        
    def update_activity(self) -> None:
        """Update session activity timestamp."""
        self.last_activity = time.time()
        self.command_count += 1
        
    async def close(self) -> None:
        """Close the browser session and cleanup resources."""
        try:
            # Simply close the context - it will handle cleanup gracefully
            await self.context.close()
            logger.info(f"Browser session {self.session_id} closed (commands executed: {self.command_count})")
        except Exception as e:
            logger.error(f"Error closing session {self.session_id}: {e}")


class BrowserManager:
    """
    Comprehensive Browser Manager for AUX Protocol.
    
    Manages Chrome browser instances and sessions with full command execution
    capabilities. Provides robust session isolation, error handling, and
    resource management.
    """
    
    def __init__(
        self, 
        config: Optional[BrowserConfig] = None,
        headless: Optional[bool] = None,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
        user_agent: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        slow_mo_ms: Optional[int] = None
    ):
        """
        Initialize the browser manager with Chrome browser settings.
        
        Args:
            config: Browser configuration object (takes precedence)
            headless: Whether to run browser in headless mode
            viewport_width: Default viewport width in pixels
            viewport_height: Default viewport height in pixels
            user_agent: Custom user agent string
            timeout_ms: Default timeout for operations in milliseconds
            slow_mo_ms: Delay between operations for debugging
        """
        # Use provided config or get global config
        if config is None:
            full_config = get_config()
            self.config = full_config.browser
        else:
            self.config = config
            
        # Override with explicit parameters if provided
        self.headless = headless if headless is not None else self.config.headless
        self.viewport_width = viewport_width if viewport_width is not None else self.config.viewport_width
        self.viewport_height = viewport_height if viewport_height is not None else self.config.viewport_height
        self.user_agent = user_agent if user_agent is not None else self.config.user_agent
        self.timeout_ms = timeout_ms if timeout_ms is not None else self.config.timeout_ms
        self.slow_mo_ms = slow_mo_ms if slow_mo_ms is not None else self.config.slow_mo_ms
        
        # Browser instance management
        self.sessions: Dict[str, BrowserSession] = {}
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None
        self._initialized = False
        
        # Performance tracking
        self.total_commands_executed = 0
        self.startup_time: Optional[float] = None
        
        # Security and logging
        self.security_manager = SecurityManager(get_config().security)
        self.session_logger = get_session_logger()
        self.state_tracker = get_state_tracker()
        
        # Session management
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the browser manager and launch Chrome browser with optimal settings."""
        if self._initialized:
            return
            
        start_time = time.time()
        logger.info("Initializing Chrome browser manager...")
        
        try:
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Configure Chrome launch options for automation with security considerations
            from ..config import config_manager
            browser_args = config_manager.get_browser_launch_args()
            
            launch_options = {
                "headless": self.headless,
                "slow_mo": self.slow_mo_ms,
                "args": browser_args
            }
            
            # Launch Chrome browser
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            self._initialized = True
            self.startup_time = time.time() - start_time
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            logger.info(f"Chrome browser manager initialized successfully in {self.startup_time:.2f}s")
            logger.info(f"Browser security level: {self.config.disable_web_security and 'REDUCED' or 'NORMAL'}")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser manager: {e}")
            await self._cleanup_on_error()
            raise
            
    async def create_session(self, session_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new isolated browser session with optimized settings.
        
        Args:
            session_config: Optional session configuration overrides
            
        Returns:
            Session ID for the created session
        """
        if not self._initialized:
            await self.initialize()
            
        session_id = str(uuid.uuid4())
        
        try:
            # Default context options optimized for automation with security considerations
            context_options = {
                "viewport": {
                    "width": self.viewport_width,
                    "height": self.viewport_height
                },
                "ignore_https_errors": self.config.ignore_https_errors,
                "java_script_enabled": True,
                "accept_downloads": True,
            }
            
            # Add custom user agent if specified
            if self.user_agent:
                context_options["user_agent"] = self.user_agent
                
            # Override with session-specific config
            if session_config:
                context_options.update(session_config)
            
            # Create isolated browser context
            context = await self.browser.new_context(**context_options)
            
            # Set default timeouts
            context.set_default_timeout(self.timeout_ms)
            context.set_default_navigation_timeout(self.timeout_ms)
            
            # Create initial page
            page = await context.new_page()
            
            # Set up page-level configurations
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9"
            })
            
            # Create session object
            session = BrowserSession(session_id, context, page)
            self.sessions[session_id] = session
            
            # Log session creation
            if self.session_logger:
                self.session_logger.log_session_start(session_id)
            
            logger.info(f"Created browser session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise
        
    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Get a browser session by ID and update activity tracking.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Browser session or None if not found
        """
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
        
    async def close_session(self, session_id: str) -> bool:
        """
        Close a browser session and cleanup its resources.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was closed, False if not found
        """
        session = self.sessions.pop(session_id, None)
        if session:
            # Log session end
            if self.session_logger:
                self.session_logger.log_session_end(session_id)
            
            # Clean up state tracking
            self.state_tracker.cleanup_session_state(session_id)
            
            await session.close()
            return True
        return False
        
    async def list_sessions(self) -> List[str]:
        """
        Get list of active session IDs.
        
        Returns:
            List of active session IDs
        """
        return list(self.sessions.keys())
        
    async def _periodic_cleanup(self) -> None:
        """
        Periodic cleanup task for inactive sessions and resources.
        """
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                
                # Clean up inactive sessions
                cleaned = await self.cleanup_inactive_sessions(self.config.session_timeout_seconds)
                
                # Clean up security manager caches
                if hasattr(self.security_manager, 'rate_limiter'):
                    self.security_manager.rate_limiter.cleanup_old_entries()
                    
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} inactive sessions")
                    
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying
        
    # Command Execution Methods
    
    async def execute_navigate(self, command: NavigateCommand) -> Union[NavigateResponse, ErrorResponse]:
        """
        Execute navigate command with comprehensive error handling.
        
        Args:
            command: Navigate command to execute
            
        Returns:
            Navigate response or error response
        """
        start_time = time.time()
        session = await self.get_session(command.session_id)
        
        if not session:
            return create_error_response(
                command_id=command.id,
                error_message=f"Session {command.session_id} not found",
                error_code=ErrorCodes.SESSION_NOT_FOUND,
                error_type="session_error"
            )
        
        try:
            logger.info(f"Navigating to {command.url} (session: {command.session_id})")
            
            # Log command received
            if self.session_logger:
                self.session_logger.log_command_received(
                    command.session_id, command.id, "navigate",
                    {"url": str(command.url), "wait_until": command.wait_until}
                )
            
            # Set referer if provided
            extra_headers = {}
            if command.referer:
                extra_headers["Referer"] = command.referer
            
            # Navigate with specified wait condition
            wait_until = command.wait_until.value if hasattr(command.wait_until, 'value') else command.wait_until
            
            response = await session.page.goto(
                str(command.url),
                wait_until=wait_until,
                timeout=command.timeout
            )
            
            # Get final URL after potential redirects
            final_url = session.page.url
            
            # Get page title
            title = await session.page.title()
            
            # Check if redirected
            redirected = str(command.url) != final_url
            
            # Calculate load time
            load_time_ms = int((time.time() - start_time) * 1000)
            
            self.total_commands_executed += 1
            
            # Log navigation
            if self.session_logger:
                self.session_logger.log_navigation(
                    command.session_id, command.id, str(command.url),
                    final_url, load_time_ms, response.status if response else None
                )
            
            nav_response = NavigateResponse(
                id=command.id,
                timestamp=time.time(),
                url=final_url,
                title=title,
                status_code=response.status if response else None,
                redirected=redirected,
                load_time_ms=load_time_ms
            )
            
            # Log successful execution
            if self.session_logger:
                self.session_logger.log_command_executed(
                    command.session_id, command.id, "navigate",
                    load_time_ms, nav_response.model_dump()
                )
            
            return nav_response
            
        except PlaywrightTimeoutError:
            error_resp = create_error_response(
                command_id=command.id,
                error_message=f"Navigation timeout after {command.timeout}ms",
                error_code=ErrorCodes.TIMEOUT,
                error_type="timeout"
            )
            
            # Log command failure
            if self.session_logger:
                self.session_logger.log_command_failed(
                    command.session_id, command.id, "navigate",
                    error_resp.error, error_resp.error_code,
                    int((time.time() - start_time) * 1000)
                )
            
            return error_resp
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            error_resp = create_error_response(
                command_id=command.id,
                error_message=f"Navigation failed: {str(e)}",
                error_code=ErrorCodes.NAVIGATION_FAILED,
                error_type="navigation_error"
            )
            
            # Log command failure
            if self.session_logger:
                self.session_logger.log_command_failed(
                    command.session_id, command.id, "navigate",
                    error_resp.error, error_resp.error_code,
                    int((time.time() - start_time) * 1000)
                )
            
            return error_resp
    
    async def execute_click(self, command: ClickCommand) -> Union[ClickResponse, ErrorResponse]:
        """
        Execute click command with element detection and interaction.
        
        Args:
            command: Click command to execute
            
        Returns:
            Click response or error response
        """
        session = await self.get_session(command.session_id)
        
        if not session:
            return create_error_response(
                command_id=command.id,
                error_message=f"Session {command.session_id} not found",
                error_code=ErrorCodes.SESSION_NOT_FOUND,
                error_type="session_error"
            )
        
        try:
            logger.info(f"Clicking element {command.selector} (session: {command.session_id})")
            
            # Log command received
            if self.session_logger:
                self.session_logger.log_command_received(
                    command.session_id, command.id, "click",
                    {"selector": command.selector, "button": command.button}
                )
            
            # Locate element
            locator = session.page.locator(command.selector)
            
            # Check element existence
            element_count = await locator.count()
            if element_count == 0:
                return create_error_response(
                    command_id=command.id,
                    error_message=f"Element not found: {command.selector}",
                    error_code=ErrorCodes.ELEMENT_NOT_FOUND,
                    error_type="element_error"
                )
            
            # Get element information
            element = locator.first
            element_visible = await element.is_visible()
            
            if not element_visible and not command.force:
                return create_error_response(
                    command_id=command.id,
                    error_message=f"Element not visible: {command.selector}",
                    error_code=ErrorCodes.ELEMENT_NOT_VISIBLE,
                    error_type="element_error"
                )
            
            # Get element details
            element_text = await element.text_content() or ""
            element_tag = await element.evaluate("el => el.tagName.toLowerCase()")
            
            # Calculate click position
            if command.position:
                # Use relative position
                box = await element.bounding_box()
                if box:
                    click_x = int(box["x"] + box["width"] * command.position["x"])
                    click_y = int(box["y"] + box["height"] * command.position["y"])
                else:
                    click_x, click_y = 0, 0
            else:
                # Use element center
                box = await element.bounding_box()
                if box:
                    click_x = int(box["x"] + box["width"] / 2)
                    click_y = int(box["y"] + box["height"] / 2)
                else:
                    click_x, click_y = 0, 0
            
            # Perform click with specified options
            click_options = {
                "button": command.button.value if hasattr(command.button, 'value') else command.button,
                "click_count": command.click_count,
                "force": command.force,
                "timeout": command.timeout
            }
            
            if command.position and box:
                click_options["position"] = {
                    "x": box["width"] * command.position["x"],
                    "y": box["height"] * command.position["y"]
                }
            
            await element.click(**click_options)
            
            self.total_commands_executed += 1
            
            # Log interaction
            if self.session_logger:
                self.session_logger.log_interaction(
                    command.session_id, command.id, "click",
                    command.selector, True, element_text=element_text,
                    element_tag=element_tag, position={"x": click_x, "y": click_y}
                )
            
            click_response = ClickResponse(
                id=command.id,
                timestamp=time.time(),
                element_found=True,
                element_visible=element_visible,
                click_position={"x": click_x, "y": click_y},
                element_text=element_text,
                element_tag=element_tag
            )
            
            # Log successful execution
            if self.session_logger:
                self.session_logger.log_command_executed(
                    command.session_id, command.id, "click",
                    0, click_response.model_dump()
                )
            
            return click_response
            
        except PlaywrightTimeoutError:
            return create_error_response(
                command_id=command.id,
                error_message=f"Click timeout after {command.timeout}ms",
                error_code=ErrorCodes.TIMEOUT,
                error_type="timeout"
            )
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return create_error_response(
                command_id=command.id,
                error_message=f"Click failed: {str(e)}",
                error_code=ErrorCodes.ELEMENT_NOT_INTERACTABLE,
                error_type="interaction_error"
            )
    
    async def execute_fill(self, command: FillCommand) -> Union[FillResponse, ErrorResponse]:
        """
        Execute fill command with input validation and typing simulation.
        
        Args:
            command: Fill command to execute
            
        Returns:
            Fill response or error response
        """
        session = await self.get_session(command.session_id)
        
        if not session:
            return create_error_response(
                command_id=command.id,
                error_message=f"Session {command.session_id} not found",
                error_code=ErrorCodes.SESSION_NOT_FOUND,
                error_type="session_error"
            )
        
        try:
            logger.info(f"Filling element {command.selector} with text (session: {command.session_id})")
            
            # Locate input element
            locator = session.page.locator(command.selector)
            
            # Check element existence
            element_count = await locator.count()
            if element_count == 0:
                return create_error_response(
                    command_id=command.id,
                    error_message=f"Element not found: {command.selector}",
                    error_code=ErrorCodes.ELEMENT_NOT_FOUND,
                    error_type="element_error"
                )
            
            element = locator.first
            
            # Get previous value
            previous_value = await element.input_value() if await element.evaluate("el => el.tagName.toLowerCase()") in ["input", "textarea"] else ""
            
            # Get element type
            element_tag = await element.evaluate("el => el.tagName.toLowerCase()")
            element_type = await element.get_attribute("type") or element_tag
            
            # Clear field if requested
            if command.clear_first:
                await element.clear()
            
            # Fill with typing delay if specified
            if command.typing_delay_ms > 0:
                await element.type(command.text, delay=command.typing_delay_ms)
            else:
                await element.fill(command.text)
            
            # Press Enter if requested
            if command.press_enter:
                await element.press("Enter")
            
            # Get current value for validation
            current_value = await element.input_value() if element_tag in ["input", "textarea"] else command.text
            
            # Validate input if requested
            validation_passed = True
            if command.validate_input:
                validation_passed = current_value == command.text
            
            self.total_commands_executed += 1
            
            return FillResponse(
                id=command.id,
                timestamp=time.time(),
                element_found=True,
                element_type=element_type,
                text_entered=command.text,
                previous_value=previous_value,
                current_value=current_value,
                validation_passed=validation_passed
            )
            
        except PlaywrightTimeoutError:
            return create_error_response(
                command_id=command.id,
                error_message=f"Fill timeout after {command.timeout}ms",
                error_code=ErrorCodes.TIMEOUT,
                error_type="timeout"
            )
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return create_error_response(
                command_id=command.id,
                error_message=f"Fill failed: {str(e)}",
                error_code=ErrorCodes.ELEMENT_NOT_INTERACTABLE,
                error_type="interaction_error"
            )
    
    async def execute_extract(self, command: ExtractCommand) -> Union[ExtractResponse, ErrorResponse]:
        """
        Execute extract command with comprehensive data extraction capabilities.
        
        Args:
            command: Extract command to execute
            
        Returns:
            Extract response or error response
        """
        session = await self.get_session(command.session_id)
        
        if not session:
            return create_error_response(
                command_id=command.id,
                error_message=f"Session {command.session_id} not found",
                error_code=ErrorCodes.SESSION_NOT_FOUND,
                error_type="session_error"
            )
        
        try:
            logger.info(f"Extracting {command.extract_type} from {command.selector} (session: {command.session_id})")
            
            # Locate elements
            locator = session.page.locator(command.selector)
            element_count = await locator.count()
            
            if element_count == 0:
                return create_error_response(
                    command_id=command.id,
                    error_message=f"No elements found: {command.selector}",
                    error_code=ErrorCodes.ELEMENT_NOT_FOUND,
                    error_type="element_error"
                )
            
            # Extract data based on type
            extracted_data = []
            element_info = []
            
            # Determine how many elements to process
            elements_to_process = element_count if command.multiple else 1
            
            for i in range(elements_to_process):
                element = locator.nth(i)
                
                try:
                    if command.extract_type == ExtractType.TEXT:
                        data = await element.text_content()
                        if command.trim_whitespace and data:
                            data = data.strip()
                    
                    elif command.extract_type == ExtractType.HTML:
                        data = await element.inner_html()
                    
                    elif command.extract_type == ExtractType.ATTRIBUTE:
                        if not command.attribute_name:
                            raise ValueError("attribute_name required for attribute extraction")
                        data = await element.get_attribute(command.attribute_name)
                    
                    elif command.extract_type == ExtractType.PROPERTY:
                        if not command.property_name:
                            raise ValueError("property_name required for property extraction")
                        data = await element.evaluate(f"el => el.{command.property_name}")
                    
                    else:
                        data = await element.text_content()
                    
                    extracted_data.append(data or "")
                    
                    # Collect element metadata
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                    class_name = await element.get_attribute("class") or ""
                    
                    element_info.append({
                        "tag": tag_name,
                        "class": class_name,
                        "index": i
                    })
                    
                except Exception as e:
                    logger.warning(f"Error extracting from element {i}: {e}")
                    extracted_data.append("")
                    element_info.append({
                        "tag": "unknown",
                        "class": "",
                        "index": i,
                        "error": str(e)
                    })
            
            # Format response data
            if command.multiple:
                response_data = extracted_data
            else:
                response_data = extracted_data[0] if extracted_data else ""
            
            self.total_commands_executed += 1
            
            return ExtractResponse(
                id=command.id,
                timestamp=time.time(),
                elements_found=element_count,
                data=response_data,
                element_info=element_info
            )
            
        except Exception as e:
            logger.error(f"Extract failed: {e}")
            return create_error_response(
                command_id=command.id,
                error_message=f"Extract failed: {str(e)}",
                error_code=ErrorCodes.EXTRACTION_FAILED,
                error_type="extraction_error"
            )
    
    async def execute_wait(self, command: WaitCommand) -> Union[WaitResponse, ErrorResponse]:
        """
        Execute wait command with flexible condition support.
        
        Args:
            command: Wait command to execute
            
        Returns:
            Wait response or error response
        """
        session = await self.get_session(command.session_id)
        
        if not session:
            return create_error_response(
                command_id=command.id,
                error_message=f"Session {command.session_id} not found",
                error_code=ErrorCodes.SESSION_NOT_FOUND,
                error_type="session_error"
            )
        
        start_time = time.time()
        
        try:
            logger.info(f"Waiting for condition {command.condition} (session: {command.session_id})")
            
            condition_met = False
            element_count = 0
            final_state = "unknown"
            
            if command.condition == WaitCondition.LOAD:
                await session.page.wait_for_load_state("load", timeout=command.timeout)
                condition_met = True
                final_state = "page_loaded"
                
            elif command.condition == WaitCondition.DOMCONTENTLOADED:
                await session.page.wait_for_load_state("domcontentloaded", timeout=command.timeout)
                condition_met = True
                final_state = "dom_content_loaded"
                
            elif command.condition == WaitCondition.NETWORKIDLE:
                await session.page.wait_for_load_state("networkidle", timeout=command.timeout)
                condition_met = True
                final_state = "network_idle"
                
            elif command.condition == WaitCondition.VISIBLE:
                if not command.selector:
                    raise ValueError("selector required for visibility condition")
                
                locator = session.page.locator(command.selector)
                await locator.wait_for(state="visible", timeout=command.timeout)
                element_count = await locator.count()
                condition_met = True
                final_state = "element_visible"
                
            elif command.condition == WaitCondition.HIDDEN:
                if not command.selector:
                    raise ValueError("selector required for hidden condition")
                
                locator = session.page.locator(command.selector)
                await locator.wait_for(state="hidden", timeout=command.timeout)
                element_count = await locator.count()
                condition_met = True
                final_state = "element_hidden"
                
            elif command.condition == WaitCondition.ATTACHED:
                if not command.selector:
                    raise ValueError("selector required for attached condition")
                
                locator = session.page.locator(command.selector)
                await locator.wait_for(state="attached", timeout=command.timeout)
                element_count = await locator.count()
                condition_met = True
                final_state = "element_attached"
                
            elif command.condition == WaitCondition.DETACHED:
                if not command.selector:
                    raise ValueError("selector required for detached condition")
                
                locator = session.page.locator(command.selector)
                await locator.wait_for(state="detached", timeout=command.timeout)
                element_count = 0
                condition_met = True
                final_state = "element_detached"
            
            # Handle custom JavaScript condition
            if command.custom_js:
                await session.page.wait_for_function(
                    command.custom_js,
                    timeout=command.timeout,
                    polling=command.poll_interval_ms
                )
                condition_met = True
                final_state = "custom_condition_met"
            
            # Handle text content waiting
            if command.text_content and command.selector:
                locator = session.page.locator(command.selector)
                # Use wait_for_function to check text content
                await session.page.wait_for_function(
                    f"() => document.querySelector('{command.selector}')?.textContent?.includes('{command.text_content}')",
                    timeout=command.timeout
                )
                element_count = await locator.count()
                condition_met = True
                final_state = "text_content_found"
            
            wait_time_ms = int((time.time() - start_time) * 1000)
            
            self.total_commands_executed += 1
            
            return WaitResponse(
                id=command.id,
                timestamp=time.time(),
                condition_met=condition_met,
                wait_time_ms=wait_time_ms,
                final_state=final_state,
                element_count=element_count if element_count > 0 else None,
                condition_details={
                    "condition": command.condition,
                    "selector": command.selector,
                    "timeout": command.timeout
                }
            )
            
        except PlaywrightTimeoutError:
            wait_time_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                command_id=command.id,
                error_message=f"Wait condition timeout after {command.timeout}ms",
                error_code=ErrorCodes.WAIT_TIMEOUT,
                error_type="timeout",
                details={
                    "condition": command.condition,
                    "wait_time_ms": wait_time_ms
                }
            )
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return create_error_response(
                command_id=command.id,
                error_message=f"Wait failed: {str(e)}",
                error_code=ErrorCodes.UNKNOWN_ERROR,
                error_type="wait_error"
            )
    
    async def cleanup_inactive_sessions(self, timeout: float = 3600) -> int:
        """
        Cleanup sessions that have been inactive for too long.
        
        Args:
            timeout: Inactivity timeout in seconds
            
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > timeout:
                inactive_sessions.append(session_id)
                
        cleanup_count = 0
        for session_id in inactive_sessions:
            if await self.close_session(session_id):
                cleanup_count += 1
                
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} inactive sessions")
            
        return cleanup_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get browser manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "initialized": self._initialized,
            "startup_time_seconds": self.startup_time,
            "active_sessions": len(self.sessions),
            "total_commands_executed": self.total_commands_executed,
            "session_details": [
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "command_count": session.command_count
                }
                for session in self.sessions.values()
            ]
        }
        
    async def _cleanup_on_error(self) -> None:
        """Cleanup resources when initialization fails."""
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
        self._initialized = False
        
    async def close(self) -> None:
        """Close all sessions and cleanup browser resources."""
        logger.info("Closing browser manager...")
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all active sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
            
        # Close browser
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            
        # Stop playwright
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")
            
        self._initialized = False
        logger.info(f"Browser manager closed. Total commands executed: {self.total_commands_executed}")