# 🤖 Use Case 4: Google ADK Integration

This example demonstrates how ReflexArc leverages **Google's Agent Development Kit (ADK)** to execute complex multi-agent workflows and utilize external ADK tools natively within the Neural Cascade.

## Scenario
A critical, complex issue is detected in the system that requires multi-step investigation. 
Instead of trying to solve it in a single prompt or a basic python script, the ReflexArc brain:
1. **Triages** the issue to the complex pathway.
2. **Executes** the `adk_investigator` skill pipeline.
3. This skill spawns a mini-swarm of ADK agents (e.g., a "Fetcher" agent and an "Analyzer" agent) working in sequence via ADK's `SequentialAgent`.

## How to Run

1. **Start the Brain** using this specific configuration. (Ensure you are in the root of the project):
   ```bash
   # Optional: Add NSA_ENABLE_ADK_UI=true to automatically launch the ADK Web UI
   NSA_ENABLE_ADK_UI=true NSA_BRAIN_CONFIG=examples/4_adk_integration/brain.yaml python main.py
   ```

2. **Trigger the Workflow**:
   Open a new terminal window and run the simulation script to inject a complex spike that requires ADK orchestration:
   ```bash
   bash examples/4_adk_integration/simulate.sh
   ```

3. **Watch the Process**:
   Observe the terminal output! You will see the Brain log messages starting with `adk_` as the ADK wrappers and the `SequentialAgent` pipeline kick in.

## Read More
For full documentation on how to add ADK Tools to the Cortex or write custom ADK workflow skills, see [docs/ADK_INTEGRATION.md](../../docs/ADK_INTEGRATION.md).
