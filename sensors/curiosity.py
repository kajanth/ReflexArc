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
            with open(self.stats_file, "w") as f:
                json.dump({"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}, f)

    def get_internal_state(self):
        with open(self.stats_file, "r") as f:
            stats = json.load(f)
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        with open(self.stats_file, "r+") as f:
            stats = json.load(f)
            stats["total_spent"] += cost
            stats["calls"] += 1
            # Rolling average for latency
            stats["avg_latency"] = ((stats["avg_latency"] * (stats["calls"]-1)) + latency) / stats["calls"]
            f.seek(0)
            json.dump(stats, f)
            f.truncate()