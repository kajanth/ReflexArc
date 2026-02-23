"""
🧠 NSA Event Bus — Singleton Pub/Sub for Real-Time Dashboard

Components publish events (spikes, decisions, skill executions),
and WebSocket connections consume them for live dashboard updates.

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


class EventBus:
    """Async event bus with fan-out to all subscribers."""

    def __init__(self, history_size=200):
        self._subscribers = set()
        self._history = deque(maxlen=history_size)

    def publish(self, event_type: str, data: dict = None):
        """Publish an event to all subscribers."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "data": data or {},
        }
        self._history.append(event)

        # Fan-out to all subscriber queues
        dead = set()
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(queue)

        # Clean up dead subscribers
        self._subscribers -= dead

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscription queue."""
        queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscription."""
        self._subscribers.discard(queue)

    def get_history(self, limit: int = 50) -> list:
        """Get recent event history for new dashboard connections."""
        items = list(self._history)
        return items[-limit:]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Singleton instance
event_bus = EventBus()
