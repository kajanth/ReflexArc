"""
⚡ Metabolic Skill: Cognitive Defrag
Category: Resource & Cost Optimization
Trigger: Circadian sensor (Sleep Cycle) / Cognitive Load sensor

Analyzes hippocampus memory patterns to identify duplicate/similar
memories, merges them, and removes near-duplicate embedding vectors.
The brain's version of "sleep spindles" — memory consolidation and
deduplication that happens during sleep.
"""

import sqlite3
import numpy as np
import os
import time
from datetime import datetime


DB_PATH = "memory/long_term_memory.db"
SIMILARITY_THRESHOLD = 0.92  # Memories above this similarity are considered duplicates
DEFRAG_LOG = "memory/defrag_log.json"


def run(data=None):
    """
    Defragment the hippocampus by merging similar memories.

    data: Optional str, unused.
    """
    if not os.path.exists(DB_PATH):
        return "No memory database found. Nothing to defragment."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load all memories with vectors
    cursor.execute("SELECT id, description, vector, timestamp FROM memories ORDER BY id")
    rows = cursor.fetchall()

    if len(rows) < 2:
        conn.close()
        return "Too few memories to defragment."

    # Build similarity matrix and find clusters
    duplicates_found = []
    ids_to_remove = set()

    # Compare each pair (O(n²) — acceptable for moderate memory sizes)
    for i in range(len(rows)):
        if rows[i][0] in ids_to_remove:
            continue

        id_a, desc_a, vec_blob_a, ts_a = rows[i]
        if not vec_blob_a:
            continue

        vec_a = np.frombuffer(vec_blob_a, dtype=np.float32)
        norm_a = np.linalg.norm(vec_a)
        if norm_a == 0:
            continue

        for j in range(i + 1, len(rows)):
            if rows[j][0] in ids_to_remove:
                continue

            id_b, desc_b, vec_blob_b, ts_b = rows[j]
            if not vec_blob_b:
                continue

            vec_b = np.frombuffer(vec_blob_b, dtype=np.float32)
            norm_b = np.linalg.norm(vec_b)
            if norm_b == 0:
                continue

            # Cosine similarity
            similarity = np.dot(vec_a, vec_b) / (norm_a * norm_b)

            if similarity > SIMILARITY_THRESHOLD:
                # Keep the newer memory (more recent context), remove the older
                ids_to_remove.add(id_a)
                duplicates_found.append({
                    "kept": id_b,
                    "removed": id_a,
                    "similarity": float(similarity),
                    "kept_desc": desc_b[:50],
                    "removed_desc": desc_a[:50],
                })
                break  # Move to next i — this one is marked for removal

    # Execute removals
    if ids_to_remove:
        placeholders = ",".join("?" * len(ids_to_remove))
        cursor.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})",
            list(ids_to_remove)
        )
        conn.commit()

    # Get final count
    cursor.execute("SELECT COUNT(*) FROM memories")
    remaining = cursor.fetchone()[0]
    conn.close()

    # Vacuum to reclaim space
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")
        conn.close()
    except Exception:
        pass

    # Log the defrag results
    _log_defrag(len(rows), remaining, duplicates_found)

    if duplicates_found:
        result = (
            f"COGNITIVE DEFRAG: Removed {len(ids_to_remove)} near-duplicate "
            f"memories (threshold: {SIMILARITY_THRESHOLD}). "
            f"{len(rows)} -> {remaining} memories. "
            f"Top merge: '{duplicates_found[0]['removed_desc']}' "
            f"≈ '{duplicates_found[0]['kept_desc']}' "
            f"({duplicates_found[0]['similarity']:.1%} similar)"
        )
    else:
        result = (
            f"COGNITIVE DEFRAG: No near-duplicates found among "
            f"{len(rows)} memories (threshold: {SIMILARITY_THRESHOLD}). "
            f"Memory is clean."
        )

    print(f"[Cerebellum]: {result}")
    return result


def _log_defrag(before, after, duplicates):
    """Log defragmentation results."""
    import json

    entry = {
        "timestamp": datetime.now().isoformat(),
        "memories_before": before,
        "memories_after": after,
        "duplicates_removed": len(duplicates),
        "threshold": SIMILARITY_THRESHOLD,
        "merges": duplicates[:10],  # Log up to 10 examples
    }

    log = []
    if os.path.exists(DEFRAG_LOG):
        try:
            with open(DEFRAG_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)
    log = log[-50:]

    os.makedirs(os.path.dirname(DEFRAG_LOG), exist_ok=True)
    with open(DEFRAG_LOG, "w") as f:
        json.dump(log, f, indent=2)
