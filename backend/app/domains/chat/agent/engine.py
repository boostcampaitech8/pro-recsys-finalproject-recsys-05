"""Stateless Agent Engine for Steambot."""

import inspect
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("steambot")

from typing import Any, List, Optional

from app.domains.chat.agent.context import ContextBuilder

class AgentEngine:
    """
    The core processing engine for Steambot.
    
    It orchestrates the Think-Act-Observe loop in a stateless manner.
    """
    
    def __init__(
        self,
        llm_provider: Any, # Typed as Any for now, will be ClovaProvider
        tools: dict[str, Any], # Map of tool_name -> tool_callable
        max_iterations: int = 5,
        system_prompt: Optional[str] = None,
        llm_config: Optional[dict[str, Any]] = None,
        steam_id: Optional[str] = None,
        embedding_model: Optional[Any] = None
    ):
        self.llm_provider = llm_provider
        self.tools = tools
        self.max_iterations = max_iterations
        self.steam_id = steam_id
        self.embedding_model = embedding_model
        self.llm_config = llm_config or {}
        self.context_builder = ContextBuilder(system_prompt=system_prompt)

    async def run_turn(
        self,
        user_message: str,
        history: List[dict[str, Any]]
    ) -> str:
        """
        Run a single turn of the agent loop.
        
        Args:
            user_message: The user's input.
            history: Conversation history.
            
        Returns:
            The final response from the agent.
        """
        logger.info(f"Starting agent turn for message: {user_message[:100]}...")
        
        # Build initial messages
        messages = self.context_builder.build_messages(
            history=history,
            current_message=user_message
        )
        
        iteration = 0
        final_content = None
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Iteration {iteration}")
            
            # 1. Think (Call LLM)
            # Note: We need to pass tool definitions to the LLM
            tool_definitions = self._get_tool_definitions()
            
            try:
                response = await self.llm_provider.chat(
                    messages=messages,
                    tools=tool_definitions,
                    **self.llm_config
                )
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                return "죄송합니다. 처리 중에 오류가 발생했습니다."

            # 2. Decide (Tool Call or Final Answer)
            if response.tool_calls:
                # Add assistant message with tool calls
                # Convert ToolCallRequest objects back to dict format for context builder
                tool_calls_dict = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                
                messages = self.context_builder.add_assistant_message(
                    messages, 
                    response.content, 
                    tool_calls_dict
                )
                
                # 3. Act (Execute Tools)
                for tool_call in response.tool_calls:
                    function_name = tool_call.name
                    arguments_dict = tool_call.arguments
                    tool_call_id = tool_call.id
                    
                    logger.info(f"Tool Call: {function_name}({arguments_dict})")
                    
                    if function_name in self.tools:
                        try:
                            # Parse arguments
                            tool_func = self.tools[function_name]
                            args = arguments_dict

                            # Inject engine-level context only into tools whose
                            # execute() signature actually accepts the parameter
                            # (explicitly or via **kwargs).
                            if self.steam_id and self._tool_accepts_param(tool_func, "steam_id"):
                                args["steam_id"] = self.steam_id

                            if self.embedding_model is not None and self._tool_accepts_param(
                                tool_func, "embedding_model"
                            ):
                                args["embedding_model"] = self.embedding_model

                            # Execute (Strict Tool Interface)
                            # All tools must inherit from Tool(ABC) and implement execute()
                            result = await tool_func.execute(**args)
                                
                            logger.info(f"Tool Result: {str(result)[:50]}...")
                        except Exception as e:
                            logger.error(f"Tool Execution Error: {e}")
                            result = f"Error executing tool {function_name}: {str(e)}"
                    else:
                        result = f"Tool {function_name} not found."
                    
                    # 4. Observe (Add result to history)
                    messages = self.context_builder.add_tool_result(
                        messages, 
                        tool_call_id, 
                        function_name, 
                        result
                    )
            else:
                # No tool calls, we have a final answer
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "죄송합니다. 답변을 생성하는 데 실패했습니다. (Too many iterations)"
            
        return final_content

    @staticmethod
    def _tool_accepts_param(tool: Any, param_name: str) -> bool:
        """
        Check whether a tool's execute() can receive the given keyword argument.

        Returns True if the parameter is explicitly declared in the signature,
        or if the signature accepts arbitrary keyword arguments (**kwargs).
        Returns False when the signature cannot be inspected, so we never
        inject arguments into an opaque callable.
        """
        try:
            signature = inspect.signature(tool.execute)
        except (TypeError, ValueError):
            return False

        parameters = signature.parameters
        if param_name in parameters:
            param = parameters[param_name]
            return param.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )

        return any(
            param.kind is inspect.Parameter.VAR_KEYWORD
            for param in parameters.values()
        )

    def _get_tool_definitions(self) -> List[dict]:
        """Convert registered tools to OpenAI function definitions."""
        definitions = []
        for name, tool in self.tools.items():
            try:
                # All tools must inherit from Tool(ABC) and implement to_schema()
                if hasattr(tool, 'to_schema'):
                    definitions.append(tool.to_schema())
                else:
                    logger.warning(f"Tool {name} does not have 'to_schema' method. Skipping.")
            except Exception as e:
                logger.error(f"Failed to get schema for tool {name}: {e}")
        return definitions
