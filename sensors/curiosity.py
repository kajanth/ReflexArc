import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"
        self._stats = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
        self._init_stats()

    def _init_stats(self):
        # ⚡ Bolt: Initialize in-memory cache to prevent blocking I/O later
        if not os.path.exists(self.stats_file):
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, "w") as f:
                json.dump(self._stats, f)
        else:
            try:
                with open(self.stats_file, "r") as f:
                    self._stats = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def get_internal_state(self):
        # ⚡ Bolt: Read from in-memory cache instead of disk to prevent blocking the asyncio event loop
        stats = self._stats
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats.get("total_spent", 0.0) > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats.get("avg_latency", 0.0) > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Read-modify-write on disk to support concurrent processes, then update in-memory cache
        try:
            with open(self.stats_file, "r+") as f:
                stats = json.load(f)
                stats["total_spent"] += cost
                stats["calls"] += 1
                # Rolling average for latency
                stats["avg_latency"] = ((stats["avg_latency"] * (stats["calls"]-1)) + latency) / stats["calls"]

                # Sync back to in-memory cache
                self._stats = stats.copy()

                f.seek(0)
                json.dump(stats, f)
                f.truncate()
        except IOError:
            pass