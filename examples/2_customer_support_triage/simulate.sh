#!/bin/bash
# ═══════════════════════════════════════════════
# Simulate a Support Ticket Spike
# ═══════════════════════════════════════════════

echo "📩 Simulating a routine password reset request..."

curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "User is asking how to reset their password.", 
    "sense_type": "support_ticket",
    "customer": "VIP"
  }'

echo -e "\n\n🚨 Simulating an angry priority escalation..."

curl -X POST http://localhost:8080/spike/threat \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "I have been charged 3 times for this, I demand a refund now!! This is unacceptable.", 
    "confidence": 0.99
  }'

echo -e "\n\n✅ Spikes injected. Check the ReflexArc dashboard or console for triage routing (Reflex vs Template vs Cortex)."
