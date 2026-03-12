"""
Skill: Filesystem Modification Handler (Proprioception Modified)
Category: autonomic
Trigger: Filesystem sensor — a file has been modified

Real implementation: validates the modified file's content (syntax check
for Python files), detects if it's a critical system file, reads its diff
via git if possible, and logs a structured change record to the agent
activity log. If the file is a skill, it hot-reloads it.
"""

import ast
import importlib
import os
import subprocess
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

CRITICAL_FILES = {
    "main.py", "brain_core.py", "dream_engine.py", "api_server.py",
    "event_bus.py", "sensor_manager.py", "plugin_loader.py",
    "brain.yaml", "secrets.yaml",
}


def _git_diff(filepath: str) -> str | None:
    """Return a short unified diff for the file if it's tracked by git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=3", "--", filepath],
            capture_output=True, text=True, timeout=5,
            cwd=Path(filepath).parent if os.path.isabs(filepath) else "."
        )
        diff = result.stdout.strip()
        return diff[:1000] if diff else None
    except Exception:
        return None


def _hot_reload_skill(module_name: str) -> str:
    """Attempt to reload a skill module so the new code takes effect immediately."""
    try:
        mod = importlib.import_module(module_name)
        importlib.reload(mod)
        return f"Hot-reloaded {module_name} successfully"
    except Exception as e:
        return f"Hot-reload failed for {module_name}: {e}"


def run(data=None):
    """
    Handle a filesystem modification event.

    Args:
        data: dict with 'file'/'path' key, or a description string

    Returns:
        Status message
    """
    file_path = None
    if isinstance(data, dict):
        file_path = data.get("file") or data.get("path")
    elif isinstance(data, str):
        for token in data.split():
            candidate = token.strip("'\"(),")
            if os.path.exists(candidate):
                file_path = candidate
                break

    if not file_path or not os.path.exists(file_path):
        logger.info("proprioception_modified_no_path", evt=str(data)[:200])
        return f"Filesystem modification noted (path not resolved): {str(data)[:100]}"

    p = Path(file_path)
    basename = p.name
    is_critical = basename in CRITICAL_FILES
    actions = []

    # 1. Syntax check Python files
    if p.suffix == ".py":
        try:
            source = p.read_text(encoding="utf-8")
            if not source.strip():
                logger.warning("modified_file_is_empty", file=file_path)
                actions.append("WARNING: file is now empty — skill will crash on next invocation")
            else:
                ast.parse(source)
                actions.append("syntax check passed")
        except SyntaxError as e:
            logger.error("modified_file_syntax_error", file=file_path, error=str(e))
            actions.append(f"SYNTAX ERROR: {e}")

    # 2. Diff via git
    diff = _git_diff(file_path)
    if diff:
        actions.append(f"git diff: {len(diff.splitlines())} lines changed")
        logger.info("file_modified_diff", file=file_path, diff_lines=len(diff.splitlines()))

    # 3. Hot-reload if it's a skill
    if str(p).startswith("skills/") or "/skills/" in str(p):
        module_name = "skills." + p.stem
        reload_result = _hot_reload_skill(module_name)
        actions.append(reload_result)

    # 4. Escalate if critical
    if is_critical:
        logger.error("critical_system_file_modified", file=file_path,
                     message="A core system file was modified. Manual review recommended.")
        actions.append("ALERT: critical system file — manual review recommended")

    logger.info("proprioception_modified",
                file=file_path,
                critical=is_critical,
                actions=actions)

    return f"Modified: {file_path} — {'CRITICAL ' if is_critical else ''}Actions: {'; '.join(actions)}"
