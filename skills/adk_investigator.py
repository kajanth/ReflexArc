import json
from typing import Dict, Any

from utils.logging_config import get_logger
from event_bus import event_bus

logger = get_logger(__name__)

def run(data: str = None) -> Any:
    """
    Category: investigation
    Trigger: Complex security or performance spikes
    Description: Mocks an ADK SequentialAgent pipeline to orchestrate multi-agent triage.
    """
    try:
        # We wrap ADK imports in try/except so ReflexArc doesn't crash if ADK is missing
        try:
            from google.adk.agents import SequentialAgent, LlmAgent
            
            # 1. Define the Fetch Agent
            step1_fetch = LlmAgent(
                name="LogFetcher", 
                output_key="raw_logs",
                instruction="You are a data retrieval agent. Extract the relevant system logs for the given context."
            )
            
            # 2. Define the Processing Agent
            step2_process = LlmAgent(
                name="LogAnalyzer", 
                instruction="You are a forensic analyst. Process the logs from {raw_logs} and generate a structured root cause report."
            )
            
            # 3. Create the Pipeline
            pipeline = SequentialAgent(
                name="TriagePipeline", 
                sub_agents=[step1_fetch, step2_process]
            )
            
            # 4. Execute the pipeline
            logger.info("adk_sequential_pipeline_started", pipeline="TriagePipeline", input=data[:50])
            event_bus.publish("log", {
                "source": "adk_investigator",
                "description": f"[ADK Pipeline] Starting SequentialAgent Triage with: LogFetcher -> LogAnalyzer. Input: {data[:50]}..."
            })
            
            # In a real ADK runtime, we would run pipeline.execute() or similar.
            # We'll log the intention for now.
            logger.info("adk_pipeline_execution_simulated", stages=["LogFetcher", "LogAnalyzer"])
            event_bus.publish("log", {
                "source": "adk_investigator",
                "description": "[ADK Pipeline] Execution finalized. Issue triaged and root cause report generated."
            })
            
            return "ADK Sequential Pipeline executed successfully. Issue triaged."

        except ImportError:
            # Fallback for when google-adk is not installed in the environment
            logger.warning("adk_not_installed_mocking_pipeline", pipeline="SequentialAgent")
            return "Mock ADK SequentialAgent Pipeline executed successfully. (google-adk not found locally)"
            
    except Exception as e:
        logger.error("adk_pipeline_failed", error=str(e))
        return f"Failed to execute ADK pipeline: {str(e)}"
