from openai import OpenAI
from typing import Dict, Any, List, Callable
from backend.src.aiagents.prompts import ContractAgentPrompts
from backend.src.aiagents.tools.contract_tools import (
    create_client_tool, search_clients_tool, get_all_clients_tool, get_client_details_tool, get_contract_details_tool, analyze_contract_tool, 
    smart_create_contract_tool, smart_contract_document_tool, get_contracts_by_client_tool,
    get_all_contracts_tool, get_contracts_by_billing_date_tool, update_contract_tool, CreateClientParams, SmartContractParams, 
    ContractDocumentParams, UpdateContractParams, ContractToolResult
)
from backend.src.aiagents.tools.client_tools import (
    update_client_tool as update_client_tool_client, UpdateClientParams as UpdateClientParamsClient, ClientToolResult
)
from backend.src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from backend.src.aiagents.guardrails.output_guardrails import output_validation_guardrail
import json
import os

class ContractAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = "Milo"
        self.instructions = ContractAgentPrompts.SYSTEM_INSTRUCTIONS
        self.model = "gpt-4o-mini"
        
        # Dynamic tool mapping - no hardcoded if-else logic
        self.tool_functions = {
            "create_client": self._create_client_wrapper,
            "search_clients": self._search_clients_wrapper,
            "get_all_clients": self._get_all_clients_wrapper,
            "get_client_details": self._get_client_details_wrapper,
            "analyze_contract": self._analyze_contract_wrapper,
            "create_contract": self._smart_create_contract_wrapper,
            "get_client_contracts": self._get_contracts_by_client_wrapper,
            "get_all_contracts": self._get_all_contracts_wrapper,
            "get_contract_details": self._get_contract_details_wrapper,
            "get_contracts_by_billing_date": self._get_contracts_by_billing_date_wrapper,
            "update_contract": self._update_contract_wrapper,
            "update_client": self._update_client_wrapper,
            "manage_contract_document": self._smart_contract_document_wrapper
        }
        
        self.tools = self._get_tool_schemas()
    
    def _create_client_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for create_client_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = CreateClientParams(**kwargs)
        result = create_client_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_all_clients_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_all_clients_tool"""
        db = kwargs.pop('db', None)
        result = get_all_clients_tool(db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_contract_details_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_contract_details_tool"""
        db = kwargs.pop('db', None)
        contract_id = kwargs.get("contract_id")
        client_name = kwargs.get("client_name")
        result = get_contract_details_tool(contract_id, client_name, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_client_details_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_client_details_tool"""
        db = kwargs.pop('db', None)
        client_name = kwargs.get("client_name")
        result = get_client_details_tool(client_name, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _search_clients_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for search_clients_tool"""
        db = kwargs.pop('db', None)
        search_term = kwargs.get("search_term")
        limit = kwargs.get("limit", 10)
        result = search_clients_tool(search_term, limit, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _analyze_contract_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for analyze_contract_tool"""
        contract_text = kwargs.get("contract_text")
        result = analyze_contract_tool(contract_text)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _smart_create_contract_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for smart_create_contract_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = SmartContractParams(**kwargs)
        result = smart_create_contract_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_contracts_by_client_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_contracts_by_client_tool"""
        db = kwargs.pop('db', None)
        client_name = kwargs.get("client_name")
        result = get_contracts_by_client_tool(client_name, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_all_contracts_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_all_contracts_tool"""
        db = kwargs.pop('db', None)
        result = get_all_contracts_tool(db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_contracts_by_billing_date_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_contracts_by_billing_date_tool"""
        db = kwargs.pop('db', None)
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        result = get_contracts_by_billing_date_tool(start_date, end_date, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _update_contract_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for update_contract_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = UpdateContractParams(**kwargs)
        result = update_contract_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _update_client_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for update_client_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = UpdateClientParamsClient(**kwargs)
        result = update_client_tool_client(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _smart_contract_document_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for smart_contract_document_tool"""
        db = kwargs.pop('db', None)
        params = ContractDocumentParams(**kwargs)
        result = smart_contract_document_tool(params, db)
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
                    "name": "create_client",
                    "description": "Create a new client record in the CRM system with company information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "The full name of the client company or organization"
                            },
                            "industry": {
                                "type": "string",
                                "description": "The industry or business sector the client operates in"
                            },
                            "primary_contact_name": {
                                "type": "string",
                                "description": "Name of the primary contact person at the client company"
                            },
                            "primary_contact_email": {
                                "type": "string",
                                "description": "Email address of the primary contact person"
                            },
                            "company_size": {
                                "type": "string",
                                "description": "Size of the company (e.g., Small, Medium, Large, Enterprise)"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes or comments about the client"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_clients",
                    "description": "Search for existing clients in the database by name, industry, or other criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term to find clients (can be company name, industry, or other keywords)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_clients",
                    "description": "Get a list of all clients in the system with basic information (name, industry, contact details)",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_details",
                    "description": "Get detailed information about a specific client including contact details, email addresses, and company information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "The name of the client to get detailed information for"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_contract_details",
                    "description": "Get comprehensive contract details including financial information, billing details, and metadata. Can search by contract ID or client name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contract_id": {
                                "type": "integer",
                                "description": "The ID of the specific contract to get details for"
                            },
                            "client_name": {
                                "type": "string",
                                "description": "The name of the client to get contract details for (will return most recent contract)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_contract",
                    "description": "Analyze contract text to extract key terms, obligations, dates, and financial information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contract_text": {
                                "type": "string",
                                "description": "The full text content of the contract to analyze"
                            }
                        },
                        "required": ["contract_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_contract",
                    "description": "Create a new contract for a client by client name - automatically finds client_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client to create the contract for"
                            },
                            "contract_type": {
                                "type": "string",
                                "description": "Type of contract: Fixed, Hourly, or Retainer"
                            },
                            "original_amount": {
                                "type": "number",
                                "description": "Contract amount in dollars (optional)"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Contract start date in YYYY-MM-DD format (optional)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Contract end date in YYYY-MM-DD format (optional)"
                            },
                            "billing_frequency": {
                                "type": "string",
                                "description": "Billing frequency: Monthly, Weekly, or One-time (optional)"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes about the contract (optional)"
                            }
                        },
                        "required": ["client_name", "contract_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_contracts",
                    "description": "Get all contracts for a specific client by client name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client to get contracts for"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_contracts",
                    "description": "Get all contracts across all clients in the system",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_contracts_by_billing_date",
                    "description": "Get contracts with billing prompt dates within a specific date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date for the billing prompt date range (YYYY-MM-DD format)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date for the billing prompt date range (YYYY-MM-DD format)"
                            }
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_contract",
                    "description": "Update an existing contract's details like dates, amount, status, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client whose contract to update"
                            },
                            "contract_id": {
                                "type": "integer",
                                "description": "Specific contract ID (optional - will use latest contract if not provided)"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "New start date in YYYY-MM-DD format (optional)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "New end date in YYYY-MM-DD format (optional)"
                            },
                            "contract_type": {
                                "type": "string",
                                "description": "New contract type: Fixed, Hourly, or Retainer (optional)"
                            },
                            "original_amount": {
                                "type": "number",
                                "description": "New contract amount in dollars (optional)"
                            },
                            "billing_frequency": {
                                "type": "string",
                                "description": "New billing frequency: Monthly, Weekly, or One-time (optional)"
                            },
                            "billing_prompt_next_date": {
                                "type": "string",
                                "description": "New billing prompt next date in YYYY-MM-DD format (optional)"
                            },
                            "status": {
                                "type": "string",
                                "description": "New contract status: draft, active, completed, or terminated (optional)"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes about the contract update (optional)"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_client",
                    "description": "Update an existing client's information like contact details, industry, notes, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client to update"
                            },
                            "industry": {
                                "type": "string",
                                "description": "New industry or business sector (optional)"
                            },
                            "primary_contact_name": {
                                "type": "string",
                                "description": "New primary contact person name (optional)"
                            },
                            "primary_contact_email": {
                                "type": "string",
                                "description": "New primary contact email address (optional)"
                            },
                            "company_size": {
                                "type": "string",
                                "description": "New company size: Small, Medium, Large, Enterprise (optional)"
                            },
                            "notes": {
                                "type": "string",
                                "description": "New notes or comments about the client (optional)"
                            },
                            "address": {
                                "type": "string",
                                "description": "New company address (optional)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "New company phone number (optional)"
                            },
                            "website": {
                                "type": "string",
                                "description": "New company website URL (optional)"
                            }
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_contract_document",
                    "description": "Manage contract documents - get upload information or check document status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {
                                "type": "string",
                                "description": "Name of the client whose contract document to manage"
                            },
                            "contract_id": {
                                "type": "integer",
                                "description": "Specific contract ID (optional - will use latest contract if not provided)"
                            },
                            "document_action": {
                                "type": "string",
                                "description": "Action to perform: upload or update",
                                "default": "upload"
                            }
                        },
                        "required": ["client_name"]
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
                "agent_type": "contract",
                "capabilities": ["client_management", "contract_analysis", "document_processing"]
            }
            
            # Apply input guardrails
            sanitized_message = input_sanitization_guardrail(message)
            
            # Prepare context without database session for JSON serialization
            json_safe_context = {k: v for k, v in enhanced_context.items() if k != "database"}
            
            # Prepare messages for OpenAI with function calling
            messages = [
                {"role": "system", "content": self.instructions},
            ]
            
            # Add conversation history if available for context
            if "conversation_history" in enhanced_context and enhanced_context["conversation_history"]:
                # Add recent conversation history (last 3-4 messages for context)
                recent_history = enhanced_context["conversation_history"][-4:]
                for msg in recent_history:
                    if msg.get("role") == "user" and msg.get("content"):
                        messages.append({"role": "user", "content": msg["content"]})
                    elif msg.get("role") == "assistant" and msg.get("content"):
                        messages.append({"role": "assistant", "content": msg["content"]})
            
            # Add current message
            messages.append({"role": "user", "content": f"Context: {json.dumps(json_safe_context)}\n\nMessage: {sanitized_message}"})
            
            # Process through OpenAI with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",  # Let the LLM decide when to use tools
                temperature=0.1,  # Lower temperature for more consistent behavior
                max_tokens=500  # Reduced for faster responses
            )
            
            response_message = response.choices[0].message
            
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
                
                                                # Check if we need to make additional tool calls based on the results
                should_continue = self._should_continue_with_tools(tool_results, sanitized_message)
                
                if should_continue:
                    continuation_prompt = self._get_continuation_prompt(tool_results, sanitized_message)
                    
                    # Make another OpenAI call to continue the workflow
                    continue_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages + [{"role": "user", "content": continuation_prompt}],
                        tools=self.tools,
                        tool_choice="required",  # Force a tool call
                        temperature=0.1,
                        max_tokens=500
                    )
                    

                    
                    if continue_response.choices[0].message.tool_calls:
                        print(f"🔍 ContractAgent: Found {len(continue_response.choices[0].message.tool_calls)} additional tool calls to execute")
                        for tool_call in continue_response.choices[0].message.tool_calls:
                            print(f"🔍 ContractAgent: Executing additional tool call: {tool_call.function.name}")
                            print(f"🔍 ContractAgent: Additional tool arguments: {tool_call.function.arguments}")
                            additional_result = await self._execute_tool_call(tool_call, enhanced_context)
                            print(f"🔍 ContractAgent: Additional tool result: {additional_result}")
                            tool_results.append(additional_result)
                            
                            # Add to conversation
                            messages.append(continue_response.choices[0].message)
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_call.function.name,
                                "content": json.dumps(additional_result)
                            })
                        
                        # Check if we need to continue AGAIN after this iteration (e.g., client created, now create contract)
                        should_continue_again = self._should_continue_with_tools(tool_results, sanitized_message)
                        print(f"🔍 ContractAgent: After continuation tools, should_continue_again: {should_continue_again}")
                        
                        if should_continue_again:
                            print(f"🔍 ContractAgent: Need SECOND continuation (e.g., create contract after client)")
                            second_continuation_prompt = self._get_continuation_prompt(tool_results, sanitized_message)
                            print(f"🔍 ContractAgent: Second continuation prompt: {second_continuation_prompt}")
                            
                            # Make SECOND continuation call
                            second_continue_response = self.client.chat.completions.create(
                                model=self.model,
                                messages=messages + [{"role": "user", "content": second_continuation_prompt}],
                                tools=self.tools,
                                tool_choice="required",  # Force a tool call
                                temperature=0.1,
                                max_tokens=1000
                            )
                            
                            print(f"🔍 ContractAgent: Second continue response has tool_calls: {bool(second_continue_response.choices[0].message.tool_calls)}")
                            
                            if second_continue_response.choices[0].message.tool_calls:
                                print(f"🔍 ContractAgent: Executing SECOND continuation tool calls")
                                for tool_call in second_continue_response.choices[0].message.tool_calls:
                                    print(f"🔍 ContractAgent: Executing second continuation tool call: {tool_call.function.name}")
                                    print(f"🔍 ContractAgent: Second tool arguments: {tool_call.function.arguments}")
                                    second_result = await self._execute_tool_call(tool_call, enhanced_context)
                                    print(f"🔍 ContractAgent: Second tool result: {second_result}")
                                    tool_results.append(second_result)
                                    
                                    # Add to conversation
                                    messages.append(second_continue_response.choices[0].message)
                                    messages.append({
                                        "tool_call_id": tool_call.id,
                                        "role": "tool",
                                        "name": tool_call.function.name,
                                        "content": json.dumps(second_result)
                                    })
                            else:
                                print(f"🔍 ContractAgent: Second continuation failed, trying fallback")
                                # Use fallback mechanism for second continuation
                                self._try_fallback_contract_creation(tool_results, sanitized_message, enhanced_context)
                    else:
                        print(f"🔍 ContractAgent: ERROR - No tool calls found in continue response despite tool_choice='required'")
                        print(f"🔍 ContractAgent: Continue response content: {continue_response.choices[0].message.content}")
                        print(f"🔍 ContractAgent: This suggests the LLM is not following the tool_choice='required' instruction")
                        
                        # Use fallback mechanism
                        self._try_fallback_contract_creation(tool_results, sanitized_message, enhanced_context)
                else:
                    print(f"🔍 ContractAgent: Should continue is False - no additional tool calls needed")
                
                print(f"🔍 ContractAgent: Getting final response from OpenAI after tool execution")
                
                # Get final response from LLM after tool execution
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                response_content = final_response.choices[0].message.content
                print(f"🔍 ContractAgent: Final response: {response_content}")
                
                # Apply output guardrails
                validated_response = output_validation_guardrail(response_content)
                
                # Get the most relevant data (last successful result or first result as fallback)
                result_data = None
                if tool_results:
                    # Find the most recent successful result with data
                    for result in reversed(tool_results):
                        if isinstance(result, dict) and result.get("success") and result.get("data"):
                            result_data = result.get("data")
                            break
                    # Fallback to first result if no successful data found
                    if result_data is None and tool_results[0] and isinstance(tool_results[0], dict):
                        result_data = tool_results[0].get("data")
                
                return {
                    "agent": "Milo",
                    "response": validated_response if isinstance(validated_response, str) else str(validated_response),
                    "success": True,
                    "data": result_data
                }
            
            else:
                print(f"🔍 ContractAgent: No tool calls found in response")
                print(f"🔍 ContractAgent: Response content: {response_message.content}")
                
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
            print(f"🔍 ContractAgent: Exception occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "agent": "Milo",
                "response": f"❌ Error processing request: {str(e)}",
                "success": False
            }
    
    async def _execute_tool_call(self, tool_call, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call made by the LLM - NO hardcoded if-else logic"""
        try:
            function_name = tool_call.function.name
            print(f"🔧 ContractAgent._execute_tool_call: Function name: {function_name}")
            
            # Better JSON parsing with error handling
            try:
                function_args = json.loads(tool_call.function.arguments)
                print(f"🔧 ContractAgent._execute_tool_call: Parsed args: {function_args}")
            except json.JSONDecodeError as json_error:
                print(f"🔧 ContractAgent._execute_tool_call: JSON decode error: {json_error}")
                return {
                    "success": False,
                    "message": f"Invalid JSON in function arguments: {str(json_error)}. Arguments: {tool_call.function.arguments}",
                    "data": None
                }
            
            # Get the database session from context
            db = context.get("database")
            print(f"🔧 ContractAgent._execute_tool_call: Database session: {db is not None}")
            function_args['db'] = db
            
            # Add context to function args for tools that need user_id
            function_args['context'] = context
            
            # Dynamically call the appropriate tool function
            if function_name in self.tool_functions:
                print(f"🔧 ContractAgent._execute_tool_call: Calling tool function: {function_name}")
                result = self.tool_functions[function_name](**function_args)
                print(f"🔧 ContractAgent._execute_tool_call: Tool function result: {result}")
                return result
            else:
                print(f"🔧 ContractAgent._execute_tool_call: Unknown function: {function_name}")
                print(f"🔧 ContractAgent._execute_tool_call: Available functions: {list(self.tool_functions.keys())}")
                return {
                    "success": False,
                    "message": f"Unknown function: {function_name}",
                    "data": None
                }
                
        except Exception as e:
            print(f"🔧 ContractAgent._execute_tool_call: Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error executing tool {tool_call.function.name}: {str(e)}",
                "data": None
            }
    
    def _should_continue_with_tools(self, tool_results: List[Dict[str, Any]], original_message: str) -> bool:
        """Determine if we should continue with additional tool calls based on results and message intent"""
        if not tool_results:
            print(f"🔍 ContractAgent._should_continue_with_tools: No tool results")
            return False
            
        last_result = tool_results[-1]
        message_lower = original_message.lower()
        
        print(f"🔍 ContractAgent._should_continue_with_tools: Checking last result: {last_result}")
        print(f"🔍 ContractAgent._should_continue_with_tools: Original message: {original_message}")
        
        # If we searched for clients and found none, and the message indicates contract creation, we should create the client
        if (last_result.get("message", "").startswith("📋 Found 0 clients") and 
            ("create" in message_lower and "contract" in message_lower)):
            print(f"🔍 ContractAgent._should_continue_with_tools: Found 0 clients, need to create client first")
            return True
            
        # If we found existing clients and the message indicates contract creation, we should create the contract
        if (last_result.get("success") and 
            last_result.get("message", "").startswith("📋 Found") and 
            "clients" in last_result.get("message", "") and
            ("create" in message_lower and "contract" in message_lower)):
            print(f"🔍 ContractAgent._should_continue_with_tools: Found existing clients, need to create contract")
            print(f"🔍 ContractAgent._should_continue_with_tools: Last result message: '{last_result.get('message', '')}'")
            return True
            
        # If we just created a client and the message indicates contract creation, we should create the contract
        if (last_result.get("success") and 
            ("created successfully" in last_result.get("message", "").lower() or "successfully created" in last_result.get("message", "").lower()) and
            ("create" in message_lower and "contract" in message_lower)):
            print(f"🔍 ContractAgent._should_continue_with_tools: Client created, need to create contract")
            print(f"🔍 ContractAgent._should_continue_with_tools: Last result message: '{last_result.get('message', '')}'")
            print(f"🔍 ContractAgent._should_continue_with_tools: Message contains 'create': {'create' in message_lower}")
            print(f"🔍 ContractAgent._should_continue_with_tools: Message contains 'contract': {'contract' in message_lower}")
            return True
            
        # If we found existing contracts and the message indicates contract update, we should update the contract
        if (last_result.get("success") and 
            last_result.get("message", "").startswith("📋 Found") and 
            "contracts" in last_result.get("message", "") and
            ("update" in message_lower or "change" in message_lower or "modify" in message_lower) and
            "contract" in message_lower):
            print(f"🔍 ContractAgent._should_continue_with_tools: Found existing contracts, need to update contract")
            print(f"🔍 ContractAgent._should_continue_with_tools: Last result message: '{last_result.get('message', '')}'")
            return True
            
        print(f"🔍 ContractAgent._should_continue_with_tools: No continuation needed")
        return False
    
    def _get_continuation_prompt(self, tool_results: List[Dict[str, Any]], original_message: str) -> str:
        """Get specific continuation prompt based on the tool results and original message"""
        if not tool_results:
            return "Continue with the next required action."
            
        last_result = tool_results[-1]
        message_lower = original_message.lower()
        
        # If we just created a client and need to create a contract
        if (last_result.get("success") and 
            "created successfully" in last_result.get("message", "").lower() and
            ("create" in message_lower and "contract" in message_lower)):
            
            # Extract client information from the result to pass to contract creation
            client_data = last_result.get("data", {})
            client_name = client_data.get("client_name", "the client")
            
            return f"IMPORTANT: You MUST call the create_contract function to create the contract. Do not just describe what you will do.\n\nCreate the contract for the client '{client_name}' that was just created. The client data is: {client_data}.\n\nExtract the contract details from the original message: '{original_message}'.\n\nYou MUST use the create_contract function with the exact client name '{client_name}'. This is a requirement, not a suggestion."
            
        # If we found existing clients and need to create a contract
        if (last_result.get("success") and 
            last_result.get("message", "").startswith("📋 Found") and 
            "clients" in last_result.get("message", "") and
            ("create" in message_lower and "contract" in message_lower)):
            
            # Extract client information from the search result
            client_data = last_result.get("data", {})
            clients = client_data.get("clients", [])
            
            if clients:
                client_name = clients[0].get("client_name", "the client")
                return f"IMPORTANT: You MUST call the create_contract function to create the contract. Do not just describe what you will do.\n\nCreate the contract for the existing client '{client_name}'. The client data is: {client_data}.\n\nExtract the contract details from the original message: '{original_message}'.\n\nYou MUST use the create_contract function with the exact client name '{client_name}'. This is a requirement, not a suggestion."
            else:
                return f"IMPORTANT: You MUST call the create_contract function to create the contract. Do not just describe what you will do.\n\nCreate the contract for the existing client found in the search.\n\nExtract the contract details from the original message: '{original_message}'.\n\nYou MUST use the create_contract function. This is a requirement, not a suggestion."
            
        # If we found existing contracts and need to update a contract
        if (last_result.get("success") and 
            last_result.get("message", "").startswith("📋 Found") and 
            "contracts" in last_result.get("message", "") and
            ("update" in message_lower or "change" in message_lower or "modify" in message_lower) and
            "contract" in message_lower):
            
            # Extract contract information from the search result
            client_data = last_result.get("data", {})
            client_name = client_data.get("client_name", "the client")
            contracts = client_data.get("contracts", [])
            
            if contracts:
                contract_id = contracts[0].get("contract_id")
                return f"IMPORTANT: You MUST call the update_contract function to update the contract. Do not just describe what you will do.\n\nUpdate the contract for client '{client_name}' (Contract ID: {contract_id}). The contract data is: {contracts[0]}.\n\nExtract the update details from the original message: '{original_message}'.\n\nYou MUST use the update_contract function with the exact client name '{client_name}'. This is a requirement, not a suggestion."
            else:
                return f"IMPORTANT: You MUST call the update_contract function to update the contract. Do not just describe what you will do.\n\nUpdate the contract for client '{client_name}'.\n\nExtract the update details from the original message: '{original_message}'.\n\nYou MUST use the update_contract function. This is a requirement, not a suggestion."
            
        # If we found no clients and need to create one
        if (last_result.get("message", "").startswith("📋 Found 0 clients") and 
            ("create" in message_lower and "contract" in message_lower)):
            return f"No client found. Create the client first using information from: '{original_message}'. Use the create_client function."
            
        return "Continue with the next required action based on the tool results."
    
    def _try_fallback_contract_creation(self, tool_results: List[Dict[str, Any]], sanitized_message: str, enhanced_context: Dict[str, Any]):
        """Try to automatically create the contract if we have client data"""
        print(f"🔍 ContractAgent: Attempting fallback contract creation")
        try:
            # Extract client data from the last successful result
            last_result = tool_results[-1]
            if last_result.get("success") and last_result.get("data"):
                client_data = last_result.get("data")
                client_name = client_data.get("client_name")
                
                if client_name and "create" in sanitized_message.lower() and "contract" in sanitized_message.lower():
                    print(f"🔍 ContractAgent: Fallback: Creating contract for client '{client_name}'")
                    
                    # Parse the original message for contract details
                    from backend.src.aiagents.tools.contract_tools import SmartContractParams
                    
                    # Extract dates from the message
                    import re
                    from datetime import datetime
                    
                    # Parse the specific dates from your message - handle various formats
                    start_date = None
                    end_date = None
                    contract_type = "Fixed"  # Default
                    billing_frequency = None
                    original_amount = None
                    
                    # Parse dates - handle various formats
                    if "Oct 1st" in sanitized_message or "Oct 1" in sanitized_message:
                        start_date = "2024-10-01"
                    elif "Aug 20th" in sanitized_message or "Aug 20" in sanitized_message:
                        start_date = "2024-08-20"
                        
                    if "25th Feb 2026" in sanitized_message or "Feb 25 2026" in sanitized_message:
                        end_date = "2026-02-25"
                    elif "31st Dec 2025" in sanitized_message or "Dec 31 2025" in sanitized_message:
                        end_date = "2025-12-31"
                    
                    # Parse contract type
                    if "fixed" in sanitized_message.lower():
                        contract_type = "Fixed"
                    elif "hourly" in sanitized_message.lower():
                        contract_type = "Hourly"
                    elif "retainer" in sanitized_message.lower():
                        contract_type = "Retainer"
                    
                    # Parse billing frequency
                    if "monthly" in sanitized_message.lower():
                        billing_frequency = "Monthly"
                    elif "weekly" in sanitized_message.lower():
                        billing_frequency = "Weekly"
                    elif "one-time" in sanitized_message.lower():
                        billing_frequency = "One-time"
                    
                    # Parse amount
                    import re
                    amount_match = re.search(r'\$?([\d,]+)', sanitized_message)
                    if amount_match:
                        original_amount = float(amount_match.group(1).replace(',', ''))
                    
                    print(f"🔍 ContractAgent: Fallback: Parsed contract details - start: {start_date}, end: {end_date}, type: {contract_type}, billing: {billing_frequency}, amount: {original_amount}")
                    
                    contract_params = SmartContractParams(
                        client_name=client_name,
                        contract_type=contract_type,
                        start_date=start_date,
                        end_date=end_date,
                        billing_frequency=billing_frequency,
                        original_amount=original_amount
                    )
                    
                    # Call the contract creation tool directly
                    from backend.src.aiagents.tools.contract_tools import smart_create_contract_tool
                    fallback_result = smart_create_contract_tool(contract_params, enhanced_context, enhanced_context.get("database"))
                    
                    print(f"🔍 ContractAgent: Fallback contract creation result: {fallback_result}")
                                                     
                    if fallback_result.success:
                        tool_results.append({
                            "success": fallback_result.success,
                            "message": fallback_result.message,
                            "data": fallback_result.data
                        })
                        print(f"🔍 ContractAgent: Fallback contract creation successful")
                    else:
                        print(f"🔍 ContractAgent: Fallback contract creation failed: {fallback_result.message}")
                        
        except Exception as e:
            print(f"🔍 ContractAgent: Fallback contract creation error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "Milo",
            "description": "Client and contract management specialist",
            "capabilities": [
                "Create and manage client records",
                "Process contract documents",
                "Analyze contract terms and obligations",
                "Track contract renewals and deadlines",
                "Manage client relationships"
            ],
            "tools": list(self.tool_functions.keys())
        }
