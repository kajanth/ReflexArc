"""
Auto-generated skill: Proprioception Created/Modified Handler
Category: autonomic
Trigger: Filesystem sensor — file creation or modification event

Monitors new or modified Python skills/modules for syntax validity and
logs them to the agent activity log.
"""

import ast
import os
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)


def run(data=None):
    """
    Handle filesystem create/modify events for skill files.

    Args:
        data: Event description from the filesystem sensor (string or dict)

    Returns:
        Status message
    """
    event_desc = str(data)[:400] if data else "unknown"
    logger.info("proprioception_created_modified", evt=event_desc)

    # Try to extract the affected file path from the event description
    file_path = None
    if isinstance(data, dict):
        file_path = data.get("file") or data.get("path")
    elif isinstance(data, str):
        # Simple heuristic: look for a recognisable path token
        for token in data.split():
            if token.endswith(".py") and os.path.exists(token):
                file_path = token
                break

    if file_path and Path(file_path).suffix == ".py":
        try:
            source = Path(file_path).read_text(encoding="utf-8")
            if source.strip():
                ast.parse(source)
                logger.info("skill_syntax_ok", file=file_path)
                return f"File created/modified and syntax-validated: {file_path}"
            else:
                logger.warning("skill_file_empty", file=file_path,
                               suggestion="File is empty — it will crash on import. Add a run() function.")
                return f"WARNING: file {file_path} is empty — no run() function defined"
        except SyntaxError as e:
            logger.error("skill_syntax_error", file=file_path, error=str(e))
            return f"Syntax error in {file_path}: {e}"

    logger.info("proprioception_created_modified_generic", evt=event_desc)
    return f"Filesystem create/modify event acknowledged: {event_desc[:120]}"
