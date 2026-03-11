# Connection Pooling Configuration

## Overview

The Hippocampus memory system now supports connection pooling for efficient async database operations. Connection pooling helps manage database connections efficiently by reusing connections instead of creating new ones for each operation.

## Benefits

- **Performance**: Reduces overhead of creating/closing connections
- **Resource Management**: Limits maximum concurrent connections
- **Scalability**: Handles concurrent operations efficiently
- **Reliability**: Prevents connection exhaustion

## Configuration

### In Brain Configuration File

Add the `database` section under `brain` in your configuration file (`config/brain.yaml` or `config/brain.json`):

#### YAML Format

```yaml
brain:
  name: "DevOps Brain"
  description: "Infrastructure monitoring and autonomous incident response"
  heartbeat_interval: 30
  prediction_interval: 120
  goal_eval_interval: 300
  
  # Database connection pooling configuration
  database:
    path: "memory/long_term_memory.db"  # SQLite database file path
    min_pool_size: 1                     # Minimum connections to maintain
    max_pool_size: 5                     # Maximum connections allowed
```

#### JSON Format

```json
{
  "brain": {
    "name": "DevOps Brain",
    "description": "Infrastructure monitoring and autonomous incident response",
    "heartbeat_interval": 30,
    "prediction_interval": 120,
    "goal_eval_interval": 300,
    "database": {
      "path": "memory/long_term_memory.db",
      "min_pool_size": 1,
      "max_pool_size": 5
    }
  }
}
```

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `path` | string | `"memory/long_term_memory.db"` | - | Path to SQLite database file |
| `min_pool_size` | integer | `1` | 1-10 | Minimum number of connections to maintain in the pool |
| `max_pool_size` | integer | `5` | 1-20 | Maximum number of connections allowed in the pool |

### Validation Rules

- `min_pool_size` must be between 1 and 10
- `max_pool_size` must be between 1 and 20
- `min_pool_size` must be less than or equal to `max_pool_size`

If these rules are violated, the system will fail at startup with a clear error message.

## How It Works

### Connection Pool Lifecycle

1. **Initialization**: When Hippocampus starts, it creates `min_pool_size` connections
2. **Acquisition**: When an operation needs a connection:
   - If available connections exist in the pool, one is reused
   - If pool is empty but under `max_pool_size`, a new connection is created
   - If pool is exhausted (at `max_pool_size`), the operation waits for a connection to be released
3. **Release**: After an operation completes, the connection is returned to the pool
4. **Cleanup**: Excess connections (above `min_pool_size`) are closed when released
5. **Shutdown**: All connections are closed when Hippocampus is closed

### Pool Statistics

You can monitor pool health using the `get_pool_stats()` method:

```python
stats = hippocampus.get_pool_stats()
# Returns:
# {
#     "pool_size": 2,      # Available connections
#     "in_use": 3,         # Connections currently in use
#     "total": 5,          # Total connections (pool_size + in_use)
#     "min_size": 1,       # Configured minimum
#     "max_size": 5        # Configured maximum
# }
```

## Usage Examples

### Basic Usage (Default Configuration)

```python
from memory.hippocampus import Hippocampus

# Uses default pool sizes (min=1, max=5)
async with Hippocampus(db_path="memory/long_term_memory.db") as hippo:
    await hippo.store_memory("vision", "Detected motion in hallway")
    context = await hippo.retrieve_context("motion detection")
```

### Custom Pool Configuration

```python
from memory.hippocampus import Hippocampus

# Custom pool sizes for high-concurrency scenarios
async with Hippocampus(
    db_path="memory/long_term_memory.db",
    min_pool_size=2,
    max_pool_size=10
) as hippo:
    # Perform operations
    await hippo.store_memory("auditory", "Loud noise detected")
```

### Concurrent Operations

The connection pool automatically handles concurrent operations:

```python
import asyncio
from memory.hippocampus import Hippocampus

async with Hippocampus(db_path="memory/long_term_memory.db") as hippo:
    # Store multiple memories concurrently
    tasks = [
        hippo.store_memory("vision", f"Event {i}")
        for i in range(10)
    ]
    await asyncio.gather(*tasks)
    
    # All connections are automatically managed and released
```

## Tuning Guidelines

### Low Concurrency (Default)

For systems with low concurrent database operations:

```yaml
database:
  min_pool_size: 1
  max_pool_size: 5
```

### Medium Concurrency

For systems with moderate concurrent operations:

```yaml
database:
  min_pool_size: 2
  max_pool_size: 10
```

### High Concurrency

For systems with many concurrent database operations:

```yaml
database:
  min_pool_size: 5
  max_pool_size: 20
```

### Considerations

- **Memory**: Each connection consumes memory. Don't set `max_pool_size` too high.
- **SQLite Limitations**: SQLite has limited concurrent write support. For write-heavy workloads, consider other databases.
- **Startup Time**: Higher `min_pool_size` increases startup time slightly.
- **Resource Usage**: Monitor pool statistics to find optimal values for your workload.

## Monitoring

### Logging

The connection pool logs important events:

```
[info] connection_pool_initialized - Pool created with min/max sizes
[debug] connection_acquired_from_pool - Connection reused from pool
[debug] connection_created - New connection created
[warning] connection_pool_exhausted - All connections in use, waiting
[debug] connection_released_to_pool - Connection returned to pool
[debug] connection_closed - Excess connection closed
[info] connection_pool_closed - All connections closed
```

### Warning Signs

Watch for these warnings in logs:

- **Frequent "connection_pool_exhausted" warnings**: Increase `max_pool_size`
- **Many "connection_created" logs**: Consider increasing `min_pool_size`
- **High "in_use" count in stats**: May need larger pool or optimization

## Backward Compatibility

The connection pooling feature is fully backward compatible:

- If no `database` section is specified, defaults are used (min=1, max=5)
- Existing code works without modification
- The `db_path` parameter can still be passed directly to `Hippocampus()`

## Testing

### Manual Testing

Run the manual test script:

```bash
python3 test_pooling_manual.py
```

### Unit Tests

Run the unit tests (requires pytest):

```bash
pytest tests/test_hippocampus_pooling.py -v
```

### Configuration Validation

Test that your configuration is valid:

```bash
python3 test_config_loading.py
```

## Troubleshooting

### Issue: "connection_pool_exhausted" warnings

**Cause**: All connections are in use, operations are waiting.

**Solution**: Increase `max_pool_size` in configuration.

### Issue: High memory usage

**Cause**: Too many connections in the pool.

**Solution**: Reduce `max_pool_size` or `min_pool_size`.

### Issue: Slow startup

**Cause**: Creating many connections at startup.

**Solution**: Reduce `min_pool_size` (connections will be created on-demand).

### Issue: Configuration validation errors

**Cause**: Invalid pool size values.

**Solution**: Ensure `min_pool_size <= max_pool_size` and both are within valid ranges.

## Implementation Details

### Architecture

The connection pool is implemented in `memory/hippocampus.py`:

- `ConnectionPool` class: Manages the pool of aiosqlite connections
- `Hippocampus` class: Uses the connection pool for all database operations
- Async context managers: Ensure proper connection lifecycle management

### Thread Safety

The connection pool uses `asyncio.Lock` to ensure thread-safe operations:

- Connection acquisition is atomic
- Connection release is atomic
- Pool statistics are consistent

### Error Handling

- Connection errors are propagated to the caller
- Failed connections are not returned to the pool
- Pool cleanup is guaranteed even on errors (via async context manager)

## Future Enhancements

Potential improvements for future versions:

- Connection health checks
- Automatic pool size adjustment based on load
- Connection timeout configuration
- Pool metrics export (Prometheus)
- Support for connection pooling with other databases (PostgreSQL, MySQL)

## References

- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)
- [SQLite Concurrency](https://www.sqlite.org/lockingv3.html)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
