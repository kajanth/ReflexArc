#!/usr/bin/env python3
"""
Validation test to verify FR-005 requirements are met.

This test verifies:
- FR-005.1: All API endpoints validate input using Pydantic models
- FR-005.3: Spike descriptions are limited to 10KB
- FR-005.4: File paths are validated to prevent directory traversal
- FR-005.5: Metric names are validated against allowed characters
"""

from api.models import SpikeRequest, GoalRequest, SkillRunRequest, SensorToggleRequest
from pydantic import ValidationError

def test_fr_005_3_spike_description_limit():
    """FR-005.3: Spike descriptions SHALL be limited to 10KB."""
    print("\nTesting FR-005.3: Spike description 10KB limit")
    
    # Test exactly 10KB (10240 bytes) - should pass
    try:
        spike = SpikeRequest(description="x" * 10240)
        print("  ✓ 10KB description accepted")
    except ValidationError:
        print("  ✗ 10KB description rejected (should pass)")
        return False
    
    # Test 10KB + 1 byte - should fail
    try:
        spike = SpikeRequest(description="x" * 10241)
        print("  ✗ 10KB+1 description accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ 10KB+1 description rejected")
    
    print("  ✅ FR-005.3 PASSED")
    return True

def test_fr_005_4_directory_traversal():
    """FR-005.4: File paths SHALL be validated to prevent directory traversal."""
    print("\nTesting FR-005.4: Directory traversal prevention")
    
    # Test parent directory reference
    try:
        skill = SkillRunRequest(skill="../etc/passwd")
        print("  ✗ Parent directory reference accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ Parent directory reference rejected")
    
    # Test forward slash
    try:
        skill = SkillRunRequest(skill="skills/malicious")
        print("  ✗ Forward slash accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ Forward slash rejected")
    
    # Test backslash
    try:
        skill = SkillRunRequest(skill="skills\\malicious")
        print("  ✗ Backslash accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ Backslash rejected")
    
    # Test valid skill name
    try:
        skill = SkillRunRequest(skill="system_health_check")
        print("  ✓ Valid skill name accepted")
    except ValidationError:
        print("  ✗ Valid skill name rejected (should pass)")
        return False
    
    print("  ✅ FR-005.4 PASSED")
    return True

def test_fr_005_5_metric_name_validation():
    """FR-005.5: Metric names SHALL be validated against allowed characters."""
    print("\nTesting FR-005.5: Metric name validation")
    
    # Test SQL injection attempt
    try:
        goal = GoalRequest(
            objective="Test",
            metric="cpu; DROP TABLE goals;",
            value=80.0
        )
        print("  ✗ SQL injection accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ SQL injection rejected")
    
    # Test special characters
    try:
        goal = GoalRequest(
            objective="Test",
            metric="cpu@percent",
            value=80.0
        )
        print("  ✗ Special character @ accepted (should fail)")
        return False
    except ValidationError:
        print("  ✓ Special character @ rejected")
    
    # Test valid metric with dots
    try:
        goal = GoalRequest(
            objective="Test",
            metric="system.cpu.percent",
            value=80.0
        )
        print("  ✓ Valid metric with dots accepted")
    except ValidationError:
        print("  ✗ Valid metric with dots rejected (should pass)")
        return False
    
    # Test valid metric with underscores and hyphens
    try:
        goal = GoalRequest(
            objective="Test",
            metric="cpu_percent-avg",
            value=80.0
        )
        print("  ✓ Valid metric with underscores and hyphens accepted")
    except ValidationError:
        print("  ✗ Valid metric rejected (should pass)")
        return False
    
    print("  ✅ FR-005.5 PASSED")
    return True

def test_fr_005_1_pydantic_models():
    """FR-005.1: All API endpoints SHALL validate input using Pydantic models."""
    print("\nTesting FR-005.1: Pydantic model validation")
    
    models = [
        ("SpikeRequest", SpikeRequest, {"description": "test"}),
        ("GoalRequest", GoalRequest, {"objective": "test", "metric": "test", "value": 1.0}),
        ("SkillRunRequest", SkillRunRequest, {"skill": "test"}),
        ("SensorToggleRequest", SensorToggleRequest, {"sensor": "test"}),
    ]
    
    for name, model_class, valid_data in models:
        try:
            instance = model_class(**valid_data)
            print(f"  ✓ {name} validates input correctly")
        except Exception as e:
            print(f"  ✗ {name} failed validation: {e}")
            return False
    
    print("  ✅ FR-005.1 PASSED")
    return True

if __name__ == "__main__":
    print("="*60)
    print("FR-005 Input Validation Requirements Test")
    print("="*60)
    
    results = []
    results.append(("FR-005.1", test_fr_005_1_pydantic_models()))
    results.append(("FR-005.3", test_fr_005_3_spike_description_limit()))
    results.append(("FR-005.4", test_fr_005_4_directory_traversal()))
    results.append(("FR-005.5", test_fr_005_5_metric_name_validation()))
    
    print("\n" + "="*60)
    print("Final Results:")
    print("="*60)
    for req, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {req}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✅ All FR-005 requirements validated successfully!")
    else:
        print("\n❌ Some requirements failed validation!")
    
    exit(0 if all_passed else 1)
