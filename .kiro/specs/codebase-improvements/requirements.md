<!-- compressed from requirements.md by spec-compress — do not edit manually -->

## Async Database Operations
Story: Convert Hippocampus memory to async DB ops for non-blocking I/O
ABBREVS: ctx=context, conn=connection, pool=connection pool
AC:
- Spike memory access → uses `aiosqlite` + non-blocking I/O
- Pool config provided → min/max sizes respected
- System shutdown → all conns closed within 10s
- DB query in async context → event loop unblocked [(no blocking I/O)]

## Structured Logging
Story: Replace print() with JSON-structured logs for production observability
ABBREVS: PII=personally identifiable info, env=environment variable
AC:
- Log written → JSON format in prod, console-readable in dev
- Any log entry → includes timestamp, level, component, context
- Log level → configurable via env variable
- Sensitive data (API keys, secrets, PII) → never logged [(sanitize before logging)]

## Type Safety
Story: Add complete type hints and enable mypy strict mode for IDE support + early error detection
AC:
- Public API method defined → has full type hints (params + return)
- Core modules checked → `mypy --strict` passes
- Generic types used → properly parameterized (List[T] not List)
- Optional fields → explicitly marked as Optional[T]

## Resource Management
Story: Ensure clean shutdown with proper resource cleanup to prevent leaks
AC:
- SIGTERM/SIGINT received → DB conns closed, sensors released, tasks cancelled within 10s
- 24-hour runtime → zero resource leaks detected
- Background tasks → cancelled before exit
- Hardware sensors → released on shutdown

## Input Validation
Story: Validate all API inputs with Pydantic to prevent injection + DoS attacks
ABBREVS: req=request, err=error
AC:
- Malformed req received → HTTP 400 + descriptive err msg
- Spike description >10KB → rejected
- File path provided → validated against directory traversal [(block ../ sequences)]
- Metric name → validated for allowed characters [a-zA-Z0-9_.]

## Embedding Model Optimization
Story: Load embedding model once, share across components, reduce memory 50%
AC:
- First embedding request → model loaded lazily, cached in memory
- Subsequent requests → reuse shared instance (no reload)
- Memory footprint → reduced by 50% vs. current baseline
- Startup time → unaffected by model load

## Configuration Validation
Story: Validate Brain config on load with Pydantic to catch errors early
AC:
- Invalid config file → rejected at startup with clear error message
- Missing required fields → caught immediately [(fail-fast)]
- Type mismatch in config → caught early, not at runtime
- Valid config → system starts normally

## Provider Resilience
Story: Add circuit breaker + exponential backoff to survive provider outages
ABBREVS: CB=circuit breaker
AC:
- Single provider fails → CB opens, system degrades gracefully (fallback to cache/mock)
- Failed provider → retried with exponential backoff (2s, 4s, 8s...)
- Provider recovers → CB closes, traffic flows again
- CB state + health → observable via metrics + health endpoint

## Provider Discovery Caching
Story: Cache provider discovery results to reduce startup from 80+ sec to <5s
ABBREVS: TTL=time-to-live
AC:
- First startup → discover + cache providers
- Subsequent startups → use cached discovery, startup <5s
- Manual rediscovery triggered → cache invalidated + fresh discovery
- Cache TTL → configurable (default 24 hours)

## Sensor Optimization
Story: Parallelize sensor monitoring + adapt polling rate to reduce CPU 30%
AC:
- Sensors monitored → parallel via `asyncio.gather()` (not sequential)
- Event-driven sensors → no polling, respond immediately to events
- Polling rate → adapts based on spike frequency (reduce when quiet)
- Failed sensor → auto-disabled, doesn't block others
- Sensor health → monitored + reported in metrics

## Event Bus Memory Management
Story: Auto-cleanup old events to keep memory bounded in long-running instances
ABBREVS: TTL=time-to-live, cleanup=purge old events
AC:
- Events older than retention TTL → auto-purged every 5 minutes
- Retention period → configurable (default 1 hour)
- Memory usage → stable over 24+ hour runtime (no growth)
- Event history size → bounded to configured limits

## Basal Ganglia Optimization
Story: Batch habit writes + use async I/O + write-behind cache to reduce disk I/O 90%
ABBREVS: flush=write to disk, cache=write-behind buffer
AC:
- Habit writes → batched together, flushed periodically (default 30s)
- Persistence → uses async I/O (non-blocking)
- Flush interval → configurable
- Clean shutdown → cache flushed, no data loss [(guarantee durability)]

## MCP Tool Parallelization
Story: Execute independent MCP tools in parallel to halve cascade latency
AC:
- Multiple MCP tools → analyzed for dependencies, independent ones run in parallel
- Tool timeout → 30s default, prevents hanging operations
- Tool failure → isolated, one tool failure doesn't break cascade
- Parallel execution → reduces latency by 50% vs. sequential

## Testing Coverage
Story: Add unit, integration, property-based tests to achieve >80% coverage with mocks
ABBREVS: cov=coverage, CI=continuous integration
AC:
- Core modules → >80% cov (unit tests)
- Full cascade flows → covered by integration tests
- Invariants → verified via property-based tests (hypothesis)
- Mock providers → enable testing without API costs
- Test suite → runs in <5 min, passes in CI/CD

## Rate Limiting
Story: Add configurable per-endpoint rate limits to prevent API abuse + budget overruns
ABBREVS: req=request, resp=response
AC:
- Excessive reqs → rejected with HTTP 429
- Resp headers → include rate limit info (remaining, reset time)
- Rate limits → configurable per endpoint
- Rate limit state → shared across instances [(use shared store)]

## Input Sanitization
Story: Sanitize all user input to prevent injection, DoS, path traversal, XSS
ABBREVS: sec=security
AC:
- User input → length limits enforced
- File paths → validated (no directory traversal)
- SQL queries → parameterized (no SQL injection)
- Web dashboard → XSS prevention (escape HTML)
- Sec scan → zero injection vulnerabilities

## Secrets Management
Story: Validate API keys at startup + support rotation + audit log usage
ABBREVS: key=API key, rot=rotation, audit=audit log
AC:
- Invalid key provided → detected at startup, system fails with clear error
- Key rotation → supported without restart (reload on interval)
- Key usage → audit logged with timestamp + request context
- Sensitive data at rest → encrypted [(AES-256 or equivalent)]
- Secrets in logs → never appear [(strip before logging)]

## Health Checks
Story: Add readiness/liveness probes for Kubernetes + detailed component health
AC:
- Readiness probe → verifies system ready (DB connected, config valid)
- Liveness probe → detects deadlocks + hangs
- Health checks → complete in <1s (don't block)
- Unhealthy components → identified explicitly (which component, why)
- Kubernetes integration → probes work with kubelet checks

## Distributed Tracing
Story: Trace all cascade flows with cost + latency attribution for debugging
ABBREVS: span=trace span, sample=sampling rate
AC:
- Cascade flow → fully traced from spike entry to result
- Each span → includes cost (USD), latency (ms), provider, layer
- Tracing overhead → <5% performance impact
- Traces → exportable to standard backends (Jaeger, Datadog, etc.)
- Sample rate → configurable for high-volume systems

## Metrics Collection
Story: Expose Prometheus metrics with Grafana dashboard for real-time monitoring
ABBREVS: scrape=collect metrics, label=metric tag
AC:
- Prometheus endpoint → exposed with metrics
- Key metrics → spikes/min, latency (p50/p95/p99), cost/spike, decisions/layer
- Metrics labeled → by sense type, layer, provider (enable filtering)
- Grafana dashboard → visualizes key metrics in real-time
- Scrape interval → 15s (configurable)

## Error Tracking
Story: Track errors in Sentry with cascade context + breadcrumbs for faster debugging
