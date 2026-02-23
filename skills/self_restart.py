"""
🫀 Autonomic Skill: Self Restart
Category: Self-Maintenance & Homeostasis
Trigger: Repeated error signals / prolonged instability

Gracefully restarts the NSA system when it detects prolonged instability
(repeated errors, memory leaks). The nervous system's equivalent of
"falling asleep and waking up" — a controlled reboot.
"""

import os
import sys
import time
import json


RESTART_LOG = "memory/restart_log.json"


def run(data=None):
    """
    Initiate a graceful self-restart of the NSA system.

    data: Optional str describing the reason for restart.
    """
    reason = data or "Manual restart requested"

    # 1. Log the restart event (so we know why we restarted)
    _log_restart(reason)

    # 2. Save current state marker
    state = {
        "restart_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "pid": os.getpid(),
        "python": sys.executable,
        "argv": sys.argv,
    }

    state_file = "memory/restart_state.json"
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    print(f"[Cerebellum]: SELF-RESTART initiated. Reason: {reason}")
    print(f"[Cerebellum]: State saved to {state_file}")

    # 3. Check if we're in a restart loop (safety valve)
    if _is_restart_loop():
        result = (
            "RESTART ABORTED: Restart loop detected "
            "(>3 restarts in 10 minutes). "
            "Escalating to Cortex for investigation."
        )
        print(f"[Cerebellum WARNING]: {result}")
        return result

    # 4. Execute restart via os.execv (replaces current process)
    # This preserves the same Python interpreter and arguments
    result = (
        f"SELF-RESTART: Restarting in 2 seconds. "
        f"Reason: {reason}. PID: {os.getpid()}"
    )
    print(f"[Cerebellum]: {result}")

    # Give sensors time to cleanup
    time.sleep(2)

    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        return f"RESTART FAILED: {e}. System remains running."

    return result  # Unreachable if execv succeeds


def _log_restart(reason):
    """Log restart event for loop detection."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "reason": reason,
        "pid": os.getpid(),
    }

    log = []
    if os.path.exists(RESTART_LOG):
        try:
            with open(RESTART_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)

    # Keep only last 50 entries
    log = log[-50:]

    os.makedirs(os.path.dirname(RESTART_LOG), exist_ok=True)
    with open(RESTART_LOG, "w") as f:
        json.dump(log, f, indent=2)


def _is_restart_loop():
    """Detect if we're in a restart loop (>3 restarts in 10 minutes)."""
    if not os.path.exists(RESTART_LOG):
        return False

    try:
        with open(RESTART_LOG, "r") as f:
            log = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    # Count restarts in the last 10 minutes
    cutoff = time.time() - 600  # 10 minutes
    recent = sum(1 for entry in log if entry.get("epoch", 0) > cutoff)

    return recent > 3
