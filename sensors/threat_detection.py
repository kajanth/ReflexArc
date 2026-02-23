"""
🧠 NSA Sensor: Threat Detection (Amygdala)
Layer: Internal — Always-on threat monitor

Scans for security-relevant events: new/unknown processes, unusual
network connections, and suspicious activity patterns. This is the
organism's "fight or flight" system.

High-priority spikes from this sensor should bypass the RAS
habituation filter — threats are never "background noise."
"""

import psutil
import time
import os


class ThreatDetectionSensor:
    def __init__(self, poll_interval=15.0, known_process_whitelist=None):
        """
        Args:
            poll_interval: Seconds between threat scans.
            known_process_whitelist: Set of process names considered safe.
        """
        self.poll_interval = poll_interval
        self._last_poll = 0

        # Build initial baseline of running processes
        self._baseline_pids = set()
        self._baseline_connections = 0
        self._initialized = False

        # Whitelist of known-safe process names
        self.whitelist = known_process_whitelist or {
            "python", "python3", "node", "bash", "zsh", "sh",
            "sshd", "systemd", "launchd", "loginwindow",
            "WindowServer", "Finder", "Dock", "kernel_task",
            "mds", "mdworker", "coreaudiod", "coreservicesd",
        }

    def _take_baseline(self):
        """Capture the initial set of running processes and connections."""
        try:
            self._baseline_pids = {p.pid for p in psutil.process_iter()}
            self._baseline_connections = len(psutil.net_connections(kind='inet'))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        self._initialized = True

    def _scan_new_processes(self):
        """Detect processes that weren't in the baseline."""
        new_suspicious = []
        try:
            current_pids = set()
            for proc in psutil.process_iter(['pid', 'name', 'username', 'create_time']):
                current_pids.add(proc.info['pid'])
                if proc.info['pid'] not in self._baseline_pids:
                    name = proc.info['name'] or "unknown"
                    # Check if it's a known-safe process
                    if name.lower() not in {w.lower() for w in self.whitelist}:
                        age = time.time() - (proc.info['create_time'] or 0)
                        if age < self.poll_interval * 2:  # Recently spawned
                            new_suspicious.append(
                                f"New process: {name} (PID: {proc.info['pid']}, "
                                f"User: {proc.info['username'] or '?'})"
                            )
            # Update baseline
            self._baseline_pids = current_pids
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        return new_suspicious

    def _scan_network_anomalies(self):
        """Detect sudden increases in network connections."""
        anomalies = []
        try:
            current_connections = psutil.net_connections(kind='inet')
            count = len(current_connections)

            # Spike detection: >50% increase in connections
            if self._baseline_connections > 0:
                increase = (count - self._baseline_connections) / self._baseline_connections
                if increase > 0.5 and count - self._baseline_connections > 10:
                    anomalies.append(
                        f"Connection surge: {self._baseline_connections} -> {count} "
                        f"(+{increase:.0%})"
                    )

            # Check for connections on suspicious ports
            suspicious_ports = {4444, 5555, 6666, 1337, 31337, 12345}
            for conn in current_connections:
                if conn.laddr and conn.laddr.port in suspicious_ports:
                    anomalies.append(
                        f"Suspicious listening port: {conn.laddr.port}"
                    )
                if conn.raddr and conn.raddr.port in suspicious_ports:
                    anomalies.append(
                        f"Suspicious outbound connection to port {conn.raddr.port}"
                    )

            self._baseline_connections = count
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        return anomalies

    async def monitor(self):
        """
        Runs a threat scan.
        Returns (True, description) if threats detected, else (False, None).
        Threat spikes are HIGH PRIORITY and should bypass RAS habituation.
        """
        now = time.time()
        if now - self._last_poll < self.poll_interval:
            return False, None
        self._last_poll = now

        if not self._initialized:
            self._take_baseline()
            return False, None

        threats = []
        threats.extend(self._scan_new_processes())
        threats.extend(self._scan_network_anomalies())

        if threats:
            severity = "CRITICAL" if len(threats) >= 3 else "ALERT"
            description = (
                f"AMYGDALA [{severity}]: {len(threats)} threat(s) detected — "
                f"{'; '.join(threats[:5])}"
            )
            return True, description

        return False, None

    def release(self):
        """No resources to release."""
        pass
