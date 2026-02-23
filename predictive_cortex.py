"""
👁️ NSA Predictive Cortex — Anticipatory Sensing
Instead of only reacting to spikes, the system predicts what's about
to happen and fires phantom spikes before problems manifest.

Uses lightweight statistical models (zero external deps):
    - Exponential smoothing for trend forecasting
    - Rate-of-change detector for acceleration toward thresholds
    - Temporal pattern detector for recurring time-of-day spikes

Prediction loop (configurable, default every 2 min):
    1. COLLECT — Sample all metric channels
    2. PREDICT — Run forecasters on sliding windows
    3. ACT — For predicted breaches, inject phantom spikes into the cascade
"""

import asyncio
import json
import math
import os
import time
from collections import deque
from datetime import datetime

import psutil

from event_bus import event_bus

PREDICTIONS_FILE = "memory/predictions.json"
HISTORY_MAX = 360          # ~12h of samples at 2-min intervals
FORECAST_HORIZON = 6       # Predict 6 samples ahead (12 min at 2-min interval)
SMOOTHING_ALPHA = 0.3      # Exponential smoothing factor (higher = more reactive)
CONFIDENCE_THRESHOLD = 0.6 # Minimum confidence to fire a phantom spike


class MetricChannel:
    """
    A single observable metric with history, forecaster, and threshold.
    """

    def __init__(self, name, measurer, threshold, direction="above",
                 unit="", description=""):
        """
        Args:
            name: Unique metric identifier (e.g. "cpu_percent")
            measurer: Callable that returns the current metric value
            threshold: Value at which this metric is "breaching"
            direction: "above" (breach when > threshold) or "below" (breach when <)
            unit: Display unit (e.g. "%", "ms", "$")
            description: Human-readable description
        """
        self.name = name
        self.measurer = measurer
        self.threshold = threshold
        self.direction = direction
        self.unit = unit
        self.description = description or name

        # Time-series history: (timestamp, value)
        self.history = deque(maxlen=HISTORY_MAX)

        # Forecast state
        self.smoothed = None         # Exponential smoothing level
        self.trend = 0.0             # Current rate of change per sample
        self.last_value = None
        self.predicted_value = None
        self.predicted_breach_in = None  # Samples until breach (None = no breach)
        self.confidence = 0.0
        self.status = "nominal"      # nominal | rising | warning | breach_predicted

    def sample(self):
        """Take a new measurement and update forecasts."""
        try:
            value = self.measurer()
        except Exception:
            return None

        now = time.time()
        self.history.append((now, value))
        self.last_value = value

        # Need at least 3 samples for meaningful prediction
        if len(self.history) < 3:
            self.smoothed = value
            self.status = "nominal"
            return value

        # ── Exponential Smoothing ──
        if self.smoothed is None:
            self.smoothed = value
        else:
            self.smoothed = SMOOTHING_ALPHA * value + (1 - SMOOTHING_ALPHA) * self.smoothed

        # ── Rate of Change (trend) ──
        # Use last 5 samples for trend estimation
        recent = list(self.history)[-5:]
        if len(recent) >= 2:
            values = [v for _, v in recent]
            # Linear slope via least squares
            n = len(values)
            x_mean = (n - 1) / 2.0
            y_mean = sum(values) / n
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n))
            self.trend = num / den if den > 0 else 0.0

        # ── Predict breach ──
        self.predicted_value = self.smoothed + self.trend * FORECAST_HORIZON
        self._estimate_breach()
        self._update_status()

        return value

    def _estimate_breach(self):
        """Estimate how many samples until the threshold is breached."""
        self.predicted_breach_in = None
        self.confidence = 0.0

        if self.trend == 0:
            return

        if self.direction == "above":
            if self.smoothed >= self.threshold:
                self.predicted_breach_in = 0
                self.confidence = 0.95
                return
            if self.trend > 0:
                samples_to_breach = (self.threshold - self.smoothed) / self.trend
                if 0 < samples_to_breach <= FORECAST_HORIZON * 2:
                    self.predicted_breach_in = samples_to_breach
                    # Confidence decays with distance
                    self.confidence = max(0.3, 1.0 - (samples_to_breach / (FORECAST_HORIZON * 3)))
        else:  # direction == "below"
            if self.smoothed <= self.threshold:
                self.predicted_breach_in = 0
                self.confidence = 0.95
                return
            if self.trend < 0:
                samples_to_breach = (self.smoothed - self.threshold) / abs(self.trend)
                if 0 < samples_to_breach <= FORECAST_HORIZON * 2:
                    self.predicted_breach_in = samples_to_breach
                    self.confidence = max(0.3, 1.0 - (samples_to_breach / (FORECAST_HORIZON * 3)))

    def _update_status(self):
        """Determine the channel status from forecast."""
        if self.predicted_breach_in is not None and self.predicted_breach_in == 0:
            self.status = "breaching"
        elif self.predicted_breach_in is not None and self.confidence >= CONFIDENCE_THRESHOLD:
            self.status = "breach_predicted"
        elif abs(self.trend) > 0 and self._trending_toward_threshold():
            self.status = "rising" if self.direction == "above" else "falling"
        else:
            self.status = "nominal"

    def _trending_toward_threshold(self):
        """Check if trend is moving toward the threshold."""
        if self.direction == "above":
            return self.trend > 0 and self.smoothed > self.threshold * 0.6
        else:
            return self.trend < 0 and self.smoothed < self.threshold * 1.4

    def get_trend_arrow(self):
        """Return a visual trend indicator."""
        if abs(self.trend) < 0.1:
            return "→"
        if self.trend > 0:
            return "↑↑" if self.trend > 1.0 else "↑"
        return "↓↓" if self.trend < -1.0 else "↓"

    def to_dict(self):
        """Serialize for API/dashboard."""
        breach_minutes = None
        if self.predicted_breach_in is not None:
            # Convert samples to minutes (2-min intervals)
            breach_minutes = round(self.predicted_breach_in * 2, 1)

        return {
            "name": self.name,
            "description": self.description,
            "current": round(self.last_value, 2) if self.last_value is not None else None,
            "smoothed": round(self.smoothed, 2) if self.smoothed is not None else None,
            "trend": round(self.trend, 3),
            "trend_arrow": self.get_trend_arrow(),
            "predicted": round(self.predicted_value, 2) if self.predicted_value is not None else None,
            "threshold": self.threshold,
            "direction": self.direction,
            "unit": self.unit,
            "status": self.status,
            "breach_in_minutes": breach_minutes,
            "confidence": round(self.confidence, 2),
            "samples": len(self.history),
        }


# ══════════════════════════════════════════════
# Built-in Measurers
# ══════════════════════════════════════════════

def _measure_cpu():
    return psutil.cpu_percent(interval=0.3)

def _measure_memory():
    return psutil.virtual_memory().percent

def _measure_disk():
    return psutil.disk_usage('/').percent

def _measure_latency():
    try:
        with open("memory/stats.json", "r") as f:
            return json.load(f).get("avg_latency", 0.0)
    except Exception:
        return 0.0

def _measure_cost_velocity():
    """Cost accumulated per minute (rolling estimate)."""
    try:
        with open("memory/stats.json", "r") as f:
            stats = json.load(f)
        # Rough: total_spent / calls * calls_per_minute
        total = stats.get("total_spent", 0)
        calls = stats.get("calls", 0)
        if calls == 0:
            return 0.0
        return round(total / max(calls, 1) * 0.5, 4)  # Assume ~0.5 calls/min
    except Exception:
        return 0.0


class PredictiveCortex:
    """
    Anticipatory sensing engine.
    Monitors metric channels, applies lightweight forecasting,
    and injects phantom spikes when breaches are predicted.
    """

    def __init__(self, orchestrator=None, prediction_interval=120):
        """
        Args:
            orchestrator: NSAOrchestrator (set after init to avoid circular ref)
            prediction_interval: Seconds between prediction cycles (default 2 min)
        """
        self.orchestrator = orchestrator
        self.prediction_interval = prediction_interval
        self.is_predicting = False
        self.phantom_history = deque(maxlen=50)

        # Initialize metric channels
        self.channels = {
            "cpu_percent": MetricChannel(
                name="cpu_percent",
                measurer=_measure_cpu,
                threshold=90,
                direction="above",
                unit="%",
                description="CPU Usage",
            ),
            "memory_percent": MetricChannel(
                name="memory_percent",
                measurer=_measure_memory,
                threshold=85,
                direction="above",
                unit="%",
                description="Memory Usage",
            ),
            "disk_percent": MetricChannel(
                name="disk_percent",
                measurer=_measure_disk,
                threshold=90,
                direction="above",
                unit="%",
                description="Disk Usage",
            ),
            "avg_latency": MetricChannel(
                name="avg_latency",
                measurer=_measure_latency,
                threshold=5.0,
                direction="above",
                unit="s",
                description="Avg Response Latency",
            ),
            "cost_velocity": MetricChannel(
                name="cost_velocity",
                measurer=_measure_cost_velocity,
                threshold=0.05,
                direction="above",
                unit="$/min",
                description="Cost Velocity",
            ),
        }

    def set_orchestrator(self, orchestrator):
        """Set the orchestrator reference (avoids circular init)."""
        self.orchestrator = orchestrator

    # ══════════════════════════════════════════════
    # Prediction Loop
    # ══════════════════════════════════════════════

    async def prediction_loop(self):
        """Continuous prediction cycle."""
        print(f"👁️  [Predictive Cortex]: Started (sampling every {self.prediction_interval}s)")

        # Wait for system to stabilize
        await asyncio.sleep(15)

        while True:
            await self.predict_cycle()
            await asyncio.sleep(self.prediction_interval)

    async def predict_cycle(self):
        """Run one prediction cycle: Collect → Predict → Act."""
        if self.is_predicting:
            return

        self.is_predicting = True
        try:
            # ── Step 1: COLLECT + PREDICT ──
            for channel in self.channels.values():
                channel.sample()

            # ── Step 2: ACT — Generate phantom spikes for predicted breaches ──
            phantoms = []
            for ch in self.channels.values():
                if ch.status == "breach_predicted" and ch.confidence >= CONFIDENCE_THRESHOLD:
                    phantoms.append(ch)
                elif ch.status == "breaching":
                    phantoms.append(ch)

            for ch in phantoms:
                await self._fire_phantom_spike(ch)

            # Publish overall prediction state
            event_bus.publish("prediction_update", {
                "channels": {name: ch.to_dict() for name, ch in self.channels.items()},
                "phantom_count": len(phantoms),
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            print(f"👁️  [Predictive Cortex] Error: {e}")
        finally:
            self.is_predicting = False

    async def _fire_phantom_spike(self, channel):
        """Generate and inject a phantom spike for a predicted breach."""
        breach_min = round(channel.predicted_breach_in * 2, 1) if channel.predicted_breach_in else 0
        trend_dir = "rising" if channel.trend > 0 else "falling"

        description = (
            f"PHANTOM_SPIKE: {channel.description} predicted to breach "
            f"{channel.threshold}{channel.unit} in ~{breach_min} min "
            f"(currently {channel.last_value:.1f}{channel.unit}, "
            f"{trend_dir} at {abs(channel.trend):.2f}{channel.unit}/sample, "
            f"confidence {channel.confidence:.0%})"
        )

        phantom_entry = {
            "timestamp": datetime.now().isoformat(),
            "channel": channel.name,
            "description": description,
            "current": channel.last_value,
            "predicted": channel.predicted_value,
            "threshold": channel.threshold,
            "breach_in_minutes": breach_min,
            "confidence": channel.confidence,
            "trend": channel.trend,
        }

        self.phantom_history.append(phantom_entry)

        event_bus.publish("phantom_spike", {
            "channel": channel.name,
            "description": description[:120],
            "breach_in_minutes": breach_min,
            "confidence": channel.confidence,
        })

        print(f"  👁️⚡ {description[:100]}")

        # Inject into the cascade if we have an orchestrator
        if self.orchestrator:
            try:
                await self.orchestrator.process_spike(
                    sense_type="predictive_cortex",
                    description=description,
                )
            except Exception as e:
                print(f"  👁️  Phantom spike injection failed: {e}")

    # ══════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════

    def get_predictions(self):
        """Return current state of all metric channels."""
        return {name: ch.to_dict() for name, ch in self.channels.items()}

    def get_phantom_history(self, limit=20):
        """Return recent phantom spike history."""
        return list(self.phantom_history)[-limit:]

    def get_summary(self):
        """Return a compact summary string for the internal state."""
        warnings = []
        for ch in self.channels.values():
            if ch.status in ("breach_predicted", "breaching"):
                warnings.append(f"{ch.name}={ch.last_value:.0f}{ch.unit}")
        if warnings:
            return f"⚠ {', '.join(warnings)}"
        return "nominal"
