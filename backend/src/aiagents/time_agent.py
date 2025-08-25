from openai import OpenAI
from backend.src.aiagents.prompts import TimeTrackerPrompts
from backend.src.aiagents.tools.time_tools import (
    create_time_entry_tool, get_timesheet_tool, CreateTimeEntryParams,
    search_projects_tool, smart_create_time_entry_tool, SmartTimeEntryParams
)
from backend.src.aiagents.tools.contract_tools import ContractToolResult
from backend.src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from backend.src.aiagents.guardrails.output_guardrails import output_validation_guardrail
from typing import Dict, Any, List
from datetime import date, timedelta
from decimal import Decimal
from backend.src.database.core.models import TimeEntry
from backend.src.database.core.schemas import TimeEntryCreate
from typing import Optional
import json
import os

class TimeTrackerAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = "Milo"
        self.instructions = TimeTrackerPrompts.SYSTEM_INSTRUCTIONS
        self.model = "gpt-4o-mini"
        
        # Dynamic tool mapping - no hardcoded if-else logic
        self.tool_functions = {
            "log_time_for_project": self._smart_create_time_entry_wrapper,
            "search_projects": self._search_projects_wrapper,
            "get_timesheet": self._get_timesheet_wrapper
        }
        
        self.tools = self._get_tool_schemas()
    
    def _smart_create_time_entry_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for smart_create_time_entry_tool"""
        db = kwargs.pop('db', None)
        
        # Convert hours to Decimal if needed
        if 'hours_worked' in kwargs and not isinstance(kwargs['hours_worked'], Decimal):
            kwargs['hours_worked'] = Decimal(str(kwargs['hours_worked']))
        
        params = SmartTimeEntryParams(**kwargs)
        result = smart_create_time_entry_tool(params, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _search_projects_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for search_projects_tool"""
        db = kwargs.pop('db', None)
        search_term = kwargs.get("search_term", "")
        
        result = search_projects_tool(search_term, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _create_time_entry_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for create_time_entry_tool"""
        db = kwargs.pop('db', None)
        
        # Set defaults for required fields if not provided
        kwargs.setdefault('employee_id', 1)
        kwargs.setdefault('contract_id', 1)
        kwargs.setdefault('client_id', 1)
        kwargs.setdefault('date', date.today().isoformat())
        kwargs.setdefault('billable', True)
        
        # Convert date string to date object if needed
        if isinstance(kwargs['date'], str):
            kwargs['date'] = date.fromisoformat(kwargs['date'])
        
        # Convert hours to Decimal if needed
        if 'hours_worked' in kwargs and not isinstance(kwargs['hours_worked'], Decimal):
            kwargs['hours_worked'] = Decimal(str(kwargs['hours_worked']))
        
        params = CreateTimeEntryParams(**kwargs)
        result = create_time_entry_tool(params, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_timesheet_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_timesheet_tool"""
        db = kwargs.pop('db', None)
        
        # Set defaults
        kwargs.setdefault('employee_id', 1)
        
        # Handle date parameters
        if 'start_date' in kwargs and isinstance(kwargs['start_date'], str):
            kwargs['start_date'] = date.fromisoformat(kwargs['start_date'])
        if 'end_date' in kwargs and isinstance(kwargs['end_date'], str):
            kwargs['end_date'] = date.fromisoformat(kwargs['end_date'])
        
        # Default to current week if no dates provided
        if 'start_date' not in kwargs or 'end_date' not in kwargs:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            kwargs.setdefault('start_date', start_date)
            kwargs.setdefault('end_date', end_date)
        
        result = get_timesheet_tool(
            employee_id=kwargs['employee_id'],
            start_date=kwargs['start_date'],
            end_date=kwargs['end_date'],
            db=db
        )
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
                    "name": "log_time_for_project",
                    "description": "Log time for a project by project name - automatically finds client and contract information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project or deliverable to log time for"
                            },
                            "hours_worked": {
                                "type": "number",
                                "description": "Number of hours worked (can be decimal like 2.5)"
                            },
                            "description_of_work": {
                                "type": "string",
                                "description": "Description of the work performed"
                            },
                            "employee_id": {
                                "type": "integer",
                                "description": "ID of the employee logging time",
                                "default": 1
                            },
                            "date": {
                                "type": "string",
                                "description": "Date of work in YYYY-MM-DD format (defaults to today)"
                            },
                            "billable": {
                                "type": "boolean",
                                "description": "Whether this time is billable to the client",
                                "default": True
                            }
                        },
                        "required": ["project_name", "hours_worked", "description_of_work"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_projects",
                    "description": "Search for available projects/deliverables by name or description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term to find projects (project name, client name, or keywords)"
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_timesheet",
                    "description": "Retrieve timesheet data for a specific employee and date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {
                                "type": "integer",
                                "description": "ID of the employee",
                                "default": 1
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date for timesheet in YYYY-MM-DD format"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date for timesheet in YYYY-MM-DD format"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message through Milo using OpenAI function calling"""
        try:
            enhanced_context = {
                **context,
                "agent_type": "time_tracking",
                "capabilities": ["time_logging", "productivity_analysis", "timesheet_generation"]
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
            
            # Process through OpenAI with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",  # Let the LLM decide which tools to use
                temperature=0.7,
                max_tokens=1000
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
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
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
            "description": "Time and productivity management specialist",
            "capabilities": [
                "Log time entries for projects",
                "Generate timesheets and reports",
                "Track billable vs non-billable hours",
                "Analyze productivity patterns",
                "Validate time entry compliance"
            ],
            "tools": list(self.tool_functions.keys())
        }
