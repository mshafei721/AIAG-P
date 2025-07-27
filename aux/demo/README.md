# AUX Protocol Interactive Demo

A comprehensive web-based demonstration of the AUX (Agent UX Layer) protocol, showcasing real-time browser automation capabilities through an intuitive interface.

## 🚀 Features

### Interactive Command Console
- **Monaco Editor Integration**: Full-featured JSON editor with syntax highlighting, auto-completion, and error detection
- **Real-time WebSocket Communication**: Live connection to AUX protocol server
- **Command History**: Track and replay executed commands
- **Response Visualization**: Pretty-printed JSON responses with execution timing

### Pre-built Scenarios
- **Basic Navigation**: Website loading and content extraction
- **Form Automation**: Automated form filling and submission
- **E-commerce Journey**: Product search and interaction workflows
- **Data Extraction**: Structured content scraping examples
- **Error Handling**: Resilience testing with invalid inputs
- **Performance Testing**: Rapid command execution benchmarks

### Modern UI/UX
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Dark/Light Themes**: Automatic system theme detection with manual override
- **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation
- **Real-time Status**: Connection indicators and session management
- **Toast Notifications**: User-friendly feedback system

## 🛠️ Setup Instructions

### Prerequisites
- AUX Protocol WebSocket server running (see main project setup)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Web server for serving static files (optional for local development)

### Quick Start

1. **Start the AUX Server**
   ```bash
   cd /path/to/aux
   python -m src.aux.server.websocket_server --host localhost --port 8080
   ```

2. **Serve the Demo** (Option 1: Simple HTTP Server)
   ```bash
   cd demo/
   python -m http.server 3000
   ```
   
   Or use any static file server:
   ```bash
   # Using Node.js http-server
   npx http-server demo/ -p 3000
   
   # Using PHP
   php -S localhost:3000 -t demo/
   ```

3. **Open in Browser**
   ```
   http://localhost:3000
   ```

4. **Connect to AUX Server**
   - Click "Connect" button in the demo interface
   - Default WebSocket URL: `ws://localhost:8080`
   - Enter API key if server authentication is enabled

## 📖 Usage Guide

### Basic Operations

1. **Connecting to Server**
   - Enter WebSocket URL (default: `ws://localhost:8080`)
   - Add API key if required by server configuration
   - Click "Connect" to establish WebSocket connection
   - Green indicator shows successful connection

2. **Executing Commands**
   - Use Quick Commands for templates
   - Edit JSON in the Monaco Editor
   - Click "Execute Command" or press Ctrl/Cmd+Enter
   - View responses in the right panel

3. **Example Scenarios**
   - Click any scenario button in the sidebar
   - Follow the step-by-step instructions
   - Each scenario includes expected results

### Command Templates

The demo includes templates for all AUX protocol commands:

#### Navigate Command
```json
{
  "id": "cmd_abc123",
  "method": "navigate",
  "session_id": "session_xyz",
  "url": "https://example.com",
  "wait_until": "load",
  "timeout": 30000
}
```

#### Click Command
```json
{
  "id": "cmd_def456",
  "method": "click",
  "session_id": "session_xyz",
  "selector": "button.submit",
  "button": "left",
  "timeout": 30000
}
```

#### Fill Command
```json
{
  "id": "cmd_ghi789",
  "method": "fill",
  "session_id": "session_xyz",
  "selector": "input[name='username']",
  "text": "demo_user",
  "clear_first": true,
  "timeout": 30000
}
```

#### Extract Command
```json
{
  "id": "cmd_jkl012",
  "method": "extract",
  "session_id": "session_xyz",
  "selector": "h1",
  "extract_type": "text",
  "multiple": false,
  "timeout": 30000
}
```

#### Wait Command
```json
{
  "id": "cmd_mno345",
  "method": "wait",
  "session_id": "session_xyz",
  "selector": ".loading",
  "condition": "hidden",
  "timeout": 30000
}
```

### Advanced Features

#### Scenario Categories
- **Fundamentals**: Basic operations (navigate, extract)
- **User Interaction**: Forms, clicks, user workflows
- **E-commerce**: Product search, shopping cart operations
- **Data Scraping**: Content extraction, structured data mining
- **Testing & QA**: Error handling, edge cases
- **Performance**: Speed testing, optimization scenarios

#### Keyboard Shortcuts
- `Ctrl/Cmd + Enter`: Execute current command
- `Ctrl/Cmd + K`: Clear command editor
- `Ctrl/Cmd + H`: Toggle command history
- `Ctrl/Cmd + T`: Toggle theme
- `Escape`: Close modals

#### Session Management
- Automatic session ID generation
- Session persistence across page reloads
- Multiple session support (coming soon)
- Session timeout handling

## 🎯 Demo Scenarios

### 1. Basic Navigation Scenario
**Objective**: Load a webpage and extract content
**Steps**:
1. Navigate to https://example.com
2. Extract page title (`h1` element)
3. Extract page content (`p` element)

**Expected Results**: Successfully loads page and extracts "Example Domain" title

### 2. Form Automation Scenario
**Objective**: Fill and submit a web form
**Steps**:
1. Navigate to form page
2. Fill customer name field
3. Fill email field
4. Select options
5. Submit form

**Expected Results**: Form submits successfully with filled data

### 3. E-commerce Journey Scenario
**Objective**: Simulate product search workflow
**Steps**:
1. Navigate to demo store
2. Search for "MacBook"
3. Extract product names and prices
4. Click on first product

**Expected Results**: Successfully navigates through product search flow

### 4. Data Extraction Scenario
**Objective**: Scrape structured content
**Steps**:
1. Navigate to quotes website
2. Extract all quote texts
3. Extract all author names
4. Navigate to next page

**Expected Results**: Efficiently extracts structured quote data

### 5. Error Handling Scenario
**Objective**: Demonstrate resilience
**Steps**:
1. Try invalid selector (expect error)
2. Test timeout scenario (expect timeout)
3. Recover with valid command

**Expected Results**: Graceful error handling and recovery

## 🔧 Configuration Options

### Server Settings
- **WebSocket URL**: Default `ws://localhost:8080`
- **API Key**: Optional authentication key
- **Auto-connect**: Connect automatically on page load
- **Session Timeout**: Configurable timeout duration

### UI Preferences
- **Theme**: Light, Dark, or System preference
- **Font Size**: Adjustable editor font size
- **Line Numbers**: Toggle line numbers in editor
- **Word Wrap**: Enable/disable word wrapping

### Performance Settings
- **Command Timeout**: Default 30 seconds
- **Connection Retry**: Automatic reconnection attempts
- **History Limit**: Maximum stored commands (default: 50)

## 🔍 Debugging & Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify AUX server is running on specified port
   - Check WebSocket URL format (ws:// or wss://)
   - Ensure no firewall blocking connection

2. **Command Timeout**
   - Increase timeout value in command
   - Check network connectivity
   - Verify target website accessibility

3. **Element Not Found**
   - Verify CSS selector syntax
   - Check if element exists on page
   - Wait for dynamic content to load

4. **Invalid JSON**
   - Use Format button to validate JSON
   - Check for missing commas or quotes
   - Verify command schema compliance

### Debug Information

The demo logs detailed information to browser console:
- WebSocket connection events
- Command execution timing
- Response parsing status
- Error details and stack traces

Access browser developer tools (F12) to view debug logs.

### Performance Monitoring

The demo tracks:
- Command execution time
- WebSocket message latency
- Memory usage patterns
- Error frequency

View real-time metrics in the connection status panel.

## 🛡️ Security Considerations

### Authentication
- API key authentication supported
- Secure WebSocket connections (WSS) recommended for production
- Rate limiting honored by demo client

### Data Privacy
- No sensitive data stored in localStorage
- Session IDs are randomly generated
- Command history can be cleared

### Network Security
- CORS headers respected
- CSP-compliant implementation
- No external resource dependencies (except CDN libraries)

## 🚀 Deployment

### Production Deployment

1. **Build Optimization**
   ```bash
   # Minify JavaScript and CSS
   npm install -g terser clean-css-cli
   terser demo.js -o demo.min.js -c -m
   cleancss -o demo.min.css demo.css
   ```

2. **Static Hosting**
   - Deploy to any static hosting service
   - Configure HTTPS for production use
   - Set up proper cache headers

3. **CDN Integration**
   - Host Monaco Editor locally for better performance
   - Use CDN for Tailwind CSS and Font Awesome
   - Implement service worker for offline capability

### Docker Deployment

```dockerfile
FROM nginx:alpine
COPY demo/ /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```bash
docker build -t aux-demo .
docker run -p 8080:80 aux-demo
```

## 📊 Analytics & Metrics

The demo can be extended with analytics:
- Command usage statistics
- Error rate monitoring
- Performance benchmarking
- User interaction patterns

Integration points for popular analytics services are provided in the codebase.

## 🤝 Contributing

To contribute to the demo:

1. Fork the repository
2. Create feature branch
3. Add new scenarios or UI improvements
4. Test across different browsers
5. Submit pull request with detailed description

### Adding New Scenarios

1. Define scenario in `scenarios.js`
2. Add UI elements if needed
3. Test scenario execution
4. Update documentation

## 📝 License

This demo is part of the AUX Protocol project and follows the same licensing terms.

## 📞 Support

For issues and questions:
- Check troubleshooting section above
- Review browser console for error details
- Open issue in main AUX Protocol repository
- Join community discussions

---

**Enjoy exploring the power of the AUX Protocol! 🤖✨**