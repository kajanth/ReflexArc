import time
import json
import os

class CuriositySensor:
    def __init__(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = "memory/stats.json"
        self._cache = None
        self._last_mtime = 0
        self._init_stats()

    def _init_stats(self):
        if not os.path.exists(self.stats_file):
            stats = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
            with open(self.stats_file, "w") as f:
                json.dump(stats, f)
            self._cache = stats
            self._last_mtime = os.path.getmtime(self.stats_file)
        else:
            with open(self.stats_file, "r") as f:
                self._cache = json.load(f)
            self._last_mtime = os.path.getmtime(self.stats_file)

    def get_internal_state(self):
        # ⚡ Bolt: Use in-memory cache to prevent sync file I/O bottlenecks
        # Impact: Removes a blocking disk read from this frequently polled sensor

        try:
            current_mtime = os.path.getmtime(self.stats_file)
            if current_mtime > self._last_mtime:
                with open(self.stats_file, "r") as f:
                    self._cache = json.load(f)
                self._last_mtime = current_mtime
        except OSError:
            pass # fallback to cache if file missing

        stats = self._cache
        
        # Logic: Is the AI becoming "bloated" or "expensive"?
        if stats["total_spent"] > self.cost_limit:
            return "FINANCIAL_PAIN"
        if stats["avg_latency"] > self.latency_threshold:
            return "COGNITIVE_LUGGISHNESS"
        
        return "STABLE"

    def log_event(self, cost, latency):
        # ⚡ Bolt: Retain read-modify-write pattern against the file for concurrency
        # but also update our in-memory cache so readers don't need to hit the disk.
        with open(self.stats_file, "r+") as f:
            stats = json.load(f)
            stats["total_spent"] += cost
            stats["calls"] += 1
            # Rolling average for latency
            stats["avg_latency"] = ((stats["avg_latency"] * (stats["calls"]-1)) + latency) / stats["calls"]
            f.seek(0)
            json.dump(stats, f)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())

            # Update cache
            self._cache = stats
            self._last_mtime = os.path.getmtime(self.stats_file)