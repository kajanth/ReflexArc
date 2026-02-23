"""
🛡️ Immune System Skill: Quarantine Process
Category: Defense & Security
Trigger: Amygdala (Threat Detection) sensor

Kills or suspends a suspicious process by PID or name.
When the threat sensor detects an unknown process, this reflex
isolates it before the Cortex investigates.
"""

import psutil
import os
import json
import time


# Processes that must NEVER be killed (safety whitelist)
PROTECTED_PROCESSES = {
    "python", "python3", "bash", "zsh", "sh", "sshd",
    "systemd", "launchd", "loginwindow", "WindowServer",
    "Finder", "Dock", "kernel_task", "init",
}

QUARANTINE_LOG = "memory/quarantine_log.json"


def run(data=None):
    """
    Quarantine a suspicious process.

    data: str containing process info, e.g.
          "New process: suspicious_app (PID: 12345, User: root)"
    """
    if not data:
        return "No process data provided."

    # Extract PID from the data string
    pid = _extract_pid(data)
    if pid is None:
        return f"Could not extract PID from: {data}"

    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc_user = proc.username()

        # Safety check: never kill protected processes
        if proc_name.lower() in {p.lower() for p in PROTECTED_PROCESSES}:
            _log_action(pid, proc_name, "SKIPPED", "Protected process")
            return f"SKIPPED: '{proc_name}' (PID: {pid}) is a protected process."

        # Attempt to suspend first (less destructive than kill)
        proc.suspend()
        _log_action(pid, proc_name, "SUSPENDED", f"User: {proc_user}")
        
        return (
            f"QUARANTINED: '{proc_name}' (PID: {pid}) suspended. "
            f"User: {proc_user}. Awaiting Cortex review for termination."
        )

    except psutil.NoSuchProcess:
        return f"Process PID {pid} no longer exists."
    except psutil.AccessDenied:
        _log_action(pid, "unknown", "ACCESS_DENIED", "Insufficient permissions")
        return f"ACCESS DENIED: Cannot quarantine PID {pid}. Escalate to Cortex."
    except Exception as e:
        return f"Quarantine failed: {e}"


def _extract_pid(data):
    """Parse PID from spike description string."""
    import re
    match = re.search(r'PID:\s*(\d+)', data)
    if match:
        return int(match.group(1))
    # Try bare number
    match = re.search(r'\b(\d{3,7})\b', data)
    if match:
        return int(match.group(1))
    return None


def _log_action(pid, name, action, detail):
    """Append quarantine action to the log."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pid": pid,
        "process": name,
        "action": action,
        "detail": detail,
    }

    log = []
    if os.path.exists(QUARANTINE_LOG):
        try:
            with open(QUARANTINE_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)

    os.makedirs(os.path.dirname(QUARANTINE_LOG), exist_ok=True)
    with open(QUARANTINE_LOG, "w") as f:
        json.dump(log, f, indent=2)
