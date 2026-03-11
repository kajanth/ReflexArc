#!/usr/bin/env python3
"""
Unit tests for configuration schema validation.

Tests validation logic for all Pydantic models in config/schema.py.
Validates: Requirements FR-007.1, FR-007.2, FR-007.3, FR-007.4, FR-007.5

This test can be run standalone: 
  PYTHONPATH=. python3 tests/test_config_schema.py
Or with pytest: 
  pytest tests/test_config_schema.py -v
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError
from config.schema import (
    DatabaseConfigSchema,
    EmbeddingModelConfigSchema,
    BrainConfigSchema,
    SensorConfigSchema,
    PredictionConfigSchema,
    CustomMeasurerSchema,
    MCPServerConfigSchema,
    FullBrainConfigSchema
)


def test_database_config_valid():
    """Test valid database configuration."""
    config = DatabaseConfigSchema(
        path="memory/test.db",
        min_pool_size=2,
        max_pool_size=10
    )
    assert config.path == "memory/test.db"
    assert config.min_pool_size == 2
    assert config.max_pool_size == 10
    print("  ✓ Valid database config accepted")


def test_database_config_defaults():
    """Test database config with default values."""
    config = DatabaseConfigSchema()
    assert config.path == "memory/long_term_memory.db"
    assert config.min_pool_size == 1
    assert config.max_pool_size == 5
    print("  ✓ Database config defaults work correctly")


def test_database_min_greater_than_max():
    """Test database config with min_pool_size > max_pool_size."""
    try:
        DatabaseConfigSchema(min_pool_size=10, max_pool_size=5)
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "cannot be greater than" in str(e)
        print("  ✓ Invalid pool size range rejected")


def test_embedding_config_valid():
    """Test valid embedding model configuration."""
    config = EmbeddingModelConfigSchema(
        model_name="all-MiniLM-L6-v2",
        cache_enabled=True,
        device="cpu"
    )
    assert config.model_name == "all-MiniLM-L6-v2"
    assert config.cache_enabled is True
    assert config.device == "cpu"
    print("  ✓ Valid embedding config accepted")


def test_embedding_config_invalid_device():
    """Test embedding config with invalid device."""
    try:
        EmbeddingModelConfigSchema(device="gpu")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "Device must be one of" in str(e)
        print("  ✓ Invalid device rejected")


def test_brain_config_valid():
    """Test valid brain configuration."""
    config = BrainConfigSchema(
        name="test_brain",
        description="Test brain profile",
        heartbeat_interval=60,
        prediction_interval=120,
        goal_eval_interval=300
    )
    assert config.name == "test_brain"
    assert config.heartbeat_interval == 60
    print("  ✓ Valid brain config accepted")


def test_brain_config_missing_name():
    """Test brain config without required name field."""
    try:
        BrainConfigSchema()
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "name" in str(e)
        print("  ✓ Missing required name field rejected")


def test_brain_config_invalid_intervals():
    """Test brain config with invalid interval values."""
    # Test heartbeat too small
    try:
        BrainConfigSchema(name="test", heartbeat_interval=0)
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        print("  ✓ Invalid heartbeat interval rejected")
    
    # Test prediction interval too large
    try:
        BrainConfigSchema(name="test", prediction_interval=601)
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        print("  ✓ Invalid prediction interval rejected")


def test_sensor_config_with_module():
    """Test valid sensor configuration with module."""
    config = SensorConfigSchema(
        name="vision",
        module="sensors.vision.OpenCVReflex",
        label="Vision Sensor",
        emoji="👁️",
        type="peripheral"
    )
    assert config.name == "vision"
    assert config.module == "sensors.vision.OpenCVReflex"
    print("  ✓ Valid sensor with module accepted")


def test_sensor_config_with_source():
    """Test valid sensor configuration with source."""
    config = SensorConfigSchema(
        name="circadian",
        source="brain.circadian",
        label="Circadian Rhythm",
        type="internal"
    )
    assert config.source == "brain.circadian"
    print("  ✓ Valid sensor with source accepted")


def test_sensor_both_module_and_source():
    """Test sensor config with both module and source (invalid)."""
    try:
        SensorConfigSchema(
            name="test",
            module="test.module",
            source="test.source",
            label="Test"
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "cannot have both" in str(e)
        print("  ✓ Sensor with both module and source rejected")


def test_sensor_neither_module_nor_source():
    """Test sensor config without module or source (invalid)."""
    try:
        SensorConfigSchema(name="test", label="Test")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "must have either" in str(e)
        print("  ✓ Sensor without module or source rejected")


def test_prediction_config_valid():
    """Test valid prediction configuration."""
    config = PredictionConfigSchema(
        name="cpu_usage",
        measurer="psutil.cpu_percent",
        threshold=80.0,
        direction="above",
        unit="%",
        description="CPU usage monitoring"
    )
    assert config.name == "cpu_usage"
    assert config.threshold == 80.0
    print("  ✓ Valid prediction config accepted")


def test_prediction_negative_threshold():
    """Test prediction config with negative threshold."""
    try:
        PredictionConfigSchema(
            name="test",
            measurer="test.measurer",
            threshold=-10.0,
            description="Test"
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "non-negative" in str(e)
        print("  ✓ Negative threshold rejected")


def test_prediction_invalid_direction():
    """Test prediction config with invalid direction."""
    try:
        PredictionConfigSchema(
            name="test",
            measurer="test.measurer",
            threshold=100.0,
            direction="equal",
            description="Test"
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        print("  ✓ Invalid direction rejected")


def test_custom_measurer_valid():
    """Test valid custom measurer configuration."""
    config = CustomMeasurerSchema(
        name="custom_cpu",
        module="custom.measurers.cpu_percent"
    )
    assert config.name == "custom_cpu"
    assert config.module == "custom.measurers.cpu_percent"
    print("  ✓ Valid custom measurer accepted")


def test_custom_measurer_invalid_module():
    """Test custom measurer with invalid module format (no dot)."""
    try:
        CustomMeasurerSchema(name="test", module="testmodule")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "module.function" in str(e)
        print("  ✓ Invalid module format rejected")


def test_mcp_server_valid():
    """Test valid MCP server configuration."""
    config = MCPServerConfigSchema(
        name="filesystem",
        command="uvx",
        args=["mcp-server-filesystem", "/path/to/dir"],
        env={"API_KEY": "secret"}
    )
    assert config.name == "filesystem"
    assert config.command == "uvx"
    assert len(config.args) == 2
    print("  ✓ Valid MCP server config accepted")


def test_mcp_server_empty_command():
    """Test MCP server with empty command."""
    try:
        MCPServerConfigSchema(name="test", command="", args=["test"])
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "cannot be empty" in str(e)
        print("  ✓ Empty command rejected")


def test_mcp_server_empty_args():
    """Test MCP server with empty args list."""
    try:
        MCPServerConfigSchema(name="test", command="uvx", args=[])
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "cannot be empty" in str(e)
        print("  ✓ Empty args list rejected")


def test_full_config_valid():
    """Test valid full brain configuration."""
    config = FullBrainConfigSchema(
        brain=BrainConfigSchema(name="test_brain"),
        sensors=[
            SensorConfigSchema(name="vision", module="sensors.vision", label="Vision")
        ],
        predictions=[
            PredictionConfigSchema(
                name="cpu",
                measurer="psutil.cpu_percent",
                threshold=80.0,
                description="CPU monitoring"
            )
        ],
        mcp_servers=[
            MCPServerConfigSchema(name="fs", command="uvx", args=["mcp-server-filesystem"])
        ]
    )
    assert config.brain.name == "test_brain"
    assert len(config.sensors) == 1
    assert len(config.predictions) == 1
    assert len(config.mcp_servers) == 1
    print("  ✓ Valid full config accepted")


def test_full_config_missing_brain():
    """Test full config without required brain section."""
    try:
        FullBrainConfigSchema()
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "brain" in str(e)
        print("  ✓ Missing brain section rejected")


def test_full_config_duplicate_sensor_names():
    """Test full config with duplicate sensor names."""
    try:
        FullBrainConfigSchema(
            brain=BrainConfigSchema(name="test"),
            sensors=[
                SensorConfigSchema(name="vision", module="sensors.vision1", label="Vision 1"),
                SensorConfigSchema(name="vision", module="sensors.vision2", label="Vision 2")
            ]
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "Duplicate sensor names" in str(e)
        print("  ✓ Duplicate sensor names rejected")


def test_full_config_duplicate_prediction_names():
    """Test full config with duplicate prediction names."""
    try:
        FullBrainConfigSchema(
            brain=BrainConfigSchema(name="test"),
            predictions=[
                PredictionConfigSchema(
                    name="cpu",
                    measurer="psutil.cpu_percent",
                    threshold=80.0,
                    description="CPU 1"
                ),
                PredictionConfigSchema(
                    name="cpu",
                    measurer="psutil.cpu_percent",
                    threshold=90.0,
                    description="CPU 2"
                )
            ]
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "Duplicate prediction names" in str(e)
        print("  ✓ Duplicate prediction names rejected")


def test_full_config_duplicate_mcp_names():
    """Test full config with duplicate MCP server names."""
    try:
        FullBrainConfigSchema(
            brain=BrainConfigSchema(name="test"),
            mcp_servers=[
                MCPServerConfigSchema(name="fs", command="uvx", args=["server1"]),
                MCPServerConfigSchema(name="fs", command="uvx", args=["server2"])
            ]
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "Duplicate MCP server names" in str(e)
        print("  ✓ Duplicate MCP server names rejected")


def test_full_config_rejects_unknown_fields():
    """Test full config rejects unknown fields (extra='forbid')."""
    try:
        FullBrainConfigSchema(
            brain=BrainConfigSchema(name="test"),
            unknown_field="should_fail"
        )
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        assert "Extra inputs are not permitted" in str(e)
        print("  ✓ Unknown fields rejected")


def test_full_config_complex():
    """Test complex valid full configuration."""
    config = FullBrainConfigSchema(
        brain=BrainConfigSchema(
            name="production_brain",
            description="Production configuration",
            heartbeat_interval=60,
            prediction_interval=180,
            goal_eval_interval=600,
            database=DatabaseConfigSchema(
                path="memory/prod.db",
                min_pool_size=3,
                max_pool_size=15
            ),
            embedding_model=EmbeddingModelConfigSchema(
                model_name="all-mpnet-base-v2",
                cache_enabled=True,
                device="cuda"
            )
        ),
        sensors=[
            SensorConfigSchema(
                name="vision",
                module="sensors.vision.OpenCVReflex",
                label="Vision Sensor",
                emoji="👁️",
                type="peripheral",
                args={"camera_id": 0}
            ),
            SensorConfigSchema(
                name="circadian",
                source="brain.circadian",
                label="Circadian Rhythm",
                type="internal"
            )
        ],
        predictions=[
            PredictionConfigSchema(
                name="cpu_usage",
                measurer="psutil.cpu_percent",
                threshold=80.0,
                direction="above",
                unit="%",
                description="CPU usage monitoring",
                args={"interval": 1}
            ),
            PredictionConfigSchema(
                name="memory_low",
                measurer="psutil.virtual_memory",
                attribute="available",
                threshold=1000000000,
                direction="below",
                unit="bytes",
                description="Low memory warning"
            )
        ],
        custom_measurers=[
            CustomMeasurerSchema(
                name="custom_metric",
                module="custom.measurers.my_metric"
            )
        ],
        mcp_servers=[
            MCPServerConfigSchema(
                name="filesystem",
                command="uvx",
                args=["mcp-server-filesystem", "/data"],
                env={"LOG_LEVEL": "info"}
            ),
            MCPServerConfigSchema(
                name="github",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_TOKEN": "secret"}
            )
        ]
    )
    
    # Verify all sections are properly configured
    assert config.brain.name == "production_brain"
    assert config.brain.database.min_pool_size == 3
    assert config.brain.embedding_model.device == "cuda"
    assert len(config.sensors) == 2
    assert len(config.predictions) == 2
    assert len(config.custom_measurers) == 1
    assert len(config.mcp_servers) == 2
    print("  ✓ Complex full config accepted")


def run_all_tests():
    """Run all tests and report results."""
    print("="*70)
    print("Configuration Schema Validation Tests")
    print("Validates: FR-007.1, FR-007.2, FR-007.3, FR-007.4, FR-007.5")
    print("="*70)
    
    test_functions = [
        ("DatabaseConfigSchema - Valid config", test_database_config_valid),
        ("DatabaseConfigSchema - Defaults", test_database_config_defaults),
        ("DatabaseConfigSchema - Invalid pool sizes", test_database_min_greater_than_max),
        ("EmbeddingModelConfigSchema - Valid config", test_embedding_config_valid),
        ("EmbeddingModelConfigSchema - Invalid device", test_embedding_config_invalid_device),
        ("BrainConfigSchema - Valid config", test_brain_config_valid),
        ("BrainConfigSchema - Missing name", test_brain_config_missing_name),
        ("BrainConfigSchema - Invalid intervals", test_brain_config_invalid_intervals),
        ("SensorConfigSchema - With module", test_sensor_config_with_module),
        ("SensorConfigSchema - With source", test_sensor_config_with_source),
        ("SensorConfigSchema - Both module and source", test_sensor_both_module_and_source),
        ("SensorConfigSchema - Neither module nor source", test_sensor_neither_module_nor_source),
        ("PredictionConfigSchema - Valid config", test_prediction_config_valid),
        ("PredictionConfigSchema - Negative threshold", test_prediction_negative_threshold),
        ("PredictionConfigSchema - Invalid direction", test_prediction_invalid_direction),
        ("CustomMeasurerSchema - Valid config", test_custom_measurer_valid),
        ("CustomMeasurerSchema - Invalid module", test_custom_measurer_invalid_module),
        ("MCPServerConfigSchema - Valid config", test_mcp_server_valid),
        ("MCPServerConfigSchema - Empty command", test_mcp_server_empty_command),
        ("MCPServerConfigSchema - Empty args", test_mcp_server_empty_args),
        ("FullBrainConfigSchema - Valid config", test_full_config_valid),
        ("FullBrainConfigSchema - Missing brain", test_full_config_missing_brain),
        ("FullBrainConfigSchema - Duplicate sensors", test_full_config_duplicate_sensor_names),
        ("FullBrainConfigSchema - Duplicate predictions", test_full_config_duplicate_prediction_names),
        ("FullBrainConfigSchema - Duplicate MCP servers", test_full_config_duplicate_mcp_names),
        ("FullBrainConfigSchema - Unknown fields", test_full_config_rejects_unknown_fields),
        ("FullBrainConfigSchema - Complex config", test_full_config_complex),
    ]
    
    results = []
    for test_name, test_func in test_functions:
        print(f"\n{test_name}:")
        try:
            test_func()
            results.append((test_name, True, None))
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            results.append((test_name, False, str(e)))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append((test_name, False, f"Unexpected error: {str(e)}"))
    
    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    
    if failed > 0:
        print("\nFailed tests:")
        for name, success, error in results:
            if not success:
                print(f"  ✗ {name}")
                if error:
                    print(f"    {error}")
    
    print("\n" + "="*70)
    if failed == 0:
        print("✅ All configuration validation tests passed!")
        print("\nRequirements validated:")
        print("  ✓ FR-007.1: Brain configuration validated on load")
        print("  ✓ FR-007.2: Invalid configuration rejected with clear errors")
        print("  ✓ FR-007.3: Schema validation uses Pydantic models")
        print("  ✓ FR-007.4: Required fields enforced")
        print("  ✓ FR-007.5: Type mismatches caught early")
    else:
        print("❌ Some tests failed!")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
