"""
Tests for MCP tool timeout configuration.

Verifies that the timeout setting flows correctly from config
through plugin_loader to NSAOrchestrator.
"""

import pytest
from config.schema import BrainConfigSchema, FullBrainConfigSchema
from plugin_loader import BrainConfig
from brain_core import NSAOrchestrator


def test_brain_config_schema_default_timeout():
    """Test that BrainConfigSchema has correct default timeout."""
    config = BrainConfigSchema(name="Test Brain")
    assert config.mcp_tool_timeout == 30.0


def test_brain_config_schema_custom_timeout():
    """Test that BrainConfigSchema accepts custom timeout."""
    config = BrainConfigSchema(name="Test Brain", mcp_tool_timeout=60.0)
    assert config.mcp_tool_timeout == 60.0


def test_brain_config_schema_timeout_validation_min():
    """Test that timeout validation rejects values below minimum."""
    with pytest.raises(Exception):  # ValidationError
        BrainConfigSchema(name="Test Brain", mcp_tool_timeout=0.5)


def test_brain_config_schema_timeout_validation_max():
    """Test that timeout validation rejects values above maximum."""
    with pytest.raises(Exception):  # ValidationError
        BrainConfigSchema(name="Test Brain", mcp_tool_timeout=500.0)


def test_plugin_loader_timeout_property():
    """Test that BrainConfig exposes mcp_tool_timeout property."""
    config = BrainConfig("config/brain.yaml")
    assert hasattr(config, "mcp_tool_timeout")
    assert isinstance(config.mcp_tool_timeout, float)
    assert config.mcp_tool_timeout > 0


def test_orchestrator_default_timeout():
    """Test that NSAOrchestrator uses default timeout when not specified."""
    brain = NSAOrchestrator(db_path=":memory:")
    assert brain.mcp_tool_timeout == 30.0
    brain.cleanup_models()


def test_orchestrator_custom_timeout():
    """Test that NSAOrchestrator accepts custom timeout."""
    brain = NSAOrchestrator(db_path=":memory:", mcp_tool_timeout=45.0)
    assert brain.mcp_tool_timeout == 45.0
    brain.cleanup_models()


def test_full_config_with_timeout():
    """Test that full config schema validates with timeout setting."""
    config_dict = {
        "brain": {
            "name": "Test Brain",
            "mcp_tool_timeout": 60.0
        },
        "sensors": [],
        "predictions": [],
        "custom_measurers": [],
        "mcp_servers": []
    }
    config = FullBrainConfigSchema(**config_dict)
    assert config.brain.mcp_tool_timeout == 60.0


def test_full_config_without_timeout():
    """Test that full config schema uses default when timeout not specified."""
    config_dict = {
        "brain": {
            "name": "Test Brain"
        },
        "sensors": [],
        "predictions": [],
        "custom_measurers": [],
        "mcp_servers": []
    }
    config = FullBrainConfigSchema(**config_dict)
    assert config.brain.mcp_tool_timeout == 30.0
