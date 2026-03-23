"""
🧠 ReflexArc Evolution Swarm — ADK Agent Definition

Exposes `root_agent` for discovery by `adk web`.
This is the same swarm spawned during ReflexArc's Dream Cycle (Phase 5),
but exposed here so you can interact with it live via the ADK Developer UI.
"""
import json
import os
from pathlib import Path

from google.adk.agents import ParallelAgent, LlmAgent

# ─── Load Context ────────────────────────────────────
# Read any recent error tasks so the agent has live context when invoked.

def _load_error_tasks_summary() -> str:
    """Load pending error tasks from memory for the CodeFixer."""
    try:
        task_file = Path("memory/error_tasks.json")
        if task_file.exists():
            with open(task_file, "r") as f:
                tasks = json.load(f)
            pending = [t for t in tasks if t.get("status") == "pending"]
            if pending:
                return "\n".join(
                    f"- [{t['id']}] {t['logger']}: {t['message']} ({t['severity']})"
                    for t in pending[-10:]
                )
    except Exception:
        pass
    return "No pending error tasks at this time."


ERROR_TASKS = _load_error_tasks_summary()

# ─── Agent Personas ───────────────────────────────────

capability_enhancer = LlmAgent(
    name="CapabilityEnhancer",
    description="Analyzes recent system events and proposes new features and capabilities for ReflexArc.",
    instruction=(
        "You are a product manager AI for a neuromorphic AI system called ReflexArc. "
        "When the user provides system logs or describes system events, suggest one concrete new feature, "
        "reflex skill, or capability that would improve the system's ability to handle such events in the future. "
        "Be specific: name the new skill file, describe what it does, and give a Python code sketch."
    ),
)

code_fixer = LlmAgent(
    name="CodeFixer",
    description=(
        "Analyzes error logs and bug reports from ReflexArc and produces concrete Python fixes. "
        f"Current pending error tasks:\n{ERROR_TASKS}"
    ),
    instruction=(
        "You are a Staff Engineer AI for a neuromorphic AI system called ReflexArc. "
        "When the user provides error logs or bug reports, identify the root cause and propose a concrete fix. "
        "Output: the filename that needs to be changed, the exact lines to modify, and the corrected code snippet. "
        "Be precise and surgical — only change what is necessary."
    ),
)

security_auditor = LlmAgent(
    name="SecurityAuditor",
    description="Reviews system logs and code for security vulnerabilities in ReflexArc.",
    instruction=(
        "You are a Cyber Security AI reviewing ReflexArc, a neuromorphic autonomous system. "
        "When the user provides logs or code snippets, identify the top security risk "
        "(e.g. exposed secrets, injection risks, dangerous subprocess calls, open ports). "
        "Propose a specific, actionable mitigation for each risk found. "
        "Format your output as a ranked risk list with proposed mitigations."
    ),
)

# ─── Root: Parallel Swarm ────────────────────────────

root_agent = ParallelAgent(
    name="EvolutionSwarm",
    description=(
        "The ReflexArc Self-Evolution Swarm. Runs three AI persona agents in parallel: "
        "CapabilityEnhancer, CodeFixer, and SecurityAuditor. "
        "Feed it system logs or error messages to get proposals from all three agents simultaneously."
    ),
    sub_agents=[capability_enhancer, code_fixer, security_auditor],
)
