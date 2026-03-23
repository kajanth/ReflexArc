import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"

        # ⚡ Bolt: Cache state to prevent synchronous file I/O bottlenecks in get_internal_state
        self._cache = None
        self._cache_mtime = 0.0

        self._init_stats()

    def _init_stats(self):
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, "w") as f:
                json.dump({"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}, f)

    def get_internal_state(self):
        # ⚡ Bolt: Only read from disk if the file has been modified (supports cross-process concurrency)
        try:
            current_mtime = os.path.getmtime(self.stats_file)
        except OSError:
            current_mtime = 0.0

        if self._cache is None or current_mtime > self._cache_mtime:
            with open(self.stats_file, "r") as f:
                self._cache = json.load(f)
            self._cache_mtime = current_mtime

        stats = self._cache
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Retain read-modify-write pattern for concurrency, but update cache to prevent immediate invalidation
        with open(self.stats_file, "r+") as f:
            stats = json.load(f)
            stats["total_spent"] += cost
            stats["calls"] += 1
            # Rolling average for latency
            stats["avg_latency"] = ((stats["avg_latency"] * (stats["calls"]-1)) + latency) / stats["calls"]
            f.seek(0)
            json.dump(stats, f)
            f.truncate()

            # Update cache to avoid redundant reads
            self._cache = stats
            try:
                self._cache_mtime = os.path.getmtime(self.stats_file)
            except OSError:
                pass