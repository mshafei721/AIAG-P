# AUX Protocol Testing Framework (M4)

## Overview

The AUX Protocol Testing Framework provides comprehensive testing capabilities for the AUX browser automation protocol. This M4 milestone implementation includes a sophisticated mock agent system, test scenario execution, and detailed reporting capabilities.

## 🏗️ Architecture

### Core Components

1. **MockAgent** - Simulates realistic AI agent behavior
2. **ScenarioRunner** - Executes test scenarios with validation
3. **TestHarness** - Coordinates test execution and manages agents
4. **TestReporter** - Generates comprehensive test reports
5. **CLI Interface** - Command-line tool for test management

### Component Relationships

```
CLI (aux-test) 
    ↓
TestHarness 
    ↓
ScenarioRunner 
    ↓
MockAgent → AUX Server → Browser
    ↓
TestReporter
```

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -e .

# Install additional dependencies for testing
pip install typer pyyaml
```

### Basic Usage

```bash
# Run all scenarios in directory
aux-test run scenarios/

# Run specific scenarios
aux-test run scenario1.yaml scenario2.yaml

# Run with parallel execution
aux-test run scenarios/ --mode parallel --parallel 5

# Run with tags
aux-test run scenarios/ --tag smoke --exclude-tag slow

# Generate performance benchmark
aux-test benchmark scenarios/performance_benchmark.yaml --iterations 5
```

## 📁 Directory Structure

```
aux/
├── src/aux/testing/           # Testing framework core
│   ├── __init__.py           # Framework exports
│   ├── mock_agent.py         # MockAgent implementation
│   ├── scenario_runner.py    # Scenario execution engine
│   ├── test_harness.py       # Test coordination
│   ├── reporting.py          # Report generation
│   ├── cli.py               # Command-line interface
│   └── main.py              # CLI entry point
├── scenarios/               # Test scenario definitions
│   ├── web_navigation_basic.yaml
│   ├── form_interaction_complete.yaml
│   ├── multi_step_workflow.yaml
│   ├── error_handling_resilience.yaml
│   ├── performance_benchmark.yaml
│   └── advanced_interaction.yaml
├── fixtures/               # Test configurations and data
│   ├── test_config.yaml   # Default test configuration
│   └── performance_config.yaml # Performance testing config
└── test_m4_integration.py # M4 validation test
```

## 🤖 MockAgent Features

### Realistic Behavior Simulation

- **Human-like Timing**: Configurable thinking delays and typing speeds
- **Natural Variations**: Random timing variations for realistic behavior
- **Error Recovery**: Automatic retry logic with exponential backoff
- **State Tracking**: Comprehensive execution state monitoring

### Configuration Options

```python
behavior = AgentBehavior(
    thinking_delay_range=(0.5, 2.0),    # Seconds
    typing_speed_range=(80, 150),       # Characters per minute
    action_delay_range=(0.2, 0.8),      # Seconds between actions
    retry_attempts=3,
    error_recovery_enabled=True,
    validate_responses=True,
    add_natural_delays=True,
    variation_factor=0.3                # 30% timing variation
)
```

### Validation System

```python
# Add custom validation rules
agent.add_validation_rule(ValidationRule(
    name="response_time",
    condition=lambda result: result.get("execution_time", 0) < 5.0,
    error_message="Response took too long"
))
```

## 📝 Test Scenario Format

### YAML Scenario Structure

```yaml
name: "Test Scenario Name"
description: "Description of what this scenario tests"
tags: ["tag1", "tag2"]
timeout: 120

config:
  behavior:
    thinking_delay_range: [0.5, 1.5]
    add_natural_delays: true

setup:
  clear_cache: true
  wait_time: 1

steps:
  - name: "Step name"
    command:
      method: "navigate"
      url: "https://example.com"
      wait_until: "load"
      timeout: 10000
    expected_result:
      success: true
    assertions:
      - type: "equals"
        field: "success"
        expected: true

teardown:
  reset_browser: false
  wait_time: 0.5
```

### Command Types

1. **navigate** - Navigate to URLs
2. **click** - Click on elements
3. **fill** - Fill form inputs
4. **extract** - Extract data from elements
5. **wait** - Wait for conditions

### Assertion Types

- `equals` - Exact value comparison
- `contains` - String/array containment
- `not_empty` - Non-empty validation
- `greater_than` / `less_than` - Numeric comparisons

## 🎯 Test Execution Modes

### Sequential Execution

```bash
aux-test run scenarios/ --mode sequential
```

- Executes scenarios one by one
- Easier debugging and troubleshooting
- Full agent state isolation

### Parallel Execution

```bash
aux-test run scenarios/ --mode parallel --parallel 5
```

- Executes multiple scenarios simultaneously
- Faster overall execution
- Configurable concurrency limits

## 📊 Reporting System

### Report Types

1. **HTML Report** - Interactive web-based report
2. **JSON Metrics** - Machine-readable test data
3. **Detailed Logs** - Comprehensive execution logs

### Report Contents

- Executive summary with success rates
- Detailed scenario results
- Performance metrics and timing analysis
- Error analysis and debugging information
- Agent behavior metrics

### Sample Report Structure

```json
{
  "summary": {
    "total_scenarios": 5,
    "passed_scenarios": 4,
    "failed_scenarios": 1,
    "success_rate": 0.8,
    "total_execution_time": 45.2
  },
  "scenarios": [...],
  "metrics": {...}
}
```

## ⚡ Performance Benchmarking

### Benchmark Configuration

```yaml
# Performance-optimized behavior
default_behavior:
  thinking_delay_range: [0.0, 0.1]
  typing_speed_range: [500, 1000]
  add_natural_delays: false
```

### Running Benchmarks

```bash
# Single benchmark run
aux-test benchmark performance_scenario.yaml

# Multiple iterations
aux-test benchmark scenarios/ --iterations 10

# Save detailed results
aux-test benchmark scenarios/ --output ./benchmark_results/
```

## 🔧 Configuration Management

### Configuration Files

```yaml
# test_config.yaml
server_url: "ws://localhost:8765"
max_parallel_agents: 3
execution_timeout: 300
stop_on_first_failure: false

default_behavior:
  thinking_delay_range: [0.5, 1.5]
  error_recovery_enabled: true
  validate_responses: true

scenario_filter_tags: ["smoke", "critical"]
exclude_tags: ["skip", "manual-only"]

save_detailed_logs: true
generate_html_report: true
```

### Using Configuration Files

```bash
aux-test run scenarios/ --config fixtures/test_config.yaml
```

## 📋 Available Test Scenarios

### 1. Basic Web Navigation (`web_navigation_basic.yaml`)
- Simple page navigation
- Content extraction
- Basic element interaction
- **Duration**: ~15 seconds
- **Tags**: navigation, basic, smoke

### 2. Complete Form Interaction (`form_interaction_complete.yaml`)
- Complex form filling
- Input validation
- Form submission
- **Duration**: ~45 seconds
- **Tags**: forms, interaction, comprehensive

### 3. Multi-Step Workflow (`multi_step_workflow.yaml`)
- Search functionality
- Navigation between pages
- State preservation
- **Duration**: ~60 seconds
- **Tags**: workflow, multi-step, complex

### 4. Error Handling Resilience (`error_handling_resilience.yaml`)
- Error condition testing
- Recovery mechanisms
- Edge case handling
- **Duration**: ~40 seconds
- **Tags**: error-handling, resilience, edge-cases

### 5. Performance Benchmark (`performance_benchmark.yaml`)
- Speed optimization testing
- Minimal delay configuration
- Performance metrics
- **Duration**: ~20 seconds
- **Tags**: performance, benchmark, speed

### 6. Advanced Interaction (`advanced_interaction.yaml`)
- Complex selectors
- Advanced wait conditions
- State tracking
- **Duration**: ~35 seconds
- **Tags**: advanced, interaction, wait-conditions

## 🛠️ Development and Debugging

### Running Integration Tests

```bash
# Validate M4 implementation
python test_m4_integration.py

# Check scenario validity
aux-test validate scenarios/*.yaml

# List available scenarios
aux-test list-scenarios scenarios/
```

### Creating New Scenarios

```bash
# Create from template
aux-test create-scenario "My Test" --template basic

# Create form-based scenario
aux-test create-scenario "Form Test" --template form
```

### Debugging Failed Tests

1. **Enable Verbose Logging**:
   ```bash
   aux-test run scenario.yaml --verbose
   ```

2. **Check Detailed Logs**:
   ```bash
   # Logs saved to ./test_results/detailed_logs.txt
   ```

3. **Review HTML Report**:
   ```bash
   # Report saved to ./test_results/test_report.html
   ```

## 🔍 Validation and Quality Assurance

### Scenario Validation

```bash
# Validate all scenarios
aux-test validate scenarios/

# Validate specific files
aux-test validate scenario1.yaml scenario2.yaml
```

### Integration Testing

```bash
# Run M4 integration test suite
python test_m4_integration.py
```

### Performance Validation

```bash
# Benchmark all scenarios
aux-test benchmark scenarios/ --iterations 3

# Performance-focused scenarios only
aux-test run scenarios/ --tag performance
```

## 🚨 Error Handling and Recovery

### Agent Error Recovery

- **Automatic Retries**: Configurable retry attempts with exponential backoff
- **State Recovery**: Agent state restoration after failures
- **Graceful Degradation**: Continue execution when possible
- **Error Logging**: Comprehensive error tracking and reporting

### Common Error Scenarios

1. **Element Not Found**: Retry with different selectors
2. **Timeout Errors**: Increase timeout or retry
3. **Network Issues**: Automatic reconnection attempts
4. **Browser Crashes**: Session recovery and restart

## 📈 Metrics and Analytics

### Collected Metrics

- **Execution Times**: Per-command and scenario timing
- **Success Rates**: Pass/fail ratios
- **Error Frequencies**: Common failure patterns
- **Performance Trends**: Speed and efficiency metrics
- **Agent Behavior**: Thinking times, typing speeds, delays

### Metric Analysis

```python
# Access metrics programmatically
results = await harness.run_scenarios(scenarios)
metrics = results.metrics

print(f"Success Rate: {metrics.success_rate:.1%}")
print(f"Avg Execution Time: {metrics.average_scenario_time:.2f}s")
print(f"Total Steps: {metrics.total_steps}")
```

## 🔮 Future Enhancements

### Planned Features

1. **Visual Testing**: Screenshot comparison capabilities
2. **Load Testing**: Multi-agent stress testing
3. **CI/CD Integration**: GitHub Actions and Jenkins support
4. **Real-time Monitoring**: Live test execution dashboards
5. **Advanced Analytics**: ML-powered failure prediction

### Extension Points

1. **Custom Commands**: Add new AUX protocol commands
2. **Validation Rules**: Custom assertion and validation logic
3. **Report Formats**: Additional output formats (PDF, CSV)
4. **Agent Behaviors**: Custom behavior simulation patterns

## 🤝 Contributing

### Adding New Scenarios

1. Create YAML scenario file in `scenarios/`
2. Follow the established format and naming conventions
3. Include comprehensive assertions and validations
4. Test scenario validity: `aux-test validate new_scenario.yaml`

### Extending the Framework

1. **New Agent Behaviors**: Extend `AgentBehavior` class
2. **Custom Validators**: Implement `ValidationRule` subclasses
3. **Report Generators**: Add new `TestReporter` methods
4. **CLI Commands**: Extend the Typer CLI application

## 📞 Support and Troubleshooting

### Common Issues

1. **Server Connection**: Ensure AUX server is running on specified port
2. **Scenario Loading**: Check YAML syntax and required fields
3. **Permission Errors**: Verify write permissions for output directories
4. **Memory Usage**: Monitor memory consumption during large test runs

### Getting Help

- Check the detailed logs in `session.log`
- Review HTML reports for visual debugging
- Use `--verbose` flag for detailed output
- Validate scenarios before execution

---

## Summary

The AUX Protocol Testing Framework (M4) provides a comprehensive, production-ready solution for testing browser automation protocols. With realistic agent behavior simulation, flexible scenario definitions, and detailed reporting capabilities, it enables thorough validation of AUX protocol implementations and serves as a foundation for continuous testing and quality assurance.

The framework successfully delivers on all M4 requirements:

✅ **Mock Agent Implementation** - Realistic behavior simulation and validation  
✅ **Test Harness Architecture** - Comprehensive test coordination and execution  
✅ **Scenario System** - Flexible YAML/JSON scenario definitions  
✅ **Reporting System** - Detailed HTML, JSON, and text reports  
✅ **CLI Interface** - Full-featured command-line tool  
✅ **Performance Benchmarking** - Speed and efficiency testing  
✅ **Integration Testing** - End-to-end validation suite  

The framework is ready for production use and provides a solid foundation for future AUX protocol development and testing.