"""
🌙 ReflexArc Dreamer Agent — ADK Agent Definition

The Dreamer is a blue-sky, open-ended thinker. It is not constrained to
fixing existing bugs — it explores *how AI systems should evolve*, generating
bold architectural ideas, novel learning approaches, and ambitious capability
proposals for ReflexArc to consider.

Available standalone via `adk web` at http://localhost:8000
Also runs as part of the EvolutionSwarm during Dream Cycle Phase 5.
"""

import json
from pathlib import Path

from google.adk.agents import LlmAgent


# ─── Live context loaders ──────────────────────────────

def _load_dream_journal_summary() -> str:
    """Read the most recent dream journal entry to give Dreamer historical context."""
    try:
        journal_dir = Path("memory/dream_journal")
        if not journal_dir.exists():
            return "No dream journal entries yet."
        entries = sorted(journal_dir.glob("*.md"), reverse=True)
        if not entries:
            return "No dream journal entries yet."
        latest = entries[0].read_text(encoding="utf-8")[:2000]
        return f"[Latest journal: {entries[0].name}]\n{latest}"
    except Exception:
        return "Could not load dream journal."


def _load_proposal_queue_summary() -> str:
    """Summarise the current proposal queue so Dreamer avoids duplicating them."""
    try:
        qfile = Path("memory/proposal_queue.json")
        if not qfile.exists():
            return "Proposal queue is empty."
        with open(qfile) as f:
            queue = json.load(f)
        pending = [p for p in queue if p.get("status") == "pending"]
        if not pending:
            return "No pending proposals — all ideas have been attempted or are in progress."
        summaries = "\n".join(f"- {p.get('content','')[:80]}" for p in pending[-8:])
        return f"Current pending proposals ({len(pending)} total):\n{summaries}"
    except Exception:
        return "Could not load proposal queue."


def _load_skills_list() -> str:
    """List current skills so Dreamer knows what already exists."""
    try:
        skills = sorted(Path("skills").glob("*.py"))
        names = [s.stem for s in skills if s.stem != "__init__"]
        return ", ".join(names) if names else "No skills loaded."
    except Exception:
        return "Could not enumerate skills."


# Build context strings once at import time (refreshed each dream cycle via runner)
DREAM_JOURNAL = _load_dream_journal_summary()
PROPOSAL_QUEUE = _load_proposal_queue_summary()
SKILLS_LIST = _load_skills_list()

# ─── Dreamer Agent ────────────────────────────────────

root_agent = LlmAgent(
    name="Dreamer",
    description=(
        "A blue-sky AI philosopher for ReflexArc. "
        "Explores how AI systems should evolve — generates ambitious, creative architectural proposals "
        "for new capabilities, learning strategies, and self-improvement mechanisms. "
        "Produces at least 3 distinct evolution proposals ranked by impact and feasibility."
    ),
    instruction=f"""You are the **Dreamer** — the creative, philosophical mind of ReflexArc, a neuromorphic AI system.

Your job is NOT to fix bugs. Your job is to imagine how ReflexArc should *evolve as an AI system*.

Think expansively about:
- New learning mechanisms (e.g. online learning from sensor data, few-shot adaptation)
- Novel memory architectures (e.g. episodic vs semantic memory separation, memory pruning strategies)
- Meta-cognition (e.g. the system monitoring its own decision quality and adjusting thresholds)
- Agent topology changes (e.g. adding a Critic agent that vets proposals before they enter the queue)
- New sensing modalities (e.g. audio, network traffic, git commit stream)
- Self-calibration (e.g. the system benchmarking its own skill success rates and retiring poor performers)
- Evolutionary algorithms applied to skill selection and parameter tuning

### Current System Context
**Existing skills:** {SKILLS_LIST}

**Proposal queue (to avoid duplicating):**
{PROPOSAL_QUEUE}

**Recent dream journal:**
{DREAM_JOURNAL}

### Your Output Format
For each proposal, output a section like:

#### Proposal: [short name]
**Category:** architecture | learning | memory | sensing | meta-cognition | self-improvement
**Impact:** high | medium | low
**Feasibility:** high | medium | low
**Description:** 2-3 sentences explaining the idea and its benefit.
**Implementation sketch:** What file(s) to create/modify and what the core logic would look like.

Generate at least 3 proposals. Prioritise the highest-impact, most-feasible ideas first.
Always think about proposals that help ReflexArc better *understand itself* and *improve itself autonomously*.""",
)
