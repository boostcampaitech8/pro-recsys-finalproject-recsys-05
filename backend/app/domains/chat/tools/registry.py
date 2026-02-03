from typing import Dict
from app.domains.chat.tools.base import Tool

class ToolRegistry:
    """
    Central registry for all agent tools.
    Manages initialization and discovery of tools.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._initialize_tools()
        
    def _initialize_tools(self):
        """Initialize and register all available tools."""
        # TODO: 여기에 도구들 등록
        # self.register(SearchTool())
        
    def register(self, tool: Tool):
        """Register a tool instance."""
        if tool.name in self._tools:
            print(f"Warning: Overwriting tool '{tool.name}'")
        self._tools[tool.name] = tool
        
    def get_tools(self) -> Dict[str, Tool]:
        """Get all registered tools."""
        return self._tools