#!/bin/bash
# ═══════════════════════════════════════════════
# Simulate IoT Events
# ═══════════════════════════════════════════════

echo "🌡️ Simulating a temperature increase..."

curl -X POST http://localhost:8080/spike/metric \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "room_temp", 
    "value": 82.5, 
    "unit": "°F", 
    "threshold": 78.0,
    "description": "Temperature in Living Room exceeded 78°F threshold."
  }'

echo -e "\n\n📷 Simulating unexpected motion detection..."

curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Motion detected at front door cam while house is marked empty.", 
    "sense_type": "vision",
    "priority": 10
  }'

echo -e "\n\n✅ Spikes injected. Check the ReflexArc dashboard or console for autonomous response (like turning on AC or alerting the owner)."
