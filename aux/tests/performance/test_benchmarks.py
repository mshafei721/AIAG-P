"""
Comprehensive performance benchmarking tests for AUX Protocol.

Includes throughput testing, latency measurement, resource usage monitoring,
and scalability assessments for the AUX Protocol implementation.
"""

import asyncio
import time
import psutil
import pytest
import statistics
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Comprehensive performance benchmarking tests."""
    
    @pytest.fixture
    async def performance_setup(self, test_config, benchmark_config):
        """Set up performance testing environment."""
        # Optimize configuration for performance testing
        perf_config = test_config
        perf_config.browser_config.headless = True
        perf_config.server_config.max_connections = 1000
        perf_config.security_config.rate_limit_per_minute = 10000
        
        security_manager = SecurityManager(perf_config.security_config)
        browser_manager = BrowserManager(perf_config)
        server = AUXWebSocketServer(perf_config, security_manager, browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        yield {
            "server": server,
            "browser_manager": browser_manager,
            "security_manager": security_manager,
            "config": perf_config,
            "benchmark_config": benchmark_config
        }
        
        await server.stop()
        await browser_manager.stop()
        
    def test_command_processing_throughput(self, performance_setup, benchmark):
        """Benchmark command processing throughput."""
        setup = performance_setup
        
        @benchmark
        async def process_commands():
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key="benchmark-key"
            )
            
            await client.connect()
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            
            # Navigate to test page
            await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": "data:text/html,<div id='content'>Benchmark Test</div>"
                }
            )
            
            # Execute 100 extract commands
            for i in range(100):
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "#content",
                        "extract_type": "text"
                    }
                )
                
            await client.close_session(session_id)
            await client.disconnect()
            
        # Run the benchmark
        asyncio.run(process_commands())
        
    def test_concurrent_session_handling(self, performance_setup, benchmark):
        """Benchmark concurrent session handling performance."""
        setup = performance_setup
        
        @benchmark
        async def handle_concurrent_sessions():
            # Create multiple clients
            clients = []
            sessions = []
            
            try:
                # Create 50 concurrent clients
                for i in range(50):
                    client = AUXClient(
                        url=f"ws://{setup['server'].host}:{setup['server'].port}",
                        api_key=f"benchmark-key-{i}"
                    )
                    await client.connect()
                    clients.append(client)
                    
                # Create sessions concurrently
                session_tasks = [client.create_session() for client in clients]
                session_responses = await asyncio.gather(*session_tasks)
                sessions = [resp["session_id"] for resp in session_responses if resp["status"] == "success"]
                
                # Execute commands concurrently
                async def execute_on_session(client, session_id):
                    await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "navigate",
                            "url": "data:text/html,<div>Concurrent Test</div>"
                        }
                    )
                    
                command_tasks = [
                    execute_on_session(clients[i], sessions[i])
                    for i in range(len(sessions))
                ]
                await asyncio.gather(*command_tasks)
                
            finally:
                # Cleanup
                for i, client in enumerate(clients):
                    if i < len(sessions):
                        try:
                            await client.close_session(sessions[i])
                        except:
                            pass
                    try:
                        await client.disconnect()
                    except:
                        pass
                        
        asyncio.run(handle_concurrent_sessions())
        
    def test_memory_usage_benchmark(self, performance_setup, benchmark):
        """Benchmark memory usage patterns."""
        setup = performance_setup
        
        @benchmark
        def memory_usage_test():
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            async def memory_intensive_operations():
                client = AUXClient(
                    url=f"ws://{setup['server'].host}:{setup['server'].port}",
                    api_key="memory-benchmark-key"
                )
                
                await client.connect()
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Create large content
                large_content = "<div>" + "Large content " * 10000 + "</div>"
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,{large_content}"
                    }
                )
                
                # Extract large content multiple times
                for i in range(20):
                    await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "extract",
                            "selector": "div",
                            "extract_type": "html"
                        }
                    )
                    
                await client.close_session(session_id)
                await client.disconnect()
                
            asyncio.run(memory_intensive_operations())
            
            # Check final memory usage
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB"
            
        memory_usage_test()


@pytest.mark.performance
class TestLatencyMeasurement:
    """Test and measure system latency characteristics."""
    
    async def test_command_response_latency(self, performance_setup):
        """Measure command response latency."""
        setup = performance_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="latency-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Warm up
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='test'>Latency Test</div>"
            }
        )
        
        # Measure latencies for different command types
        latencies = {
            "navigate": [],
            "click": [],
            "fill": [],
            "extract": [],
            "wait": []
        }
        
        # Test navigate latency
        for i in range(10):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Navigate Test {i}</div>"
                }
            )
            latency = time.time() - start_time
            latencies["navigate"].append(latency)
            assert response["status"] == "success"
            
        # Test extract latency
        for i in range(20):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "extract",
                    "selector": "div",
                    "extract_type": "text"
                }
            )
            latency = time.time() - start_time
            latencies["extract"].append(latency)
            assert response["status"] == "success"
            
        # Test click latency (on interactive page)
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<button id='btn'>Click Me</button>"
            }
        )
        
        for i in range(10):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "click",
                    "selector": "#btn"
                }
            )
            latency = time.time() - start_time
            latencies["click"].append(latency)
            assert response["status"] == "success"
            
        # Test fill latency
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<input id='input' type='text'>"
            }
        )
        
        for i in range(10):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "fill",
                    "selector": "#input",
                    "value": f"Test value {i}"
                }
            )
            latency = time.time() - start_time
            latencies["fill"].append(latency)
            assert response["status"] == "success"
            
        # Test wait latency
        for i in range(5):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "wait",
                    "condition": "load",
                    "timeout": 1000
                }
            )
            latency = time.time() - start_time
            latencies["wait"].append(latency)
            assert response["status"] == "success"
            
        # Analyze latency statistics
        for command_type, measurements in latencies.items():
            if measurements:
                avg_latency = statistics.mean(measurements)
                median_latency = statistics.median(measurements)
                p95_latency = sorted(measurements)[int(0.95 * len(measurements))]
                
                print(f"\n{command_type.upper()} Latency Statistics:")
                print(f"  Average: {avg_latency:.3f}s")
                print(f"  Median: {median_latency:.3f}s")
                print(f"  95th percentile: {p95_latency:.3f}s")
                print(f"  Min: {min(measurements):.3f}s")
                print(f"  Max: {max(measurements):.3f}s")
                
                # Performance assertions
                assert avg_latency < 1.0, f"{command_type} average latency too high: {avg_latency:.3f}s"
                assert p95_latency < 2.0, f"{command_type} 95th percentile latency too high: {p95_latency:.3f}s"
                
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_network_latency_impact(self, performance_setup):
        """Test impact of network latency on performance."""
        setup = performance_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="network-latency-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Test with artificial network delays
        base_latencies = []
        
        # Measure baseline latency
        for i in range(10):
            start_time = time.time()
            response = await client.execute_command(
                session_id=session_id,
                command={
                    "method": "navigate",
                    "url": f"data:text/html,<div>Baseline Test {i}</div>"
                }
            )
            latency = time.time() - start_time
            base_latencies.append(latency)
            assert response["status"] == "success"
            
        baseline_avg = statistics.mean(base_latencies)
        
        # Test with simulated network delay
        # (This would require network simulation tools in a real environment)
        
        print(f"\nNetwork Latency Impact:")
        print(f"  Baseline average latency: {baseline_avg:.3f}s")
        
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.performance
class TestThroughputMeasurement:
    """Test system throughput under various loads."""
    
    async def test_commands_per_second(self, performance_setup):
        """Measure commands per second throughput."""
        setup = performance_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="throughput-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='counter'>0</div>"
            }
        )
        
        # Measure throughput for different command types
        command_counts = {
            "extract": 200,
            "evaluate": 100,
            "fill": 50
        }
        
        for command_type, count in command_counts.items():
            print(f"\nMeasuring {command_type} throughput...")
            
            if command_type == "extract":
                commands = [
                    {
                        "method": "extract",
                        "selector": "#counter",
                        "extract_type": "text"
                    }
                    for _ in range(count)
                ]
            elif command_type == "evaluate":
                commands = [
                    {
                        "method": "evaluate",
                        "script": f"document.getElementById('counter').textContent = '{i}'"
                    }
                    for i in range(count)
                ]
            elif command_type == "fill":
                # Set up input field
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": "data:text/html,<input id='input' type='text'>"
                    }
                )
                commands = [
                    {
                        "method": "fill",
                        "selector": "#input",
                        "value": f"Value {i}"
                    }
                    for i in range(count)
                ]
                
            # Execute commands and measure time
            start_time = time.time()
            
            tasks = [
                client.execute_command(session_id=session_id, command=cmd)
                for cmd in commands
            ]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Calculate throughput
            successful_commands = len([r for r in results if r["status"] == "success"])
            throughput = successful_commands / duration
            
            print(f"  {command_type.upper()} Throughput: {throughput:.2f} commands/second")
            print(f"  Total time: {duration:.3f}s")
            print(f"  Successful commands: {successful_commands}/{count}")
            
            # Performance assertions
            assert throughput > 10, f"{command_type} throughput too low: {throughput:.2f} cmd/s"
            assert successful_commands >= count * 0.95, f"Too many failed {command_type} commands"
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_concurrent_client_throughput(self, performance_setup):
        """Measure throughput with multiple concurrent clients."""
        setup = performance_setup
        
        client_count = 10
        commands_per_client = 20
        
        async def client_workload(client_id):
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key=f"concurrent-test-key-{client_id}"
            )
            
            try:
                await client.connect()
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Execute commands
                for i in range(commands_per_client):
                    response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "navigate",
                            "url": f"data:text/html,<div>Client {client_id} Command {i}</div>"
                        }
                    )
                    assert response["status"] == "success"
                    
                await client.close_session(session_id)
                return commands_per_client
                
            finally:
                await client.disconnect()
                
        # Run concurrent clients
        start_time = time.time()
        
        tasks = [client_workload(i) for i in range(client_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate overall throughput
        successful_commands = sum(r for r in results if isinstance(r, int))
        total_throughput = successful_commands / duration
        
        print(f"\nConcurrent Client Throughput:")
        print(f"  Clients: {client_count}")
        print(f"  Commands per client: {commands_per_client}")
        print(f"  Total successful commands: {successful_commands}")
        print(f"  Total time: {duration:.3f}s")
        print(f"  Overall throughput: {total_throughput:.2f} commands/second")
        print(f"  Per-client throughput: {total_throughput / client_count:.2f} commands/second")
        
        # Performance assertions
        assert total_throughput > 50, f"Concurrent throughput too low: {total_throughput:.2f} cmd/s"
        assert successful_commands >= client_count * commands_per_client * 0.9, "Too many failed commands"


@pytest.mark.performance
class TestResourceUtilization:
    """Test resource utilization under load."""
    
    async def test_cpu_utilization(self, performance_setup):
        """Monitor CPU utilization during load testing."""
        setup = performance_setup
        
        # Monitor CPU usage
        process = psutil.Process()
        cpu_samples = []
        
        async def monitor_cpu():
            while True:
                cpu_percent = process.cpu_percent()
                cpu_samples.append(cpu_percent)
                await asyncio.sleep(0.1)
                
        # Start CPU monitoring
        monitor_task = asyncio.create_task(monitor_cpu())
        
        try:
            # Create load
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key="cpu-test-key"
            )
            
            await client.connect()
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            
            # Execute CPU-intensive operations
            for i in range(100):
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>{'Large content ' * 1000}</div>"
                    }
                )
                
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "div",
                        "extract_type": "html"
                    }
                )
                
            await client.close_session(session_id)
            await client.disconnect()
            
        finally:
            monitor_task.cancel()
            
        # Analyze CPU usage
        if cpu_samples:
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)
            
            print(f"\nCPU Utilization:")
            print(f"  Average CPU: {avg_cpu:.2f}%")
            print(f"  Peak CPU: {max_cpu:.2f}%")
            print(f"  Samples: {len(cpu_samples)}")
            
            # CPU should not be maxed out
            assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.2f}%"
            assert max_cpu < 95, f"Peak CPU usage too high: {max_cpu:.2f}%"
            
    async def test_memory_growth_pattern(self, performance_setup):
        """Test memory growth patterns under sustained load."""
        setup = performance_setup
        
        process = psutil.Process()
        memory_samples = []
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="memory-growth-test-key"
        )
        
        await client.connect()
        
        # Monitor memory over multiple sessions
        for session_num in range(20):
            # Record memory before session
            memory_before = process.memory_info().rss
            
            session_response = await client.create_session()
            session_id = session_response["session_id"]
            
            # Perform operations
            for i in range(10):
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>Session {session_num} Operation {i}</div>"
                    }
                )
                
            await client.close_session(session_id)
            
            # Record memory after session
            memory_after = process.memory_info().rss
            memory_samples.append({
                "session": session_num,
                "before": memory_before,
                "after": memory_after,
                "growth": memory_after - memory_before
            })
            
        await client.disconnect()
        
        # Analyze memory growth
        total_growth = memory_samples[-1]["after"] - memory_samples[0]["before"]
        avg_growth_per_session = statistics.mean([s["growth"] for s in memory_samples])
        
        print(f"\nMemory Growth Pattern:")
        print(f"  Total memory growth: {total_growth / 1024 / 1024:.2f} MB")
        print(f"  Average growth per session: {avg_growth_per_session / 1024:.2f} KB")
        print(f"  Sessions tested: {len(memory_samples)}")
        
        # Memory growth should be reasonable
        assert total_growth < 50 * 1024 * 1024, f"Total memory growth too high: {total_growth / 1024 / 1024:.2f}MB"
        assert avg_growth_per_session < 1024 * 1024, f"Average session growth too high: {avg_growth_per_session / 1024:.2f}KB"
        
    async def test_connection_pooling_efficiency(self, performance_setup):
        """Test connection pooling efficiency."""
        setup = performance_setup
        
        # Test connection reuse vs creation overhead
        connection_times = []
        
        # Measure connection establishment time
        for i in range(10):
            start_time = time.time()
            
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key=f"pool-test-key-{i}"
            )
            
            await client.connect()
            session_response = await client.create_session()
            
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            
            await client.close_session(session_response["session_id"])
            await client.disconnect()
            
        # Analyze connection efficiency
        avg_connection_time = statistics.mean(connection_times)
        
        print(f"\nConnection Pooling Efficiency:")
        print(f"  Average connection time: {avg_connection_time:.3f}s")
        print(f"  Min connection time: {min(connection_times):.3f}s")
        print(f"  Max connection time: {max(connection_times):.3f}s")
        
        # Connection time should be reasonable
        assert avg_connection_time < 1.0, f"Connection time too slow: {avg_connection_time:.3f}s"


@pytest.mark.performance
class TestScalabilityLimits:
    """Test system scalability limits and breaking points."""
    
    async def test_maximum_concurrent_sessions(self, performance_setup):
        """Test maximum number of concurrent sessions."""
        setup = performance_setup
        
        clients = []
        sessions = []
        max_sessions = 100  # Start with reasonable limit
        
        try:
            for i in range(max_sessions):
                client = AUXClient(
                    url=f"ws://{setup['server'].host}:{setup['server'].port}",
                    api_key=f"scale-test-key-{i}"
                )
                
                try:
                    await client.connect()
                    clients.append(client)
                    
                    session_response = await client.create_session()
                    if session_response["status"] == "success":
                        sessions.append(session_response["session_id"])
                    else:
                        # Hit limit
                        break
                        
                except Exception:
                    # Hit connection limit
                    break
                    
            print(f"\nScalability Test Results:")
            print(f"  Maximum concurrent connections: {len(clients)}")
            print(f"  Maximum concurrent sessions: {len(sessions)}")
            
            # Test that existing sessions still work
            if sessions:
                test_client = clients[0]
                test_session = sessions[0]
                
                response = await test_client.execute_command(
                    session_id=test_session,
                    command={
                        "method": "navigate",
                        "url": "data:text/html,<div>Scalability Test</div>"
                    }
                )
                assert response["status"] == "success", "Existing sessions should still work under load"
                
            # Should handle at least 10 concurrent sessions
            assert len(sessions) >= 10, f"Should support at least 10 concurrent sessions, got {len(sessions)}"
            
        finally:
            # Cleanup
            for i, client in enumerate(clients):
                try:
                    if i < len(sessions):
                        await client.close_session(sessions[i])
                    await client.disconnect()
                except:
                    pass
                    
    async def test_command_queue_limits(self, performance_setup):
        """Test command queue handling under extreme load."""
        setup = performance_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="queue-test-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Navigate to test page
        await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div id='counter'>0</div>"
            }
        )
        
        # Queue many commands rapidly
        queue_size = 1000
        start_time = time.time()
        
        tasks = []
        for i in range(queue_size):
            task = client.execute_command(
                session_id=session_id,
                command={
                    "method": "evaluate",
                    "script": f"document.getElementById('counter').textContent = '{i}'"
                }
            )
            tasks.append(task)
            
        # Execute all commands
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful = len([r for r in results if isinstance(r, dict) and r.get("status") == "success"])
        failed = len([r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("status") == "error")])
        duration = end_time - start_time
        
        print(f"\nCommand Queue Test:")
        print(f"  Queued commands: {queue_size}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Throughput: {successful / duration:.2f} cmd/s")
        
        # Should handle reasonable queue sizes efficiently
        success_rate = successful / queue_size
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.2%}"
        
        await client.close_session(session_id)
        await client.disconnect()
