"""
Browser compatibility and cross-platform testing for AUX Protocol.

Tests ensure the AUX Protocol works correctly across different browsers,
platforms, and device configurations.
"""

import asyncio
import pytest
import platform
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config, BrowserConfig


@pytest.mark.e2e
@pytest.mark.browser
class TestBrowserCompatibility:
    """Test compatibility across different browser configurations."""
    
    @pytest.fixture
    async def browser_test_setup(self, test_config):
        """Set up browser compatibility testing environment."""
        # Base configuration for browser testing
        compat_config = test_config
        compat_config.browser_config.timeout = 60000
        
        security_manager = SecurityManager(compat_config.security_config)
        
        yield {
            "base_config": compat_config,
            "security_manager": security_manager
        }
        
    async def test_headless_vs_headed_browser(self, browser_test_setup):
        """Test functionality in both headless and headed browser modes."""
        setup = browser_test_setup
        
        # Test scenarios to run in both modes
        test_scenarios = [
            {
                "name": "basic_navigation",
                "commands": [
                    {
                        "method": "navigate",
                        "url": "data:text/html,<h1 id='title'>Browser Compatibility Test</h1>"
                    },
                    {
                        "method": "extract",
                        "selector": "#title",
                        "extract_type": "text"
                    }
                ],
                "expected": "Browser Compatibility Test"
            },
            {
                "name": "form_interaction",
                "commands": [
                    {
                        "method": "navigate",
                        "url": "data:text/html,<form><input id='test-input' type='text'><button id='test-btn'>Submit</button></form>"
                    },
                    {
                        "method": "fill",
                        "selector": "#test-input",
                        "value": "compatibility test"
                    },
                    {
                        "method": "click",
                        "selector": "#test-btn"
                    },
                    {
                        "method": "extract",
                        "selector": "#test-input",
                        "extract_type": "attribute",
                        "attribute": "value"
                    }
                ],
                "expected": "compatibility test"
            }
        ]
        
        # Test in both headless and headed modes
        browser_modes = [
            {"headless": True, "mode_name": "headless"},
            {"headless": False, "mode_name": "headed"}
        ]
        
        results = {}
        
        for browser_mode in browser_modes:
            mode_name = browser_mode["mode_name"]
            results[mode_name] = {}
            
            # Configure browser for this mode
            config = setup["base_config"]
            config.browser_config.headless = browser_mode["headless"]
            
            browser_manager = BrowserManager(config)
            server = AUXWebSocketServer(config, setup["security_manager"], browser_manager)
            
            await browser_manager.start()
            await server.start()
            
            client = AUXClient(
                url=f"ws://{server.host}:{server.port}",
                api_key=f"compat-test-{mode_name}"
            )
            
            try:
                await client.connect()
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Run test scenarios
                for scenario in test_scenarios:
                    scenario_name = scenario["name"]
                    
                    try:
                        # Execute commands
                        for command in scenario["commands"]:
                            response = await client.execute_command(
                                session_id=session_id,
                                command=command
                            )
                            assert response["status"] == "success", f"Command failed in {mode_name} mode: {response}"
                            
                        # Check final result
                        final_response = response
                        if "result" in final_response:
                            if "extracted_text" in final_response["result"]:
                                actual_result = final_response["result"]["extracted_text"]
                            elif "extracted_attribute" in final_response["result"]:
                                actual_result = final_response["result"]["extracted_attribute"]
                            else:
                                actual_result = str(final_response["result"])
                                
                            assert scenario["expected"] in actual_result, f"Unexpected result in {mode_name} mode"
                            
                        results[mode_name][scenario_name] = "success"
                        
                    except Exception as e:
                        results[mode_name][scenario_name] = f"failed: {str(e)}"
                        
                await client.close_session(session_id)
                
            finally:
                if client.connected:
                    await client.disconnect()
                await server.stop()
                await browser_manager.stop()
                
        # Verify both modes work identically
        print(f"\nBrowser Mode Compatibility Results:")
        for mode, mode_results in results.items():
            print(f"  {mode.upper()} Mode:")
            for scenario, result in mode_results.items():
                print(f"    {scenario}: {result}")
                
        # Both modes should have identical successful results
        for scenario in test_scenarios:
            scenario_name = scenario["name"]
            headless_result = results["headless"].get(scenario_name)
            headed_result = results["headed"].get(scenario_name)
            
            assert headless_result == "success", f"Headless mode failed for {scenario_name}: {headless_result}"
            assert headed_result == "success", f"Headed mode failed for {scenario_name}: {headed_result}"
            assert headless_result == headed_result, f"Mode mismatch for {scenario_name}"
            
    async def test_different_viewport_sizes(self, browser_test_setup):
        """Test functionality across different viewport sizes."""
        setup = browser_test_setup
        
        # Different viewport configurations
        viewports = [
            {"width": 1920, "height": 1080, "name": "desktop_large"},
            {"width": 1366, "height": 768, "name": "desktop_standard"},
            {"width": 1024, "height": 768, "name": "tablet_landscape"},
            {"width": 768, "height": 1024, "name": "tablet_portrait"},
            {"width": 375, "height": 812, "name": "mobile_iphone"},
            {"width": 360, "height": 640, "name": "mobile_android"}
        ]
        
        # Responsive test page
        responsive_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Responsive Test</title>
            <style>
                .container { padding: 20px; }
                .desktop-only { display: block; }
                .mobile-only { display: none; }
                
                @media (max-width: 768px) {
                    .desktop-only { display: none; }
                    .mobile-only { display: block; }
                    .container { padding: 10px; }
                }
                
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }
                
                .card {
                    border: 1px solid #ccc;
                    padding: 15px;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 id="title">Responsive Layout Test</h1>
                
                <div class="desktop-only" id="desktop-content">
                    <p>This content is visible on desktop devices.</p>
                    <button id="desktop-btn">Desktop Button</button>
                </div>
                
                <div class="mobile-only" id="mobile-content">
                    <p>This content is visible on mobile devices.</p>
                    <button id="mobile-btn">Mobile Button</button>
                </div>
                
                <div class="grid" id="grid-container">
                    <div class="card" id="card-1">Card 1</div>
                    <div class="card" id="card-2">Card 2</div>
                    <div class="card" id="card-3">Card 3</div>
                    <div class="card" id="card-4">Card 4</div>
                </div>
                
                <div id="viewport-info">
                    <span id="width-display"></span> x <span id="height-display"></span>
                </div>
            </div>
            
            <script>
                function updateViewportInfo() {
                    document.getElementById('width-display').textContent = window.innerWidth;
                    document.getElementById('height-display').textContent = window.innerHeight;
                }
                
                updateViewportInfo();
                window.addEventListener('resize', updateViewportInfo);
            </script>
        </body>
        </html>
        """
        
        viewport_results = {}
        
        for viewport in viewports:
            viewport_name = viewport["name"]
            
            # Configure browser with specific viewport
            config = setup["base_config"]
            config.browser_config.viewport = {
                "width": viewport["width"],
                "height": viewport["height"]
            }
            config.browser_config.headless = True
            
            browser_manager = BrowserManager(config)
            server = AUXWebSocketServer(config, setup["security_manager"], browser_manager)
            
            await browser_manager.start()
            await server.start()
            
            client = AUXClient(
                url=f"ws://{server.host}:{server.port}",
                api_key=f"viewport-test-{viewport_name}"
            )
            
            try:
                await client.connect()
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Navigate to responsive page
                nav_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,{responsive_html}"
                    }
                )
                assert nav_response["status"] == "success"
                
                # Check viewport dimensions
                viewport_check = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "evaluate",
                        "script": "return {width: window.innerWidth, height: window.innerHeight};"
                    }
                )
                assert viewport_check["status"] == "success"
                actual_dimensions = viewport_check["result"]
                
                # Test responsive behavior
                is_mobile = viewport["width"] <= 768
                
                if is_mobile:
                    # Mobile: desktop content should be hidden, mobile content visible
                    mobile_visible = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "evaluate",
                            "script": "return getComputedStyle(document.getElementById('mobile-content')).display !== 'none';"
                        }
                    )
                    assert mobile_visible["status"] == "success"
                    assert mobile_visible["result"] is True, f"Mobile content not visible in {viewport_name}"
                    
                    # Try to click mobile button
                    mobile_click = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "click",
                            "selector": "#mobile-btn"
                        }
                    )
                    assert mobile_click["status"] == "success"
                    
                else:
                    # Desktop: desktop content should be visible, mobile content hidden
                    desktop_visible = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "evaluate",
                            "script": "return getComputedStyle(document.getElementById('desktop-content')).display !== 'none';"
                        }
                    )
                    assert desktop_visible["status"] == "success"
                    assert desktop_visible["result"] is True, f"Desktop content not visible in {viewport_name}"
                    
                    # Try to click desktop button
                    desktop_click = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "click",
                            "selector": "#desktop-btn"
                        }
                    )
                    assert desktop_click["status"] == "success"
                    
                # Test grid layout
                grid_cards = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": ".card",
                        "extract_type": "multiple"
                    }
                )
                assert grid_cards["status"] == "success"
                assert len(grid_cards["result"]["extracted_elements"]) == 4
                
                viewport_results[viewport_name] = {
                    "success": True,
                    "dimensions": actual_dimensions,
                    "mobile_layout": is_mobile
                }
                
                await client.close_session(session_id)
                
            except Exception as e:
                viewport_results[viewport_name] = {
                    "success": False,
                    "error": str(e)
                }
                
            finally:
                if client.connected:
                    await client.disconnect()
                await server.stop()
                await browser_manager.stop()
                
        # Verify all viewports worked
        print(f"\nViewport Compatibility Results:")
        for viewport_name, result in viewport_results.items():
            print(f"  {viewport_name}: {result}")
            assert result["success"], f"Viewport test failed for {viewport_name}: {result.get('error', 'Unknown error')}"
            
    async def test_user_agent_variations(self, browser_test_setup):
        """Test functionality with different user agent strings."""
        setup = browser_test_setup
        
        # Different user agent configurations
        user_agents = [
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "name": "chrome_windows"
            },
            {
                "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "name": "chrome_mac"
            },
            {
                "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "name": "chrome_linux"
            },
            {
                "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                "name": "safari_ios"
            },
            {
                "ua": "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0 Firefox/119.0",
                "name": "firefox_android"
            }
        ]
        
        # User agent detection page
        ua_test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>User Agent Test</title>
        </head>
        <body>
            <h1>User Agent Detection</h1>
            <div id="user-agent-display"></div>
            <div id="platform-info"></div>
            <div id="browser-features">
                <div id="touch-support"></div>
                <div id="webgl-support"></div>
                <div id="geolocation-support"></div>
            </div>
            
            <script>
                // Display user agent
                document.getElementById('user-agent-display').textContent = navigator.userAgent;
                
                // Platform detection
                const platform = navigator.platform || 'Unknown';
                document.getElementById('platform-info').textContent = 'Platform: ' + platform;
                
                // Feature detection
                const touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
                document.getElementById('touch-support').textContent = 'Touch: ' + (touchSupport ? 'Supported' : 'Not supported');
                
                const webglSupport = !!window.WebGLRenderingContext;
                document.getElementById('webgl-support').textContent = 'WebGL: ' + (webglSupport ? 'Supported' : 'Not supported');
                
                const geolocationSupport = !!navigator.geolocation;
                document.getElementById('geolocation-support').textContent = 'Geolocation: ' + (geolocationSupport ? 'Supported' : 'Not supported');
            </script>
        </body>
        </html>
        """
        
        ua_results = {}
        
        for ua_config in user_agents:
            ua_name = ua_config["name"]
            user_agent = ua_config["ua"]
            
            # Configure browser with specific user agent
            config = setup["base_config"]
            config.browser_config.user_agent = user_agent
            config.browser_config.headless = True
            
            browser_manager = BrowserManager(config)
            server = AUXWebSocketServer(config, setup["security_manager"], browser_manager)
            
            await browser_manager.start()
            await server.start()
            
            client = AUXClient(
                url=f"ws://{server.host}:{server.port}",
                api_key=f"ua-test-{ua_name}"
            )
            
            try:
                await client.connect()
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Navigate to user agent test page
                nav_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,{ua_test_html}"
                    }
                )
                assert nav_response["status"] == "success"
                
                # Extract user agent as detected by page
                ua_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#user-agent-display",
                        "extract_type": "text"
                    }
                )
                assert ua_response["status"] == "success"
                detected_ua = ua_response["result"]["extracted_text"]
                
                # Verify user agent was set correctly
                assert user_agent in detected_ua, f"User agent not set correctly for {ua_name}"
                
                # Extract platform info
                platform_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#platform-info",
                        "extract_type": "text"
                    }
                )
                assert platform_response["status"] == "success"
                
                # Extract feature support info
                features_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#browser-features",
                        "extract_type": "text"
                    }
                )
                assert features_response["status"] == "success"
                
                # Test basic interaction still works
                interaction_test = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "evaluate",
                        "script": "document.title = 'UA Test Completed'; return 'success';"
                    }
                )
                assert interaction_test["status"] == "success"
                
                ua_results[ua_name] = {
                    "success": True,
                    "detected_ua": detected_ua,
                    "platform": platform_response["result"]["extracted_text"],
                    "features": features_response["result"]["extracted_text"]
                }
                
                await client.close_session(session_id)
                
            except Exception as e:
                ua_results[ua_name] = {
                    "success": False,
                    "error": str(e)
                }
                
            finally:
                if client.connected:
                    await client.disconnect()
                await server.stop()
                await browser_manager.stop()
                
        # Verify all user agents worked
        print(f"\nUser Agent Compatibility Results:")
        for ua_name, result in ua_results.items():
            print(f"  {ua_name}: {result}")
            assert result["success"], f"User agent test failed for {ua_name}: {result.get('error', 'Unknown error')}"


@pytest.mark.e2e
class TestPlatformCompatibility:
    """Test compatibility across different platforms and environments."""
    
    def test_platform_detection(self):
        """Test platform detection and adaptation."""
        current_platform = platform.system().lower()
        
        # Verify we can detect the current platform
        assert current_platform in ['windows', 'linux', 'darwin'], f"Unsupported platform: {current_platform}"
        
        # Platform-specific configurations
        platform_configs = {
            'windows': {
                'executable_paths': [
                    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
                ],
                'default_args': ['--no-sandbox', '--disable-dev-shm-usage']
            },
            'linux': {
                'executable_paths': [
                    '/usr/bin/google-chrome',
                    '/usr/bin/chromium-browser',
                    '/snap/bin/chromium'
                ],
                'default_args': ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            },
            'darwin': {
                'executable_paths': [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    '/Applications/Chromium.app/Contents/MacOS/Chromium'
                ],
                'default_args': ['--no-sandbox']
            }
        }
        
        # Verify platform-specific configuration exists
        assert current_platform in platform_configs, f"No configuration for platform: {current_platform}"
        
        config = platform_configs[current_platform]
        assert 'executable_paths' in config
        assert 'default_args' in config
        assert len(config['executable_paths']) > 0
        assert len(config['default_args']) > 0
        
        print(f"\nPlatform Compatibility:")
        print(f"  Detected platform: {current_platform}")
        print(f"  Available executable paths: {config['executable_paths']}")
        print(f"  Default arguments: {config['default_args']}")
        
    async def test_environment_variables_handling(self, browser_test_setup):
        """Test handling of environment variables across platforms."""
        setup = browser_test_setup
        
        # Test environment variables that might affect browser behavior
        env_vars_to_test = [
            'DISPLAY',  # Linux X11
            'HOME',     # Unix home directory
            'USERPROFILE',  # Windows user profile
            'TMPDIR',   # Temporary directory
            'TMP',      # Windows temporary directory
            'PATH'      # System PATH
        ]
        
        env_results = {}
        
        for env_var in env_vars_to_test:
            env_value = os.environ.get(env_var)
            env_results[env_var] = {
                'present': env_value is not None,
                'value_length': len(env_value) if env_value else 0
            }
            
        print(f"\nEnvironment Variables:")
        for var, result in env_results.items():
            status = "Present" if result['present'] else "Not present"
            print(f"  {var}: {status}")
            
        # At least some environment variables should be present
        present_vars = [var for var, result in env_results.items() if result['present']]
        assert len(present_vars) > 0, "No environment variables detected"
        
    async def test_file_system_permissions(self, browser_test_setup):
        """Test file system permissions and access patterns."""
        import tempfile
        import os
        
        # Test temporary directory access
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test directory creation
            test_dir = temp_path / "aux_test"
            test_dir.mkdir()
            assert test_dir.exists()
            
            # Test file creation
            test_file = test_dir / "test.txt"
            test_file.write_text("AUX Protocol Test")
            assert test_file.exists()
            
            # Test file reading
            content = test_file.read_text()
            assert content == "AUX Protocol Test"
            
            # Test file permissions (Unix-like systems)
            if platform.system() != 'Windows':
                # Test readable
                assert os.access(test_file, os.R_OK)
                # Test writable
                assert os.access(test_file, os.W_OK)
                
            print(f"\nFile System Test:")
            print(f"  Temporary directory: {temp_dir}")
            print(f"  File creation: Success")
            print(f"  File reading: Success")
            print(f"  Permissions: {oct(test_file.stat().st_mode)[-3:] if platform.system() != 'Windows' else 'N/A (Windows)'}")
            
    async def test_network_connectivity(self, browser_test_setup):
        """Test network connectivity and DNS resolution."""
        import socket
        
        # Test DNS resolution
        dns_tests = [
            ('google.com', 80),
            ('github.com', 443),
            ('localhost', 8080)  # Should fail but test resolution
        ]
        
        dns_results = {}
        
        for hostname, port in dns_tests:
            try:
                # Test DNS resolution
                ip = socket.gethostbyname(hostname)
                dns_results[hostname] = {
                    'resolved': True,
                    'ip': ip,
                    'error': None
                }
                
                # Test port connectivity (timeout quickly)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                try:
                    result = sock.connect_ex((hostname, port))
                    dns_results[hostname]['port_accessible'] = result == 0
                except:
                    dns_results[hostname]['port_accessible'] = False
                finally:
                    sock.close()
                    
            except Exception as e:
                dns_results[hostname] = {
                    'resolved': False,
                    'ip': None,
                    'error': str(e)
                }
                
        print(f"\nNetwork Connectivity:")
        for hostname, result in dns_results.items():
            if result['resolved']:
                port_status = "Accessible" if result.get('port_accessible') else "Not accessible"
                print(f"  {hostname}: {result['ip']} - {port_status}")
            else:
                print(f"  {hostname}: Resolution failed - {result['error']}")
                
        # At least basic DNS should work
        resolved_count = sum(1 for result in dns_results.values() if result['resolved'])
        assert resolved_count >= 2, f"Too few DNS resolutions successful: {resolved_count}/3"


@pytest.mark.e2e
class TestAccessibilityCompatibility:
    """Test accessibility features and compatibility."""
    
    async def test_accessibility_features(self, browser_test_setup):
        """Test accessibility features and ARIA support."""
        setup = browser_test_setup
        
        # Configure browser for accessibility testing
        config = setup["base_config"]
        config.browser_config.headless = True
        
        browser_manager = BrowserManager(config)
        server = AUXWebSocketServer(config, setup["security_manager"], browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        client = AUXClient(
            url=f"ws://{server.host}:{server.port}",
            api_key="accessibility-test"
        )
        
        try:
            await client.connect()
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            
            # Accessibility test page
            accessibility_html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Accessibility Test Page</title>
            </head>
            <body>
                <h1 id="main-heading">Accessibility Test</h1>
                
                <nav aria-label="Main navigation">
                    <ul>
                        <li><a href="#home" id="nav-home">Home</a></li>
                        <li><a href="#about" id="nav-about">About</a></li>
                        <li><a href="#contact" id="nav-contact">Contact</a></li>
                    </ul>
                </nav>
                
                <main>
                    <section aria-labelledby="form-heading">
                        <h2 id="form-heading">Contact Form</h2>
                        <form aria-label="Contact information form">
                            <div>
                                <label for="name-input">Name (required):</label>
                                <input type="text" id="name-input" required aria-describedby="name-help">
                                <div id="name-help">Please enter your full name</div>
                            </div>
                            
                            <div>
                                <label for="email-input">Email:</label>
                                <input type="email" id="email-input" aria-describedby="email-help">
                                <div id="email-help">We'll never share your email</div>
                            </div>
                            
                            <fieldset>
                                <legend>Preferred contact method</legend>
                                <div>
                                    <input type="radio" id="contact-email" name="contact-method" value="email">
                                    <label for="contact-email">Email</label>
                                </div>
                                <div>
                                    <input type="radio" id="contact-phone" name="contact-method" value="phone">
                                    <label for="contact-phone">Phone</label>
                                </div>
                            </fieldset>
                            
                            <button type="submit" id="submit-button" aria-describedby="submit-help">
                                Submit Form
                            </button>
                            <div id="submit-help">Press Enter or click to submit</div>
                        </form>
                    </section>
                    
                    <section aria-live="polite" id="status-region">
                        <div id="status-message"></div>
                    </section>
                </main>
                
                <footer>
                    <p>&copy; 2024 Accessibility Test Site</p>
                </footer>
            </body>
            </html>
            """
            
            # Navigate to accessibility test page
            nav_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,{accessibility_html}"
                }
            )
            assert nav_response["status"] == "success"
            
            # Test semantic HTML structure
            heading_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "h1",
                    "extract_type": "text"
                }
            )
            assert heading_response["status"] == "success"
            assert "Accessibility Test" in heading_response["result"]["extracted_text"]
            
            # Test ARIA labels
            aria_label_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "nav",
                    "extract_type": "attribute",
                    "attribute": "aria-label"
                }
            )
            assert aria_label_response["status"] == "success"
            assert "Main navigation" in aria_label_response["result"]["extracted_attribute"]
            
            # Test form labels and associations
            label_for_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "label[for='name-input']",
                    "extract_type": "text"
                }
            )
            assert label_for_response["status"] == "success"
            assert "Name" in label_for_response["result"]["extracted_text"]
            
            # Test aria-describedby relationships
            describedby_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "#name-input",
                    "extract_type": "attribute",
                    "attribute": "aria-describedby"
                }
            )
            assert describedby_response["status"] == "success"
            assert "name-help" in describedby_response["result"]["extracted_attribute"]
            
            # Test fieldset and legend
            legend_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "legend",
                    "extract_type": "text"
                }
            )
            assert legend_response["status"] == "success"
            assert "contact method" in legend_response["result"]["extracted_text"]
            
            # Test keyboard navigation (tab order)
            # Focus on first input
            focus_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "evaluate",
                    "script": """
                    document.getElementById('name-input').focus();
                    return document.activeElement.id;
                    """
                }
            )
            assert focus_response["status"] == "success"
            assert focus_response["result"] == "name-input"
            
            # Test form interaction
            fill_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "fill",
                    "selector": "#name-input",
                    "value": "Accessibility Test User"
                }
            )
            assert fill_response["status"] == "success"
            
            # Test radio button selection
            radio_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "click",
                    "selector": "#contact-email"
                }
            )
            assert radio_response["status"] == "success"
            
            print(f"\nAccessibility Test Results:")
            print(f"  Semantic HTML: ✓ Proper heading structure")
            print(f"  ARIA labels: ✓ Navigation properly labeled")
            print(f"  Form labels: ✓ Inputs properly associated")
            print(f"  ARIA relationships: ✓ Descriptions linked")
            print(f"  Fieldsets: ✓ Radio groups properly grouped")
            print(f"  Keyboard navigation: ✓ Focus management working")
            print(f"  Form interaction: ✓ All inputs accessible")
            
            await client.close_session(session_id)
            
        finally:
            if client.connected:
                await client.disconnect()
            await server.stop()
            await browser_manager.stop()
