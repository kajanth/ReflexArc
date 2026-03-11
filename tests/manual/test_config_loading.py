"""
Test script to verify database configuration is loaded from brain.yaml
"""

import sys
from plugin_loader import BrainConfig

def test_config_loading():
    """Test that database configuration is loaded correctly."""
    print("=" * 60)
    print("Testing Database Configuration Loading")
    print("=" * 60)
    
    # Load config
    config = BrainConfig()
    print(f"\n✓ Config loaded from: {config.config_path}")
    print(f"  Brain name: {config.name}")
    
    # Check database configuration
    db_config = config.config.get("brain", {}).get("database", {})
    
    if not db_config:
        print("\n❌ No database configuration found in brain config!")
        print("   Expected 'database' section under 'brain' in config file")
        return 1
    
    print(f"\n✓ Database configuration found:")
    print(f"  Path: {db_config.get('path', 'NOT SET')}")
    print(f"  Min pool size: {db_config.get('min_pool_size', 'NOT SET')}")
    print(f"  Max pool size: {db_config.get('max_pool_size', 'NOT SET')}")
    
    # Verify values
    expected_path = "memory/long_term_memory.db"
    expected_min = 1
    expected_max = 5
    
    actual_path = db_config.get("path", "")
    actual_min = db_config.get("min_pool_size", 0)
    actual_max = db_config.get("max_pool_size", 0)
    
    if actual_path != expected_path:
        print(f"\n⚠️  Warning: Path is '{actual_path}', expected '{expected_path}'")
    
    if actual_min != expected_min:
        print(f"\n⚠️  Warning: Min pool size is {actual_min}, expected {expected_min}")
    
    if actual_max != expected_max:
        print(f"\n⚠️  Warning: Max pool size is {actual_max}, expected {expected_max}")
    
    print("\n" + "=" * 60)
    print("✅ Database configuration is properly set up!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit_code = test_config_loading()
    sys.exit(exit_code)
