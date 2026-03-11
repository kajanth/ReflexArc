# Technology Stack

## Language & Runtime

- Python 3.x
- Async/await patterns throughout (asyncio)
- Type hints for better code clarity

## Core Dependencies

### AI/ML Providers
- `openai` - OpenAI GPT models
- `anthropic` - Claude models
- `google-genai` - Gemini models
- `boto3` - AWS Bedrock provider
- `sentence-transformers` - Local embeddings ($0 cost)

### Web & API
- `aiohttp` - Async HTTP server + WebSocket support
- `pydantic` - Request/response validation and config schemas

### System Monitoring
- `psutil` - System vitals (CPU, memory, disk)
- `opencv-python` - Vision sensor
- `pyaudio` - Auditory sensor
- `watchdog` - Filesystem monitoring

### Data & Storage
- `aiosqlite` - Async SQLite for Hippocampus memory
- `numpy` - Vector operations for RAS and clustering
- `scikit-learn` - Memory clustering in Dream Engine

### Configuration
- `pyyaml` - YAML config parsing (optional, JSON fallback available)
- `structlog` - Structured logging

## Common Commands

### Setup
```bash
workon AI
# python3 -m venv .venv
# source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running
```bash
# Default brain (DevOps)
python main.py

# Custom brain profile
NSA_BRAIN_CONFIG=config/trading.yaml python main.py

# Custom API port
NSA_API_PORT=9090 python main.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config_schema.py

# Run with verbose output
python -m pytest -v tests/

# Manual test scripts (for interactive testing)
python test_pooling_manual.py
python test_model_cleanup_manual.py
```

### Type Checking
```bash
mypy brain_core.py providers/ memory/
```

## Environment Variables

Required (at least one):
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GOOGLE_API_KEY` - Google Gemini API key
- `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_DEFAULT_REGION` - AWS Bedrock

Optional:
- `NSA_API_PORT` - API server port (default: 8080)
- `NSA_BRAIN_CONFIG` - Path to brain config file (default: config/brain.yaml)
- `TOKENIZERS_PARALLELISM` - Set to "false" to avoid warnings
- `HF_HUB_DISABLE_SYMLINKS_WARNING` - Set to "1" to suppress warnings

## API Documentation

Interactive OpenAPI docs available at:
- Swagger UI: `http://localhost:8080/docs`
- OpenAPI spec: `http://localhost:8080/openapi.yaml`

## Development Tools

- `mypy` - Static type checking
- `pybreaker` - Circuit breaker pattern for provider resilience
- `pytest` - Testing framework (implied by test files)
