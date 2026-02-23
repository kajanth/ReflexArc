"""
⚡ Metabolic Skill: Token Budget Enforcer
Category: Resource & Cost Optimization
Trigger: Cognitive Load sensor / Curiosity sensor

Hard-blocks Cortex calls when daily spending exceeds the $0.50 budget
from agent.md. Forces all decisions to REFLEX or LOG. The organism's
"starvation response" — when energy reserves are depleted, only
cheap reflexes are allowed.
"""

import json
import os
import time
from datetime import datetime


STATS_FILE = "memory/stats.json"
BUDGET_FILE = "memory/budget_config.json"
ENFORCEMENT_LOG = "memory/budget_enforcement.log"

DEFAULT_DAILY_BUDGET = 0.50  # From agent.md: "Daily operating cost remains below $0.50"
DEFAULT_WARNING_THRESHOLD = 0.80  # Warn at 80% of budget


def run(data=None):
    """
    Check spending against budget and enforce limits.

    data: Optional str:
          - None or "check": Check current budget status
          - "set:<amount>": Set daily budget
          - "reset": Reset daily spending counter
    """
    if data and data.strip().lower().startswith("set:"):
        return _set_budget(data)
    elif data and data.strip().lower() == "reset":
        return _reset_spending()
    else:
        return _check_budget()


def _check_budget():
    """Check current spending against the daily budget."""
    stats = _get_stats()
    config = _get_config()

    daily_budget = config.get("daily_budget", DEFAULT_DAILY_BUDGET)
    warning_pct = config.get("warning_threshold", DEFAULT_WARNING_THRESHOLD)

    spent = stats.get("total_spent", 0.0)
    calls = stats.get("calls", 0)
    remaining = max(0, daily_budget - spent)
    usage_pct = spent / daily_budget if daily_budget > 0 else 0

    # Determine enforcement action
    if usage_pct >= 1.0:
        action = "LOCKDOWN"
        message = (
            f"🚫 BUDGET LOCKDOWN: ${spent:.4f} / ${daily_budget:.2f} "
            f"({usage_pct:.0%}). Cortex calls BLOCKED. "
            f"Only REFLEX and LOG actions permitted until reset."
        )
        _enforce_lockdown(True)

    elif usage_pct >= warning_pct:
        action = "WARNING"
        message = (
            f"⚠️ BUDGET WARNING: ${spent:.4f} / ${daily_budget:.2f} "
            f"({usage_pct:.0%}). ${remaining:.4f} remaining. "
            f"Prefer REFLEX over COMPLEX."
        )
        _enforce_lockdown(False)

    else:
        action = "HEALTHY"
        message = (
            f"✅ BUDGET HEALTHY: ${spent:.4f} / ${daily_budget:.2f} "
            f"({usage_pct:.0%}). ${remaining:.4f} remaining. "
            f"{calls} API calls today."
        )
        _enforce_lockdown(False)

    _log_enforcement(action, spent, daily_budget)
    print(f"[Cerebellum]: {message}")
    return message


def _set_budget(data):
    """Set the daily budget limit."""
    try:
        amount = float(data.split(":")[1])
        config = _get_config()
        config["daily_budget"] = amount
        _save_config(config)
        return f"Daily budget set to ${amount:.2f}"
    except (IndexError, ValueError) as e:
        return f"Invalid budget format. Use: set:<amount> (e.g., set:1.00)"


def _reset_spending():
    """Reset the daily spending counter."""
    try:
        with open(STATS_FILE, "r+") as f:
            stats = json.load(f)
            old_spent = stats.get("total_spent", 0)
            stats["total_spent"] = 0.0
            stats["calls"] = 0
            stats["avg_latency"] = 0.0
            f.seek(0)
            json.dump(stats, f)
            f.truncate()
        _enforce_lockdown(False)
        return f"Spending reset. Previous spending: ${old_spent:.4f}"
    except (FileNotFoundError, json.JSONDecodeError):
        return "No stats file found to reset."


def _enforce_lockdown(locked):
    """Write lockdown state for brain_core to read."""
    lockdown_file = "memory/budget_lockdown.flag"
    if locked:
        with open(lockdown_file, "w") as f:
            f.write(datetime.now().isoformat())
    elif os.path.exists(lockdown_file):
        os.remove(lockdown_file)


def _get_stats():
    """Read current stats."""
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}


def _get_config():
    """Read budget configuration."""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "daily_budget": DEFAULT_DAILY_BUDGET,
        "warning_threshold": DEFAULT_WARNING_THRESHOLD,
    }


def _save_config(config):
    """Save budget configuration."""
    os.makedirs(os.path.dirname(BUDGET_FILE), exist_ok=True)
    with open(BUDGET_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _log_enforcement(action, spent, budget):
    """Log enforcement actions."""
    os.makedirs(os.path.dirname(ENFORCEMENT_LOG), exist_ok=True)
    with open(ENFORCEMENT_LOG, "a") as f:
        f.write(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{action}: ${spent:.4f}/${budget:.2f}\n"
        )
