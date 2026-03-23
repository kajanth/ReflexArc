"""
Auto-generated skill: Short Snake Case Handler
Category: autonomic
Trigger: Generic event requiring a concise snake_case response action

A lightweight general-purpose skill that logs an event and returns
a structured acknowledgement. Used as a fallback for short-named triggers
that haven't been given a specialised handler yet.
"""

import re
from utils.logging_config import get_logger

logger = get_logger(__name__)


def _to_snake(text: str) -> str:
    """Convert arbitrary text to snake_case for structured logging."""
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', '_', text.strip().lower())


def run(data=None):
    """
    Handle short/generic events.

    Args:
        data: Event description or payload (string or dict)

    Returns:
        Status message
    """
    if isinstance(data, dict):
        event_type = data.get("type") or data.get("event") or "generic"
        payload = {k: v for k, v in data.items() if k not in ("type", "event")}
    else:
        event_type = _to_snake(str(data)[:40]) if data else "generic"
        payload = {"raw": str(data)[:200] if data else None}

    logger.info("short_snake_case_handler", event_type=event_type, payload=payload)
    return f"Event '{event_type}' acknowledged and logged"
