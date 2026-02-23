"""
🫀 Autonomic Skill: Memory Cleanup (Synaptic Pruning)
Category: Self-Maintenance & Homeostasis
Trigger: Circadian sensor (Sleep Cycle) / Cognitive Load sensor

Purges old or redundant entries from the hippocampus database.
Analogous to synaptic pruning — removes memories older than N days
that have never been retrieved, keeping the memory system lean.
"""

import sqlite3
import os
import time
from datetime import datetime, timedelta


DB_PATH = "memory/long_term_memory.db"
DEFAULT_RETENTION_DAYS = 30
MAX_MEMORIES = 10000


def run(data=None):
    """
    Prune old and redundant memories from the hippocampus.

    data: Optional str with retention days, e.g. "retention:14"
    """
    retention_days = DEFAULT_RETENTION_DAYS
    if data:
        try:
            import re
            match = re.search(r'retention:(\d+)', data)
            if match:
                retention_days = int(match.group(1))
        except Exception:
            pass

    if not os.path.exists(DB_PATH):
        return "No memory database found. Nothing to prune."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count before
    cursor.execute("SELECT COUNT(*) FROM memories")
    count_before = cursor.fetchone()[0]

    if count_before == 0:
        conn.close()
        return "Memory database is empty. Nothing to prune."

    actions = []

    # 1. Remove memories older than retention period
    cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff,))
    old_deleted = cursor.rowcount
    if old_deleted > 0:
        actions.append(f"Pruned {old_deleted} memories older than {retention_days} days")

    # 2. If still too many, remove oldest entries beyond the cap
    cursor.execute("SELECT COUNT(*) FROM memories")
    current_count = cursor.fetchone()[0]
    if current_count > MAX_MEMORIES:
        excess = current_count - MAX_MEMORIES
        cursor.execute(
            "DELETE FROM memories WHERE id IN "
            "(SELECT id FROM memories ORDER BY timestamp ASC LIMIT ?)",
            (excess,)
        )
        actions.append(f"Capped: removed {excess} excess memories (limit: {MAX_MEMORIES})")

    # 3. Remove exact duplicate descriptions
    cursor.execute("""
        DELETE FROM memories WHERE id NOT IN (
            SELECT MIN(id) FROM memories GROUP BY description
        )
    """)
    dupes_deleted = cursor.rowcount
    if dupes_deleted > 0:
        actions.append(f"Deduplicated {dupes_deleted} exact duplicate memories")

    conn.commit()

    # Count after
    cursor.execute("SELECT COUNT(*) FROM memories")
    count_after = cursor.fetchone()[0]
    conn.close()

    # Reclaim space
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")
        conn.close()
    except Exception:
        pass

    if not actions:
        actions.append("No pruning needed — memory is healthy")

    result = (
        f"SYNAPTIC PRUNING: {count_before} -> {count_after} memories. "
        f"{'; '.join(actions)}"
    )
    print(f"[Cerebellum]: {result}")
    return result
