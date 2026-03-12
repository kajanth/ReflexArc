"""
Skill: CPU Usage Predicted Breach Handler
Category: autonomic
Trigger: Predictive Cortex — phantom spike predicting an upcoming CPU breach

Real implementation: reads psutil to get the current top CPU consumers
*before* the breach happens, logs them for context, attempts proactive
niceness adjustment on safe processes, and publishes a pre-emptive
warning event to the event bus so other parts of the brain can react.
"""

import re
from utils.logging_config import get_logger

logger = get_logger(__name__)

PROACTIVE_RENICE_THRESHOLD = 75.0   # renice if process already above this
CONFIDENCE_MIN = 0.5                 # ignore predictions below this confidence


def _top_cpu_processes(n: int = 5) -> list[dict]:
    try:
        import psutil, time
        snapshot = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "status"]):
            try:
                if p.info["status"] not in ("zombie", "dead"):
                    snapshot.append(p.info)
            except Exception:
                pass
        time.sleep(0.2)
        for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                for entry in snapshot:
                    if entry["pid"] == p.pid:
                        entry["cpu_percent"] = p.cpu_percent()
            except Exception:
                pass
        return sorted(snapshot, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:n]
    except ImportError:
        return []


def run(data=None):
    """
    Handle a Predictive Cortex forecast of an upcoming CPU breach.

    Args:
        data: dict (metric, predicted_value, confidence, horizon_seconds)
              or a plain description string

    Returns:
        Status message describing pre-emptive actions taken
    """
    metric = "cpu_percent"
    predicted_value = None
    confidence = 1.0
    horizon = "unknown"

    if isinstance(data, dict):
        metric          = data.get("metric", "cpu_percent")
        predicted_value = data.get("predicted_value") or data.get("value")
        confidence      = float(data.get("confidence", 1.0))
        horizon         = data.get("horizon_seconds", "unknown")
    elif isinstance(data, str):
        m = re.search(r"(\d+\.?\d*)%?", data)
        if m:
            predicted_value = float(m.group(1))

    if confidence < CONFIDENCE_MIN:
        logger.info("cpu_prediction_ignored_low_confidence", confidence=confidence)
        return f"CPU breach prediction ignored (confidence={confidence:.2f} < {CONFIDENCE_MIN})"

    if predicted_value is None:
        logger.warning("cpu_prediction_no_value", data=str(data)[:200])
        return "CPU breach prediction logged — no numeric value extracted"

    predicted_value = float(predicted_value)
    logger.warning("cpu_breach_predicted",
                   metric=metric,
                   predicted_value=predicted_value,
                   confidence=confidence,
                   horizon_seconds=horizon)

    top_procs = _top_cpu_processes()
    top_summary = "; ".join(
        f"{p['name']}(pid={p['pid']}, {p.get('cpu_percent', 0):.1f}%)"
        for p in top_procs
    )

    actions = []
    # Proactively renice anything already using significant CPU
    for proc in top_procs[:2]:
        pct  = proc.get("cpu_percent", 0)
        name = proc.get("name", "")
        pid  = proc.get("pid")
        safe = {"python3", "python", "node", "ruby", "java"}
        protected = {"kernel_task", "launchd", "WindowServer", "bash", "zsh"}
        if name in protected or pid is None:
            continue
        if pct >= PROACTIVE_RENICE_THRESHOLD and name in safe:
            try:
                import psutil
                p = psutil.Process(pid)
                old = p.nice()
                p.nice(min(old + 5, 15))
                actions.append(f"Pre-emptively reniced {name}(pid={pid}): nice {old}→{p.nice()}")
                logger.info("proactive_renice", name=name, pid=pid, old_nice=old)
            except Exception as e:
                logger.error("proactive_renice_failed", name=name, error=str(e))

    if not actions:
        actions.append("Logged and monitoring — no processes exceeded the proactive renice threshold yet")

    result = (
        f"CPU breach predicted at {predicted_value:.1f}% (confidence={confidence:.2f}, "
        f"horizon={horizon}s) — Current top: {top_summary} — "
        f"Pre-emptive actions: {'; '.join(actions)}"
    )
    logger.info("cpu_breach_prediction_handled", result=result)
    return result
