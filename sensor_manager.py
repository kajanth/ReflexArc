"""
🧠 NSA Sensor Manager
Wraps all sensors with enable/disable state and provides a unified
interface for the main loop, API, and dashboard.

Usage:
    mgr = SensorManager()
    mgr.register("vision", OpenCVReflex(sensitivity=20000))
    mgr.register("auditory", AudioSensor(...))

    # Main loop polls only enabled sensors
    for name, sensor in mgr.active_sensors():
        spiked, desc = await sensor.monitor()

    # Toggle via dashboard/API
    mgr.disable("vision")
    mgr.enable("vision")
"""

import json
import os
import time
from typing import Dict, Optional, List, Tuple

from event_bus import event_bus

STATE_FILE = "memory/sensor_state.json"


class SensorManager:
    """Manages sensor registration, enable/disable state, and persistence."""

    def __init__(self):
        self._sensors = {}      # name -> sensor instance
        self._enabled = {}      # name -> bool
        self._metadata = {}     # name -> {emoji, label, type}
        self._load_state()

    def register(self, name: str, sensor, emoji: str = "📡",
                 label: str = None, sensor_type: str = "peripheral"):
        """Register a sensor with the manager."""
        self._sensors[name] = sensor
        self._metadata[name] = {
            "emoji": emoji,
            "label": label or name.replace("_", " ").title(),
            "type": sensor_type,
        }
        # Preserve persisted state, default to enabled
        if name not in self._enabled:
            self._enabled[name] = True

    def enable(self, name: str) -> bool:
        """Enable a sensor. Returns False if sensor not found."""
        if name not in self._sensors:
            return False
        self._enabled[name] = True
        self._save_state()
        event_bus.publish("sensor_toggle", {
            "sensor": name,
            "state": "enabled",
            "label": self._metadata.get(name, {}).get("label", name),
        })
        print(f"[SensorMgr] ✓ {name} ENABLED")
        return True

    def disable(self, name: str) -> bool:
        """Disable a sensor. Returns False if sensor not found."""
        if name not in self._sensors:
            return False
        self._enabled[name] = False
        self._save_state()
        event_bus.publish("sensor_toggle", {
            "sensor": name,
            "state": "disabled",
            "label": self._metadata.get(name, {}).get("label", name),
        })
        print(f"[SensorMgr] ✗ {name} DISABLED")
        return True

    def toggle(self, name: str) -> Optional[bool]:
        """Toggle a sensor. Returns new state, or None if not found."""
        if name not in self._sensors:
            return None
        if self._enabled.get(name, True):
            self.disable(name)
            return False
        else:
            self.enable(name)
            return True

    def is_enabled(self, name: str) -> bool:
        """Check if a sensor is enabled."""
        return self._enabled.get(name, True)

    def get_sensor(self, name: str):
        """Get a sensor instance by name."""
        return self._sensors.get(name)

    def active_sensors(self) -> List[Tuple[str, object]]:
        """Return (name, sensor) pairs for enabled sensors only."""
        return [
            (name, sensor)
            for name, sensor in self._sensors.items()
            if self._enabled.get(name, True)
        ]

    def all_sensors(self) -> Dict:
        """Return full status for all sensors (for API/dashboard)."""
        result = {}
        for name, sensor in self._sensors.items():
            meta = self._metadata.get(name, {})
            result[name] = {
                "enabled": self._enabled.get(name, True),
                "emoji": meta.get("emoji", "📡"),
                "label": meta.get("label", name),
                "type": meta.get("type", "peripheral"),
            }
        return result

    def get_status_summary(self) -> Dict:
        """Summary for the dashboard header."""
        total = len(self._sensors)
        active = sum(1 for v in self._enabled.values() if v)
        return {
            "total": total,
            "active": active,
            "disabled": total - active,
        }

    def release_all(self):
        """Release all sensor resources."""
        for name, sensor in self._sensors.items():
            try:
                if hasattr(sensor, 'release'):
                    sensor.release()
            except Exception:
                pass

    def _save_state(self):
        """Persist sensor enable/disable state to disk."""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump(self._enabled, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        """Load persisted sensor state from disk."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    self._enabled = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
