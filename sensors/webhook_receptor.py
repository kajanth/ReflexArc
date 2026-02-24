"""
🧠 NSA Sensor: Webhook Receptor
Layer 0 — Peripheral Sense

This is a "virtual" sensor. Unlike polling sensors, it does not actively grab data.
Instead, it acts as a receptor for incoming HTTP POSTs to the /webhook/{source} API endpoint.
When a payload is received, it caches it and yields it to the next `monitor()` cycle
as a biological spike.
"""

import json
from collections import deque

class WebhookReceptor:
    def __init__(self, max_queue_size=100):
        """
        Initializes the webhook receptor.
        
        Args:
            max_queue_size: Max number of incoming webhooks to buffer.
        """
        self.queue = deque(maxlen=max_queue_size)
    
    def ingest_webhook(self, source: str, payload: dict):
        """
        Called by the API Server when a POST /webhook/{source} is received.
        Appends the webhook to the internal queue for processing.
        """
        self.queue.append({
            "source": source,
            "payload": payload
        })

    async def monitor(self) -> tuple[bool, str]:
        """
        Called by the sensor loop. Yields any queued webhooks.
        Returns (True, description) if webhooks are available, else (False, None).
        """
        if not self.queue:
            return False, None
            
        events = []
        while self.queue:
            events.append(self.queue.popleft())
            
        summary_parts = []
        for ev in events[:3]: # Cap summary at 3
            src = ev["source"].upper()
            
            # Simple heuristic to extract a basic summary from common webhook structures
            payload = ev["payload"]
            action = payload.get("action", "event")
            
            # Attempt to extract some string context
            context = ""
            for key in ["title", "message", "name", "id"]:
                if key in payload and isinstance(payload[key], str):
                    context = f" '{payload[key]}'"
                    break
                    
            summary_parts.append(f"[{src}] {action}{context}")

        overflow = f" (+{len(events)-3} more)" if len(events) > 3 else ""
        description = f"Webhook Received: {', '.join(summary_parts)}{overflow}"
        
        return True, description

    def release(self):
        """Cleanup logic when the brain shuts down."""
        self.queue.clear()
