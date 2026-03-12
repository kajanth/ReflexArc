"""
Auto-generated skill: Proprioception Deleted Handler
Category: autonomic
Trigger: Filesystem sensor — file deletion event

Responds to file deletions by logging the event and checking whether
the deleted file was a critical skill or config.
"""

import os
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Files whose deletion warrants an elevated alert
CRITICAL_PATHS = {
    "brain.yaml", "main.py", "dream_engine.py", "api_server.py",
    "brain_core.py", "hippocampus.py",
}


def run(data=None):
    """
    Handle filesystem deletion events.

    Args:
        data: Event description (string or dict with 'file'/'path' key)

    Returns:
        Status message
    """
    event_desc = str(data)[:400] if data else "unknown"
    logger.info("proprioception_deleted", event=event_desc)

    # Try to extract the affected file path
    file_path = None
    if isinstance(data, dict):
        file_path = data.get("file") or data.get("path")
    elif isinstance(data, str):
        for token in data.split():
            if "/" in token or token.endswith(".py") or token.endswith(".yaml"):
                file_path = token
                break

    if file_path:
        basename = Path(file_path).name
        if basename in CRITICAL_PATHS:
            logger.error("critical_file_deleted", file=file_path,
                         action="ALERT — critical system file deleted, manual investigation required")
            return f"ALERT: Critical file deleted: {file_path}"

        logger.info("file_deleted", file=file_path)
        return f"File deletion logged: {file_path}"

    return f"Filesystem deletion event acknowledged: {event_desc[:120]}"
