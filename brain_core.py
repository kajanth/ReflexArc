import os
import time
import importlib
import numpy as np
from sentence_transformers import SentenceTransformer

# Local Imports
from memory.hippocampus import Hippocampus
from sensors.curiosity import CuriositySensor
from sensors.cognitive_load import CognitiveLoadSensor
from sensors.circadian import CircadianSensor
from providers import ModelRouter
from skill_template_engine import SkillTemplateEngine
from event_bus import event_bus
from basal_ganglia import BasalGanglia
from heartbeat import DigitalHeart
from dream_engine import DreamEngine
from prefrontal_cortex import PrefrontalCortex
from predictive_cortex import PredictiveCortex


class NSAOrchestrator:
    def __init__(self):
        # 1. Digital Receptors & Memory
        self.router = ModelRouter()
        self.memory = Hippocampus()
        self.curiosity = CuriositySensor()
        self.cognitive_load = CognitiveLoadSensor()
        self.circadian = CircadianSensor()
        
        # 2. AI Skill Template Engine (Layer 4.5: Guided AI)
        self.template_engine = SkillTemplateEngine(router=self.router)
        
        # 3. Layer 1: RAS (Local Embedding Model - $0 tokens)
        self.ras_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.habituation_vector = None
        self.novelty_threshold = 0.22  # Lower = more sensitive

        # 4. Layer 5.5: Basal Ganglia (Habit Formation)
        self.basal_ganglia = BasalGanglia()

        # 5. Digital Heart
        self.heart = DigitalHeart(bpm=2)

        # 6. Dream Engine (REM Sleep / Memory Consolidation)
        self.dream_engine = DreamEngine(router=self.router)

        # 7. Prefrontal Cortex (Long-Term Planning & Goals)
        self.prefrontal_cortex = PrefrontalCortex(router=self.router)
        self.prefrontal_cortex.set_orchestrator(self)

        # 8. Predictive Cortex (Anticipatory Sensing)
        self.predictive_cortex = PredictiveCortex()
        self.predictive_cortex.set_orchestrator(self)

    async def process_spike(self, sense_type, description):
        """The Neural Cascade: From Stimulus to Action."""
        start_time = time.time()

        # ──────────────────────────────────────────────
        # SLEEP FAST-PATH (triggers dream cycle)
        # ──────────────────────────────────────────────
        if "Protocol Gamma" in description or ("SLEEP" in description and "HEARTBEAT" not in description):
            return await self.dream()

        # ──────────────────────────────────────────────
        # GOAL INVESTIGATION FAST-PATH (proactive spikes from prefrontal cortex)
        # ──────────────────────────────────────────────
        if "GOAL_INVESTIGATION" in description:
            # These bypass RAS — they're deliberate, not environmental
            event_bus.publish("goal_spike", {
                "description": description[:120],
            })
            # Fall through to normal Thalamus routing (don't return early)
            # The spike will be triaged and handled by the appropriate layer

        # ──────────────────────────────────────────────
        # PHANTOM SPIKE FAST-PATH (predictive spikes bypass RAS)
        # ──────────────────────────────────────────────
        if "PHANTOM_SPIKE" in description:
            event_bus.publish("phantom_spike_exec", {
                "description": description[:120],
            })
            # Fall through to Thalamus — let the system triage predicted threats

        # ──────────────────────────────────────────────
        # HEARTBEAT FAST-PATH (bypasses RAS — never redundant)
        # ──────────────────────────────────────────────
        if "HEARTBEAT_SIGNAL" in description:
            print("[Thalamus]: Internal Pulse received. Running System Checks.")
            event_bus.publish("heartbeat_exec", {
                "description": "Periodic maintenance check",
            })
            try:
                module = importlib.import_module("skills.homeostasis")
                importlib.reload(module)
                health_status = module.run(description)
                
                # If health_status is a number > 90, escalate to Cortex
                if isinstance(health_status, (int, float)) and health_status > 90:
                    print("[Heart → Cortex]: System stress detected, escalating...")
                    cortex_res = self.router.route(
                        tier="cortex",
                        messages=[
                            {"role": "system", "content": open("agent.md").read()},
                            {"role": "user", "content": f"URGENT: System health score is {health_status}/100. Investigate and recommend corrective actions."}
                        ],
                    )
                    event_bus.publish("cortex_exec", {
                        "provider": cortex_res.provider,
                        "model": cortex_res.model,
                        "cost": cortex_res.cost,
                        "tokens": cortex_res.total_tokens,
                        "result": cortex_res.content[:200],
                    })
                    self._log_stats(cortex_res, start_time)
                    return cortex_res.content

                return f"Heartbeat: System Healthy. ({health_status})"
            except Exception as e:
                print(f"[Heart] Maintenance check failed: {e}")
                return f"Heartbeat: Check failed — {e}"
        
        # ──────────────────────────────────────────────
        # LAYER 1: RAS (Habituation/Novelty)
        # ──────────────────────────────────────────────
        current_vec = self.ras_model.encode(description)
        if self.habituation_vector is not None:
            similarity = np.dot(current_vec, self.habituation_vector) / (
                np.linalg.norm(current_vec) * np.linalg.norm(self.habituation_vector)
            )
            distance = 1 - similarity
            
            if distance < self.novelty_threshold:
                event_bus.publish("ras_filter", {
                    "result": "HABITUATED",
                    "distance": round(float(distance), 4),
                    "description": description[:80]
                })
                return None
        
        self.habituation_vector = current_vec
        novelty_dist = distance if 'distance' in locals() else 'Init'
        print(f"\n[RAS]: Novelty Spike Detected ({sense_type.upper()}). Distance: {novelty_dist}")
        event_bus.publish("spike", {
            "sense_type": sense_type,
            "description": description,
            "novelty_distance": str(novelty_dist),
        })
        event_bus.publish("ras_filter", {
            "result": "NOVEL",
            "distance": str(novelty_dist),
        })

        # ──────────────────────────────────────────────
        # LAYER 3: HIPPOCAMPUS (Context Retrieval)
        # ──────────────────────────────────────────────
        context = self.memory.retrieve_context(description)
        self.memory.store_memory(sense_type, description)

        # ──────────────────────────────────────────────
        # LAYER 2: THALAMUS (Triage/Decision)
        # ──────────────────────────────────────────────
        skills_available = [f.replace(".py", "") for f in os.listdir('skills') if f.endswith('.py')]
        
        templates_available = self.template_engine.get_available_templates()
        template_desc = {k: v['description'] for k, v in templates_available.items()}
        
        internal_state = self._get_internal_state()
        
        triage_prompt = f"""
        STIMULUS: {description}
        CONTEXT: {context}
        AVAILABLE_REFLEXES: {skills_available}
        AVAILABLE_TEMPLATES: {template_desc}
        INTERNAL_STATE: {internal_state}
        
        If an available reflex matches the task exactly, reply 'REFLEX:name'.
        If an available template matches the task, reply 'TEMPLATE:name'.
        If it's a routine observation, reply 'LOG'.
        If it's truly novel and no reflex or template fits, reply 'COMPLEX'.
        Prefer REFLEX > TEMPLATE > LOG > COMPLEX (cheapest first).
        If INTERNAL_STATE shows COGNITIVE_OVERLOAD, avoid COMPLEX.
        """
        
        triage_res = self.router.route(
            tier="nano",
            messages=[
                {"role": "system", "content": "You are the Thalamus, a cost-aware triage unit."},
                {"role": "user", "content": triage_prompt}
            ],
        )
        decision = triage_res.content.strip()
        
        event_bus.publish("decision", {
            "decision": decision,
            "provider": triage_res.provider,
            "model": triage_res.model,
            "cost": triage_res.cost,
        })
        
        self.cognitive_load.record_decision(decision)
        self.circadian.record_spike()

        # ──────────────────────────────────────────────
        # LAYER 5: CEREBELLUM (Reflex Execution)
        # ──────────────────────────────────────────────
        if "REFLEX" in decision:
            skill_name = decision.split(":")[1].strip()
            print(f"[Cerebellum]: Executing Reflexive Action: {skill_name}")
            try:
                module = importlib.import_module(f"skills.{skill_name}")
                importlib.reload(module)
                result = module.run(description)
                event_bus.publish("reflex_exec", {
                    "skill": skill_name,
                    "result": str(result)[:200],
                })
                # Layer 5.5: Basal Ganglia — reinforce successful reflex
                pattern_id = f"REFLEX:{skill_name}"
                self.basal_ganglia.reinforce_habit(pattern_id)
                # Causal feedback to prefrontal cortex
                if "GOAL_INVESTIGATION" in description:
                    self._report_goal_action(description, f"REFLEX:{skill_name}")
                self._log_stats(triage_res, start_time)
                return result
            except Exception as e:
                print(f"[!] Reflex Failed: {e}. Escalating to Template/Cortex.")
                decision = "COMPLEX"

        # ──────────────────────────────────────────────
        # LAYER 4.5: TEMPLATE ENGINE (Guided AI)
        # ──────────────────────────────────────────────
        if "TEMPLATE" in decision:
            template_name = decision.split(":")[1].strip()
            print(f"[Template Engine]: Executing AI Template: {template_name}")
            try:
                variables = {
                    "stimulus": description,
                    "context": context,
                    "sense_type": sense_type,
                    "internal_state": internal_state,
                }
                result, response = self.template_engine.execute(template_name, variables)
                event_bus.publish("template_exec", {
                    "template": template_name,
                    "provider": getattr(response, 'provider', ''),
                    "model": getattr(response, 'model', ''),
                    "cost": getattr(response, 'cost', 0),
                    "result": str(result)[:200],
                })
                # Layer 5.5: Basal Ganglia — reinforce successful template
                pattern_id = f"TEMPLATE:{template_name}"
                self.basal_ganglia.reinforce_habit(pattern_id)
                # Causal feedback to prefrontal cortex
                if "GOAL_INVESTIGATION" in description:
                    self._report_goal_action(description, f"TEMPLATE:{template_name}")
                if response:
                    self._log_stats(response, start_time)
                else:
                    self._log_stats(triage_res, start_time)
                return result
            except Exception as e:
                print(f"[!] Template Failed: {e}. Escalating to Cortex.")
                decision = "COMPLEX"

        # ──────────────────────────────────────────────
        # LAYER 4: CORTEX (High-Level Reasoning & Learning)
        # ──────────────────────────────────────────────
        if "COMPLEX" in decision:
            print("[Cortex]: Critical Event. Reasoning...")
            cortex_res = self.router.route(
                tier="cortex",
                messages=[
                    {"role": "system", "content": open("agent.md").read()},
                    {"role": "user", "content": f"Context: {context}\nEvent: {description}\nTask: Solve this and suggest if a new 'skill' script should be written."}
                ],
            )
            
            event_bus.publish("cortex_exec", {
                "provider": cortex_res.provider,
                "model": cortex_res.model,
                "cost": cortex_res.cost,
                "tokens": cortex_res.total_tokens,
                "result": cortex_res.content[:200],
            })
            self._log_stats(cortex_res, start_time)
            # Causal feedback to prefrontal cortex
            if "GOAL_INVESTIGATION" in description:
                self._report_goal_action(description, f"CORTEX:{cortex_res.model}")
            return cortex_res.content

        return "Log recorded."

    def _get_internal_state(self):
        """Gather internal sensor readings for triage context."""
        curiosity_state = self.curiosity.get_internal_state()
        cognitive_metrics = self.cognitive_load.get_metrics()
        circadian_phase = self.circadian.get_phase()
        
        available_providers = self.router.get_available_providers()
        dream_status = "DREAMING" if self.dream_engine.is_dreaming else "AWAKE"
        goals = self.prefrontal_cortex.get_goals()
        off_track = sum(1 for g in goals.values() if g.get("status") == "off_track")
        goal_status = f"{len(goals)} goals ({off_track} off-track)" if goals else "No goals"
        
        return (
            f"Curiosity: {curiosity_state} | "
            f"CognitiveLoad: {cognitive_metrics['cortex_ratio']:.0%} cortex ratio, "
            f"efficiency {cognitive_metrics['efficiency_score']:.0%} | "
            f"Circadian: {circadian_phase} | "
            f"Dream: {dream_status} | "
            f"Goals: {goal_status} | "
            f"Predictions: {self.predictive_cortex.get_summary()} | "
            f"Providers: {', '.join(available_providers)}"
        )

    async def dream(self):
        """Trigger the dream cycle (REM sleep / memory consolidation)."""
        print("\n🌙 [Brain]: Entering dream state...")
        result = await self.dream_engine.dream()
        print("☀️  [Brain]: Dream cycle complete. Waking up.")
        return result

    def _log_stats(self, response, start_time):
        """Interoception: Log cost and latency for the 6th sense."""
        latency = time.time() - start_time
        cost = getattr(response, 'cost', 0.0)
        if cost == 0.0:
            prompt_tokens = getattr(response, 'prompt_tokens', 0)
            completion_tokens = getattr(response, 'completion_tokens', 0)
            cost = (prompt_tokens * 0.000005) + (completion_tokens * 0.000015)
        self.curiosity.log_event(cost, latency)

    def _report_goal_action(self, description, action):
        """Report a completed action to the prefrontal cortex for causal tracking."""
        # Extract goal ID from the GOAL_INVESTIGATION description
        # Format: "GOAL_INVESTIGATION: [objective] strategy"
        for goal_id, goal in self.prefrontal_cortex.goals.items():
            if goal["objective"] in description:
                self.prefrontal_cortex.record_action(goal_id, action)
                break