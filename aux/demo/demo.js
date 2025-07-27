/**
 * AUX Protocol Interactive Demo
 * 
 * This script provides a comprehensive demo interface for the AUX protocol,
 * including real-time WebSocket communication, Monaco Editor integration,
 * and interactive command execution.
 */

class AUXDemo {
    constructor() {
        // State management
        this.websocket = null;
        this.isConnected = false;
        this.sessionId = null;
        this.currentTheme = 'light';
        this.commandHistory = [];
        this.editors = {};
        
        // Settings
        this.settings = {
            wsUrl: 'ws://localhost:8080',
            apiKey: '',
            autoConnect: false,
            theme: 'system'
        };

        // Command templates
        this.commandTemplates = {
            navigate: {
                id: this.generateId(),
                method: "navigate",
                session_id: "",
                url: "https://example.com",
                wait_until: "load",
                timeout: 30000
            },
            click: {
                id: this.generateId(),
                method: "click",
                session_id: "",
                selector: "button",
                button: "left",
                timeout: 30000
            },
            fill: {
                id: this.generateId(),
                method: "fill",
                session_id: "",
                selector: "input[name='username']",
                text: "demo_user",
                clear_first: true,
                timeout: 30000
            },
            extract: {
                id: this.generateId(),
                method: "extract",
                session_id: "",
                selector: "h1",
                extract_type: "text",
                multiple: false,
                timeout: 30000
            },
            wait: {
                id: this.generateId(),
                method: "wait",
                session_id: "",
                selector: ".loading",
                condition: "hidden",
                timeout: 30000
            }
        };

        this.init();
    }

    /**
     * Initialize the demo application
     */
    async init() {
        console.log('🚀 Initializing AUX Protocol Demo');
        
        // Load settings from localStorage
        this.loadSettings();
        
        // Initialize theme
        this.initTheme();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize Monaco Editor
        await this.initMonacoEditor();
        
        // Setup initial command
        this.loadCommandTemplate('navigate');
        
        // Auto-connect if enabled
        if (this.settings.autoConnect) {
            setTimeout(() => this.connect(), 1000);
        }
        
        console.log('✅ Demo initialized successfully');
    }

    /**
     * Generate unique ID for commands
     */
    generateId() {
        return 'cmd_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        const saved = localStorage.getItem('aux-demo-settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
        
        // Update UI with loaded settings
        document.getElementById('ws-url').value = this.settings.wsUrl;
        document.getElementById('api-key').value = this.settings.apiKey;
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('aux-demo-settings', JSON.stringify(this.settings));
    }

    /**
     * Initialize theme system
     */
    initTheme() {
        const savedTheme = this.settings.theme;
        
        if (savedTheme === 'system') {
            this.currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        } else {
            this.currentTheme = savedTheme;
        }
        
        this.applyTheme();
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (this.settings.theme === 'system') {
                this.currentTheme = e.matches ? 'dark' : 'light';
                this.applyTheme();
            }
        });
    }

    /**
     * Apply current theme
     */
    applyTheme() {
        const html = document.documentElement;
        const themeIcon = document.getElementById('theme-icon');
        
        if (this.currentTheme === 'dark') {
            html.classList.add('dark');
            themeIcon.className = 'fas fa-sun text-lg';
        } else {
            html.classList.remove('dark');
            themeIcon.className = 'fas fa-moon text-lg';
        }
        
        // Update Monaco Editor themes if they exist
        if (this.editors.command) {
            monaco.editor.setTheme(this.currentTheme === 'dark' ? 'vs-dark' : 'vs');
        }
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
            this.settings.theme = this.currentTheme;
            this.applyTheme();
            this.saveSettings();
        });

        // Connection button
        document.getElementById('connect-btn').addEventListener('click', () => {
            if (this.isConnected) {
                this.disconnect();
            } else {
                this.connect();
            }
        });

        // Settings
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.showSettings();
        });

        document.getElementById('settings-cancel').addEventListener('click', () => {
            this.hideSettings();
        });

        document.getElementById('settings-save').addEventListener('click', () => {
            this.saveSettingsFromModal();
        });

        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabId = e.target.dataset.tab;
                this.switchTab(tabId);
            });
        });

        // Quick commands
        document.querySelectorAll('.quick-command').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.currentTarget.dataset.command;
                this.loadCommandTemplate(command);
            });
        });

        // Scenario buttons
        document.querySelectorAll('.scenario-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const scenario = e.currentTarget.dataset.scenario;
                this.loadScenario(scenario);
            });
        });

        // Command editor actions
        document.getElementById('execute-btn').addEventListener('click', () => {
            this.executeCommand();
        });

        document.getElementById('format-btn').addEventListener('click', () => {
            this.formatCommand();
        });

        document.getElementById('clear-btn').addEventListener('click', () => {
            this.clearCommand();
        });

        document.getElementById('clear-history-btn').addEventListener('click', () => {
            this.clearHistory();
        });

        // Connection settings
        document.getElementById('ws-url').addEventListener('change', (e) => {
            this.settings.wsUrl = e.target.value;
            this.saveSettings();
        });

        document.getElementById('api-key').addEventListener('change', (e) => {
            this.settings.apiKey = e.target.value;
            this.saveSettings();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to execute command
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.executeCommand();
            }
        });
    }

    /**
     * Initialize Monaco Editor
     */
    async initMonacoEditor() {
        return new Promise((resolve) => {
            require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
            
            require(['vs/editor/editor.main'], () => {
                // Command editor
                this.editors.command = monaco.editor.create(document.getElementById('command-editor'), {
                    value: '',
                    language: 'json',
                    theme: this.currentTheme === 'dark' ? 'vs-dark' : 'vs',
                    automaticLayout: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    formatOnPaste: true,
                    formatOnType: true
                });

                // Response viewer
                this.editors.response = monaco.editor.create(document.getElementById('response-viewer'), {
                    value: '',
                    language: 'json',
                    theme: this.currentTheme === 'dark' ? 'vs-dark' : 'vs',
                    automaticLayout: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    readOnly: true
                });

                // Setup JSON schema validation for commands
                this.setupJsonSchema();
                
                resolve();
            });
        });
    }

    /**
     * Setup JSON schema validation for AUX commands
     */
    setupJsonSchema() {
        const auxCommandSchema = {
            type: "object",
            properties: {
                id: { type: "string", description: "Unique command identifier" },
                method: { 
                    type: "string", 
                    enum: ["navigate", "click", "fill", "extract", "wait"],
                    description: "Command method name"
                },
                session_id: { type: "string", description: "Browser session ID" },
                timeout: { 
                    type: "integer", 
                    minimum: 1000, 
                    maximum: 300000,
                    description: "Command timeout in milliseconds (1s-5min)"
                }
            },
            required: ["id", "method", "session_id"],
            additionalProperties: true
        };

        monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
            validate: true,
            schemas: [{
                uri: "http://aux-protocol.com/command-schema.json",
                fileMatch: ["*"],
                schema: auxCommandSchema
            }]
        });
    }

    /**
     * Connect to WebSocket server
     */
    async connect() {
        try {
            this.showToast('Connecting to AUX server...', 'info');
            
            const wsUrl = document.getElementById('ws-url').value;
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.sessionId = this.generateId();
                this.updateConnectionStatus();
                this.showToast('Connected to AUX server', 'success');
                console.log('✅ Connected to AUX WebSocket server');
            };

            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event);
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.sessionId = null;
                this.updateConnectionStatus();
                this.showToast('Disconnected from AUX server', 'warning');
                console.log('🔌 Disconnected from AUX WebSocket server');
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.showToast('Connection error', 'error');
            };

        } catch (error) {
            console.error('❌ Connection failed:', error);
            this.showToast('Failed to connect: ' + error.message, 'error');
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleWebSocketMessage(event) {
        try {
            const response = JSON.parse(event.data);
            console.log('📨 Received response:', response);
            
            // Display response in editor
            this.editors.response.setValue(JSON.stringify(response, null, 2));
            
            // Update response status indicator
            this.updateResponseStatus(response);
            
            // Add to history
            this.addToHistory('response', response);
            
        } catch (error) {
            console.error('❌ Error parsing response:', error);
            this.showToast('Error parsing server response', 'error');
        }
    }

    /**
     * Update connection status in UI
     */
    updateConnectionStatus() {
        const indicator = document.getElementById('connection-indicator');
        const text = document.getElementById('connection-text');
        const button = document.getElementById('connect-btn');
        const sessionInfo = document.getElementById('session-info');
        const sessionDisplay = document.getElementById('session-id-display');

        if (this.isConnected) {
            indicator.className = 'w-3 h-3 rounded-full bg-green-500 connection-indicator';
            text.textContent = 'Connected';
            button.textContent = 'Disconnect';
            button.className = 'px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition-colors';
            
            sessionInfo.classList.remove('hidden');
            sessionDisplay.textContent = this.sessionId?.substring(0, 8) + '...';
        } else {
            indicator.className = 'w-3 h-3 rounded-full bg-gray-400';
            text.textContent = 'Disconnected';
            button.textContent = 'Connect';
            button.className = 'px-4 py-2 bg-aux-500 hover:bg-aux-600 text-white font-medium rounded-lg transition-colors';
            
            sessionInfo.classList.add('hidden');
        }
    }

    /**
     * Update response status indicator
     */
    updateResponseStatus(response) {
        const statusEl = document.getElementById('response-status');
        const timeEl = document.getElementById('execution-time');
        
        if (response.success) {
            statusEl.className = 'px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
            statusEl.textContent = 'SUCCESS';
        } else {
            statusEl.className = 'px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
            statusEl.textContent = 'ERROR';
        }
        
        if (response.execution_time_ms) {
            timeEl.textContent = `${response.execution_time_ms}ms`;
        }
        
        statusEl.classList.remove('hidden');
    }

    /**
     * Execute current command
     */
    async executeCommand() {
        if (!this.isConnected) {
            this.showToast('Please connect to the server first', 'warning');
            return;
        }

        try {
            const commandText = this.editors.command.getValue();
            if (!commandText.trim()) {
                this.showToast('Please enter a command', 'warning');
                return;
            }

            const command = JSON.parse(commandText);
            
            // Set session ID if not present
            if (!command.session_id) {
                command.session_id = this.sessionId;
            }
            
            // Generate new ID if not present
            if (!command.id) {
                command.id = this.generateId();
            }

            console.log('📤 Sending command:', command);
            
            // Add to history
            this.addToHistory('command', command);
            
            // Send command
            this.websocket.send(JSON.stringify(command));
            
            // Clear previous response
            this.editors.response.setValue('');
            document.getElementById('response-status').classList.add('hidden');
            document.getElementById('execution-time').textContent = '';
            
            this.showToast('Command sent', 'info');
            
        } catch (error) {
            console.error('❌ Error executing command:', error);
            this.showToast('Invalid JSON command: ' + error.message, 'error');
        }
    }

    /**
     * Format current command JSON
     */
    formatCommand() {
        try {
            const command = JSON.parse(this.editors.command.getValue());
            this.editors.command.setValue(JSON.stringify(command, null, 2));
            this.showToast('Command formatted', 'success');
        } catch (error) {
            this.showToast('Invalid JSON - cannot format', 'error');
        }
    }

    /**
     * Clear command editor
     */
    clearCommand() {
        this.editors.command.setValue('');
        this.editors.response.setValue('');
        document.getElementById('response-status').classList.add('hidden');
        document.getElementById('execution-time').textContent = '';
    }

    /**
     * Load command template
     */
    loadCommandTemplate(commandType) {
        if (this.commandTemplates[commandType]) {
            const template = { ...this.commandTemplates[commandType] };
            template.id = this.generateId();
            template.session_id = this.sessionId || "";
            
            this.editors.command.setValue(JSON.stringify(template, null, 2));
            this.showToast(`Loaded ${commandType} template`, 'info');
        }
    }

    /**
     * Load example scenario
     */
    loadScenario(scenarioType) {
        const scenarios = {
            'basic-navigation': [
                {
                    id: this.generateId(),
                    method: "navigate",
                    session_id: this.sessionId || "",
                    url: "https://example.com",
                    wait_until: "load",
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "extract",
                    session_id: this.sessionId || "",
                    selector: "h1",
                    extract_type: "text",
                    timeout: 30000
                }
            ],
            'form-automation': [
                {
                    id: this.generateId(),
                    method: "navigate",
                    session_id: this.sessionId || "",
                    url: "https://httpbin.org/forms/post",
                    wait_until: "load",
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "fill",
                    session_id: this.sessionId || "",
                    selector: "input[name='custname']",
                    text: "John Doe",
                    clear_first: true,
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "click",
                    session_id: this.sessionId || "",
                    selector: "input[type='submit']",
                    timeout: 30000
                }
            ],
            'ecommerce-journey': [
                {
                    id: this.generateId(),
                    method: "navigate",
                    session_id: this.sessionId || "",
                    url: "https://demo.opencart.com/",
                    wait_until: "load",
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "fill",
                    session_id: this.sessionId || "",
                    selector: "input[name='search']",
                    text: "laptop",
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "click",
                    session_id: this.sessionId || "",
                    selector: ".btn-default",
                    timeout: 30000
                }
            ],
            'data-extraction': [
                {
                    id: this.generateId(),
                    method: "navigate",
                    session_id: this.sessionId || "",
                    url: "https://quotes.toscrape.com/",
                    wait_until: "load",
                    timeout: 30000
                },
                {
                    id: this.generateId(),
                    method: "extract",
                    session_id: this.sessionId || "",
                    selector: ".quote",
                    extract_type: "text",
                    multiple: true,
                    timeout: 30000
                }
            ]
        };

        if (scenarios[scenarioType]) {
            const scenario = scenarios[scenarioType];
            this.editors.command.setValue(JSON.stringify(scenario[0], null, 2));
            this.showToast(`Loaded ${scenarioType} scenario`, 'info');
        }
    }

    /**
     * Add item to command history
     */
    addToHistory(type, data) {
        const historyContainer = document.getElementById('command-history');
        const timestamp = new Date().toLocaleTimeString();
        
        // Remove empty state message
        const emptyState = historyContainer.querySelector('.text-center');
        if (emptyState) {
            emptyState.remove();
        }

        const historyItem = document.createElement('div');
        historyItem.className = 'p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600';
        
        const isCommand = type === 'command';
        const method = data.method || 'response';
        const badgeClass = isCommand ? `command-${method}` : (data.success ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300');
        
        historyItem.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                    <span class="command-badge ${badgeClass}">
                        ${isCommand ? method.toUpperCase() : (data.success ? 'SUCCESS' : 'ERROR')}
                    </span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">${timestamp}</span>
                </div>
                <button class="text-xs text-aux-600 dark:text-aux-400 hover:underline" onclick="auxDemo.loadFromHistory('${JSON.stringify(data).replace(/'/g, "\\'")}')">
                    Load
                </button>
            </div>
            <pre class="text-xs text-gray-700 dark:text-gray-300 overflow-x-auto">${JSON.stringify(data, null, 2)}</pre>
        `;
        
        historyContainer.insertBefore(historyItem, historyContainer.firstChild);
        
        // Keep only last 20 items
        while (historyContainer.children.length > 20) {
            historyContainer.removeChild(historyContainer.lastChild);
        }
    }

    /**
     * Load command from history
     */
    loadFromHistory(dataStr) {
        try {
            const data = JSON.parse(dataStr);
            this.editors.command.setValue(JSON.stringify(data, null, 2));
            this.showToast('Command loaded from history', 'info');
        } catch (error) {
            this.showToast('Error loading from history', 'error');
        }
    }

    /**
     * Clear command history
     */
    clearHistory() {
        const historyContainer = document.getElementById('command-history');
        historyContainer.innerHTML = `
            <div class="text-center text-gray-500 dark:text-gray-400 py-8">
                <i class="fas fa-history text-2xl mb-2"></i>
                <p>No commands executed yet</p>
            </div>
        `;
    }

    /**
     * Switch between tabs
     */
    switchTab(tabId) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabId) {
                btn.className = 'tab-btn active py-3 px-1 text-sm font-medium border-b-2 border-aux-500 text-aux-600 dark:text-aux-400';
            } else {
                btn.className = 'tab-btn py-3 px-1 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200';
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            if (content.id === `${tabId}-tab`) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    }

    /**
     * Show settings modal
     */
    showSettings() {
        document.getElementById('settings-modal').classList.remove('hidden');
        document.getElementById('theme-select').value = this.settings.theme;
        document.getElementById('auto-connect').checked = this.settings.autoConnect;
    }

    /**
     * Hide settings modal
     */
    hideSettings() {
        document.getElementById('settings-modal').classList.add('hidden');
    }

    /**
     * Save settings from modal
     */
    saveSettingsFromModal() {
        this.settings.theme = document.getElementById('theme-select').value;
        this.settings.autoConnect = document.getElementById('auto-connect').checked;
        
        this.saveSettings();
        this.initTheme();
        this.hideSettings();
        this.showToast('Settings saved', 'success');
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        
        const colors = {
            info: 'bg-blue-500 text-white',
            success: 'bg-green-500 text-white',
            warning: 'bg-yellow-500 text-white',
            error: 'bg-red-500 text-white'
        };
        
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle'
        };
        
        toast.className = `${colors[type]} px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-slide-up`;
        toast.innerHTML = `
            <i class="${icons[type]}"></i>
            <span>${message}</span>
            <button class="ml-2 hover:bg-black/10 rounded p-1" onclick="this.parentElement.remove()">
                <i class="fas fa-times text-sm"></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after duration
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, duration);
    }
}

// Initialize demo when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.auxDemo = new AUXDemo();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.auxDemo?.isConnected) {
        console.log('🔍 Page hidden - maintaining WebSocket connection');
    } else if (!document.hidden && window.auxDemo && !window.auxDemo.isConnected) {
        console.log('👁️ Page visible - checking connection');
    }
});

// Handle before page unload
window.addEventListener('beforeunload', () => {
    if (window.auxDemo?.isConnected) {
        window.auxDemo.disconnect();
    }
});