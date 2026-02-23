"""
🧬 Endocrine Skill: Schedule Task
Category: Scheduling & Communication
Trigger: Circadian sensor / Manual

Manages a simple cron-like task queue stored in memory/schedule.json.
The Circadian sensor checks this queue each cycle and fires skills
at their scheduled times. Think of it as the organism's "hormone release
schedule" — timed actions that regulate system behavior.
"""

import json
import os
import time
from datetime import datetime


SCHEDULE_FILE = "memory/schedule.json"


def run(data=None):
    """
    Manage the task schedule. Actions:
    - "check" or None: Check and execute due tasks
    - "add:<skill>:<cron_hour>:<description>" : Schedule a new task
    - "list": List all scheduled tasks
    - "clear": Clear all scheduled tasks

    data: str with the action command.
    """
    _ensure_schedule()

    if not data or data.strip().lower() == "check":
        return _check_and_execute()
    elif data.strip().lower().startswith("add:"):
        return _add_task(data)
    elif data.strip().lower() == "list":
        return _list_tasks()
    elif data.strip().lower() == "clear":
        return _clear_tasks()
    else:
        # Default: treat data as a check command
        return _check_and_execute()


def _ensure_schedule():
    """Create schedule file if it doesn't exist."""
    os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
    if not os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "w") as f:
            json.dump({"tasks": []}, f, indent=2)


def _load_schedule():
    """Load the schedule from disk."""
    try:
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"tasks": []}


def _save_schedule(schedule):
    """Save the schedule to disk."""
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f, indent=2)


def _add_task(data):
    """
    Add a scheduled task.
    Format: "add:<skill_name>:<hour_24h>:<description>"
    Example: "add:memory_cleanup:3:Nightly memory pruning"
    """
    parts = data.split(":", 3)
    if len(parts) < 3:
        return "Invalid format. Use: add:<skill>:<hour>:<description>"

    _, skill_name, hour_str = parts[0], parts[1], parts[2]
    description = parts[3] if len(parts) > 3 else f"Scheduled {skill_name}"

    try:
        hour = int(hour_str)
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        return f"Invalid hour '{hour_str}'. Must be 0-23."

    schedule = _load_schedule()
    task = {
        "id": len(schedule["tasks"]) + 1,
        "skill": skill_name,
        "hour": hour,
        "description": description,
        "enabled": True,
        "last_run": None,
        "created": datetime.now().isoformat(),
    }
    schedule["tasks"].append(task)
    _save_schedule(schedule)

    result = f"SCHEDULED: '{skill_name}' at {hour:02d}:00 — {description}"
    print(f"[Cerebellum]: {result}")
    return result


def _check_and_execute():
    """Check for due tasks and execute them."""
    schedule = _load_schedule()
    current_hour = datetime.now().hour
    today = datetime.now().strftime("%Y-%m-%d")
    executed = []

    for task in schedule["tasks"]:
        if not task.get("enabled", True):
            continue

        if task["hour"] != current_hour:
            continue

        # Check if already run today
        last_run = task.get("last_run", "")
        if last_run and last_run.startswith(today):
            continue

        # Execute the scheduled skill
        skill_name = task["skill"]
        try:
            import importlib
            module = importlib.import_module(f"skills.{skill_name}")
            importlib.reload(module)
            result = module.run(task.get("description"))
            task["last_run"] = datetime.now().isoformat()
            executed.append(f"{skill_name}: OK")
        except Exception as e:
            task["last_run"] = datetime.now().isoformat()
            executed.append(f"{skill_name}: FAILED ({e})")

    _save_schedule(schedule)

    if executed:
        result = f"SCHEDULE CHECK: Executed {len(executed)} task(s) — {'; '.join(executed)}"
    else:
        result = f"SCHEDULE CHECK: No tasks due at hour {current_hour:02d}:00"

    print(f"[Cerebellum]: {result}")
    return result


def _list_tasks():
    """List all scheduled tasks."""
    schedule = _load_schedule()
    tasks = schedule.get("tasks", [])

    if not tasks:
        return "SCHEDULE: No tasks configured."

    lines = [f"SCHEDULE ({len(tasks)} tasks):"]
    for t in tasks:
        status = "✓" if t.get("enabled", True) else "✗"
        lines.append(
            f"  [{status}] #{t['id']} {t['skill']} @ {t['hour']:02d}:00 — "
            f"{t.get('description', '')} (last: {t.get('last_run', 'never')})"
        )

    result = "\n".join(lines)
    print(f"[Cerebellum]: {result}")
    return result


def _clear_tasks():
    """Clear all scheduled tasks."""
    _save_schedule({"tasks": []})
    result = "SCHEDULE: All tasks cleared."
    print(f"[Cerebellum]: {result}")
    return result
