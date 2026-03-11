"""
Pytest configuration and shared fixtures for ReflexArc NSA tests.
"""

import pytest
import asyncio
import tempfile
import os
from typing import Generator, AsyncGenerator

# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Provide a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Clean up
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config():
    """Provide a minimal mock configuration for testing."""
    return {
        "name": "Test Brain",
        "brain": {
            "database": {
                "path": ":memory:",
                "min_pool_size": 1,
                "max_pool_size": 3
            },
            "embedding_model": "all-MiniLM-L6-v2",
            "spike_interval": 1.0,
            "mcp_tool_timeout": 30.0
        },
        "sensors": {},
        "predictions": {},
        "custom_measurers": {},
        "mcp_servers": {}
    }


# Async fixtures
@pytest.fixture
async def mock_hippocampus(temp_db_path):
    """Provide a mock Hippocampus instance for testing."""
    from memory.hippocampus import Hippocampus
    
    async with Hippocampus(
        db_path=temp_db_path,
        min_pool_size=1,
        max_pool_size=2
    ) as hippo:
        yield hippo


@pytest.fixture
def mock_provider():
    """Provide a mock AI provider for testing."""
    from tests.mocks.mock_provider import MockProvider
    return MockProvider()


# Test markers
pytest_plugins = ["pytest_asyncio"]

# Configure asyncio mode
pytestmark = pytest.mark.asyncio