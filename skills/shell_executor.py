"""
🦾 Motor Cortex Skill: Shell Executor
Category: Environment Interaction
Trigger: Cortex delegation / Triage routing

Safely executes whitelisted shell commands. Only pre-approved commands
are allowed — this is a sandboxed reflex, not an arbitrary command runner.
Provides the Cortex with a way to "use its hands" without writing
a new skill every time.
"""

import subprocess
import os
import time
import re


# Strict whitelist: only these commands can be executed
COMMAND_WHITELIST = {
    "uptime":       {"cmd": ["uptime"], "description": "System uptime"},
    "df":           {"cmd": ["df", "-h"], "description": "Disk usage"},
    "free":         {"cmd": ["free", "-h"], "description": "Memory usage (Linux)"},
    "vm_stat":      {"cmd": ["vm_stat"], "description": "Memory usage (macOS)"},
    "who":          {"cmd": ["who"], "description": "Logged-in users"},
    "git_status":   {"cmd": ["git", "status", "--short"], "description": "Git status"},
    "git_log":      {"cmd": ["git", "log", "--oneline", "-5"], "description": "Recent commits"},
    "ls_skills":    {"cmd": ["ls", "-la", "skills/"], "description": "List skill files"},
    "ls_memory":    {"cmd": ["ls", "-la", "memory/"], "description": "List memory files"},
    "hostname":     {"cmd": ["hostname"], "description": "System hostname"},
    "date":         {"cmd": ["date"], "description": "Current date/time"},
    "ping_google":  {"cmd": ["ping", "-c", "1", "8.8.8.8"], "description": "Ping Google DNS"},
    "ps_summary":   {"cmd": ["ps", "aux", "--sort=-pcpu"], "description": "Process list by CPU"},
}

# Maximum output length (characters) to prevent flooding
MAX_OUTPUT_LENGTH = 2000
EXECUTION_TIMEOUT = 10  # seconds


def run(data=None):
    """
    Execute a whitelisted shell command.

    data: str with the command alias, e.g. "uptime" or "git_status"
          If data is "list", returns available commands.
    """
    if not data or data.strip().lower() == "list":
        return _list_commands()

    command_name = _resolve_command(data.strip().lower())

    if command_name not in COMMAND_WHITELIST:
        available = ", ".join(sorted(COMMAND_WHITELIST.keys()))
        return (
            f"BLOCKED: '{data}' is not a whitelisted command. "
            f"Available: {available}"
        )

    cmd_entry = COMMAND_WHITELIST[command_name]
    cmd = cmd_entry["cmd"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=os.getcwd(),
        )

        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[stderr]: {result.stderr.strip()}"

        # Truncate if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n... [truncated, {len(output)} chars total]"

        status = "OK" if result.returncode == 0 else f"EXIT:{result.returncode}"
        response = f"SHELL [{command_name}] ({status}):\n{output}"

    except subprocess.TimeoutExpired:
        response = f"SHELL [{command_name}]: TIMEOUT after {EXECUTION_TIMEOUT}s"
    except FileNotFoundError:
        response = f"SHELL [{command_name}]: Command not found on this system"
    except Exception as e:
        response = f"SHELL [{command_name}]: ERROR — {e}"

    print(f"[Cerebellum]: {response[:200]}")
    return response


def _resolve_command(data):
    """Try to fuzzy-match the input to a whitelisted command."""
    # Direct match
    if data in COMMAND_WHITELIST:
        return data

    # Try with underscores/hyphens
    normalized = data.replace("-", "_").replace(" ", "_")
    if normalized in COMMAND_WHITELIST:
        return normalized

    # Try partial match
    for key in COMMAND_WHITELIST:
        if key.startswith(data) or data in key:
            return key

    return data  # Will fail the whitelist check


def _list_commands():
    """Return a formatted list of available commands."""
    lines = ["SHELL EXECUTOR — Available Commands:"]
    for name, entry in sorted(COMMAND_WHITELIST.items()):
        cmd_str = " ".join(entry["cmd"])
        lines.append(f"  • {name:15s} → {cmd_str:30s} ({entry['description']})")
    result = "\n".join(lines)
    print(f"[Cerebellum]: {result}")
    return result
