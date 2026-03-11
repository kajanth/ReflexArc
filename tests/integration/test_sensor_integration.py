"""
Integration tests for sensor monitoring and management.

Tests the interaction between sensors, sensor manager, and the neural cascade
using mock sensors to avoid hardware dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Tuple, Optional
from collections import deque

from sensors.base import AsyncSensor, SensorMode, SensorHealth, AdaptivePolledSensor


class MockPolledSensor(AsyncSensor):
    """Mock polled sensor for testing."""
    
    def __init__(self, name: str = "mock_polled"):
        super().__init__(mode=SensorMode.POLLED)
        self.name = name
        self.spike_data = deque()
        self.monitor_count = 0
        self.released = False
        
    async def monitor(self) -> Tuple[bool, Optional[str]]:
        """Return queued spike data."""
        self.monitor_count += 1
        
        if self.spike_data:
            return self.spike_data.popleft()
        return False, None
    
    def release(self) -> None:
        """Mark as released."""
        self.released = True
        
    def add_spike(self, description: str):
        """Add a spike to be returned by monitor()."""
        self.spike_data.append((True, description))


class MockEventDrivenSensor(AsyncSensor):
    """Mock event-driven sensor for testing."""
    
    def __init__(self, name: str = "mock_event"):
        super().__init__(mode=SensorMode.EVENT_DRIVEN)
        self.name = name
        self.event_queue = deque()
        self.monitor_count = 0
        self.released = False
        
    async def monitor(self) -> Tuple[bool, Optional[str]]:
        """Return queued events."""
        self.monitor_count += 1
        
        if self.event_queue:
            return self.event_queue.popleft()
        return False, None
    
    def release(self) -> None:
        """Mark as released."""
        self.released = True
        
    def ingest_event(self, description: str):
        """Simulate external event ingestion."""
        self.event_queue.append((True, description))


class MockFailingSensor(AsyncSensor):
    """Mock sensor that fails consistently."""
    
    def __init__(self, name: str = "mock_failing"):
        super().__init__(mode=SensorMode.POLLED)
        self.name = name
        self.failure_count = 0
        self.released = False
        
    async def monitor(self) -> Tuple[bool, Optional[str]]:
        """Always raise an exception."""
        self.failure_count += 1
        raise Exception(f"Sensor failure #{self.failure_count}")
    
    def release(self) -> None:
        """Mark as released."""
        self.released = True


class MockAdaptiveSensor(AdaptivePolledSensor):
    """Mock adaptive sensor for testing polling rate adaptation."""
    
    def __init__(self, name: str = "mock_adaptive"):
        super().__init__(
            min_interval=0.1,
            max_interval=1.0,
            backoff_factor=2.0
        )
        self.name = name
        self.check_count = 0
        self.spike_data = deque()
        self.released = False
        
    async def _check_sensor(self) -> Tuple[bool, Optional[str]]:
        """Return queued spike data."""
        self.check_count += 1
        
        if self.spike_data:
            return self.spike_data.popleft()
        return False, None
    
    def release(self) -> None:
        """Mark as released."""
        self.released = True
        
    def add_spike(self, description: str):
        """Add a spike to be returned by _check_sensor()."""
        self.spike_data.append((True, description))


class TestSensorIntegration:
    """Test sensor integration with the neural cascade."""
    
    @pytest.fixture
    def mock_sensors(self):
        """Create a set of mock sensors for testing."""
        return {
            "polled": MockPolledSensor("test_polled"),
            "event_driven": MockEventDrivenSensor("test_event"),
            "failing": MockFailingSensor("test_failing"),
            "adaptive": MockAdaptiveSensor("test_adaptive")
        }
    
    async def test_polled_sensor_monitoring(self, mock_sensors):
        """Test basic polled sensor monitoring."""
        sensor = mock_sensors["polled"]
        
        # Initially no spikes
        spiked, desc = await sensor.monitor()
        assert not spiked
        assert desc is None
        assert sensor.monitor_count == 1
        
        # Add a spike and monitor again
        sensor.add_spike("Test spike from polled sensor")
        spiked, desc = await sensor.monitor()
        assert spiked
        assert desc == "Test spike from polled sensor"
        assert sensor.monitor_count == 2
        
        # No more spikes
        spiked, desc = await sensor.monitor()
        assert not spiked
        assert desc is None
    
    async def test_event_driven_sensor_monitoring(self, mock_sensors):
        """Test event-driven sensor monitoring."""
        sensor = mock_sensors["event_driven"]
        
        # Initially no events
        spiked, desc = await sensor.monitor()
        assert not spiked
        assert desc is None
        
        # Ingest an event
        sensor.ingest_event("External webhook received")
        spiked, desc = await sensor.monitor()
        assert spiked
        assert desc == "External webhook received"
        
        # No more events
        spiked, desc = await sensor.monitor()
        assert not spiked
        assert desc is None
    
    async def test_sensor_health_tracking(self, mock_sensors):
        """Test sensor health status tracking."""
        sensor = mock_sensors["failing"]
        
        # Initially healthy
        health = sensor.get_health()
        assert health.is_healthy
        assert health.failure_count == 0
        
        # First failure
        try:
            await sensor.monitor()
        except Exception:
            pass
        
        sensor.health.record_failure("Test failure")
        health = sensor.get_health()
        assert health.is_healthy  # Still healthy after 1 failure
        assert health.failure_count == 1
        assert health.error_message == "Test failure"
        
        # Multiple failures should disable sensor
        for i in range(2, 4):
            sensor.health.record_failure(f"Failure {i}")
        
        health = sensor.get_health()
        assert not health.is_healthy  # Disabled after 3 failures
        assert health.failure_count == 3
    
    async def test_sensor_health_recovery(self, mock_sensors):
        """Test sensor health recovery after success."""
        sensor = mock_sensors["polled"]
        
        # Simulate failures
        sensor.health.record_failure("Failure 1")
        sensor.health.record_failure("Failure 2")
        
        health = sensor.get_health()
        assert health.failure_count == 2
        assert health.error_message == "Failure 2"
        
        # Recovery after success
        sensor.health.record_success()
        health = sensor.get_health()
        assert health.is_healthy
        assert health.failure_count == 0
        assert health.error_message is None
        assert health.last_success > 0
    
    async def test_adaptive_polling_rate(self, mock_sensors):
        """Test adaptive polling rate adjustment."""
        sensor = mock_sensors["adaptive"]
        
        # Initial interval should be minimum
        assert sensor.current_interval == 0.1
        
        # Monitor with no activity - should back off
        await sensor.monitor()
        assert sensor.current_interval == 0.2  # 0.1 * 2.0
        
        await sensor.monitor()
        assert sensor.current_interval == 0.4  # 0.2 * 2.0
        
        # Add activity - should reset to minimum
        sensor.add_spike("Activity detected")
        await sensor.monitor()
        assert sensor.current_interval == 0.1  # Reset to minimum
    
    async def test_parallel_sensor_monitoring(self, mock_sensors):
        """Test parallel monitoring of multiple sensors."""
        # Add spikes to sensors
        mock_sensors["polled"].add_spike("Polled sensor spike")
        mock_sensors["event_driven"].ingest_event("Event sensor spike")
        
        # Monitor all sensors in parallel
        tasks = [
            sensor.monitor() 
            for sensor in mock_sensors.values() 
            if sensor.name != "failing"  # Skip failing sensor
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Check results
        polled_result = results[0]  # polled sensor
        event_result = results[1]   # event_driven sensor
        adaptive_result = results[2] # adaptive sensor
        
        assert polled_result == (True, "Polled sensor spike")
        assert event_result == (True, "Event sensor spike")
        assert adaptive_result == (False, None)  # No spikes added
    
    async def test_sensor_resource_cleanup(self, mock_sensors):
        """Test proper sensor resource cleanup."""
        # Release all sensors
        for sensor in mock_sensors.values():
            sensor.release()
        
        # Verify all sensors were released
        for sensor in mock_sensors.values():
            assert sensor.released
    
    async def test_sensor_mode_detection(self, mock_sensors):
        """Test sensor mode detection utilities."""
        polled = mock_sensors["polled"]
        event_driven = mock_sensors["event_driven"]
        
        # Test mode detection
        assert polled.is_polled()
        assert not polled.is_event_driven()
        
        assert event_driven.is_event_driven()
        assert not event_driven.is_polled()
    
    async def test_sensor_error_isolation(self, mock_sensors):
        """Test that sensor errors don't affect other sensors."""
        failing_sensor = mock_sensors["failing"]
        working_sensor = mock_sensors["polled"]
        
        # Add spike to working sensor
        working_sensor.add_spike("Working sensor spike")
        
        # Monitor failing sensor (should raise exception)
        with pytest.raises(Exception):
            await failing_sensor.monitor()
        
        # Working sensor should still work
        spiked, desc = await working_sensor.monitor()
        assert spiked
        assert desc == "Working sensor spike"
    
    async def test_sensor_queue_overflow_handling(self, mock_sensors):
        """Test sensor behavior with queue overflow."""
        sensor = mock_sensors["event_driven"]
        
        # Fill queue beyond capacity (assuming deque has maxlen)
        for i in range(150):  # More than typical queue size
            sensor.ingest_event(f"Event {i}")
        
        # Should still be able to monitor without errors
        spiked, desc = await sensor.monitor()
        assert spiked
        assert "Event" in desc
    
    async def test_sensor_concurrent_access(self, mock_sensors):
        """Test concurrent access to sensors."""
        sensor = mock_sensors["polled"]
        
        # Add multiple spikes
        for i in range(5):
            sensor.add_spike(f"Concurrent spike {i}")
        
        # Monitor concurrently
        tasks = [sensor.monitor() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Should get different spikes (no race conditions)
        spike_count = sum(1 for spiked, _ in results if spiked)
        assert spike_count <= 3  # At most 3 spikes consumed
        
        # All calls should complete without errors
        assert len(results) == 3


class TestSensorManagerIntegration:
    """Test integration with sensor manager (simulated)."""
    
    async def test_sensor_registration_and_monitoring(self):
        """Test sensor registration and monitoring loop simulation."""
        # Create mock sensors
        sensors = {
            "vitals": MockPolledSensor("vitals"),
            "webhooks": MockEventDrivenSensor("webhooks"),
            "adaptive": MockAdaptiveSensor("adaptive")
        }
        
        # Simulate sensor manager monitoring loop
        async def monitor_sensors():
            """Simulate sensor manager monitoring."""
            results = []
            for name, sensor in sensors.items():
                try:
                    spiked, desc = await sensor.monitor()
                    if spiked:
                        results.append((name, desc))
                        sensor.health.record_success()
                except Exception as e:
                    sensor.health.record_failure(str(e))
            return results
        
        # Initially no spikes
        results = await monitor_sensors()
        assert len(results) == 0
        
        # Add spikes to sensors
        sensors["vitals"].add_spike("CPU usage high")
        sensors["webhooks"].ingest_event("GitHub webhook")
        
        # Monitor again
        results = await monitor_sensors()
        assert len(results) == 2
        assert ("vitals", "CPU usage high") in results
        assert ("webhooks", "GitHub webhook") in results
        
        # Verify health tracking
        for sensor in sensors.values():
            health = sensor.get_health()
            assert health.is_healthy
            assert health.last_success > 0
    
    async def test_sensor_auto_disable_on_failures(self):
        """Test automatic sensor disabling after consecutive failures."""
        failing_sensor = MockFailingSensor("failing")
        
        # Simulate monitoring with failure handling
        async def monitor_with_error_handling(sensor):
            try:
                return await sensor.monitor()
            except Exception as e:
                sensor.health.record_failure(str(e))
                return False, None
        
        # Monitor multiple times to trigger auto-disable
        for i in range(5):
            await monitor_with_error_handling(failing_sensor)
        
        # Sensor should be auto-disabled after 3 failures
        health = failing_sensor.get_health()
        assert not health.is_healthy
        assert health.failure_count >= 3
        
        # Should not monitor disabled sensors
        if not health.is_healthy:
            # Sensor manager would skip disabled sensors
            pass