"""
🧠 NSA Basal Ganglia — Habit Formation (Layer 5.5)

Reinforces patterns that succeed via Reflex or Template layers.
Repeated patterns get "burned in" — making them faster and cheaper
over time, like muscle memory.
"""

import json
import os

HABITS_FILE = "memory/habits.json"


class BasalGanglia:
    def __init__(self):
        self.habits = {}
        self._load_habits()

    def reinforce_habit(self, pattern_id: str):
        """
        Reinforce a pattern that succeeded.
        Makes repeated patterns cheaper and faster over time.
        """
        if pattern_id in self.habits:
            habit = self.habits[pattern_id]
            habit["count"] += 1
            habit["latency_multiplier"] = max(0.1, habit["latency_multiplier"] * 0.95)
            habit["cost_multiplier"] = max(0.1, habit["cost_multiplier"] * 0.90)
        else:
            self.habits[pattern_id] = {
                "count": 1,
                "latency_multiplier": 1.0,
                "cost_multiplier": 1.0,
            }

        self._save_habits()
        return self.habits[pattern_id]

    def get_habit_optimization(self, pattern_id: str):
        """Retrieve optimization parameters if a habit exists."""
        return self.habits.get(pattern_id, {
            "latency_multiplier": 1.0,
            "cost_multiplier": 1.0,
            "count": 0,
        })

    def is_habitual(self, pattern_id: str, threshold: int = 3) -> bool:
        """Check if a pattern has been reinforced enough to be a habit."""
        habit = self.habits.get(pattern_id)
        return habit is not None and habit["count"] >= threshold

    def get_all_habits(self) -> dict:
        """Return all habits for dashboard display."""
        return self.habits

    def _save_habits(self):
        """Persist habits to disk."""
        try:
            os.makedirs(os.path.dirname(HABITS_FILE), exist_ok=True)
            with open(HABITS_FILE, "w") as f:
                json.dump(self.habits, f, indent=2)
        except Exception:
            pass

    def _load_habits(self):
        """Load habits from disk."""
        if os.path.exists(HABITS_FILE):
            try:
                with open(HABITS_FILE, "r") as f:
                    self.habits = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
