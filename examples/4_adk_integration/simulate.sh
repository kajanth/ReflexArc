#!/bin/bash
# ═══════════════════════════════════════════════
# Simulate a Complex Incident triggering ADK
# ═══════════════════════════════════════════════

echo "🔥 Simulating a complex triage event that requires ADK orchestration..."

curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "SECURITY ALERT: Multiple failed SSH login attempts followed by an unusual outbound connection from web-node-04 to a flagged IP address. Perform a forensic snapshot and investigate.", 
    "sense_type": "webhook",
    "source": "threat_monitor"
  }'

echo -e "\n\n✅ Spikes injected. Check the ReflexArc dashboard or console for the ADK SequentialAgent response!"
