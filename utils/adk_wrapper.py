import json
from typing import Dict, Any, List, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ADKToolRegistry:
    """
    A unified wrapper bridging Google's Agent Development Kit (ADK) 
    tools with ReflexArc's ModelRouter schema requirements.
    """
    def __init__(self):
        self.tools = {}
        self.is_initialized = False
        
    def initialize(self):
        """Lazy load ADK to prevent crash if not installed."""
        try:
            import google.adk.tools as adk_tools
            # We can register global ADK tools here later
            self.is_initialized = True
            logger.info("adk_registry_initialized", status="success")
        except ImportError:
            logger.warning("adk_registry_failed", reason="google-adk not installed")
            
    def register_tool(self, adk_tool_instance: Any):
        """
        Takes an instance of an ADK tool and adds it to our registry.
        ADK tools typically have a .name, .description, and .input_schema.
        """
        if not self.is_initialized:
            self.initialize()
            
        tool_name = getattr(adk_tool_instance, "name", type(adk_tool_instance).__name__)
        # Ensure it has a prefix to identify it as an ADK tool in the router
        if not tool_name.startswith("adk_"):
            tool_name = f"adk_{tool_name}"
            
        self.tools[tool_name] = adk_tool_instance
        logger.debug("adk_tool_registered", tool_name=tool_name)
        
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Convert all registered ADK tools to standard OpenAI function schemas 
        so the Cortex LLM can understand them.
        """
        schema_tools = []
        for name, tool_instance in self.tools.items():
            
            description = getattr(tool_instance, "description", f"ADK Tool: {name}")
            
            # ADK schemas might be typed slightly differently depending on the version. 
            # We'll try to extract the parameters map. 
            parameters = {"type": "object", "properties": {}}
            if hasattr(tool_instance, "input_schema"):
                # Simplified extraction of properties. Will need to adjust if ADK changes schema objects
                try:
                    # Depending on if ADK uses pydantic schemas or dicts
                    if isinstance(tool_instance.input_schema, dict):
                         parameters = tool_instance.input_schema
                    elif hasattr(tool_instance.input_schema, "model_json_schema"):
                         parameters = tool_instance.input_schema.model_json_schema()
                except Exception as e:
                    logger.warning("adk_schema_extraction_failed", tool=name, error=str(e))

            schema_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                },
                "_is_adk_tool": True,
                "_original_name": name
            })
            
        return schema_tools

    async def execute_tool(self, name: str, arguments: dict) -> str:
        """Execute the mapped ADK tool by its registry name."""
        if name not in self.tools:
            return f"Error: ADK tool '{name}' not found."
            
        tool = self.tools[name]
        try:
            logger.info("executing_adk_tool", tool_name=name)
            
            # Most ADK tools use an execute() or __call__() method.
            if hasattr(tool, "execute"):
                import inspect
                # Some ADK wrapper tools might be async, handle appropriately
                if inspect.iscoroutinefunction(tool.execute):
                     result = await tool.execute(**arguments)
                else:
                     result = tool.execute(**arguments)
                return str(result)
            elif callable(tool):
                import inspect
                if inspect.iscoroutinefunction(tool):
                     result = await tool(**arguments)
                else:
                     result = tool(**arguments)
                return str(result)
            else:
                 return f"Error: ADK tool '{name}' has no execute method."
                 
        except Exception as e:
            logger.error("adk_tool_execution_failed", tool=name, error=str(e))
            return f"Error executing ADK tool: {str(e)}"

# Global instance
adk_registry = ADKToolRegistry()
