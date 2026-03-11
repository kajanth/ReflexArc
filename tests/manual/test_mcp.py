import asyncio
from mcp_client import MCPServerManager
import yaml

async def test():
    mgr = MCPServerManager()
    with open("config/brain.yaml") as f:
        conf = yaml.safe_load(f)
    print("Loaded config, starting MCP servers...")
    
    # Filter to just one server to simplify if needed, or start all
    await mgr.start_all(conf.get("mcp_servers", []))
    
    tools = mgr.get_all_tools()
    print(f"Discovered {len(tools)} tools.")
    
    if tools:
        # Just grab the first tool to test execution 
        tool_name = tools[0]["function"]["name"]
        print(f"Executing tool {tool_name} with empty args...")
        
        try:
            # Most tools will fail gracefully if missing args, which is what we want to test
            res = await mgr.execute_tool(tool_name, {})
            print("Result:", res[:200])
        except Exception as e:
            print("Exception:", e)
            
    print("Stopping servers...")
    await mgr.stop_all()

if __name__ == "__main__":
    asyncio.run(test())
