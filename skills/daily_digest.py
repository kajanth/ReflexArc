"""
🧬 Endocrine Skill: Daily Digest
Category: Scheduling & Communication
Trigger: Circadian sensor (Sleep Cycle / Protocol Gamma)

Generates a summary report from the day's hippocampus memories
and curiosity stats, then writes it to memory/digests/.
The organism's nightly "dream journal" — consolidating what happened today.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta


DIGESTS_DIR = "memory/digests"
STATS_FILE = "memory/stats.json"
DB_PATH = "memory/long_term_memory.db"


def run(data=None):
    """
    Generate a daily digest from today's memories and system stats.

    data: Optional context string.
    """
    os.makedirs(DIGESTS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    digest_file = os.path.join(DIGESTS_DIR, f"digest_{today}.md")

    # Gather data
    memories = _get_todays_memories()
    stats = _get_stats()
    skill_count = _count_skills()

    # Build digest
    lines = [
        f"# 🧠 NSA Daily Digest — {today}",
        f"_Generated: {datetime.now().strftime('%H:%M:%S')}_\n",
        "## 📊 System Metrics",
        f"- **Total Token Spend:** ${stats.get('total_spent', 0):.4f}",
        f"- **API Calls:** {stats.get('calls', 0)}",
        f"- **Avg Latency:** {stats.get('avg_latency', 0):.2f}s",
        f"- **Active Skills:** {skill_count}\n",
        f"## 🧬 Memories Recorded ({len(memories)})",
    ]

    if memories:
        # Group by sense type
        by_sense = {}
        for ts, sense, desc in memories:
            by_sense.setdefault(sense, []).append((ts, desc))

        for sense, events in by_sense.items():
            lines.append(f"\n### {sense.upper()} ({len(events)} events)")
            for ts, desc in events[:10]:  # Cap at 10 per sense
                lines.append(f"- `{ts}` {desc[:80]}")
            if len(events) > 10:
                lines.append(f"- _...and {len(events) - 10} more_")
    else:
        lines.append("_No new memories recorded today._\n")

    # Efficiency analysis
    lines.extend([
        "\n## ⚡ Efficiency Analysis",
        f"- **Cost per call:** ${(stats.get('total_spent', 0) / max(stats.get('calls', 1), 1)):.6f}",
        f"- **Budget remaining:** ${max(0, 0.50 - stats.get('total_spent', 0)):.4f} of $0.50/day",
    ])

    digest_content = "\n".join(lines)

    with open(digest_file, "w") as f:
        f.write(digest_content)

    result = (
        f"DAILY DIGEST generated: {digest_file} "
        f"({len(memories)} memories, ${stats.get('total_spent', 0):.4f} spent)"
    )
    print(f"[Cerebellum]: {result}")
    return result


def _get_todays_memories():
    """Retrieve today's memories from hippocampus."""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, sense_type, description FROM memories "
            "WHERE timestamp > datetime('now', '-1 day') "
            "ORDER BY timestamp DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def _get_stats():
    """Read current stats from curiosity sensor."""
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}


def _count_skills():
    """Count available skill scripts."""
    try:
        return len([f for f in os.listdir("skills")
                    if f.endswith(".py") and f != "__init__.py"])
    except OSError:
        return 0
