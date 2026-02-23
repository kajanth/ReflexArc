# 🧠 NSA ReflexArc — Neuro-Synthetic Autonomous System

A bio-inspired, config-driven AI organism that processes the physical world through a multi-layer neural cascade. It sees, hears, feels, learns, dreams, plans, and predicts — like a complete digital nervous system.

**One config file = one brain.** Swap `config/brain.yaml` to repurpose the entire system for any domain: DevOps, trading, IoT, customer support, or anything else. The core cascade is 100% domain-agnostic.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SENSORY INPUT ($0)                              │
│ 👀 Vision  👂 Audio  📡 Vitals  📂 Files  🌐 Net  🛡️ Threats  📨 API   │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ spike
                    ┌────▼─────┐
                    │ Layer 1  │  RAS (Habituation Filter)
                    │  $0.00   │  Local embeddings — drops background noise
                    └────┬─────┘
                         │ novel
                    ┌────▼─────┐
                    │ Layer 2  │  Thalamus (Triage)
                    │ ~$0.001  │  Cheap model — routes to REFLEX, TEMPLATE, or COMPLEX
                    └────┬─────┘
                   ┌─────┼──────────┐
              ┌────▼──┐ ┌▼────────┐ ┌▼────────┐
              │Layer 5│ │Layer 4.5│ │ Layer 4  │
              │ $0.00 │ │~$0.001  │ │ ~$0.01+  │
              │Reflex │ │Template │ │ Cortex   │
              │Python │ │Guided AI│ │Full Think│
              └───┬───┘ └────┬────┘ └─────┬────┘
                  └──────────┼────────────┘
                        ┌────▼─────┐
                        │ Layer 5.5│  Basal Ganglia — Habit Reinforcement
                        │  $0.00   │  Repeated patterns get faster routing
                        └──────────┘
                              │
         ┌────────────────────┼────────────────────┐
    ┌────▼─────┐        ┌────▼─────┐         ┌────▼─────┐
    │  🌙 Dream │        │  🎯 Goals │         │  👁️ Predict│
    │  Engine   │        │  Engine   │         │  Engine   │
    │ Overnight │        │ Every 5m  │         │ Every 2m  │
    │ $0.03/cyc │        │ $0/eval   │         │  $0.00    │
    └──────────┘        └──────────┘         └──────────┘
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url> && cd ReflexArc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Providers

Set **at least one** API key. The router auto-discovers available providers:

```bash
# Option A: OpenAI
export OPENAI_API_KEY="sk-..."

# Option B: Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Option C: Google Gemini
export GOOGLE_API_KEY="AIza..."

# Option D: AWS Bedrock (uses IAM or explicit keys)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

### 3. Run

```bash
python main.py
```

The system will load your brain config, show which providers are online, initialize all sensors, start the API server on port `8080`, and enter zero-token idle mode — consuming no API tokens until a sensory spike is detected.

**Environment variables:**
```bash
NSA_API_PORT=9090 python main.py                     # Change API port
NSA_BRAIN_CONFIG=config/trading.yaml python main.py   # Use a different brain profile
```

---

## 📁 Project Structure

```
ReflexArc/
├── main.py                    # Entry point — config-driven sensor loop
├── brain_core.py              # NSAOrchestrator — the neural cascade
├── api_server.py              # HTTP API + WebSocket + dashboard
├── agent.md                   # System DNA — identity & protocols
├── plugin_loader.py           # 🔌 Config-driven dynamic plugin loader
├── sensor_manager.py          # Sensor registry with enable/disable
├── event_bus.py               # Pub/sub event system
├── basal_ganglia.py           # Habit formation & pattern reinforcement
├── skill_template_engine.py   # Layer 4.5 — guided AI via markdown templates
├── dream_engine.py            # 🌙 Offline memory consolidation (REM sleep)
├── prefrontal_cortex.py       # 🎯 Goal-directed planning & evaluation
├── predictive_cortex.py       # 👁️ Anticipatory sensing & phantom spikes
│
├── config/                    # Brain profiles (swap to change domain)
│   ├── brain.yaml             # DevOps brain (default)
│   ├── brain.json             # JSON fallback (no PyYAML needed)
│   └── trading.yaml           # Example: trading brain
│
├── providers/                 # Multi-provider model router
│   ├── base.py                # BaseProvider ABC + StandardResponse
│   ├── router.py              # ModelRouter (cheapest/weighted/priority)
│   ├── openai_provider.py     # GPT-4o, GPT-4.1, o3-mini
│   ├── anthropic_provider.py  # Claude 3.5, Claude 4
│   ├── gemini_provider.py     # Gemini 2.0 Flash, 2.5 Pro
│   └── bedrock_provider.py    # Any Bedrock model (Converse API)
│
├── sensors/                   # Layer 0 — peripheral & internal senses
│   ├── vision.py              # 👀 Motion detection (OpenCV)
│   ├── auditory.py            # 👂 Sound spike detection (PyAudio)
│   ├── system_vitals.py       # 📡 CPU/RAM/Disk/Temp pain signals
│   ├── filesystem.py          # 📂 Proprioception (watchdog)
│   ├── network_probe.py       # 🌐 Connectivity & latency
│   ├── threat_detection.py    # 🛡️ Amygdala — process/port scanning
│   ├── curiosity.py           # 💰 Cost & latency tracking
│   ├── circadian.py           # ⏰ Sleep/Active/Drowsy cycle
│   └── cognitive_load.py      # 📊 Cortex-vs-Reflex ratio
│
├── skills/                    # Layer 5 — Cerebellum ($0 reflexes)
│   ├── templates/             # Layer 4.5 — AI skill templates (.md)
│   ├── quarantine_process.py  # 🛡️ Immune
│   ├── firewall_block.py
│   ├── forensic_snapshot.py
│   ├── memory_cleanup.py      # 🫀 Autonomic
│   ├── disk_pressure_relief.py
│   ├── self_restart.py
│   ├── daily_digest.py        # 🧬 Endocrine
│   ├── alert_notify.py
│   ├── schedule_task.py
│   ├── file_organizer.py      # 🦾 Motor Cortex
│   ├── shell_executor.py
│   ├── api_caller.py
│   ├── token_budget_enforcer.py # ⚡ Metabolic
│   ├── skill_indexer.py
│   ├── cognitive_defrag.py
│   └── auto_*.py              # 🧬 Auto-generated by Dream Engine
│
├── memory/                    # Hippocampus + system state
│   ├── hippocampus.py         # Vector memory (SentenceTransformer + SQLite)
│   ├── long_term_memory.db    # Stored memories
│   ├── stats.json             # Cost/latency tracking
│   ├── goals.json             # Persistent objectives (Prefrontal Cortex)
│   ├── causal_log.json        # Action → outcome tracking
│   ├── patterns.json          # Discovered memory patterns (Dream Engine)
│   ├── predictions.json       # Forecast state
│   ├── dream_journal/         # Nightly dream reports
│   └── providers.json         # Provider routing config
│
├── web/
│   └── dashboard.html         # 🖥️ Real-time web dashboard
│
└── requirements.txt
```

---

## 🔌 Config-Driven Plugin System

The entire brain is assembled from a single config file. Swap it to change domains.

### `config/brain.yaml`

```yaml
brain:
  name: "DevOps Brain"
  heartbeat_interval: 30
  prediction_interval: 120
  goal_eval_interval: 300

sensors:
  - name: system_vitals
    module: sensors.system_vitals.SystemVitalsSensor
    emoji: "📡"
    label: "System Vitals"
    type: peripheral

  - name: circadian
    source: brain.circadian    # Internal sensors reference brain attributes
    emoji: "⏰"
    type: internal

predictions:
  - name: cpu_percent
    measurer: psutil.cpu_percent
    threshold: 90
    direction: above
    unit: "%"

custom_measurers:
  - name: portfolio_value
    module: plugins.measurers.portfolio.get_value
```

### Switching Domains

```bash
# DevOps (default)
python3 main.py

# Trading
NSA_BRAIN_CONFIG=config/trading.yaml python3 main.py

# IoT / Smart Home
NSA_BRAIN_CONFIG=config/iot.yaml python3 main.py
```

| Domain | Sensors | Skills | Goals |
|--------|---------|--------|-------|
| **DevOps** | CPU, network, logs | restart_service, scale_pods | "p95 latency < 200ms" |
| **Trading** | price_feed, order_book, news | place_order, hedge | "Sharpe ratio > 1.5" |
| **IoT** | temperature, motion, energy | adjust_thermostat | "Energy < $100/mo" |
| **Support** | ticket_queue, CSAT | auto_reply, route | "Avg response < 5min" |

---

## 🔄 The Neural Cascade

Every sensory spike flows through this hierarchy:

| Layer | Name | Cost | What It Does |
|-------|------|------|--------------|
| **0** | Peripheral Senses | $0 | Hardware detection (OpenCV, PyAudio, psutil) |
| **1** | RAS | $0 | Local embedding similarity — drops background noise |
| **3** | Hippocampus | $0 | Stores/retrieves context from vector memory (SQLite) |
| **2** | Thalamus | ~$0.001 | Cheap model triage: REFLEX / TEMPLATE / LOG / COMPLEX |
| **5** | Cerebellum | $0 | Executes Python skills — the preferred outcome |
| **4.5** | Template Engine | ~$0.001 | Guided AI via markdown templates |
| **4** | Cortex | ~$0.01+ | Full reasoning — last resort, proposes new skills |
| **5.5** | Basal Ganglia | $0 | Reinforces repeated patterns for faster routing |

**Advanced Systems:**

| System | Cycle | Cost | What It Does |
|--------|-------|------|--------------|
| ❤️ **Digital Heart** | Every 30s | $0 | Periodic health checks, circadian monitoring |
| 🌙 **Dream Engine** | Overnight | ~$0.03 | Clusters memories, names patterns, auto-generates skills, prunes stale data |
| 🎯 **Prefrontal Cortex** | Every 5min | ~$0.001 | Evaluates persistent goals, generates proactive spikes when off-track |
| 👁️ **Predictive Cortex** | Every 2min | $0 | Exponential smoothing forecasts → phantom spikes before breaches |

---

## 📡 API Reference

### Inject Spikes

```bash
# Generic spike
curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{"description": "Deployment completed for v2.3.1", "sense_type": "ci_cd"}'

# High-priority threat
curl -X POST http://localhost:8080/spike/threat \
  -H 'Content-Type: application/json' \
  -d '{"description": "Unauthorized SSH login from 192.168.1.100"}'

# Metric breach
curl -X POST http://localhost:8080/spike/metric \
  -H 'Content-Type: application/json' \
  -d '{"metric": "cpu_usage", "value": 95.2, "unit": "%", "threshold": 90.0}'
```

### Query System State

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Full system status (providers, circadian, cognitive load, goals, predictions) |
| `/skills` | GET | List all Python skills + AI templates |
| `/memories/recent` | GET | Recent hippocampus memories |
| `/health` | GET | Health check for load balancers |
| `/sensors` | GET | All sensors with enable/disable state |

### Goal Management (Prefrontal Cortex)

```bash
# Create a goal
curl -X POST http://localhost:8080/goal \
  -H 'Content-Type: application/json' \
  -d '{"objective":"Keep CPU below 80%","metric":"cpu_percent","operator":"<","value":80,"priority":"high"}'

# List all goals with status
curl http://localhost:8080/goals

# Force evaluation cycle
curl -X POST http://localhost:8080/goal/evaluate

# Remove a goal
curl -X DELETE http://localhost:8080/goal \
  -H 'Content-Type: application/json' -d '{"id":"..."}'
```

### Predictions (Predictive Cortex)

```bash
# Current forecasts for all metric channels
curl http://localhost:8080/predictions

# Phantom spike history
curl http://localhost:8080/predictions/history
```

### Dream Engine

```bash
# Recent dream journal entries
curl http://localhost:8080/dreams/recent

# Discovered memory patterns
curl http://localhost:8080/patterns

# Manually trigger a dream cycle
curl -X POST http://localhost:8080/dream/trigger
```

### Sensors

```bash
# Toggle a sensor on/off
curl -X POST http://localhost:8080/sensor/toggle \
  -H 'Content-Type: application/json' -d '{"sensor":"vision"}'
```

### Skills

```bash
# Manually run a skill
curl -X POST http://localhost:8080/skill/run \
  -H 'Content-Type: application/json' \
  -d '{"skill": "forensic_snapshot", "data": "Manual trigger"}'
```

### WebSocket

```
ws://localhost:8080/ws/live
```

Real-time events: `spike`, `heartbeat`, `dream_cycle`, `skill_genesis`, `goal_evaluation`, `prediction_update`, `phantom_spike`, `sensor_toggle`, and more.

---

## 🖥️ Dashboard

A real-time web dashboard is available at **http://localhost:8080** during runtime.

**Panels include:**
- 📊 System stats (token spend, latency, efficiency)
- 📡 Sensors (with toggle switches)
- 🎯 Goals (color-coded progress bars: 🟢 on track / 🟡 at risk / 🔴 off track)
- 👁️ Predictions (trend arrows ↑↓→, breach-time estimates)
- 🧬 Recent memories
- 🦾 Skills (with flash-on-execute)
- 🌙 Dream state indicator (☀️ AWAKE / 🌙 DREAMING)
- ⚡ Neural cascade status (IDLE → TRIAGE → REFLEX/CORTEX)

---

## 🧩 Extending the System

### Add a New Sensor

Create `sensors/my_sensor.py`:

```python
class MySensor:
    async def monitor(self):
        """Return (True, description) on spike, (False, None) otherwise."""
        if something_happened:
            return True, "Description of what happened"
        return False, None

    def release(self):
        pass
```

Add to `config/brain.yaml`:
```yaml
sensors:
  - name: my_sensor
    module: sensors.my_sensor.MySensor
    args: { threshold: 100 }
    emoji: "🔔"
    label: "My Sensor"
    type: peripheral
```

### Add a New Skill

Create `skills/my_skill.py`:

```python
def run(data=None):
    """
    Category: autonomic
    Trigger: System Vitals sensor
    """
    result = "Did the thing."
    print(f"[Cerebellum]: {result}")
    return result
```

Auto-discovered by the Thalamus via `os.listdir('skills')`.

### Add a New AI Template

Create `skills/templates/my_template.md`:

```markdown
---
name: my_template
model: nano
category: analysis
description: Does something smart cheaply
max_tokens: 100
---

# System Prompt
You are a specialist in X.

# User Prompt
Analyze this: {{stimulus}}
Context: {{context}}
```

### Add a New Provider

```python
# providers/my_provider.py
from providers.base import BaseProvider, StandardResponse

class MyProvider(BaseProvider):
    @property
    def provider_name(self):
        return "myprovider"

    def is_available(self):
        return self._get_env_key("MY_API_KEY") is not None

    def chat(self, messages, model, max_tokens=200):
        return StandardResponse(content="...", prompt_tokens=10,
                                completion_tokens=20, model=model,
                                provider=self.provider_name)
```

Register in `providers/router.py` and add to `memory/providers.json`.

### Add Custom Measurers (for Goals & Predictions)

Add to `config/brain.yaml`:

```yaml
custom_measurers:
  - name: response_time
    module: plugins.measurers.api.get_p95_latency

predictions:
  - name: response_time
    measurer: plugins.measurers.api.get_p95_latency
    threshold: 200
    direction: above
    unit: "ms"
    description: "API P95 Latency"
```

Then create a goal targeting that metric:
```bash
curl -X POST http://localhost:8080/goal \
  -d '{"objective":"Keep P95 under 200ms","metric":"response_time","operator":"<","value":200}'
```

---

## 📊 Protocols

### Protocol Alpha — Conservation of Token Energy
Never use an expensive model for a cheap problem. `REFLEX > TEMPLATE > LOG > COMPLEX`. Budget enforced at $0.50/day.

### Protocol Beta — Contextual Anchoring
Every spike stored in Hippocampus. Thalamus always sees recent context for pattern matching.

### Protocol Gamma — Self-Optimization (Dream Cycle)
During SLEEP phase, the Dream Engine runs 4 phases:
1. **Replay** — Cluster memories by semantic similarity ($0)
2. **Consolidate** — Name patterns via AI (~$0.01)
3. **Skill Genesis** — Auto-generate Python skills for recurring patterns (~$0.02)
4. **Prune** — Deduplicate + age-prune stale memories ($0)

Output: `memory/dream_journal/YYYY-MM-DD.md`

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `openai` | OpenAI provider |
| `anthropic` | Anthropic Claude provider |
| `google-genai` | Google Gemini provider |
| `boto3` | AWS Bedrock provider |
| `aiohttp` | API server + WebSocket |
| `sentence-transformers` | RAS local embeddings ($0) |
| `opencv-python` | Vision sensor |
| `pyaudio` | Auditory sensor |
| `psutil` | System vitals + metrics |
| `watchdog` | Filesystem sensor |
| `numpy` | Vector math for RAS + clustering |
| `pyyaml` | YAML config (optional — JSON fallback) |

---

## 📜 License

MIT
