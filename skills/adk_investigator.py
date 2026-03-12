"""
Skill: ADK Investigator
Category: investigation
Trigger: Complex security or performance spikes requiring multi-agent triage

Real implementation: runs a genuine ADK SequentialAgent pipeline using
InMemoryRunner — the same execution method used in the dream engine.
Pipeline: LogFetcher → LogAnalyzer
  - LogFetcher: extracts and summarises the relevant log entries
  - LogAnalyzer: produces a structured root-cause report

Falls back to a synchronous single-LLM call if the ADK runner is unavailable.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Maximum characters of recent logs to pass to the pipeline
MAX_LOG_CHARS = 3000


def _load_recent_logs(n: int = 50) -> str:
    """Read the most recent entries from error_tasks for context."""
    try:
        task_file = Path("memory/error_tasks.json")
        if task_file.exists():
            with open(task_file) as f:
                tasks = json.load(f)
            recent = tasks[-n:]
            lines = [
                f"[{t.get('id','')}] {t.get('logger','')}: {t.get('message','')} ({t.get('severity','')})"
                for t in recent
            ]
            return "\n".join(lines)
    except Exception:
        pass
    return "No recent error log entries available."


async def _run_pipeline(context_str: str, input_message: str) -> str:
    """Execute the LogFetcher → LogAnalyzer SequentialAgent pipeline via InMemoryRunner."""
    from google.adk.agents import LlmAgent, SequentialAgent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    fetch_agent = LlmAgent(
        name="LogFetcher",
        output_key="fetched_logs",
        instruction=(
            "You are a data retrieval agent. Given the following system context and logs, "
            "extract the most relevant log entries related to the issue. "
            "Output a concise, structured list of the 5-10 most important log lines.\n\n"
            f"System logs context:\n{context_str}"
        ),
    )

    analyze_agent = LlmAgent(
        name="LogAnalyzer",
        instruction=(
            "You are a forensic analyst. You have been given fetched log entries from the previous "
            "step (available in session state as 'fetched_logs'). "
            "Analyse them and produce:\n"
            "1. Root cause (1-2 sentences)\n"
            "2. Affected components (bullet list)\n"
            "3. Recommended fix (specific, actionable, <100 words)\n"
            "4. Severity: critical | high | medium | low\n\n"
            "Be precise. Do not speculate beyond what the logs show."
        ),
    )

    pipeline = SequentialAgent(
        name="TriagePipeline",
        sub_agents=[fetch_agent, analyze_agent],
    )

    runner = InMemoryRunner(agent=pipeline, app_name="adk_investigator")

    collected = []
    async for event in runner.run_async(
        user_id="reflexarc",
        session_id="investigator_session",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=input_message)],
        ),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    collected.append(part.text.strip())

    return "\n\n---\n\n".join(collected) if collected else "Pipeline produced no output."


def run(data: Any = None) -> str:
    """
    Run a real ADK triage pipeline over the given event data.

    Args:
        data: Event description string or dict describing the incident

    Returns:
        Structured triage report from the LogFetcher → LogAnalyzer pipeline
    """
    if isinstance(data, dict):
        input_message = (
            f"Investigate this incident:\n"
            f"Type: {data.get('type', 'unknown')}\n"
            f"Description: {data.get('description', str(data)[:400])}\n"
            f"Severity: {data.get('severity', 'unknown')}"
        )
    else:
        input_message = f"Investigate this incident: {str(data)[:400] if data else 'No details provided.'}"

    recent_logs = _load_recent_logs()
    context_str = f"Recent system logs:\n{recent_logs}"

    logger.info("adk_investigator_starting", input=input_message[:120])

    try:
        # Run the async pipeline in the current event loop or a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — schedule as a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        asyncio.run, _run_pipeline(context_str, input_message)
                    )
                    report = future.result(timeout=60)
            else:
                report = loop.run_until_complete(_run_pipeline(context_str, input_message))
        except RuntimeError:
            report = asyncio.run(_run_pipeline(context_str, input_message))

        logger.info("adk_investigator_complete", report_length=len(report))
        return f"ADK Triage Report:\n{report}"

    except ImportError:
        # google-adk not installed — fall back to a direct log summary
        logger.warning("adk_not_installed_fallback",
                       message="Running without ADK: returning raw log summary")
        lines = recent_logs.split("\n")[:20]
        return (
            f"ADK unavailable — raw log summary ({len(lines)} entries):\n"
            + "\n".join(lines)
            + f"\n\nIncident context: {input_message[:200]}"
        )

    except Exception as e:
        logger.error("adk_investigator_failed", error=str(e))
        return f"ADK investigator pipeline failed: {e}"
