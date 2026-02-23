"""
🫀 Autonomic Skill: Disk Pressure Relief
Category: Self-Maintenance & Homeostasis
Trigger: System Vitals sensor (Disk > 95% threshold)

When disk usage is critical, cleans temporary files, old logs,
__pycache__ directories, and rotates large log files. A direct
reflex to the "PAIN SIGNAL" from the nociceptors.
"""

import os
import shutil
import time
import glob
from datetime import datetime, timedelta


# Directories to clean
TEMP_DIRS = ["/tmp/nsa_*", "__pycache__"]
LOG_DIR = "memory"
LOG_MAX_SIZE_MB = 10
LOG_ROTATE_DAYS = 7


def run(data=None):
    """
    Relieve disk pressure by cleaning temp files and rotating logs.

    data: Optional str with context about disk state.
    """
    freed_bytes = 0
    actions = []

    # 1. Clean __pycache__ directories recursively
    pycache_bytes = _clean_pycache(".")
    if pycache_bytes > 0:
        freed_bytes += pycache_bytes
        actions.append(f"Cleaned __pycache__: {_human_size(pycache_bytes)}")

    # 2. Clean .pyc files
    pyc_bytes = _clean_pattern(".", "*.pyc")
    if pyc_bytes > 0:
        freed_bytes += pyc_bytes
        actions.append(f"Removed .pyc files: {_human_size(pyc_bytes)}")

    # 3. Rotate large log files
    rotated = _rotate_logs()
    if rotated:
        actions.append(f"Rotated {rotated} oversized log files")

    # 4. Clean old forensic snapshots (keep last 10)
    forensic_cleaned = _clean_old_snapshots("memory/forensics", keep=10)
    if forensic_cleaned > 0:
        actions.append(f"Archived {forensic_cleaned} old forensic snapshots")

    # 5. Clean old digest files (keep last 30)
    digest_cleaned = _clean_old_snapshots("memory/digests", keep=30)
    if digest_cleaned > 0:
        actions.append(f"Archived {digest_cleaned} old digests")

    # 6. SQLite VACUUM on memory database
    try:
        import sqlite3
        db_path = "memory/long_term_memory.db"
        if os.path.exists(db_path):
            size_before = os.path.getsize(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute("VACUUM")
            conn.close()
            size_after = os.path.getsize(db_path)
            saved = size_before - size_after
            if saved > 0:
                freed_bytes += saved
                actions.append(f"VACUUM'd database: {_human_size(saved)} recovered")
    except Exception:
        pass

    if not actions:
        actions.append("Disk is clean — no pressure relief needed")

    result = (
        f"DISK PRESSURE RELIEF: {_human_size(freed_bytes)} freed. "
        f"{'; '.join(actions)}"
    )
    print(f"[Cerebellum]: {result}")
    return result


def _clean_pycache(root):
    """Remove all __pycache__ directories recursively."""
    total = 0
    for dirpath, dirnames, _ in os.walk(root):
        for d in dirnames:
            if d == "__pycache__":
                full = os.path.join(dirpath, d)
                try:
                    size = _dir_size(full)
                    shutil.rmtree(full)
                    total += size
                except Exception:
                    pass
    return total


def _clean_pattern(root, pattern):
    """Remove files matching a glob pattern recursively."""
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if glob.fnmatch.fnmatch(f, pattern):
                full = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(full)
                    os.remove(full)
                except Exception:
                    pass
    return total


def _rotate_logs():
    """Rotate log files larger than LOG_MAX_SIZE_MB."""
    rotated = 0
    for f in glob.glob("*.log") + glob.glob("*.txt"):
        try:
            if os.path.getsize(f) > LOG_MAX_SIZE_MB * 1024 * 1024:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{f}.{timestamp}.bak"
                os.rename(f, rotated_name)
                # Create empty replacement
                open(f, "w").close()
                rotated += 1
        except Exception:
            pass
    return rotated


def _clean_old_snapshots(directory, keep=10):
    """Remove oldest files in a directory, keeping only the most recent N."""
    if not os.path.isdir(directory):
        return 0
    files = sorted(
        [os.path.join(directory, f) for f in os.listdir(directory)
         if os.path.isfile(os.path.join(directory, f))],
        key=os.path.getmtime,
        reverse=True
    )
    removed = 0
    for f in files[keep:]:
        try:
            os.remove(f)
            removed += 1
        except Exception:
            pass
    return removed


def _dir_size(path):
    """Calculate total size of a directory."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except Exception:
                pass
    return total


def _human_size(bytes_val):
    """Convert bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"
