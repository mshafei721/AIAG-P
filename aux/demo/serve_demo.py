#!/usr/bin/env python3
"""
AUX Protocol Demo Server

A simple HTTP server that serves the AUX demo interface and optionally
starts the AUX WebSocket server in the background.
"""

import http.server
import socketserver
import threading
import argparse
import webbrowser
import time
import os
import sys
from pathlib import Path

# Add parent directory to path to import AUX modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.aux.server.websocket_server import WebSocketServer
    AUX_SERVER_AVAILABLE = True
except ImportError:
    print("⚠️  AUX server modules not available. Demo will serve UI only.")
    AUX_SERVER_AVAILABLE = False


class DemoHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for demo server with CORS support."""
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()
    
    def log_message(self, format, *args):
        # Custom log format
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")


class DemoServer:
    """Demo server that manages both HTTP and WebSocket servers."""
    
    def __init__(self, http_port=3000, ws_port=8080, auto_open=True):
        self.http_port = http_port
        self.ws_port = ws_port
        self.auto_open = auto_open
        self.http_server = None
        self.ws_server = None
        self.ws_thread = None
        
    def start_websocket_server(self):
        """Start the AUX WebSocket server in a background thread."""
        if not AUX_SERVER_AVAILABLE:
            print("❌ AUX server not available. Please install AUX protocol first.")
            return False
            
        try:
            import asyncio
            
            def run_ws_server():
                # Create new event loop for thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    self.ws_server = WebSocketServer(
                        host="localhost",
                        port=self.ws_port,
                        api_key=None  # No authentication for demo
                    )
                    
                    async def start_server():
                        await self.ws_server.start()
                        print(f"✅ AUX WebSocket server started on ws://localhost:{self.ws_port}")
                        
                        # Keep server running
                        try:
                            await asyncio.Future()  # Run forever
                        except asyncio.CancelledError:
                            pass
                        finally:
                            await self.ws_server.stop()
                    
                    loop.run_until_complete(start_server())
                    
                except Exception as e:
                    print(f"❌ Error starting WebSocket server: {e}")
                finally:
                    loop.close()
            
            self.ws_thread = threading.Thread(target=run_ws_server, daemon=True)
            self.ws_thread.start()
            
            # Wait a moment for server to start
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Failed to start WebSocket server: {e}")
            return False
    
    def start_http_server(self):
        """Start the HTTP server for demo interface."""
        try:
            # Change to demo directory
            demo_dir = Path(__file__).parent
            os.chdir(demo_dir)
            
            # Create HTTP server
            self.http_server = socketserver.TCPServer(
                ("", self.http_port), 
                DemoHTTPRequestHandler
            )
            
            print(f"✅ Demo HTTP server started on http://localhost:{self.http_port}")
            
            # Open browser if requested
            if self.auto_open:
                def open_browser():
                    time.sleep(1)  # Wait for server to be ready
                    webbrowser.open(f"http://localhost:{self.http_port}")
                
                threading.Thread(target=open_browser, daemon=True).start()
            
            # Start serving
            self.http_server.serve_forever()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down servers...")
        except Exception as e:
            print(f"❌ Error starting HTTP server: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop all servers."""
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            print("✅ HTTP server stopped")
        
        if self.ws_server and hasattr(self.ws_server, 'stop'):
            # WebSocket server will be stopped when thread exits
            print("✅ WebSocket server stopped")
    
    def run(self, start_aux_server=True):
        """Run the complete demo setup."""
        print("🚀 Starting AUX Protocol Demo Server")
        print("=" * 50)
        
        # Start WebSocket server if requested and available
        if start_aux_server:
            if self.start_websocket_server():
                print(f"📡 WebSocket: ws://localhost:{self.ws_port}")
            else:
                print("⚠️  WebSocket server not started. Demo will work in UI-only mode.")
        
        # Start HTTP server (this blocks)
        print(f"🌐 Demo UI: http://localhost:{self.http_port}")
        print("\n📖 Instructions:")
        print("1. Open the demo in your browser")
        print("2. Click 'Connect' to connect to the AUX server")
        print("3. Try the example scenarios or create custom commands")
        print("4. Press Ctrl+C to stop all servers")
        print("-" * 50)
        
        self.start_http_server()


def main():
    """Main entry point for demo server."""
    parser = argparse.ArgumentParser(
        description="AUX Protocol Interactive Demo Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python serve_demo.py                    # Start with defaults
  python serve_demo.py --http-port 8000   # Custom HTTP port
  python serve_demo.py --no-aux-server    # UI only, no WebSocket server
  python serve_demo.py --no-browser       # Don't open browser automatically
        """
    )
    
    parser.add_argument(
        '--http-port', 
        type=int, 
        default=3000,
        help='HTTP server port for demo UI (default: 3000)'
    )
    
    parser.add_argument(
        '--ws-port', 
        type=int, 
        default=8080,
        help='WebSocket server port for AUX protocol (default: 8080)'
    )
    
    parser.add_argument(
        '--no-aux-server', 
        action='store_true',
        help='Start only HTTP server, not AUX WebSocket server'
    )
    
    parser.add_argument(
        '--no-browser', 
        action='store_true',
        help='Do not open browser automatically'
    )
    
    args = parser.parse_args()
    
    # Create and run demo server
    demo = DemoServer(
        http_port=args.http_port,
        ws_port=args.ws_port,
        auto_open=not args.no_browser
    )
    
    try:
        demo.run(start_aux_server=not args.no_aux_server)
    except KeyboardInterrupt:
        print("\n👋 Demo server stopped by user")
    except Exception as e:
        print(f"\n❌ Demo server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()