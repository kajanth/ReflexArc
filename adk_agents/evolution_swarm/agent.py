"""
🧠 ReflexArc Evolution Swarm — ADK Agent Definition

Exposes `root_agent` for discovery by `adk web`.
This is the same swarm spawned during ReflexArc's Dream Cycle (Phase 5),
but exposed here so you can interact with it live via the ADK Developer UI.

Agent topology:
  EvolutionSwarm (SequentialAgent)
  ├── MetaCognitionPipeline (SequentialAgent)  ← Dreamer → Thinker
  │   ├── Dreamer     — blue-sky evolution proposals
  │   └── Thinker     — comparative evaluation & selection
  └── OperationalSwarm (ParallelAgent)          ← existing trio runs in parallel
      ├── CapabilityEnhancer
      ├── CodeFixer
      └── SecurityAuditor
"""
import json
from pathlib import Path

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent


# ─── Context loaders ──────────────────────────────────

def _load_error_tasks_summary() -> str:
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


def _load_dream_journal() -> str:
    try:
        journal_dir = Path("memory/dream_journal")
        if not journal_dir.exists():
            return "No dream journal entries yet."
        entries = sorted(journal_dir.glob("*.md"), reverse=True)
        if not entries:
            return "No dream journal entries yet."
        return f"[{entries[0].name}]\n{entries[0].read_text(encoding='utf-8')[:1800]}"
    except Exception:
        return "Could not load dream journal."


def _load_proposal_queue() -> str:
    try:
        qfile = Path("memory/proposal_queue.json")
        if not qfile.exists():
            return "Queue empty."
        with open(qfile) as f:
            queue = json.load(f)
        pending = [p for p in queue if p.get("status") == "pending"]
        done = [p for p in queue if p.get("status") in ("implemented", "failed")]
        lines = [f"Pending: {len(pending)}, Implemented: {len(done)}"]
        for p in pending[-6:]:
            lines.append(f"  - {p.get('content', '')[:80]}")
        return "\n".join(lines)
    except Exception:
        return "Could not load queue."


def _load_skills() -> str:
    try:
        return ", ".join(
            s.stem for s in sorted(Path("skills").glob("*.py"))
            if s.stem != "__init__"
        )
    except Exception:
        return "unknown"


def _load_error_rate() -> str:
    try:
        efile = Path("memory/error_tasks.json")
        if not efile.exists():
            return "No error data."
        with open(efile) as f:
            errors = json.load(f)
        critical = [e for e in errors if e.get("severity") in ("critical", "error")]
        return f"{len(errors)} total, {len(critical)} critical"
    except Exception:
        return "unavailable"


# Load context once per module import (refreshed per runner invocation in dream_engine)
ERROR_TASKS    = _load_error_tasks_summary()
DREAM_JOURNAL  = _load_dream_journal()
PROPOSAL_QUEUE = _load_proposal_queue()
SKILLS_LIST    = _load_skills()
ERROR_RATE     = _load_error_rate()


# ─── Dreamer ──────────────────────────────────────────

dreamer = LlmAgent(
    name="Dreamer",
    description=(
        "Blue-sky AI evolution philosopher. Generates bold proposals for how "
        "ReflexArc should evolve — new learning mechanisms, memory architectures, "
        "meta-cognition strategies, and self-improvement loops."
    ),
    instruction=(
        "You are the **Dreamer** — the creative, philosophical mind of ReflexArc.\n\n"
        "Your job is NOT to fix bugs. Your job is to imagine how ReflexArc should "
        "*evolve as an AI system*.\n\n"
        "Think expansively about:\n"
        "- New learning mechanisms (online learning, few-shot adaptation, reinforcement from sensor feedback)\n"
        "- Novel memory architectures (episodic/semantic separation, forgetting curves, memory clustering)\n"
        "- Meta-cognition (the system evaluating its own decision quality and adjusting routing thresholds)\n"
        "- Agent topology (Critic agent that vets proposals, Validator that tests changes before committing)\n"
        "- New sensing modalities (audio, network traffic, git commit stream, calendar events)\n"
        "- Self-calibration (benchmarking skill success rates, retiring poor performers automatically)\n"
        "- Evolutionary algorithms applied to skill selection and parameter tuning\n\n"
        f"**Existing skills:** {SKILLS_LIST}\n\n"
        f"**Pending proposals (avoid duplicating):**\n{PROPOSAL_QUEUE}\n\n"
        f"**Recent dream journal:**\n{DREAM_JOURNAL}\n\n"
        "Output 3-5 proposals using this format for each:\n\n"
        "#### Proposal: [short name]\n"
        "**Category:** architecture | learning | memory | sensing | meta-cognition | self-improvement\n"
        "**Impact:** high | medium | low\n"
        "**Feasibility:** high | medium | low\n"
        "**Description:** 2-3 sentences.\n"
        "**Implementation sketch:** Files to create/modify and core logic.\n\n"
        "Prioritise highest-impact, most-feasible ideas. Always think about "
        "proposals that help ReflexArc better *understand itself* and *improve itself autonomously*."
    ),
)


# ─── Thinker ──────────────────────────────────────────

thinker = LlmAgent(
    name="Thinker",
    description=(
        "Structured comparative reasoner. Reads Dreamer's proposals from context, "
        "evaluates them systematically, selects the single best one for the current "
        "system state, and produces a concrete executable implementation plan with rollback."
    ),
    instruction=(
        "You are the **Thinker** — the analytical, decision-making mind of ReflexArc.\n\n"
        "You will receive proposals from the Dreamer (in the conversation context above). "
        "Evaluate each one systematically and select exactly ONE to implement NOW.\n\n"
        "**Score each proposal 1-5 on:**\n"
        "- Impact: autonomy/resilience/capability improvement\n"
        "- Feasibility: implementable in Python/aiohttp/ADK\n"
        "- Risk: won't break existing functionality (5 = very low risk)\n"
        "- Urgency: does current system state make this pressing?\n\n"
        f"**Current system state:**\n"
        f"- Error profile: {ERROR_RATE}\n"
        f"- Recent journal:\n{DREAM_JOURNAL[:600]}\n\n"
        "**Output format:**\n\n"
        "Comparison table:\n"
        "| Proposal | Impact | Feasibility | Risk | Urgency | Total |\n"
        "|---|---|---|---|---|---|\n"
        "| ... | /5 | /5 | /5 | /5 | /20 |\n\n"
        "Then:\n"
        "#### Proposal: [selected name]\n"
        "**Why selected:** 1-2 sentences.\n"
        "**Implementation plan:**\n"
        "1. `path/to/file.py` — what exactly to change\n"
        "2. `path/to/file2.py` — what exactly to change\n"
        "**Expected outcome:** What changes measurably.\n"
        "**Rollback:** How to revert safely.\n\n"
        "Be decisive. Select exactly one proposal. "
        "The system can only implement one thing per dream cycle."
    ),
)


# ─── Operational agents ───────────────────────────────

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
        "When the user provides logs or code snippets, identify the top security risk. "
        "Propose a specific, actionable mitigation for each risk found. "
        "Format your output as a ranked risk list with proposed mitigations."
    ),
)


# ─── Meta-Cognition Pipeline: Dreamer → Thinker ──────
# Sequential so Thinker receives Dreamer's output in the conversation context

meta_cognition_pipeline = SequentialAgent(
    name="MetaCognitionPipeline",
    description=(
        "ReflexArc's strategic self-evolution pipeline. "
        "Dreamer generates bold evolution proposals, then Thinker evaluates them "
        "and selects the single best one with a concrete implementation plan."
    ),
    sub_agents=[dreamer, thinker],
)

# ─── Operational Swarm: existing trio in parallel ─────

operational_swarm = ParallelAgent(
    name="OperationalSwarm",
    description=(
        "Parallel operational agents: CapabilityEnhancer proposes features, "
        "CodeFixer patches errors, SecurityAuditor flags risks."
    ),
    sub_agents=[capability_enhancer, code_fixer, security_auditor],
)

# ─── Root: Full Evolution Swarm ───────────────────────
# Sequential: strategic meta-cognition first, then tactical operational improvements

root_agent = SequentialAgent(
    name="EvolutionSwarm",
    description=(
        "The full ReflexArc Self-Evolution Swarm. "
        "Phase 1 — MetaCognitionPipeline: Dreamer imagines bold evolution strategies, "
        "Thinker evaluates and selects the best one to implement. "
        "Phase 2 — OperationalSwarm: CapabilityEnhancer, CodeFixer, and SecurityAuditor "
        "run in parallel for immediate operational improvements."
    ),
    sub_agents=[meta_cognition_pipeline, operational_swarm],
)
