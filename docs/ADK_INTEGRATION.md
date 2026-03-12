# Google Agent Development Kit (ADK) Integration

ReflexArc seamlessly integrates with [Google's Agent Development Kit (ADK)](https://google.github.io/adk-docs/). ADK provides powerful multi-agent workflow primitives (`SequentialAgent`, `ParallelAgent`) and a rich ecosystem of tools that can enhance ReflexArc's reasoning capabilities.

## Architecture & How It Works

The integration bridges ADK and ReflexArc without compromising the core neural cascade (Thalamus -> Cortex -> Basal Ganglia):

1. **`utils/adk_wrapper.py`**: This bridge dynamically translates ADK tools into the standard OpenAPI/JSON Schema that ReflexArc's Model Router requires. 
2. **Cortex Integration (`brain_core.py`)**: During the `COMPLEX` processing phase, the Cortex pulls available ADK tools from the `adk_registry` and passes them to the chosen LLM (Gemini, Claude, or OpenAI). Output from ADK tools is parsed and inserted back into the context window.
3. **Observability**: When `google-adk` is installed, ReflexArc automatically hooks into ADK's telemetry (like AgentOps or MLflow), allowing for deep traces of the Cortex's reasoning paths via the `@trace_call` decorator in `providers/router.py`.

> **Note on Compatibility**: `google-adk` currently requires Python 3.11-3.13. If ReflexArc runs on an unsupported runtime (like 3.14+), the integration gracefully degrades, maintaining system stability while mocking ADK behaviors for testing.

---

## 2. Using the ADK Web UI
If `google-adk` is successfully installed in your environment, you can launch the ADK Developer UI alongside ReflexArc. It provides a web dashboard to observe agent runs locally.
Simply set the `NSA_ENABLE_ADK_UI` environment variable to `true` when starting the Brain:

```bash
NSA_ENABLE_ADK_UI=true NSA_BRAIN_CONFIG=... python main.py
```
This will spawn `adk web` in the background and clean it up when ReflexArc shuts down.

---

## 3. Using Pre-Built ADK Tools in the Cortex

ADK provides dozens of integrations (Google Search, GitHub, BigQuery, Daytona Sandboxes, etc.). To empower the ReflexArc Cortex with an ADK tool:

1. Import the ADK tool in `main.py` (or any startup script).
2. Register it with the `adk_registry`.

**Example:**
```python
from utils.adk_wrapper import adk_registry
from google.adk.tools.search import GoogleSearchTool

# Give the Cortex the ability to search the web
search_tool = GoogleSearchTool()
adk_registry.register_tool(search_tool)
```

During a `COMPLEX` spike event, the Cortex will now autonomously decide if it should trigger a Google Search before executing a Reflex skill!

---

## 2. Extending ReflexArc with ADK Workflows

ReflexArc's "Reflexes" (skills) are typically single-action Python functions. For multi-step cognitive tasks (like investigating an alert, retrieving logs, summarizing them, and opening a Jira ticket), you can build a skill that uses ADK's `SequentialAgent`.

**Example: `skills/adk_investigator.py`**
```python
from google.adk.agents import SequentialAgent, LlmAgent
from utils.logging_config import get_logger

logger = get_logger(__name__)

def run(data: str = None):
    """
    Category: investigation
    Description: Orchestrates multi-agent triage using ADK.
    """
    step1_fetch = LlmAgent(name="LogFetcher", instruction="Extract relevant system logs.")
    step2_process = LlmAgent(name="LogAnalyzer", instruction="Process {logs} into a root cause report.")
    
    pipeline = SequentialAgent(name="TriagePipeline", sub_agents=[step1_fetch, step2_process])
    
    # Execute the multi-step agent flow
    result = pipeline.execute(context={"alert_data": data})
    
    logger.info("adk_pipeline_complete", result=result)
    return result
```
When the Thalamus routes an event to this skill, the entire multi-agent ADK workflow executes automatically.

---

## Getting Started

Check out the interactive example located in `examples/4_adk_integration` to simulate a spike that triggers an ADK workflow!
