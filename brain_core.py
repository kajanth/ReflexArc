import os
import time
import importlib
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List, Tuple

# Local Imports
from memory.hippocampus import Hippocampus
from sensors.curiosity import CuriositySensor
from sensors.cognitive_load import CognitiveLoadSensor
from sensors.circadian import CircadianSensor
from providers import ModelRouter
from providers.base import StandardResponse
from skill_template_engine import SkillTemplateEngine
from event_bus import event_bus
from basal_ganglia import BasalGanglia
from heartbeat import DigitalHeart
from dream_engine import DreamEngine
from prefrontal_cortex import PrefrontalCortex
from predictive_cortex import PredictiveCortex
from brocas_area import BrocasArea
from utils.logging_config import get_logger
from utils.embeddings import get_embedding_model, cleanup_embedding_model

logger = get_logger(__name__)


class NSAOrchestrator:
    """
    The central nervous system orchestrator for the NSA.
    
    Coordinates the neural cascade from sensory input through
    decision-making to action execution.
    """
    
    def __init__(self, db_path: str = "memory/long_term_memory.db",
                 min_pool_size: int = 1, max_pool_size: int = 5,
                 mcp_tool_timeout: float = 30.0) -> None:
        """
        Initialize the NSA Orchestrator.
        
        Args:
            db_path: Path to the SQLite database for memory storage
            min_pool_size: Minimum number of database connections to maintain
            max_pool_size: Maximum number of database connections allowed
            mcp_tool_timeout: Timeout for MCP tool execution in seconds
        """
        # 1. Digital Receptors & Memory
        self.router: ModelRouter = ModelRouter()
        self.memory: Hippocampus = Hippocampus(
            db_path=db_path,
            min_pool_size=min_pool_size,
            max_pool_size=max_pool_size
        )
        self.curiosity: CuriositySensor = CuriositySensor()
        self.cognitive_load: CognitiveLoadSensor = CognitiveLoadSensor()
        self.circadian: CircadianSensor = CircadianSensor()
        
        # MCP tool execution timeout
        self.mcp_tool_timeout: float = mcp_tool_timeout
        
        # 2. AI Skill Template Engine (Layer 4.5: Guided AI)
        self.template_engine: SkillTemplateEngine = SkillTemplateEngine(router=self.router)
        
        # 3. Layer 1: RAS (Local Embedding Model - $0 tokens)
        # Note: Embedding model is now shared via get_embedding_model() for memory efficiency
        self.habituation_vector: Optional[np.ndarray] = None
        
        # Adaptive RAS Variables
        self.base_novelty_threshold: float = 0.22  # Lower = more sensitive
        self.novelty_threshold: float = self.base_novelty_threshold
        self.ras_spike_times: List[float] = []

        # 4. Layer 5.5: Basal Ganglia (Habit Formation)
        self.basal_ganglia: BasalGanglia = BasalGanglia()

        # 5. Digital Heart
        self.heart: DigitalHeart = DigitalHeart(bpm=2)

        # 6. Dream Engine (REM Sleep / Memory Consolidation)
        self.dream_engine: DreamEngine = DreamEngine(router=self.router)

        # 7. Prefrontal Cortex (Long-Term Planning & Goals)
        self.prefrontal_cortex: PrefrontalCortex = PrefrontalCortex(router=self.router)
        self.prefrontal_cortex.set_orchestrator(self)

        # 8. Predictive Cortex (Anticipatory Sensing)
        self.predictive_cortex: PredictiveCortex = PredictiveCortex()
        self.predictive_cortex.set_orchestrator(self)

        # 9. Broca's Area (Natural Language Interface)
        self.brocas_area: BrocasArea = BrocasArea(self)
        
        # MCP Manager (attached later by main.py)
        self.mcp_manager: Optional[Any] = None

    def _handle_reinforce_spike(self, event_data: Dict[str, Any]) -> None:
        """Synaptic Plasticity: Lower the baseline threshold (increase sensitivity) for useful vectors."""
        desc = event_data.get('description', '')[:50]
        logger.info("synaptic_reward",
                   description_preview=desc,
                   old_threshold=self.base_novelty_threshold)
        # Make the global novelty baseline slightly more sensitive
        self.base_novelty_threshold = max(0.10, self.base_novelty_threshold - 0.01)
        self.novelty_threshold = self.base_novelty_threshold

    async def process_spike(self, sense_type: str, description: str) -> Optional[str]:
        """The Neural Cascade: From Stimulus to Action."""
        start_time = time.time()

        # ──────────────────────────────────────────────
        # SLEEP FAST-PATH (triggers dream cycle)
        # ──────────────────────────────────────────────
        if "Protocol Gamma" in description or ("SLEEP" in description and "HEARTBEAT" not in description):
            return await self.dream()

        bypass_ras = False

        # ──────────────────────────────────────────────
        # GOAL INVESTIGATION FAST-PATH (proactive spikes from prefrontal cortex)
        # ──────────────────────────────────────────────
        if "GOAL_INVESTIGATION" in description:
            # These bypass RAS — they're deliberate, not environmental
            bypass_ras = True
            event_bus.publish("goal_spike", {
                "description": description[:120],
            })
            # Fall through to normal Thalamus routing

        # ──────────────────────────────────────────────
        # PHANTOM SPIKE FAST-PATH (predictive spikes bypass RAS)
        # ──────────────────────────────────────────────
        if "PHANTOM_SPIKE" in description:
            bypass_ras = True
            event_bus.publish("phantom_spike_exec", {
                "description": description[:120],
            })
            # Fall through to Thalamus — let the system triage predicted threats

        # ──────────────────────────────────────────────
        # HEARTBEAT FAST-PATH (bypasses RAS — never redundant)
        # ──────────────────────────────────────────────
        if "HEARTBEAT_SIGNAL" in description:
            logger.info("heartbeat_received", message="Internal pulse received")
            event_bus.publish("heartbeat_exec", {
                "description": "Periodic maintenance check",
            })
            try:
                module = importlib.import_module("skills.homeostasis")
                importlib.reload(module)
                health_status = module.run(description)
                
                # If health_status is a number > 90, escalate to Cortex
                if isinstance(health_status, (int, float)) and health_status > 90:
                    logger.warning("system_stress_detected",
                                  health_score=health_status,
                                  message="Escalating to Cortex")
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
                logger.error("heartbeat_check_failed", error=str(e))
                return f"Heartbeat: Check failed — {e}"
        
        # ──────────────────────────────────────────────
        # LAYER 1: RAS (Habituation/Novelty)
        # ──────────────────────────────────────────────
        now = time.time()
        self.ras_spike_times.append(now)
        # Prune older than 60 seconds
        self.ras_spike_times = [t for t in self.ras_spike_times if now - t <= 60.0]
        
        spm = len(self.ras_spike_times)
        if spm > 20: # High noise environment
            self.novelty_threshold = min(0.60, self.base_novelty_threshold + 0.15)
        elif spm < 5: # Quiet environment
            self.novelty_threshold = max(0.05, self.base_novelty_threshold - 0.05)
        else:
            self.novelty_threshold = self.base_novelty_threshold
            
        novelty_dist = "Bypass"
        if not bypass_ras:
            ras_model = get_embedding_model()
            current_vec = ras_model.encode(description)
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
            logger.info("novelty_spike_detected",
                       sense_type=sense_type,
                       novelty_distance=novelty_dist)
        else:
            logger.debug("ras_bypassed", reason="deliberate_internal_spike")
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
        context = await self.memory.retrieve_context(description)
        await self.memory.store_memory(sense_type, description)

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
        If the stimulus is a PHANTOM_SPIKE predicting a future breach:
          - If a reflex/template can PREVENT it, reply 'REFLEX:name' or 'TEMPLATE:name'.
          - If it requires monitoring or complex planning, reply 'COMPLEX'.
          - If it's a low-confidence prediction to ignore, reply 'LOG'.
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
            logger.info("executing_reflex", skill=skill_name, layer="cerebellum")
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
                
                # Synaptic Plasticity — Reward the RAS for letting this through
                event_bus.publish("reinforce_spike", {
                    "description": description
                })
                self._handle_reinforce_spike({"description": description})
                
                # Causal feedback to prefrontal cortex
                if "GOAL_INVESTIGATION" in description:
                    self._report_goal_action(description, f"REFLEX:{skill_name}")
                self._log_stats(triage_res, start_time)
                return result
            except ModuleNotFoundError:
                # Check if this is actually a template before escalating to Cortex
                template_path = os.path.join("skills", "templates", f"{skill_name}.md")
                if os.path.exists(template_path):
                    logger.info("rerouting_to_template",
                               skill=skill_name,
                               reason="no_python_skill_found")
                    decision = f"TEMPLATE:{skill_name}"
                else:
                    logger.error("reflex_failed",
                                skill=skill_name,
                                reason="skill_not_found",
                                action="escalating_to_cortex")
                    decision = "COMPLEX"
            except Exception as e:
                logger.error("reflex_execution_failed",
                            skill=skill_name,
                            error=str(e),
                            action="escalating")
                decision = "COMPLEX"

        # ──────────────────────────────────────────────
        # LAYER 4.5: TEMPLATE ENGINE (Guided AI)
        # ──────────────────────────────────────────────
        if "TEMPLATE" in decision:
            template_name = decision.split(":")[1].strip()
            logger.info("executing_template", template=template_name, layer="template_engine")
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
                logger.error("template_execution_failed",
                            template=template_name,
                            error=str(e),
                            action="escalating_to_cortex")
                decision = "COMPLEX"

        # ──────────────────────────────────────────────
        # LAYER 4: CORTEX (High-Level Reasoning & Learning)
        # ──────────────────────────────────────────────
        if "COMPLEX" in decision:
            logger.info("cortex_reasoning", layer="cortex", message="Critical event")
            
            # 1. Fetch available MCP tools
            mcp_tools = []
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                mcp_tools = self.mcp_manager.get_all_tools()
                
            messages = [
                {"role": "system", "content": open("agent.md").read()},
                {"role": "user", "content": f"Context: {context}\nEvent: {description}\nTask: Solve this and suggest if a new 'skill' script should be written."}
            ]
            
            # 2. First Cortex pass (decide whether to use tools)
            cortex_res = self.router.route(
                tier="cortex",
                messages=messages,
                tools=mcp_tools if mcp_tools else None
            )
            
            total_cost = cortex_res.cost
            total_tokens = cortex_res.total_tokens
            
            # 3. Handle tool calls (if any)
            if mcp_tools and cortex_res.tool_calls:
                # Append assistant's tool call request to the message history
                assistant_msg = {"role": "assistant", "content": cortex_res.content or "", "tool_calls": cortex_res.tool_calls}
                messages.append(assistant_msg)
                
                # Execute tools in parallel with error isolation
                # Each tool is wrapped in try/except to prevent one failure from affecting others
                # Timeouts are per-tool (default 30s) to prevent one slow tool from blocking others
                # Errors are returned as tuples (tc, result, error) rather than raised
                # See docs/MCP_ERROR_ISOLATION.md for details
                logger.info("executing_mcp_tools",
                           num_tools=len(cortex_res.tool_calls),
                           execution="parallel")
                
                async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
                    """
                    Execute a single tool with error isolation.
                    
                    Returns:
                        Tuple[Dict, str, Optional[str]]: (tool_call, result_text, error_message)
                        - On success: (tc, result, None)
                        - On failure: (tc, "", error_message)
                    
                    Error isolation ensures:
                    - One tool failure doesn't prevent other tools from executing
                    - Timeout in one tool doesn't block other tools
                    - Parse errors are handled gracefully
                    - All errors are logged with context
                    """
                    tool_name = tc["function"]["name"]
                    import json
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except Exception as e:
                        logger.warning("tool_args_parse_failed",
                                      tool=tool_name,
                                      error=str(e))
                        args = {}
                    
                    try:
                        logger.debug("mcp_tool_start", tool=tool_name)
                        result_text = await asyncio.wait_for(
                            self.mcp_manager.execute_tool(tool_name, args),
                            timeout=self.mcp_tool_timeout
                        )
                        logger.info("mcp_tool_success",
                                   tool=tool_name,
                                   result_length=len(result_text))
                        return (tc, result_text, None)
                    except asyncio.TimeoutError:
                        error_msg = f"Tool execution timed out after {self.mcp_tool_timeout} seconds"
                        logger.error("mcp_tool_timeout", tool=tool_name, timeout=self.mcp_tool_timeout)
                        return (tc, "", error_msg)
                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        logger.error("mcp_tool_failed",
                                    tool=tool_name,
                                    error=str(e))
                        return (tc, "", error_msg)
                
                # Execute all tools in parallel
                tool_tasks = [_execute_one_tool(tc) for tc in cortex_res.tool_calls]
                tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
                
                # Append all tool results to messages
                for tc, result_text, error in tool_results:
                    tool_name = tc["function"]["name"]
                    content = result_text if not error else f"ERROR: {error}"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tool_name,
                        "content": content
                    })
                
                # 4. Second Cortex pass (with tool results)
                logger.info("processing_tool_results", num_tools=len(cortex_res.tool_calls))
                final_res = self.router.route(
                    tier="cortex",
                    messages=messages,
                    # We usually drop tools on the final synthesis pass to force a conclusion
                )
                
                total_cost += final_res.cost
                total_tokens += final_res.total_tokens
                # Use the final content, but attribute the total cost to this spike
                cortex_res.content = final_res.content
            
            # 5. Publish and log
            event_bus.publish("cortex_exec", {
                "provider": cortex_res.provider,
                "model": cortex_res.model,
                "cost": total_cost,
                "tokens": total_tokens,
                "result": cortex_res.content[:200],
            })
            
            cortex_res.cost = total_cost
            cortex_res.total_tokens = total_tokens
            self._log_stats(cortex_res, start_time)
            
            # Causal feedback to prefrontal cortex
            if "GOAL_INVESTIGATION" in description:
                self._report_goal_action(description, f"CORTEX:{cortex_res.model}")
                
            return cortex_res.content

        return "Log recorded."

    def _get_internal_state(self) -> str:
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

    async def dream(self) -> str:
        """Trigger the dream cycle (REM sleep / memory consolidation)."""
        logger.info("dream_cycle_start", phase="entering_dream_state")
        result = await self.dream_engine.dream()
        logger.info("dream_cycle_complete", phase="waking_up")
        return result

    def _log_stats(self, response: StandardResponse, start_time: float) -> None:
        """Interoception: Log cost and latency for the 6th sense."""
        latency = time.time() - start_time
        cost = getattr(response, 'cost', 0.0)
        if cost == 0.0:
            prompt_tokens = getattr(response, 'prompt_tokens', 0)
            completion_tokens = getattr(response, 'completion_tokens', 0)
            cost = (prompt_tokens * 0.000005) + (completion_tokens * 0.000015)
        self.curiosity.log_event(cost, latency)

    def _report_goal_action(self, description: str, action: str) -> None:
        """Report a completed action to the prefrontal cortex for causal tracking."""
        # Extract goal ID from the GOAL_INVESTIGATION description
        # Format: "GOAL_INVESTIGATION: [objective] strategy"
        for goal_id, goal in self.prefrontal_cortex.goals.items():
            if goal["objective"] in description:
                self.prefrontal_cortex.record_action(goal_id, action)
                break
    
    def cleanup_models(self) -> None:
        """
        Release SentenceTransformer model resources.
        
        Called during shutdown to free memory and ensure clean exit.
        Uses the shared embedding model cleanup to release resources.
        """
        logger.info("cleaning_up_models", component="nsa_orchestrator")
        cleanup_embedding_model()