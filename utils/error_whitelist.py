"""
🚨 ReflexArc Error Whitelist System

Tracks how often each error occurs across the system. When an error exceeds
a configurable threshold, it is flagged to the user via the dashboard with
two options:
  - Whitelist: Suppress future notifications for this error
  - Keep Flagging: Continue alerting each time it appears

Files:
  memory/error_tasks.json    — raw error backlog (written by logging interceptor)
  memory/error_whitelist.json — user-approved suppressions
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

ERROR_TASKS_FILE = Path("memory/error_tasks.json")
WHITELIST_FILE = Path("memory/error_whitelist.json")

# How many times the same error must appear before alerting the user
RECURRENCE_THRESHOLD = 3


# ─── Whitelist Operations ─────────────────────────────────────

def load_whitelist() -> Dict[str, Any]:
    """Load the error whitelist from disk."""
    if not WHITELIST_FILE.exists():
        return {}
    try:
        with open(WHITELIST_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_whitelist(whitelist: Dict[str, Any]) -> None:
    """Persist the whitelist to disk."""
    WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WHITELIST_FILE, "w") as f:
        json.dump(whitelist, f, indent=2)


def whitelist_error(error_key: str, reason: str = "user_approved") -> None:
    """
    Add an error key to the whitelist so it won't be flagged again.

    Args:
        error_key: Typically "{logger}::{message}"
        reason: Human-readable reason for whitelisting
    """
    whitelist = load_whitelist()
    whitelist[error_key] = {
        "whitelisted_at": datetime.now().isoformat(),
        "reason": reason,
    }
    save_whitelist(whitelist)


def is_whitelisted(error_key: str) -> bool:
    """Return True if this error key has been whitelisted by the user."""
    whitelist = load_whitelist()
    return error_key in whitelist


def remove_from_whitelist(error_key: str) -> None:
    """Remove an error from the whitelist (re-enable flagging)."""
    whitelist = load_whitelist()
    whitelist.pop(error_key, None)
    save_whitelist(whitelist)


# ─── Recurrence Detection ─────────────────────────────────────

def _error_key(task: Dict[str, Any]) -> str:
    """Build a stable key for grouping similar errors."""
    logger = task.get("logger", "unknown")
    message = task.get("message", "")[:80]  # Limit to 80 chars for key stability
    return f"{logger}::{message}"


def check_recurring_errors(threshold: int = RECURRENCE_THRESHOLD) -> List[Dict[str, Any]]:
    """
    Scan error_tasks.json and return errors that exceed the recurrence threshold
    and are not already whitelisted.

    Returns a list of alert dicts ready to be published to the event_bus.
    """
    if not ERROR_TASKS_FILE.exists():
        return []

    try:
        with open(ERROR_TASKS_FILE, "r") as f:
            tasks = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    # Count occurrences per error key
    counts: Dict[str, int] = {}
    examples: Dict[str, Dict] = {}
    for task in tasks:
        key = _error_key(task)
        counts[key] = counts.get(key, 0) + 1
        if key not in examples:
            examples[key] = task

    alerts = []
    whitelist = load_whitelist()
    for key, count in counts.items():
        if count >= threshold and key not in whitelist:
            example = examples[key]
            alerts.append({
                "type": "recurring_error",
                "error_key": key,
                "logger": example.get("logger", "unknown"),
                "message": example.get("message", ""),
                "severity": example.get("severity", "error"),
                "occurrences": count,
                "first_seen": example.get("time_str", ""),
                "action_whitelist_url": f"/errors/whitelist?key={key}",
            })

    return alerts


def mark_errors_reviewed(error_key: str) -> None:
    """Mark all pending tasks with this key as reviewed."""
    if not ERROR_TASKS_FILE.exists():
        return
    try:
        with open(ERROR_TASKS_FILE, "r") as f:
            tasks = json.load(f)
        for t in tasks:
            if _error_key(t) == error_key:
                t["status"] = "reviewed"
        with open(ERROR_TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=2)
    except (json.JSONDecodeError, IOError):
        pass
