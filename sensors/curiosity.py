import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"
        self._stats_cache = None
        self._init_stats()

    def _init_stats(self):
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
        if not os.path.exists(self.stats_file):
            self._stats_cache = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
            with open(self.stats_file, "w") as f:
                json.dump(self._stats_cache, f)
        else:
            with open(self.stats_file, "r") as f:
                self._stats_cache = json.load(f)

    def get_internal_state(self):
        # ⚡ Bolt: Cache state in memory to prevent synchronous disk I/O bottlenecks on every routine call
        stats = self._stats_cache
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Update in-memory cache and efficiently overwrite file without reading first
        stats = self._stats_cache
        stats["total_spent"] += cost
        stats["calls"] += 1
        # Rolling average for latency
        stats["avg_latency"] = ((stats["avg_latency"] * (stats["calls"]-1)) + latency) / stats["calls"]

        with open(self.stats_file, "w") as f:
            json.dump(stats, f)