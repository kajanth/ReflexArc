# MCP Tool Configuration

## Overview

The NSA ReflexArc system supports external tool integration via the Model Context Protocol (MCP). This document explains how to configure MCP tool execution, including timeout handling and error management.

## MCP Tool Timeout

### What is it?

The `mcp_tool_timeout` setting controls how long the system will wait for an MCP tool to complete execution before timing out. This prevents hanging operations from blocking the neural cascade.

### Configuration

Add the timeout setting to your brain configuration file:

```yaml
brain:
  name: "Your Brain"
  mcp_tool_timeout: 30.0  # seconds (default: 30.0)
```

**Valid Range**: 1.0 to 300.0 seconds (enforced by schema validation)

### Default Behavior

- **Default timeout**: 30 seconds
- **Timeout action**: Tool execution is cancelled, error is logged, cascade continues
- **Error handling**: Timeout errors are isolated - other tools continue executing

### How It Works

1. When the Cortex (Layer 4) decides to use MCP tools, it extracts tool calls from the AI response
2. Each tool is executed with `asyncio.wait_for()` using the configured timeout
3. If a tool exceeds the timeout:
   - `asyncio.TimeoutError` is caught
   - Error message is logged with structured logging
   - Empty result is returned with error description
   - Other tools continue executing (error isolation)

### Example Configurations

#### Fast Tools (API calls, simple queries)
```yaml
brain:
  mcp_tool_timeout: 10.0  # 10 seconds for quick operations
```

#### Standard Tools (database queries, file operations)
```yaml
brain:
  mcp_tool_timeout: 30.0  # 30 seconds (default)
```

#### Long-Running Tools (data processing, external services)
```yaml
brain:
  mcp_tool_timeout: 120.0  # 2 minutes for complex operations
```

## Parallel Tool Execution

MCP tools are executed in parallel using `asyncio.gather()` for optimal performance:

- **Independent tools**: Execute simultaneously
- **Timeout per tool**: Each tool has its own timeout
- **Error isolation**: One tool failure doesn't affect others
- **Result aggregation**: All results (success or error) are collected

## Monitoring and Logging

Tool execution is logged with structured logging:

```json
{
  "event": "mcp_tool_start",
  "tool": "search_database",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

On timeout:
```json
{
  "event": "mcp_tool_timeout",
  "tool": "search_database",
  "timeout": 30.0,
  "level": "error",
  "timestamp": "2024-01-15T10:30:30Z"
}
```

On success:
```json
{
  "event": "mcp_tool_success",
  "tool": "search_database",
  "result_length": 1024,
  "timestamp": "2024-01-15T10:30:15Z"
}
```

## Best Practices

### Choosing the Right Timeout

1. **Profile your tools**: Measure typical execution times
2. **Add buffer**: Set timeout to 2-3x typical execution time
3. **Consider network**: Account for network latency if tools call external services
4. **Balance responsiveness**: Shorter timeouts = faster failure detection, but may cause false timeouts

### Handling Timeouts

When tools timeout frequently:

1. **Investigate root cause**: Check tool implementation, network, external services
2. **Increase timeout**: If tools legitimately need more time
3. **Optimize tools**: Improve tool performance if possible
4. **Add retries**: Implement retry logic in tool code for transient failures

### Production Recommendations

- **Development**: 60-120 seconds (generous for debugging)
- **Production**: 30 seconds (balance between responsiveness and reliability)
- **Critical systems**: 10-15 seconds (fail fast, retry quickly)

## Schema Validation

The timeout value is validated by Pydantic schema:

```python
mcp_tool_timeout: float = Field(
    30.0, 
    ge=1.0,      # Minimum: 1 second
    le=300.0,    # Maximum: 5 minutes
    description="Timeout for MCP tool execution in seconds"
)
```

Invalid values will cause startup failure with a clear error message.

## Implementation Details

### Code Location

- **Configuration**: `config/schema.py` - `BrainConfigSchema.mcp_tool_timeout`
- **Loading**: `plugin_loader.py` - `BrainConfig.mcp_tool_timeout` property
- **Initialization**: `main.py` - Passed to `NSAOrchestrator.__init__()`
- **Execution**: `brain_core.py` - `NSAOrchestrator.process_spike()` MCP tool section

### Timeout Implementation

```python
try:
    result_text = await asyncio.wait_for(
        self.mcp_manager.execute_tool(tool_name, args),
        timeout=self.mcp_tool_timeout
    )
    logger.info("mcp_tool_success", tool=tool_name, result_length=len(result_text))
    return (tc, result_text, None)
except asyncio.TimeoutError:
    error_msg = f"Tool execution timed out after {self.mcp_tool_timeout} seconds"
    logger.error("mcp_tool_timeout", tool=tool_name, timeout=self.mcp_tool_timeout)
    return (tc, "", error_msg)
```

## Related Configuration

### MCP Server Configuration

Define MCP servers in your brain config:

```yaml
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    env:
      NODE_ENV: "production"
```

### Database Connection Pooling

MCP tools may interact with the database. Configure pooling:

```yaml
brain:
  database:
    path: "memory/long_term_memory.db"
    min_pool_size: 1
    max_pool_size: 5
```

See `docs/CONNECTION_POOLING.md` for details.

## Troubleshooting

### Problem: Tools timing out frequently

**Solutions**:
1. Check tool logs for performance issues
2. Increase `mcp_tool_timeout` value
3. Verify network connectivity to external services
4. Profile tool execution time

### Problem: System feels sluggish

**Solutions**:
1. Decrease `mcp_tool_timeout` for faster failure detection
2. Optimize slow tools
3. Consider removing unnecessary tools from responses

### Problem: Timeout validation error on startup

**Error**: `mcp_tool_timeout must be between 1.0 and 300.0`

**Solution**: Check your config file and ensure the value is within valid range:
```yaml
brain:
  mcp_tool_timeout: 30.0  # Must be 1.0 <= value <= 300.0
```

## See Also

- `config/brain.yaml` - Example configuration
- `config/schema.py` - Configuration schema validation
- `docs/CONNECTION_POOLING.md` - Database connection management
- `docs/EMBEDDING_MODEL_CONFIGURATION.md` - Embedding model setup
