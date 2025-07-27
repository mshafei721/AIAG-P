/**
 * AUX Protocol Demo Scenarios
 * 
 * This file contains predefined scenarios that demonstrate various 
 * capabilities of the AUX protocol in real-world use cases.
 */

export const demoScenarios = {
    'basic-navigation': {
        title: 'Basic Navigation',
        description: 'Load and extract page content from a website',
        category: 'fundamentals',
        difficulty: 'beginner',
        estimatedTime: '30 seconds',
        steps: [
            {
                title: 'Navigate to Example.com',
                description: 'Load the example.com website and wait for it to fully load',
                command: {
                    method: "navigate",
                    url: "https://example.com",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Page loads successfully with "Example Domain" title'
            },
            {
                title: 'Extract Page Title',
                description: 'Extract the main heading from the page',
                command: {
                    method: "extract",
                    selector: "h1",
                    extract_type: "text",
                    multiple: false,
                    timeout: 30000
                },
                expectedResult: 'Returns "Example Domain" text'
            },
            {
                title: 'Extract Page Content',
                description: 'Extract the main paragraph content',
                command: {
                    method: "extract",
                    selector: "p",
                    extract_type: "text",
                    multiple: false,
                    timeout: 30000
                },
                expectedResult: 'Returns the page description paragraph'
            }
        ]
    },

    'form-automation': {
        title: 'Form Automation',
        description: 'Fill and submit web forms automatically',
        category: 'interaction',
        difficulty: 'intermediate',
        estimatedTime: '1 minute',
        steps: [
            {
                title: 'Navigate to Form Page',
                description: 'Load a test form page from httpbin.org',
                command: {
                    method: "navigate",
                    url: "https://httpbin.org/forms/post",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Form page loads with input fields visible'
            },
            {
                title: 'Fill Customer Name',
                description: 'Enter a customer name in the form field',
                command: {
                    method: "fill",
                    selector: "input[name='custname']",
                    text: "John Doe",
                    clear_first: true,
                    timeout: 30000
                },
                expectedResult: 'Name field is filled with "John Doe"'
            },
            {
                title: 'Fill Customer Telephone',
                description: 'Enter a phone number in the telephone field',
                command: {
                    method: "fill",
                    selector: "input[name='custtel']",
                    text: "+1-555-0123",
                    clear_first: true,
                    timeout: 30000
                },
                expectedResult: 'Phone field is filled with the number'
            },
            {
                title: 'Fill Email Address',
                description: 'Enter an email address in the email field',
                command: {
                    method: "fill",
                    selector: "input[name='custemail']",
                    text: "john.doe@example.com",
                    clear_first: true,
                    timeout: 30000
                },
                expectedResult: 'Email field is filled with the address'
            },
            {
                title: 'Select Pizza Size',
                description: 'Select the medium pizza size option',
                command: {
                    method: "click",
                    selector: "input[value='medium']",
                    timeout: 30000
                },
                expectedResult: 'Medium pizza option is selected'
            },
            {
                title: 'Add Pizza Topping',
                description: 'Select pepperoni as a topping',
                command: {
                    method: "click",
                    selector: "input[value='pepperoni']",
                    timeout: 30000
                },
                expectedResult: 'Pepperoni topping is checked'
            },
            {
                title: 'Submit Form',
                description: 'Click the submit button to send the form',
                command: {
                    method: "click",
                    selector: "input[type='submit']",
                    timeout: 30000
                },
                expectedResult: 'Form is submitted and response page loads'
            }
        ]
    },

    'ecommerce-journey': {
        title: 'E-commerce Journey',
        description: 'Product search and interaction on a demo store',
        category: 'ecommerce',
        difficulty: 'intermediate',
        estimatedTime: '2 minutes',
        steps: [
            {
                title: 'Navigate to Demo Store',
                description: 'Load the OpenCart demo store homepage',
                command: {
                    method: "navigate",
                    url: "https://demo.opencart.com/",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'OpenCart demo store loads successfully'
            },
            {
                title: 'Search for Products',
                description: 'Enter "MacBook" in the search field',
                command: {
                    method: "fill",
                    selector: "input[name='search']",
                    text: "MacBook",
                    clear_first: true,
                    timeout: 30000
                },
                expectedResult: 'Search field contains "MacBook"'
            },
            {
                title: 'Execute Search',
                description: 'Click the search button to find products',
                command: {
                    method: "click",
                    selector: "button.btn-default",
                    timeout: 30000
                },
                expectedResult: 'Search results page loads with MacBook products'
            },
            {
                title: 'Extract Product Names',
                description: 'Get all product names from search results',
                command: {
                    method: "extract",
                    selector: ".product-thumb h4 a",
                    extract_type: "text",
                    multiple: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of MacBook product names'
            },
            {
                title: 'Extract Product Prices',
                description: 'Get all product prices from search results',
                command: {
                    method: "extract",
                    selector: ".product-thumb .price",
                    extract_type: "text",
                    multiple: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of product prices'
            },
            {
                title: 'Click First Product',
                description: 'Click on the first MacBook in search results',
                command: {
                    method: "click",
                    selector: ".product-thumb:first-child h4 a",
                    timeout: 30000
                },
                expectedResult: 'Product detail page loads for the selected MacBook'
            }
        ]
    },

    'data-extraction': {
        title: 'Data Extraction',
        description: 'Scrape structured content from a quotes website',
        category: 'scraping',
        difficulty: 'beginner',
        estimatedTime: '45 seconds',
        steps: [
            {
                title: 'Navigate to Quotes Site',
                description: 'Load the quotes.toscrape.com website',
                command: {
                    method: "navigate",
                    url: "https://quotes.toscrape.com/",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Quotes website loads with multiple quotes visible'
            },
            {
                title: 'Extract All Quote Texts',
                description: 'Get the text of all quotes on the page',
                command: {
                    method: "extract",
                    selector: ".quote .text",
                    extract_type: "text",
                    multiple: true,
                    trim_whitespace: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of quote texts'
            },
            {
                title: 'Extract All Authors',
                description: 'Get the names of all quote authors',
                command: {
                    method: "extract",
                    selector: ".quote .author",
                    extract_type: "text",
                    multiple: true,
                    trim_whitespace: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of author names'
            },
            {
                title: 'Extract Quote Tags',
                description: 'Get all tags associated with quotes',
                command: {
                    method: "extract",
                    selector: ".quote .tags a",
                    extract_type: "text",
                    multiple: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of all tags used'
            },
            {
                title: 'Navigate to Next Page',
                description: 'Click the "Next" button to load more quotes',
                command: {
                    method: "click",
                    selector: ".next a",
                    timeout: 30000
                },
                expectedResult: 'Page 2 loads with additional quotes'
            }
        ]
    },

    'social-media-interaction': {
        title: 'Social Media Interaction',
        description: 'Interact with social media elements on a demo site',
        category: 'social',
        difficulty: 'intermediate',
        estimatedTime: '1 minute',
        steps: [
            {
                title: 'Navigate to JSONPlaceholder',
                description: 'Load a demo social media-like interface',
                command: {
                    method: "navigate",
                    url: "https://jsonplaceholder.typicode.com/",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'JSONPlaceholder demo site loads'
            },
            {
                title: 'Extract Navigation Links',
                description: 'Get all main navigation menu items',
                command: {
                    method: "extract",
                    selector: "nav a",
                    extract_type: "text",
                    multiple: true,
                    timeout: 30000
                },
                expectedResult: 'Returns array of navigation link texts'
            },
            {
                title: 'Click on Guide Link',
                description: 'Navigate to the guide section',
                command: {
                    method: "click",
                    selector: "a[href*='guide']",
                    timeout: 30000
                },
                expectedResult: 'Guide page loads with documentation'
            }
        ]
    },

    'error-handling': {
        title: 'Error Handling & Resilience',
        description: 'Demonstrate error handling with invalid selectors and timeouts',
        category: 'testing',
        difficulty: 'advanced',
        estimatedTime: '1 minute',
        steps: [
            {
                title: 'Navigate to Test Page',
                description: 'Load a simple test page',
                command: {
                    method: "navigate",
                    url: "https://example.com",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Page loads successfully'
            },
            {
                title: 'Test Invalid Selector',
                description: 'Try to click an element that does not exist',
                command: {
                    method: "click",
                    selector: ".non-existent-element",
                    timeout: 5000
                },
                expectedResult: 'Returns error: element not found'
            },
            {
                title: 'Test Timeout Scenario',
                description: 'Wait for an element that will never appear',
                command: {
                    method: "wait",
                    selector: ".loading-spinner-that-never-exists",
                    condition: "visible",
                    timeout: 3000
                },
                expectedResult: 'Returns timeout error after 3 seconds'
            },
            {
                title: 'Recover with Valid Action',
                description: 'Execute a valid command to show recovery',
                command: {
                    method: "extract",
                    selector: "title",
                    extract_type: "text",
                    timeout: 5000
                },
                expectedResult: 'Successfully extracts page title'
            }
        ]
    },

    'advanced-interaction': {
        title: 'Advanced Interaction Patterns',
        description: 'Complex user interactions including waits and conditional logic',
        category: 'advanced',
        difficulty: 'advanced',
        estimatedTime: '2 minutes',
        steps: [
            {
                title: 'Navigate to Dynamic Content Site',
                description: 'Load a page with dynamic content loading',
                command: {
                    method: "navigate",
                    url: "https://httpbin.org/delay/2",
                    wait_until: "load",
                    timeout: 35000
                },
                expectedResult: 'Page loads after 2-second delay'
            },
            {
                title: 'Navigate to Form with Validation',
                description: 'Load a page with client-side form validation',
                command: {
                    method: "navigate",
                    url: "https://httpbin.org/forms/post",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Form page loads with validation features'
            },
            {
                title: 'Test Form Validation',
                description: 'Try to submit empty form to trigger validation',
                command: {
                    method: "click",
                    selector: "input[type='submit']",
                    timeout: 30000
                },
                expectedResult: 'Form validation may trigger'
            },
            {
                title: 'Fill Required Fields',
                description: 'Fill minimum required fields to pass validation',
                command: {
                    method: "fill",
                    selector: "input[name='custname']",
                    text: "Test User",
                    clear_first: true,
                    timeout: 30000
                },
                expectedResult: 'Required field is filled'
            },
            {
                title: 'Wait for Dynamic Element',
                description: 'Wait for any dynamic content to load',
                command: {
                    method: "wait",
                    selector: "form",
                    condition: "visible",
                    timeout: 10000
                },
                expectedResult: 'Form is visible and ready for interaction'
            }
        ]
    },

    'performance-testing': {
        title: 'Performance Testing',
        description: 'Test performance with rapid sequential commands',
        category: 'performance',
        difficulty: 'advanced',
        estimatedTime: '45 seconds',
        steps: [
            {
                title: 'Load Fast Website',
                description: 'Navigate to a lightweight, fast-loading site',
                command: {
                    method: "navigate",
                    url: "https://example.com",
                    wait_until: "load",
                    timeout: 30000
                },
                expectedResult: 'Page loads quickly'
            },
            {
                title: 'Rapid Element Extraction 1',
                description: 'Quickly extract page title',
                command: {
                    method: "extract",
                    selector: "h1",
                    extract_type: "text",
                    timeout: 5000
                },
                expectedResult: 'Title extracted in minimal time'
            },
            {
                title: 'Rapid Element Extraction 2',
                description: 'Quickly extract page content',
                command: {
                    method: "extract",
                    selector: "p",
                    extract_type: "text",
                    timeout: 5000
                },
                expectedResult: 'Content extracted in minimal time'
            },
            {
                title: 'Rapid Element Extraction 3',
                description: 'Quickly extract link information',
                command: {
                    method: "extract",
                    selector: "a",
                    extract_type: "attribute",
                    attribute_name: "href",
                    timeout: 5000
                },
                expectedResult: 'Link href extracted in minimal time'
            },
            {
                title: 'Multiple Element Extraction',
                description: 'Extract multiple elements simultaneously',
                command: {
                    method: "extract",
                    selector: "*",
                    extract_type: "text",
                    multiple: true,
                    timeout: 10000
                },
                expectedResult: 'All text content extracted efficiently'
            }
        ]
    }
};

export const scenarioCategories = {
    fundamentals: {
        name: 'Fundamentals',
        description: 'Basic AUX protocol operations',
        color: 'blue',
        icon: 'fas fa-play-circle'
    },
    interaction: {
        name: 'User Interaction',
        description: 'Form filling and clicking actions',
        color: 'green',
        icon: 'fas fa-mouse-pointer'
    },
    ecommerce: {
        name: 'E-commerce',
        description: 'Shopping and product interactions',
        color: 'purple',
        icon: 'fas fa-shopping-cart'
    },
    scraping: {
        name: 'Data Scraping',
        description: 'Content extraction and data mining',
        color: 'orange',
        icon: 'fas fa-database'
    },
    social: {
        name: 'Social Media',
        description: 'Social platform interactions',
        color: 'pink',
        icon: 'fas fa-users'
    },
    testing: {
        name: 'Testing & QA',
        description: 'Error handling and edge cases',
        color: 'red',
        icon: 'fas fa-bug'
    },
    advanced: {
        name: 'Advanced',
        description: 'Complex interaction patterns',
        color: 'indigo',
        icon: 'fas fa-cogs'
    },
    performance: {
        name: 'Performance',
        description: 'Speed and efficiency testing',
        color: 'yellow',
        icon: 'fas fa-tachometer-alt'
    }
};

export const difficultyLevels = {
    beginner: {
        name: 'Beginner',
        description: 'Simple commands for getting started',
        color: 'green',
        icon: 'fas fa-seedling'
    },
    intermediate: {
        name: 'Intermediate',
        description: 'Multi-step workflows and interactions',
        color: 'yellow',
        icon: 'fas fa-tree'
    },
    advanced: {
        name: 'Advanced',
        description: 'Complex scenarios with error handling',
        color: 'red',
        icon: 'fas fa-rocket'
    }
};