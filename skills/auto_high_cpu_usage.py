"""
Skill: High CPU Usage Handler
Category: autonomic
Trigger: System Vitals sensor — cpu_percent exceeds threshold

Real implementation: identifies the top CPU-consuming processes via psutil,
logs them, publishes a structured event to the brain, and attempts to
SIGTERM or nicen the worst offender if it's a known-safe process.
"""

import os
import signal
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Processes that are safe to renice (lower priority) rather than terminate
RENICE_SAFE  = {"python3", "python", "node", "ruby", "java"}
# Processes that must NEVER be touched
PROTECTED = {"kernel_task", "launchd", "WindowServer", "loginwindow", "bash", "zsh", "ssh"}

# CPU % at which we escalate from warn → renice → SIGTERM
WARN_THRESHOLD  = 70.0
RENICE_THRESHOLD = 85.0
KILL_THRESHOLD  = 95.0


def _get_top_processes(n: int = 5) -> list[dict]:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "username", "status"]):
            try:
                info = p.info
                if info["status"] in ("zombie", "dead"):
                    continue
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        # Second pass to get stable cpu_percent (first call returns 0.0)
        import time; time.sleep(0.3)
        for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                for entry in procs:
                    if entry["pid"] == p.pid:
                        entry["cpu_percent"] = p.cpu_percent()
            except Exception:
                pass
        return sorted(procs, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:n]
    except ImportError:
        return []


def run(data=None):
    """
    Handle high CPU usage events from the system vitals sensor.

    Args:
        data: dict with keys 'metric', 'value', 'threshold' or a description string

    Returns:
        Status message describing action taken
    """
    # Parse trigger value
    cpu_value = None
    if isinstance(data, dict):
        cpu_value = float(data.get("value") or data.get("cpu_percent", 0))
    elif isinstance(data, str):
        import re
        m = re.search(r"(\d+\.?\d*)%?", data)
        if m:
            cpu_value = float(m.group(1))

    top_procs = _get_top_processes()
    top_summary = "; ".join(
        f"{p['name']}(pid={p['pid']}, {p.get('cpu_percent',0):.1f}%)"
        for p in top_procs
    )

    logger.warning("high_cpu_usage_detected",
                   cpu_value=cpu_value,
                   top_processes=top_summary)

    actions_taken = []

    for proc in top_procs[:1]:  # Only act on the top offender
        name = proc.get("name", "")
        pid  = proc.get("pid")
        pct  = proc.get("cpu_percent", 0)

        if name in PROTECTED or pid is None:
            continue

        try:
            import psutil
            p = psutil.Process(pid)

            if pct >= KILL_THRESHOLD and name in RENICE_SAFE:
                p.terminate()
                actions_taken.append(f"SIGTERM sent to {name}(pid={pid}) at {pct:.1f}%")
                logger.error("high_cpu_process_terminated", name=name, pid=pid, cpu_pct=pct)

            elif pct >= RENICE_THRESHOLD and name in RENICE_SAFE:
                # Lower priority (raise niceness) instead of killing
                current_nice = p.nice()
                p.nice(min(current_nice + 10, 19))
                actions_taken.append(f"Reniced {name}(pid={pid}) from nice={current_nice} to {p.nice()}")
                logger.warning("high_cpu_process_reniced", name=name, pid=pid, cpu_pct=pct)

        except Exception as e:
            logger.error("cpu_remediation_failed", name=name, pid=pid, error=str(e))

    if not actions_taken:
        actions_taken.append("Logged and monitored — no automatic action taken (process is protected or value below action threshold)")

    result = f"HIGH CPU ({cpu_value}%) — Top: {top_summary} — Actions: {'; '.join(actions_taken)}"
    logger.info("high_cpu_handled", result=result)
    return result
