import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"
        self.stats_cache = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
        self._init_stats()

    def _init_stats(self):
        if not os.path.exists(self.stats_file):
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, "w") as f:
                json.dump(self.stats_cache, f)
        else:
            try:
                with open(self.stats_file, "r") as f:
                    self.stats_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def get_internal_state(self):
        # ⚡ Bolt: Cache state in memory to prevent synchronous file I/O bottlenecks
        # Impact: Eliminates blocking disk reads on every routine call
        stats = self.stats_cache
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats.get("total_spent", 0.0) > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats.get("avg_latency", 0.0) > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Update in-memory cache directly
        # Impact: Prevents reading the file first before modifying and saving
        self.stats_cache["total_spent"] = self.stats_cache.get("total_spent", 0.0) + cost
        self.stats_cache["calls"] = self.stats_cache.get("calls", 0) + 1

        calls = self.stats_cache["calls"]
        current_avg = self.stats_cache.get("avg_latency", 0.0)
        # Rolling average for latency
        self.stats_cache["avg_latency"] = ((current_avg * (calls - 1)) + latency) / calls

        # Still need to persist to disk, but we avoid the read
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats_cache, f)
        except IOError:
            pass