# 🧠 NSA ReflexArc — Neuro-Synthetic Autonomous System

A bio-inspired AI organism that processes the physical world through a 5-layer neural cascade, conserving token energy by preferring cheap local reflexes over expensive reasoning. It sees, hears, feels, and learns — like a digital nervous system.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SENSORY INPUT ($0)                              │
│ 👀 Vision  👂 Audio  📡 Vitals  📂 Files  🌐 Net  🛡️ Threats  📨 API   │
│                                                              ↑        │
│                                                     POST /spike       │
│                                                  (external systems)   │
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
              └───────┘ └─────────┘ └──────────┘
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

The system will show which providers are online, initialize all sensors, start the API server on port `8080`, and enter zero-token idle mode — consuming no API tokens until a sensory spike is detected.

To change the API port:
```bash
NSA_API_PORT=9090 python main.py
```

---

## 📁 Project Structure

```
ReflexArc/
├── main.py                    # Entry point — sensor loop + graceful shutdown
├── brain_core.py              # NSAOrchestrator — the 5-layer neural cascade
├── api_server.py              # 🌐 HTTP API — external stimulus receptor
├── agent.md                   # System DNA — identity, protocols, success metrics
├── dashboard.py               # Real-time status display
├── optimization_cycle.py      # Sleep Cycle — auto-generates new skills
├── skill_template_engine.py   # Layer 4.5 — guided AI via markdown templates
│
├── providers/                 # Multi-provider model router
│   ├── base.py                # BaseProvider ABC + StandardResponse
│   ├── router.py              # ModelRouter (cheapest/weighted/priority)
│   ├── openai_provider.py     # GPT-4o, GPT-5, o1, o3
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
│   │   ├── summarize_event.md
│   │   ├── classify_threat.md
│   │   ├── explain_anomaly.md
│   │   ├── suggest_skill.md
│   │   └── compose_alert.md
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
│   ├── system_check.py        # Legacy
│   ├── homeostasis.py
│   └── alert_security.py
│
├── memory/                    # Hippocampus + system state
│   ├── hippocampus.py         # Vector memory (SentenceTransformer + SQLite)
│   ├── long_term_memory.db    # Stored memories
│   ├── stats.json             # Cost/latency tracking
│   └── providers.json         # Provider routing config (auto-generated)
│
└── requirements.txt
```

---

## ⚙️ Configuration & Customization

### Provider Routing — `memory/providers.json`

Auto-generated on first run. Controls which provider handles each tier:

```json
{
  "strategy": "cheapest",
  "tiers": {
    "nano": [
      {"provider": "gemini",    "model": "gemini-2.0-flash",           "cost_per_1k_input": 0.0,     "cost_per_1k_output": 0.0,    "weight": 1.0},
      {"provider": "openai",    "model": "gpt-4o-mini",                "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006, "weight": 0.9},
      {"provider": "anthropic", "model": "claude-3-5-haiku-20241022",  "cost_per_1k_input": 0.0008,  "cost_per_1k_output": 0.004,  "weight": 0.7},
      {"provider": "bedrock",   "model": "anthropic.claude-3-5-haiku-20241022-v1:0", "cost_per_1k_input": 0.0008, "cost_per_1k_output": 0.004, "weight": 0.6}
    ],
    "mini": [ ... ],
    "cortex": [ ... ]
  }
}
```

| Field | Description |
|-------|-------------|
| `strategy` | `"cheapest"` (lowest cost), `"weighted"` (random by weight), `"priority"` (first available) |
| `cost_per_1k_input` | Cost per 1K input tokens — used for cheapest strategy sorting |
| `cost_per_1k_output` | Cost per 1K output tokens — used for cost estimation in logs |
| `weight` | 0.0–1.0 — higher = more likely to be chosen in weighted mode |
| `enabled` | Set to `false` to disable a specific model without removing it |

**Change the strategy at runtime:**
```bash
# Edit memory/providers.json and change "strategy" to "weighted"
# The router reloads config on each request
```

### Sensor Tuning

| Sensor | Config | Default |
|--------|--------|---------|
| **Vision** | `sensitivity` in `main.py` | `20000` (lower = more sensitive) |
| **Auditory** | `rms_threshold` in `main.py` | `500` (RMS amplitude) |
| **System Vitals** | `cpu_threshold`, `ram_threshold`, etc. in `sensors/system_vitals.py` | CPU: 90%, RAM: 90%, Disk: 95% |
| **Circadian** | `SLEEP_START`, `SLEEP_END`, `DROWSY_ZONE` in `sensors/circadian.py` | Sleep: 1–5 AM, Drowsy: 11 PM–1 AM & 5–7 AM |
| **Network Probe** | `endpoints` list in `sensors/network_probe.py` | Google DNS, OpenAI API |
| **Threat Detection** | `SUSPICIOUS_PORTS` in `sensors/threat_detection.py` | 4444, 5555, 1337, 31337, etc. |
| **Cognitive Load** | `OVERLOAD_THRESHOLD` in `sensors/cognitive_load.py` | 40% cortex ratio |
| **RAS Novelty** | `novelty_threshold` in `brain_core.py` | `0.22` (lower = more triggers) |

### Notifications — `memory/notify_config.json`

Configure webhooks for the `alert_notify` skill:

```json
{
  "channels": [
    {"type": "slack",   "name": "Ops Channel", "url": "https://hooks.slack.com/services/..."},
    {"type": "discord", "name": "Alerts",      "url": "https://discord.com/api/webhooks/..."},
    {"type": "webhook", "name": "PagerDuty",   "url": "https://events.pagerduty.com/..."}
  ]
}
```

Or use environment variables: `NSA_SLACK_WEBHOOK`, `NSA_DISCORD_WEBHOOK`, `NSA_WEBHOOK_URL`.

### Budget Control — `memory/budget_config.json`

```json
{
  "daily_budget": 0.50,
  "warning_threshold": 0.80
}
```

When spend exceeds the budget, `token_budget_enforcer` creates a lockdown flag that blocks Cortex calls.

### API Server — `api_server.py`

The API server runs on port `8080` by default (override with `NSA_API_PORT` env var).

| Env Variable | Default | Description |
|---|---|---|
| `NSA_API_PORT` | `8080` | Port for the HTTP API server |

---

## 📡 API Reference

External systems (CI/CD, monitoring, IoT, chatbots) can inject spikes into the neural cascade via HTTP.

### Inject Spikes

**`POST /spike`** — Generic spike injection
```bash
curl -X POST http://localhost:8080/spike \
  -H 'Content-Type: application/json' \
  -d '{"description": "Deployment completed for v2.3.1", "sense_type": "ci_cd", "priority": "normal"}'
```

**`POST /spike/threat`** — High-priority threat (bypasses normal priority)
```bash
curl -X POST http://localhost:8080/spike/threat \
  -H 'Content-Type: application/json' \
  -d '{"description": "Unauthorized SSH login from 192.168.1.100", "source": "fail2ban"}'
```

**`POST /spike/metric`** — System metric with threshold breach
```bash
curl -X POST http://localhost:8080/spike/metric \
  -H 'Content-Type: application/json' \
  -d '{"metric": "cpu_usage", "value": 95.2, "unit": "%", "source": "prometheus", "threshold": 90.0}'
```

### Query System State

**`GET /status`** — Full system status (providers, circadian, cognitive load)
```bash
curl http://localhost:8080/status
```

**`GET /skills`** — List all Python skills + AI templates
```bash
curl http://localhost:8080/skills
```

**`GET /memories/recent?limit=5`** — Recent hippocampus memories
```bash
curl http://localhost:8080/memories/recent?limit=5
```

**`GET /health`** — Simple health check for load balancers
```bash
curl http://localhost:8080/health
```

### Execute Skills

**`POST /skill/run`** — Manually trigger any Python skill
```bash
curl -X POST http://localhost:8080/skill/run \
  -H 'Content-Type: application/json' \
  -d '{"skill": "forensic_snapshot", "data": "Manual trigger from ops team"}'
```

---

## 🧩 Extending the System

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
        # Call your API, return StandardResponse
        return StandardResponse(
            content="...",
            prompt_tokens=10,
            completion_tokens=20,
            model=model,
            provider=self.provider_name,
        )
```

Register it in `providers/router.py`:
```python
PROVIDER_REGISTRY["myprovider"] = MyProvider
```

Then add it to `memory/providers.json` under any tier.

### Add a New Skill (Python Reflex)

Create `skills/my_skill.py`:

```python
def run(data=None):
    """
    Category: autonomic
    Trigger: System Vitals sensor
    """
    # Your $0 deterministic logic here
    result = "Did the thing."
    print(f"[Cerebellum]: {result}")
    return result
```

That's it. The Thalamus auto-discovers it via `os.listdir('skills')`.

### Add a New AI Template

Create `skills/templates/my_template.md`:

```markdown
---
name: my_template
model: nano
category: analysis
description: Does something smart cheaply
output_format: text
max_tokens: 100
---

# System Prompt
You are a specialist in X.

# User Prompt
Analyze this: {{stimulus}}
Context: {{context}}
```

Available variables: `{{stimulus}}`, `{{context}}`, `{{sense_type}}`, `{{internal_state}}`.

Model tiers: `nano` (cheapest), `mini` (mid), `cortex` (full reasoning).

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
        """Cleanup resources."""
        pass
```

Register it in `main.py` under the `sensors` dict.

---

## 🔄 The Neural Cascade

Every sensory spike flows through this hierarchy:

| Layer | Name | Cost | What It Does |
|-------|------|------|--------------|
| **0** | Peripheral Senses | $0 | Hardware detection (OpenCV, PyAudio, psutil) |
| **1** | RAS (Reticular Activating System) | $0 | Local embedding similarity — drops background noise |
| **3** | Hippocampus | $0 | Stores/retrieves context from vector memory (SQLite) |
| **2** | Thalamus | ~$0.001 | Cheap model triage: REFLEX / TEMPLATE / LOG / COMPLEX |
| **5** | Cerebellum | $0 | Executes Python skills — the preferred outcome |
| **4.5** | Template Engine | ~$0.001 | Guided AI via markdown templates |
| **4** | Cortex | ~$0.01+ | Full reasoning — last resort, proposes new skills |

**Goal:** Push >90% of actions to Layer 5 (Cerebellum). Every time the Cortex fires, the Sleep Cycle should harden that pattern into a new reflex.

---

## 📊 Protocols

### Protocol Alpha — Conservation of Token Energy
Never use an expensive model for a cheap problem. The Thalamus enforces: `REFLEX > TEMPLATE > LOG > COMPLEX`. The `token_budget_enforcer` skill hard-blocks Cortex at $0.50/day.

### Protocol Beta — Contextual Anchoring
Every spike is stored in the Hippocampus. When reasoning, the Thalamus always sees the last similar events for pattern matching.

### Protocol Gamma — Self-Optimization (Sleep Cycle)
During low-activity periods (detected by the Circadian sensor), the system:
1. Runs `daily_digest` — summarizes the day
2. Runs `cognitive_defrag` — merges duplicate memories
3. Runs `memory_cleanup` — prunes old memories
4. Analyzes repeated Cortex calls and proposes new Python skills to handle them

---

## 📋 Skills Reference

### 🛡️ Immune System (Defense & Security)

| Skill | What It Does |
|-------|-------------|
| `quarantine_process` | Suspends suspicious processes by PID with safety whitelist |
| `firewall_block` | Logs + blocks suspicious connections (macOS pf / Linux iptables) |
| `forensic_snapshot` | Captures full system state (processes, ports, connections) to JSON |

### 🫀 Autonomic (Self-Maintenance)

| Skill | What It Does |
|-------|-------------|
| `memory_cleanup` | Synaptic pruning — removes old/duplicate memories from hippocampus |
| `disk_pressure_relief` | Cleans pycache, rotates logs, vacuums SQLite |
| `self_restart` | Graceful restart with loop detection (>3 in 10 min = abort) |

### 🧬 Endocrine (Scheduling & Communication)

| Skill | What It Does |
|-------|-------------|
| `daily_digest` | Generates markdown summary from day's memories + stats |
| `alert_notify` | Sends webhooks (Slack/Discord/HTTP) for critical events |
| `schedule_task` | Cron-like task queue — `add:skill:hour:desc`, `check`, `list` |

### 🦾 Motor Cortex (Environment Interaction)

| Skill | What It Does |
|-------|-------------|
| `file_organizer` | Validates auto-skills, backs up modified skills |
| `shell_executor` | Runs whitelisted commands only (`uptime`, `git status`, `df`, etc.) |
| `api_caller` | HTTP calls to pre-configured endpoints (GitHub/OpenAI status, etc.) |

### ⚡ Metabolic (Cost Optimization)

| Skill | What It Does |
|-------|-------------|
| `token_budget_enforcer` | Enforces $0.50/day budget; LOCKDOWN mode blocks Cortex |
| `skill_indexer` | AST-scans all skills → generates `memory/skill_index.json` manifest |
| `cognitive_defrag` | Merges near-duplicate memories by cosine similarity (sleep spindles) |

---

## 🖥️ Dashboard

```bash
python dashboard.py
```

Displays real-time:
- Token spend & estimated savings
- Cognitive latency
- Active sensors (9)
- Cortex ratio & efficiency score
- Circadian phase (ACTIVE / DROWSY / SLEEP)
- Recent memories
- Learned skills

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `openai` | OpenAI provider |
| `anthropic` | Anthropic Claude provider |
| `google-genai` | Google Gemini provider |
| `boto3` | AWS Bedrock provider |
| `aiohttp` | API server (external stimulus receptor) |
| `sentence-transformers` | RAS local embeddings ($0) |
| `opencv-python` | Vision sensor |
| `pyaudio` | Auditory sensor |
| `psutil` | System vitals + forensics |
| `watchdog` | Filesystem sensor |
| `numpy` | Vector math for RAS + cognitive defrag |

---

## 📜 License

MIT
