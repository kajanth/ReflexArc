#!/usr/bin/env python3
"""
Example: Adaptive Polling Sensor

Demonstrates how to create and use an adaptive polling sensor that
automatically adjusts its polling rate based on activity.

This example shows:
1. Creating an adaptive sensor
2. Monitoring with automatic interval adjustment
3. Observing the adaptive behavior
4. Integration with SensorManager

Run: python examples/adaptive_sensor_example.py
"""

import asyncio
import time
from typing import Tuple, Optional

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.base import AdaptivePolledSensor, SensorMode
from sensor_manager import SensorManager


class ExampleAdaptiveSensor(AdaptivePolledSensor):
    """
    Example adaptive sensor that simulates activity detection.
    
    This sensor demonstrates adaptive polling by:
    - Starting with 1s polling interval
    - Backing off to 10s when no activity
    - Resetting to 1s when activity detected
    """
    
    def __init__(self):
        super().__init__(
            min_interval=1.0,    # Poll every 1s when active
            max_interval=10.0,   # Poll every 10s when idle
            backoff_factor=1.5   # Increase by 1.5x on no activity
        )
        self.check_count = 0
        self.activity_threshold = 5  # Simulate activity every 5 checks
    
    async def _check_sensor(self) -> Tuple[bool, Optional[str]]:
        """
        Simulate sensor checking logic.
        
        Returns activity every 5th check to demonstrate adaptive behavior.
        """
        self.check_count += 1
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Simulate activity detection every 5 checks
        if self.check_count % self.activity_threshold == 0:
            return True, f"Activity detected (check #{self.check_count})"
        
        return False, None
    
    def release(self) -> None:
        """Clean up resources."""
        print(f"Sensor released after {self.check_count} checks")


async def demonstrate_adaptive_polling():
    """Demonstrate adaptive polling behavior."""
    
    print("=" * 70)
    print("Adaptive Polling Demonstration")
    print("=" * 70)
    print()
    
    sensor = ExampleAdaptiveSensor()
    
    print(f"Initial Configuration:")
    print(f"  Min Interval: {sensor.min_interval}s")
    print(f"  Max Interval: {sensor.max_interval}s")
    print(f"  Backoff Factor: {sensor.backoff_factor}x")
    print(f"  Mode: {sensor.mode.value}")
    print()
    
    print("Starting monitoring loop...")
    print("Watch how the interval adapts based on activity:")
    print()
    
    start_time = time.time()
    last_check_time = start_time
    
    # Monitor for 30 seconds
    while time.time() - start_time < 30:
        # Call monitor (adaptive logic handles timing)
        spiked, description = await sensor.monitor()
        
        current_time = time.time()
        elapsed = current_time - last_check_time
        
        if sensor.check_count > 0:  # Only print if check actually happened
            status = "🔴 SPIKE" if spiked else "⚪ idle"
            print(f"[{current_time - start_time:6.2f}s] {status} | "
                  f"Interval: {sensor.current_interval:5.2f}s | "
                  f"Since last: {elapsed:5.2f}s | "
                  f"Checks: {sensor.check_count}")
            
            if spiked:
                print(f"           └─> {description}")
            
            last_check_time = current_time
        
        # Small sleep to prevent busy loop
        await asyncio.sleep(0.1)
    
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Total Runtime: {time.time() - start_time:.2f}s")
    print(f"  Total Checks: {sensor.check_count}")
    print(f"  Final Interval: {sensor.current_interval:.2f}s")
    print(f"  Health: {'✅ Healthy' if sensor.health.is_healthy else '❌ Unhealthy'}")
    print("=" * 70)
    
    sensor.release()


async def demonstrate_sensor_manager_integration():
    """Demonstrate integration with SensorManager."""
    
    print()
    print("=" * 70)
    print("SensorManager Integration")
    print("=" * 70)
    print()
    
    # Create sensor manager
    mgr = SensorManager()
    
    # Register multiple adaptive sensors
    mgr.register("sensor_1", ExampleAdaptiveSensor(), 
                 emoji="📊", label="Sensor 1")
    mgr.register("sensor_2", ExampleAdaptiveSensor(), 
                 emoji="📈", label="Sensor 2")
    
    print("Registered 2 adaptive sensors")
    print()
    
    # Monitor for 10 seconds
    start_time = time.time()
    spike_count = 0
    
    while time.time() - start_time < 10:
        # Monitor all sensors in parallel
        results = await mgr.monitor_all_parallel()
        
        for sensor_name, spiked, description in results:
            if spiked:
                spike_count += 1
                print(f"[{time.time() - start_time:6.2f}s] {sensor_name}: {description}")
        
        await asyncio.sleep(0.1)
    
    print()
    print(f"Total spikes detected: {spike_count}")
    print()
    
    # Show sensor status
    status = mgr.all_sensors()
    print("Sensor Status:")
    for name, info in status.items():
        print(f"  {info['emoji']} {info['label']}: "
              f"{'✅ Enabled' if info['enabled'] else '❌ Disabled'} | "
              f"Failures: {info['health']['failures']}")
    
    print("=" * 70)
    
    mgr.release_all()


async def demonstrate_health_tracking():
    """Demonstrate health tracking and auto-disable."""
    
    print()
    print("=" * 70)
    print("Health Tracking Demonstration")
    print("=" * 70)
    print()
    
    class FailingSensor(AdaptivePolledSensor):
        """Sensor that fails after a few checks."""
        
        def __init__(self):
            super().__init__(min_interval=0.5, max_interval=5.0)
            self.check_count = 0
        
        async def _check_sensor(self):
            self.check_count += 1
            if self.check_count > 3:
                raise Exception("Simulated sensor failure")
            return False, None
        
        def release(self):
            pass
    
    sensor = FailingSensor()
    
    print("Monitoring a sensor that will fail...")
    print()
    
    for i in range(10):
        try:
            spiked, desc = await sensor.monitor()
            health = sensor.get_health()
            
            print(f"Check {i+1}: "
                  f"{'✅ Success' if health.is_healthy else '❌ Failed'} | "
                  f"Failures: {health.failure_count}")
            
            if not health.is_healthy:
                print(f"  └─> Auto-disabled after {health.failure_count} failures")
                print(f"  └─> Error: {health.error_message}")
                break
        except Exception as e:
            print(f"Check {i+1}: Exception caught: {e}")
        
        await asyncio.sleep(0.6)
    
    print()
    print("Health tracking prevents failed sensors from impacting the system")
    print("=" * 70)


async def main():
    """Run all demonstrations."""
    
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         ReflexArc NSA - Adaptive Polling Demonstration            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Run demonstrations
    await demonstrate_adaptive_polling()
    await demonstrate_sensor_manager_integration()
    await demonstrate_health_tracking()
    
    print()
    print("✅ All demonstrations complete!")
    print()
    print("Key Takeaways:")
    print("  • Adaptive polling reduces CPU usage during idle periods")
    print("  • Intervals automatically adjust based on activity")
    print("  • Health tracking prevents failed sensors from impacting system")
    print("  • Seamless integration with SensorManager")
    print()


if __name__ == "__main__":
    asyncio.run(main())
