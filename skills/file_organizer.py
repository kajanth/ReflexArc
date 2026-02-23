"""
🦾 Motor Cortex Skill: File Organizer
Category: Environment Interaction
Trigger: Filesystem (Proprioception) sensor

Reacts to filesystem change spikes. Auto-sorts new files in watched
directories, renames skill files following conventions, and archives
old logs. The organism's ability to "tidy up its workspace."
"""

import os
import shutil
import time
from datetime import datetime


ARCHIVE_DIR = "memory/archive"
SKILL_CONVENTIONS = {
    ".py": "skills",
    ".json": "memory",
    ".log": "memory/logs",
    ".txt": "memory/logs",
    ".md": ".",
}


def run(data=None):
    """
    Organize files based on filesystem change events.

    data: str describing the change, e.g.
          "Proprioception: CREATED: new_script.py; MODIFIED: config.json"
    """
    if not data:
        return "No filesystem event data provided."

    actions = []

    # Parse events from the proprioception spike
    events = _parse_events(data)

    for event_type, filename in events:
        if event_type == "CREATED":
            action = _handle_new_file(filename)
            if action:
                actions.append(action)

        elif event_type == "MODIFIED":
            action = _handle_modified_file(filename)
            if action:
                actions.append(action)

    if not actions:
        actions.append("No organizational action needed")

    result = f"FILE ORGANIZER: {'; '.join(actions)}"
    print(f"[Cerebellum]: {result}")
    return result


def _parse_events(data):
    """Extract (event_type, filename) pairs from spike description."""
    events = []
    # Format: "Proprioception: CREATED: file.py; MODIFIED: other.json"
    parts = data.replace("Proprioception: ", "").split(";")
    for part in parts:
        part = part.strip()
        for event_type in ["CREATED", "MODIFIED", "DELETED", "MOVED"]:
            if part.startswith(f"{event_type}:"):
                filename = part[len(event_type) + 1:].strip()
                events.append((event_type, filename))
                break
    return events


def _handle_new_file(filename):
    """Handle a newly created file — check conventions and placement."""
    basename = os.path.basename(filename)
    ext = os.path.splitext(basename)[1].lower()

    # Check if the file is a new auto-generated skill (from optimization cycle)
    if basename.startswith("auto_skill_") and ext == ".py":
        # Verify it has the run() function
        full_path = os.path.join("skills", basename)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r") as f:
                    content = f.read()
                if "def run(" not in content:
                    # Invalid skill — quarantine it
                    quarantine = os.path.join(ARCHIVE_DIR, "invalid_skills")
                    os.makedirs(quarantine, exist_ok=True)
                    shutil.move(full_path, os.path.join(quarantine, basename))
                    return f"Quarantined invalid skill: {basename} (missing run())"
                return f"New auto-skill validated: {basename}"
            except Exception:
                pass

    # Log any new file creation
    return f"Noted: {basename} created"


def _handle_modified_file(filename):
    """Handle a modified file — backup if critical."""
    basename = os.path.basename(filename)

    # Auto-backup modified skill files
    if basename.endswith(".py") and os.path.exists(os.path.join("skills", basename)):
        backup_dir = os.path.join(ARCHIVE_DIR, "skill_backups")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{basename}.{timestamp}.bak"

        try:
            source = os.path.join("skills", basename)
            shutil.copy2(source, os.path.join(backup_dir, backup_name))
            return f"Backed up modified skill: {basename}"
        except Exception:
            pass

    return None
