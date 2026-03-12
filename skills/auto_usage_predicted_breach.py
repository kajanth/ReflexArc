"""
Auto-generated skill: Usage Predicted Breach Handler
Category: autonomic
Trigger: Predictive Cortex — phantom spike predicting an upcoming resource breach

Takes proactive action when the predictive cortex forecasts a resource
threshold breach (CPU, memory, disk). Logs the prediction and attempts
lightweight pre-emptive measures via the shell_executor or system_check skill.
"""

import importlib
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Thresholds at which we consider pre-emptive action meaningful
ACTION_THRESHOLD = 85.0  # percent


def run(data=None):
    """
    Handle predicted resource breach events.

    Args:
        data: Prediction payload (dict with 'metric', 'predicted_value', 'confidence')
              or raw description string

    Returns:
        Status message describing action taken
    """
    metric = "unknown"
    predicted = None
    confidence = None

    if isinstance(data, dict):
        metric = data.get("metric", "unknown")
        predicted = data.get("predicted_value") or data.get("value")
        confidence = data.get("confidence")
    else:
        desc = str(data)[:200] if data else ""
        logger.info("usage_breach_predicted_raw", description=desc)
        return f"Predicted breach event acknowledged: {desc[:100]}"

    logger.warning(
        "usage_breach_predicted",
        metric=metric,
        predicted_value=predicted,
        confidence=confidence,
        threshold=ACTION_THRESHOLD,
    )

    # If predicted value is very high, trigger a system_check as a soft response
    if predicted is not None and float(predicted) >= ACTION_THRESHOLD:
        try:
            system_check = importlib.import_module("skills.system_check")
            result = system_check.run(data={"triggered_by": "predicted_breach", "metric": metric})
            logger.info("system_check_triggered", result=str(result)[:120])
            return (
                f"Predicted breach of {metric} at {predicted}% — system_check triggered: {result}"
            )
        except Exception as e:
            logger.error("system_check_failed", error=str(e))

    return (
        f"Predicted breach of {metric} logged (predicted={predicted}, "
        f"confidence={confidence}) — below immediate action threshold"
    )
