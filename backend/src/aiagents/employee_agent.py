from typing import Dict, Any, List


class EmployeeAgent:
    """
    A container for the Employee Agent's configuration.
    All runtime logic is now handled by the LangGraph engine.
    """
    def __init__(self):
        """Initializes the agent with its specific instructions and tool schemas."""
        self.instructions = "You are Core, an expert AI assistant for employee and HR management."
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
                            "employee_number": {"type": "string", "description": "Optional employee ID/number"},
                            "job_title": {"type": "string", "description": "Job position"},
                            "department": {"type": "string", "description": "Department name"},
                            "employment_type": {"type": "string", "enum": ["permanent", "contract", "intern", "consultant"], "description": "Employment type"},
                            "full_time_part_time": {"type": "string", "enum": ["full_time", "part_time"], "description": "Work schedule"},
                            "committed_hours": {"type": "integer", "description": "Hours per week/month commitment"},
                            "hire_date": {"type": "string", "description": "Hire date in YYYY-MM-DD format"},
                            "termination_date": {"type": "string", "description": "Termination date in YYYY-MM-DD format"},
                            "rate_type": {"type": "string", "enum": ["hourly", "salary", "project_based"], "description": "Compensation type"},
                            "rate": {"type": "number", "description": "Rate amount"},
                            "currency": {"type": "string", "description": "Currency code"},
                            # Legacy fields removed - using nda_document_file_path and contract_document_file_path
                            "nda_document_data": {"type": "string", "description": "Base64 encoded NDA document data for upload during creation"},
                            "nda_document_filename": {"type": "string", "description": "NDA document filename"},
                            "nda_document_size": {"type": "integer", "description": "NDA document file size in bytes"},
                            "nda_document_mime_type": {"type": "string", "description": "NDA document MIME type"},
                            "contract_document_data": {"type": "string", "description": "Base64 encoded contract document data for upload during creation"},
                            "contract_document_filename": {"type": "string", "description": "Contract document filename"},
                            "contract_document_size": {"type": "integer", "description": "Contract document file size in bytes"},
                            "contract_document_mime_type": {"type": "string", "description": "Contract document MIME type"}
                        },
                        "required": ["profile_id", "employment_type", "full_time_part_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_employee",
                    "description": "Update an existing employee's information using employee_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer", "description": "ID of the employee to update"},
                            "employee_number": {"type": "string", "description": "New employee ID/number"},
                            "job_title": {"type": "string", "description": "New job title"},
                            "department": {"type": "string", "description": "New department"},
                            "employment_type": {"type": "string", "enum": ["permanent", "contract", "intern", "consultant"], "description": "New employment type"},
                            "full_time_part_time": {"type": "string", "enum": ["full_time", "part_time"], "description": "New work schedule"},
                            "committed_hours": {"type": "integer", "description": "New hours per week/month commitment"},
                            "hire_date": {"type": "string", "description": "New hire date in YYYY-MM-DD format"},
                            "termination_date": {"type": "string", "description": "New termination date in YYYY-MM-DD format"},
                            "rate_type": {"type": "string", "enum": ["hourly", "salary", "project_based"], "description": "New compensation type"},
                            "rate": {"type": "number", "description": "New rate amount"},
                            "currency": {"type": "string", "description": "New currency code"},
                            # Legacy fields removed - using nda_document_file_path and contract_document_file_path
                        },
                        "required": ["employee_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_employee_from_details",
                    "description": "**PRIMARY TOOL FOR EMPLOYEE UPDATES** - Update an employee record from natural language input. Use this for requests like 'Update employee_number to EMP10 for Tina Miles' or 'Change John Doe's job title to Senior Manager'. This tool handles employee searching and updating automatically in one step.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_name": {"type": "string", "description": "Full name of the employee to update (e.g., 'Tina Miles', 'John Doe')"},
                            "employee_number": {"type": "string", "description": "New employee ID/number (e.g., 'EMP10', 'DS002')"},
                            "job_title": {"type": "string", "description": "New job position (e.g., 'Senior Manager', 'Lead Developer')"},
                            "department": {"type": "string", "description": "New department name (e.g., 'Engineering', 'Marketing')"},
                            "employment_type": {"type": "string", "description": "New employment type: permanent, contract, intern, or consultant"},
                            "full_time_part_time": {"type": "string", "description": "New work schedule: full_time or part_time"},
                            "committed_hours": {"type": "integer", "description": "New hours per week/month commitment"},
                            "hire_date": {"type": "string", "description": "New hire date (e.g., '15th Aug 2025', 'January 1st 2026')"},
                            "termination_date": {"type": "string", "description": "New termination date"},
                            "rate_type": {"type": "string", "description": "New compensation type: hourly, salary, or project_based"},
                            "rate": {"type": "number", "description": "New rate amount (e.g., 85 for $85 hourly, 12000 for $12,000 monthly)"},
                            "currency": {"type": "string", "description": "New currency code (defaults to USD)"},
                            # Legacy fields removed - using nda_document_file_path and contract_document_file_path
                        },
                        "required": ["employee_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_employees",
                    "description": "Search for employees by name, job title, department, employment type, or any other criteria. This tool is designed to handle filtering and can process various search terms to find matching employees.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Search term (e.g., 'software engineer', 'part-time', 'marketing', 'John Doe')"}
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
                    "description": "Get a list of all employees in the system. This tool returns comprehensive employee information without filtering.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_employees_by_committed_hours",
                    "description": "Get employees with committed hours greater than or equal to the specified minimum hours. Use this for queries like 'show employees with committed hours more than 20' or 'employees with hours >= 25'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "min_hours": {"type": "integer", "description": "Minimum committed hours per week to filter by (e.g., 20 for 'more than 20 hours')"}
                        },
                        "required": ["min_hours"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_profiles_by_name",
                    "description": "Search for user profiles by name. DO NOT USE THIS FOR EMPLOYEE CREATION - use create_employee_from_details instead. This tool is ONLY for profile lookup when the user specifically asks to 'find profile for [name]' without any creation intent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Name to search for in user profiles"}
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_employee_from_details",
                    "description": "**PRIMARY TOOL FOR EMPLOYEE CREATION** - Create a new employee record from natural language input. Use this FIRST for ALL employee creation requests where the user provides details like 'Create a new employee with the following details: His name is Steve York, he is a fulltime senior researcher, works in the Research department and is permanent. His monthly salary is $10,000. He joined us on 15th Aug 2025' or 'Add employee Tina Miles as EMP002, consultant, part-time, Marketing department, $75 hourly, starting January 1st 2026'. This tool handles profile searching and employee creation automatically in one step.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_name": {"type": "string", "description": "Full name of the employee (e.g., 'Steve York', 'Tina Miles')"},
                            "employee_number": {"type": "string", "description": "Optional employee ID/number (e.g., 'EMP002', 'DS001')"},
                            "job_title": {"type": "string", "description": "Job position extracted from the message (e.g., 'Senior Researcher', 'Data Scientist')"},
                            "department": {"type": "string", "description": "Department name extracted from the message (e.g., 'Research', 'Marketing')"},
                            "employment_type": {"type": "string", "description": "Employment type: permanent, contract, intern, or consultant"},
                            "full_time_part_time": {"type": "string", "description": "Work schedule: full_time or part_time (convert 'fulltime' to 'full_time')"},
                            "committed_hours": {"type": "integer", "description": "Hours per week/month commitment (e.g., 40 for full-time)"},
                            "hire_date": {"type": "string", "description": "Hire date from the message (e.g., '15th Aug 2025', 'January 1st 2026')"},
                            "termination_date": {"type": "string", "description": "Optional termination date"},
                            "rate_type": {"type": "string", "description": "Compensation type: hourly, salary, or project_based (extracted from '$75 hourly' or '$10,000 monthly')"},
                            "rate": {"type": "number", "description": "Rate amount (e.g., 75 for $75 hourly, 10000 for $10,000 monthly)"},
                            "salary": {"type": "number", "description": "Monthly salary amount in numbers (e.g., 10000 for $10,000) - use this for salary-based compensation"},
                            "currency": {"type": "string", "description": "Currency code (defaults to USD)"},
                            # Legacy fields removed - using nda_document_file_path and contract_document_file_path
                            "nda_document_data": {"type": "string", "description": "Base64 encoded NDA document data for upload during creation"},
                            "nda_document_filename": {"type": "string", "description": "NDA document filename"},
                            "nda_document_size": {"type": "integer", "description": "NDA document file size in bytes"},
                            "nda_document_mime_type": {"type": "string", "description": "NDA document MIME type"},
                            "contract_document_data": {"type": "string", "description": "Base64 encoded contract document data for upload during creation"},
                            "contract_document_filename": {"type": "string", "description": "Contract document filename"},
                            "contract_document_size": {"type": "integer", "description": "Contract document file size in bytes"},
                            "contract_document_mime_type": {"type": "string", "description": "Contract document MIME type"}
                        },
                        "required": ["employee_name", "employment_type", "full_time_part_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_employee",
                    "description": "Delete an employee record from the HR system. Can delete by employee_id, profile_id, employee_number, or employee_name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer", "description": "Employee ID"},
                            "profile_id": {"type": "string", "description": "Profile ID (UUID)"},
                            "employee_number": {"type": "string", "description": "Employee number"},
                            "employee_name": {"type": "string", "description": "Employee name (first name, last name, or full name)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "upload_employee_document",
                    "description": "Upload NDA or contract documents for an employee. Handles file upload and database updates with enhanced metadata tracking. CRITICAL: Always extract employee name from user message - look for patterns like 'for employee [Name]', 'for [Name]', 'this is for [Name]'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer", "description": "Employee ID"},
                            "employee_name": {"type": "string", "description": "Employee name extracted from user message (e.g., 'Steve York' from 'for employee Steve York'). REQUIRED when employee_id not provided."},
                            "document_type": {"type": "string", "enum": ["nda", "contract"], "description": "Type of document to upload"},
                            "file_data": {"type": "string", "description": "Base64 encoded file content"},
                            "filename": {"type": "string", "description": "Original filename"},
                            "file_size": {"type": "integer", "description": "File size in bytes"},
                            "mime_type": {"type": "string", "description": "MIME type of the file"}
                        },
                        "required": ["document_type", "file_data", "filename", "file_size", "mime_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_employee_document",
                    "description": "Delete NDA or contract documents for an employee. Removes both file and database references.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer", "description": "Employee ID"},
                            "employee_name": {"type": "string", "description": "Employee name (alternative to employee_id)"},
                            "document_type": {"type": "string", "enum": ["nda", "contract"], "description": "Type of document to delete"}
                        },
                        "required": ["document_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_employee_document",
                    "description": "Get document information and download URLs for an employee. Provides access to both NDA and contract documents.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "integer", "description": "Employee ID"},
                            "employee_name": {"type": "string", "description": "Employee name (alternative to employee_id)"},
                            "document_type": {"type": "string", "enum": ["nda", "contract"], "description": "Type of document to retrieve"}
                        },
                        "required": ["document_type"]
                    }
                }
            }
        ]

    def get_capabilities(self) -> Dict[str, Any]:
        """
        A simple description of the agent's purpose.
        """
        return {
            "name": "EmployeeAgent",
            "description": "Employee and HR management specialist",
            "tools": [tool['function']['name'] for tool in self.tools]
        }
