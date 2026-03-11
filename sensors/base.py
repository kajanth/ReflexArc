"""
🧠 NSA Sensor: Base Interface
Layer 0 — Peripheral Sense

Defines the async sensor interface for the ReflexArc NSA system.
Supports both event-driven and polled sensor modes with health monitoring.

**Validates: Requirements FR-010.1, FR-010.2, FR-010.4**

This module provides:
- AsyncSensor: Base protocol/interface for all sensors
- SensorMode: Enum for event-driven vs polled modes
- SensorHealth: Health status tracking
- Helper utilities for sensor implementation
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass
import time


class SensorMode(Enum):
    """
    Sensor operation mode.
    
    - POLLED: Sensor is actively queried at intervals (traditional polling)
    - EVENT_DRIVEN: Sensor pushes events when they occur (webhooks, watchers)
    """
    POLLED = "polled"
    EVENT_DRIVEN = "event_driven"


@dataclass
class SensorHealth:
    """
    Health status for a sensor.
    
    Attributes:
        is_healthy: Whether the sensor is currently healthy
        failure_count: Number of consecutive failures
        last_success: Timestamp of last successful monitor call
        last_failure: Timestamp of last failure
        error_message: Most recent error message if any
    """
    is_healthy: bool = True
    failure_count: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    error_message: Optional[str] = None
    
    def record_success(self) -> None:
        """Record a successful sensor operation."""
        self.is_healthy = True
        self.failure_count = 0
        self.last_success = time.time()
        self.error_message = None
    
    def record_failure(self, error: str) -> None:
        """Record a failed sensor operation."""
        self.failure_count += 1
        self.last_failure = time.time()
        self.error_message = error
        
        # Auto-disable after 3 consecutive failures (FR-010.4)
        if self.failure_count >= 3:
            self.is_healthy = False


class AsyncSensor(ABC):
    """
    Base interface for all NSA sensors.
    
    All sensors must implement the async monitor() method which returns
    a tuple of (spiked: bool, description: str).
    
    Sensors can operate in two modes:
    - POLLED: Traditional polling where monitor() actively checks for changes
    - EVENT_DRIVEN: Event-based where monitor() returns queued events
    
    Example (Polled Sensor):
        ```python
        class CPUSensor(AsyncSensor):
            def __init__(self):
                super().__init__(mode=SensorMode.POLLED)
                self.threshold = 80.0
            
            async def monitor(self) -> Tuple[bool, Optional[str]]:
                cpu = psutil.cpu_percent()
                if cpu > self.threshold:
                    return True, f"CPU at {cpu}%"
                return False, None
            
            def release(self) -> None:
                pass
        ```
    
    Example (Event-Driven Sensor):
        ```python
        class WebhookSensor(AsyncSensor):
            def __init__(self):
                super().__init__(mode=SensorMode.EVENT_DRIVEN)
                self.queue = deque()
            
            def ingest_event(self, data: dict) -> None:
                self.queue.append(data)
            
            async def monitor(self) -> Tuple[bool, Optional[str]]:
                if not self.queue:
                    return False, None
                event = self.queue.popleft()
                return True, f"Event: {event}"
            
            def release(self) -> None:
                self.queue.clear()
        ```
    """
    
    def __init__(self, mode: SensorMode = SensorMode.POLLED):
        """
        Initialize the sensor.
        
        Args:
            mode: Operating mode (POLLED or EVENT_DRIVEN)
        """
        self.mode = mode
        self.health = SensorHealth()
    
    @abstractmethod
    async def monitor(self) -> Tuple[bool, Optional[str]]:
        """
        Monitor the sensor for activity.
        
        This method is called by the sensor manager to check for new spikes.
        
        For POLLED sensors:
            - Actively check the sensor state
            - Return (True, description) if a spike should be generated
            - Return (False, None) if no activity detected
        
        For EVENT_DRIVEN sensors:
            - Check internal queue for pending events
            - Return (True, description) if events are available
            - Return (False, None) if queue is empty
        
        Returns:
            Tuple of (spiked, description):
                - spiked: True if a spike should be generated
                - description: Human-readable description of the spike (or None)
        
        Raises:
            Exception: Any exception will be caught by the sensor manager
                      and recorded in the health status
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """
        Release any resources held by the sensor.
        
        Called during system shutdown to ensure proper cleanup.
        Should close connections, stop threads, release hardware, etc.
        
        This method should be idempotent and not raise exceptions.
        """
        pass
    
    def get_health(self) -> SensorHealth:
        """
        Get the current health status of the sensor.
        
        Returns:
            SensorHealth object with current status
        """
        return self.health
    
    def is_event_driven(self) -> bool:
        """
        Check if this sensor is event-driven.
        
        Event-driven sensors should not be polled aggressively as they
        push events when they occur (FR-010.2).
        
        Returns:
            True if sensor is event-driven, False if polled
        """
        return self.mode == SensorMode.EVENT_DRIVEN
    
    def is_polled(self) -> bool:
        """
        Check if this sensor uses polling.
        
        Returns:
            True if sensor is polled, False if event-driven
        """
        return self.mode == SensorMode.POLLED


class AdaptivePolledSensor(AsyncSensor):
    """
    Base class for polled sensors with adaptive polling rates.
    
    Automatically adjusts polling interval based on activity:
    - Increases interval when no activity detected (saves CPU)
    - Decreases interval when activity detected (improves responsiveness)
    
    Example:
        ```python
        class NetworkSensor(AdaptivePolledSensor):
            def __init__(self):
                super().__init__(
                    min_interval=1.0,   # Poll at least every 1s
                    max_interval=30.0,  # Poll at most every 30s
                    backoff_factor=1.5  # Slow down by 1.5x on no activity
                )
            
            async def _check_sensor(self) -> Tuple[bool, Optional[str]]:
                # Implement actual sensor logic here
                return False, None
        ```
    """
    
    def __init__(
        self,
        min_interval: float = 1.0,
        max_interval: float = 60.0,
        backoff_factor: float = 1.5,
        mode: SensorMode = SensorMode.POLLED
    ):
        """
        Initialize adaptive polled sensor.
        
        Args:
            min_interval: Minimum seconds between polls (when active)
            max_interval: Maximum seconds between polls (when idle)
            backoff_factor: Multiplier for interval on no activity
            mode: Operating mode (should be POLLED)
        """
        super().__init__(mode=mode)
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.backoff_factor = backoff_factor
        self.current_interval = min_interval
        self._last_poll = 0.0
    
    async def monitor(self) -> Tuple[bool, Optional[str]]:
        """
        Monitor with adaptive polling rate.
        
        Returns:
            Tuple of (spiked, description)
        """
        now = time.time()
        
        # Check if enough time has passed since last poll
        if now - self._last_poll < self.current_interval:
            return False, None
        
        self._last_poll = now
        
        # Call subclass implementation
        spiked, description = await self._check_sensor()
        
        # Adjust polling interval based on activity
        if spiked:
            # Activity detected - poll more frequently
            self.current_interval = self.min_interval
        else:
            # No activity - back off polling rate
            self.current_interval = min(
                self.current_interval * self.backoff_factor,
                self.max_interval
            )
        
        return spiked, description
    
    @abstractmethod
    async def _check_sensor(self) -> Tuple[bool, Optional[str]]:
        """
        Implement the actual sensor check logic.
        
        Subclasses should override this method instead of monitor().
        
        Returns:
            Tuple of (spiked, description)
        """
        pass
