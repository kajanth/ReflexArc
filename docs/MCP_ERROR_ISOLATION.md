# MCP Tool Error Isolation

## Overview

The NSA ReflexArc system implements comprehensive error isolation for MCP (Model Context Protocol) tool execution. This ensures that failures in individual tools do not prevent other tools from executing or cause cascading failures in the neural cascade.

## Architecture

### Location

MCP tool execution occurs in the **Cortex layer (Layer 4)** of the neural cascade, specifically in the `process_spike()` method of the `NSAOrchestrator` class in `brain_core.py`.

### Execution Flow

```
1. Cortex decides to use tools
2. Tools execute in parallel (asyncio.gather)
3. Each tool wrapped in error isolation
4. Results collected (success or error)
5. All results passed to second Cortex pass
6. Final response synthesized
```

## Error Isolation Mechanisms

### 1. Per-Tool Try/Except Wrapping

Each tool execution is wrapped in its own try/except block:

```python
async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
    """Execute a single tool with error isolation."""
    tool_name = tc["function"]["name"]
    
    # Parse arguments with error handling
    try:
        args = json.loads(tc["function"]["arguments"])
    except Exception as e:
        logger.warning("tool_args_parse_failed", tool=tool_name, error=str(e))
        args = {}  # Continue with empty args
    
    # Execute tool with error handling
    try:
        result_text = await asyncio.wait_for(
            self.mcp_manager.execute_tool(tool_name, args),
            timeout=self.mcp_tool_timeout
        )
        return (tc, result_text, None)
    except asyncio.TimeoutError:
        error_msg = f"Tool execution timed out after {self.mcp_tool_timeout} seconds"
        logger.error("mcp_tool_timeout", tool=tool_name, timeout=self.mcp_tool_timeout)
        return (tc, "", error_msg)
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error("mcp_tool_failed", tool=tool_name, error=str(e))
        return (tc, "", error_msg)
```

### 2. Parallel Execution with asyncio.gather

Tools execute in parallel using `asyncio.gather()` with `return_exceptions=False`:

```python
# Execute all tools in parallel
tool_tasks = [_execute_one_tool(tc) for tc in cortex_res.tool_calls]
tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
```

**Key Point**: `return_exceptions=False` is safe here because exceptions are caught inside `_execute_one_tool()` and returned as error tuples rather than raised.

### 3. Timeout Isolation

Each tool has its own timeout using `asyncio.wait_for()`:

```python
result_text = await asyncio.wait_for(
    self.mcp_manager.execute_tool(tool_name, args),
    timeout=self.mcp_tool_timeout  # Default: 30 seconds
)
```

**Benefits**:
- One slow tool doesn't block others
- Timeout is per-tool, not global
- Timeout errors are caught and returned as error messages

### 4. Error Message Propagation

Errors are returned as structured tuples, not raised as exceptions:

```python
# Return type: Tuple[Dict, str, Optional[str]]
# (tool_call, result_text, error_message)

# Success case
return (tc, result_text, None)

# Error case
return (tc, "", error_msg)
```

This allows the AI model to see which tools failed and why, enabling intelligent fallback strategies.

## Error Types Handled

### 1. Argument Parse Errors

**Cause**: Invalid JSON in tool arguments

**Handling**: 
- Log warning
- Continue with empty arguments `{}`
- Tool still executes

**Example**:
```python
# Invalid JSON: "invalid json {{"
# Result: args = {}, tool executes with empty args
```

### 2. Execution Errors

**Cause**: Exception during tool execution (network error, invalid input, etc.)

**Handling**:
- Log error with details
- Return error message to AI model
- Other tools continue executing

**Example**:
```python
# Tool raises: Exception("Database connection failed")
# Result: ("", "Tool execution failed: Database connection failed")
```

### 3. Timeout Errors

**Cause**: Tool execution exceeds timeout (default 30s)

**Handling**:
- Cancel tool execution
- Log timeout event
- Return timeout error message
- Other tools continue executing

**Example**:
```python
# Tool takes > 30 seconds
# Result: ("", "Tool execution timed out after 30 seconds")
```

## Benefits

### 1. Resilience

- **One tool failure doesn't break the cascade**: Other tools continue executing
- **Partial results are useful**: AI model can work with available information
- **Graceful degradation**: System continues functioning with reduced capabilities

### 2. Observability

- **Structured logging**: All errors logged with context
- **Error attribution**: Know exactly which tool failed and why
- **Performance tracking**: Timeout and latency per tool

### 3. Performance

- **Parallel execution**: 50-70% latency reduction for multi-tool scenarios
- **Timeout isolation**: One slow tool doesn't block others
- **Resource efficiency**: Concurrent I/O operations

### 4. AI Model Intelligence

- **Error context**: AI model sees which tools failed
- **Fallback strategies**: Can suggest alternatives or retry
- **Partial synthesis**: Can work with available tool results

## Configuration

### Timeout Configuration

The tool timeout is configurable via the brain config:

```yaml
brain:
  mcp_tool_timeout: 30  # seconds (default: 30)
```

**Recommendations**:
- **Fast tools** (API calls): 10-15 seconds
- **Medium tools** (database queries): 30 seconds (default)
- **Slow tools** (file processing): 60-120 seconds

### Logging Configuration

Error isolation events are logged at different levels:

- `DEBUG`: Tool start events
- `INFO`: Tool success events
- `WARNING`: Argument parse failures
- `ERROR`: Tool execution failures and timeouts

## Testing

Comprehensive tests verify error isolation behavior:

### Test Coverage

1. **One tool failure**: Verify other tools continue
2. **Timeout isolation**: Verify timeout doesn't affect other tools
3. **Parse error handling**: Verify graceful handling of invalid JSON
4. **All failures**: Verify system handles complete failure
5. **Parallel performance**: Verify tools execute concurrently

### Running Tests

```bash
# Run error isolation tests
python -m pytest tests/test_mcp_error_isolation.py -v

# Run with coverage
python -m pytest tests/test_mcp_error_isolation.py --cov=brain_core --cov-report=term-missing
```

## Performance Characteristics

### Latency Comparison

**Scenario**: 3 tools, each taking 5 seconds

- **Sequential**: 15 seconds total
- **Parallel with error isolation**: 5 seconds total (limited by slowest tool)

**Scenario**: 5 tools with varying latencies (2s, 5s, 3s, 8s, 4s)

- **Sequential**: 22 seconds total
- **Parallel with error isolation**: 8 seconds total (limited by slowest tool)

### Error Scenarios

**Scenario**: 3 tools, one fails immediately

- **Without isolation**: Entire cascade fails
- **With isolation**: 2 tools succeed, 1 fails gracefully, cascade continues

**Scenario**: 3 tools, one times out after 30s

- **Without isolation**: All tools blocked for 30s, then cascade fails
- **With isolation**: 2 tools complete quickly, 1 times out independently, cascade continues

## Best Practices

### 1. Tool Design

- **Idempotent**: Tools should be safe to retry
- **Fast failure**: Fail quickly if preconditions not met
- **Descriptive errors**: Return helpful error messages
- **Timeout aware**: Design for 30-second timeout

### 2. Error Handling

- **Log context**: Include tool name, arguments, error details
- **Structured errors**: Use consistent error message format
- **Actionable messages**: Help AI model understand what went wrong

### 3. Monitoring

- **Track failure rates**: Monitor which tools fail most often
- **Track timeout rates**: Identify slow tools
- **Track parallel efficiency**: Measure latency improvements

## Future Enhancements

### Potential Improvements

1. **Configurable timeout per tool**: Different tools may need different timeouts
2. **Retry logic**: Automatic retry for transient failures
3. **Circuit breaker**: Disable frequently failing tools
4. **Metrics collection**: Prometheus metrics for tool execution
5. **Dependency analysis**: Detect and respect tool dependencies

### Backward Compatibility

All enhancements will maintain backward compatibility with existing MCP tool implementations.

## Related Documentation

- [MCP Tool Configuration](MCP_TOOL_CONFIGURATION.md) - Tool timeout and configuration
- [Connection Pooling](CONNECTION_POOLING.md) - Database connection management
- [Adaptive Polling](ADAPTIVE_POLLING.md) - Sensor optimization

## References

- **Implementation**: `brain_core.py` lines 380-494
- **Tests**: `tests/test_mcp_error_isolation.py`
- **Analysis**: `TASK_13.1_MCP_TOOL_DEPENDENCY_ANALYSIS.md`
