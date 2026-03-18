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
        # ⚡ Bolt: Cache state in memory to prevent synchronous file I/O bottlenecks
        # Impact: Removes blocking disk reads during get_internal_state
        if not os.path.exists(self.stats_file):
            self.stats = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f)
        else:
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)

    def get_internal_state(self):
        # Read from in-memory dictionary rather than reading from disk
        stats = self.stats
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # Update in-memory dictionary first
        self.stats["total_spent"] += cost
        self.stats["calls"] += 1
        # Rolling average for latency
        self.stats["avg_latency"] = ((self.stats["avg_latency"] * (self.stats["calls"]-1)) + latency) / self.stats["calls"]

        # Write the updated stats to disk
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f)