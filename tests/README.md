# ReflexArc NSA Test Suite

This directory contains the comprehensive test suite for the ReflexArc NSA (Neural Sensory Architecture) system.

## Directory Structure

```
tests/
├── __init__.py                 # Tests package
├── conftest.py                 # Pytest configuration and shared fixtures
├── README.md                   # This file
├── unit/                       # Unit tests for individual components
│   ├── __init__.py
│   ├── layers/                 # Tests for neural cascade layers
│   │   └── __init__.py
│   ├── providers/              # Tests for AI provider implementations
│   │   └── __init__.py
│   ├── sensors/                # Tests for sensor implementations
│   │   └── __init__.py
│   ├── test_api_models.py      # API request/response model validation
│   ├── test_config_schema.py   # Configuration schema validation
│   ├── test_mcp_timeout_config.py  # MCP timeout configuration
│   ├── test_model_cleanup.py   # Embedding model cleanup
│   ├── test_models_validation.py   # Additional model validation
│   ├── test_requirements_validation.py  # Requirements validation
│   └── test_validation_error_handling.py  # Error handling validation
├── integration/                # Integration tests for full system flows
│   ├── __init__.py
│   ├── api/                    # API endpoint integration tests
│   │   └── __init__.py
│   ├── cascade/                # Neural cascade flow tests
│   │   └── __init__.py
│   ├── test_hippocampus_pooling.py  # Database connection pooling
│   └── test_mcp_error_isolation.py  # MCP tool error isolation
├── mocks/                      # Mock objects for testing
│   ├── __init__.py
│   └── mock_provider.py        # Mock AI provider for cost-free testing
├── manual/                     # Manual test scripts for interactive testing
│   ├── __init__.py
│   ├── test_cleanup_functions.py   # Verify cleanup function signatures
│   ├── test_config_loading.py     # Test configuration loading
│   ├── test_mcp.py                # Manual MCP testing
│   ├── test_model_cleanup_manual.py  # Manual model cleanup testing
│   ├── test_pooling_manual.py     # Manual connection pooling testing
│   ├── test_prediction.py         # Manual prediction testing
│   └── verify_domain.py           # Domain verification
└── property/                   # Property-based tests using hypothesis
    └── __init__.py
```

## Test Categories

### Unit Tests (`tests/unit/`)
Test individual components in isolation:
- **API Models**: Pydantic validation for request/response models
- **Config Schema**: Configuration validation and error handling
- **Model Cleanup**: Embedding model resource management
- **Sensor Base**: Async sensor interface and health monitoring
- **MCP Configuration**: Tool timeout and configuration validation

### Integration Tests (`tests/integration/`)
Test full system flows and component interactions:
- **Hippocampus Pooling**: Database connection pooling functionality
- **MCP Error Isolation**: Tool failure isolation and error handling
- **Cascade Flows**: End-to-end neural cascade processing
- **API Endpoints**: Full HTTP API integration testing

### Mock Objects (`tests/mocks/`)
Provide test doubles for external dependencies:
- **Mock Provider**: AI provider that returns deterministic responses without API costs
- **Mock Sensors**: Simulated sensor data for testing
- **Mock MCP Tools**: Simulated external tools

### Manual Tests (`tests/manual/`)
Interactive test scripts for manual verification:
- **Connection Pooling**: Manual verification of database pooling
- **Model Cleanup**: Manual verification of resource cleanup
- **Configuration Loading**: Manual config validation
- **Domain Verification**: Manual domain-specific testing

### Property-Based Tests (`tests/property/`)
Use Hypothesis to test system properties across many inputs:
- **RAS Habituation**: Test novelty detection properties
- **Cost Optimization**: Verify cost minimization properties
- **Event Bus Ordering**: Test event ordering invariants

## Running Tests

### Prerequisites
```bash
pip install pytest pytest-asyncio pytest-cov hypothesis
```

### Run All Tests
```bash
# Run all tests with coverage
pytest tests/ --cov=. --cov-report=html

# Run with verbose output
pytest tests/ -v

# Run specific test category
pytest tests/unit/ -v
pytest tests/integration/ -v
```

### Run Specific Tests
```bash
# Run specific test file
pytest tests/unit/test_api_models.py -v

# Run specific test function
pytest tests/unit/test_config_schema.py::test_valid_brain_config -v

# Run tests matching pattern
pytest tests/ -k "test_validation" -v
```

### Manual Tests
```bash
# Run manual tests (require full environment)
cd tests/manual/
python test_pooling_manual.py
python test_model_cleanup_manual.py
python test_config_loading.py
```

## Test Configuration

### Fixtures (`conftest.py`)
Shared test fixtures available to all tests:
- `temp_db_path`: Temporary database file for testing
- `temp_dir`: Temporary directory for test files
- `mock_config`: Minimal configuration for testing
- `mock_hippocampus`: Async Hippocampus instance
- `mock_provider`: Mock AI provider for cost-free testing

### Environment Variables
Set these for testing:
```bash
export PYTHONPATH=.
export NSA_BRAIN_CONFIG=config/brain.yaml
export TOKENIZERS_PARALLELISM=false
```

## Writing New Tests

### Unit Test Example
```python
import pytest
from your_module import YourClass

def test_your_function():
    """Test description following docstring format."""
    # Arrange
    input_data = "test input"
    
    # Act
    result = your_function(input_data)
    
    # Assert
    assert result == "expected output"

@pytest.mark.asyncio
async def test_async_function(mock_hippocampus):
    """Test async function with fixture."""
    result = await async_function(mock_hippocampus)
    assert result is not None
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_full_cascade_flow(mock_provider, temp_db_path):
    """Test complete spike processing through neural cascade."""
    # Setup system with mock provider
    brain = NSAOrchestrator(db_path=temp_db_path)
    brain.router.add_provider(mock_provider)
    
    # Process spike
    result = await brain.process_spike("test spike", "system")
    
    # Verify cascade execution
    assert result["decision"] in ["REFLEX", "TEMPLATE", "COMPLEX"]
    assert "cost" in result
```

### Property-Based Test Example
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
def test_spike_processing_properties(spike_text):
    """Test that spike processing maintains invariants."""
    result = process_spike(spike_text)
    
    # Properties that should always hold
    assert result["cost"] >= 0
    assert result["latency_ms"] >= 0
    assert result["decision"] in ["REFLEX", "TEMPLATE", "COMPLEX"]
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for core modules
- **Integration Tests**: Cover all major system flows
- **Property Tests**: Verify key system invariants
- **Manual Tests**: Interactive verification of complex scenarios

## Continuous Integration

Tests run automatically on:
- Pull requests
- Main branch commits
- Nightly builds

CI pipeline includes:
- Linting (flake8, black, mypy)
- Unit and integration tests
- Coverage reporting
- Security scanning (bandit, safety)

## Bio-Inspired Testing Philosophy

Following the system's bio-inspired architecture, our testing strategy mirrors biological systems:

- **Reflexive Testing** (Unit): Fast, isolated tests like neural reflexes
- **Cognitive Testing** (Integration): Complex reasoning tests like cortical processing
- **Adaptive Testing** (Property): Tests that adapt to different inputs like biological adaptation
- **Memory Testing** (Persistence): Tests for long-term memory and learning

This ensures our digital nervous system maintains the same reliability and robustness as biological neural networks.