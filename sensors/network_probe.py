"""
🧠 NSA Sensor: Network Probe (Chemoreceptors)
Layer 0 — Peripheral Sense

Monitors network connectivity and key external endpoints.
Detects internet outages, high API latency, and DNS failures.
The organism must know if its communication channels to the outside
world are healthy before attempting expensive Cortex calls.
"""

import asyncio
import time
import socket


class NetworkProbeSensor:
    def __init__(self, endpoints=None, timeout=3.0, latency_threshold=2.0,
                 poll_interval=30.0):
        """
        Args:
            endpoints: List of (host, port) tuples to probe.
            timeout: Socket timeout in seconds.
            latency_threshold: Latency (seconds) above which a warning fires.
            poll_interval: Minimum seconds between probe sweeps.
        """
        self.endpoints = endpoints or [
            ("api.openai.com", 443),    # Primary API dependency
            ("8.8.8.8", 53),            # Google DNS (basic internet check)
            ("1.1.1.1", 53),            # Cloudflare DNS (redundancy)
        ]
        self.timeout = timeout
        self.latency_threshold = latency_threshold
        self.poll_interval = poll_interval
        self._last_poll = 0
        self._last_status = {}  # Track previous state for change detection

    def _probe_endpoint(self, host, port):
        """
        Attempt a TCP connection to the endpoint.
        Returns (reachable: bool, latency_ms: float).
        """
        try:
            start = time.time()
            sock = socket.create_connection((host, port), timeout=self.timeout)
            latency = time.time() - start
            sock.close()
            return True, latency
        except (socket.timeout, socket.error, OSError):
            return False, float('inf')

    async def monitor(self):
        """
        Probes external endpoints.
        Returns (True, description) on connectivity issues, else (False, None).
        """
        now = time.time()
        if now - self._last_poll < self.poll_interval:
            return False, None
        self._last_poll = now

        alerts = []
        all_down = True

        # Bolt Performance Optimization:
        # Wrap blocking _probe_endpoint calls in asyncio.to_thread and execute them
        # concurrently with asyncio.gather to prevent event loop blocking and reduce
        # total network latency from O(N) to O(1).
        probe_tasks = [
            asyncio.to_thread(self._probe_endpoint, host, port)
            for host, port in self.endpoints
        ]
        results = await asyncio.gather(*probe_tasks)

        for (host, port), (reachable, latency) in zip(self.endpoints, results):
            endpoint_key = f"{host}:{port}"
            was_reachable = self._last_status.get(endpoint_key, True)

            if reachable:
                all_down = False
                if latency > self.latency_threshold:
                    alerts.append(f"{host} high latency ({latency:.2f}s)")
                if not was_reachable:
                    # Recovered!
                    alerts.append(f"{host} RECOVERED")
            else:
                if was_reachable:
                    alerts.append(f"{host}:{port} UNREACHABLE")

            self._last_status[endpoint_key] = reachable

        if all_down:
            return True, "NETWORK BLACKOUT: All endpoints unreachable. Switching to offline mode."

        if alerts:
            return True, f"Network anomaly: {'; '.join(alerts)}"

        return False, None

    def release(self):
        """No resources to release."""
        pass
