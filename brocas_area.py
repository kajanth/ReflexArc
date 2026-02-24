"""
🗣️ NSA Broca's Area — Natural Language Interface
The system's "speech center". Translates plain-English operator commands
into concrete system actions, and explains past system behavior in
a human-readable reasoning chain.

Handles three intent classes:
    INTERROGATE  — "Why did you restart nginx?", "What happened at 3pm?"
    MODIFY       — "Be more aggressive about threat detection"
    GOAL_SET     — "Keep API latency under 50ms"

Usage:
    broca = BrocasArea(brain)
    response = await broca.chat("Why is CPU so high?")
"""

import json
import time
from datetime import datetime
from typing import Optional

from event_bus import event_bus


# ── Modifiable system parameters ──────────────────────────────────────────────
# Maps human-readable parameter names to (object_path, attribute) tuples.
# "object" is resolved at runtime against the brain orchestrator.
MODIFIABLE_PARAMS = {
    "novelty_threshold": {
        "path": "brain",
        "attr": "novelty_threshold",
        "description": "RAS novelty sensitivity (lower = more sensitive)",
        "min": 0.05, "max": 0.95,
    },
    "heartbeat_interval": {
        "path": "brain.heart",
        "attr": "interval",
        "description": "Heartbeat interval in seconds",
        "min": 10, "max": 600,
    },
    "prediction_interval": {
        "path": "brain.predictive_cortex",
        "attr": "prediction_interval",
        "description": "Predictive cortex sampling interval in seconds",
        "min": 30, "max": 600,
    },
    "goal_eval_interval": {
        "path": "brain.prefrontal_cortex",
        "attr": "eval_interval",
        "description": "Prefrontal cortex goal evaluation interval in seconds",
        "min": 60, "max": 3600,
    },
}


class BrocasArea:
    """
    Natural Language Interface for the NSA system.
    """

    def __init__(self, brain, sensor_mgr=None):
        """
        Args:
            brain: NSAOrchestrator instance.
            sensor_mgr: SensorManager for sensor threshold control.
        """
        self.brain = brain
        self.sensor_mgr = sensor_mgr
        self.conversation_history = []  # Multi-turn chat history

    # ══════════════════════════════════════════════
    # Public Entry Point
    # ══════════════════════════════════════════════

    async def chat(self, message: str) -> dict:
        """
        Process a plain-English message from the operator.
        Returns a dict with 'response', 'intent', and 'action_taken'.
        """
        start = time.time()

        # 1. Classify intent
        intent, parsed = await self._classify_intent(message)

        # 2. Execute the intent
        response = ""
        action_taken = None

        if intent == "INTERROGATE":
            response = await self._handle_interrogation(message)
        elif intent == "MODIFY":
            response, action_taken = await self._handle_modification(message, parsed)
        elif intent == "GOAL_SET":
            response, action_taken = await self._handle_goal_setting(message, parsed)
        else:
            response = await self._handle_general(message)

        # 3. Store in conversation history (for context in follow-up questions)
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": response})
        # Keep last 10 turns
        self.conversation_history = self.conversation_history[-20:]

        # 4. Publish to event bus so it shows in the live log
        event_bus.publish("broca_chat", {
            "message": message[:120],
            "intent": intent,
            "response": response[:200],
            "action_taken": action_taken,
            "latency": round(time.time() - start, 2),
        })

        return {
            "intent": intent,
            "response": response,
            "action_taken": action_taken,
        }

    # ══════════════════════════════════════════════
    # Intent Classification
    # ══════════════════════════════════════════════

    async def _classify_intent(self, message: str) -> tuple:
        """
        Ask the LLM to classify the operator's message and extract structured data.
        Returns (intent_class, parsed_data_dict).
        """
        system_prompt = """You are a natural language intent classifier for an AI system called ReflexArc.
Classify the operator's message into exactly one of:

INTERROGATE — asking about past events, reasoning, or system behavior
MODIFY — wanting to change system behavior, thresholds, or settings
GOAL_SET — setting a performance or metric target for the system
GENERAL — general question or conversation

If MODIFY, extract: {"action": "modify", "parameter": "<parameter_name>", "direction": "increase|decrease|set", "value": <number_or_null>}
   Known parameters: novelty_threshold, heartbeat_interval, prediction_interval, goal_eval_interval
   For sensor thresholds, use: {"action": "modify", "parameter": "sensor_threshold", "sensor": "<sensor_name>", "direction": "increase|decrease"}

If GOAL_SET, extract: {"action": "goal_set", "objective": "<plain text>", "metric": "<metric_name>", "operator": "<|>|<=|>=|==", "value": <number>}
   Known metrics: cpu_percent, memory_percent, disk_percent, spike_count, token_spend, avg_latency

Respond ONLY with a JSON object:
{"intent": "INTERROGATE|MODIFY|GOAL_SET|GENERAL", "data": {...} or null}"""

        try:
            res = self.brain.router.route(
                tier="nano",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=200,
            )
            obj = json.loads(res.content.strip())
            return obj.get("intent", "GENERAL"), obj.get("data") or {}
        except Exception:
            return "GENERAL", {}

    # ══════════════════════════════════════════════
    # Interrogation Handler
    # ══════════════════════════════════════════════

    async def _handle_interrogation(self, message: str) -> str:
        """
        Answer a question about past system behavior.
        Searches memory, then reconstructs the reasoning chain.
        """
        # Gather evidence from multiple sources
        memory_context = self.brain.memory.retrieve_context(message, top_k=5)

        # Get recent event history for reasoning chain reconstruction
        recent_events = event_bus.get_history(50)
        chain_summary = self._reconstruct_chain(recent_events)

        # Get current system vitals
        internal = self.brain._get_internal_state()
        predictions = self.brain.predictive_cortex.get_summary()
        goals = self.brain.prefrontal_cortex.get_goals()
        goal_summary = ", ".join(
            f"{g['objective']} ({g['status']})"
            for g in list(goals.values())[-3:]
        ) or "No goals set"

        system_prompt = f"""You are the Broca's Area of the ReflexArc AI brain — the system's speech center.
You help operators understand why the system behaved a certain way.

Current System State:
  Internal: {internal}
  Predictions: {predictions}
  Active Goals: {goal_summary}

Recent Memory Context (most relevant to the question):
  {memory_context}

Recent Reasoning Chain (last 50 events):
{chain_summary}

Answer the operator's question concisely and conversationally. Reference specific events from the chain when possible.
Format nervous-system layer names like: RAS → Thalamus → Cerebellum → Cortex
Be direct, factual, and brief (2-4 sentences max unless complexity demands more)."""

        res = self.brain.router.route(
            tier="mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *self.conversation_history[-6:],
                {"role": "user", "content": message},
            ],
            max_tokens=400,
        )
        return res.content.strip()

    def _reconstruct_chain(self, events: list) -> str:
        """Convert raw event bus events into a human-readable reasoning chain."""
        lines = []
        for ev in events[-30:]:
            t = ev.get("time_str", "?")
            etype = ev.get("type", "?")
            data = ev.get("data", {})

            if etype == "spike":
                lines.append(f"  [{t}] ⚡ STIMULUS ({data.get('sense_type','?')}): {str(data.get('description',''))[:80]}")
            elif etype == "ras_filter":
                result = data.get("result", "?")
                lines.append(f"  [{t}] 🔍 RAS: {result} (dist={data.get('distance','?')})")
            elif etype == "decision":
                lines.append(f"  [{t}] 🧠 THALAMUS: {data.get('decision','?')} via {data.get('model','?')}")
            elif etype == "reflex_exec":
                lines.append(f"  [{t}] ⚡ CEREBELLUM: ran reflex '{data.get('skill','?')}'")
            elif etype == "template_exec":
                lines.append(f"  [{t}] 📋 TEMPLATE: ran '{data.get('template','?')}'")
            elif etype == "cortex_exec":
                lines.append(f"  [{t}] 🤖 CORTEX: reasoned → {str(data.get('result',''))[:80]}")
            elif etype == "goal_status":
                lines.append(f"  [{t}] 🎯 GOAL: {data.get('objective','?')} = {data.get('status','?')}")
            elif etype == "phantom_spike_exec":
                lines.append(f"  [{t}] 👁️ PHANTOM: {str(data.get('description',''))[:80]}")
            elif etype == "broca_chat":
                lines.append(f"  [{t}] 🗣️ BROCA: '{str(data.get('message',''))[:60]}'")

        return "\n".join(lines) if lines else "  No recent events recorded."

    # ══════════════════════════════════════════════
    # Behavior Modification Handler
    # ══════════════════════════════════════════════

    async def _handle_modification(self, message: str, parsed: dict) -> tuple:
        """
        Apply a live parameter change based on operator intent.
        Returns (response_text, action_taken_dict).
        """
        param = parsed.get("parameter", "")
        direction = parsed.get("direction", "")
        value = parsed.get("value")
        sensor = parsed.get("sensor", "")

        # ── Sensor threshold modification ──
        if param == "sensor_threshold" and sensor and self.sensor_mgr:
            sensor_obj = self.sensor_mgr.get_sensor(sensor)
            if sensor_obj and hasattr(sensor_obj, "threshold"):
                old = sensor_obj.threshold
                factor = 0.7 if direction == "increase" else 1.3  # More sensitive = lower threshold
                sensor_obj.threshold = round(old * factor)
                action = {"type": "sensor_threshold", "sensor": sensor, "old": old, "new": sensor_obj.threshold}
                return (
                    f"✅ Adjusted `{sensor}` sensor threshold: {old} → {sensor_obj.threshold}. "
                    f"It will now be {'more' if direction == 'increase' else 'less'} sensitive to stimuli.",
                    action
                )
            return f"⚠️ Could not find sensor `{sensor}` or it has no adjustable threshold.", None

        # ── Known system parameters ──
        if param in MODIFIABLE_PARAMS:
            spec = MODIFIABLE_PARAMS[param]
            # Resolve the target object
            obj = self.brain
            for part in spec["path"].split(".")[1:]:  # Skip "brain" prefix
                obj = getattr(obj, part, None)
                if obj is None:
                    break

            if obj is None:
                return f"⚠️ Could not resolve parameter `{param}`.", None

            old_value = getattr(obj, spec["attr"], None)

            # Determine new value
            if value is not None:
                new_value = max(spec["min"], min(spec["max"], float(value)))
            elif direction == "increase":
                new_value = min(spec["max"], round(old_value * 1.3, 3))
            elif direction == "decrease":
                new_value = max(spec["min"], round(old_value * 0.7, 3))
            else:
                return f"⚠️ Not sure how to modify `{param}`. Try specifying a value or direction.", None

            setattr(obj, spec["attr"], new_value)
            action = {"type": "param_change", "parameter": param, "old": old_value, "new": new_value}
            return (
                f"✅ Updated `{param}` ({spec['description']}): {old_value} → {new_value}.",
                action
            )

        # ── Fallback: ask LLM to interpret ──
        return await self._handle_general(message), None

    # ══════════════════════════════════════════════
    # Goal Setting Handler
    # ══════════════════════════════════════════════

    async def _handle_goal_setting(self, message: str, parsed: dict) -> tuple:
        """
        Create a new goal in the Prefrontal Cortex.
        Returns (response_text, action_taken_dict).
        """
        objective = parsed.get("objective", message[:80])
        metric = parsed.get("metric", "")
        operator = parsed.get("operator", "<=")
        value = parsed.get("value")

        if not metric or value is None:
            return (
                "⚠️ I understood you want to set a goal, but couldn't extract a specific metric or target value. "
                "Try being more explicit, e.g. 'Keep CPU below 80%' or 'Keep avg_latency under 2 seconds'.",
                None
            )

        goal = self.brain.prefrontal_cortex.add_goal(
            objective=objective,
            metric=metric,
            operator=operator,
            value=float(value),
            priority="high",
        )
        action = {"type": "goal_created", "goal_id": goal["id"], "metric": metric}
        return (
            f"✅ New goal created: **{objective}** (`{metric} {operator} {value}`). "
            f"The Prefrontal Cortex will evaluate this every ~{self.brain.prefrontal_cortex.eval_interval}s "
            f"and escalate if it goes off-track.",
            action
        )

    # ══════════════════════════════════════════════
    # General Handler
    # ══════════════════════════════════════════════

    async def _handle_general(self, message: str) -> str:
        """Handle open-ended questions about the system."""
        internal = self.brain._get_internal_state()

        skills = []
        try:
            import os
            skills = [f.replace(".py", "") for f in os.listdir("skills") if f.endswith(".py")]
        except Exception:
            pass

        system_prompt = f"""You are Broca's Area, the natural language speech center of the ReflexArc AI brain.
You can answer questions about the system's architecture, current state, and capabilities.

ReflexArc Architecture:
  Layer 0: Peripheral Sensors (Vision, Audio, Network, Filesystem, etc.)
  Layer 1: RAS — Reticular Activating System (detects novelty via embedding similarity)
  Layer 2: Thalamus — Triage unit (classifies events into REFLEX/TEMPLATE/LOG/COMPLEX)
  Layer 3: Hippocampus — Long-term memory via semantic search
  Layer 4: Cortex — LLM reasoning engine for complex events (uses MCP tools if available)
  Layer 4.5: Template Engine — Pre-structured AI skill templates
  Layer 5: Cerebellum — Reflex execution (Python skill modules)
  Layer 5.5: Basal Ganglia — Habit formation (reinforces successful patterns)
  Background: Prefrontal Cortex (goal tracking), Predictive Cortex (anticipatory sensing),
              Dream Engine (memory consolidation), Digital Heart (periodic pulse), Broca's Area (you!)

Current System State: {internal}
Available Skills: {', '.join(skills[:20])}

If requested, you have access to external tools via Model Context Protocol (MCP) to read files, run commands, or investigate the host machine. Use them if the user asks a question requiring external context.

Be conversational, helpful, and accurate. Keep responses concise."""

        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[-6:],
            {"role": "user", "content": message},
        ]
        
        mcp_tools = None
        if hasattr(self.brain, "mcp_manager") and self.brain.mcp_manager:
            mcp_tools = self.brain.mcp_manager.get_all_tools()

        res = self.brain.router.route(
            tier="mini",
            messages=messages,
            max_tokens=800,
            tools=mcp_tools if mcp_tools else None
        )
        
        # ── Handle MCP Tool Calls ──
        if mcp_tools and getattr(res, "tool_calls", None):
            assistant_msg = {"role": "assistant", "content": res.content or "", "tool_calls": res.tool_calls}
            messages.append(assistant_msg)
            
            for tc in res.tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                    
                print(f"  [Broca 🗣️🔨] Executing MCP Tool: {tool_name}")
                result_text = await self.brain.mcp_manager.execute_tool(tool_name, args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tool_name,
                    "content": result_text
                })
                
            print("[Broca 🗣️]: Synthesizing tool results...")
            res = self.brain.router.route(
                tier="mini",
                messages=messages,
                max_tokens=800,
            )

        return res.content.strip()
