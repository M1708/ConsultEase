from openai import OpenAI
from typing import Dict, Any, List, Callable
from backend.src.aiagents.prompts import EmployeePrompts
from backend.src.aiagents.tools.employee_tools import (
    create_employee_tool, update_employee_tool, search_employees_tool,
    get_employee_details_tool, get_all_employees_tool, search_profiles_by_name_tool,
    CreateEmployeeParams, UpdateEmployeeParams, EmployeeToolResult
)
from backend.src.database.core.models import User, Employee
from backend.src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from backend.src.aiagents.guardrails.output_guardrails import output_validation_guardrail
import json
import os

class EmployeeAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = "Milo"
        self.instructions = EmployeePrompts.SYSTEM_INSTRUCTIONS
        self.model = "gpt-4o-mini"
        
        # Dynamic tool mapping - no hardcoded if-else logic
        self.tool_functions = {
            "create_employee": self._create_employee_wrapper,
            "update_employee": self._update_employee_wrapper,
            "search_employees": self._search_employees_wrapper,
            "get_employee_details": self._get_employee_details_wrapper,
            "get_all_employees": self._get_all_employees_wrapper,
            "search_profiles_by_name": self._search_profiles_by_name_wrapper,
            "check_employee_exists": self._check_employee_exists_wrapper
        }
        
        self.tools = self._get_tool_schemas()
    
    def _create_employee_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for create_employee_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = CreateEmployeeParams(**kwargs)
        result = create_employee_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _update_employee_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for update_employee_tool"""
        db = kwargs.pop('db', None)
        context = kwargs.pop('context', None)
        params = UpdateEmployeeParams(**kwargs)
        result = update_employee_tool(params, context, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _search_employees_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for search_employees_tool"""
        db = kwargs.pop('db', None)
        search_term = kwargs.get("search_term")
        limit = kwargs.get("limit", 50)
        result = search_employees_tool(search_term, limit, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_employee_details_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_employee_details_tool"""
        db = kwargs.pop('db', None)
        employee_id = kwargs.get("employee_id")
        result = get_employee_details_tool(employee_id, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _get_all_employees_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for get_all_employees_tool"""
        db = kwargs.pop('db', None)
        result = get_all_employees_tool(db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _search_profiles_by_name_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for search_profiles_by_name_tool"""
        db = kwargs.pop('db', None)
        search_term = kwargs.get("search_term")
        result = search_profiles_by_name_tool(search_term, db)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
    
    def _check_employee_exists_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for check_employee_exists_tool"""
        db = kwargs.pop('db', None)
        profile_id = kwargs.get("profile_id")
        result = check_employee_exists_tool(profile_id, db)
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
                    "name": "create_employee",
                    "description": "Create a new employee record in the HR system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "profile_id": {
                                "type": "string",
                                "description": "UUID of the user profile this employee record belongs to"
                            },
                            "employee_number": {
                                "type": "string",
                                "description": "Optional unique employee ID number"
                            },
                            "job_title": {
                                "type": "string",
                                "description": "Job title or position"
                            },
                            "department": {
                                "type": "string",
                                "description": "Department or division"
                            },
                            "employment_type": {
                                "type": "string",
                                "description": "Type of employment: permanent, contract, intern, or consultant",
                                "enum": ["permanent", "contract", "intern", "consultant"]
                            },
                            "full_time_part_time": {
                                "type": "string",
                                "description": "Work schedule: full_time or part_time",
                                "enum": ["full_time", "part_time"]
                            },
                            "committed_hours": {
                                "type": "integer",
                                "description": "Hours per week/month the employee is committed to work"
                            },
                            "hire_date": {
                                "type": "string",
                                "description": "Date when employee was hired (YYYY-MM-DD format)"
                            },
                            "termination_date": {
                                "type": "string",
                                "description": "Date when employment ended (YYYY-MM-DD format)"
                            },
                            "rate_type": {
                                "type": "string",
                                "description": "Type of compensation: hourly, salary, or project_based",
                                "enum": ["hourly", "salary", "project_based"]
                            },
                            "rate": {
                                "type": "number",
                                "description": "Compensation rate (hourly rate, annual salary, or project amount)"
                            },
                            "currency": {
                                "type": "string",
                                "description": "Currency for compensation (default: USD)"
                            },
                            "nda_file_link": {
                                "type": "string",
                                "description": "Link to NDA document file"
                            },
                            "contract_file_link": {
                                "type": "string",
                                "description": "Link to employment contract document file"
                            }
                        },
                        "required": ["profile_id", "employment_type", "full_time_part_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_employee",
                    "description": "Update an existing employee's information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {
                                "type": "integer",
                                "description": "ID of the employee to update"
                            },
                            "employee_number": {
                                "type": "string",
                                "description": "New employee ID number"
                            },
                            "job_title": {
                                "type": "string",
                                "description": "New job title"
                            },
                            "department": {
                                "type": "string",
                                "description": "New department"
                            },
                            "employment_type": {
                                "type": "string",
                                "description": "New employment type",
                                "enum": ["permanent", "contract", "intern", "consultant"]
                            },
                            "full_time_part_time": {
                                "type": "string",
                                "description": "New work schedule",
                                "enum": ["full_time", "part_time"]
                            },
                            "committed_hours": {
                                "type": "integer",
                                "description": "New committed hours"
                            },
                            "hire_date": {
                                "type": "string",
                                "description": "New hire date (YYYY-MM-DD format)"
                            },
                            "termination_date": {
                                "type": "string",
                                "description": "New termination date (YYYY-MM-DD format)"
                            },
                            "rate_type": {
                                "type": "string",
                                "description": "New rate type",
                                "enum": ["hourly", "salary", "project_based"]
                            },
                            "rate": {
                                "type": "number",
                                "description": "New compensation rate"
                            },
                            "currency": {
                                "type": "string",
                                "description": "New currency"
                            },
                            "nda_file_link": {
                                "type": "string",
                                "description": "New NDA file link"
                            },
                            "contract_file_link": {
                                "type": "string",
                                "description": "New contract file link"
                            }
                        },
                        "required": ["employee_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_employees",
                    "description": "Search for employees by name, job title, department, or employee number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term to find employees"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_employee_details",
                    "description": "Get comprehensive details for a specific employee",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {
                                "type": "integer",
                                "description": "ID of the employee to get details for"
                            }
                        },
                        "required": ["employee_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_employees",
                    "description": "Get a list of all employees in the system with basic information",
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
                    "name": "search_profiles_by_name",
                    "description": "Search for user profiles by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term to find user profiles"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_employee_exists",
                    "description": "Check if an employee with the given profile_id already exists.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "profile_id": {
                                "type": "string",
                                "description": "UUID of the user profile to check for employee existence"
                            }
                        },
                        "required": ["profile_id"]
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
                "agent_type": "employee",
                "capabilities": ["employee_management", "hr_operations", "compensation_tracking"]
            }
            
            # Apply input guardrails
            sanitized_message = input_sanitization_guardrail(message)
            
            # Check if this is an employee creation request
            if self._is_employee_creation_request(sanitized_message):
                return await self._handle_employee_creation_workflow(sanitized_message, enhanced_context)
            
            # Check if this is an employee search request (MUST come before show all)
            if self._is_employee_search_request(sanitized_message):
                return await self._handle_employee_search_workflow(sanitized_message, enhanced_context)
            
            # Check if this is a "show all employees" request
            if self._is_show_all_employees_request(sanitized_message):
                return await self._handle_show_all_employees_workflow(sanitized_message, enhanced_context)
            
            # Check if this is an employee update request
            if self._is_employee_update_request(sanitized_message):
                return await self._handle_employee_update_workflow(sanitized_message, enhanced_context)
            
            # Prepare context without database session for JSON serialization
            json_safe_context = {k: v for k, v in enhanced_context.items() if k != "database"}
            
            # Prepare messages for OpenAI with function calling
            messages = [
                {"role": "system", "content": self.instructions},
            ]
            
            # Add conversation history if available for context
            if "conversation_history" in enhanced_context and enhanced_context["conversation_history"]:
                messages.extend(enhanced_context["conversation_history"][-5:])  # Last 5 messages
            
            # Add user message
            messages.append({"role": "user", "content": sanitized_message})
            
            # First attempt with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=500
            )
            
            response_message = response.choices[0].message
            
            # Check if tool calls were made
            if response_message.tool_calls:
                print(f"🔍 EmployeeAgent: Tool calls detected: {len(response_message.tool_calls)}")
                
                # Execute tool calls
                tool_results = []
                tool_calls = response_message.tool_calls
                for tool_call in tool_calls:
                    result = await self._execute_tool_call(tool_call, enhanced_context)
                    tool_results.append(result)
                
                # Get final response from LLM after tool execution
                messages.append(response_message)
                
                # Add tool results to messages with proper tool_call_id
                for i, tool_call in enumerate(tool_calls):
                    if i < len(tool_results):
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,  # Use the correct tool_call_id
                            "name": tool_call.function.name,
                            "content": json.dumps(tool_results[i])
                        })
                
                # Get final response from LLM after tool execution
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
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
                print(f"🔍 EmployeeAgent: No tool calls found in response")
                print(f"🔍 EmployeeAgent: Response content: {response_message.content}")
                
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
            print(f"🔍 EmployeeAgent: Exception occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "agent": "Milo",
                "response": f"❌ Error processing request: {str(e)}",
                "success": False
            }
    
    async def _execute_tool_call(self, tool_call, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call made by the LLM"""
        try:
            function_name = tool_call.function.name
            print(f"🔧 EmployeeAgent._execute_tool_call: Function name: {function_name}")
            
            # Better JSON parsing with error handling
            try:
                function_args = json.loads(tool_call.function.arguments)
                print(f"🔧 EmployeeAgent._execute_tool_call: Parsed args: {function_args}")
            except json.JSONDecodeError as json_error:
                print(f"🔧 EmployeeAgent._execute_tool_call: JSON decode error: {json_error}")
                return {
                    "success": False,
                    "message": f"Invalid JSON in function arguments: {str(json_error)}. Arguments: {tool_call.function.arguments}",
                    "data": None
                }
            
            # Get the database session from context
            db = context.get("database")
            print(f"🔧 EmployeeAgent._execute_tool_call: Database session: {db is not None}")
            function_args['db'] = db
            
            # Add context to function args for tools that need user_id
            function_args['context'] = context
            
            # Dynamically call the appropriate tool function
            if function_name in self.tool_functions:
                print(f"🔧 EmployeeAgent._execute_tool_call: Calling tool function: {function_name}")
                result = self.tool_functions[function_name](**function_args)
                print(f"🔧 EmployeeAgent._execute_tool_call: Tool function result: {result}")
                return result
            else:
                print(f"🔧 EmployeeAgent._execute_tool_call: Unknown function: {function_name}")
                print(f"🔧 EmployeeAgent._execute_tool_call: Available functions: {list(self.tool_functions.keys())}")
                return {
                    "success": False,
                    "message": f"Unknown function: {function_name}",
                    "data": None
                }
                
        except Exception as e:
            print(f"🔧 EmployeeAgent._execute_tool_call: Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error executing tool {tool_call.function.name}: {str(e)}",
                "data": None
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "Milo",
            "description": "Human resources and employee management specialist",
            "capabilities": [
                "Create and manage employee records",
                "Update employee information and status",
                "Search and retrieve employee details",
                "Manage employment types and compensation",
                "Handle employee onboarding and offboarding"
            ],
            "tools": list(self.tool_functions.keys())
        }
    
    def _is_employee_creation_request(self, message: str) -> bool:
        """Check if the message is requesting employee creation"""
        message_lower = message.lower()
        creation_keywords = [
            "create", "add", "new", "employee record", "hire", "onboard"
        ]
        # Must contain creation keywords AND NOT contain "show", "list", "get", "display", "see"
        show_keywords = ["show", "list", "get", "display", "see"]
        has_creation = any(keyword in message_lower for keyword in creation_keywords)
        has_show = any(keyword in message_lower for keyword in show_keywords)
        return has_creation and not has_show
    
    def _is_show_all_employees_request(self, message: str) -> bool:
        """Check if the message is requesting to show all employees"""
        message_lower = message.lower()
        
        # Must be exactly "show me all employees" or similar generic requests
        exact_matches = [
            "show me all employees",
            "show all employees", 
            "list all employees",
            "get all employees",
            "display all employees",
            "see all employees",
            "show employees",
            "list employees",
            "get employees"
        ]
        
        # Check for exact matches first
        if message_lower.strip() in exact_matches:
            return True
        
        # Check for generic patterns that don't have specific filters
        show_keywords = ["show me all", "show all", "list all", "get all", "display all", "see all"]
        employee_keywords = ["employees", "employee", "staff", "personnel"]
        
        has_show = any(keyword in message_lower for keyword in show_keywords)
        has_employee = any(keyword in message_lower for keyword in employee_keywords)
        
        # Must NOT contain specific filter keywords
        filter_keywords = [
            "part-time", "part time", "full-time", "full time", "permanent", "contract", "intern", "consultant",
            "engineering", "research", "marketing", "sales", "hr", "human resources", "finance", "it",
            "software engineer", "analyst", "manager", "consultant", "developer"
        ]
        has_specific_filter = any(keyword in message_lower for keyword in filter_keywords)
        
        return has_show and has_employee and not has_specific_filter
    
    def _is_employee_update_request(self, message: str) -> bool:
        """Check if the message is requesting employee updates"""
        message_lower = message.lower()
        update_keywords = [
            "update", "change", "modify", "edit", "set"
        ]
        employee_keywords = [
            "employee", "record", "job title", "department", "employment", "schedule"
        ]
        # Must contain update keywords AND employee-related keywords
        has_update = any(keyword in message_lower for keyword in update_keywords)
        has_employee = any(keyword in message_lower for keyword in employee_keywords)
        return has_update and has_employee
    
    def _is_employee_search_request(self, message: str) -> bool:
        """Check if the message is requesting employee search/filtering"""
        message_lower = message.lower()
        
        # Must contain search keywords
        search_keywords = [
            "show me all", "show all", "list all", "get all", "display all", "see all", "find", "search"
        ]
        has_search = any(keyword in message_lower for keyword in search_keywords)
        
        # Must contain specific filter keywords (not just "employees")
        filter_keywords = [
            "part-time", "part time", "full-time", "full time", "permanent", "contract", "intern", "consultant",
            "engineering", "research", "marketing", "sales", "hr", "human resources", "finance", "it",
            "software engineer", "analyst", "manager", "consultant", "developer",
            "salary", "hourly", "daily", "weekly", "monthly", "rate", "compensation"
        ]
        has_specific_filter = any(keyword in message_lower for keyword in filter_keywords)
        
        # Must NOT be just "show me all employees" (that's handled by show all workflow)
        is_generic_show_all = (
            message_lower.strip() in ["show me all employees", "show all employees", "list all employees", "get all employees", "display all employees", "see all employees"]
        )
        
        return has_search and has_specific_filter and not is_generic_show_all
    
    async def _handle_employee_creation_workflow(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle employee creation workflow with forced sequential tool calls"""
        try:
            print(f"🔧 EmployeeAgent: Starting employee creation workflow for: {message}")
            
            # Extract employee details from message
            employee_details = self._extract_employee_details(message)
            
            # Step 1: Search for profile
            print(f"🔧 EmployeeAgent: Step 1 - Searching for profile: {employee_details.get('name', 'Unknown')}")
            profile_result = await self._execute_profile_search(employee_details.get('name', ''), context)
            
            if not profile_result.get('success'):
                return {
                    "agent": "Milo",
                    "response": profile_result.get('message', '❌ Failed to find user profile'),
                    "success": False
                }
            
            # Extract profile_id from the result
            profile_data = profile_result.get('data', {})
            profiles = profile_data.get('profiles', [])
            
            if not profiles:
                return {
                    "agent": "Milo",
                    "response": "❌ No user profile found. Please create a user profile first before creating an employee record.",
                    "success": False
                }
            
            profile_id = profiles[0].get('profile_id')
            print(f"🔧 EmployeeAgent: Found profile_id: {profile_id}")
            
            # Step 1.5: Check if employee already exists
            print(f"🔧 EmployeeAgent: Step 1.5 - Checking if employee already exists")
            employee_exists_result = await self._check_employee_exists(profile_id, context)
            
            if employee_exists_result.get('success') and employee_exists_result.get('data', {}).get('exists'):
                # Employee already exists, return information about existing record
                existing_employee = employee_exists_result.get('data', {}).get('employee', {})
                return {
                    "agent": "Milo",
                    "response": self._create_existing_employee_response(existing_employee),
                    "success": True,
                    "data": existing_employee
                }
            
            # Step 2: Create employee
            print(f"🔧 EmployeeAgent: Step 2 - Creating employee with profile_id: {profile_id}")
            employee_result = await self._execute_employee_creation(profile_id, employee_details, context)
            
            if employee_result.get('success'):
                # Create a user-friendly response without exposing sensitive information
                user_response = self._create_user_friendly_response(employee_details, employee_result)
                return {
                    "agent": "Milo",
                    "response": user_response,
                    "success": True,
                    "data": employee_result.get('data')
                }
            else:
                return {
                    "agent": "Milo",
                    "response": f"❌ Failed to create employee record: {employee_result.get('message', 'Unknown error')}",
                    "success": False
                }
                
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error in employee creation workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "agent": "Milo",
                "response": f"❌ Error in employee creation workflow: {str(e)}",
                "success": False
            }
    
    async def _handle_show_all_employees_workflow(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle show all employees workflow"""
        try:
            print(f"🔧 EmployeeAgent: Handling show all employees request")
            
            # Get database session from context
            db = context.get("database")
            
            # Call the get_all_employees tool directly
            from backend.src.aiagents.tools.employee_tools import get_all_employees_tool
            result = get_all_employees_tool(db)
            
            if result.success:
                employees = result.data.get("employees", [])
                if employees:
                    response = f"📋 Found {len(employees)} employee(s) in the system:\n\n"
                    
                    for i, emp in enumerate(employees, 1):
                        # Get profile information for the employee
                        profile = emp.get("profile", {})
                        first_name = profile.get("first_name", "Unknown")
                        last_name = profile.get("last_name", "Unknown")
                        full_name = f"{first_name} {last_name}".strip()
                        
                        response += f"**{i}. {full_name}**\n"
                        response += f"   - **Job Title**: {emp.get('job_title', 'N/A')}\n"
                        response += f"   - **Department**: {emp.get('department', 'N/A')}\n"
                        response += f"   - **Employment Type**: {emp.get('employment_type', 'N/A').title()}\n"
                        response += f"   - **Work Schedule**: {emp.get('full_time_part_time', 'N/A').replace('_', '-').title()}\n"
                        response += f"   - **Hire Date**: {emp.get('hire_date', 'N/A')}\n"
                        response += f"   - **Status**: {'Active' if not emp.get('termination_date') else 'Terminated'}\n\n"
                else:
                    response = "📋 No employees found in the system."
                
                return {
                    "agent": "Milo",
                    "response": response,
                    "success": True,
                    "data": result.data
                }
            else:
                return {
                    "agent": "Milo",
                    "response": f"❌ Failed to retrieve employees: {result.message}",
                    "success": False,
                    "data": None
                }
                
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error in show all employees workflow: {str(e)}")
            return {
                "agent": "Milo",
                "response": f"❌ Error retrieving employees: {str(e)}",
                "success": False,
                "data": None
            }
    
    async def _handle_employee_update_workflow(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle employee update workflow"""
        try:
            print(f"🔧 EmployeeAgent: Handling employee update request")
            
            # Extract employee details from the message
            employee_details = self._extract_employee_update_details(message)
            
            if not employee_details.get('name'):
                return {
                    "agent": "Milo",
                    "response": "❌ Please specify which employee you want to update. For example: 'Update Sarah Miles job title to Senior Analyst'",
                    "success": False,
                    "data": None
                }
            
            # Get database session from context
            db = context.get("database")
            
            # Step 1: Search for the user profile by name first
            from backend.src.aiagents.tools.employee_tools import search_profiles_by_name_tool
            profile_search_result = search_profiles_by_name_tool(employee_details['name'], db)
            
            if not profile_search_result.success or not profile_search_result.data.get("profiles"):
                return {
                    "agent": "Milo",
                    "response": f"⚠️ Warning: No user profile found for '{employee_details['name']}'.\n\nPlease check the name or create a user profile first before updating employee records.",
                    "success": False,
                    "data": None
                }
            
            profiles = profile_search_result.data["profiles"]
            
            # Step 2: Find the best profile match (exact name match first)
            target_profile = None
            for profile in profiles:
                profile_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
                if profile_name.lower() == employee_details['name'].lower():
                    target_profile = profile
                    break
            
            # If no exact match, use the first result
            if not target_profile and profiles:
                target_profile = profiles[0]
            
            if not target_profile:
                return {
                    "agent": "Milo",
                    "response": f"❌ Could not find a matching user profile for '{employee_details['name']}'.",
                    "success": False,
                    "data": None
                }
            
            profile_id = target_profile['profile_id']
            print(f"🔧 EmployeeAgent: Found profile for {employee_details['name']}")
            
            # Step 3: Search for employee record using the profile ID
            # Direct database query instead of using search tool
            from backend.src.database.core.models import Employee
            target_employee = db.query(Employee).filter(Employee.profile_id == profile_id).first()
            
            if not target_employee:
                return {
                    "agent": "Milo",
                    "response": f"⚠️ Warning: No employee record found for '{employee_details['name']}'.\n\nThis user has a profile but no employee record. Please create an employee record first.",
                    "success": False,
                    "data": None
                }
            
            print(f"🔧 EmployeeAgent: Found employee record for {employee_details['name']}")
            
            # Step 4: Prepare update parameters
            from backend.src.aiagents.tools.employee_tools import update_employee_tool, UpdateEmployeeParams
            
            update_params = UpdateEmployeeParams(
                employee_id=target_employee.employee_id
            )
            
            # Update only the fields that were specified in the message
            if employee_details.get('job_title'):
                update_params.job_title = employee_details['job_title']
            if employee_details.get('department'):
                update_params.department = employee_details['department']
            if employee_details.get('employment_type'):
                update_params.employment_type = employee_details['employment_type']
            if employee_details.get('full_time_part_time'):
                update_params.full_time_part_time = employee_details['full_time_part_time']
            if employee_details.get('rate_type'):
                update_params.rate_type = employee_details['rate_type']
            if employee_details.get('rate'):
                update_params.rate = employee_details['rate']
            if employee_details.get('currency'):
                update_params.currency = employee_details['currency']
            
            # Step 6: Execute the update
            update_result = update_employee_tool(update_params, context, db)
            
            if update_result.success:
                # Get updated employee details from the database
                updated_employee = db.query(Employee).filter(Employee.employee_id == target_employee.employee_id).first()
                if updated_employee:
                    profile = db.query(User).filter(User.user_id == updated_employee.profile_id).first()
                    full_name = f"{profile.first_name} {profile.last_name}".strip() if profile else employee_details['name']
                    
                    response = f"✅ Successfully updated employee record for {full_name}!\n\n"
                    response += f"**Updated Employee Details:**\n"
                    response += f"- **Name**: {full_name}\n"
                    response += f"- **Job Title**: {updated_employee.job_title or 'N/A'}\n"
                    response += f"- **Department**: {updated_employee.department or 'N/A'}\n"
                    response += f"- **Employment Type**: {updated_employee.employment_type.title() if updated_employee.employment_type else 'N/A'}\n"
                    response += f"- **Work Schedule**: {updated_employee.full_time_part_time.replace('_', '-').title() if updated_employee.full_time_part_time else 'N/A'}\n"
                    response += f"- **Hire Date**: {updated_employee.hire_date.strftime('%Y-%m-%d') if updated_employee.hire_date else 'N/A'}\n"
                    response += f"- **Status**: {'Active' if not updated_employee.termination_date else 'Terminated'}\n\n"
                    response += f"The employee record has been successfully updated in the database."
                else:
                    response = f"✅ Successfully updated employee record for {employee_details['name']}!\n\nThe employee record has been updated in the database."
                
                return {
                    "agent": "Milo",
                    "response": response,
                    "success": True,
                    "data": update_result.data
                }
            else:
                return {
                    "agent": "Milo",
                    "response": f"❌ Failed to update employee record: {update_result.message}",
                    "success": False,
                    "data": None
                }
                
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error in employee update workflow: {str(e)}")
            return {
                "agent": "Milo",
                "response": f"❌ Error updating employee: {str(e)}",
                "success": False,
                "data": None
            }
    
    def _extract_employee_details(self, message: str) -> Dict[str, Any]:
        """Extract employee details from the message"""
        message_lower = message.lower()
        
        details = {}
        
        # Extract name - look for patterns like "for [Name]" 
        import re
        
        # Pattern 1: "Create an employee record for [Name]" - stop at "as a" or "in the"
        name_match = re.search(r'for\s+([^,\n]+?)(?:\s+as\s+a|\s+in\s+the|$)', message_lower)
        if name_match:
            name = name_match.group(1).strip()
            # Clean up the name by removing extra words
            name_parts = name.split()
            if len(name_parts) >= 2:
                # Take first two parts as first and last name
                details['name'] = f"{name_parts[0].title()} {name_parts[1].title()}"
            else:
                details['name'] = name.title()
        
        # Pattern 2: Look for specific names if pattern 1 fails
        if 'name' not in details:
            if "john doe" in message_lower:
                details['name'] = "John Doe"
            elif "jane doe" in message_lower:
                details['name'] = "Jane Doe"
            elif "sarah miles" in message_lower:
                details['name'] = "Sarah Miles"
        
        # Extract employment type
        if "permanent" in message_lower:
            details['employment_type'] = "permanent"
        elif "contract" in message_lower:
            details['employment_type'] = "contract"
        elif "intern" in message_lower:
            details['employment_type'] = "intern"
        elif "consultant" in message_lower:
            details['employment_type'] = "consultant"
        
        # Extract full time/part time
        if "full-time" in message_lower or "full time" in message_lower:
            details['full_time_part_time'] = "full_time"
        elif "part-time" in message_lower or "part time" in message_lower:
            details['full_time_part_time'] = "part_time"
        
        # Extract job title - look for "as a [job title]" pattern
        # Handle different patterns like "as a analyst", "as a permanent analyst", "as a full-time analyst"
        job_title_patterns = [
            r'as\s+a\s+(?:permanent\s+)?(?:full-time\s+)?(?:part-time\s+)?([^,\n]+?)(?:\s+in\s+the|$)',
            r'as\s+a\s+(?:contract\s+)?([^,\n]+?)(?:\s+in\s+the|$)',
            r'as\s+a\s+([^,\n]+?)(?:\s+in\s+the|$)'
        ]
        
        job_title_found = False
        for pattern in job_title_patterns:
            job_title_match = re.search(pattern, message_lower)
            if job_title_match:
                job_title = job_title_match.group(1).strip()
                # Clean up job title by removing employment type and work schedule words
                job_title_clean = re.sub(r'\b(permanent|contract|full-time|part-time|full time|part time)\b', '', job_title).strip()
                if job_title_clean:
                    details['job_title'] = job_title_clean.title()
                    job_title_found = True
                    break
        
        if not job_title_found:
            # Fallback to keyword matching
            if "software engineer" in message_lower:
                details['job_title'] = "Software Engineer"
            elif "developer" in message_lower:
                details['job_title'] = "Developer"
            elif "manager" in message_lower:
                details['job_title'] = "Manager"
            elif "analyst" in message_lower:
                details['job_title'] = "Analyst"
            elif "consultant" in message_lower:
                details['job_title'] = "Consultant"
            elif "coordinator" in message_lower:
                details['job_title'] = "Coordinator"
            elif "specialist" in message_lower:
                details['job_title'] = "Specialist"
            elif "assistant" in message_lower:
                details['job_title'] = "Assistant"
            elif "director" in message_lower:
                details['job_title'] = "Director"
            elif "supervisor" in message_lower:
                details['job_title'] = "Supervisor"
        
        # Extract department - look for "in the [department]" pattern
        department_match = re.search(r'in\s+the\s+([^,\n]+?)(?:\s+permanent|\s+full-time|\s+part-time|$)', message_lower)
        if department_match:
            department = department_match.group(1).strip()
            # Clean up department by removing employment type and work schedule words
            department_clean = re.sub(r'\b(permanent|contract|full-time|part-time|full time|part time)\b', '', department).strip()
            if department_clean:
                details['department'] = department_clean.title()
            else:
                details['department'] = department.title()
        else:
            # Fallback to keyword matching
            if "engineering" in message_lower:
                details['department'] = "Engineering"
            elif "marketing" in message_lower:
                details['department'] = "Marketing"
            elif "sales" in message_lower:
                details['department'] = "Sales"
            elif "hr" in message_lower or "human resources" in message_lower:
                details['department'] = "Human Resources"
            elif "research" in message_lower:
                details['department'] = "Research"
            elif "finance" in message_lower:
                details['department'] = "Finance"
            elif "operations" in message_lower:
                details['department'] = "Operations"
            elif "it" in message_lower or "information technology" in message_lower:
                details['department'] = "Information Technology"
            elif "legal" in message_lower:
                details['department'] = "Legal"
            elif "customer service" in message_lower:
                details['department'] = "Customer Service"
        
        return details
    
    def _extract_employee_update_details(self, message: str) -> Dict[str, Any]:
        """Extract employee update details from the message"""
        message_lower = message.lower()
        
        details = {}
        
        # Extract name - look for patterns like "Sarah Miles" or "Sarah"
        import re
        
        # Pattern 1: Look for names in quotes or specific name patterns
        name_patterns = [
            r'"([^"]+)"',  # Names in quotes
            r'for\s+([^,\n]+?)(?:\s+job-title|\s+department|\s+employment|\s+schedule|$)',  # "for [Name]"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # First Last pattern
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, message)
            if name_match:
                name = name_match.group(1).strip()
                # Clean up the name
                name_parts = name.split()
                if len(name_parts) >= 2:
                    details['name'] = f"{name_parts[0].title()} {name_parts[1].title()}"
                    break
                else:
                    details['name'] = name.title()
                    break
        
        # If no name found, try to extract from the message
        if 'name' not in details:
            if "sarah miles" in message_lower:
                details['name'] = "Sarah Miles"
            elif "john doe" in message_lower:
                details['name'] = "John Doe"
            elif "jane doe" in message_lower:
                details['name'] = "Jane Doe"
        
        # Extract job title updates
        if "job-title" in message_lower or "job title" in message_lower:
            # Look for "job-title is [title]" or "job title is [title]"
            job_title_match = re.search(r'job-title?\s+is\s+([^,\n]+?)(?:\s+and|\s+she|\s+he|\s+in|\s+department|$)', message_lower)
            if job_title_match:
                job_title = job_title_match.group(1).strip()
                details['job_title'] = job_title.title()
        
        # Extract department updates
        if "department" in message_lower:
            # Look for "in the [department]" or "department is [department]"
            dept_patterns = [
                r'in\s+the\s+([^,\n]+?)(?:\s+department|$)',
                r'department\s+is\s+([^,\n]+?)(?:\s+and|\s+she|\s+he|$)',
            ]
            for pattern in dept_patterns:
                dept_match = re.search(pattern, message_lower)
                if dept_match:
                    department = dept_match.group(1).strip()
                    details['department'] = department.title()
                    break
        
        # Extract employment type updates
        if "employment type" in message_lower or "employment" in message_lower:
            if "permanent" in message_lower:
                details['employment_type'] = "permanent"
            elif "contract" in message_lower:
                details['employment_type'] = "contract"
            elif "intern" in message_lower:
                details['employment_type'] = "intern"
            elif "consultant" in message_lower:
                details['employment_type'] = "consultant"
        
        # Extract work schedule updates
        if "full-time" in message_lower or "full time" in message_lower:
            details['full_time_part_time'] = "full_time"
        elif "part-time" in message_lower or "part time" in message_lower:
            details['full_time_part_time'] = "part_time"
        
        return details
    
    async def _execute_profile_search(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute profile search tool"""
        try:
            # Get database session from context
            db = context.get("database")
            
            # Call the tool directly
            from backend.src.aiagents.tools.employee_tools import search_profiles_by_name_tool
            result = search_profiles_by_name_tool(name, db)
            
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
            
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error executing profile search: {str(e)}")
            return {
                "success": False,
                "message": f"Error searching for profile: {str(e)}",
                "data": None
            }
    
    async def _check_employee_exists(self, profile_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if an employee with the given profile_id already exists."""
        try:
            # Get database session from context
            db = context.get("database")
            
            # Call the tool directly
            from backend.src.aiagents.tools.employee_tools import check_employee_exists_tool
            result = check_employee_exists_tool(profile_id, db)
            
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
            
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error checking employee existence: {str(e)}")
            return {
                "success": False,
                "message": f"Error checking employee existence: {str(e)}",
                "data": {}
            }

    async def _execute_employee_creation(self, profile_id: str, employee_details: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute employee creation tool"""
        try:
            # Get database session from context
            db = context.get("database")
            
            # Prepare employee creation parameters
            from backend.src.aiagents.tools.employee_tools import create_employee_tool, CreateEmployeeParams
            
            create_params = CreateEmployeeParams(
                profile_id=profile_id,
                employment_type=employee_details.get('employment_type', 'permanent'),
                full_time_part_time=employee_details.get('full_time_part_time', 'full_time'),
                job_title=employee_details.get('job_title'),
                department=employee_details.get('department'),
                hire_date=None,  # Will default to today in the tool
                currency="USD"
            )
            
            # Call the tool directly
            result = create_employee_tool(create_params, context, db)
            
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
            
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error executing employee creation: {str(e)}")
            return {
                "success": False,
                "message": f"Error creating employee: {str(e)}",
                "data": None
            }

    def _create_user_friendly_response(self, employee_details: Dict[str, Any], employee_result: Dict[str, Any]) -> str:
        """Create a user-friendly response without exposing sensitive information"""
        name = employee_details.get('name', 'the employee')
        job_title = employee_details.get('job_title', 'employee')
        department = employee_details.get('department', 'department')
        employment_type = employee_details.get('employment_type', 'employee')
        work_schedule = employee_details.get('full_time_part_time', 'employee')
        
        # Format employment type and work schedule for display
        employment_display = employment_type.title() if employment_type else 'Employee'
        schedule_display = 'Full-time' if work_schedule == 'full_time' else 'Part-time' if work_schedule == 'part_time' else work_schedule.title()
        
        response = f"✅ Successfully created employee record for {name}!\n\n"
        response += f"**Employee Details:**\n"
        response += f"- **Name**: {name}\n"
        response += f"- **Job Title**: {job_title}\n"
        response += f"- **Department**: {department}\n"
        response += f"- **Employment Type**: {employment_display}\n"
        response += f"- **Work Schedule**: {schedule_display}\n"
        response += f"- **Hire Date**: Today\n"
        response += f"- **Status**: Active\n\n"
        response += f"The employee record has been successfully created and is now active in the system."
        
        return response

    def _create_existing_employee_response(self, existing_employee: Dict[str, Any]) -> str:
        """Create a user-friendly response for an existing employee."""
        name = existing_employee.get('name', 'the employee')
        job_title = existing_employee.get('job_title', 'employee')
        department = existing_employee.get('department', 'department')
        employment_type = existing_employee.get('employment_type', 'employee')
        work_schedule = existing_employee.get('full_time_part_time', 'employee')

        # Format employment type and work schedule for display
        employment_display = employment_type.title() if employment_type else 'Employee'
        schedule_display = 'Full-time' if work_schedule == 'full_time' else 'Part-time' if work_schedule == 'part_time' else work_schedule.title()

        response = f"✅ Employee record for {name} already exists!\n\n"
        response += f"**Existing Employee Details:**\n"
        response += f"- **Name**: {name}\n"
        response += f"- **Job Title**: {job_title}\n"
        response += f"- **Department**: {department}\n"
        response += f"- **Employment Type**: {employment_display}\n"
        response += f"- **Work Schedule**: {schedule_display}\n"
        response += f"- **Hire Date**: {existing_employee.get('hire_date', 'N/A')}\n"
        response += f"- **Status**: {existing_employee.get('termination_date', 'Active')}\n\n"
        response += f"If you need to update any information for this employee, just let me know what changes you'd like to make."

        return response

    async def _handle_employee_search_workflow(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle employee search workflow with filtering"""
        try:
            print(f"🔧 EmployeeAgent: Handling employee search request")
            
            # Extract search criteria from the message
            search_criteria = self._extract_search_criteria(message)
            
            # Get database session from context
            db = context.get("database")
            
            # Build the query with filters
            query = db.query(Employee).join(User, Employee.profile_id == User.user_id)
            
            # Apply filters based on search criteria
            if search_criteria.get('work_schedule'):
                if search_criteria['work_schedule'] == 'part_time':
                    query = query.filter(Employee.full_time_part_time == 'part_time')
                elif search_criteria['work_schedule'] == 'full_time':
                    query = query.filter(Employee.full_time_part_time == 'full_time')
            
            if search_criteria.get('employment_type'):
                query = query.filter(Employee.employment_type == search_criteria['employment_type'])
            
            if search_criteria.get('department'):
                query = query.filter(Employee.department.ilike(f"%{search_criteria['department']}%"))
            
            if search_criteria.get('job_title'):
                query = query.filter(Employee.job_title.ilike(f"%{search_criteria['job_title']}%"))
            
            # Add rate type filtering
            if search_criteria.get('rate_type'):
                query = query.filter(Employee.rate_type == search_criteria['rate_type'])
            
            # Add rate amount range filtering
            if search_criteria.get('rate_gt'):
                query = query.filter(Employee.rate > search_criteria['rate_gt'])
            if search_criteria.get('rate_lt'):
                query = query.filter(Employee.rate < search_criteria['rate_lt'])
            if search_criteria.get('rate_gte'):
                query = query.filter(Employee.rate >= search_criteria['rate_gte'])
            if search_criteria.get('rate_lte'):
                query = query.filter(Employee.rate <= search_criteria['rate_lte'])
            
            # Add committed hours range filtering
            if search_criteria.get('hours_gt'):
                query = query.filter(Employee.committed_hours > search_criteria['hours_gt'])
            if search_criteria.get('hours_lt'):
                query = query.filter(Employee.committed_hours < search_criteria['hours_lt'])
            if search_criteria.get('hours_gte'):
                query = query.filter(Employee.committed_hours >= search_criteria['hours_gte'])
            if search_criteria.get('hours_lte'):
                query = query.filter(Employee.committed_hours <= search_criteria['hours_lte'])
            
            # Add hire date filtering
            if search_criteria.get('hire_year'):
                from datetime import datetime
                year = int(search_criteria['hire_year'])
                query = query.filter(
                    (Employee.hire_date >= datetime(year, 1, 1).date()) &
                    (Employee.hire_date <= datetime(year, 12, 31).date())
                )
            
            if search_criteria.get('hire_after'):
                from datetime import datetime
                import calendar
                date_str = search_criteria['hire_after']
                # Simple month parsing - can be enhanced
                month_names = {month.lower(): i for i, month in enumerate(calendar.month_name) if month}
                for month_name, month_num in month_names.items():
                    if month_name in date_str.lower():
                        year = int(re.search(r'\d{4}', date_str).group())
                        query = query.filter(Employee.hire_date > datetime(year, month_num, 1).date())
                        break
            
            if search_criteria.get('hire_before'):
                from datetime import datetime
                import calendar
                date_str = search_criteria['hire_before']
                month_names = {month.lower(): i for i, month in enumerate(calendar.month_name) if month}
                for month_name, month_num in month_names.items():
                    if month_name in date_str.lower():
                        year = int(re.search(r'\d{4}', date_str).group())
                        query = query.filter(Employee.hire_date < datetime(year, month_num, 1).date())
                        break
            
            # Add status filtering (active/terminated)
            if search_criteria.get('status') == 'active':
                query = query.filter(Employee.termination_date.is_(None))
            elif search_criteria.get('status') == 'terminated':
                query = query.filter(Employee.termination_date.isnot(None))
            
            # Add currency filtering
            if search_criteria.get('currency'):
                query = query.filter(Employee.currency == search_criteria['currency'])
            
            # Add document availability filtering
            if search_criteria.get('has_nda') is True:
                query = query.filter(Employee.nda_file_link.isnot(None))
            elif search_criteria.get('has_nda') is False:
                query = query.filter(Employee.nda_file_link.is_(None))
                
            if search_criteria.get('has_contract') is True:
                query = query.filter(Employee.contract_file_link.isnot(None))
            elif search_criteria.get('has_contract') is False:
                query = query.filter(Employee.contract_file_link.is_(None))
            
            # Execute the query
            employees = query.all()
            
            if not employees:
                # Try to provide helpful suggestions
                suggestions = []
                
                # Work schedule suggestions
                if search_criteria.get('work_schedule') == 'part_time':
                    suggestions.append("Try searching for 'full-time employees' instead")
                elif search_criteria.get('work_schedule') == 'full_time':
                    suggestions.append("Try searching for 'part-time employees' instead")
                
                # Rate type suggestions
                if search_criteria.get('rate_type') == 'salary':
                    suggestions.append("Try searching for 'hourly employees' instead")
                elif search_criteria.get('rate_type') == 'hourly':
                    suggestions.append("Try searching for 'salary employees' instead")
                
                # Rate amount suggestions
                if search_criteria.get('rate_gt'):
                    suggestions.append(f"Try lowering the rate threshold (e.g., 'employees with rate > ${search_criteria['rate_gt'] * 0.8:,.0f}')")
                if search_criteria.get('rate_lt'):
                    suggestions.append(f"Try increasing the rate threshold (e.g., 'employees with rate < ${search_criteria['rate_lt'] * 1.2:,.0f}')")
                
                # Hours suggestions
                if search_criteria.get('hours_gt'):
                    suggestions.append(f"Try lowering the hours threshold (e.g., 'employees working > {search_criteria['hours_gt'] - 5} hours/week')")
                if search_criteria.get('hours_lt'):
                    suggestions.append(f"Try increasing the hours threshold (e.g., 'employees working < {search_criteria['hours_lt'] + 5} hours/week')")
                
                # Department suggestions
                if search_criteria.get('department'):
                    suggestions.append("Try searching without department filter")
                
                # Job title suggestions
                if search_criteria.get('job_title'):
                    suggestions.append("Try searching without job title filter")
                
                # Status suggestions
                if search_criteria.get('status') == 'active':
                    suggestions.append("Try searching for 'all employees' to include terminated ones")
                elif search_criteria.get('status') == 'terminated':
                    suggestions.append("Try searching for 'active employees' instead")
                
                # Document suggestions
                if search_criteria.get('has_nda') is True:
                    suggestions.append("Try searching for 'employees without NDA' instead")
                elif search_criteria.get('has_nda') is False:
                    suggestions.append("Try searching for 'employees with NDA' instead")
                    
                if search_criteria.get('has_contract') is True:
                    suggestions.append("Try searching for 'employees without contracts' instead")
                elif search_criteria.get('has_contract') is False:
                    suggestions.append("Try searching for 'employees with contracts' instead")
                
                # General suggestions
                if len(search_criteria) > 2:
                    suggestions.append("Try reducing the number of search criteria")
                
                suggestion_text = f"\n\nSuggestions:\n" + "\n".join(f"- {s}" for s in suggestions) if suggestions else ""
                
                return {
                    "agent": "Milo",
                    "response": f"📋 No employees found matching your search criteria.{suggestion_text}",
                    "success": True,
                    "data": {"employees": [], "count": 0}
                }
            
            # Format results
            employee_list = []
            for emp in employees:
                # Get profile information for each employee
                profile = db.query(User).filter(User.user_id == emp.profile_id).first()
                
                employee_list.append({
                    "employee_id": emp.employee_id,
                    "profile_id": str(emp.profile_id),
                    "employee_number": emp.employee_number,
                    "job_title": emp.job_title,
                    "department": emp.department,
                    "employment_type": emp.employment_type,
                    "full_time_part_time": emp.full_time_part_time,
                    "committed_hours": emp.committed_hours,
                    "hire_date": str(emp.hire_date) if emp.hire_date else None,
                    "termination_date": str(emp.termination_date) if emp.termination_date else None,
                    "rate_type": emp.rate_type,
                    "rate": float(emp.rate) if emp.rate else None,
                    "currency": emp.currency,
                    "nda_file_link": emp.nda_file_link,
                    "contract_file_link": emp.contract_file_link,
                    "profile": {
                        "first_name": profile.first_name if profile else None,
                        "last_name": profile.last_name if profile else None,
                        "email": profile.email if profile else None,
                        "full_name": profile.full_name if profile else "Unknown"
                    } if profile else {
                        "first_name": None,
                        "last_name": None,
                        "email": None,
                        "full_name": "Unknown"
                    }
                })
            
            # Create response
            search_description = self._create_search_description(search_criteria)
            response = f"📋 {search_description}\n\n"
            
            for i, emp in enumerate(employee_list, 1):
                profile = emp.get("profile", {})
                full_name = profile.get("full_name", "Unknown")
                
                response += f"**{i}. {full_name}**\n"
                response += f"   - **Job Title**: {emp.get('job_title', 'N/A')}\n"
                response += f"   - **Department**: {emp.get('department', 'N/A')}\n"
                response += f"   - **Employment Type**: {emp.get('employment_type', 'N/A').title()}\n"
                response += f"   - **Work Schedule**: {emp.get('full_time_part_time', 'N/A').replace('_', '-').title()}\n"
                
                # Only show committed hours if not null
                if emp.get('committed_hours'):
                    response += f"   - **Committed Hours**: {emp.get('committed_hours')} hours/week\n"
                
                response += f"   - **Hire Date**: {emp.get('hire_date', 'N/A')}\n"
                
                # Only show termination date if not null
                if emp.get('termination_date'):
                    response += f"   - **Termination Date**: {emp.get('termination_date')}\n"
                
                response += f"   - **Status**: {'Active' if not emp.get('termination_date') else 'Terminated'}\n"
                
                # Only show rate information if not null
                if emp.get('rate_type'):
                    response += f"   - **Rate Type**: {emp.get('rate_type').replace('_', ' ').title()}\n"
                
                if emp.get('rate'):
                    currency = emp.get('currency', 'USD')
                    response += f"   - **Rate**: {emp.get('rate')} {currency}\n"
                
                # Only show file links if not null
                if emp.get('nda_file_link'):
                    response += f"   - **NDA File**: Available\n"
                
                if emp.get('contract_file_link'):
                    response += f"   - **Contract File**: Available\n"
                
                response += "\n"
            
            return {
                "agent": "Milo",
                "response": response,
                "success": True,
                "data": {
                    "employees": employee_list,
                    "count": len(employee_list),
                    "search_criteria": search_criteria
                }
            }
                
        except Exception as e:
            print(f"🔧 EmployeeAgent: Error in employee search workflow: {str(e)}")
            return {
                "agent": "Milo",
                "response": f"❌ Error searching employees: {str(e)}",
                "success": False,
                "data": None
            }

    def _extract_search_criteria(self, message: str) -> Dict[str, Any]:
        """Extract search criteria from the message"""
        message_lower = message.lower()
        
        criteria = {}
        
        # Extract work schedule
        if "part-time" in message_lower or "part time" in message_lower:
            criteria['work_schedule'] = 'part_time'
        elif "full-time" in message_lower or "full time" in message_lower:
            criteria['work_schedule'] = 'full_time'
        
        # Extract employment type
        if "permanent" in message_lower:
            criteria['employment_type'] = 'permanent'
        elif "contract" in message_lower:
            criteria['employment_type'] = 'contract'
        elif "intern" in message_lower:
            criteria['employment_type'] = 'intern'
        elif "consultant" in message_lower:
            criteria['employment_type'] = 'consultant'
        
        # Extract department
        if "engineering" in message_lower:
            criteria['department'] = 'Engineering'
        elif "research" in message_lower:
            criteria['department'] = 'Research'
        elif "marketing" in message_lower:
            criteria['department'] = 'Marketing'
        elif "sales" in message_lower:
            criteria['department'] = 'Sales'
        elif "hr" in message_lower or "human resources" in message_lower:
            criteria['department'] = 'Human Resources'
        elif "finance" in message_lower:
            criteria['department'] = 'Finance'
        elif "it" in message_lower or "information technology" in message_lower:
            criteria['department'] = 'Information Technology'
        
        # Extract job title
        if "software engineer" in message_lower:
            criteria['job_title'] = 'Software Engineer'
        elif "analyst" in message_lower:
            criteria['job_title'] = 'Analyst'
        elif "manager" in message_lower:
            criteria['job_title'] = 'Manager'
        elif "consultant" in message_lower:
            criteria['job_title'] = 'Consultant'
        elif "developer" in message_lower:
            criteria['job_title'] = 'Developer'
        
        # Extract rate type
        if "salary" in message_lower:
            criteria['rate_type'] = 'salary'
        elif "hourly" in message_lower:
            criteria['rate_type'] = 'hourly'
        elif "daily" in message_lower:
            criteria['rate_type'] = 'daily'
        elif "weekly" in message_lower:
            criteria['rate_type'] = 'weekly'
        elif "monthly" in message_lower:
            criteria['rate_type'] = 'monthly'
        
        # Extract rate amount ranges
        import re
        rate_patterns = [
            (r'rate\s*>\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_gt'),
            (r'rate\s*<\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_lt'),
            (r'rate\s*>=\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_gte'),
            (r'rate\s*<=\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_lte'),
            (r'salary\s*>\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_gt'),
            (r'salary\s*<\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_lt'),
            (r'salary\s*>=\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_gte'),
            (r'salary\s*<=\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)', 'rate_lte'),
            (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\+\s*rate', 'rate_gt'),
            (r'rate\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*\+', 'rate_gt'),
            (r'rate\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*-', 'rate_lt'),
            (r'rate\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*and\s*below', 'rate_lte'),
            (r'rate\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*and\s*above', 'rate_gte')
        ]
        
        for pattern, key in rate_patterns:
            match = re.search(pattern, message_lower)
            if match:
                rate_value = float(match.group(1).replace(',', ''))
                criteria[key] = rate_value
                break
        
        # Extract committed hours ranges
        hours_patterns = [
            (r'(\d+)\s*\+\s*hours?', 'hours_gt'),
            (r'hours?\s*>\s*(\d+)', 'hours_gt'),
            (r'hours?\s*<\s*(\d+)', 'hours_lt'),
            (r'hours?\s*>=\s*(\d+)', 'hours_gte'),
            (r'hours?\s*<=\s*(\d+)', 'hours_lte'),
            (r'working\s*>\s*(\d+)\s*hours?', 'hours_gt'),
            (r'working\s*<\s*(\d+)\s*hours?', 'hours_lt'),
            (r'working\s*>=\s*(\d+)\s*hours?', 'hours_gte'),
            (r'working\s*<=\s*(\d+)\s*hours?', 'hours_lte')
        ]
        
        for pattern, key in hours_patterns:
            match = re.search(pattern, message_lower)
            if match:
                hours_value = int(match.group(1))
                criteria[key] = hours_value
                break
        
        # Extract hire date ranges
        hire_patterns = [
            (r'hired\s*in\s*(\d{4})', 'hire_year'),
            (r'hired\s*after\s*(\w+\s+\d{4})', 'hire_after'),
            (r'hired\s*before\s*(\w+\s+\d{4})', 'hire_before'),
            (r'hired\s*(\w+\s+\d{4})', 'hire_date'),
            (r'(\d{4})\s*hires?', 'hire_year'),
            (r'new\s*employees?\s*(\d{4})', 'hire_year')
        ]
        
        for pattern, key in hire_patterns:
            match = re.search(pattern, message_lower)
            if match:
                criteria[key] = match.group(1)
                break
        
        # Extract termination status
        if "active" in message_lower or "current" in message_lower:
            criteria['status'] = 'active'
        elif "terminated" in message_lower or "former" in message_lower or "ex-employee" in message_lower:
            criteria['status'] = 'terminated'
        
        # Extract currency
        if "usd" in message_lower or "dollar" in message_lower or "$" in message:
            criteria['currency'] = 'USD'
        elif "eur" in message_lower or "euro" in message_lower or "€" in message:
            criteria['currency'] = 'EUR'
        elif "gbp" in message_lower or "pound" in message_lower or "£" in message:
            criteria['currency'] = 'GBP'
        elif "cad" in message_lower or "canadian" in message_lower:
            criteria['currency'] = 'CAD'
        elif "aud" in message_lower or "australian" in message_lower:
            criteria['currency'] = 'AUD'
        
        # Extract document status
        if "with nda" in message_lower or "nda" in message_lower:
            criteria['has_nda'] = True
        elif "without nda" in message_lower or "no nda" in message_lower:
            criteria['has_nda'] = False
            
        if "with contract" in message_lower or "contract" in message_lower:
            criteria['has_contract'] = True
        elif "without contract" in message_lower or "no contract" in message_lower:
            criteria['has_contract'] = False
        
        return criteria
    
    def _create_search_description(self, search_criteria: Dict[str, Any]) -> str:
        """Create a description of the search criteria"""
        descriptions = []
        
        if search_criteria.get('work_schedule'):
            if search_criteria['work_schedule'] == 'part_time':
                descriptions.append("part-time employees")
            elif search_criteria['work_schedule'] == 'full_time':
                descriptions.append("full-time employees")
        
        if search_criteria.get('employment_type'):
            descriptions.append(f"{search_criteria['employment_type']} employees")
        
        if search_criteria.get('department'):
            descriptions.append(f"employees in {search_criteria['department']} department")
        
        if search_criteria.get('job_title'):
            descriptions.append(f"{search_criteria['job_title']} employees")
        
        if search_criteria.get('rate_type'):
            descriptions.append(f"employees on {search_criteria['rate_type']} basis")
        
        # Add rate amount ranges
        if search_criteria.get('rate_gt'):
            descriptions.append(f"employees with rate > ${search_criteria['rate_gt']:,}")
        if search_criteria.get('rate_lt'):
            descriptions.append(f"employees with rate < ${search_criteria['rate_lt']:,}")
        if search_criteria.get('rate_gte'):
            descriptions.append(f"employees with rate >= ${search_criteria['rate_gte']:,}")
        if search_criteria.get('rate_lte'):
            descriptions.append(f"employees with rate <= ${search_criteria['rate_lte']:,}")
        
        # Add committed hours ranges
        if search_criteria.get('hours_gt'):
            descriptions.append(f"employees working > {search_criteria['hours_gt']} hours/week")
        if search_criteria.get('hours_lt'):
            descriptions.append(f"employees working < {search_criteria['hours_lt']} hours/week")
        if search_criteria.get('hours_gte'):
            descriptions.append(f"employees working >= {search_criteria['hours_gte']} hours/week")
        if search_criteria.get('hours_lte'):
            descriptions.append(f"employees working <= {search_criteria['hours_lte']} hours/week")
        
        # Add hire date ranges
        if search_criteria.get('hire_year'):
            descriptions.append(f"employees hired in {search_criteria['hire_year']}")
        if search_criteria.get('hire_after'):
            descriptions.append(f"employees hired after {search_criteria['hire_after']}")
        if search_criteria.get('hire_before'):
            descriptions.append(f"employees hired before {search_criteria['hire_before']}")
        
        # Add status
        if search_criteria.get('status') == 'active':
            descriptions.append("active employees")
        elif search_criteria.get('status') == 'terminated':
            descriptions.append("terminated employees")
        
        # Add currency
        if search_criteria.get('currency'):
            descriptions.append(f"employees paid in {search_criteria['currency']}")
        
        # Add document status
        if search_criteria.get('has_nda') is True:
            descriptions.append("employees with NDA")
        elif search_criteria.get('has_nda') is False:
            descriptions.append("employees without NDA")
            
        if search_criteria.get('has_contract') is True:
            descriptions.append("employees with contracts")
        elif search_criteria.get('has_contract') is False:
            descriptions.append("employees without contracts")
        
        if not descriptions:
            return "employees in the system"
        
        return " and ".join(descriptions)
