from openai import OpenAI
from typing import Dict, Any, List, Callable

from src.aiagents.tools.deliverable_tools import (
    smart_create_deliverable_tool, get_deliverables_by_client_tool, 
    get_deliverables_by_contract_tool, search_deliverables_tool,
    SmartDeliverableParams, DeliverableToolResult
)
from  src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from  src.aiagents.guardrails.output_guardrails import output_validation_guardrail
import json
import os

class DeliverableAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = "Milo"
        self.instructions = "You are Milo, an AI assistant."
        self.model = "gpt-4o-mini"
        
        # Dynamic tool mapping - no hardcoded if-else logic
        self.tool_functions = {
            "create_deliverable": self._smart_create_deliverable_wrapper,
            "get_client_deliverables": self._get_deliverables_by_client_wrapper,
            "get_contract_deliverables": self._get_deliverables_by_contract_wrapper,
            "search_deliverables": self._search_deliverables_wrapper
        }
        
        self.tools = self._get_tool_schemas()
    
    def _smart_create_deliverable_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for smart_create_deliverable_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = SmartDeliverableParams(**kwargs)
        result = smart_create_deliverable_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_deliverables_by_client_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_deliverables_by_client_tool"""
        db = kwargs.pop('db', None)
        client_name = kwargs.get("client_name")
        result = get_deliverables_by_client_tool(client_name, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_deliverables_by_contract_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_deliverables_by_contract_tool"""
        db = kwargs.pop('db', None)
        client_name = kwargs.get("client_name")
        contract_id = kwargs.get("contract_id")
        result = get_deliverables_by_contract_tool(client_name, contract_id, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _search_deliverables_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for search_deliverables_tool"""
        db = kwargs.pop('db', None)
        search_term = kwargs.get("search_term")
        result = search_deliverables_tool(search_term, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Define OpenAI function calling schemas for tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_deliverable",
                    "description": "Create a new deliverable for a client by client name - automatically finds contract and handles client resolution",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client to create the deliverable for"
                            },
                            "deliverable_name": {
                                "type": "string",
                                "description": "Name of the deliverable/project task"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the deliverable (optional)"
                            },
                            "contract_id": {
                                "type": "integer",
                                "description": "Specific contract ID (optional - will use latest active contract if not provided)"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date in YYYY-MM-DD format (optional)"
                            },
                            "billing_basis": {
                                "type": "string",
                                "description": "Billing basis: Fixed, Hourly, or Milestone (optional, defaults to Fixed)"
                            },
                            "estimated_hours": {
                                "type": "number",
                                "description": "Estimated hours for completion (optional)"
                            },
                            "assigned_employees": {
                                "type": "integer",
                                "description": "Number of employees assigned to this deliverable (optional, defaults to 1)"
                            },
                            "assigned_employee_name": {
                                "type": "string",
                                "description": "Name of the assigned employee (optional)"
                            },
                            "billing_amount": {
                                "type": "number",
                                "description": "Total billing amount for this deliverable (optional)"
                            }
                        },
                        "required": ["client_name", "deliverable_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_deliverables",
                    "description": "Get all deliverables for a specific client by client name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client to get deliverables for"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_contract_deliverables",
                    "description": "Get deliverables for a specific contract by client name and optional contract ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client"
                            },
                            "contract_id": {
                                "type": "integer",
                                "description": "Specific contract ID (optional - will use latest contract if not provided)"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_deliverables",
                    "description": "Search for deliverables by name, description, or client name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term to find deliverables"
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            }
        ]
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message through Milo using OpenAI function calling"""
        try:
            # Add context to message processing
            enhanced_context = {
                **context,
                "agent_type": "deliverable",
                "capabilities": ["deliverable_management", "project_tracking", "client_coordination"]
            }
            
            # Apply input guardrails
            sanitized_message = input_sanitization_guardrail(message)
            
            # Prepare context without database session for JSON serialization
            json_safe_context = {k: v for k, v in enhanced_context.items() if k != "database"}
            
            # Prepare messages for OpenAI with function calling
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
                tool_choice="auto",  # Let the LLM decide which tools to use
                temperature=0.3,     # 🚀 PHASE 2: Balanced for better natural language understanding
                max_tokens=500,      # 🚀 OPTIMIZATION: Reduced from 1000 to 500 for faster generation
                timeout=10.0         # 🚀 OPTIMIZATION: Added 10s timeout for faster failure detection
            )
            
            response_message = response.choices[0].message
            
            # Check if the LLM wants to call any tools
            if response_message.tool_calls:
                # Execute the tool calls dynamically
                tool_results = []
                for tool_call in response_message.tool_calls:
                    tool_result = await self._execute_tool_call(tool_call, enhanced_context)
                    tool_results.append(tool_result)
                
                # Add tool call and results to conversation
                messages.append(response_message)
                for i, tool_call in enumerate(response_message.tool_calls):
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(tool_results[i])
                    })
                
                # Get final response from LLM after tool execution
                # 🚀 PHASE 1 OPTIMIZATION: Reduced timeout and optimized parameters for faster responses
                # TODO: If performance degrades, revert temperature to 0.7 and max_tokens to 1000
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,     # 🚀 PHASE 2: Balanced for better natural language understanding
                    max_tokens=500,      # 🚀 OPTIMIZATION: Reduced from 1000 to 500 for faster generation
                    timeout=10.0         # 🚀 OPTIMIZATION: Added 10s timeout for faster failure detection
                )
                
                response_content = final_response.choices[0].message.content
                
                # Apply output guardrails
                validated_response = output_validation_guardrail(response_content)
                
                return {
                    "agent": "Milo",
                    "response": validated_response if isinstance(validated_response, str) else str(validated_response),
                    "success": True,
                    "data": tool_results[0] if tool_results and isinstance(tool_results[0], dict) and tool_results[0].get("data") else None
                }
            
            else:
                # No tool calls needed, return direct response
                response_content = response_message.content
                
                # Apply output guardrails
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
        """Execute a tool call made by the LLM - NO hardcoded if-else logic"""
        try:
            function_name = tool_call.function.name
            
            # Better JSON parsing with error handling
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as json_error:
                return {
                    "success": False,
                    "message": f"Invalid JSON in function arguments: {str(json_error)}. Arguments: {tool_call.function.arguments}",
                    "data": None
                }
            
            # Get the database session from context
            db = context.get("database")
            function_args['db'] = db
            
            # Add context to function args for tools that need user_id
            function_args['context'] = context
            
            # Dynamically call the appropriate tool function
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
        """Return agent capabilities"""
        return {
            "name": "Milo",
            "description": "Project deliverable and milestone management specialist",
            "capabilities": [
                "Create and manage project deliverables",
                "Track deliverable progress and status",
                "Coordinate deliverable assignments",
                "Monitor deadlines and milestones",
                "Link deliverables to contracts and clients"
            ],
            "tools": list(self.tool_functions.keys())
        }
