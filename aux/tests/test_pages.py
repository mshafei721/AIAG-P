"""
Mock HTML test pages for browser manager testing.

This module provides HTML content for creating test pages that can be used
for integration testing without requiring external websites. The pages are
designed to test various browser automation scenarios.
"""

from typing import Dict, Any


def get_basic_test_page() -> str:
    """Get basic HTML page for simple navigation tests."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Basic Test Page</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .hidden { display: none; }
        .visible { display: block; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        input { padding: 8px; margin: 5px; width: 200px; }
        .status { padding: 10px; background: #f0f0f0; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Basic Test Page</h1>
        <p>This is a test page for browser automation.</p>
        
        <button id="test-button" onclick="handleClick()">Click Me</button>
        <button id="hidden-button" class="hidden">Hidden Button</button>
        
        <div id="click-result" class="status">No clicks yet</div>
        
        <form id="test-form">
            <input type="text" id="text-input" placeholder="Enter text here">
            <input type="search" id="search-input" placeholder="Search...">
            <button type="submit" id="submit-button">Submit</button>
        </form>
        
        <div id="extract-content">
            <p class="content-text">This is extractable text content.</p>
            <a href="https://example.com" class="test-link">Example Link</a>
            <div data-value="test-data" class="data-element">Data Element</div>
        </div>
        
        <ul id="list-items">
            <li class="item">Item 1</li>
            <li class="item">Item 2</li>
            <li class="item">Item 3</li>
        </ul>
        
        <div id="loading-indicator" class="visible">Loading...</div>
        <div id="complete-indicator" class="hidden">Complete!</div>
    </div>
    
    <script>
        let clickCount = 0;
        
        function handleClick() {
            clickCount++;
            document.getElementById('click-result').textContent = 
                `Button clicked ${clickCount} time(s)`;
        }
        
        function showComplete() {
            document.getElementById('loading-indicator').className = 'hidden';
            document.getElementById('complete-indicator').className = 'visible';
        }
        
        function hideComplete() {
            document.getElementById('loading-indicator').className = 'visible';
            document.getElementById('complete-indicator').className = 'hidden';
        }
        
        // Auto-complete after 2 seconds
        setTimeout(showComplete, 2000);
        
        // Form submission handler
        document.getElementById('test-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const input = document.getElementById('text-input');
            alert('Form submitted with: ' + input.value);
        });
        
        // Global test functions
        window.testFunctions = {
            showHidden: function() {
                document.getElementById('hidden-button').className = 'visible';
            },
            hideHidden: function() {
                document.getElementById('hidden-button').className = 'hidden';
            },
            updateContent: function(text) {
                document.querySelector('.content-text').textContent = text;
            },
            isReady: function() {
                return document.readyState === 'complete';
            }
        };
    </script>
</body>
</html>
"""


def get_form_test_page() -> str:
    """Get HTML page with complex forms for input testing."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">  
    <title>Form Test Page</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { 
            padding: 8px; margin-bottom: 10px; width: 250px; 
            border: 1px solid #ccc; border-radius: 4px;
        }
        button { 
            padding: 10px 20px; background: #007bff; color: white; 
            border: none; border-radius: 4px; cursor: pointer;
        }
        .validation-error { color: red; font-size: 12px; }
        .success-message { color: green; padding: 10px; background: #f0f8ff; }
    </style>
</head>
<body>
    <h1>Form Test Page</h1>
    
    <form id="registration-form">
        <div class="form-group">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
            <div id="username-error" class="validation-error"></div>
        </div>
        
        <div class="form-group">
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" required>
            <div id="email-error" class="validation-error"></div>
        </div>
        
        <div class="form-group">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
        </div>
        
        <div class="form-group">
            <label for="country">Country:</label>
            <select id="country" name="country">
                <option value="">Select Country</option>
                <option value="us">United States</option>
                <option value="ca">Canada</option>
                <option value="uk">United Kingdom</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="bio">Bio:</label>
            <textarea id="bio" name="bio" rows="4" placeholder="Tell us about yourself..."></textarea>
        </div>
        
        <div class="form-group">
            <input type="checkbox" id="terms" name="terms">
            <label for="terms">I agree to the terms and conditions</label>
        </div>
        
        <button type="submit" id="submit-form">Register</button>
    </form>
    
    <div id="form-result" class="success-message" style="display: none;"></div>
    
    <script>
        document.getElementById('registration-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous errors
            document.querySelectorAll('.validation-error').forEach(el => el.textContent = '');
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            
            // Simple validation
            let isValid = true;
            
            if (!data.username || data.username.length < 3) {
                document.getElementById('username-error').textContent = 
                    'Username must be at least 3 characters';
                isValid = false;
            }
            
            if (!data.email || !data.email.includes('@')) {
                document.getElementById('email-error').textContent = 
                    'Please enter a valid email address';
                isValid = false;
            }
            
            if (isValid) {
                document.getElementById('form-result').style.display = 'block';
                document.getElementById('form-result').textContent = 
                    `Registration successful for ${data.username}!`;
            }
        });
        
        // Test functions
        window.formTestFunctions = {
            fillForm: function() {
                document.getElementById('username').value = 'testuser';
                document.getElementById('email').value = 'test@example.com';
                document.getElementById('password').value = 'password123';
                document.getElementById('country').value = 'us';
                document.getElementById('bio').value = 'This is a test bio.';
                document.getElementById('terms').checked = true;
            },
            clearForm: function() {
                document.getElementById('registration-form').reset();
            },
            validateForm: function() {
                return document.querySelectorAll('.validation-error').length === 0;
            }
        };
    </script>
</body>
</html>
"""


def get_dynamic_content_page() -> str:
    """Get HTML page with dynamic content for wait condition testing."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dynamic Content Test Page</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .loading { 
            color: #666; font-style: italic; 
            background: #f0f0f0; padding: 10px; margin: 10px 0;
        }
        .content { 
            background: #e8f5e8; padding: 15px; margin: 10px 0; 
            border-left: 4px solid #4caf50;
        }
        .error { 
            background: #fee; padding: 15px; margin: 10px 0; 
            border-left: 4px solid #f44336; color: #d32f2f;
        }
        .hidden { display: none; }
        .visible { display: block; }
        button { 
            padding: 8px 16px; margin: 5px; background: #2196f3; 
            color: white; border: none; border-radius: 4px; cursor: pointer;
        }
        .progress-bar {
            width: 100%; height: 20px; background: #f0f0f0; 
            border-radius: 10px; overflow: hidden; margin: 10px 0;
        }
        .progress-fill {
            height: 100%; background: #4caf50; width: 0%; 
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <h1>Dynamic Content Test Page</h1>
    
    <div class="controls">
        <button onclick="startLoading()">Start Loading</button>
        <button onclick="stopLoading()">Stop Loading</button>
        <button onclick="showError()">Show Error</button>
        <button onclick="addItem()">Add Item</button>
        <button onclick="removeItem()">Remove Item</button>
    </div>
    
    <div id="status-indicator" class="loading hidden">Loading content...</div>
    <div id="success-indicator" class="content hidden">Content loaded successfully!</div>
    <div id="error-indicator" class="error hidden">An error occurred!</div>
    
    <div class="progress-bar">
        <div id="progress-fill" class="progress-fill"></div>
    </div>
    <div id="progress-text">0%</div>
    
    <div id="dynamic-list">
        <h3>Dynamic List</h3>
        <ul id="item-list">
            <li class="list-item">Initial item</li>
        </ul>
    </div>
    
    <div id="timed-content" class="hidden">
        <p>This content appears after 3 seconds</p>
    </div>
    
    <div id="ajax-content" class="hidden">
        <p>This simulates AJAX loaded content</p>
    </div>
    
    <script>
        let itemCounter = 1;
        let loadingInterval;
        let progressInterval;
        
        function startLoading() {
            // Hide all status indicators
            document.querySelectorAll('[id$="-indicator"]').forEach(el => 
                el.className = el.className.replace('visible', 'hidden'));
            
            // Show loading
            document.getElementById('status-indicator').className = 'loading visible';
            
            // Simulate progress
            let progress = 0;
            progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(progressInterval);
                    finishLoading();
                }
                updateProgress(progress);
            }, 200);
        }
        
        function finishLoading() {
            document.getElementById('status-indicator').className = 'loading hidden';
            document.getElementById('success-indicator').className = 'content visible';
            document.getElementById('ajax-content').className = 'visible';
        }
        
        function stopLoading() {
            clearInterval(progressInterval);
            document.getElementById('status-indicator').className = 'loading hidden';
            updateProgress(0);
        }
        
        function showError() {
            clearInterval(progressInterval);
            document.querySelectorAll('[id$="-indicator"]').forEach(el => 
                el.className = el.className.replace('visible', 'hidden'));
            document.getElementById('error-indicator').className = 'error visible';
        }
        
        function updateProgress(percent) {
            const fill = document.getElementById('progress-fill');
            const text = document.getElementById('progress-text');
            fill.style.width = percent + '%';
            text.textContent = Math.round(percent) + '%';
        }
        
        function addItem() {
            itemCounter++;
            const list = document.getElementById('item-list');
            const newItem = document.createElement('li');
            newItem.className = 'list-item';
            newItem.textContent = `Dynamic item ${itemCounter}`;
            list.appendChild(newItem);
        }
        
        function removeItem() {
            const items = document.querySelectorAll('.list-item');
            if (items.length > 1) {  // Keep at least one item
                items[items.length - 1].remove();
            }
        }
        
        // Show timed content after 3 seconds
        setTimeout(() => {
            document.getElementById('timed-content').className = 'visible';
        }, 3000);
        
        // Global test functions
        window.dynamicTestFunctions = {
            isLoadingVisible: function() {
                return document.getElementById('status-indicator').className.includes('visible');
            },
            isSuccessVisible: function() {
                return document.getElementById('success-indicator').className.includes('visible');
            },
            isErrorVisible: function() {
                return document.getElementById('error-indicator').className.includes('visible');
            },
            getProgress: function() {
                return parseInt(document.getElementById('progress-text').textContent);
            },
            getItemCount: function() {
                return document.querySelectorAll('.list-item').length;
            },
            waitForProgress: function(targetPercent) {
                return new Promise((resolve) => {
                    const checkProgress = () => {
                        if (this.getProgress() >= targetPercent) {
                            resolve(true);
                        } else {
                            setTimeout(checkProgress, 100);
                        }
                    };
                    checkProgress();
                });
            }
        };
    </script>
</body>
</html>
"""


def get_test_page_data() -> Dict[str, Any]:
    """Get test page data for creating data URLs."""
    return {
        "basic": {
            "html": get_basic_test_page(),
            "title": "Basic Test Page",
            "description": "Simple page for basic browser automation tests"
        },
        "forms": {
            "html": get_form_test_page(), 
            "title": "Form Test Page",
            "description": "Complex forms for input and validation testing"
        },
        "dynamic": {
            "html": get_dynamic_content_page(),
            "title": "Dynamic Content Test Page", 
            "description": "Dynamic content for wait condition testing"
        }
    }


def create_data_url(html_content: str) -> str:
    """Create a data URL from HTML content for browser navigation."""
    import base64
    encoded = base64.b64encode(html_content.encode('utf-8')).decode('ascii')
    return f"data:text/html;base64,{encoded}"


def get_test_page_urls() -> Dict[str, str]:
    """Get data URLs for all test pages."""
    pages = get_test_page_data()
    return {
        name: create_data_url(page["html"])
        for name, page in pages.items()
    }