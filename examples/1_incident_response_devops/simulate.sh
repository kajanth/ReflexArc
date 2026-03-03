#!/bin/bash
# ═══════════════════════════════════════════════
# Simulate a DevOps Incident
# ═══════════════════════════════════════════════

echo "🔥 Simulating a CPU spike incident..."

curl -X POST http://localhost:8080/spike/metric \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "cpu_usage", 
    "value": 98.5, 
    "unit": "%", 
    "threshold": 90.0,
    "description": "CPU usage spiked to 98.5% on worker-node-03"
  }'

echo -e "\n\n🚨 Simulating a Datadog Webhook Alert..."

curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "P1 ALERT: API latency degraded. p95 > 2000ms. 502 Bad Gateway spike detected on auth-service.", 
    "sense_type": "webhook",
    "source": "datadog"
  }'

echo -e "\n\n✅ Spikes injected. Check the ReflexArc dashboard or console for the autonomous response."
