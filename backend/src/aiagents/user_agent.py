from openai import OpenAI

from src.aiagents.tools.user_tools import (
    create_user_tool, get_user_details_tool, update_user_tool, delete_user_tool, search_users_tool,
    CreateUserParams, UpdateUserParams, SearchUsersParams, GetUserDetailsParams, DeleteUserParams, UserToolResult
)
from src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from src.aiagents.guardrails.output_guardrails import output_validation_guardrail
from typing import Dict, Any, List
import json
import os

class UserAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = "Milo"
        self.instructions = "You are Milo, an AI assistant."
        self.model = "gpt-4o-mini"
        
        self.tool_functions = {
            "create_user": self._create_user_wrapper,
            "get_user_details": self._get_user_details_wrapper,
            "update_user": self._update_user_wrapper,
            "delete_user": self._delete_user_wrapper,
            "search_users": self._search_users_wrapper,
        }
        
        self.tools = self._get_tool_schemas()
    
    def _create_user_wrapper(self, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop('db', None)
        params = CreateUserParams(**kwargs)
        result = create_user_tool(params, db)
        return result.model_dump()

    def _get_user_details_wrapper(self, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop('db', None)
        params = GetUserDetailsParams(**kwargs)
        result = get_user_details_tool(params, db)
        return result.model_dump()

    def _update_user_wrapper(self, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop('db', None)
        params = UpdateUserParams(**kwargs)
        result = update_user_tool(params, db)
        return result.model_dump()

    def _delete_user_wrapper(self, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop('db', None)
        params = DeleteUserParams(**kwargs)
        result = delete_user_tool(params, db)
        return result.model_dump()

    def _search_users_wrapper(self, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop('db', None)
        params = SearchUsersParams(**kwargs)
        result = search_users_tool(params, db)
        return result.model_dump()
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_user",
                    "description": "Create a new user account",
                    "parameters": CreateUserParams.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_details",
                    "description": "Retrieve detailed information about a specific user",
                    "parameters": GetUserDetailsParams.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_user",
                    "description": "Update an existing user's information",
                    "parameters": UpdateUserParams.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_user",
                    "description": "Delete a user account",
                    "parameters": DeleteUserParams.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_users",
                    "description": "Search for users by email, name, role, or status",
                    "parameters": SearchUsersParams.model_json_schema()
                }
            }
        ]
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            enhanced_context = {
                **context,
                "agent_type": "user_management",
                "capabilities": ["create_user", "read_user", "update_user", "delete_user", "search_user"]
            }
            
            sanitized_message = input_sanitization_guardrail(message)
            json_safe_context = {k: v for k, v in enhanced_context.items() if k != "database"}
            
            messages = [
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": f"Context: {json.dumps(json_safe_context)}\n\nMessage: {sanitized_message}"}
            ]
            
            # 🚀 PHASE 1 OPTIMIZATION: Reduced timeout and optimized parameters for faster responses
            # TODO: If performance degrades, revert temperature to 0.7 and max_tokens to 1000
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1,     # 🚀 OPTIMIZATION: Reduced from 0.7 to 0.1 for faster, more deterministic responses
                max_tokens=500,      # 🚀 OPTIMIZATION: Reduced from 1000 to 500 for faster generation
                timeout=10.0         # 🚀 OPTIMIZATION: Added 10s timeout for faster failure detection
            )
            
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                tool_results = []
                for tool_call in response_message.tool_calls:
                    tool_result = await self._execute_tool_call(tool_call, enhanced_context)
                    tool_results.append(tool_result)
                
                messages.append(response_message)
                for i, tool_call in enumerate(response_message.tool_calls):
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(tool_results[i])
                    })
                
                # 🚀 PHASE 1 OPTIMIZATION: Reduced timeout and optimized parameters for faster responses
                # TODO: If performance degrades, revert temperature to 0.7 and max_tokens to 1000
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,     # 🚀 OPTIMIZATION: Reduced from 0.7 to 0.1 for faster, more deterministic responses
                    max_tokens=500,      # 🚀 OPTIMIZATION: Reduced from 1000 to 500 for faster generation
                    timeout=10.0         # 🚀 OPTIMIZATION: Added 10s timeout for faster failure detection
                )
                
                response_content = final_response.choices[0].message.content
                validated_response = output_validation_guardrail(response_content)
                
                return {
                    "agent": "Milo",
                    "response": validated_response if isinstance(validated_response, str) else str(validated_response),
                    "success": True,
                    "data": tool_results[0] if tool_results and isinstance(tool_results[0], dict) and tool_results[0].get("data") else None
                }
            
            else:
                response_content = response_message.content
                validated_response = output_validation_guardrail(response_content)
                
                return {
                    "agent": "Milo",
                    "response": validated_response if isinstance(validated_response, str) else str(validated_response),
                    "success": True,
                    "data": None
                }
            
        except Exception as e:
            return {
                "agent": "Milo",
                "response": f"❌ Error processing request: {str(e)}",
                "success": False
            }
    
    async def _execute_tool_call(self, tool_call, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            function_name = tool_call.function.name
            
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as json_error:
                return {
                    "success": False,
                    "message": f"Invalid JSON in function arguments: {str(json_error)}. Arguments: {tool_call.function.arguments}",
                    "data": None
                }
            
            db = context.get("database")
            function_args['db'] = db
            function_args['context'] = context
            
            if function_name in self.tool_functions:
                return self.tool_functions[function_name](**function_args)
            else:
                return {
                    "success": False,
                    "message": f"Unknown function: {function_name}",
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing tool {tool_call.function.name}: {str(e)}",
                "data": None
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Milo",
            "description": "User account and profile management specialist",
            "capabilities": [
                "Create user accounts",
                "Retrieve user details",
                "Update user information",
                "Delete user accounts",
                "Search users"
            ],
            "tools": list(self.tool_functions.keys())
        }
