"""
Skill: Pain Signal Warning Handler
Category: autonomic
Trigger: System Vitals sensor — any metric exceeds its 'pain' threshold

Real implementation: a multi-metric triage handler. Pain signals represent
the system's general "discomfort" — elevated resource usage, memory pressure,
disk pressure, or high error rate. This skill reads the current vitals,
classifies the severity, and takes graduated actions:
  - LOW: log + monitor
  - MEDIUM: log + free caches if memory, log top processes if CPU
  - HIGH: log + attempt automated recovery (call self_restart or cognitive_defrag)
"""

from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

PAIN_LEVELS = {
    "cpu_percent":   {"medium": 70, "high": 90},
    "memory_percent":{"medium": 75, "high": 90},
    "disk_percent":  {"medium": 80, "high": 95},
    "error_rate":    {"medium": 5,  "high": 20},
}


def _get_vitals() -> dict:
    try:
        import psutil
        vm = psutil.virtual_memory()
        du = psutil.disk_usage("/")
        return {
            "cpu_percent":    psutil.cpu_percent(interval=0.5),
            "memory_percent": vm.percent,
            "memory_available_mb": vm.available // (1024 * 1024),
            "disk_percent":   du.percent,
            "disk_free_gb":   du.free // (1024 ** 3),
        }
    except ImportError:
        return {}


def _classify_pain(vitals: dict) -> tuple[str, list[str]]:
    """Return (severity, list of offending metrics)."""
    offenders = []
    severity = "low"
    for metric, thresholds in PAIN_LEVELS.items():
        val = vitals.get(metric)
        if val is None:
            continue
        if val >= thresholds["high"]:
            offenders.append(f"{metric}={val:.1f}% (HIGH)")
            severity = "high"
        elif val >= thresholds["medium"] and severity != "high":
            offenders.append(f"{metric}={val:.1f}% (MEDIUM)")
            severity = "medium"
    return severity, offenders


def _attempt_memory_recovery() -> str:
    """Try to free Python's memory by triggering GC and cognitive defrag."""
    import gc
    gc.collect()
    results = ["GC collected"]
    try:
        import importlib
        defrag = importlib.import_module("skills.cognitive_defrag")
        r = defrag.run()
        results.append(f"cognitive_defrag: {str(r)[:80]}")
    except Exception as e:
        results.append(f"cognitive_defrag failed: {e}")
    return "; ".join(results)


def run(data=None):
    """
    Handle a system pain signal warning.

    Args:
        data: dict with 'metric', 'value', 'severity', or a description string

    Returns:
        Status report with vitals snapshot and actions taken
    """
    vitals = _get_vitals()

    # Override with event data if richer
    if isinstance(data, dict):
        for k in ("cpu_percent", "memory_percent", "disk_percent"):
            if k in data:
                try:
                    vitals[k] = float(data[k])
                except (TypeError, ValueError):
                    pass

    severity, offenders = _classify_pain(vitals)
    vitals_str = ", ".join(f"{k}={v}" for k, v in vitals.items())

    logger.warning("pain_signal_detected",
                   severity=severity,
                   offenders=offenders,
                   vitals=vitals_str)

    actions = []

    if severity == "low":
        actions.append("Monitoring — vitals within acceptable range")

    elif severity == "medium":
        if vitals.get("cpu_percent", 0) >= PAIN_LEVELS["cpu_percent"]["medium"]:
            # Log top processes
            try:
                import psutil
                top = sorted(
                    [p.info for p in psutil.process_iter(["pid", "name", "cpu_percent"])
                     if p.info.get("cpu_percent", 0) > 5],
                    key=lambda x: x.get("cpu_percent", 0), reverse=True
                )[:3]
                top_str = "; ".join(f"{p['name']}({p.get('cpu_percent',0):.1f}%)" for p in top)
                actions.append(f"Top CPU consumers: {top_str}")
            except Exception:
                pass
        if vitals.get("memory_percent", 0) >= PAIN_LEVELS["memory_percent"]["medium"]:
            result = _attempt_memory_recovery()
            actions.append(f"Memory recovery: {result}")

    elif severity == "high":
        # Attempt automated recovery
        result = _attempt_memory_recovery()
        actions.append(f"Emergency memory recovery: {result}")
        logger.error("pain_signal_high_severity",
                     offenders=offenders,
                     vitals=vitals_str,
                     action="automated_recovery_attempted")

    actions_str = "; ".join(actions) if actions else "None"
    result = f"Pain signal [{severity.upper()}] — {', '.join(offenders) or 'vitals ok'} — Actions: {actions_str}"
    logger.info("pain_signal_handled", result=result)
    return result
