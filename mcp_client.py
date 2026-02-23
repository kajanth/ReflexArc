import asyncio
import json
import uuid
import os
import subprocess
from typing import Dict, Any, List, Optional

class MCPClient:
    """
    A lightweight, zero-dependency MCP (Model Context Protocol) client.
    Because environments might not have the official `mcp` SDK installed,
    this implements the core JSON-RPC 2.0 stdio protocol directly for tools.
    """
    
    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        
        self.process: Optional[asyncio.subprocess.Process] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        
        self.is_initialized = False
        self.tools: List[Dict[str, Any]] = []

    async def start(self):
        """Start the MCP server subprocess and initialize the protocol."""
        print(f"[MCPClient] Starting server '{self.name}': {self.command} {' '.join(self.args)}")
        
        # Merge environment variables
        env = os.environ.copy()
        env.update(self.env)
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                # Force unbuffered I/O if possible
                limit=1024 * 1024  # 1MB buffer
            )
        except Exception as e:
            print(f"[MCPClient] Failed to start {self.name}: {e}")
            raise
            
        # Start reading the stdout/stderr streams
        self._read_task = asyncio.create_task(self._read_loop())
        asyncio.create_task(self._stderr_loop())
        
        # 1. Initialize Request
        init_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", # MCP v1
                "clientInfo": {
                    "name": "ReflexArc Cortex",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        
        try:
            init_res = await self._send_request(init_req)
            
            # Send initialized notification
            await self._send_notification({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            })
            
            self.is_initialized = True
            
            # Fetch available tools
            await self.discover_tools()
            print(f"  ✓ {self.name} online ({len(self.tools)} tools discovered)")
            
        except Exception as e:
            print(f"[MCPClient] Initialization failed for {self.name}: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Terminate the server process."""
        if self._read_task:
            self._read_task.cancel()
            
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                
        print(f"[MCPClient] Stopped server '{self.name}'")

    async def _send_request(self, body: dict) -> dict:
        """Send a JSON-RPC request and await the response."""
        req_id = body.get("id")
        if req_id is None:
            req_id = str(uuid.uuid4())
            body["id"] = req_id
            
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future
        
        await self._send_raw(body)
        
        try:
            # Wait up to 30 seconds for a tool to execute
            response = await asyncio.wait_for(future, timeout=30.0)
            if "error" in response:
                raise Exception(response["error"].get("message", "Unknown RPC error"))
            return response.get("result", {})
        except Exception as e:
            self._pending_requests.pop(req_id, None)
            raise e

    async def _send_notification(self, body: dict):
        """Send a fire-and-forget notification."""
        await self._send_raw(body)

    async def _send_raw(self, body: dict):
        """Write a framed message to stdin."""
        if not self.process or not self.process.stdin:
            raise Exception("Process not running")
            
        payload = json.dumps(body) + "\n"
        self.process.stdin.write(payload.encode("utf-8"))
        await self.process.stdin.drain()

    async def _read_loop(self):
        """Read stdout, parsing JSON-RPC messages (JSON Lines format for stdio transport)."""
        buffer = ""
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                    
                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue
                    
                # The official MCP stdio transport requires JSON-RPC messages to be
                # newline delimited.
                try:
                    msg = json.loads(line_str)
                    self._handle_message(msg)
                except json.JSONDecodeError:
                    print(f"[MCPClient] {self.name} raw output: {line_str}")
                
            except Exception as e:
                print(f"[MCPClient] Read error: {e}")
                break

    async def _stderr_loop(self):
        """Log stderr from the server."""
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    break
                print(f"[{self.name} STDERR] {line.decode('utf-8').strip()}")
            except Exception:
                break

    def _handle_message(self, msg: dict):
        """Route incoming messages to waiting futures."""
        if "id" in msg:
            req_id = str(msg["id"])
            if req_id in self._pending_requests:
                future = self._pending_requests.pop(req_id)
                if not future.done():
                    future.set_result(msg)
        elif "method" in msg:
            # Handle unsolicited notifications if needed (e.g. logging)
            method = msg["method"]
            if method == "notifications/message":
                print(f"[{self.name} NOTIFY] {msg.get('params', {}).get('message')}")

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Query the server for available tools."""
        req = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {}
        }
        res = await self._send_request(req)
        self.tools = res.get("tools", [])
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool on the MCP server."""
        print(f"[MCPClient] Calling {self.name}.{tool_name} with {json.dumps(arguments)}")
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        res = await self._send_request(req)
        
        # MCP tools return an array of content blocks (text or image)
        content_blocks = res.get("content", [])
        text_parts = []
        
        is_error = res.get("isError", False)
        
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
                
        output = "\n".join(text_parts)
        if is_error:
            output = f"Tool Error: {output}"
            
        return output


class MCPServerManager:
    """Manages multiple MCP server connections simultaneously."""
    
    def __init__(self):
        self.servers: Dict[str, MCPClient] = {}
        
    async def start_all(self, server_configs: List[Dict[str, Any]]):
        """Initialize all servers from config."""
        if not server_configs:
            return
            
        print("\n--- Initializing MCP Servers ---")
        tasks = []
        for conf in server_configs:
            name = conf.get("name")
            cmd = conf.get("command")
            args = conf.get("args", [])
            env = conf.get("env", {})
            
            if not name or not cmd:
                print(f"[!] MCP config missing name or command: {conf}")
                continue
                
            client = MCPClient(name, cmd, args, env)
            self.servers[name] = client
            tasks.append(client.start())
            
        if tasks:
            # We want to wait for all, but not fail entirely if one breaks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    print(f"[!] MCP Server start failed: {res}")
                    
    async def stop_all(self):
        """Cleanup all processes."""
        print("[!] Stopping MCP servers...")
        tasks = [s.stop() for s in self.servers.values()]
        if tasks:
            await asyncio.gather(*tasks)

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Aggregate all tools across all connected servers.
        Reformats them directly into the OpenAI/Anthropic 'function' schema format.
        """
        all_tools = []
        for server_name, client in self.servers.items():
            if not client.is_initialized:
                continue
                
            for tool in client.tools:
                # Convert MCP Tool schema to standard LLM function schema
                all_tools.append({
                    "type": "function",
                    "function": {
                        # Prefix the tool name with the server name to avoid collisions
                        "name": f"mcp_{server_name}__{tool['name']}",
                        "description": tool.get("description", f"Tool {tool['name']} from {server_name}"),
                        "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                    },
                    # We inject this metadata so brain_core knows where to route it
                    "_mcp_server": server_name,
                    "_mcp_tool_name": tool["name"]
                })
        return all_tools

    async def execute_tool(self, fully_qualified_name: str, arguments: dict) -> str:
        """Route a tool call to the correct server."""
        # Name format: mcp_SERVERNAME__TOOLNAME
        if not fully_qualified_name.startswith("mcp_"):
            return "Error: Invalid MCP tool name"
            
        parts = fully_qualified_name[4:].split("__", 1)
        if len(parts) != 2:
            return "Error: Malformed MCP tool name"
            
        server_name, tool_name = parts
        
        client = self.servers.get(server_name)
        if not client:
            return f"Error: MCP Server '{server_name}' not found or offline"
            
        try:
            return await client.call_tool(tool_name, arguments)
        except Exception as e:
            return f"Error executing tool: {str(e)}"
