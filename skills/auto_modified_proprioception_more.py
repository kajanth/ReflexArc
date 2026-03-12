"""
Auto-generated skill: Proprioception More Handler
Category: autonomic
Trigger: Filesystem sensor — bulk/repeated modification events

Handles burst filesystem events by aggregating them and writing a summary
to the agent activity log to prevent event flooding.
"""

import time
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Simple in-process dedup window (5 seconds)
_last_seen: dict[str, float] = {}
_DEDUP_WINDOW = 5.0


def run(data=None):
    """
    Handle repeated filesystem modification events with deduplication.

    Args:
        data: Event description (string or dict)

    Returns:
        Status message
    """
    event_desc = str(data)[:400] if data else "unknown"

    # Deduplicate within window
    now = time.time()
    last = _last_seen.get(event_desc[:60], 0)
    if now - last < _DEDUP_WINDOW:
        return f"Duplicate fs event suppressed (within {_DEDUP_WINDOW}s window)"

    _last_seen[event_desc[:60]] = now
    # Prune old entries
    cutoff = now - 60
    to_remove = [k for k, v in _last_seen.items() if v < cutoff]
    for k in to_remove:
        del _last_seen[k]

    logger.info("proprioception_more", evt=event_desc, active_tracked=len(_last_seen))
    return f"Filesystem burst event logged ({len(_last_seen)} active paths tracked)"
