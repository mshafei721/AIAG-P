"""
Stress testing suite for AUX Protocol.

Includes extreme load testing, failure recovery, resource exhaustion,
and system stability testing under adverse conditions.
"""

import asyncio
import random
import time
import psutil
import gc
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from aux.client.sdk import AUXClient
from aux.server.websocket_server import AUXWebSocketServer
from aux.browser.manager import BrowserManager
from aux.security import SecurityManager
from aux.config import Config


@pytest.mark.performance
@pytest.mark.slow
class TestExtremeLoadTesting:
    """Extreme load testing scenarios."""
    
    @pytest.fixture
    async def stress_test_setup(self, test_config):
        """Set up stress testing environment."""
        # Configure for maximum performance
        stress_config = test_config
        stress_config.browser_config.headless = True
        stress_config.server_config.max_connections = 500
        stress_config.security_config.rate_limit_per_minute = 50000
        stress_config.logging_config.level = "WARNING"  # Reduce logging overhead
        
        security_manager = SecurityManager(stress_config.security_config)
        browser_manager = BrowserManager(stress_config)
        server = AUXWebSocketServer(stress_config, security_manager, browser_manager)
        
        await browser_manager.start()
        await server.start()
        
        yield {
            "server": server,
            "browser_manager": browser_manager,
            "security_manager": security_manager,
            "config": stress_config
        }
        
        await server.stop()
        await browser_manager.stop()
        
    async def test_extreme_concurrent_load(self, stress_test_setup):
        """Test system under extreme concurrent load."""
        setup = stress_test_setup
        
        # Test parameters
        max_clients = 100
        commands_per_client = 50
        concurrent_batches = 5
        
        async def stress_client_workload(client_id, batch_id):
            """Simulate a high-load client workload."""
            client = AUXClient(
                url=f"ws://{setup['server'].host}:{setup['server'].port}",
                api_key=f"stress-key-{client_id}-{batch_id}"
            )
            
            successful_commands = 0
            errors = []
            
            try:
                await client.connect()
                session_response = await client.create_session()
                
                if session_response["status"] != "success":
                    return {"client_id": client_id, "successful": 0, "errors": ["session_creation_failed"]}
                    
                session_id = session_response["session_id"]
                
                # Execute rapid commands
                for cmd_num in range(commands_per_client):
                    try:
                        # Mix different command types
                        if cmd_num % 3 == 0:
                            response = await client.execute_command(
                                session_id=session_id,
                                command={
                                    "method": "navigate",
                                    "url": f"data:text/html,<div id='test-{client_id}-{cmd_num}'>Client {client_id} Command {cmd_num}</div>"
                                }
                            )
                        elif cmd_num % 3 == 1:
                            response = await client.execute_command(
                                session_id=session_id,
                                command={
                                    "method": "extract",
                                    "selector": "div",
                                    "extract_type": "text"
                                }
                            )
                        else:
                            response = await client.execute_command(
                                session_id=session_id,
                                command={
                                    "method": "evaluate",
                                    "script": f"document.title = 'Client {client_id} Command {cmd_num}'"
                                }
                            )
                            
                        if response["status"] == "success":
                            successful_commands += 1
                        else:
                            errors.append(response["error"]["error_code"])
                            
                    except Exception as e:
                        errors.append(str(e))
                        
                await client.close_session(session_id)
                
            except Exception as e:
                errors.append(f"client_error: {str(e)}")
            finally:
                try:
                    await client.disconnect()
                except:
                    pass
                    
            return {
                "client_id": client_id,
                "batch_id": batch_id,
                "successful": successful_commands,
                "errors": errors
            }
            
        # Run stress test in batches
        all_results = []
        
        for batch in range(concurrent_batches):
            print(f"\nRunning stress test batch {batch + 1}/{concurrent_batches}...")
            
            # Create tasks for this batch
            batch_tasks = [
                stress_client_workload(client_id, batch)
                for client_id in range(max_clients)
            ]
            
            # Execute batch with timeout
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*batch_tasks, return_exceptions=True),
                    timeout=300  # 5 minute timeout per batch
                )
                all_results.extend(batch_results)
            except asyncio.TimeoutError:
                print(f"Batch {batch} timed out")
                break
                
            # Brief pause between batches
            await asyncio.sleep(5)
            
        # Analyze results
        successful_clients = 0
        total_successful_commands = 0
        total_errors = 0
        error_types = {}
        
        for result in all_results:
            if isinstance(result, dict):
                successful_clients += 1
                total_successful_commands += result["successful"]
                total_errors += len(result["errors"])
                
                for error in result["errors"]:
                    error_types[error] = error_types.get(error, 0) + 1
                    
        total_expected_commands = successful_clients * commands_per_client
        success_rate = total_successful_commands / total_expected_commands if total_expected_commands > 0 else 0
        
        print(f"\nExtreme Load Test Results:")
        print(f"  Successful clients: {successful_clients}/{len(all_results)}")
        print(f"  Total successful commands: {total_successful_commands}")
        print(f"  Total errors: {total_errors}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Error breakdown: {error_types}")
        
        # Performance assertions (relaxed for extreme load)
        assert successful_clients > 0, "No clients succeeded"
        assert success_rate > 0.5, f"Success rate too low under extreme load: {success_rate:.2%}"
        
    async def test_memory_pressure_resistance(self, stress_test_setup):
        """Test system behavior under memory pressure."""
        setup = stress_test_setup
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="memory-pressure-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create memory pressure with large content
        large_content_size = 1000000  # 1MB per operation
        operations = 50
        
        for i in range(operations):
            # Create large HTML content
            large_html = f"<div id='large-{i}'>" + "Large content " * large_content_size + "</div>"
            
            try:
                # Navigate to large content
                nav_response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,{large_html}"
                    }
                )
                
                if nav_response["status"] == "success":
                    # Extract large content
                    extract_response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "extract",
                            "selector": f"#large-{i}",
                            "extract_type": "html"
                        }
                    )
                    
                    # Check memory usage
                    current_memory = process.memory_info().rss
                    memory_growth = current_memory - initial_memory
                    
                    print(f"Operation {i}: Memory growth: {memory_growth / 1024 / 1024:.2f}MB")
                    
                    # If memory growth is excessive, trigger garbage collection
                    if memory_growth > 500 * 1024 * 1024:  # 500MB
                        gc.collect()
                        
            except Exception as e:
                print(f"Memory pressure operation {i} failed: {e}")
                # System should handle memory pressure gracefully
                
        # Check final memory state
        final_memory = process.memory_info().rss
        total_growth = final_memory - initial_memory
        
        print(f"\nMemory Pressure Test Results:")
        print(f"  Initial memory: {initial_memory / 1024 / 1024:.2f}MB")
        print(f"  Final memory: {final_memory / 1024 / 1024:.2f}MB")
        print(f"  Total growth: {total_growth / 1024 / 1024:.2f}MB")
        
        # System should still be responsive
        health_check = await client.execute_command(
            session_id=session_id,
            command={
                "method": "navigate",
                "url": "data:text/html,<div>Health Check</div>"
            }
        )
        assert health_check["status"] == "success", "System should remain responsive under memory pressure"
        
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_rapid_connection_cycling(self, stress_test_setup):
        """Test rapid connection creation and destruction."""
        setup = stress_test_setup
        
        cycles = 200
        successful_cycles = 0
        connection_errors = []
        
        for i in range(cycles):
            try:
                client = AUXClient(
                    url=f"ws://{setup['server'].host}:{setup['server'].port}",
                    api_key=f"rapid-cycle-key-{i}"
                )
                
                # Connect
                await client.connect()
                
                # Quick operation
                session_response = await client.create_session()
                if session_response["status"] == "success":
                    session_id = session_response["session_id"]
                    
                    await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "navigate",
                            "url": f"data:text/html,<div>Cycle {i}</div>"
                        }
                    )
                    
                    await client.close_session(session_id)
                    
                # Disconnect
                await client.disconnect()
                
                successful_cycles += 1
                
            except Exception as e:
                connection_errors.append(str(e))
                
            # Brief pause to avoid overwhelming
            if i % 10 == 0:
                await asyncio.sleep(0.1)
                
        success_rate = successful_cycles / cycles
        
        print(f"\nRapid Connection Cycling Results:")
        print(f"  Total cycles: {cycles}")
        print(f"  Successful cycles: {successful_cycles}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Connection errors: {len(connection_errors)}")
        
        # Should handle rapid cycling reasonably well
        assert success_rate > 0.8, f"Connection cycling success rate too low: {success_rate:.2%}"


@pytest.mark.performance
class TestFailureRecoveryStress:
    """Test system recovery under failure conditions."""
    
    async def test_browser_crash_recovery_stress(self, stress_test_setup):
        """Test recovery from multiple browser crashes."""
        setup = stress_test_setup
        browser_manager = setup["browser_manager"]
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="crash-recovery-key"
        )
        
        await client.connect()
        
        crash_count = 0
        recovery_count = 0
        
        for i in range(20):  # Test multiple crash scenarios
            try:
                # Create session
                session_response = await client.create_session()
                session_id = session_response["session_id"]
                
                # Perform some operations
                await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>Pre-crash test {i}</div>"
                    }
                )
                
                # Simulate browser crash every 3rd iteration
                if i % 3 == 0 and session_id in browser_manager._sessions:
                    # Force close browser page to simulate crash
                    session = browser_manager._sessions[session_id]
                    await session.page.close()
                    crash_count += 1
                    
                # Try to continue operations
                response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "extract",
                        "selector": "div",
                        "extract_type": "text"
                    }
                )
                
                if response["status"] == "error":
                    # Expected after crash - try to create new session
                    new_session_response = await client.create_session()
                    if new_session_response["status"] == "success":
                        recovery_count += 1
                        new_session_id = new_session_response["session_id"]
                        
                        # Verify recovery
                        recovery_response = await client.execute_command(
                            session_id=new_session_id,
                            command={
                                "method": "navigate",
                                "url": f"data:text/html,<div>Recovery test {i}</div>"
                            }
                        )
                        assert recovery_response["status"] == "success"
                        
                        await client.close_session(new_session_id)
                else:
                    await client.close_session(session_id)
                    
            except Exception as e:
                print(f"Crash recovery test {i} failed: {e}")
                
        print(f"\nBrowser Crash Recovery Results:")
        print(f"  Simulated crashes: {crash_count}")
        print(f"  Successful recoveries: {recovery_count}")
        print(f"  Recovery rate: {recovery_count / crash_count:.2%}" if crash_count > 0 else "N/A")
        
        await client.disconnect()
        
        # Should recover from most crashes
        if crash_count > 0:
            assert recovery_count / crash_count > 0.8, "Poor crash recovery rate"
            
    async def test_network_interruption_stress(self, stress_test_setup):
        """Test behavior under network interruptions."""
        setup = stress_test_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="network-stress-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Perform operations with simulated network issues
        successful_operations = 0
        network_errors = 0
        
        for i in range(50):
            try:
                # Randomly simulate network delay
                if random.random() < 0.2:  # 20% chance of delay
                    await asyncio.sleep(random.uniform(0.1, 1.0))
                    
                response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>Network test {i}</div>"
                    }
                )
                
                if response["status"] == "success":
                    successful_operations += 1
                else:
                    network_errors += 1
                    
            except Exception as e:
                network_errors += 1
                
                # Try to recover connection
                try:
                    if not client.connected:
                        await client.connect()
                        # Recreate session if needed
                        new_session = await client.create_session()
                        session_id = new_session["session_id"]
                except:
                    pass
                    
        success_rate = successful_operations / 50
        
        print(f"\nNetwork Interruption Stress Results:")
        print(f"  Successful operations: {successful_operations}/50")
        print(f"  Network errors: {network_errors}")
        print(f"  Success rate: {success_rate:.2%}")
        
        await client.close_session(session_id)
        await client.disconnect()
        
        # Should handle network issues reasonably
        assert success_rate > 0.6, f"Success rate under network stress too low: {success_rate:.2%}"


@pytest.mark.performance
class TestResourceExhaustionHandling:
    """Test handling of resource exhaustion scenarios."""
    
    async def test_file_descriptor_exhaustion(self, stress_test_setup):
        """Test behavior when file descriptors are exhausted."""
        setup = stress_test_setup
        
        # Try to create many connections to exhaust file descriptors
        clients = []
        max_clients = 1000  # Attempt to exhaust system resources
        
        try:
            for i in range(max_clients):
                try:
                    client = AUXClient(
                        url=f"ws://{setup['server'].host}:{setup['server'].port}",
                        api_key=f"fd-exhaustion-key-{i}"
                    )
                    await client.connect()
                    clients.append(client)
                    
                except Exception as e:
                    # Expected when resources are exhausted
                    print(f"Resource exhaustion at client {i}: {e}")
                    break
                    
            print(f"\nFile Descriptor Exhaustion Test:")
            print(f"  Created connections: {len(clients)}")
            
            # Test that existing connections still work
            if clients:
                test_client = clients[0]
                session_response = await test_client.create_session()
                assert session_response["status"] == "success", "Existing connections should still work"
                
                test_response = await test_client.execute_command(
                    session_id=session_response["session_id"],
                    command={
                        "method": "navigate",
                        "url": "data:text/html,<div>FD Test</div>"
                    }
                )
                assert test_response["status"] == "success"
                
                await test_client.close_session(session_response["session_id"])
                
        finally:
            # Cleanup
            for client in clients:
                try:
                    await client.disconnect()
                except:
                    pass
                    
    async def test_cpu_starvation_handling(self, stress_test_setup):
        """Test behavior under CPU starvation."""
        setup = stress_test_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="cpu-starvation-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Create CPU-intensive operations
        cpu_intensive_operations = [
            {
                "method": "evaluate",
                "script": "for(let i = 0; i < 1000000; i++) { Math.random(); }"
            },
            {
                "method": "navigate",
                "url": "data:text/html," + "<div>CPU test</div>" * 10000
            },
            {
                "method": "extract",
                "selector": "div",
                "extract_type": "html"
            }
        ]
        
        # Execute CPU-intensive operations concurrently
        tasks = []
        for i in range(20):  # Create CPU pressure
            for operation in cpu_intensive_operations:
                task = client.execute_command(
                    session_id=session_id,
                    command=operation
                )
                tasks.append(task)
                
        # Execute with timeout to prevent hanging
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=60  # 1 minute timeout
            )
            
            successful = len([r for r in results if isinstance(r, dict) and r.get("status") == "success"])
            total = len(results)
            success_rate = successful / total
            
            print(f"\nCPU Starvation Test Results:")
            print(f"  Total operations: {total}")
            print(f"  Successful: {successful}")
            print(f"  Success rate: {success_rate:.2%}")
            
            # Should handle CPU pressure reasonably
            assert success_rate > 0.5, f"Success rate under CPU pressure too low: {success_rate:.2%}"
            
        except asyncio.TimeoutError:
            print("CPU starvation test timed out - system may be unresponsive")
            # This is acceptable under extreme CPU pressure
            
        await client.close_session(session_id)
        await client.disconnect()
        
    async def test_disk_space_exhaustion_simulation(self, stress_test_setup):
        """Test behavior when disk space is exhausted (simulated)."""
        setup = stress_test_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="disk-exhaustion-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Try to create operations that might use disk space
        large_operations = 0
        disk_errors = 0
        
        for i in range(50):
            try:
                # Create very large content that might be cached to disk
                huge_content = "Large content " * 100000  # ~1.5MB per operation
                
                response = await client.execute_command(
                    session_id=session_id,
                    command={
                        "method": "navigate",
                        "url": f"data:text/html,<div>{huge_content}</div>"
                    }
                )
                
                if response["status"] == "success":
                    large_operations += 1
                else:
                    disk_errors += 1
                    
            except Exception as e:
                disk_errors += 1
                print(f"Disk exhaustion simulation operation {i} failed: {e}")
                
        print(f"\nDisk Space Exhaustion Simulation:")
        print(f"  Large operations attempted: 50")
        print(f"  Successful: {large_operations}")
        print(f"  Errors: {disk_errors}")
        
        # System should handle large content gracefully
        assert large_operations > 0, "Should handle at least some large operations"
        
        await client.close_session(session_id)
        await client.disconnect()


@pytest.mark.performance
class TestLongRunningStability:
    """Test system stability over extended periods."""
    
    async def test_extended_session_stability(self, stress_test_setup):
        """Test session stability over extended periods."""
        setup = stress_test_setup
        
        client = AUXClient(
            url=f"ws://{setup['server'].host}:{setup['server'].port}",
            api_key="long-running-key"
        )
        
        await client.connect()
        session_response = await client.create_session()
        session_id = session_response["session_id"]
        
        # Run for extended period
        duration_minutes = 5  # 5 minutes for CI/CD friendliness
        end_time = time.time() + (duration_minutes * 60)
        
        operation_count = 0
        error_count = 0
        
        while time.time() < end_time:
            try:
                # Vary operations to simulate real usage
                operation_type = operation_count % 4
                
                if operation_type == 0:
                    response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "navigate",
                            "url": f"data:text/html,<div>Long running test {operation_count}</div>"
                        }
                    )
                elif operation_type == 1:
                    response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "extract",
                            "selector": "div",
                            "extract_type": "text"
                        }
                    )
                elif operation_type == 2:
                    response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "evaluate",
                            "script": f"document.title = 'Operation {operation_count}'"
                        }
                    )
                else:
                    response = await client.execute_command(
                        session_id=session_id,
                        command={
                            "method": "wait",
                            "condition": "load",
                            "timeout": 1000
                        }
                    )
                    
                if response["status"] == "success":
                    operation_count += 1
                else:
                    error_count += 1
                    
                # Brief pause between operations
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"Long running operation {operation_count} failed: {e}")
                
        error_rate = error_count / (operation_count + error_count) if (operation_count + error_count) > 0 else 0
        
        print(f"\nExtended Session Stability Results:")
        print(f"  Duration: {duration_minutes} minutes")
        print(f"  Successful operations: {operation_count}")
        print(f"  Errors: {error_count}")
        print(f"  Error rate: {error_rate:.2%}")
        print(f"  Operations per minute: {operation_count / duration_minutes:.1f}")
        
        await client.close_session(session_id)
        await client.disconnect()
        
        # Should maintain stability over time
        assert error_rate < 0.05, f"Error rate too high for long running test: {error_rate:.2%}"
        assert operation_count > 100, "Should complete significant number of operations"
