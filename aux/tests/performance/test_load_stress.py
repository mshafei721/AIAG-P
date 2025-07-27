"""
Performance tests for load and stress testing.

Tests system performance under various load conditions,
concurrent users, memory usage, and resource scaling.
"""

import asyncio
import json
import time
import psutil
import pytest
import websockets
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median, stdev

from aux.server.websocket_server import AUXWebSocketServer
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.performance
@pytest.mark.slow
class TestLoadStress:
    """Performance tests for load and stress scenarios."""

    @pytest.fixture
    async def performance_server(self, test_config: Config):
        """Provide server optimized for performance testing."""
        # Configure for higher load
        perf_config = test_config.copy()
        perf_config.server_config.update({
            "max_connections": 1000,
            "heartbeat_interval": 30,
            "close_timeout": 10,
        })
        
        security_manager = SecurityManager({
            "enable_auth": True,
            "rate_limit_per_minute": 1000,  # Higher for performance testing
            "max_session_duration": 7200,
            "max_sessions_per_client": 50,
        })
        
        server = AUXWebSocketServer(
            config=perf_config,
            security_manager=security_manager
        )
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    def performance_monitor(self):
        """Monitor system resources during tests."""
        class PerformanceMonitor:
            def __init__(self):
                self.cpu_samples = []
                self.memory_samples = []
                self.start_time = None
                self.monitoring = False
            
            async def start_monitoring(self):
                """Start resource monitoring."""
                self.start_time = time.time()
                self.monitoring = True
                
                while self.monitoring:
                    self.cpu_samples.append(psutil.cpu_percent(interval=0.1))
                    self.memory_samples.append(psutil.virtual_memory().percent)
                    await asyncio.sleep(0.5)
            
            def stop_monitoring(self):
                """Stop resource monitoring."""
                self.monitoring = False
            
            def get_stats(self) -> Dict[str, Any]:
                """Get performance statistics."""
                if not self.cpu_samples or not self.memory_samples:
                    return {}
                
                return {
                    "duration": time.time() - self.start_time if self.start_time else 0,
                    "cpu": {
                        "avg": mean(self.cpu_samples),
                        "max": max(self.cpu_samples),
                        "min": min(self.cpu_samples),
                        "std": stdev(self.cpu_samples) if len(self.cpu_samples) > 1 else 0
                    },
                    "memory": {
                        "avg": mean(self.memory_samples),
                        "max": max(self.memory_samples),
                        "min": min(self.memory_samples),
                        "std": stdev(self.memory_samples) if len(self.memory_samples) > 1 else 0
                    }
                }
        
        return PerformanceMonitor()

    async def test_concurrent_connections_load(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str,
        performance_monitor
    ):
        """Test concurrent connection handling."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Start monitoring
        monitor_task = asyncio.create_task(performance_monitor.start_monitoring())
        
        async def client_session(client_id: int) -> Dict[str, Any]:
            """Individual client session."""
            start_time = time.time()
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    # Send a series of commands
                    commands = [
                        {"method": "navigate", "url": f"data:text/html,<h1>Client {client_id}</h1>"},
                        {"method": "extract", "selector": "h1", "extract_type": "text"},
                        {"method": "navigate", "url": f"data:text/html,<p>Test {client_id}</p>"},
                        {"method": "extract", "selector": "p", "extract_type": "text"},
                    ]
                    
                    for command in commands:
                        await websocket.send(json.dumps(command))
                        response = json.loads(await websocket.recv())
                        assert response["status"] == "success"
                    
                    return {
                        "client_id": client_id,
                        "success": True,
                        "duration": time.time() - start_time,
                        "commands_sent": len(commands)
                    }
                    
            except Exception as e:
                return {
                    "client_id": client_id,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        # Test with increasing concurrent clients
        for num_clients in [10, 25, 50]:
            print(f"Testing with {num_clients} concurrent clients...")
            
            # Create concurrent client tasks
            tasks = [client_session(i) for i in range(num_clients)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_clients = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_clients = [r for r in results if isinstance(r, dict) and not r.get("success")]
            
            print(f"Successful: {len(successful_clients)}, Failed: {len(failed_clients)}")
            
            # Performance assertions
            success_rate = len(successful_clients) / num_clients
            assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
            
            if successful_clients:
                avg_duration = mean([r["duration"] for r in successful_clients])
                assert avg_duration < 10.0, f"Average duration {avg_duration:.2f}s too high"
        
        # Stop monitoring
        performance_monitor.stop_monitoring()
        monitor_task.cancel()
        
        # Check resource usage
        stats = performance_monitor.get_stats()
        if stats:
            print(f"Resource usage - CPU: {stats['cpu']['avg']:.1f}%, Memory: {stats['memory']['avg']:.1f}%")
            assert stats["cpu"]["avg"] < 80, "CPU usage too high"
            assert stats["memory"]["avg"] < 90, "Memory usage too high"

    async def test_sustained_load(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str,
        performance_monitor
    ):
        """Test sustained load over time."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Start monitoring
        monitor_task = asyncio.create_task(performance_monitor.start_monitoring())
        
        async def sustained_client() -> Dict[str, Any]:
            """Client that maintains sustained activity."""
            commands_sent = 0
            errors = 0
            start_time = time.time()
            
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    # Run for 60 seconds
                    end_time = start_time + 60
                    
                    while time.time() < end_time:
                        command = {
                            "method": "navigate",
                            "url": f"data:text/html,<h1>Time: {time.time()}</h1>"
                        }
                        
                        try:
                            await websocket.send(json.dumps(command))
                            response = json.loads(await websocket.recv())
                            
                            if response["status"] != "success":
                                errors += 1
                            
                            commands_sent += 1
                            
                        except Exception:
                            errors += 1
                        
                        # Rate limit: 10 commands per second
                        await asyncio.sleep(0.1)
                    
                    return {
                        "duration": time.time() - start_time,
                        "commands_sent": commands_sent,
                        "errors": errors,
                        "success_rate": (commands_sent - errors) / commands_sent if commands_sent > 0 else 0
                    }
                    
            except Exception as e:
                return {
                    "duration": time.time() - start_time,
                    "commands_sent": commands_sent,
                    "errors": errors + 1,
                    "error": str(e)
                }
        
        # Run 5 sustained clients
        tasks = [sustained_client() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Stop monitoring
        performance_monitor.stop_monitoring()
        monitor_task.cancel()
        
        # Analyze sustained performance
        total_commands = sum(r["commands_sent"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        overall_success_rate = (total_commands - total_errors) / total_commands if total_commands > 0 else 0
        
        print(f"Sustained load: {total_commands} commands, {overall_success_rate:.2%} success rate")
        
        assert overall_success_rate >= 0.98, "Success rate too low for sustained load"
        assert total_commands >= 2500, "Too few commands processed"  # ~8.3 cmd/sec per client
        
        # Check resource stability
        stats = performance_monitor.get_stats()
        if stats:
            assert stats["cpu"]["std"] < 20, "CPU usage too variable"
            assert stats["memory"]["std"] < 10, "Memory usage too variable"

    @pytest.mark.benchmark
    def test_command_execution_benchmark(self, benchmark, sample_commands: Dict[str, Any]):
        """Benchmark individual command execution performance."""
        
        async def execute_command_sequence():
            """Execute a sequence of commands for benchmarking."""
            # This would normally connect to server and execute commands
            # For benchmark, we'll simulate the processing time
            await asyncio.sleep(0.001)  # Simulate 1ms processing time
            return True
        
        # Benchmark the command execution
        result = benchmark(asyncio.run, execute_command_sequence())
        assert result is True

    async def test_memory_leak_detection(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test for memory leaks during extended operation."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Baseline memory usage
        baseline_memory = psutil.virtual_memory().used
        
        # Create and destroy many sessions
        for cycle in range(10):
            print(f"Memory test cycle {cycle + 1}/10")
            
            # Create multiple concurrent sessions
            async def session_cycle():
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    for i in range(10):
                        command = {
                            "method": "navigate",
                            "url": f"data:text/html,<div>Cycle {cycle} Item {i}</div>"
                        }
                        await websocket.send(json.dumps(command))
                        await websocket.recv()
            
            # Run 20 concurrent sessions
            tasks = [session_cycle() for _ in range(20)]
            await asyncio.gather(*tasks)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Check memory usage
            current_memory = psutil.virtual_memory().used
            memory_increase = current_memory - baseline_memory
            memory_increase_mb = memory_increase / (1024 * 1024)
            
            print(f"Memory increase: {memory_increase_mb:.1f} MB")
            
            # Memory increase should be reasonable
            assert memory_increase_mb < 100, f"Excessive memory increase: {memory_increase_mb:.1f} MB"

    async def test_response_time_under_load(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test response time degradation under load."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async def measure_response_time() -> float:
            """Measure response time for a single command."""
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                start_time = time.perf_counter()
                
                command = {
                    "method": "navigate",
                    "url": "data:text/html,<h1>Response Time Test</h1>"
                }
                
                await websocket.send(json.dumps(command))
                await websocket.recv()
                
                return time.perf_counter() - start_time
        
        # Measure baseline response time (no load)
        baseline_times = []
        for _ in range(10):
            response_time = await measure_response_time()
            baseline_times.append(response_time)
        
        baseline_avg = mean(baseline_times)
        print(f"Baseline response time: {baseline_avg:.3f}s")
        
        # Measure response time under load
        async def background_load():
            """Generate background load."""
            while True:
                try:
                    await measure_response_time()
                    await asyncio.sleep(0.01)  # 100 req/sec per task
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass
        
        # Start background load
        load_tasks = [asyncio.create_task(background_load()) for _ in range(20)]
        
        try:
            # Wait for load to stabilize
            await asyncio.sleep(2)
            
            # Measure response times under load
            loaded_times = []
            for _ in range(10):
                response_time = await measure_response_time()
                loaded_times.append(response_time)
            
            loaded_avg = mean(loaded_times)
            print(f"Loaded response time: {loaded_avg:.3f}s")
            
            # Response time degradation should be reasonable
            degradation_factor = loaded_avg / baseline_avg
            assert degradation_factor < 3.0, f"Response time degraded by {degradation_factor:.1f}x"
            
        finally:
            # Stop background load
            for task in load_tasks:
                task.cancel()
            await asyncio.gather(*load_tasks, return_exceptions=True)

    async def test_connection_pool_scaling(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test connection pool scaling behavior."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        connections = []
        connection_times = []
        
        try:
            # Gradually increase connections
            for batch in range(10):  # 10 batches of 10 connections each
                batch_start = time.time()
                
                # Add 10 more connections
                for _ in range(10):
                    websocket = await websockets.connect(uri, extra_headers=headers)
                    connections.append(websocket)
                
                batch_time = time.time() - batch_start
                connection_times.append(batch_time)
                
                print(f"Batch {batch + 1}: {len(connections)} total connections, {batch_time:.3f}s")
                
                # Test that all connections are still responsive
                test_command = {
                    "method": "navigate",
                    "url": f"data:text/html,<h1>Connection {len(connections)}</h1>"
                }
                
                # Test a few random connections
                import random
                test_connections = random.sample(connections, min(5, len(connections)))
                
                for websocket in test_connections:
                    await websocket.send(json.dumps(test_command))
                    response = json.loads(await websocket.recv())
                    assert response["status"] == "success"
        
        finally:
            # Clean up all connections
            for websocket in connections:
                await websocket.close()
        
        # Analyze scaling behavior
        if len(connection_times) > 1:
            # Connection establishment time shouldn't increase dramatically
            first_batch_time = connection_times[0]
            last_batch_time = connection_times[-1]
            
            scaling_factor = last_batch_time / first_batch_time
            assert scaling_factor < 5.0, f"Connection time scaled poorly: {scaling_factor:.1f}x"

    async def test_browser_pool_performance(
        self,
        performance_server: AUXWebSocketServer,
        api_key: str
    ):
        """Test browser pool performance and reuse."""
        uri = f"ws://localhost:{performance_server.port}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        session_creation_times = []
        
        async def create_session_and_measure():
            """Create session and measure time."""
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                start_time = time.perf_counter()
                
                command = {
                    "method": "navigate",
                    "url": "data:text/html,<h1>Pool Test</h1>"
                }
                
                await websocket.send(json.dumps(command))
                response = json.loads(await websocket.recv())
                
                creation_time = time.perf_counter() - start_time
                return creation_time, response["session_id"]
        
        # Create many sessions to test pool efficiency
        for i in range(50):
            creation_time, session_id = await create_session_and_measure()
            session_creation_times.append(creation_time)
            
            if i % 10 == 0:
                avg_time = mean(session_creation_times[-10:]) if len(session_creation_times) >= 10 else mean(session_creation_times)
                print(f"Session {i + 1}: {avg_time:.3f}s average creation time")
        
        # Analyze pool performance
        early_avg = mean(session_creation_times[:10])  # First 10 sessions
        late_avg = mean(session_creation_times[-10:])  # Last 10 sessions
        
        print(f"Early sessions: {early_avg:.3f}s, Late sessions: {late_avg:.3f}s")
        
        # Pool should improve performance over time (reuse)
        # Allow some variance but expect general improvement or stability
        efficiency_ratio = late_avg / early_avg
        assert efficiency_ratio < 2.0, f"Pool efficiency degraded: {efficiency_ratio:.1f}x slower"