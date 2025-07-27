"""
Comprehensive end-to-end tests for real-world AUX Protocol scenarios.

Tests cover complete user workflows, browser automation scenarios,
and real-world usage patterns with actual web pages and interactions.
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.e2e
@pytest.mark.browser
class TestWebAutomationScenarios:
    """Test real web automation scenarios."""
    
    @pytest.fixture
    async def e2e_setup(self, test_config, test_websites):
        """Set up end-to-end testing environment."""
        # Configure for real browser automation
        e2e_config = test_config
        e2e_config.browser_config.headless = False  # Use headed browser for E2E
        e2e_config.browser_config.timeout = 60000
        
        security_manager = SecurityManager(e2e_config.security_config)
        browser_manager = BrowserManager(e2e_config)
        server = AUXWebSocketServer(e2e_config, security_manager, browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        client = AUXClient(
            url=f"ws://{server.host}:{server.port}",
            api_key="e2e-test-key"
        )
        
        yield {
            "server": server,
            "client": client,
            "browser_manager": browser_manager,
            "config": e2e_config,
            "test_websites": test_websites
        }
        
        if client.connected:
            await client.disconnect()
        await server.stop()
        await browser_manager.stop()
        
    async def test_complete_form_submission_workflow(self, e2e_setup):
        """Test complete form submission workflow."""
        setup = e2e_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create a comprehensive form page
        form_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Contact Form Test</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input, textarea, select { width: 300px; padding: 8px; }
                button { padding: 10px 20px; background: #007cba; color: white; border: none; cursor: pointer; }
                .success { color: green; margin-top: 20px; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>Contact Form</h1>
            <form id="contact-form">
                <div class="form-group">
                    <label for="firstName">First Name *</label>
                    <input type="text" id="firstName" name="firstName" required>
                </div>
                <div class="form-group">
                    <label for="lastName">Last Name *</label>
                    <input type="text" id="lastName" name="lastName" required>
                </div>
                <div class="form-group">
                    <label for="email">Email *</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="phone">Phone</label>
                    <input type="tel" id="phone" name="phone">
                </div>
                <div class="form-group">
                    <label for="country">Country</label>
                    <select id="country" name="country">
                        <option value="">Select Country</option>
                        <option value="us">United States</option>
                        <option value="ca">Canada</option>
                        <option value="uk">United Kingdom</option>
                        <option value="au">Australia</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="subject">Subject *</label>
                    <select id="subject" name="subject" required>
                        <option value="">Select Subject</option>
                        <option value="general">General Inquiry</option>
                        <option value="support">Technical Support</option>
                        <option value="sales">Sales Question</option>
                        <option value="billing">Billing Issue</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="message">Message *</label>
                    <textarea id="message" name="message" rows="5" required></textarea>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="newsletter" name="newsletter" value="yes">
                        Subscribe to newsletter
                    </label>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="terms" name="terms" value="yes" required>
                        I agree to the terms and conditions *
                    </label>
                </div>
                <button type="submit" id="submit-btn">Submit Form</button>
            </form>
            <div id="result" class="success" style="display:none;">Thank you! Your form has been submitted successfully.</div>
            <div id="error" class="error" style="display:none;">Please fill in all required fields.</div>
            
            <script>
                document.getElementById('contact-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    // Simple validation
                    const required = ['firstName', 'lastName', 'email', 'subject', 'message', 'terms'];
                    let valid = true;
                    
                    for (let field of required) {
                        const element = document.getElementById(field);
                        if (!element.value || (element.type === 'checkbox' && !element.checked)) {
                            valid = false;
                            break;
                        }
                    }
                    
                    if (valid) {
                        document.getElementById('result').style.display = 'block';
                        document.getElementById('error').style.display = 'none';
                        document.getElementById('submit-btn').textContent = 'Form Submitted!';
                        document.getElementById('submit-btn').disabled = true;
                    } else {
                        document.getElementById('error').style.display = 'block';
                        document.getElementById('result').style.display = 'none';
                    }
                });
            </script>
        </body>
        </html>
        """
        
        # Navigate to form page
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{form_html}"
            }
        )
        assert nav_response["status"] == "success"
        
        # Wait for page to load
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#contact-form"
            }
        )
        
        # Fill out the form step by step
        form_data = {
            "#firstName": "John",
            "#lastName": "Doe",
            "#email": "john.doe@example.com",
            "#phone": "+1-555-123-4567",
            "#message": "This is a test message for the contact form. I am testing the AUX Protocol automation capabilities with a comprehensive form submission workflow."
        }
        
        # Fill text inputs
        for selector, value in form_data.items():
            fill_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "fill",
                    "selector": selector,
                    "value": value,
                    "clear_first": True
                }
            )
            assert fill_response["status"] == "success", f"Failed to fill {selector}"
            
        # Select country
        country_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "select",
                "selector": "#country",
                "value": "us"
            }
        )
        assert country_response["status"] == "success"
        
        # Select subject
        subject_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "select",
                "selector": "#subject",
                "value": "support"
            }
        )
        assert subject_response["status"] == "success"
        
        # Check newsletter checkbox
        newsletter_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#newsletter"
            }
        )
        assert newsletter_response["status"] == "success"
        
        # Check terms checkbox (required)
        terms_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#terms"
            }
        )
        assert terms_response["status"] == "success"
        
        # Verify form is filled correctly before submission
        verification_fields = [
            ("#firstName", "John"),
            ("#lastName", "Doe"),
            ("#email", "john.doe@example.com")
        ]
        
        for selector, expected_value in verification_fields:
            verify_response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": selector,
                    "extract_type": "attribute",
                    "attribute": "value"
                }
            )
            assert verify_response["status"] == "success"
            actual_value = verify_response["result"]["extracted_attribute"]
            assert actual_value == expected_value, f"Field {selector} has incorrect value: {actual_value}"
            
        # Submit the form
        submit_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#submit-btn"
            }
        )
        assert submit_response["status"] == "success"
        
        # Wait for success message
        success_wait_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#result",
                "timeout": 10000
            }
        )
        assert success_wait_response["status"] == "success"
        
        # Verify success message
        success_message_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#result",
                "extract_type": "text"
            }
        )
        assert success_message_response["status"] == "success"
        success_text = success_message_response["result"]["extracted_text"]
        assert "Thank you" in success_text
        assert "submitted successfully" in success_text
        
        # Verify button state changed
        button_text_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#submit-btn",
                "extract_type": "text"
            }
        )
        assert button_text_response["status"] == "success"
        button_text = button_text_response["result"]["extracted_text"]
        assert "Form Submitted!" in button_text
        
        await client.close_session(session_id)
        
    async def test_multi_page_navigation_workflow(self, e2e_setup):
        """Test multi-page navigation and data persistence."""
        setup = e2e_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create a multi-page application
        pages = {
            "home": """
            <!DOCTYPE html>
            <html>
            <head><title>Home Page</title></head>
            <body>
                <h1>Welcome to Our Site</h1>
                <nav>
                    <a href="#about" id="about-link">About Us</a>
                    <a href="#contact" id="contact-link">Contact</a>
                    <a href="#products" id="products-link">Products</a>
                </nav>
                <div id="content">
                    <p>This is the home page content.</p>
                    <button id="get-started">Get Started</button>
                </div>
                <script>
                    let currentPage = 'home';
                    
                    function navigate(page) {
                        currentPage = page;
                        updateContent(page);
                        window.history.pushState({page: page}, '', '#' + page);
                    }
                    
                    function updateContent(page) {
                        const content = document.getElementById('content');
                        switch(page) {
                            case 'about':
                                content.innerHTML = '<h2>About Us</h2><p>We are a technology company focused on browser automation.</p><button id="back-home">Back to Home</button>';
                                break;
                            case 'contact':
                                content.innerHTML = '<h2>Contact Us</h2><form id="contact-form"><input type="email" id="email" placeholder="Your email"><button type="submit">Submit</button></form>';
                                break;
                            case 'products':
                                content.innerHTML = '<h2>Our Products</h2><ul><li>AUX Protocol</li><li>Browser Automation</li><li>Testing Suite</li></ul><button id="learn-more">Learn More</button>';
                                break;
                            default:
                                content.innerHTML = '<p>This is the home page content.</p><button id="get-started">Get Started</button>';
                        }
                    }
                    
                    document.addEventListener('click', function(e) {
                        if (e.target.id === 'about-link') {
                            e.preventDefault();
                            navigate('about');
                        } else if (e.target.id === 'contact-link') {
                            e.preventDefault();
                            navigate('contact');
                        } else if (e.target.id === 'products-link') {
                            e.preventDefault();
                            navigate('products');
                        } else if (e.target.id === 'back-home') {
                            navigate('home');
                        } else if (e.target.id === 'get-started') {
                            navigate('products');
                        }
                    });
                    
                    // Handle form submission
                    document.addEventListener('submit', function(e) {
                        if (e.target.id === 'contact-form') {
                            e.preventDefault();
                            const email = document.getElementById('email').value;
                            if (email) {
                                document.getElementById('content').innerHTML = '<h2>Thank You!</h2><p>We will contact you at ' + email + '</p><button id="back-home">Back to Home</button>';
                            }
                        }
                    });
                </script>
            </body>
            </html>
            """
        }
        
        # Navigate to the multi-page application
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{pages['home']}"
            }
        )
        assert nav_response["status"] == "success"
        
        # Verify home page loaded
        home_title_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "h1",
                "extract_type": "text"
            }
        )
        assert home_title_response["status"] == "success"
        assert "Welcome to Our Site" in home_title_response["result"]["extracted_text"]
        
        # Navigate to About page
        about_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#about-link"
            }
        )
        assert about_response["status"] == "success"
        
        # Wait for content to update
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#back-home"
            }
        )
        
        # Verify About page content
        about_content_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content h2",
                "extract_type": "text"
            }
        )
        assert about_content_response["status"] == "success"
        assert "About Us" in about_content_response["result"]["extracted_text"]
        
        # Navigate to Products page via Get Started button from home
        home_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#back-home"
            }
        )
        assert home_response["status"] == "success"
        
        # Click Get Started to go to products
        products_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#get-started"
            }
        )
        assert products_response["status"] == "success"
        
        # Verify Products page
        products_title_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content h2",
                "extract_type": "text"
            }
        )
        assert products_title_response["status"] == "success"
        assert "Our Products" in products_title_response["result"]["extracted_text"]
        
        # Navigate to Contact page
        contact_nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#contact-link"
            }
        )
        assert contact_nav_response["status"] == "success"
        
        # Fill and submit contact form
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#contact-form"
            }
        )
        
        email_fill_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#email",
                "value": "test@example.com"
            }
        )
        assert email_fill_response["status"] == "success"
        
        form_submit_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#contact-form button"
            }
        )
        assert form_submit_response["status"] == "success"
        
        # Verify thank you message
        thank_you_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content h2",
                "extract_type": "text"
            }
        )
        assert thank_you_response["status"] == "success"
        assert "Thank You" in thank_you_response["result"]["extracted_text"]
        
        await client.close_session(session_id)
        
    async def test_dynamic_content_interaction(self, e2e_setup):
        """Test interaction with dynamic content and JavaScript."""
        setup = e2e_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create a dynamic content page
        dynamic_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dynamic Content Test</title>
            <style>
                .hidden { display: none; }
                .loading { color: #999; }
                .content { margin: 20px 0; }
                .item { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
                .selected { background-color: #e6f3ff; }
            </style>
        </head>
        <body>
            <h1>Dynamic Content Demo</h1>
            
            <div id="controls">
                <button id="load-data">Load Data</button>
                <button id="add-item">Add Item</button>
                <button id="clear-all">Clear All</button>
                <input type="text" id="search" placeholder="Search items...">
            </div>
            
            <div id="status">Ready</div>
            <div id="content" class="content"></div>
            
            <script>
                let items = [];
                let nextId = 1;
                
                function updateStatus(message) {
                    document.getElementById('status').textContent = message;
                }
                
                function renderItems(filter = '') {
                    const content = document.getElementById('content');
                    const filteredItems = items.filter(item => 
                        item.title.toLowerCase().includes(filter.toLowerCase()) ||
                        item.description.toLowerCase().includes(filter.toLowerCase())
                    );
                    
                    if (filteredItems.length === 0) {
                        content.innerHTML = '<p>No items to display.</p>';
                        return;
                    }
                    
                    content.innerHTML = filteredItems.map(item => `
                        <div class="item" data-id="${item.id}">
                            <h3>${item.title}</h3>
                            <p>${item.description}</p>
                            <button onclick="selectItem(${item.id})">Select</button>
                            <button onclick="deleteItem(${item.id})">Delete</button>
                        </div>
                    `).join('');
                }
                
                function loadData() {
                    updateStatus('Loading data...');
                    
                    // Simulate API call
                    setTimeout(() => {
                        items = [
                            { id: nextId++, title: 'First Item', description: 'This is the first dynamically loaded item.' },
                            { id: nextId++, title: 'Second Item', description: 'This is the second dynamically loaded item.' },
                            { id: nextId++, title: 'Third Item', description: 'This is the third dynamically loaded item.' }
                        ];
                        renderItems();
                        updateStatus(`Loaded ${items.length} items`);
                    }, 1000);
                }
                
                function addItem() {
                    const newItem = {
                        id: nextId++,
                        title: `Item ${nextId - 1}`,
                        description: `This is item number ${nextId - 1} added dynamically.`
                    };
                    items.push(newItem);
                    renderItems();
                    updateStatus(`Added item ${newItem.id}. Total: ${items.length} items`);
                }
                
                function clearAll() {
                    items = [];
                    renderItems();
                    updateStatus('All items cleared');
                }
                
                function selectItem(id) {
                    // Remove previous selections
                    document.querySelectorAll('.item').forEach(item => {
                        item.classList.remove('selected');
                    });
                    
                    // Select current item
                    const item = document.querySelector(`[data-id="${id}"]`);
                    if (item) {
                        item.classList.add('selected');
                        updateStatus(`Selected item ${id}`);
                    }
                }
                
                function deleteItem(id) {
                    items = items.filter(item => item.id !== id);
                    renderItems();
                    updateStatus(`Deleted item ${id}. Remaining: ${items.length} items`);
                }
                
                // Event listeners
                document.getElementById('load-data').addEventListener('click', loadData);
                document.getElementById('add-item').addEventListener('click', addItem);
                document.getElementById('clear-all').addEventListener('click', clearAll);
                document.getElementById('search').addEventListener('input', function(e) {
                    renderItems(e.target.value);
                });
            </script>
        </body>
        </html>
        """
        
        # Navigate to dynamic content page
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{dynamic_html}"
            }
        )
        assert nav_response["status"] == "success"
        
        # Wait for page to load
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#load-data"
            }
        )
        
        # Load initial data
        load_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#load-data"
            }
        )
        assert load_response["status"] == "success"
        
        # Wait for data to load (simulated delay)
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": ".item",
                "timeout": 5000
            }
        )
        
        # Verify items were loaded
        items_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": ".item",
                "extract_type": "multiple"
            }
        )
        assert items_response["status"] == "success"
        items_count = len(items_response["result"]["extracted_elements"])
        assert items_count == 3, f"Expected 3 items, found {items_count}"
        
        # Add a new item
        add_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#add-item"
            }
        )
        assert add_response["status"] == "success"
        
        # Verify new item was added
        await asyncio.sleep(0.5)  # Brief wait for DOM update
        new_items_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": ".item",
                "extract_type": "multiple"
            }
        )
        assert new_items_response["status"] == "success"
        new_items_count = len(new_items_response["result"]["extracted_elements"])
        assert new_items_count == 4, f"Expected 4 items after adding, found {new_items_count}"
        
        # Test item selection
        select_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": ".item:first-child button:first-of-type"  # Select first item
            }
        )
        assert select_response["status"] == "success"
        
        # Verify item was selected
        await asyncio.sleep(0.5)
        selected_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": ".item.selected",
                "extract_type": "text"
            }
        )
        assert selected_response["status"] == "success"
        assert "First Item" in selected_response["result"]["extracted_text"]
        
        # Test search functionality
        search_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#search",
                "value": "second"
            }
        )
        assert search_response["status"] == "success"
        
        # Verify search filtered results
        await asyncio.sleep(0.5)
        filtered_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": ".item",
                "extract_type": "multiple"
            }
        )
        assert filtered_response["status"] == "success"
        filtered_count = len(filtered_response["result"]["extracted_elements"])
        assert filtered_count == 1, f"Expected 1 filtered item, found {filtered_count}"
        
        # Clear search
        clear_search_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#search",
                "value": "",
                "clear_first": True
            }
        )
        assert clear_search_response["status"] == "success"
        
        # Delete an item
        delete_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": ".item:first-child button:last-of-type"  # Delete first item
            }
        )
        assert delete_response["status"] == "success"
        
        # Verify item was deleted
        await asyncio.sleep(0.5)
        remaining_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": ".item",
                "extract_type": "multiple"
            }
        )
        assert remaining_response["status"] == "success"
        remaining_count = len(remaining_response["result"]["extracted_elements"])
        assert remaining_count == 3, f"Expected 3 items after deletion, found {remaining_count}"
        
        # Clear all items
        clear_all_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#clear-all"
            }
        )
        assert clear_all_response["status"] == "success"
        
        # Verify all items were cleared
        await asyncio.sleep(0.5)
        empty_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#content",
                "extract_type": "text"
            }
        )
        assert empty_response["status"] == "success"
        assert "No items to display" in empty_response["result"]["extracted_text"]
        
        await client.close_session(session_id)


@pytest.mark.e2e
@pytest.mark.browser
class TestAdvancedWebScenarios:
    """Test advanced web automation scenarios."""
    
    async def test_file_upload_scenario(self, e2e_setup):
        """Test file upload functionality."""
        setup = e2e_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create file upload page
        upload_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Upload Test</title>
            <style>
                .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
                .file-info { margin: 10px 0; }
                .success { color: green; }
            </style>
        </head>
        <body>
            <h1>File Upload Demo</h1>
            <form id="upload-form">
                <div class="upload-area">
                    <input type="file" id="file-input" name="file" accept=".txt,.pdf,.jpg,.png">
                    <p>Select a file to upload</p>
                </div>
                <div class="file-info">
                    <label for="description">File Description:</label>
                    <input type="text" id="description" name="description" placeholder="Enter file description">
                </div>
                <button type="submit" id="upload-btn">Upload File</button>
            </form>
            <div id="result"></div>
            
            <script>
                document.getElementById('file-input').addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (file) {
                        document.querySelector('.upload-area p').textContent = 
                            `Selected: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
                    }
                });
                
                document.getElementById('upload-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const file = document.getElementById('file-input').files[0];
                    const description = document.getElementById('description').value;
                    
                    if (file) {
                        // Simulate upload
                        document.getElementById('result').innerHTML = 
                            `<div class="success">
                                <h3>Upload Successful!</h3>
                                <p>File: ${file.name}</p>
                                <p>Size: ${(file.size / 1024).toFixed(2)} KB</p>
                                <p>Type: ${file.type}</p>
                                <p>Description: ${description || 'No description provided'}</p>
                            </div>`;
                        document.getElementById('upload-btn').textContent = 'Upload Complete';
                        document.getElementById('upload-btn').disabled = true;
                    } else {
                        document.getElementById('result').innerHTML = 
                            '<div style="color: red;">Please select a file to upload.</div>';
                    }
                });
            </script>
        </body>
        </html>
        """
        
        # Navigate to upload page
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{upload_html}"
            }
        )
        assert nav_response["status"] == "success"
        
        # Wait for file input to be available
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#file-input"
            }
        )
        
        # Create a test file (simulate file selection)
        # Note: In a real browser, this would require actual file handling
        # For this test, we'll simulate the file selection effect
        simulate_file_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "evaluate",
                "script": """
                // Simulate file selection
                const fileInput = document.getElementById('file-input');
                const file = new File(['test file content'], 'test.txt', { type: 'text/plain' });
                
                // Create a new FileList with our test file
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
                
                return 'File simulated successfully';
                """
            }
        )
        assert simulate_file_response["status"] == "success"
        
        # Add file description
        description_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#description",
                "value": "Test file for AUX Protocol E2E testing"
            }
        )
        assert description_response["status"] == "success"
        
        # Submit the upload form
        upload_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#upload-btn"
            }
        )
        assert upload_response["status"] == "success"
        
        # Wait for upload result
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#result .success"
            }
        )
        
        # Verify upload success message
        result_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#result",
                "extract_type": "text"
            }
        )
        assert result_response["status"] == "success"
        result_text = result_response["result"]["extracted_text"]
        assert "Upload Successful" in result_text
        assert "test.txt" in result_text
        assert "Test file for AUX Protocol" in result_text
        
        await client.close_session(session_id)
        
    async def test_modal_dialog_interaction(self, e2e_setup):
        """Test interaction with modal dialogs."""
        setup = e2e_setup
        client = setup["client"]
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create page with modal dialogs
        modal_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Modal Dialog Test</title>
            <style>
                .modal {
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                }
                .modal-content {
                    background-color: white;
                    margin: 15% auto;
                    padding: 20px;
                    border-radius: 5px;
                    width: 400px;
                    position: relative;
                }
                .close {
                    position: absolute;
                    right: 10px;
                    top: 10px;
                    font-size: 20px;
                    cursor: pointer;
                }
                .modal-buttons {
                    margin-top: 20px;
                    text-align: right;
                }
                .modal-buttons button {
                    margin-left: 10px;
                    padding: 8px 16px;
                }
                button {
                    padding: 10px 20px;
                    margin: 5px;
                }
            </style>
        </head>
        <body>
            <h1>Modal Dialog Demo</h1>
            
            <div>
                <button id="show-info-modal">Show Info Modal</button>
                <button id="show-confirm-modal">Show Confirm Modal</button>
                <button id="show-form-modal">Show Form Modal</button>
            </div>
            
            <div id="result"></div>
            
            <!-- Info Modal -->
            <div id="info-modal" class="modal">
                <div class="modal-content">
                    <span class="close" data-modal="info-modal">&times;</span>
                    <h2>Information</h2>
                    <p>This is an informational modal dialog. It provides important details to the user.</p>
                    <div class="modal-buttons">
                        <button id="info-ok" data-modal="info-modal">OK</button>
                    </div>
                </div>
            </div>
            
            <!-- Confirm Modal -->
            <div id="confirm-modal" class="modal">
                <div class="modal-content">
                    <span class="close" data-modal="confirm-modal">&times;</span>
                    <h2>Confirmation</h2>
                    <p>Are you sure you want to proceed with this action?</p>
                    <div class="modal-buttons">
                        <button id="confirm-cancel" data-modal="confirm-modal">Cancel</button>
                        <button id="confirm-ok" data-modal="confirm-modal">Confirm</button>
                    </div>
                </div>
            </div>
            
            <!-- Form Modal -->
            <div id="form-modal" class="modal">
                <div class="modal-content">
                    <span class="close" data-modal="form-modal">&times;</span>
                    <h2>User Information</h2>
                    <form id="modal-form">
                        <div style="margin-bottom: 15px;">
                            <label for="modal-name">Name:</label><br>
                            <input type="text" id="modal-name" style="width: 100%; padding: 5px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label for="modal-email">Email:</label><br>
                            <input type="email" id="modal-email" style="width: 100%; padding: 5px;">
                        </div>
                        <div class="modal-buttons">
                            <button type="button" id="form-cancel" data-modal="form-modal">Cancel</button>
                            <button type="submit" id="form-submit">Submit</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                function showModal(modalId) {
                    document.getElementById(modalId).style.display = 'block';
                }
                
                function hideModal(modalId) {
                    document.getElementById(modalId).style.display = 'none';
                }
                
                function updateResult(message) {
                    document.getElementById('result').innerHTML = '<p style="color: green;">' + message + '</p>';
                }
                
                // Show modal buttons
                document.getElementById('show-info-modal').addEventListener('click', () => showModal('info-modal'));
                document.getElementById('show-confirm-modal').addEventListener('click', () => showModal('confirm-modal'));
                document.getElementById('show-form-modal').addEventListener('click', () => showModal('form-modal'));
                
                // Close buttons and modal actions
                document.addEventListener('click', function(e) {
                    if (e.target.classList.contains('close') || e.target.dataset.modal) {
                        const modalId = e.target.dataset.modal;
                        if (modalId) {
                            hideModal(modalId);
                        }
                    }
                    
                    if (e.target.id === 'info-ok') {
                        updateResult('Info modal acknowledged');
                        hideModal('info-modal');
                    } else if (e.target.id === 'confirm-ok') {
                        updateResult('Action confirmed');
                        hideModal('confirm-modal');
                    } else if (e.target.id === 'confirm-cancel') {
                        updateResult('Action cancelled');
                        hideModal('confirm-modal');
                    } else if (e.target.id === 'form-cancel') {
                        updateResult('Form cancelled');
                        hideModal('form-modal');
                    }
                });
                
                // Form submission
                document.getElementById('modal-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const name = document.getElementById('modal-name').value;
                    const email = document.getElementById('modal-email').value;
                    
                    if (name && email) {
                        updateResult(`Form submitted: ${name} (${email})`);
                        hideModal('form-modal');
                        document.getElementById('modal-form').reset();
                    } else {
                        alert('Please fill in all fields');
                    }
                });
                
                // Close modal when clicking outside
                window.addEventListener('click', function(e) {
                    if (e.target.classList.contains('modal')) {
                        e.target.style.display = 'none';
                    }
                });
            </script>
        </body>
        </html>
        """
        
        # Navigate to modal page
        nav_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": f"data:text/html,{modal_html}"
            }
        )
        assert nav_response["status"] == "success"
        
        # Test Info Modal
        info_modal_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#show-info-modal"
            }
        )
        assert info_modal_response["status"] == "success"
        
        # Wait for modal to appear
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#info-modal"
            }
        )
        
        # Click OK button
        info_ok_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#info-ok"
            }
        )
        assert info_ok_response["status"] == "success"
        
        # Verify result
        info_result_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#result",
                "extract_type": "text"
            }
        )
        assert info_result_response["status"] == "success"
        assert "Info modal acknowledged" in info_result_response["result"]["extracted_text"]
        
        # Test Confirm Modal - Cancel
        confirm_modal_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#show-confirm-modal"
            }
        )
        assert confirm_modal_response["status"] == "success"
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#confirm-modal"
            }
        )
        
        # Click Cancel
        cancel_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#confirm-cancel"
            }
        )
        assert cancel_response["status"] == "success"
        
        # Test Form Modal
        form_modal_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#show-form-modal"
            }
        )
        assert form_modal_response["status"] == "success"
        
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "wait",
                "condition": "visible",
                "selector": "#form-modal"
            }
        )
        
        # Fill form in modal
        name_fill_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#modal-name",
                "value": "John Doe"
            }
        )
        assert name_fill_response["status"] == "success"
        
        email_fill_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "fill",
                "selector": "#modal-email",
                "value": "john.doe@example.com"
            }
        )
        assert email_fill_response["status"] == "success"
        
        # Submit form
        submit_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "click",
                "selector": "#form-submit"
            }
        )
        assert submit_response["status"] == "success"
        
        # Verify form submission result
        form_result_response = await client.execute_command(
            session_id=session_id,
            command={
                "method": "extract",
                "selector": "#result",
                "extract_type": "text"
            }
        )
        assert form_result_response["status"] == "success"
        result_text = form_result_response["result"]["extracted_text"]
        assert "Form submitted" in result_text
        assert "John Doe" in result_text
        assert "john.doe@example.com" in result_text
        
        await client.close_session(session_id)
