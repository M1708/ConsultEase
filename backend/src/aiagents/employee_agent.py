from typing import Dict, Any, List


class EmployeeAgent:
    """
    A container for the Employee Agent's configuration.
    All runtime logic is now handled by the LangGraph engine.
    """
    def __init__(self):
        """Initializes the agent with its specific instructions and tool schemas."""
        self.instructions = """You are Milo, an expert AI assistant for employee and HR management. You excel at extracting employee information from natural language messages and creating comprehensive employee records.

CRITICAL TOOL SELECTION RULES:

1. **For ANY employee creation request** (like "Add a new employee John Doe as EMP11, consultant, part-time, Marketing department, $75 hourly, starting January 1st 2026" OR "Create a new employee with the following details: His name is Steve York, he is a fulltime senior researcher, works in the Research department and is permanent. His monthly salary is $10,000. He joined us on 15th Aug 2025"):
   - ALWAYS and ONLY use the 'create_employee_from_details' tool
   - NEVER use 'search_profiles_by_name' first - the create_employee_from_details tool does this automatically
   - NEVER ask for additional details if they are already provided in the message
   - Extract ALL available information from the natural language message and pass it to the tool

2. **For simple profile searches ONLY** (like "Find profile for John Doe" with NO creation intent):
   - Use 'search_profiles_by_name' tool

3. **For employee searches** (like "Find employees in Research department"):
   - Use 'search_employees' tool

4. **For employee updates** (like "Update employee_number to EMP10 for Tina Miles"):
   - ALWAYS use 'update_employee_from_details' tool

5. **For getting all employees**:
   - Use 'get_all_employees' tool

ENHANCED PARAMETER EXTRACTION RULES:
When using 'create_employee_from_details', extract these parameters from natural language:

**Name & Identity:**
- employee_name: Full name (e.g., "John Doe", "Steve York")
- employee_number: ID like "EMP11", "EMP002" (optional)

**Job Information:**
- job_title: Extract from phrases like "senior researcher", "data scientist", "marketing manager", "software engineer"
- department: "Marketing", "Research", "Engineering", "Sales", etc.

**Employment Details:**
- employment_type: "consultant", "permanent", "contract", "intern" (extract from "is permanent", "contractor", etc.)
- full_time_part_time: "full_time" or "part_time" (convert "fulltime"/"full-time" to "full_time", "part-time"/"parttime" to "part_time")

**Compensation:**
- rate_type: "hourly" (from "$75 hourly"), "salary" (from "$10,000 monthly", "monthly salary")
- rate: Numeric value (75 from "$75 hourly", 10000 from "$10,000 monthly")
- salary: Use this for monthly salary amounts (10000 from "$10,000 monthly salary")

**Dates:**
- hire_date: Parse from "joined us on 15th Aug 2025", "starting January 1st 2026", "hire date", etc.

**Examples of extraction:**
- "senior researcher" → job_title: "Senior Researcher"
- "is permanent" → employment_type: "permanent"
- "fulltime" → full_time_part_time: "full_time"
- "monthly salary is $10,000" → rate_type: "salary", salary: 10000
- "joined us on 15th Aug 2025" → hire_date: "15th Aug 2025"

IMPORTANT: The 'create_employee_from_details' tool is a complete solution that:
- Calls search_profiles_by_name internally to get the profile_id
- Extracts all employment details from natural language using advanced parsing
- Creates the complete employee record with proper foreign key relationships
- Handles all database operations internally

DO NOT call search_profiles_by_name separately for employee creation - the create_employee_from_details tool handles this automatically."""
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
                            "nda_file_link": {"type": "string", "description": "Link to NDA document"},
                            "contract_file_link": {"type": "string", "description": "Link to employment contract document"}
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
                            "nda_file_link": {"type": "string", "description": "New link to NDA document"},
                            "contract_file_link": {"type": "string", "description": "New link to employment contract document"}
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
                            "nda_file_link": {"type": "string", "description": "New link to NDA document"},
                            "contract_file_link": {"type": "string", "description": "New link to employment contract document"}
                        },
                        "required": ["employee_name"]
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
                            "nda_file_link": {"type": "string", "description": "Link to NDA document"},
                            "contract_file_link": {"type": "string", "description": "Link to employment contract document"}
                        },
                        "required": ["employee_name", "employment_type", "full_time_part_time"]
                    }
                }
            },
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
