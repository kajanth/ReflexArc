# Project Structure

## Root Level Files

- `main.py` - Entry point, sensor loop orchestration, graceful shutdown handling
- `brain_core.py` - NSAOrchestrator class, neural cascade implementation
- `api_server.py` - HTTP API + WebSocket server + dashboard
- `agent.md` - System DNA, identity, and protocols (loaded into Cortex context)
- `plugin_loader.py` - Config-driven dynamic plugin loader (BrainConfig class)
- `sensor_manager.py` - Sensor registry with enable/disable functionality
- `event_bus.py` - Pub/sub event system for system-wide notifications
- `basal_ganglia.py` - Habit formation and pattern reinforcement (Layer 5.5)
- `skill_template_engine.py` - Layer 4.5 guided AI via markdown templates
- `dream_engine.py` - Offline memory consolidation (REM sleep simulation)
- `prefrontal_cortex.py` - Goal-directed planning and evaluation
- `predictive_cortex.py` - Anticipatory sensing with phantom spikes
- `brocas_area.py` - Natural language interface for system interrogation
- `heartbeat.py` - DigitalHeart class for periodic maintenance pulses
- `mcp_client.py` - Model Context Protocol client for external tools
- `requirements.txt` - Python dependencies

## Configuration (`config/`)

Brain profiles that define the entire system behavior:
- `brain.yaml` - Default DevOps brain configuration
- `brain.json` - JSON fallback (no PyYAML needed)
- `schema.py` - Pydantic schemas for config validation
- Domain-specific configs: `trading.yaml`, `iot.yaml`, `secops.yaml`, `support.yaml`, `mlops.yaml`

Config structure:
- `brain` - Core settings (intervals, database, embedding model)
- `sensors` - Peripheral and internal sensor definitions
- `predictions` - Prediction channel configurations
- `custom_measurers` - Custom metric functions for goals
- `mcp_servers` - External tool server configurations

## Providers (`providers/`)

Multi-provider model router with cost optimization:
- `base.py` - BaseProvider ABC, StandardResponse, ModelInfo, ProviderConfig
- `router.py` - ModelRouter with tier-based routing (nano/mini/cortex)
- `openai_provider.py` - OpenAI GPT models
- `anthropic_provider.py` - Anthropic Claude models
- `gemini_provider.py` - Google Gemini models
- `bedrock_provider.py` - AWS Bedrock models (Converse API)
- `circuit_breaker.py` - Resilience pattern for provider failures
- `pricing.py` - Cost calculation utilities

## Sensors (`sensors/`)

Layer 0 - Peripheral and internal senses:
- `base.py` - BaseSensor ABC
- `vision.py` - OpenCV motion detection
- `auditory.py` - PyAudio sound spike detection
- `system_vitals.py` - CPU/RAM/Disk/Temp monitoring (psutil)
- `filesystem.py` - File change detection (watchdog)
- `network_probe.py` - Connectivity and latency monitoring
- `threat_detection.py` - Process/port scanning (Amygdala)
- `webhook_receptor.py` - External webhook handling
- `curiosity.py` - Cost and latency tracking (6th sense)
- `circadian.py` - Sleep/Active/Drowsy cycle management
- `cognitive_load.py` - Cortex vs Reflex ratio tracking

## Skills (`skills/`)

Layer 5 - Cerebellum ($0 reflexes):
- Python modules with `run(data)` function
- Auto-discovered by Thalamus via `os.listdir('skills')`
- Docstring format: Category, Trigger, Description
- Categories: autonomic, immune, motor, endocrine, metabolic
- `auto_*.py` - Auto-generated skills from Dream Engine

### Skill Templates (`skills/templates/`)

Layer 4.5 - Guided AI templates:
- Markdown files with YAML frontmatter
- Variables: `{{stimulus}}`, `{{context}}`, `{{sense_type}}`
- Frontmatter: name, model, category, description, max_tokens
- Examples: `classify_threat.md`, `compose_alert.md`, `explain_anomaly.md`

## Memory (`memory/`)

Hippocampus and system state:
- `hippocampus.py` - Vector memory with async connection pooling
- `long_term_memory.db` - SQLite database for memories
- `stats.json` - Cost/latency tracking
- `habits.json` - Basal ganglia habit reinforcement data
- `patterns.json` - Discovered patterns from Dream Engine
- `providers.json` - Provider routing configuration
- `schedule.json` - Scheduled task state
- `sensor_state.json` - Sensor enable/disable state
- `dream_journal/` - Nightly dream cycle reports (YYYY-MM-DD.md)
- Log files: `firewall_log.json`, `quarantine_log.json`, `notify_log.json`, etc.

## API (`api/`)

HTTP API request/response models:
- `models.py` - Pydantic models for endpoint validation
- Request models: SpikeRequest, GoalRequest, SkillRunRequest, SensorToggleRequest, etc.
- Validation: Input sanitization, length limits, character restrictions

## Tests (`tests/`)

Unit and integration tests:
- `test_config_schema.py` - Config validation tests
- `test_api_models.py` - API request validation tests
- `test_hippocampus_pooling.py` - Database connection pooling tests
- `test_model_cleanup.py` - Embedding model cleanup tests
- `test_sensor_base.py` - Sensor base class tests

Manual test scripts at root level for interactive testing.

## Utilities (`utils/`)

Shared utilities:
- `embeddings.py` - Shared embedding model management with caching
- `logging_config.py` - Structured logging configuration (structlog)

## Web (`web/`)

Frontend assets:
- `dashboard.html` - Real-time web dashboard with WebSocket
- `docs.html` - API documentation viewer

## Examples (`examples/`)

Domain-specific example configurations:
- `1_incident_response_devops/` - DevOps incident response
- `2_customer_support_triage/` - Customer support automation
- `3_smart_home_iot/` - IoT smart home control

Each example includes: README.md, brain.yaml, simulate.sh

## Documentation (`docs/`)

Technical documentation:
- `CONNECTION_POOLING.md` - Database pooling implementation details
- `EMBEDDING_MODEL_CONFIGURATION.md` - Embedding model setup guide
- `MCP_TOOL_CONFIGURATION.md` - MCP tool timeout handling and configuration
- `ADAPTIVE_POLLING.md` - Adaptive sensor polling implementation

## Code Organization Patterns

### Async First
All I/O operations use async/await. Sensors, memory, API, and providers are async.

### Plugin Architecture
Sensors, skills, providers, and measurers are dynamically loaded from config.

### Event-Driven
Event bus for system-wide notifications (spike, decision, reflex_exec, cortex_exec, etc.)

### Validation Everywhere
Pydantic schemas for configs and API requests. Input sanitization to prevent injection.

### Resource Management
Connection pooling for database, model caching for embeddings, graceful shutdown with cleanup.

### Naming Conventions
- Classes: PascalCase (NSAOrchestrator, SystemVitalsSensor)
- Functions/methods: snake_case (process_spike, get_metrics)
- Constants: UPPER_SNAKE_CASE (MEASURERS, PROVIDER_REGISTRY)
- Files: snake_case.py
- Config files: lowercase.yaml

### Import Organization
1. Standard library imports
2. Third-party imports
3. Local imports (with comment "# Local Imports")
