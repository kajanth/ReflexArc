"""
🧠 NSA Sensor: System Vitals (Nociceptors / Autonomic Nervous System)
Layer 0 — Peripheral Sense

Monitors the host machine's health: CPU, memory, disk, and temperature.
Fires a "pain signal" spike when any metric crosses a danger threshold.
This is the organism's body-awareness — it must know when its hardware
is under stress before higher cognition can intervene.
"""

import psutil
import asyncio


class SystemVitalsSensor:
    def __init__(self, cpu_threshold=85.0, ram_threshold=90.0, disk_threshold=95.0,
                 poll_interval=5.0):
        """
        Args:
            cpu_threshold: CPU usage % that triggers a spike.
            ram_threshold: RAM usage % that triggers a spike.
            disk_threshold: Disk usage % that triggers a spike.
            poll_interval: Minimum seconds between full scans (avoids redundant reads).
        """
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.disk_threshold = disk_threshold
        self.poll_interval = poll_interval
        self._last_poll = 0

    async def monitor(self):
        """
        Polls system vitals.
        Returns (True, description) if any threshold is breached, else (False, None).
        """
        import time
        now = time.time()
        if now - self._last_poll < self.poll_interval:
            return False, None
        self._last_poll = now

        alerts = []

        # --- CPU ---
        # ⚡ Bolt: Use interval=None to non-blockingly calculate average CPU utilization
        # since the last poll instead of blocking the async event loop for 0.1 seconds.
        cpu = psutil.cpu_percent(interval=None)
        if cpu > self.cpu_threshold:
            alerts.append(f"CPU at {cpu:.1f}%")

        # --- RAM ---
        ram = psutil.virtual_memory().percent
        if ram > self.ram_threshold:
            alerts.append(f"RAM at {ram:.1f}%")

        # --- DISK ---
        disk = psutil.disk_usage('/').percent
        if disk > self.disk_threshold:
            alerts.append(f"Disk at {disk:.1f}%")

        # --- Temperature (if available) ---
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.critical and entry.current > entry.critical * 0.9:
                            alerts.append(f"Temp({name}/{entry.label}): {entry.current}°C")
        except (AttributeError, NotImplementedError):
            pass  # Not available on all platforms

        if alerts:
            severity = "CRITICAL" if len(alerts) >= 2 else "WARNING"
            description = f"PAIN SIGNAL [{severity}]: {', '.join(alerts)}"
            return True, description

        return False, None

    def release(self):
        """No hardware resources to release."""
        pass
