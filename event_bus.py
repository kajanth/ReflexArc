"""
🧠 NSA Event Bus — Singleton Pub/Sub for Real-Time Dashboard

Components publish events (spikes, decisions, skill executions),
and WebSocket connections consume them for live dashboard updates.

Now with automatic memory management and periodic cleanup.

Usage:
    from event_bus import event_bus

    # Publishing (from brain_core, sensors, etc.)
    event_bus.publish("spike", {"sense_type": "vision", "description": "..."})
    event_bus.publish("decision", {"decision": "REFLEX:system_check", "layer": "thalamus"})

    # Subscribing (from WebSocket handler)
    async for event in event_bus.subscribe():
        await ws.send_json(event)
"""

import asyncio
import time
import json
from collections import deque
from typing import Dict, Any, Optional, Set, Deque, AsyncIterator
from utils.logging_config import get_logger

logger = get_logger(__name__)


class EventBus:
    """Async event bus with fan-out to all subscribers and automatic cleanup."""

    def __init__(self, history_size: int = 200, retention_seconds: int = 3600) -> None:
        """
        Initialize event bus.
        
        Args:
            history_size: Maximum number of events to keep in history
            retention_seconds: How long to keep events (default 1 hour)
        """
        self._subscribers: Set[asyncio.Queue[Dict[str, Any]]] = set()
        self._history: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self._retention_seconds: int = retention_seconds
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._running: bool = False

    def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event to all subscribers."""
        event: Dict[str, Any] = {
            "type": event_type,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "data": data or {},
        }
        self._history.append(event)

        # Fan-out to all subscriber queues
        dead: Set[asyncio.Queue[Dict[str, Any]]] = set()
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(queue)

        # Clean up dead subscribers
        if dead:
            self._subscribers -= dead
            logger.debug("removed_dead_subscribers", count=len(dead))

    def subscribe(self) -> asyncio.Queue[Dict[str, Any]]:
        """Create a new subscription queue."""
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        logger.debug("subscriber_added", total_subscribers=len(self._subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        """Remove a subscription."""
        self._subscribers.discard(queue)
        logger.debug("subscriber_removed", total_subscribers=len(self._subscribers))

    def get_history(self, limit: int = 50) -> list[Dict[str, Any]]:
        """Get recent event history for new dashboard connections."""
        items: list[Dict[str, Any]] = list(self._history)
        return items[-limit:]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
    
    async def _cleanup_loop(self) -> None:
        """Periodically clean up old events from history."""
        logger.info("event_bus_cleanup_started",
                   retention_seconds=self._retention_seconds)
        
        while self._running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                cutoff_time: float = time.time() - self._retention_seconds
                original_size: int = len(self._history)
                
                # Filter out old events
                self._history = deque(
                    (e for e in self._history if e['timestamp'] > cutoff_time),
                    maxlen=self._history.maxlen
                )
                
                removed: int = original_size - len(self._history)
                if removed > 0:
                    logger.info("event_bus_cleanup",
                               removed=removed,
                               remaining=len(self._history),
                               retention_seconds=self._retention_seconds)
                
            except asyncio.CancelledError:
                logger.info("event_bus_cleanup_cancelled")
                break
            except Exception as e:
                logger.error("event_bus_cleanup_error", error=str(e))
    
    def start_cleanup(self) -> None:
        """Start the periodic cleanup task."""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("event_bus_cleanup_task_started")
    
    def stop_cleanup(self) -> None:
        """Stop the periodic cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            logger.info("event_bus_cleanup_task_stopped")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "history_size": len(self._history),
            "history_max": self._history.maxlen,
            "subscriber_count": len(self._subscribers),
            "retention_seconds": self._retention_seconds,
            "oldest_event_age": time.time() - self._history[0]['timestamp'] if self._history else 0
        }


# Singleton instance
event_bus = EventBus()
