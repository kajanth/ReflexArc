# Implementation Tasks: ReflexArc NSA Codebase Improvements

## Phase 1: Quick Wins (High Impact, Low Effort)

### 1. Add Async Database Support
- [ ] 1.1 Add `aiosqlite` to requirements.txt
- [ ] 1.2 Update `memory/hippocampus.py` to use async database operations
  - [ ] 1.2.1 Replace `sqlite3` with `aiosqlite`
  - [ ] 1.2.2 Convert `store_memory()` to async
  - [ ] 1.2.3 Convert `retrieve_context()` to async
  - [ ] 1.2.4 Add proper connection lifecycle management (async context manager)
- [ ] 1.3 Update all callers in `brain_core.py` to await async methods
- [ ] 1.4 Add connection pooling configuration

### 2. Implement Structured Logging
- [ ] 2.1 Add `structlog` to requirements.txt
- [ ] 2.2 Create `utils/logging_config.py` with structured logging setup
  - [ ] 2.2.1 Configure JSON output for production
  - [ ] 2.2.2 Add context processors (timestamp, level, logger name)
  - [ ] 2.2.3 Add development-friendly console renderer
- [ ] 2.3 Replace print statements in `brain_core.py` with structured logging
- [ ] 2.4 Replace print statements in `providers/router.py` with structured logging
- [ ] 2.5 Replace print statements in `main.py` with structured logging
- [ ] 2.6 Replace print statements in `event_bus.py` with structured logging
- [ ] 2.7 Replace print statements in `plugin_loader.py` with structured logging

### 3. Add Type Hints to Core APIs
- [ ] 3.1 Add type hints to `brain_core.py`
  - [ ] 3.1.1 Add type hints to `NSAOrchestrator.__init__()`
  - [ ] 3.1.2 Add type hints to `process_spike()` method
  - [ ] 3.1.3 Add type hints to `_get_internal_state()` method
  - [ ] 3.1.4 Add type hints to `_log_stats()` method
- [ ] 3.2 Add type hints to `providers/router.py`
  - [ ] 3.2.1 Add type hints to `ModelRouter` class methods
  - [ ] 3.2.2 Add type hints to `route()` method
  - [ ] 3.2.3 Add type hints to helper methods
- [ ] 3.3 Add type hints to `memory/hippocampus.py`
- [ ] 3.4 Add type hints to `event_bus.py`
- [ ] 3.5 Add `mypy` to dev dependencies for type checking

### 4. Implement Proper Resource Cleanup
- [ ] 4.1 Add `__aenter__` and `__aexit__` to `Hippocampus` for async context manager
- [ ] 4.2 Add `__del__` method to `Hippocampus` for cleanup fallback
- [ ] 4.3 Update `NSAOrchestrator` to properly close Hippocampus connection
- [ ] 4.4 Add cleanup for `SentenceTransformer` models on shutdown
- [ ] 4.5 Ensure all sensor `release()` methods are called in shutdown handler

### 5. Add Input Validation to API Endpoints
- [ ] 5.1 Add `pydantic` to requirements.txt (already present, verify version)
- [ ] 5.2 Create `api/models.py` with Pydantic request/response models
  - [ ] 5.2.1 Create `SpikeRequest` model with validation
  - [ ] 5.2.2 Create `GoalRequest` model with validation
  - [ ] 5.2.3 Create `SkillRunRequest` model with validation
  - [ ] 5.2.4 Create `SensorToggleRequest` model with validation
- [ ] 5.3 Update `api_server.py` to use Pydantic models for validation
  - [ ] 5.3.1 Add validation to `/spike` endpoint
  - [ ] 5.3.2 Add validation to `/goal` endpoint
  - [ ] 5.3.3 Add validation to `/skill/run` endpoint
  - [ ] 5.3.4 Add validation to `/sensor/toggle` endpoint
- [ ] 5.4 Add error handling for validation failures with proper HTTP status codes

## Phase 2: Architecture & Design Improvements

### 6. Optimize Embedding Model Usage
- [ ] 6.1 Create shared embedding model singleton in `utils/embeddings.py`
- [ ] 6.2 Update `brain_core.py` to use shared model
- [ ] 6.3 Update `memory/hippocampus.py` to use shared model
- [ ] 6.4 Add lazy loading for embedding model
- [ ] 6.5 Add model caching configuration

### 7. Implement Configuration Validation
- [ ] 7.1 Create `config/schema.py` with Pydantic schemas for brain config
  - [ ] 7.1.1 Create `BrainConfigSchema`
  - [ ] 7.1.2 Create `SensorConfigSchema`
  - [ ] 7.1.3 Create `PredictionConfigSchema`
  - [ ] 7.1.4 Create `MCPServerConfigSchema`
- [ ] 7.2 Update `plugin_loader.py` to validate config on load
- [ ] 7.3 Add helpful error messages for invalid configurations
- [ ] 7.4 Add config validation tests

### 8. Add Circuit Breakers for Provider Failures
- [ ] 8.1 Add `pybreaker` to requirements.txt
- [ ] 8.2 Create `providers/circuit_breaker.py` with circuit breaker logic
- [ ] 8.3 Integrate circuit breakers into `ModelRouter`
- [ ] 8.4 Add exponential backoff for failed providers
- [ ] 8.5 Add metrics for circuit breaker state changes

### 9. Implement Provider Discovery Caching
- [ ] 9.1 Add TTL-based caching for provider discovery results
- [ ] 9.2 Store cached discovery in `memory/provider_cache.json`
- [ ] 9.3 Add cache invalidation on manual rediscovery
- [ ] 9.4 Add configurable cache TTL (default 24 hours)

## Phase 3: Performance Optimizations

### 10. Optimize Sensor Polling
- [ ] 10.1 Implement event-driven sensor architecture
  - [ ] 10.1.1 Create `sensors/base.py` with async sensor interface
  - [ ] 10.1.2 Add support for event-driven sensors (webhooks, filesystem watchers)
  - [ ] 10.1.3 Add support for polled sensors with adaptive rates
- [ ] 10.2 Use `asyncio.gather()` for parallel sensor monitoring
- [ ] 10.3 Add adaptive polling rates based on sensor activity
- [ ] 10.4 Add sensor health monitoring and auto-disable for failing sensors

### 11. Optimize Event Bus Memory Management
- [ ] 11.1 Add periodic cleanup of old events in `event_bus.py`
- [ ] 11.2 Implement time-based event expiration (default 1 hour)
- [ ] 11.3 Add configurable history size limits
- [ ] 11.4 Add memory usage monitoring for event bus

### 12. Optimize Basal Ganglia Persistence
- [ ] 12.1 Implement batched writes for habit reinforcement
- [ ] 12.2 Add async I/O for habit persistence
- [ ] 12.3 Add write-behind caching with periodic flush
- [ ] 12.4 Add configurable flush interval (default 30 seconds)

### 13. Implement Parallel MCP Tool Execution
- [ ] 13.1 Analyze tool dependencies in `brain_core.py`
- [ ] 13.2 Execute independent tools in parallel using `asyncio.gather()`
- [ ] 13.3 Add timeout handling for tool execution
- [ ] 13.4 Add error isolation (one tool failure doesn't break others)

## Phase 4: Testing Infrastructure

### 14. Add Unit Tests
- [ ] 14.1 Add `pytest`, `pytest-asyncio`, `pytest-cov` to dev requirements
- [ ] 14.2 Create `tests/` directory structure
- [ ] 14.3 Add unit tests for RAS layer (`tests/test_ras.py`)
  - [ ] 14.3.1 Test novelty detection
  - [ ] 14.3.2 Test habituation filtering
  - [ ] 14.3.3 Test adaptive threshold adjustment
- [ ] 14.4 Add unit tests for Thalamus layer (`tests/test_thalamus.py`)
  - [ ] 14.4.1 Test routing decisions
  - [ ] 14.4.2 Test skill discovery
  - [ ] 14.4.3 Test template discovery
- [ ] 14.5 Add unit tests for Hippocampus (`tests/test_hippocampus.py`)
  - [ ] 14.5.1 Test memory storage
  - [ ] 14.5.2 Test context retrieval
  - [ ] 14.5.3 Test similarity search
- [ ] 14.6 Add unit tests for Basal Ganglia (`tests/test_basal_ganglia.py`)
  - [ ] 14.6.1 Test habit reinforcement
  - [ ] 14.6.2 Test habit optimization
  - [ ] 14.6.3 Test persistence

### 15. Add Integration Tests
- [ ] 15.1 Create `tests/integration/` directory
- [ ] 15.2 Add full cascade integration test (`tests/integration/test_cascade.py`)
  - [ ] 15.2.1 Test spike → RAS → Thalamus → Reflex flow
  - [ ] 15.2.2 Test spike → RAS → Thalamus → Template flow
  - [ ] 15.2.3 Test spike → RAS → Thalamus → Cortex flow
- [ ] 15.3 Add provider integration tests with mocks
- [ ] 15.4 Add sensor integration tests
- [ ] 15.5 Add API endpoint integration tests

### 16. Add Mock Providers for Testing
- [ ] 16.1 Create `tests/mocks/mock_provider.py`
- [ ] 16.2 Implement deterministic mock responses
- [ ] 16.3 Add cost tracking for test assertions
- [ ] 16.4 Add latency simulation
- [ ] 16.5 Update tests to use mock providers

### 17. Add Property-Based Tests
- [ ] 17.1 Add `hypothesis` to dev requirements
- [ ] 17.2 Add property tests for RAS habituation logic
- [ ] 17.3 Add property tests for cost optimization
- [ ] 17.4 Add property tests for event bus ordering

## Phase 5: Security & Reliability

### 18. Implement Rate Limiting
- [ ] 18.1 Add `aiohttp-ratelimit` or similar to requirements
- [ ] 18.2 Add rate limiting middleware to API server
- [ ] 18.3 Configure per-endpoint rate limits
  - [ ] 18.3.1 `/spike` endpoint: 100 req/min
  - [ ] 18.3.2 `/goal` endpoint: 10 req/min
  - [ ] 18.3.3 `/skill/run` endpoint: 20 req/min
- [ ] 18.4 Add rate limit headers to responses
- [ ] 18.5 Add rate limit exceeded error handling

### 19. Enhance Input Sanitization
- [ ] 19.1 Add length limits to spike descriptions (max 10KB)
- [ ] 19.2 Add sanitization for file paths in skill execution
- [ ] 19.3 Add validation for goal metric names (prevent injection)
- [ ] 19.4 Add content-type validation for API requests
- [ ] 19.5 Add CORS configuration for web dashboard

### 20. Implement Secrets Management
- [ ] 20.1 Add API key validation on startup
- [ ] 20.2 Add support for secrets rotation
- [ ] 20.3 Add audit logging for API key usage
- [ ] 20.4 Add encrypted storage option for sensitive data
- [ ] 20.5 Document secrets management best practices

### 21. Enhance Health Checks
- [ ] 21.1 Expand `/health` endpoint with detailed checks
  - [ ] 21.1.1 Check provider availability
  - [ ] 21.1.2 Check database connectivity
  - [ ] 21.1.3 Check memory usage
  - [ ] 21.1.4 Check sensor status
  - [ ] 21.1.5 Check event bus health
- [ ] 21.2 Add `/ready` endpoint for Kubernetes readiness probes
- [ ] 21.3 Add `/live` endpoint for liveness probes
- [ ] 21.4 Add health check timeout configuration

## Phase 6: Observability

### 22. Implement OpenTelemetry Instrumentation
- [ ] 22.1 Add `opentelemetry-api`, `opentelemetry-sdk` to requirements
- [ ] 22.2 Create `utils/telemetry.py` with tracing setup
- [ ] 22.3 Add tracing to neural cascade flow
  - [ ] 22.3.1 Trace RAS layer
  - [ ] 22.3.2 Trace Thalamus layer
  - [ ] 22.3.3 Trace Hippocampus layer
  - [ ] 22.3.4 Trace execution layers (Reflex/Template/Cortex)
- [ ] 22.4 Add custom spans for provider calls
- [ ] 22.5 Add span attributes for cost and latency

### 23. Add Metrics Collection
- [ ] 23.1 Add `prometheus-client` to requirements
- [ ] 23.2 Create `utils/metrics.py` with metric definitions
  - [ ] 23.2.1 Add counter for spikes by sense type
  - [ ] 23.2.2 Add histogram for cascade latency
  - [ ] 23.2.3 Add gauge for cost per spike
  - [ ] 23.2.4 Add counter for decisions by layer
- [ ] 23.3 Add `/metrics` endpoint for Prometheus scraping
- [ ] 23.4 Add Grafana dashboard JSON template

### 24. Enhance Error Tracking
- [ ] 24.1 Add `sentry-sdk` to optional requirements
- [ ] 24.2 Create `utils/error_tracking.py` with Sentry integration
- [ ] 24.3 Add error context (spike description, layer, provider)
- [ ] 24.4 Add breadcrumbs for cascade flow
- [ ] 24.5 Add performance monitoring integration

### 25. Add Audit Logging
- [ ] 25.1 Create `utils/audit_log.py` for audit events
- [ ] 25.2 Log all API requests with user context
- [ ] 25.3 Log all provider API calls with cost
- [ ] 25.4 Log all skill executions
- [ ] 25.5 Add audit log rotation and retention policy

## Phase 7: Documentation

### 26. Enhance API Documentation
- [ ] 26.1 Add request/response examples to OpenAPI spec
- [ ] 26.2 Add error code documentation
- [ ] 26.3 Add rate limit information
- [ ] 26.4 Add authentication documentation (if applicable)
- [ ] 26.5 Generate interactive API docs with examples

### 27. Add Code Documentation
- [ ] 27.1 Add docstrings to all public methods in `brain_core.py`
- [ ] 27.2 Add docstrings to all public methods in `providers/router.py`
- [ ] 27.3 Add docstrings to all public methods in `memory/hippocampus.py`
- [ ] 27.4 Add docstrings to all sensor classes
- [ ] 27.5 Add module-level docstrings explaining purpose

### 28. Create Architecture Decision Records
- [ ] 28.1 Create `docs/adr/` directory
- [ ] 28.2 Document ADR-001: Bio-inspired architecture choice
- [ ] 28.3 Document ADR-002: Cost-optimization strategy
- [ ] 28.4 Document ADR-003: Multi-provider routing
- [ ] 28.5 Document ADR-004: Event-driven observability

### 29. Add Developer Guide
- [ ] 29.1 Create `docs/DEVELOPMENT.md`
- [ ] 29.2 Document local development setup
- [ ] 29.3 Document testing procedures
- [ ] 29.4 Document debugging techniques
- [ ] 29.5 Document contribution guidelines

### 30. Add Operations Guide
- [ ] 30.1 Create `docs/OPERATIONS.md`
- [ ] 30.2 Document deployment procedures
- [ ] 30.3 Document monitoring and alerting
- [ ] 30.4 Document troubleshooting common issues
- [ ] 30.5 Document backup and recovery procedures

## Phase 8: Specific Bug Fixes

### 31. Fix Event Bus Memory Leak
- [ ] 31.1 Implement periodic cleanup in `event_bus.py`
- [ ] 31.2 Add time-based event expiration
- [ ] 31.3 Add memory monitoring
- [ ] 31.4 Add tests for memory leak prevention

### 32. Fix Circular Import Issues
- [ ] 32.1 Refactor `predictive_cortex.py` to avoid circular imports
- [ ] 32.2 Use dependency injection for orchestrator reference
- [ ] 32.3 Create interface/protocol for orchestrator
- [ ] 32.4 Update all circular dependencies

### 33. Fix Database Connection Leaks
- [ ] 33.1 Ensure all database connections are properly closed
- [ ] 33.2 Add connection pool monitoring
- [ ] 33.3 Add connection timeout configuration
- [ ] 33.4 Add tests for connection cleanup

### 34. Fix RAS Spike Time Memory Growth
- [ ] 34.1 Implement sliding window for spike times
- [ ] 34.2 Add automatic cleanup of old spike times
- [ ] 34.3 Add configurable retention period
- [ ] 34.4 Add memory usage monitoring

## Phase 9: CI/CD & Deployment

### 35. Add CI/CD Pipeline
- [ ] 35.1 Create `.github/workflows/test.yml` for automated testing
- [ ] 35.2 Add linting checks (flake8, black, mypy)
- [ ] 35.3 Add test coverage reporting
- [ ] 35.4 Add security scanning (bandit, safety)
- [ ] 35.5 Add dependency vulnerability scanning

### 36. Add Docker Support
- [ ] 36.1 Create production `Dockerfile`
- [ ] 36.2 Create development `docker-compose.yml`
- [ ] 36.3 Add multi-stage builds for optimization
- [ ] 36.4 Add health check configuration
- [ ] 36.5 Document Docker deployment

### 37. Add Kubernetes Manifests
- [ ] 37.1 Create `k8s/` directory
- [ ] 37.2 Add deployment manifest
- [ ] 37.3 Add service manifest
- [ ] 37.4 Add configmap for brain config
- [ ] 37.5 Add secrets for API keys
- [ ] 37.6 Add horizontal pod autoscaler

## Success Criteria

- All Phase 1 (Quick Wins) tasks completed and tested
- Test coverage > 80% for core modules
- All print statements replaced with structured logging
- Type hints added to all public APIs
- API endpoints have input validation
- Database operations are async
- No memory leaks in 24-hour stress test
- Documentation complete and up-to-date
- CI/CD pipeline passing all checks
