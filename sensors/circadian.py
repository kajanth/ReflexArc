"""
🧠 NSA Sensor: Circadian Rhythm (Suprachiasmatic Nucleus)
Layer: Internal — Protocol Gamma trigger

Tracks time-of-day and activity levels to determine the system's
biological phase: ACTIVE, DROWSY, or SLEEP.

During SLEEP phase transitions, fires a spike to trigger the
optimization_cycle.py (memory consolidation + skill hardening).
This directly implements Protocol Gamma from agent.md.
"""

import time
from datetime import datetime, timedelta
from collections import deque


class CircadianSensor:
    def __init__(self, sleep_start_hour=2, sleep_end_hour=6,
                 drowsy_window_minutes=30, activity_window=300,
                 inactivity_threshold=3):
        """
        Args:
            sleep_start_hour: Hour (24h) when the system enters forced sleep.
            sleep_end_hour: Hour (24h) when the system wakes up.
            drowsy_window_minutes: Minutes before sleep_start to enter DROWSY phase.
            activity_window: Seconds to look back for activity measurement.
            inactivity_threshold: If fewer than this many spikes in the window, consider idle.
        """
        self.sleep_start_hour = sleep_start_hour
        self.sleep_end_hour = sleep_end_hour
        self.drowsy_window = timedelta(minutes=drowsy_window_minutes)
        self.activity_window = activity_window
        self.inactivity_threshold = inactivity_threshold

        # Rolling log of spike timestamps
        self._spike_log = deque(maxlen=1000)
        self._current_phase = "ACTIVE"
        self._sleep_triggered = False
        self._last_transition = None

    def record_spike(self):
        """Called by main loop whenever any sensor fires a spike."""
        self._spike_log.append(time.time())

    def _get_recent_activity(self):
        """Count spikes within the activity window."""
        cutoff = time.time() - self.activity_window
        return sum(1 for t in self._spike_log if t > cutoff)

    def get_phase(self):
        """
        Determine the current biological phase.
        Returns one of: 'ACTIVE', 'DROWSY', 'SLEEP'
        """
        now = datetime.now()
        hour = now.hour

        # Time-based sleep (forced quiet hours)
        if self.sleep_start_hour <= hour or hour < self.sleep_end_hour:
            return "SLEEP"

        # Drowsy zone: approaching sleep time
        sleep_time = now.replace(hour=self.sleep_start_hour, minute=0, second=0)
        if sleep_time < now:
            sleep_time += timedelta(days=1)
        if now >= sleep_time - self.drowsy_window:
            return "DROWSY"

        # Activity-based detection: prolonged inactivity = drowsy
        activity = self._get_recent_activity()
        if activity < self.inactivity_threshold:
            return "DROWSY"

        return "ACTIVE"

    async def monitor(self):
        """
        Checks for phase transitions.
        Returns (True, description) on a phase change, else (False, None).
        Specifically fires on ACTIVE->SLEEP or DROWSY->SLEEP to trigger
        the optimization cycle.
        """
        new_phase = self.get_phase()

        if new_phase != self._current_phase:
            old_phase = self._current_phase
            self._current_phase = new_phase
            self._last_transition = datetime.now()

            if new_phase == "SLEEP" and not self._sleep_triggered:
                self._sleep_triggered = True
                return True, (
                    f"Circadian transition: {old_phase} -> SLEEP. "
                    f"Triggering Protocol Gamma (memory consolidation + skill hardening)."
                )

            if new_phase == "ACTIVE":
                self._sleep_triggered = False  # Reset for next cycle
                return True, f"Circadian transition: {old_phase} -> ACTIVE. System waking up."

            return True, f"Circadian transition: {old_phase} -> {new_phase}."

        return False, None

    def release(self):
        """No resources to release."""
        pass
