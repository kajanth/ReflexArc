"""
🧠 NSA Prefrontal Cortex — Long-Term Planning & Goal System
The jump from "animal brain" to "frontal-lobe reasoning".

Maintains persistent objectives, periodically evaluates progress,
proactively generates spikes when goals are off-track, and builds
a causal model of which actions moved goals forward.

Evaluation cycle (configurable interval, default 5 min):
    1. MEASURE — Collect current metric values
    2. EVALUATE — Compare against targets
    3. ACT — For off-track goals, consult Cortex and inject proactive spike
    4. RECORD — Log progress history and causal links
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Optional

import psutil

from event_bus import event_bus

GOALS_FILE = "memory/goals.json"
CAUSAL_LOG_FILE = "memory/causal_log.json"

# Operator mapping for goal evaluation
OPERATORS = {
    "<": lambda v, t: v < t,
    ">": lambda v, t: v > t,
    "<=": lambda v, t: v <= t,
    ">=": lambda v, t: v >= t,
    "==": lambda v, t: v == t,
    "!=": lambda v, t: v != t,
}


# ══════════════════════════════════════════════
# Built-in Measurers
# ══════════════════════════════════════════════

def _measure_cpu_percent():
    return psutil.cpu_percent(interval=0.5)

def _measure_memory_percent():
    return psutil.virtual_memory().percent

def _measure_disk_percent():
    return psutil.disk_usage('/').percent

def _measure_spike_count():
    try:
        with open("memory/stats.json", "r") as f:
            return json.load(f).get("calls", 0)
    except Exception:
        return 0

def _measure_token_spend():
    try:
        with open("memory/stats.json", "r") as f:
            return round(json.load(f).get("total_spent", 0.0), 4)
    except Exception:
        return 0.0

def _measure_avg_latency():
    try:
        with open("memory/stats.json", "r") as f:
            return round(json.load(f).get("avg_latency", 0.0), 3)
    except Exception:
        return 0.0

def _measure_memory_count():
    try:
        import sqlite3
        conn = sqlite3.connect("memory/long_term_memory.db")
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


MEASURERS = {
    "cpu_percent": _measure_cpu_percent,
    "memory_percent": _measure_memory_percent,
    "disk_percent": _measure_disk_percent,
    "spike_count": _measure_spike_count,
    "token_spend": _measure_token_spend,
    "avg_latency": _measure_avg_latency,
    "memory_count": _measure_memory_count,
}


class PrefrontalCortex:
    """
    Goal-directed planning engine.
    Maintains objectives, evaluates progress, generates proactive spikes.
    """

    def __init__(self, router, orchestrator=None, eval_interval=300):
        """
        Args:
            router: ModelRouter for AI-powered goal analysis
            orchestrator: NSAOrchestrator (set after init to avoid circular ref)
            eval_interval: Seconds between evaluation cycles (default 5 min)
        """
        self.router = router
        self.orchestrator = orchestrator
        self.eval_interval = eval_interval
        self.is_evaluating = False
        self.goals = {}
        self.causal_log = []
        self._pending_actions = {}  # Track actions awaiting causal measurement
        self._load_goals()
        self._load_causal_log()

    def set_orchestrator(self, orchestrator):
        """Set the orchestrator reference (avoids circular init)."""
        self.orchestrator = orchestrator

    # ══════════════════════════════════════════════
    # Goal Management
    # ══════════════════════════════════════════════

    def add_goal(self, objective: str, metric: str, operator: str,
                 value: float, priority: str = "medium") -> dict:
        """Create a new goal. Returns the goal dict."""
        goal_id = metric.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]

        goal = {
            "id": goal_id,
            "objective": objective,
            "metric": metric,
            "target": {"operator": operator, "value": value},
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "last_evaluated": None,
            "current_value": None,
            "progress_history": [],
            "causal_log": [],
        }

        self.goals[goal_id] = goal
        self._save_goals()

        event_bus.publish("goal_created", {
            "id": goal_id,
            "objective": objective,
            "metric": metric,
            "target": f"{operator} {value}",
            "priority": priority,
        })

        print(f"🎯 [Prefrontal Cortex]: New goal — {objective} ({metric} {operator} {value})")
        return goal

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal by ID."""
        if goal_id in self.goals:
            del self.goals[goal_id]
            self._save_goals()
            event_bus.publish("goal_removed", {"id": goal_id})
            return True
        return False

    def get_goals(self) -> dict:
        """Return all goals."""
        return self.goals

    def get_goal(self, goal_id: str) -> Optional[dict]:
        """Return a specific goal."""
        return self.goals.get(goal_id)

    # ══════════════════════════════════════════════
    # Evaluation Loop
    # ══════════════════════════════════════════════

    async def evaluate_loop(self):
        """Run continuous evaluation at the configured interval."""
        print(f"🎯 [Prefrontal Cortex]: Goal evaluation started (every {self.eval_interval}s)")

        # Wait a bit before first evaluation to let the system stabilize
        await asyncio.sleep(30)

        while True:
            await self.evaluate_all()
            await asyncio.sleep(self.eval_interval)

    async def evaluate_all(self):
        """Run one evaluation cycle across all goals."""
        if self.is_evaluating:
            return "Already evaluating."
        if not self.goals:
            return "No goals defined."

        self.is_evaluating = True
        event_bus.publish("goal_evaluation", {"phase": "START", "count": len(self.goals)})
        print(f"\n🎯 [Prefrontal Cortex]: Evaluating {len(self.goals)} goals...")

        results = {}
        try:
            for goal_id, goal in self.goals.items():
                result = await self._evaluate_goal(goal)
                results[goal_id] = result

            self._save_goals()

            event_bus.publish("goal_evaluation", {
                "phase": "COMPLETE",
                "results": {gid: r["status"] for gid, r in results.items()},
            })

            summary = ", ".join(f"{g['objective'][:25]}={g['status']}" for g in self.goals.values())
            print(f"🎯 [Prefrontal Cortex]: Evaluation complete — {summary}")
            return results

        except Exception as e:
            event_bus.publish("goal_evaluation", {"phase": "ERROR", "error": str(e)})
            print(f"🎯 [Prefrontal Cortex]: Evaluation error — {e}")
            return {"error": str(e)}
        finally:
            self.is_evaluating = False

    async def _evaluate_goal(self, goal):
        """Evaluate a single goal through Measure → Evaluate → Act → Record."""
        metric = goal["metric"]
        target = goal["target"]

        # ── Step 1: MEASURE ──
        measurer = MEASURERS.get(metric)
        if not measurer:
            goal["status"] = "error"
            goal["current_value"] = None
            return {"status": "error", "reason": f"No measurer for metric: {metric}"}

        try:
            current_value = measurer()
        except Exception as e:
            goal["status"] = "error"
            return {"status": "error", "reason": str(e)}

        goal["current_value"] = current_value
        goal["last_evaluated"] = datetime.now().isoformat()

        # ── Step 2: EVALUATE ──
        op_func = OPERATORS.get(target["operator"])
        if not op_func:
            goal["status"] = "error"
            return {"status": "error", "reason": f"Unknown operator: {target['operator']}"}

        is_met = op_func(current_value, target["value"])

        # Determine status with hysteresis
        old_status = goal["status"]
        if is_met:
            goal["status"] = "on_track"
        else:
            # How far off are we?
            distance = abs(current_value - target["value"])
            threshold = abs(target["value"]) * 0.15 if target["value"] != 0 else 5
            if distance <= threshold:
                goal["status"] = "at_risk"
            else:
                goal["status"] = "off_track"

        # Record progress
        progress_entry = {
            "timestamp": datetime.now().isoformat(),
            "value": current_value,
            "status": goal["status"],
        }
        goal["progress_history"].append(progress_entry)
        # Keep last 100 entries
        goal["progress_history"] = goal["progress_history"][-100:]

        event_bus.publish("goal_status", {
            "id": goal["id"],
            "objective": goal["objective"],
            "metric": metric,
            "current": current_value,
            "target": f"{target['operator']} {target['value']}",
            "status": goal["status"],
        })

        # ── Step 3: ACT (proactive spike for off-track goals) ──
        if goal["status"] == "off_track" and self.orchestrator:
            await self._generate_proactive_spike(goal, current_value)

        # ── Step 4: RECORD causal links ──
        self._check_pending_causals(goal, current_value)

        return {
            "status": goal["status"],
            "value": current_value,
            "target": f"{target['operator']} {target['value']}",
            "changed": old_status != goal["status"],
        }

    async def _generate_proactive_spike(self, goal, current_value):
        """Ask the Cortex for a strategy and inject a proactive spike."""
        target = goal["target"]

        # Build context from recent causal log
        recent_actions = goal.get("causal_log", [])[-5:]
        causal_context = ""
        if recent_actions:
            causal_context = "\n\nPrevious actions and their effects:\n"
            for entry in recent_actions:
                delta_sign = "+" if entry.get("delta", 0) >= 0 else ""
                causal_context += (
                    f"  - {entry.get('action', '?')}: "
                    f"{entry.get('before', '?')} → {entry.get('after', '?')} "
                    f"({delta_sign}{entry.get('delta', '?')})\n"
                )

        prompt = (
            f"GOAL: {goal['objective']}\n"
            f"METRIC: {goal['metric']} (current: {current_value}, "
            f"target: {target['operator']} {target['value']})\n"
            f"STATUS: OFF-TRACK — requires intervention\n"
            f"PRIORITY: {goal.get('priority', 'medium')}\n"
            f"{causal_context}\n"
            f"Recommend a specific, actionable investigation or remediation step. "
            f"Reply in 1-2 sentences only."
        )

        try:
            response = self.router.route(
                tier="nano",
                messages=[
                    {"role": "system", "content": "You are the Prefrontal Cortex — a goal-directed planning unit. Be concise and actionable."},
                    {"role": "user", "content": prompt},
                ],
            )

            strategy = response.content.strip()

            # Record pre-action value for causal tracking
            self._pending_actions[goal["id"]] = {
                "metric": goal["metric"],
                "before_value": current_value,
                "timestamp": datetime.now().isoformat(),
            }

            # Inject proactive spike into the cascade
            event_bus.publish("proactive_spike", {
                "goal_id": goal["id"],
                "objective": goal["objective"],
                "strategy": strategy,
            })

            print(f"  🎯→⚡ Proactive spike: {strategy[:80]}")

            # Fire the spike through the normal cascade
            await self.orchestrator.process_spike(
                sense_type="prefrontal_cortex",
                description=f"GOAL_INVESTIGATION: [{goal['objective']}] {strategy}"
            )

        except Exception as e:
            print(f"  🎯 [Prefrontal Cortex]: Proactive spike failed — {e}")

    # ══════════════════════════════════════════════
    # Causal Tracking
    # ══════════════════════════════════════════════

    def record_action(self, goal_id: str, action: str):
        """Called after an action (REFLEX/TEMPLATE/CORTEX) is taken for a goal."""
        if goal_id not in self._pending_actions:
            # No pending measurement — record anyway with current value
            goal = self.goals.get(goal_id)
            if goal:
                measurer = MEASURERS.get(goal["metric"])
                if measurer:
                    try:
                        self._pending_actions[goal_id] = {
                            "metric": goal["metric"],
                            "before_value": measurer(),
                            "timestamp": datetime.now().isoformat(),
                            "action": action,
                        }
                    except Exception:
                        pass

        if goal_id in self._pending_actions:
            self._pending_actions[goal_id]["action"] = action

    def _check_pending_causals(self, goal, current_value):
        """Check if any pending actions have had a measurable effect."""
        goal_id = goal["id"]
        if goal_id not in self._pending_actions:
            return

        pending = self._pending_actions.pop(goal_id)
        action = pending.get("action", "unknown")
        before = pending.get("before_value", current_value)

        causal_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "before": before,
            "after": current_value,
            "delta": round(current_value - before, 4),
            "goal_status": goal["status"],
        }

        # Add to goal's causal log
        if "causal_log" not in goal:
            goal["causal_log"] = []
        goal["causal_log"].append(causal_entry)
        goal["causal_log"] = goal["causal_log"][-50:]  # Keep last 50

        # Add to global causal log
        causal_entry["goal_id"] = goal_id
        causal_entry["objective"] = goal["objective"]
        self.causal_log.append(causal_entry)
        self.causal_log = self.causal_log[-200:]
        self._save_causal_log()

        # Log significant causal relationships
        if abs(causal_entry["delta"]) > 0:
            direction = "improved" if self._is_improvement(goal, causal_entry["delta"]) else "worsened"
            event_bus.publish("causal_link", {
                "goal_id": goal_id,
                "action": action,
                "delta": causal_entry["delta"],
                "direction": direction,
            })
            print(f"  📊 Causal link: {action} → {goal['metric']} {direction} by {abs(causal_entry['delta'])}")

    def _is_improvement(self, goal, delta):
        """Determine if a delta represents improvement toward the goal."""
        op = goal["target"]["operator"]
        # For < and <= goals, negative delta = improvement
        if op in ("<", "<="):
            return delta < 0
        # For > and >= goals, positive delta = improvement
        if op in (">", ">="):
            return delta > 0
        return False

    # ══════════════════════════════════════════════
    # Persistence
    # ══════════════════════════════════════════════

    def _load_goals(self):
        if os.path.exists(GOALS_FILE):
            try:
                with open(GOALS_FILE, "r") as f:
                    self.goals = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.goals = {}

    def _save_goals(self):
        try:
            os.makedirs(os.path.dirname(GOALS_FILE), exist_ok=True)
            with open(GOALS_FILE, "w") as f:
                json.dump(self.goals, f, indent=2)
        except Exception:
            pass

    def _load_causal_log(self):
        if os.path.exists(CAUSAL_LOG_FILE):
            try:
                with open(CAUSAL_LOG_FILE, "r") as f:
                    self.causal_log = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.causal_log = []

    def _save_causal_log(self):
        try:
            os.makedirs(os.path.dirname(CAUSAL_LOG_FILE), exist_ok=True)
            with open(CAUSAL_LOG_FILE, "w") as f:
                json.dump(self.causal_log, f, indent=2)
        except Exception:
            pass
