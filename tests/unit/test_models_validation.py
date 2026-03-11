#!/usr/bin/env python3
"""Quick validation test for API models."""

from api.models import SpikeRequest, GoalRequest, SkillRunRequest, SensorToggleRequest
from pydantic import ValidationError

def test_spike_request():
    """Test SpikeRequest validation."""
    # Valid request
    try:
        spike = SpikeRequest(description="Test spike", sense_type="api", priority="normal")
        print("✓ Valid SpikeRequest created successfully")
    except Exception as e:
        print(f"✗ SpikeRequest failed: {e}")
        return False
    
    # Invalid: empty description
    try:
        spike = SpikeRequest(description="   ")
        print("✗ Empty description should have failed")
        return False
    except ValidationError:
        print("✓ Empty description validation works")
    
    return True

def test_goal_request():
    """Test GoalRequest validation."""
    # Valid request
    try:
        goal = GoalRequest(objective="Keep CPU low", metric="cpu_percent", value=80.0)
        print("✓ Valid GoalRequest created successfully")
    except Exception as e:
        print(f"✗ GoalRequest failed: {e}")
        return False
    
    # Invalid: injection attempt
    try:
        goal = GoalRequest(objective="Test", metric="cpu; DROP TABLE goals;", value=80.0)
        print("✗ Metric injection should have failed")
        return False
    except ValidationError:
        print("✓ Metric injection validation works")
    
    return True

def test_skill_run_request():
    """Test SkillRunRequest validation."""
    # Valid request
    try:
        skill = SkillRunRequest(skill="system_health_check", data="Test data")
        print("✓ Valid SkillRunRequest created successfully")
    except Exception as e:
        print(f"✗ SkillRunRequest failed: {e}")
        return False
    
    # Invalid: directory traversal
    try:
        skill = SkillRunRequest(skill="../../../etc/passwd")
        print("✗ Directory traversal should have failed")
        return False
    except ValidationError:
        print("✓ Directory traversal validation works")
    
    return True

def test_sensor_toggle_request():
    """Test SensorToggleRequest validation."""
    # Valid request
    try:
        sensor = SensorToggleRequest(sensor="vision", action="toggle")
        print("✓ Valid SensorToggleRequest created successfully")
    except Exception as e:
        print(f"✗ SensorToggleRequest failed: {e}")
        return False
    
    # Invalid: invalid action
    try:
        sensor = SensorToggleRequest(sensor="vision", action="destroy")
        print("✗ Invalid action should have failed")
        return False
    except ValidationError:
        print("✓ Invalid action validation works")
    
    return True

if __name__ == "__main__":
    print("Testing API Models Validation\n")
    
    results = []
    results.append(("SpikeRequest", test_spike_request()))
    results.append(("GoalRequest", test_goal_request()))
    results.append(("SkillRunRequest", test_skill_run_request()))
    results.append(("SensorToggleRequest", test_sensor_toggle_request()))
    
    print("\n" + "="*50)
    print("Test Results:")
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✅ All validation tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    exit(0 if all_passed else 1)
