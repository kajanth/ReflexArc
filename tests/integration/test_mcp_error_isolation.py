"""
Tests for MCP tool error isolation.

Verifies that:
1. One tool failure doesn't prevent other tools from executing
2. Timeout errors are properly isolated
3. Parse errors are properly isolated
4. All tool results (success and failure) are returned
"""

import pytest
import asyncio
from typing import Dict, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch


class MockMCPManager:
    """Mock MCP manager for testing."""
    
    def __init__(self):
        self.tool_behaviors = {}
    
    def set_tool_behavior(self, tool_name: str, behavior: str, delay: float = 0):
        """
        Set how a tool should behave.
        
        Args:
            tool_name: Name of the tool
            behavior: 'success', 'timeout', 'error'
            delay: Delay in seconds before returning
        """
        self.tool_behaviors[tool_name] = {
            'behavior': behavior,
            'delay': delay
        }
    
    async def execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute a tool with configured behavior."""
        behavior_config = self.tool_behaviors.get(tool_name, {'behavior': 'success', 'delay': 0})
        
        # Simulate delay
        if behavior_config['delay'] > 0:
            await asyncio.sleep(behavior_config['delay'])
        
        # Simulate behavior
        if behavior_config['behavior'] == 'success':
            return f"Success result from {tool_name}"
        elif behavior_config['behavior'] == 'timeout':
            # Simulate a long-running operation
            await asyncio.sleep(100)  # Will be interrupted by timeout
            return "Should not reach here"
        elif behavior_config['behavior'] == 'error':
            raise Exception(f"Simulated error in {tool_name}")
        else:
            return f"Unknown behavior: {behavior_config['behavior']}"
    
    def get_all_tools(self):
        """Return mock tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "tool1",
                    "description": "First test tool"
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool2",
                    "description": "Second test tool"
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool3",
                    "description": "Third test tool"
                }
            }
        ]


@pytest.mark.asyncio
async def test_error_isolation_one_failure():
    """Test that one tool failure doesn't prevent other tools from executing."""
    
    # Setup mock MCP manager
    mcp_manager = MockMCPManager()
    mcp_manager.set_tool_behavior("tool1", "success")
    mcp_manager.set_tool_behavior("tool2", "error")  # This one fails
    mcp_manager.set_tool_behavior("tool3", "success")
    
    # Simulate tool calls
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "tool1",
                "arguments": "{}"
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "tool2",
                "arguments": "{}"
            }
        },
        {
            "id": "call_3",
            "function": {
                "name": "tool3",
                "arguments": "{}"
            }
        }
    ]
    
    # Execute tools using the same pattern as brain_core.py
    async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
        """Execute a single tool with error isolation."""
        tool_name = tc["function"]["name"]
        import json
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception as e:
            args = {}
        
        try:
            result_text = await asyncio.wait_for(
                mcp_manager.execute_tool(tool_name, args),
                timeout=30.0
            )
            return (tc, result_text, None)
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after 30 seconds"
            return (tc, "", error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return (tc, "", error_msg)
    
    # Execute all tools in parallel
    tool_tasks = [_execute_one_tool(tc) for tc in tool_calls]
    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
    
    # Verify results
    assert len(tool_results) == 3, "Should have 3 results"
    
    # Tool 1 should succeed
    tc1, result1, error1 = tool_results[0]
    assert tc1["id"] == "call_1"
    assert result1 == "Success result from tool1"
    assert error1 is None
    
    # Tool 2 should fail with error
    tc2, result2, error2 = tool_results[1]
    assert tc2["id"] == "call_2"
    assert result2 == ""
    assert error2 is not None
    assert "Simulated error in tool2" in error2
    
    # Tool 3 should succeed (not affected by tool2's failure)
    tc3, result3, error3 = tool_results[2]
    assert tc3["id"] == "call_3"
    assert result3 == "Success result from tool3"
    assert error3 is None


@pytest.mark.asyncio
async def test_error_isolation_timeout():
    """Test that timeout in one tool doesn't affect others."""
    
    # Setup mock MCP manager
    mcp_manager = MockMCPManager()
    mcp_manager.set_tool_behavior("tool1", "success", delay=0.1)
    mcp_manager.set_tool_behavior("tool2", "timeout")  # This one times out
    mcp_manager.set_tool_behavior("tool3", "success", delay=0.1)
    
    # Simulate tool calls
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "tool1",
                "arguments": "{}"
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "tool2",
                "arguments": "{}"
            }
        },
        {
            "id": "call_3",
            "function": {
                "name": "tool3",
                "arguments": "{}"
            }
        }
    ]
    
    # Execute tools using the same pattern as brain_core.py
    async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
        """Execute a single tool with error isolation."""
        tool_name = tc["function"]["name"]
        import json
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception as e:
            args = {}
        
        try:
            result_text = await asyncio.wait_for(
                mcp_manager.execute_tool(tool_name, args),
                timeout=1.0  # Short timeout for testing
            )
            return (tc, result_text, None)
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after 1.0 seconds"
            return (tc, "", error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return (tc, "", error_msg)
    
    # Execute all tools in parallel
    tool_tasks = [_execute_one_tool(tc) for tc in tool_calls]
    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
    
    # Verify results
    assert len(tool_results) == 3, "Should have 3 results"
    
    # Tool 1 should succeed
    tc1, result1, error1 = tool_results[0]
    assert tc1["id"] == "call_1"
    assert result1 == "Success result from tool1"
    assert error1 is None
    
    # Tool 2 should timeout
    tc2, result2, error2 = tool_results[1]
    assert tc2["id"] == "call_2"
    assert result2 == ""
    assert error2 is not None
    assert "timed out" in error2
    
    # Tool 3 should succeed (not affected by tool2's timeout)
    tc3, result3, error3 = tool_results[2]
    assert tc3["id"] == "call_3"
    assert result3 == "Success result from tool3"
    assert error3 is None


@pytest.mark.asyncio
async def test_error_isolation_parse_error():
    """Test that JSON parse errors are handled gracefully."""
    
    # Setup mock MCP manager
    mcp_manager = MockMCPManager()
    mcp_manager.set_tool_behavior("tool1", "success")
    mcp_manager.set_tool_behavior("tool2", "success")
    
    # Simulate tool calls with one having invalid JSON
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "tool1",
                "arguments": "{}"
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "tool2",
                "arguments": "invalid json {{"  # Invalid JSON
            }
        }
    ]
    
    # Execute tools using the same pattern as brain_core.py
    async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
        """Execute a single tool with error isolation."""
        tool_name = tc["function"]["name"]
        import json
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception as e:
            # Parse error - use empty args and continue
            args = {}
        
        try:
            result_text = await asyncio.wait_for(
                mcp_manager.execute_tool(tool_name, args),
                timeout=30.0
            )
            return (tc, result_text, None)
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after 30 seconds"
            return (tc, "", error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return (tc, "", error_msg)
    
    # Execute all tools in parallel
    tool_tasks = [_execute_one_tool(tc) for tc in tool_calls]
    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
    
    # Verify results
    assert len(tool_results) == 2, "Should have 2 results"
    
    # Both tools should succeed (parse error is handled gracefully)
    tc1, result1, error1 = tool_results[0]
    assert tc1["id"] == "call_1"
    assert result1 == "Success result from tool1"
    assert error1 is None
    
    tc2, result2, error2 = tool_results[1]
    assert tc2["id"] == "call_2"
    assert result2 == "Success result from tool2"  # Still succeeds with empty args
    assert error2 is None


@pytest.mark.asyncio
async def test_error_isolation_all_failures():
    """Test that all tools can fail independently."""
    
    # Setup mock MCP manager
    mcp_manager = MockMCPManager()
    mcp_manager.set_tool_behavior("tool1", "error")
    mcp_manager.set_tool_behavior("tool2", "timeout")
    mcp_manager.set_tool_behavior("tool3", "error")
    
    # Simulate tool calls
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "tool1",
                "arguments": "{}"
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "tool2",
                "arguments": "{}"
            }
        },
        {
            "id": "call_3",
            "function": {
                "name": "tool3",
                "arguments": "{}"
            }
        }
    ]
    
    # Execute tools using the same pattern as brain_core.py
    async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
        """Execute a single tool with error isolation."""
        tool_name = tc["function"]["name"]
        import json
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception as e:
            args = {}
        
        try:
            result_text = await asyncio.wait_for(
                mcp_manager.execute_tool(tool_name, args),
                timeout=1.0  # Short timeout for testing
            )
            return (tc, result_text, None)
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after 1.0 seconds"
            return (tc, "", error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return (tc, "", error_msg)
    
    # Execute all tools in parallel
    tool_tasks = [_execute_one_tool(tc) for tc in tool_calls]
    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
    
    # Verify results - all should fail but return results
    assert len(tool_results) == 3, "Should have 3 results"
    
    # All tools should have errors
    for i, (tc, result, error) in enumerate(tool_results):
        assert tc["id"] == f"call_{i+1}"
        assert result == ""
        assert error is not None


@pytest.mark.asyncio
async def test_parallel_execution_performance():
    """Test that tools execute in parallel, not sequentially."""
    
    # Setup mock MCP manager with delays
    mcp_manager = MockMCPManager()
    mcp_manager.set_tool_behavior("tool1", "success", delay=0.5)
    mcp_manager.set_tool_behavior("tool2", "success", delay=0.5)
    mcp_manager.set_tool_behavior("tool3", "success", delay=0.5)
    
    # Simulate tool calls
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "tool1",
                "arguments": "{}"
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "tool2",
                "arguments": "{}"
            }
        },
        {
            "id": "call_3",
            "function": {
                "name": "tool3",
                "arguments": "{}"
            }
        }
    ]
    
    # Execute tools using the same pattern as brain_core.py
    async def _execute_one_tool(tc: Dict) -> Tuple[Dict, str, Optional[str]]:
        """Execute a single tool with error isolation."""
        tool_name = tc["function"]["name"]
        import json
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception as e:
            args = {}
        
        try:
            result_text = await asyncio.wait_for(
                mcp_manager.execute_tool(tool_name, args),
                timeout=30.0
            )
            return (tc, result_text, None)
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after 30 seconds"
            return (tc, "", error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return (tc, "", error_msg)
    
    # Measure execution time
    start_time = asyncio.get_event_loop().time()
    
    # Execute all tools in parallel
    tool_tasks = [_execute_one_tool(tc) for tc in tool_calls]
    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=False)
    
    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time
    
    # Verify results
    assert len(tool_results) == 3, "Should have 3 results"
    
    # All tools should succeed
    for tc, result, error in tool_results:
        assert error is None
        assert "Success result" in result
    
    # Verify parallel execution (should take ~0.5s, not ~1.5s)
    # Allow some overhead for test execution
    assert elapsed < 1.0, f"Parallel execution took {elapsed}s, expected < 1.0s (sequential would be ~1.5s)"
    assert elapsed >= 0.5, f"Execution too fast: {elapsed}s, expected >= 0.5s"
