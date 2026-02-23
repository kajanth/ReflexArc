"""
🔌 NSA Plugin Loader — Config-Driven Brain Assembly
Reads a YAML/JSON brain config and dynamically imports sensors,
metric channels, and custom measurers. This is what makes ReflexArc
generic — swap the config file, swap the brain's domain.

Usage:
    from plugin_loader import BrainConfig

    config = BrainConfig("config/brain.yaml")
    sensor_mgr = config.build_sensors(brain)
    channels = config.build_prediction_channels()
    measurers = config.build_custom_measurers()

Override config path via environment variable:
    NSA_BRAIN_CONFIG=config/trading.yaml python3 main.py
"""

import importlib
import json
import os
import sys
from collections import deque

# Try YAML first, fall back to JSON-only
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ══════════════════════════════════════════════
# Dynamic Import Utilities
# ══════════════════════════════════════════════

def load_class(dotted_path: str):
    """
    Dynamically import a class from a dotted module path.

    Example:
        load_class("sensors.vision.OpenCVReflex")
        → imports sensors.vision and returns OpenCVReflex class
    """
    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(f"Invalid class path: {dotted_path} (expected 'module.ClassName')")
    module_path, class_name = parts
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise ImportError(f"Class '{class_name}' not found in module '{module_path}'")
    return cls


def load_function(dotted_path: str):
    """
    Dynamically import a function from a dotted module path.

    Example:
        load_function("psutil.cpu_percent")
        → imports psutil and returns cpu_percent function
    """
    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(f"Invalid function path: {dotted_path}")
    module_path, func_name = parts
    module = importlib.import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise ImportError(f"Function '{func_name}' not found in module '{module_path}'")
    return func


# ══════════════════════════════════════════════
# Built-in Measurer Functions (for prediction channels)
# ══════════════════════════════════════════════

def _builtin_stats_latency():
    """Read avg latency from stats.json."""
    try:
        with open("memory/stats.json", "r") as f:
            return json.load(f).get("avg_latency", 0.0)
    except Exception:
        return 0.0

def _builtin_cost_velocity():
    """Estimate cost per minute from stats.json."""
    try:
        with open("memory/stats.json", "r") as f:
            stats = json.load(f)
        total = stats.get("total_spent", 0)
        calls = stats.get("calls", 0)
        if calls == 0:
            return 0.0
        return round(total / max(calls, 1) * 0.5, 4)
    except Exception:
        return 0.0

BUILTIN_MEASURERS = {
    "builtin.stats_latency": _builtin_stats_latency,
    "builtin.cost_velocity": _builtin_cost_velocity,
}


# ══════════════════════════════════════════════
# Brain Config
# ══════════════════════════════════════════════

class BrainConfig:
    """
    Reads and parses a brain configuration file (YAML or JSON).
    Provides methods to build sensors, prediction channels, and measurers.
    """

    DEFAULT_PATH = "config/brain.yaml"

    def __init__(self, config_path=None):
        """
        Args:
            config_path: Path to config file. Auto-detects format.
                         Falls back to DEFAULT_PATH if not specified.
                         Checks NSA_BRAIN_CONFIG env var first.
        """
        self.config_path = (
            config_path
            or os.environ.get("NSA_BRAIN_CONFIG")
            or self.DEFAULT_PATH
        )
        self.config = self._load_config()
        self.brain_config = self.config.get("brain", {})

    def _load_config(self):
        """Load config from YAML or JSON file."""
        if not os.path.exists(self.config_path):
            print(f"[PluginLoader] Config not found: {self.config_path} — using defaults")
            return self._default_config()

        with open(self.config_path, "r") as f:
            raw = f.read()

        # Try YAML first
        if self.config_path.endswith((".yaml", ".yml")) and HAS_YAML:
            config = yaml.safe_load(raw)
            print(f"[PluginLoader] Loaded YAML config: {self.config_path}")
            return config

        # Try JSON
        if self.config_path.endswith(".json"):
            config = json.loads(raw)
            print(f"[PluginLoader] Loaded JSON config: {self.config_path}")
            return config

        # YAML file but no PyYAML — try JSON fallback
        if not HAS_YAML:
            json_path = self.config_path.rsplit(".", 1)[0] + ".json"
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                print(f"[PluginLoader] PyYAML not installed, loaded JSON fallback: {json_path}")
                return config
            print(f"[PluginLoader] PyYAML not installed and no JSON fallback found — using defaults")
            return self._default_config()

        print(f"[PluginLoader] Unknown config format: {self.config_path} — using defaults")
        return self._default_config()

    def _default_config(self):
        """Return the hardcoded default config (backward compatible)."""
        return {
            "brain": {
                "name": "ReflexArc Brain",
                "heartbeat_interval": 30,
                "prediction_interval": 120,
                "goal_eval_interval": 300,
            },
            "sensors": [],
            "predictions": [],
            "custom_measurers": [],
        }

    # ──────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────

    @property
    def name(self):
        return self.brain_config.get("name", "ReflexArc Brain")

    @property
    def heartbeat_interval(self):
        return self.brain_config.get("heartbeat_interval", 30)

    @property
    def prediction_interval(self):
        return self.brain_config.get("prediction_interval", 120)

    @property
    def goal_eval_interval(self):
        return self.brain_config.get("goal_eval_interval", 300)

    # ──────────────────────────────────────────
    # Sensor Builder
    # ──────────────────────────────────────────

    def build_sensors(self, brain, sensor_mgr):
        """
        Dynamically import and register all sensors from config.

        Args:
            brain: NSAOrchestrator instance (for internal sensor refs)
            sensor_mgr: SensorManager to register into

        Returns:
            SensorManager with all sensors registered
        """
        sensor_configs = self.config.get("sensors", [])

        if not sensor_configs:
            print("[PluginLoader] No sensors in config — using legacy registration")
            return sensor_mgr

        for sensor_def in sensor_configs:
            name = sensor_def.get("name")
            emoji = sensor_def.get("emoji", "📡")
            label = sensor_def.get("label", name)
            sensor_type = sensor_def.get("type", "peripheral")

            # Internal sensors (reference brain attributes)
            if "source" in sensor_def:
                source_path = sensor_def["source"]
                # e.g., "brain.circadian" → brain.circadian
                parts = source_path.split(".")
                obj = brain
                for part in parts[1:]:  # skip "brain"
                    obj = getattr(obj, part, None)
                    if obj is None:
                        print(f"  ⚠️  Internal sensor '{name}': {source_path} not found, skipping")
                        break
                if obj is not None and obj is not brain:
                    sensor_mgr.register(name, obj, emoji=emoji,
                                         label=label, sensor_type=sensor_type)
                    print(f"  ✓ {emoji} {label} (internal: {source_path})")
                continue

            # External sensors (dynamic import)
            module_path = sensor_def.get("module")
            if not module_path:
                print(f"  ⚠️  Sensor '{name}': no module specified, skipping")
                continue

            try:
                cls = load_class(module_path)
                args = sensor_def.get("args", {})
                sensor = cls(**args) if args else cls()
                sensor_mgr.register(name, sensor, emoji=emoji,
                                     label=label, sensor_type=sensor_type)
                print(f"  ✓ {emoji} {label} ({module_path})")
            except Exception as e:
                print(f"  ⚠️  Sensor '{name}' ({module_path}): {e} — skipping")

        return sensor_mgr

    # ──────────────────────────────────────────
    # Prediction Channel Builder
    # ──────────────────────────────────────────

    def build_prediction_channels(self):
        """
        Build MetricChannel objects from config.
        Imports are done lazily to avoid circular dependencies.

        Returns:
            Dict of {name: MetricChannel} or None if no predictions in config
        """
        from predictive_cortex import MetricChannel

        pred_configs = self.config.get("predictions", [])

        if not pred_configs:
            return None  # Use defaults

        channels = {}
        for ch_def in pred_configs:
            name = ch_def.get("name")
            measurer_path = ch_def.get("measurer", "")
            threshold = ch_def.get("threshold", 100)
            direction = ch_def.get("direction", "above")
            unit = ch_def.get("unit", "")
            description = ch_def.get("description", name)
            attribute = ch_def.get("attribute")
            args = ch_def.get("args", {})

            # Resolve the measurer function
            measurer = self._resolve_measurer(measurer_path, attribute, args)
            if measurer is None:
                print(f"  ⚠️  Prediction '{name}': could not resolve measurer '{measurer_path}', skipping")
                continue

            channels[name] = MetricChannel(
                name=name,
                measurer=measurer,
                threshold=threshold,
                direction=direction,
                unit=unit,
                description=description,
            )
            print(f"  ✓ Prediction channel: {name} ({description})")

        return channels if channels else None

    def _resolve_measurer(self, path, attribute=None, args=None):
        """
        Resolve a measurer path to a callable.
        Handles builtins, psutil methods, and custom plugins.
        """
        # Check builtins first
        if path in BUILTIN_MEASURERS:
            return BUILTIN_MEASURERS[path]

        try:
            func = load_function(path)

            # If args specified, create a partial-like wrapper
            if args:
                import functools
                func = functools.partial(func, **args)

            # If attribute specified, wrap to extract it
            if attribute:
                original = func
                def _wrapped():
                    result = original()
                    return getattr(result, attribute)
                return _wrapped

            return func
        except Exception:
            return None

    # ──────────────────────────────────────────
    # Custom Measurer Builder
    # ──────────────────────────────────────────

    def build_custom_measurers(self):
        """
        Load custom measurer functions for the goal system.

        Returns:
            Dict of {name: callable} or empty dict
        """
        measurer_configs = self.config.get("custom_measurers", [])
        measurers = {}

        for m_def in measurer_configs:
            name = m_def.get("name")
            module_path = m_def.get("module")
            if not name or not module_path:
                continue

            try:
                func = load_function(module_path)
                measurers[name] = func
                print(f"  ✓ Custom measurer: {name} ({module_path})")
            except Exception as e:
                print(f"  ⚠️  Measurer '{name}' ({module_path}): {e} — skipping")

        return measurers

    # ──────────────────────────────────────────
    # MCP Server Builder
    # ──────────────────────────────────────────

    def build_mcp_servers(self, loop=None):
        """
        Initializes an MCPServerManager and connects to all configured MCP servers.
        This spawns subprocesses, so it must be run within the event loop.

        Returns:
            MCPServerManager instance (started)
        """
        from mcp_client import MCPServerManager
        
        mcp_configs = self.config.get("mcp_servers", [])
        manager = MCPServerManager()
        
        if not mcp_configs:
            return manager
            
        # We need to run the async start_all.
        # It's usually called from async main() so we can either wait or just return
        # the coroutine for the caller to await.
        # Let's return a tuple of (manager, coroutine_to_await)
        start_coro = manager.start_all(mcp_configs)
        return manager, start_coro

    def get_raw_config(self):
        """Return the raw config dict."""
        return self.config
