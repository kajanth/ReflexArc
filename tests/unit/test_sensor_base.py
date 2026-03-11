"""
Unit tests for sensors/base.py

Tests the async sensor interface, health monitoring, and adaptive polling.
"""

import pytest
import asyncio
import time
from sensors.base import (
    AsyncSensor,
    AdaptivePolledSensor,
    SensorMode,
    SensorHealth
)


class MockPolledSensor(AsyncSensor):
    """Mock polled sensor for testing."""
    
    def __init__(self):
        super().__init__(mode=SensorMode.POLLED)
        self.monitor_count = 0
        self.should_spike = False
        self.released = False
    
    async def monitor(self):
        self.monitor_count += 1
        if self.should_spike:
            return True, "Mock spike detected"
        return False, None
    
    def release(self):
        self.released = True


class MockEventDrivenSensor(AsyncSensor):
    """Mock event-driven sensor for testing."""
    
    def __init__(self):
        super().__init__(mode=SensorMode.EVENT_DRIVEN)
        self.events = []
        self.released = False
    
    def ingest_event(self, data):
        """Simulate receiving an event."""
        self.events.append(data)
    
    async def monitor(self):
        if not self.events:
            return False, None
        event = self.events.pop(0)
        return True, f"Event: {event}"
    
    def release(self):
        self.events.clear()
        self.released = True


class MockAdaptiveSensor(AdaptivePolledSensor):
    """Mock adaptive sensor for testing."""
    
    def __init__(self):
        super().__init__(
            min_interval=0.1,
            max_interval=1.0,
            backoff_factor=2.0
        )
        self.check_count = 0
        self.should_spike = False
    
    async def _check_sensor(self):
        self.check_count += 1
        if self.should_spike:
            return True, "Adaptive spike"
        return False, None
    
    def release(self):
        pass


# --- SensorHealth Tests ---

def test_sensor_health_initial_state():
    """Test that SensorHealth starts in healthy state."""
    health = SensorHealth()
    assert health.is_healthy is True
    assert health.failure_count == 0
    assert health.error_message is None


def test_sensor_health_record_success():
    """Test recording successful operations."""
    health = SensorHealth()
    health.failure_count = 2
    health.error_message = "Previous error"
    
    health.record_success()
    
    assert health.is_healthy is True
    assert health.failure_count == 0
    assert health.error_message is None
    assert health.last_success > 0


def test_sensor_health_record_failure():
    """Test recording failed operations."""
    health = SensorHealth()
    
    health.record_failure("Error 1")
    assert health.failure_count == 1
    assert health.is_healthy is True  # Still healthy after 1 failure
    
    health.record_failure("Error 2")
    assert health.failure_count == 2
    assert health.is_healthy is True  # Still healthy after 2 failures
    
    health.record_failure("Error 3")
    assert health.failure_count == 3
    assert health.is_healthy is False  # Auto-disabled after 3 failures (FR-010.4)
    assert health.error_message == "Error 3"


# --- AsyncSensor Tests ---

@pytest.mark.asyncio
async def test_polled_sensor_mode():
    """Test polled sensor mode detection."""
    sensor = MockPolledSensor()
    assert sensor.mode == SensorMode.POLLED
    assert sensor.is_polled() is True
    assert sensor.is_event_driven() is False


@pytest.mark.asyncio
async def test_event_driven_sensor_mode():
    """Test event-driven sensor mode detection."""
    sensor = MockEventDrivenSensor()
    assert sensor.mode == SensorMode.EVENT_DRIVEN
    assert sensor.is_event_driven() is True
    assert sensor.is_polled() is False


@pytest.mark.asyncio
async def test_polled_sensor_monitor():
    """Test polled sensor monitoring."""
    sensor = MockPolledSensor()
    
    # No spike initially
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert desc is None
    assert sensor.monitor_count == 1
    
    # Trigger spike
    sensor.should_spike = True
    spiked, desc = await sensor.monitor()
    assert spiked is True
    assert desc == "Mock spike detected"
    assert sensor.monitor_count == 2


@pytest.mark.asyncio
async def test_event_driven_sensor_monitor():
    """Test event-driven sensor monitoring."""
    sensor = MockEventDrivenSensor()
    
    # No events initially
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert desc is None
    
    # Ingest events
    sensor.ingest_event("event1")
    sensor.ingest_event("event2")
    
    # Should return first event
    spiked, desc = await sensor.monitor()
    assert spiked is True
    assert desc == "Event: event1"
    
    # Should return second event
    spiked, desc = await sensor.monitor()
    assert spiked is True
    assert desc == "Event: event2"
    
    # No more events
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert desc is None


@pytest.mark.asyncio
async def test_sensor_release():
    """Test sensor resource cleanup."""
    sensor = MockPolledSensor()
    assert sensor.released is False
    
    sensor.release()
    assert sensor.released is True


@pytest.mark.asyncio
async def test_sensor_health_tracking():
    """Test that sensors track their health."""
    sensor = MockPolledSensor()
    health = sensor.get_health()
    
    assert health.is_healthy is True
    assert health.failure_count == 0


# --- AdaptivePolledSensor Tests ---

@pytest.mark.asyncio
async def test_adaptive_sensor_initial_interval():
    """Test adaptive sensor starts with minimum interval."""
    sensor = MockAdaptiveSensor()
    assert sensor.current_interval == 0.1  # min_interval


@pytest.mark.asyncio
async def test_adaptive_sensor_backoff():
    """Test adaptive sensor backs off when no activity."""
    sensor = MockAdaptiveSensor()
    
    # First poll should execute
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert sensor.check_count == 1
    assert sensor.current_interval == 0.2  # 0.1 * 2.0 backoff
    
    # Immediate second poll should be skipped (interval not elapsed)
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert sensor.check_count == 1  # Not incremented
    
    # Wait for interval and poll again
    await asyncio.sleep(0.25)
    spiked, desc = await sensor.monitor()
    assert spiked is False
    assert sensor.check_count == 2
    assert sensor.current_interval == 0.4  # 0.2 * 2.0 backoff


@pytest.mark.asyncio
async def test_adaptive_sensor_activity_resets_interval():
    """Test adaptive sensor resets to min interval on activity."""
    sensor = MockAdaptiveSensor()
    
    # Back off the interval
    await sensor.monitor()
    await asyncio.sleep(0.25)
    await sensor.monitor()
    assert sensor.current_interval == 0.4  # Backed off
    
    # Trigger activity
    sensor.should_spike = True
    await asyncio.sleep(0.5)
    spiked, desc = await sensor.monitor()
    assert spiked is True
    assert sensor.current_interval == 0.1  # Reset to min_interval


@pytest.mark.asyncio
async def test_adaptive_sensor_max_interval():
    """Test adaptive sensor respects maximum interval."""
    sensor = MockAdaptiveSensor()
    
    # Keep polling with no activity to reach max interval
    for _ in range(10):
        await sensor.monitor()
        await asyncio.sleep(sensor.current_interval + 0.1)
    
    # Should cap at max_interval
    assert sensor.current_interval <= 1.0  # max_interval


@pytest.mark.asyncio
async def test_adaptive_sensor_parallel_monitoring():
    """Test that adaptive sensors work correctly with parallel monitoring."""
    sensor = MockAdaptiveSensor()
    
    # Simulate parallel monitoring (like asyncio.gather)
    results = await asyncio.gather(
        sensor.monitor(),
        sensor.monitor(),
        sensor.monitor()
    )
    
    # Only first call should execute due to interval
    spikes = [r[0] for r in results]
    assert spikes.count(False) == 3  # All return False (no activity)
    assert sensor.check_count == 1  # Only one actual check
