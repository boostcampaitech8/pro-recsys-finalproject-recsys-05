"""Stateless Agent Engine for Steambot."""

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
        max_iterations: int = 5
    ):
        self.llm_provider = llm_provider
        self.tools = tools
        self.max_iterations = max_iterations
        self.context_builder = ContextBuilder()

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
        logger.info(f"Starting agent turn for message: {user_message[:50]}...")
        
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
                    tools=tool_definitions
                )
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                return "죄송합니다. 처리 중에 오류가 발생했습니다."

            # 2. Decide (Tool Call or Final Answer)
            if response.tool_calls:
                # Add assistant message with tool calls
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
                            
                            # Execute
                            if hasattr(tool_func, 'run'): # If it's a class-based tool
                                result = await tool_func.run(**args)
                            else: # If it's a raw function
                                if  getattr(tool_func, "__code__", None) and tool_func.__code__.co_flags & 0x80: # Check if async
                                     result = await tool_func(**args)
                                else:
                                     result = tool_func(**args)
                                
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

    def _get_tool_definitions(self) -> List[dict]:
        """Convert registered tools to OpenAI function definitions."""
        definitions = []
        for name, tool in self.tools.items():
            # If tool is a class with 'get_definition' method
            if hasattr(tool, 'get_definition'):
                definitions.append(tool.get_definition())
            # If tool has 'openai_schema' attribute (standard in some libraries)
            elif hasattr(tool, 'openai_schema'):
                definitions.append(tool.openai_schema)
            # Fallback handling would go here
        return definitions
