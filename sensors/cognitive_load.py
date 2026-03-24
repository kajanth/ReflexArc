"""
🧠 NSA Sensor: Cognitive Load (Prefrontal Cortex Monitor)
Layer: Internal — Interoceptive (extends Curiosity Sensor)

Tracks the ratio of Layer 4 (Cortex/expensive) invocations vs
Layer 5 (Reflex/cheap) invocations over time. When the system is
"thinking too hard" — relying on the Cortex too much — it fires
a COGNITIVE_OVERLOAD signal.

This directly implements Protocol Alpha (Conservation of Token Energy)
and can proactively trigger the optimization cycle to harden
repetitive Cortex tasks into Reflexes.
"""

import json
import os
import time
import sqlite3


class CognitiveLoadSensor:
    def __init__(self, cortex_ratio_threshold=0.4, window_hours=24,
                 min_calls_for_signal=5, stats_file="memory/stats.json",
                 db_path="memory/long_term_memory.db"):
        """
        Args:
            cortex_ratio_threshold: If cortex_calls / total_calls exceeds this, fire.
            window_hours: How far back to look for call history.
            min_calls_for_signal: Minimum total calls before the ratio is meaningful.
            stats_file: Path to the curiosity stats file.
            db_path: Path to the hippocampus database.
        """
        self.cortex_ratio_threshold = cortex_ratio_threshold
        self.window_hours = window_hours
        self.min_calls = min_calls_for_signal
        self.stats_file = stats_file
        self.db_path = db_path

        # ⚡ Bolt: Cache state to prevent synchronous file I/O bottlenecks in _get_financial_state
        self._cache = None
        self._cache_mtime = 0.0

        # Internal tracking (augments stats.json)
        self._cortex_calls = 0
        self._reflex_calls = 0
        self._log_calls = 0
        self._last_signal = None
        self._poll_interval = 60.0  # Check every 60 seconds
        self._last_poll = 0

    def record_decision(self, decision_type):
        """
        Called by the orchestrator after each triage decision.

        Args:
            decision_type: One of 'COMPLEX', 'REFLEX', 'LOG'
        """
        if "COMPLEX" in decision_type:
            self._cortex_calls += 1
        elif "REFLEX" in decision_type:
            self._reflex_calls += 1
        else:
            self._log_calls += 1

    def get_metrics(self):
        """Return current cognitive load metrics."""
        total = self._cortex_calls + self._reflex_calls + self._log_calls
        if total == 0:
            return {
                "cortex_calls": 0,
                "reflex_calls": 0,
                "log_calls": 0,
                "total_calls": 0,
                "cortex_ratio": 0.0,
                "efficiency_score": 1.0,
            }

        cortex_ratio = self._cortex_calls / total
        efficiency = 1.0 - cortex_ratio  # Higher = better

        return {
            "cortex_calls": self._cortex_calls,
            "reflex_calls": self._reflex_calls,
            "log_calls": self._log_calls,
            "total_calls": total,
            "cortex_ratio": cortex_ratio,
            "efficiency_score": efficiency,
        }

    def _get_financial_state(self):
        """Read current spending from the curiosity stats file."""
        try:
            current_mtime = os.path.getmtime(self.stats_file)
        except OSError:
            current_mtime = 0.0

        if self._cache is None or current_mtime != self._cache_mtime:
            try:
                with open(self.stats_file, "r") as f:
                    self._cache = json.load(f)
                self._cache_mtime = current_mtime
            except (FileNotFoundError, json.JSONDecodeError):
                self._cache = {}
                self._cache_mtime = current_mtime

        stats = self._cache or {}
        return stats.get("total_spent", 0.0), stats.get("calls", 0)

    def _get_recent_complex_patterns(self):
        """Query hippocampus for recent COMPLEX-type events to identify patterns."""
        patterns = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT description FROM memories "
                "WHERE timestamp > datetime('now', ?) "
                "ORDER BY timestamp DESC LIMIT 20",
                (f'-{self.window_hours} hours',)
            )
            patterns = [row[0] for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error:
            pass
        return patterns

    async def monitor(self):
        """
        Checks cognitive load metrics.
        Returns (True, description) if overloaded, else (False, None).
        """
        now = time.time()
        if now - self._last_poll < self._poll_interval:
            return False, None
        self._last_poll = now

        metrics = self.get_metrics()
        total_spent, total_api_calls = self._get_financial_state()

        # Not enough data yet
        if metrics["total_calls"] < self.min_calls:
            return False, None

        alerts = []

        # Check cortex ratio
        if metrics["cortex_ratio"] > self.cortex_ratio_threshold:
            alerts.append(
                f"Cortex ratio {metrics['cortex_ratio']:.0%} exceeds "
                f"threshold {self.cortex_ratio_threshold:.0%} "
                f"({metrics['cortex_calls']} cortex / {metrics['total_calls']} total)"
            )

        # Check spending velocity
        if total_api_calls > 0 and total_spent > 0:
            cost_per_call = total_spent / total_api_calls
            if cost_per_call > 0.01:  # More than 1 cent per call average
                alerts.append(
                    f"High cost-per-call: ${cost_per_call:.4f}/call "
                    f"(total: ${total_spent:.4f})"
                )

        if alerts:
            # Suggest patterns that could be hardened
            recent = self._get_recent_complex_patterns()
            pattern_hint = ""
            if recent:
                pattern_hint = f" Recent memory patterns: {recent[:3]}"

            description = (
                f"COGNITIVE_OVERLOAD [Protocol Alpha]: {'; '.join(alerts)}. "
                f"Efficiency: {metrics['efficiency_score']:.0%}.{pattern_hint} "
                f"Recommend triggering optimization cycle to harden reflexes."
            )
            return True, description

        return False, None

    def release(self):
        """No resources to release."""
        pass
