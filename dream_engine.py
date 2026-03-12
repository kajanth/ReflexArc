"""
🌙 NSA Dream Engine — Offline Memory Consolidation
Like biological REM sleep, this module runs during the circadian
SLEEP phase and performs:

    Phase 1: REPLAY — Cluster today's memories by semantic similarity
    Phase 2: CONSOLIDATE — Name patterns, identify unresolved recurring spikes
    Phase 3: SKILL GENESIS — Auto-generate skills for recurring unresolved patterns
    Phase 4: PRUNE — Deduplicate and age-prune stale memories

After all phases, writes a dream journal entry to:
    memory/dream_journal/YYYY-MM-DD.md

Triggered by: Circadian sensor SLEEP transition
Cost: ~$0.03 per dream cycle (one mini + one cortex call)
"""

import asyncio
import importlib
import json
import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
from sentence_transformers import SentenceTransformer

from event_bus import event_bus

# Configure HuggingFace cache directory
HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
os.environ.setdefault("TRANSFORMERS_CACHE", HF_CACHE_DIR)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", HF_CACHE_DIR)

# Reuse the same embedding model as the RAS / Hippocampus
_model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=HF_CACHE_DIR)


def cleanup_dream_model() -> None:
    """
    Release the dream engine embedding model resources.
    
    Called during shutdown to free memory and ensure clean exit.
    """
    global _model
    if _model is not None:
        print("[Dream] Cleaning up embedding model...")
        del _model
        _model = None

DB_PATH = "memory/long_term_memory.db"
PATTERNS_FILE = "memory/patterns.json"
JOURNAL_DIR = "memory/dream_journal"
EVOLUTION_PROPOSALS = "memory/evolution_proposals.md"
CLUSTER_THRESHOLD = 0.78      # Cosine similarity to group memories
RECURRENCE_THRESHOLD = 3      # Minimum occurrences to trigger skill genesis
STALE_DAYS = 30               # Memories older than this get pruned


class DreamEngine:
    """
    Orchestrates the 4-phase dream cycle.
    Requires a ModelRouter instance for AI-powered consolidation.
    """

    def __init__(self, router):
        self.router = router
        self.is_dreaming = False
        self._patterns = {}
        self._load_patterns()

    # ══════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════

    async def dream(self):
        """
        Run the full dream cycle. Returns the dream journal text.
        Safe to call from any context — guards against concurrent runs.
        """
        if self.is_dreaming:
            return "Already dreaming — please wait."

        self.is_dreaming = True
        start = time.time()
        journal_lines = []
        today = datetime.now().strftime("%Y-%m-%d")

        event_bus.publish("dream_cycle", {"phase": "START", "date": today})
        print("\n🌙 ═══════════════════════════════════════")
        print("   DREAM CYCLE INITIATED")
        print("   ═══════════════════════════════════════\n")

        try:
            # ── Phase 1: REPLAY ───────────────────────
            memories, clusters = self._phase_replay()
            journal_lines.append(f"# 🌙 Dream Journal — {today}\n")
            journal_lines.append(f"## Phase 1: Replay")
            journal_lines.append(f"- Memories processed: **{len(memories)}**")
            journal_lines.append(f"- Clusters formed: **{len(clusters)}**\n")

            if not memories:
                journal_lines.append("*No memories from the last 24 hours. Quiet day.*\n")
                self._write_journal(today, journal_lines)
                return "\n".join(journal_lines)

            # ── Phase 2: CONSOLIDATE ──────────────────
            pattern_report = await self._phase_consolidate(clusters, memories)
            journal_lines.append(f"## Phase 2: Consolidate")
            journal_lines.append(pattern_report + "\n")

            # ── Phase 3: SKILL GENESIS ────────────────
            genesis_report = await self._phase_skill_genesis()
            journal_lines.append(f"## Phase 3: Skill Genesis")
            journal_lines.append(genesis_report + "\n")

            # ── Phase 4: PRUNE ────────────────────────
            prune_report = self._phase_prune()
            journal_lines.append(f"## Phase 4: Prune")
            journal_lines.append(prune_report + "\n")
            
            # ── Phase 5: SELF EVOLUTION (ADK SWARM) ───
            evolution_report = await self._phase_self_evolution(clusters, memories)
            journal_lines.append(f"## Phase 5: Self-Evolution (ADK Swarm)")
            journal_lines.append(evolution_report + "\n")

            # ── Phase 6: IMPLEMENT PROPOSAL ──────────
            impl_report = await self._phase_implement_next_proposal()
            journal_lines.append(f"## Phase 6: Proposal Implementation")
            journal_lines.append(impl_report + "\n")

            # ── Error Whitelist Check ─────────────────
            self._check_and_flag_recurring_errors()

            elapsed = time.time() - start
            journal_lines.append(f"---")
            journal_lines.append(f"*Dream cycle completed in {elapsed:.1f}s*")

            journal_text = "\n".join(journal_lines)
            self._write_journal(today, journal_lines)
            self._save_patterns()

            event_bus.publish("dream_cycle", {
                "phase": "COMPLETE",
                "date": today,
                "memories_processed": len(memories),
                "clusters": len(clusters),
                "elapsed": round(elapsed, 1),
            })

            print(f"\n☀️  Dream cycle complete. {len(memories)} memories → "
                  f"{len(clusters)} clusters. Elapsed: {elapsed:.1f}s")

            return journal_text

        except Exception as e:
            event_bus.publish("dream_cycle", {"phase": "ERROR", "error": str(e)})
            print(f"[Dream] ✗ Error during dream cycle: {e}")
            return f"Dream cycle failed: {e}"

        finally:
            self.is_dreaming = False

    async def evolve(self) -> str:
        """Run just the self-evolution and proposal implementation phases (without full memory clustering/pruning)."""
        if self.is_dreaming:
            return "Skipped: Already dreaming/evolving."

        self.is_dreaming = True
        try:
            event_bus.publish("dream_cycle", {"phase": "DAYTIME_EVOLUTION_START"})
            
            # Fetch recent memories directly, skipping the heavy semantic clustering
            _, memories = self._phase_replay()
            
            evolution_report = await self._phase_self_evolution([], memories)
            impl_report = await self._phase_implement_next_proposal()
            self._check_and_flag_recurring_errors()
            
            event_bus.publish("dream_cycle", {"phase": "DAYTIME_EVOLUTION_COMPLETE"})
            return f"{evolution_report}\n{impl_report}"
        except Exception as e:
            event_bus.publish("dream_cycle", {"phase": "ERROR", "error": str(e)})
            print(f"🧬 [Evolution] ✗ Error during daytime evolution: {e}")
            return f"Evolution cycle failed: {e}"
        finally:
            self.is_dreaming = False

    async def daytime_evolution_loop(self, interval_seconds: int = 1800):
        """Background loop for daytime evolution when enabled."""
        import asyncio
        print(f"🧬 [Evolution]: Daytime background loop started ({interval_seconds}s interval).")
        while True:
            await asyncio.sleep(interval_seconds)
            if not self.is_dreaming:
                print("\n🧬 [Evolution]: Waking up for daytime evolution cycle...")
                try:
                    await self.evolve()
                except Exception as e:
                    print(f"🧬 [Evolution] Failed: {e}")

    # ══════════════════════════════════════════════
    # Phase 1: REPLAY — Cluster memories by similarity
    # ══════════════════════════════════════════════

    def _phase_replay(self):
        """Load recent memories and cluster by cosine similarity. Cost: $0."""
        event_bus.publish("dream_cycle", {"phase": "REPLAY"})
        print("  💤 Phase 1: REPLAY — Loading and clustering memories...")

        if not os.path.exists(DB_PATH):
            return [], []

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, sense_type, description, vector "
            "FROM memories WHERE timestamp > datetime('now', '-1 day') "
            "ORDER BY timestamp"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("    No recent memories found.")
            return [], []

        # Build memory objects with pre-computed vectors
        memories = []
        for row in rows:
            mid, ts, stype, desc, vec_blob = row
            if vec_blob:
                vec = np.frombuffer(vec_blob, dtype=np.float32)
            else:
                vec = _model.encode(desc)
            memories.append({
                "id": mid,
                "timestamp": ts,
                "sense_type": stype,
                "description": desc,
                "vector": vec,
            })

        # Greedy clustering by cosine similarity
        clusters = self._cluster_memories(memories)
        print(f"    {len(memories)} memories → {len(clusters)} clusters")

        return memories, clusters

    def _cluster_memories(self, memories):
        """Group memories into clusters based on cosine similarity."""
        clusters = []
        assigned = set()

        for i, mem_a in enumerate(memories):
            if i in assigned:
                continue

            cluster = [mem_a]
            assigned.add(i)
            vec_a = mem_a["vector"]
            norm_a = np.linalg.norm(vec_a)
            if norm_a == 0:
                continue

            for j, mem_b in enumerate(memories):
                if j in assigned or j <= i:
                    continue

                vec_b = mem_b["vector"]
                norm_b = np.linalg.norm(vec_b)
                if norm_b == 0:
                    continue

                sim = np.dot(vec_a, vec_b) / (norm_a * norm_b)
                if sim > CLUSTER_THRESHOLD:
                    cluster.append(mem_b)
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    # ══════════════════════════════════════════════
    # Phase 2: CONSOLIDATE — Name patterns via AI
    # ══════════════════════════════════════════════

    async def _phase_consolidate(self, clusters, all_memories):
        """Ask the AI to name clusters and identify patterns. Cost: ~$0.01."""
        event_bus.publish("dream_cycle", {"phase": "CONSOLIDATE"})
        print("  💤 Phase 2: CONSOLIDATE — Naming patterns via AI...")

        # Only send clusters with 2+ memories (single-item clusters are noise)
        significant_clusters = [c for c in clusters if len(c) >= 2]

        if not significant_clusters:
            self._update_patterns_from_clusters(clusters, {})
            return "- No significant patterns found (all unique events)."

        # Build a summary for the AI
        cluster_summaries = []
        for idx, cluster in enumerate(significant_clusters):
            samples = [m["description"][:100] for m in cluster[:5]]
            sense_types = list(set(m["sense_type"] for m in cluster))
            cluster_summaries.append(
                f"CLUSTER {idx+1} ({len(cluster)} events, types: {sense_types}):\n"
                + "\n".join(f"  - {s}" for s in samples)
            )

        prompt = (
            "Analyze these memory clusters from an AI system's last 24 hours.\n\n"
            + "\n\n".join(cluster_summaries) +
            "\n\nRespond with ONLY a JSON array (no markdown, no explanation):\n"
            '[{"cluster_id":1,"pattern_name":"short_snake_case","summary":"One sentence","resolved":false}]'
        )

        try:
            response = self.router.route(
                tier="mini",
                messages=[
                    {"role": "system", "content": "Output ONLY valid JSON. No markdown fences. No explanation."},
                    {"role": "user", "content": prompt},
                ],
            )

            patterns = self._extract_json(response.content)

            if patterns:
                pattern_map = {p.get("cluster_id", i+1): p for i, p in enumerate(patterns)}
                self._update_patterns_from_clusters(significant_clusters, pattern_map)

                report_lines = []
                for p in patterns:
                    status = "✅ resolved" if p.get("resolved") else "⚠️ unresolved"
                    report_lines.append(
                        f"- **{p.get('pattern_name', '?')}**: {p.get('summary', '?')} [{status}]"
                    )
                return "\n".join(report_lines)
            else:
                # JSON parse failed — use intelligent fallback names
                print("    [Dream] AI response wasn't valid JSON, generating names from content.")
                self._update_patterns_with_fallback_names(significant_clusters)
                report_lines = []
                for idx, cluster in enumerate(significant_clusters):
                    name = self._generate_fallback_name(cluster)
                    report_lines.append(f"- **{name}**: {len(cluster)} similar events (auto-named)")
                return "\n".join(report_lines)

        except Exception as e:
            print(f"    [Dream] Consolidation error: {e}")
            self._update_patterns_with_fallback_names(significant_clusters)
            return f"- Consolidation partially failed ({e}). Patterns saved with auto-names."

    def _extract_json(self, text):
        """Robustly extract a JSON array from AI response text."""
        import re
        text = text.strip()

        # Strategy 1: Direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Strip markdown fences (```json ... ``` or ``` ... ```)
        if "```" in text:
            match = re.search(r'```(?:json)?\s*\n(.*?)```', text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(1).strip())
                    if isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    pass

        # Strategy 3: Find the first [ ... ] block
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return None

    def _generate_fallback_name(self, cluster):
        """Generate a meaningful snake_case name from cluster content."""
        # Extract common words from descriptions
        from collections import Counter
        words = []
        stop_words = {'the', 'a', 'an', 'is', 'was', 'are', 'in', 'on', 'at',
                       'to', 'for', 'of', 'and', 'or', 'has', 'had', 'with',
                       'from', 'by', 'be', 'as', 'it', 'its', 'this', 'that',
                       'not', 'no', 'but', 'if', 'do', 'does', 'did', 'so'}

        for m in cluster:
            desc = m.get("description", "")
            # Extract meaningful words
            for word in desc.split():
                word = word.strip(".:,;!?()[]{}\"'").lower()
                if len(word) > 2 and word not in stop_words and word.isalpha():
                    words.append(word)

        # Take the 2-3 most common meaningful words
        common = Counter(words).most_common(3)
        if common:
            name_parts = [w for w, _ in common]
            return "_".join(name_parts[:3])

        # Absolute fallback: use sense type
        sense_types = set(m.get("sense_type", "unknown") for m in cluster)
        return "_".join(sense_types) + "_pattern"

    def _update_patterns_with_fallback_names(self, clusters):
        """Update patterns using auto-generated names from cluster content."""
        now = datetime.now().isoformat()
        for cluster in clusters:
            name = self._generate_fallback_name(cluster)
            summary = cluster[0]["description"][:80]

            if name in self._patterns:
                self._patterns[name]["occurrences"] += len(cluster)
                self._patterns[name]["last_seen"] = now
                self._patterns[name]["cluster_size"] = len(cluster)
            else:
                self._patterns[name] = {
                    "description": summary,
                    "occurrences": len(cluster),
                    "first_seen": now,
                    "last_seen": now,
                    "resolved": False,
                    "associated_skill": None,
                    "cluster_size": len(cluster),
                }

    def _update_patterns_from_clusters(self, clusters, pattern_map):
        """Merge discovered clusters into the persistent patterns store."""
        now = datetime.now().isoformat()

        for idx, cluster in enumerate(clusters):
            cluster_id = idx + 1
            ai_info = pattern_map.get(cluster_id, {})
            name = ai_info.get("pattern_name", f"cluster_{cluster_id}")
            summary = ai_info.get("summary", cluster[0]["description"][:80])
            resolved = ai_info.get("resolved", False)

            if name in self._patterns:
                # Existing pattern — increment count
                self._patterns[name]["occurrences"] += len(cluster)
                self._patterns[name]["last_seen"] = now
                self._patterns[name]["cluster_size"] = len(cluster)
                if resolved and not self._patterns[name].get("resolved"):
                    self._patterns[name]["resolved"] = True
            else:
                # New pattern
                self._patterns[name] = {
                    "description": summary,
                    "occurrences": len(cluster),
                    "first_seen": now,
                    "last_seen": now,
                    "resolved": resolved,
                    "associated_skill": None,
                    "cluster_size": len(cluster),
                }

    # ══════════════════════════════════════════════
    # Phase 3: SKILL GENESIS — Auto-generate skills
    # ══════════════════════════════════════════════

    async def _phase_skill_genesis(self):
        """Generate new skills for recurring unresolved patterns. Cost: ~$0.02."""
        event_bus.publish("dream_cycle", {"phase": "SKILL_GENESIS"})
        print("  💤 Phase 3: SKILL GENESIS — Checking for auto-skill opportunities...")

        # Find unresolved patterns that recur often enough
        candidates = {
            name: info for name, info in self._patterns.items()
            if not info.get("resolved")
            and not info.get("associated_skill")
            and info.get("occurrences", 0) >= RECURRENCE_THRESHOLD
        }

        if not candidates:
            print("    No recurring unresolved patterns. No new skills needed.")
            return "- No recurring unresolved patterns found. No new skills generated."

        report_lines = []
        for name, info in candidates.items():
            print(f"    🧬 Generating skill for pattern: {name} ({info['occurrences']} occurrences)")

            prompt = (
                f"You are an AI system that auto-generates Python skills.\n\n"
                f"A recurring pattern has been detected in the system's memory:\n"
                f"  Pattern: {name}\n"
                f"  Description: {info['description']}\n"
                f"  Occurrences: {info['occurrences']}\n"
                f"  First seen: {info['first_seen']}\n"
                f"  Last seen: {info['last_seen']}\n\n"
                f"Write a Python module with a `run(data)` function that handles this pattern.\n"
                f"The function receives a string `data` containing the event description.\n"
                f"It should return a string describing what action was taken.\n\n"
                f"Rules:\n"
                f"- Use only standard library modules (os, subprocess, json, datetime, etc.)\n"
                f"- Include a module-level docstring explaining the skill\n"
                f"- Include error handling\n"
                f"- The skill should be safe and defensive\n"
                f"- Do NOT use any external API keys\n\n"
                f"Output ONLY the Python code, no markdown fences or explanation."
            )

            try:
                response = self.router.route(
                    tier="cortex",
                    messages=[
                        {"role": "system", "content": "You are a Python skill generator. Output only valid Python code."},
                        {"role": "user", "content": prompt},
                    ],
                )

                code = response.content.strip()
                # Strip markdown fences if present
                if code.startswith("```"):
                    code = code.split("\n", 1)[1]
                    code = code.rsplit("```", 1)[0].strip()

                # Validate it's parseable Python
                import ast
                ast.parse(code)

                # Save the skill
                skill_name = f"auto_{name}"
                skill_path = f"skills/{skill_name}.py"
                with open(skill_path, "w") as f:
                    f.write(code)

                # Mark the pattern as resolved
                info["associated_skill"] = skill_name
                info["resolved"] = True

                event_bus.publish("skill_genesis", {
                    "skill_name": skill_name,
                    "pattern": name,
                    "occurrences": info["occurrences"],
                })

                # Log to memory/agent_logs/changes_log.jsonl
                try:
                    from pathlib import Path
                    changes_log = Path("memory/agent_logs/changes_log.jsonl")
                    changes_log.parent.mkdir(parents=True, exist_ok=True)
                    change_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "type": "skill_added",
                        "file": skill_path,
                        "skill_name": skill_name,
                        "trigger": f"Recurring pattern '{name}' ({info['occurrences']} occurrences)",
                        "author": "dream_engine"
                    }
                    with open(changes_log, "a") as clf:
                        clf.write(json.dumps(change_entry) + "\n")
                except Exception:
                    pass

                report_lines.append(
                    f"- 🧬 **{skill_name}.py** generated for pattern `{name}` "
                    f"({info['occurrences']} occurrences)"
                )
                print(f"    ✓ New skill written: {skill_path}")

            except SyntaxError:
                report_lines.append(f"- ⚠️ Skill for `{name}` failed validation (bad syntax)")
                print(f"    ✗ Generated code for {name} failed AST validation")
            except Exception as e:
                report_lines.append(f"- ⚠️ Skill for `{name}` failed: {e}")
                print(f"    ✗ Error generating skill for {name}: {e}")

        return "\n".join(report_lines) if report_lines else "- No new skills generated."

    # ══════════════════════════════════════════════
    # Phase 4: PRUNE — Cleanup stale memories
    # ══════════════════════════════════════════════

    def _phase_prune(self):
        """Deduplicate and prune old memories. Cost: $0."""
        event_bus.publish("dream_cycle", {"phase": "PRUNE"})
        print("  💤 Phase 4: PRUNE — Cleaning up stale memories...")

        results = []

        # Run cognitive defrag (merge near-duplicates)
        try:
            defrag = importlib.import_module("skills.cognitive_defrag")
            importlib.reload(defrag)
            defrag_result = defrag.run()
            results.append(f"- Defrag: {defrag_result}")
        except Exception as e:
            results.append(f"- Defrag failed: {e}")

        # Run memory cleanup (age-based pruning)
        try:
            cleanup = importlib.import_module("skills.memory_cleanup")
            importlib.reload(cleanup)
            cleanup_result = cleanup.run(f"retention:{STALE_DAYS}")
            results.append(f"- Pruning: {cleanup_result}")
        except Exception as e:
            results.append(f"- Pruning failed: {e}")

        return "\n".join(results)

    # ══════════════════════════════════════════════
    # Phase 5: SELF EVOLUTION — ADK Agent Swarm
    # ══════════════════════════════════════════════

    async def _phase_self_evolution(self, clusters, all_memories):
        """
        Spin up an ADK ParallelAgent with 3 personas (Capability, Fixer, Security)
        to evaluate the day's memories and propose codebase updates.
        Cost: ~$0.05
        """
        event_bus.publish("dream_cycle", {"phase": "SELF_EVOLUTION"})
        print("  💤 Phase 5: SELF-EVOLUTION — Spawning ADK reasoning swarm...")
        
        try:
            from google.adk.agents import ParallelAgent, LlmAgent
            has_adk = True
        except ImportError:
            has_adk = False
            
        if not has_adk:
             print("    [Dream] google-adk not found. Skipping self-evolution swarm.")
             return "- Swarm skipped (`google-adk` package not available in this environment)."

        if not all_memories:
             return "- No memories today to analyze for evolution."

        # Prepare context for the agents
        recent_log_data = "\n".join([m["description"][:100] for m in all_memories[-15:]])
        
        # Load error tasks backlog
        import json
        from pathlib import Path
        error_tasks_summary = "No pending error tasks."
        try:
            task_file = Path("memory/error_tasks.json")
            if task_file.exists():
                with open(task_file, "r") as f:
                    tasks = json.load(f)
                    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
                    if pending_tasks:
                        error_tasks_summary = "\n".join(
                            [f"- [{t['id']}] {t['logger']}: {t['message']} (Severity: {t['severity']})" 
                             for t in pending_tasks[-10:]]
                        )
        except Exception as e:
            error_tasks_summary = f"Could not load error tasks: {e}"

        context = {
            "recent_logs": recent_log_data,
            "error_tasks": error_tasks_summary
        }

        report_lines = []

        try:
            # Truncate to avoid exceeding context limits
            log_snippet = recent_log_data[:2000]
            task_snippet = error_tasks_summary[:1000]

            # Persona 1: Enhancer
            enhancer = LlmAgent(
                name="CapabilityEnhancer",
                instruction=(
                    f"You are a product manager AI. Review these recent system logs:\n{log_snippet}\n"
                    "Suggest one new feature, skill, or capability the system should build to handle "
                    "these events better in the future. Be highly specific but concise."
                )
            )

            # Persona 2: Code Fixer
            fixer = LlmAgent(
                name="CodeFixer",
                instruction=(
                    f"You are a Staff Engineer AI. Review these recent system logs:\n{log_snippet}\n\n"
                    f"Pending error tasks from the live system:\n{task_snippet}\n\n"
                    "Identify the root cause of these errors and propose a concrete "
                    "architectural fix or Python refactor to resolve them. Include the filename and modified code."
                )
            )

            # Persona 3: Security Auditor
            auditor = LlmAgent(
                name="SecurityAuditor",
                instruction=(
                    f"You are a Cyber Security AI. Review these recent system logs:\n{log_snippet}\n"
                    "Look for exposed secrets, unusual payloads, or dangerous system calls. "
                    "Identify the top vulnerability and propose a mitigation."
                )
            )

            # Orchestrate in Parallel using InMemoryRunner (correct ADK pattern)
            swarm = ParallelAgent(
                name="EvolutionSwarm",
                sub_agents=[enhancer, fixer, auditor]
            )

            print("    [Dream] Swarm initialized. Awaiting proposals...")
            event_bus.publish("log", {
                "source": "dream_engine",
                "description": "[ADK Swarm] Evolution Swarm initialized with Enhancer, Fixer, and Auditor. Analyzing 24h logs..."
            })

            from google.adk.runners import InMemoryRunner
            import uuid
            import google.genai.types as types

            runner = InMemoryRunner(agent=swarm, app_name="reflexarc_dream")
            session = await runner.session_service.create_session(
                app_name="reflexarc_dream",
                user_id="dream_engine"
            )

            # Build the user prompt combining logs and error tasks
            user_prompt = (
                f"Analyze the following system logs and error backlog.\n\n"
                f"Recent Logs:\n{recent_log_data}\n\n"
                f"Pending Error Tasks:\n{error_tasks_summary}"
            )

            new_message = types.Content(
                role="user",
                parts=[types.Part(text=user_prompt)]
            )

            # Collect all final responses from each sub-agent
            proposals = []
            report_lines.append("### Swarm Architecture Review:")

            async for event in runner.run_async(
                user_id="dream_engine",
                session_id=session.id,
                new_message=new_message
            ):
                # Grab final text responses from each persona
                if event.is_final_response() and event.content and event.content.parts:
                    agent_name = getattr(event, 'author', 'Swarm')
                    content = event.content.parts[0].text or ""

                    proposals.append(f"#### {agent_name} Proposal\n{content}\n")
                    
                    preview = content[:150].replace('\n', ' ') + "..."
                    report_lines.append(f"- **{agent_name}**: {preview}")

                    event_bus.publish("log", {
                        "source": "dream_engine",
                        "description": f"[ADK Proposal - {agent_name}] {preview}"
                    })

                    # Write to memory/agent_logs/
                    try:
                        agent_logs_dir = Path("memory/agent_logs")
                        agent_logs_dir.mkdir(parents=True, exist_ok=True)
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "agent": agent_name,
                            "session_id": session.id,
                            "swarm": "EvolutionSwarm",
                            "preview": preview,
                            "full_response_length": len(content)
                        }
                        with open(agent_logs_dir / "agent_activity.jsonl", "a") as lf:
                            lf.write(json.dumps(log_entry) + "\n")
                    except Exception as log_err:
                        pass  # Never let log writes crash the swarm


            # Save full proposals to independent file
            if proposals:
                proposal_text = f"# 🚀 Self-Evolution Proposals ({datetime.now().strftime('%Y-%m-%d')})\n\n" + "\n".join(proposals)
                os.makedirs(os.path.dirname(EVOLUTION_PROPOSALS), exist_ok=True)
                with open(EVOLUTION_PROPOSALS, "w") as f:
                    f.write(proposal_text)
                report_lines.append(f"\n*Full proposals saved to `{EVOLUTION_PROPOSALS}`*")
                print(f"    ✓ Swarm complete. Saved to {EVOLUTION_PROPOSALS}")

                # Log to the changes log
                from utils.changes_logger import log_change
                log_change(
                    change_type="proposal_saved",
                    file=EVOLUTION_PROPOSALS,
                    description=f"ADK EvolutionSwarm wrote {len(proposals)} proposals: {', '.join(p.split(chr(10))[0] for p in proposals)}",
                    author="evolution_swarm",
                    extra={"agent_count": len(proposals), "date": datetime.now().strftime('%Y-%m-%d')}
                )

                # De-duplicate and enqueue for implementation next cycle
                from utils.proposal_queue import enqueue_proposals
                structured = []
                for raw in proposals:
                    lines = raw.strip().split("\n", 1)
                    agent = lines[0].replace("####", "").replace("Proposal", "").strip() if lines else "unknown"
                    content = lines[1].strip() if len(lines) > 1 else raw
                    structured.append({"agent": agent, "content": content})

                q_result = enqueue_proposals(structured)
                report_lines.append(
                    f"- Proposal queue: **{q_result['added']} added**, "
                    f"{q_result['duplicates_skipped']} duplicates skipped"
                )
                print(f"    \U0001f4e5 Queue: +{q_result['added']} new, {q_result['duplicates_skipped']} dupes skipped")

            return "\n".join(report_lines)


        except Exception as e:
            print(f"    [Dream] Swarm execution failed: {e}")
            return f"- Swarm execution failed: {e}"

    # ══════════════════════════════════════════════
    # Phase 6: IMPLEMENT — Apply Next Queued Proposal
    # ══════════════════════════════════════════════

    async def _phase_implement_next_proposal(self) -> str:
        """
        Pick up the next pending proposal from the queue and attempt to apply it.
        Only one proposal is implemented per dream cycle to keep changes atomic.
        """
        event_bus.publish("dream_cycle", {"phase": "PROPOSAL_IMPLEMENTATION"})
        print("  💤 Phase 6: PROPOSAL IMPLEMENTATION — Checking queue...")

        from utils.proposal_queue import next_pending, mark_proposal, queue_stats, attempt_implementation

        stats = queue_stats()
        stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items()) or "empty"
        print(f"    Queue status: {stats_str}")

        proposal = next_pending()
        if not proposal:
            return f"- Queue is empty or all proposals processed. Stats: {stats_str}"

        print(f"    📋 Implementing: [{proposal['id']}] from {proposal['agent']}")
        event_bus.publish("log", {
            "source": "dream_engine",
            "description": f"[Proposal Queue] Attempting to implement proposal {proposal['id']} from {proposal['agent']}"
        })

        # Mark as in-progress before attempting (in case of crash)
        mark_proposal(proposal["id"], "in_progress")

        result = attempt_implementation(proposal, self.router)

        if result.startswith("APPLIED"):
            mark_proposal(proposal["id"], "implemented", result)
            print(f"    ✓ {result}")
            event_bus.publish("log", {
                "source": "dream_engine",
                "description": f"[Proposal Queue] ✅ {result}"
            })
            return f"- {result} (proposal `{proposal['id']}`)"
        elif result.startswith("ADVISORY"):
            mark_proposal(proposal["id"], "implemented", result)
            return f"- {result} (recorded as advisory, no code change)"
        else:
            mark_proposal(proposal["id"], "failed", result)
            print(f"    ✗ {result}")
            return f"- {result} (proposal `{proposal['id']}` marked as failed)"

    # ══════════════════════════════════════════════
    # Error Whitelist — Recurring Error Flagging
    # ══════════════════════════════════════════════

    def _check_and_flag_recurring_errors(self) -> None:
        """
        Scan the error backlog for recurring errors and fire a dashboard alert
        so the user can whitelist them or keep them flagged.
        """
        try:
            from utils.error_whitelist import check_recurring_errors

            alerts = check_recurring_errors()
            for alert in alerts:
                print(f"    🚨 Recurring error detected ({alert['occurrences']}x): {alert['message'][:60]}")
                event_bus.publish("user_alert", {
                    "type": "recurring_error",
                    "title": f"Recurring Error ({alert['occurrences']}x): {alert['logger']}",
                    "message": alert["message"],
                    "severity": alert["severity"],
                    "occurrences": alert["occurrences"],
                    "error_key": alert["error_key"],
                    "actions": [
                        {
                            "label": "Whitelist (stop flagging)",
                            "url": f"/errors/whitelist",
                            "method": "POST",
                            "body": {"error_key": alert["error_key"]},
                        },
                        {
                            "label": "Keep flagging",
                            "url": f"/errors/dismiss",
                            "method": "POST",
                            "body": {"error_key": alert["error_key"]},
                        },
                    ],
                })
        except Exception as e:
            print(f"    [Dream] Recurring error check failed: {e}")

    # ══════════════════════════════════════════════
    # Persistence
    # ══════════════════════════════════════════════


    def _load_patterns(self):
        """Load patterns from disk."""
        if os.path.exists(PATTERNS_FILE):
            try:
                with open(PATTERNS_FILE, "r") as f:
                    self._patterns = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._patterns = {}

    def _save_patterns(self):
        """Persist patterns to disk."""
        try:
            os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
            with open(PATTERNS_FILE, "w") as f:
                json.dump(self._patterns, f, indent=2)
        except Exception:
            pass

    def _write_journal(self, date_str, lines):
        """Write the dream journal as a markdown file."""
        os.makedirs(JOURNAL_DIR, exist_ok=True)
        path = os.path.join(JOURNAL_DIR, f"{date_str}.md")
        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"    📓 Dream journal saved: {path}")

    def get_recent_journals(self, limit=7):
        """Return the most recent dream journal entries."""
        if not os.path.exists(JOURNAL_DIR):
            return []

        files = sorted(
            [f for f in os.listdir(JOURNAL_DIR) if f.endswith(".md")],
            reverse=True
        )[:limit]

        journals = []
        for fname in files:
            path = os.path.join(JOURNAL_DIR, fname)
            with open(path, "r") as f:
                journals.append({
                    "date": fname.replace(".md", ""),
                    "content": f.read(),
                })

        return journals

    def get_patterns(self):
        """Return all discovered patterns."""
        return self._patterns
