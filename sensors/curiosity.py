import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"
        self._init_stats()

    def _init_stats(self):
        if not os.path.exists(self.stats_file):
            self.stats = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f)
        else:
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)

    def get_internal_state(self):
        # ⚡ Bolt: Cache internal state in memory to prevent synchronous file I/O bottleneck
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if self.stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if self.stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Update cached state directly, avoid reading from disk on every event
        self.stats["total_spent"] += cost
        self.stats["calls"] += 1
        # Rolling average for latency
        self.stats["avg_latency"] = ((self.stats["avg_latency"] * (self.stats["calls"]-1)) + latency) / self.stats["calls"]

        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f)