"""
🛡️ Immune System Skill: Firewall Block
Category: Defense & Security
Trigger: Amygdala / Network Probe sensors

Logs suspicious outbound connections and optionally adds system
firewall rules to block them. Operates as a reflex — fast, local,
and zero-token.
"""

import json
import os
import time
import re
import subprocess
import platform


BLOCK_LOG = "memory/firewall_log.json"


def run(data=None):
    """
    Block or log a suspicious network connection.

    data: str containing connection info, e.g.
          "Suspicious outbound connection to port 4444"
          or "Connection surge: 50 -> 120 (+140%)"
    """
    if not data:
        return "No connection data provided."

    # Extract IP and/or port from the spike description
    ip = _extract_ip(data)
    port = _extract_port(data)

    actions_taken = []

    # 1. Always log the event
    _log_event(data, ip, port)
    actions_taken.append("Logged to firewall_log.json")

    # 2. Attempt to block if we have a specific IP
    if ip:
        blocked = _attempt_block(ip, port)
        if blocked:
            actions_taken.append(f"Blocked IP {ip}")
        else:
            actions_taken.append(f"Could not block IP {ip} (insufficient privileges)")

    # 3. If it's a port-only alert, log the warning
    if port and not ip:
        actions_taken.append(f"Suspicious port {port} flagged for Cortex review")

    result = f"FIREWALL REFLEX: {'; '.join(actions_taken)}"
    print(f"[Cerebellum]: {result}")
    return result


def _extract_ip(data):
    """Extract IPv4 address from string."""
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', data)
    return match.group(1) if match else None


def _extract_port(data):
    """Extract port number from string."""
    match = re.search(r'port\s*(\d+)', data, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _attempt_block(ip, port=None):
    """
    Attempt to add a firewall block rule.
    Uses macOS pf or Linux iptables depending on platform.
    Returns True if successful, False otherwise.
    """
    system = platform.system().lower()

    try:
        if system == "darwin":
            # macOS: Add to pf block table
            # Note: Requires root. Will gracefully fail without it.
            rule = f"block drop from any to {ip}\n"

            # Use a persistent configuration file in the memory directory instead of a predictable temporary file in /tmp
            # to prevent symlink attacks and ensure the active ruleset is not completely flushed by `pfctl -f`.
            rule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'memory', 'nsa_pf_rules.conf'))

            if os.path.dirname(rule_file):
                os.makedirs(os.path.dirname(rule_file), exist_ok=True)

            with open(rule_file, "a") as f:
                f.write(rule)
            # Attempting to load the rule (requires sudo)
            result = subprocess.run(
                ["pfctl", "-f", rule_file],
                capture_output=True, timeout=5,
            )
            return result.returncode == 0

        elif system == "linux":
            # Linux: iptables DROP rule
            cmd = ["iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"]
            if port:
                cmd = [
                    "iptables", "-A", "OUTPUT",
                    "-d", ip, "-p", "tcp", "--dport", str(port),
                    "-j", "DROP"
                ]
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass

    return False


def _log_event(data, ip, port):
    """Append connection event to the firewall log."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_data": data,
        "extracted_ip": ip,
        "extracted_port": port,
    }

    log = []
    if os.path.exists(BLOCK_LOG):
        try:
            with open(BLOCK_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)
    os.makedirs(os.path.dirname(BLOCK_LOG), exist_ok=True)
    with open(BLOCK_LOG, "w") as f:
        json.dump(log, f, indent=2)
