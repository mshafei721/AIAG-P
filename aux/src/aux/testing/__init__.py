"""
AUX Testing Framework.

This module provides comprehensive testing capabilities for the AUX protocol,
including mock agents, test scenario execution, and performance benchmarking.
"""

from .mock_agent import MockAgent, AgentBehavior
from .scenario_runner import ScenarioRunner, TestScenario
from .test_harness import TestHarness, TestResults, TestConfiguration
from .reporting import TestReporter, TestMetrics

__all__ = [
    "MockAgent",
    "AgentBehavior", 
    "ScenarioRunner",
    "TestScenario",
    "TestHarness",
    "TestResults",
    "TestConfiguration",
    "TestReporter",
    "TestMetrics",
]