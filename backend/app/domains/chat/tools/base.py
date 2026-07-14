"""Base class for agent tools."""

from abc import ABC, abstractmethod
from typing import Any
from app.domains.chat.interfaces import UserIntent


class Tool(ABC):
    """
    Abstract base class for agent tools.
    
    Tools are capabilities that the agent can use to interact with
    the environment, such as reading files, executing commands, etc.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in function calls."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        pass

    @property
    def tags(self) -> list[UserIntent]:
        """List of intents this tool supports."""
        return []
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters.
        
        Returns:
            String result of the tool execution.
        """
        pass
    
    def to_schema(self) -> dict[str, Any]:
        """Convert tool to OpenAI function schema format."""
        # 일부 도구가 최상위 "type": "object"를 누락 — Gemini는 이 경우 스키마를
        # 무시하고 빈 인자로 호출하므로 여기서 일괄 보정한다.
        parameters = dict(self.parameters)
        parameters.setdefault("type", "object")
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            }
        }

