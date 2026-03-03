# 🎧 Use Case 2: Customer Support Agent Triage

This example demonstrates how ReflexArc filters incoming communication to reduce cognitive load on human support teams.

## Scenario
A company receives hundreds of support tickets an hour via a webhook from Zendesk or Intercom.

1. **Senses**: The `webhooks` sensor ingests every incoming ticket as a "spike."
2. **Filters (RAS)**: The Habitation Filter compares the text against local embedding memory. Repeated queries (e.g. "How to change password") are marked as "habitual" (background noise).
3. **Triage (Thalamus)**: 
   - Known queries trigger a **Template Skill** (`~0.001¢`) to send a canned response link.
   - High-priority threats (like a furious VIP customer demanding a refund) generate a "threat spike" (Cortisol release 🔴) which routes directly to the **Cortex** (LLM) for immediate reasoning to appease the customer and loop in a manager.
4. **Learning (Synaptic Plasticity)**: As more tickets arrive, the brain tracks what works, automatically creating Python or Template skills overnight in the **Dream Engine** for the most common issues.

## How to Run

1. **Start the Brain** using this specific configuration:
   ```bash
   # Make sure you are in the root of the ReflexArc project
   NSA_BRAIN_CONFIG=examples/2_customer_support_triage/brain.yaml python main.py
   ```

2. **Trigger Support Tickets**:
   Open a new terminal window and inject the tickets:
   ```bash
   bash examples/2_customer_support_triage/simulate.sh
   ```

3. **Watch the Cascade**:
   Check `http://localhost:8080` to see how the system categorizes the routine password reset vs the angry escalation.
