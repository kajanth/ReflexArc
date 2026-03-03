# 🛠️ Use Case 1: DevOps Incident Auto-Remediation

This example demonstrates how ReflexArc acts as an **autonomous Site Reliability Engineer (SRE)**.

## Scenario
Your infrastructure experiences a sudden spike in CPU usage and API latency. A monitoring tool (like Datadog or PagerDuty) fires a webhook alert. 

Instead of waking up an engineer, the **ReflexArc Brain**:
1. **Senses** the CPU spike (via local `system_vitals` or incoming `webhook`).
2. **Filters** it through the RAS (Reticular Activating System) to see if it's novel or just background noise.
3. **Triages** it in the Thalamus.
4. **Responds** via the Neural Cascade:
   - For a known, simple CPU issue, it triggers a `$0` **Reflex** (e.g., executing a Python script to restart the worker node).
   - For a complex 502 Bad Gateway, it engages the **Cortex** (LLM) to analyze logs and propose a root cause and remediation strategy.

## How to Run

1. **Start the Brain** using this specific configuration:
   ```bash
   # Make sure you are in the root of the ReflexArc project
   NSA_BRAIN_CONFIG=examples/1_incident_response_devops/brain.yaml python main.py
   ```

2. **Trigger the Incident**:
   Open a new terminal window and run the simulation script to inject sensory spikes:
   ```bash
   bash examples/1_incident_response_devops/simulate.sh
   ```

3. **Watch the Cascade**:
   Observe the terminal output or go to `http://localhost:8080` to see the brain triage the alert and execute skills.
