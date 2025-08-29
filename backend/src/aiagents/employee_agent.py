from typing import Dict, Any, List


class EmployeeAgent:
    """
    A container for the Employee Agent's configuration.
    All runtime logic is now handled by the LangGraph engine.
    """
    def __init__(self):
        """Initializes the agent with its specific instructions and tool schemas."""
        self.instructions = "You are Milo, an AI assistant."
        self.tools = self._get_tool_schemas()

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Defines the OpenAI function calling schemas for the tools this agent can use.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_employee",
                    "description": "Create a new employee record in the HR system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "profile_id": {"type": "string", "description": "UUID of the user profile"},
                            "job_title": {"type": "string", "description": "Job title"},
                            "department": {"type": "string", "description": "Department"},
                            "employment_type": {"type": "string", "enum": ["permanent", "contract", "intern", "consultant"]},
                            "full_time_part_time": {"type": "string", "enum": ["full_time", "part_time"]},
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
                            "employee_id": {"type": "integer", "description": "ID of the employee to update"},
                            "job_title": {"type": "string", "description": "New job title"},
                            "department": {"type": "string", "description": "New department"},
                        },
                        "required": ["employee_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_employees",
                    "description": "Search for employees by name, job title, or department",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Search term"}
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
                            "employee_id": {"type": "integer", "description": "ID of the employee"}
                        },
                        "required": ["employee_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_employees",
                    "description": "Get a list of all employees in the system.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_profiles_by_name",
                    "description": "Search for user profiles by name to find the required profile_id for creating an employee.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Name to search for in user profiles"}
                        },
                        "required": ["search_term"]
                    }
                }
            }
        ]
