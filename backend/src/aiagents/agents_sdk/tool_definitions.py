"""
Tool Definitions for OpenAI Agents SDK

This module converts existing tool functions to OpenAI Agents SDK compatible format
with proper type hints and parameter validation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import asyncio
import re
from datetime import datetime

# Import existing tools
from ..tools.contract_tools import (
    smart_create_contract_tool,
    update_contract_tool,
    search_contracts_tool,
    get_contract_details_tool,
    create_client_tool,
    search_clients_tool,
    get_contracts_by_client_tool,
    get_all_clients_with_contracts_tool,
    get_contracts_for_next_month_billing_tool,
    get_contracts_by_amount_tool,
    CreateClientParams,
    UpdateContractParams,
    SmartContractParams,
    ContractToolResult
)

# Import employee tools
from ..tools.employee_tools import (
    create_employee_tool,
    update_employee_tool,
    search_employees_tool,
    get_employee_details_tool,
    delete_employee_tool,
    check_employee_exists_tool,
    search_profiles_by_name_tool,
    get_all_employees_tool,
    get_employees_by_committed_hours_tool,
    upload_employee_document_tool,
    delete_employee_document_tool,
    get_employee_document_tool,
    CreateEmployeeParams,
    UpdateEmployeeParams,
    DeleteEmployeeParams,
    UploadEmployeeDocumentParams,
    DeleteEmployeeDocumentParams,
    GetEmployeeDocumentParams
)

# Import user tools
from ..tools.user_tools import (
    create_user_tool,
    get_user_details_tool,
    update_user_tool,
    delete_user_tool,
    search_users_tool,
    CreateUserParams,
    UpdateUserParams,
    SearchUsersParams,
    GetUserDetailsParams,
    DeleteUserParams,
    UserToolResult
)

def _convert_date_format(date_str: str) -> str:
    """Convert date from 'Feb 15th 2026' or 'March 15 2026' format to '2026-02-15' format"""
    try:
        # Remove ordinal suffixes (st, nd, rd, th)
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        
        # Try different date formats
        date_formats = [
            "%b %d %Y",      # "Feb 15 2026"
            "%B %d %Y",      # "March 15 2026"
            "%m/%d/%Y",      # "03/15/2026"
            "%m-%d-%Y",      # "03-15-2026"
            "%Y-%m-%d"       # "2026-03-15" (already correct format)
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                # Return in YYYY-MM-DD format
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If all formats fail, return the original string
        return date_str
    except Exception:
        # If parsing fails, return the original string
        return date_str



def _extract_field_from_request(user_request: str) -> Optional[Dict[str, Any]]:
    """Extract the field to update and its value from user request."""
    user_request_lower = user_request.lower()
    
    # Field extraction patterns
    field_patterns = [
        # Billing frequency patterns
        (r"billing\s+frequency\s+to\s+(\w+)", "billing_frequency"),
        (r"change\s+billing\s+frequency\s+to\s+(\w+)", "billing_frequency"),
        (r"update\s+billing\s+frequency\s+to\s+(\w+)", "billing_frequency"),
        (r"set\s+billing\s+frequency\s+to\s+(\w+)", "billing_frequency"),
        
        # Current amount patterns (MUST BE FIRST to avoid conflicts with general amount patterns)
        (r"current\s+amount\s+to\s+[\$]?([\d,]+(?:\.\d{2})?)", "current_amount"),
        (r"change\s+current\s+amount\s+to\s+[\$]?([\d,]+(?:\.\d{2})?)", "current_amount"),
        (r"update\s+current\s+amount\s+to\s+[\$]?([\d,]+(?:\.\d{2})?)", "current_amount"),
        (r"set\s+current\s+amount\s+to\s+[\$]?([\d,]+(?:\.\d{2})?)", "current_amount"),
        
        # Amount patterns (general - comes after current amount to avoid conflicts)
        (r"amount\s+to\s+\$?([\d,]+(?:\.\d{2})?)", "original_amount"),
        (r"change\s+amount\s+to\s+\$?([\d,]+(?:\.\d{2})?)", "original_amount"),
        (r"update\s+amount\s+to\s+\$?([\d,]+(?:\.\d{2})?)", "original_amount"),
        (r"set\s+amount\s+to\s+\$?([\d,]+(?:\.\d{2})?)", "original_amount"),
        
        # Status patterns
        (r"status\s+to\s+(\w+)", "status"),
        (r"change\s+status\s+to\s+(\w+)", "status"),
        (r"update\s+status\s+to\s+(\w+)", "status"),
        (r"set\s+status\s+to\s+(\w+)", "status"),
        
        # Date patterns - Natural language dates
        (r"change\s+start\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "start_date"),
        (r"update\s+start\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "start_date"),
        (r"set\s+start\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "start_date"),
        (r"start\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "start_date"),
        
        (r"change\s+end\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "end_date"),
        (r"update\s+end\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "end_date"),
        (r"set\s+end\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "end_date"),
        (r"end\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "end_date"),
        
        (r"change\s+termination\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "termination_date"),
        (r"update\s+termination\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "termination_date"),
        (r"set\s+termination\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "termination_date"),
        (r"termination\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "termination_date"),
        
        # Date patterns - ISO format (YYYY-MM-DD)
        (r"start\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "start_date"),
        (r"end\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "end_date"),
        (r"termination\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "termination_date"),
        (r"change\s+termination\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "termination_date"),
        (r"update\s+termination\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "termination_date"),
        (r"set\s+termination\s+date\s+to\s+(\d{4}-\d{2}-\d{2})", "termination_date"),
        
        # Amendment patterns
        (r"amendments?\s+to\s+(.+)", "amendments"),
        (r"change\s+amendments?\s+to\s+(.+)", "amendments"),
        (r"update\s+amendments?\s+to\s+(.+)", "amendments"),
        (r"set\s+amendments?\s+to\s+(.+)", "amendments"),
        
        # Billing prompt date patterns
        (r"next\s+billing\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "billing_prompt_next_date"),
        (r"billing\s+prompt\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "billing_prompt_next_date"),
        (r"update\s+next\s+billing\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "billing_prompt_next_date"),
        (r"change\s+next\s+billing\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "billing_prompt_next_date"),
        (r"set\s+next\s+billing\s+date\s+to\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4})", "billing_prompt_next_date"),
    ]
    
    
    for i, (pattern, field_name) in enumerate(field_patterns):
        #(f"🔍 FIELD EXTRACTION DEBUG: Testing pattern {i}: '{pattern}' for field '{field_name}'")
        match = re.search(pattern, user_request_lower)
        if match:
            value = match.group(1)
            #print(f"🔍 FIELD EXTRACTION DEBUG: ✅ MATCHED! Raw value: '{value}', field: '{field_name}'")
            
            # Special handling for different field types
            if field_name in ["original_amount", "current_amount"]:
                # Remove commas and convert to float
                original_value = value
                value = float(value.replace(",", ""))
                #print(f"🔍 FIELD EXTRACTION DEBUG: Converted '{original_value}' to {value} (float)")
            elif field_name in ["start_date", "end_date", "termination_date"]:
                # Check if it's a natural language date that needs conversion
                if re.match(r'\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4}', value):
                    # Convert natural language date to ISO format
                    original_value = value
                    value = _convert_date_format(value)
                    
                else:
                    # Keep as string for ISO format dates
                    print(f"🔍 FIELD EXTRACTION DEBUG: Keeping ISO date as string: '{value}'")
            elif field_name == "billing_prompt_next_date":
                # Convert date format from "Feb 15th 2026" to "2026-02-15"
                original_value = value
                value = _convert_date_format(value)
                
            elif field_name == "billing_frequency":
                # Capitalize first letter
                original_value = value
                value = value.capitalize()
                
            elif field_name == "status":
                # Keep as lowercase
                
                value = value.lower()
            elif field_name == "amendments":
                # Keep amendments as string, trim whitespace
                
                value = value.strip()
            
            result = {field_name: value}
            
            return result
        else:
            print(f"🔍 FIELD EXTRACTION DEBUG: ❌ No match for pattern {i}")
    
    print(f"🔍 FIELD EXTRACTION DEBUG: No patterns matched, returning None")
    
    return None



class ContractSearchParams(BaseModel):
    """Parameters for contract search operations"""
    client_name: Optional[str] = Field(None, description="Name of the client to search contracts for")
    status: Optional[str] = Field(None, description="Contract status (active, draft, terminated, etc.)")
    contract_type: Optional[str] = Field(None, description="Type of contract (Fixed, Hourly, Retainer)")
    min_amount: Optional[float] = Field(None, description="Minimum contract amount")
    max_amount: Optional[float] = Field(None, description="Maximum contract amount")


class ContractUpdateParams(BaseModel):
    """Parameters for contract update operations"""
    client_name: str = Field(..., description="Name of the client")
    contract_id: Optional[int] = Field(None, description="Specific contract ID to update")
    start_date: Optional[str] = Field(None, description="New start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="New end date (YYYY-MM-DD)")
    contract_type: Optional[str] = Field(None, description="New contract type")
    original_amount: Optional[float] = Field(None, description="New contract amount")
    billing_frequency: Optional[str] = Field(None, description="New billing frequency")
    billing_prompt_next_date: Optional[str] = Field(None, description="New billing prompt date in YYYY-MM-DD format")
    status: Optional[str] = Field(None, description="New contract status")
    notes: Optional[str] = Field(None, description="Additional notes")


class ClientCreateParams(BaseModel):
    """Parameters for client creation"""
    client_name: str = Field(..., description="Name of the client company")
    primary_contact_name: Optional[str] = Field(None, description="Primary contact person's name")
    primary_contact_email: Optional[str] = Field(None, description="Primary contact email")
    company_size: Optional[str] = Field(None, description="Company size category")
    industry: Optional[str] = Field(None, description="Industry sector")
    notes: Optional[str] = Field(None, description="Additional notes about the client")


class ContractCreateParams(BaseModel):
    """Parameters for contract creation"""
    client_name: str = Field(..., description="Name of the client")
    contract_type: str = Field(..., description="Type of contract (Fixed, Hourly, Retainer)")
    original_amount: Optional[float] = Field(None, description="Contract amount")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    billing_frequency: Optional[str] = Field(None, description="Billing frequency")
    notes: Optional[str] = Field(None, description="Contract notes")


class ToolRegistry:
    """Registry for OpenAI Agents SDK compatible tools"""

    def __init__(self):
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools"""
        self.tools.update({
            # Contract and Client Tools
            "search_contracts": self._create_search_contracts_tool(),
            "update_contract": self._create_update_contract_tool(),
            "create_client": self._create_client_tool(),
            "create_contract": self._create_contract_tool(),
            "get_contract_details": self._create_get_contract_details_tool(),
            "get_client_contracts": self._create_get_client_contracts_tool(),
            "get_all_clients_with_contracts": self._create_get_all_clients_with_contracts_tool(),
            "get_contracts_for_next_month_billing": self._create_get_contracts_for_next_month_billing_tool(),
            "get_contracts_by_amount": self._create_get_contracts_by_amount_tool(),

            # Employee Tools
            "create_employee": self._create_employee_tool(),
            "update_employee": self._create_update_employee_tool(),
            "search_employees": self._create_search_employees_tool(),
            "get_employee_details": self._create_get_employee_details_tool(),
            "delete_employee": self._create_delete_employee_tool(),
            "check_employee_exists": self._create_check_employee_exists_tool(),
            "search_profiles": self._create_search_profiles_tool(),
            "get_all_employees": self._create_get_all_employees_tool(),
            "get_employees_by_committed_hours": self._create_get_employees_by_committed_hours_tool(),
            "upload_employee_document": self._create_upload_employee_document_tool(),
            "delete_employee_document": self._create_delete_employee_document_tool(),
            "get_employee_document": self._create_get_employee_document_tool(),

            # User Tools
            "create_user": self._create_user_tool(),
            "get_user_details": self._create_get_user_details_tool(),
            "update_user": self._create_update_user_tool(),
            "delete_user": self._create_delete_user_tool(),
            "search_users": self._create_search_users_tool(),
        })

    def _create_search_contracts_tool(self):
        """Create SDK-compatible contract search tool"""
        async def search_contracts(params: ContractSearchParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Search for contracts based on various criteria"""
            try:
                # Convert Pydantic model to dict for existing tool
                search_params = params.model_dump(exclude_unset=True)

                # Call existing tool
                result = await search_contracts_tool(**search_params)

                if result.success:
                    contracts = result.data.get("contracts", [])
                    if contracts:
                        contract_summaries = []
                        for contract in contracts[:5]:  # Limit to 5 results
                            summary = f"- Contract ID {contract['contract_id']}: {contract['client_name']} - {contract['contract_type']}"
                            if contract.get('original_amount'):
                                summary += f" (${contract['original_amount']:,.2f})"
                            summary += f" - {contract['status']}"
                            contract_summaries.append(summary)

                        return ContractToolResult(
                            success=True,
                            message=f"Found {len(contracts)} contracts:\n" + "\n".join(contract_summaries),
                            data={"contracts": contracts, "count": len(contracts)}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No contracts found matching the criteria.",
                            data={"contracts": [], "count": 0}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Search failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error searching contracts: {str(e)}"
                )

        return {
            "function": search_contracts,
            "name": "search_contracts",
            "description": "Search for contracts by client name, status, type, or amount range",
            "parameters": ContractSearchParams
        }

    def _create_update_contract_tool(self):
        """Create SDK-compatible contract update tool"""
        async def update_contract(params: ContractUpdateParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Update an existing contract with new information"""
            try:
                # Convert Pydantic model to dict for existing tool
                update_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    update_params['context'] = context

                # Extract field from original user request if available
                if context and context.get('original_user_request'):
                    
                    extracted_field = _extract_field_from_request(context['original_user_request'])
                    if extracted_field:
                        
                        update_params.update(extracted_field)
                    
                else:
                    print(f"🔍 FIELD EXTRACTION: No original_user_request in context")

                # Call existing tool
                result = await update_contract_tool(UpdateContractParams(**update_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Update failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error updating contract: {str(e)}"
                )

        return {
            "function": update_contract,
            "name": "update_contract",
            "description": "Update contract details including dates, amounts, status, and notes",
            "parameters": ContractUpdateParams
        }

    def _create_client_tool(self):
        """Create SDK-compatible client creation tool"""
        async def create_client(params: ClientCreateParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Create a new client profile"""
            try:
                # Convert Pydantic model to dict for existing tool
                client_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    client_params['context'] = context

                # Call existing tool
                result = await create_client_tool(CreateClientParams(**client_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Client creation failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error creating client: {str(e)}"
                )

        return {
            "function": create_client,
            "name": "create_client",
            "description": "Create a new client profile with contact information and company details",
            "parameters": ClientCreateParams
        }

    def _create_contract_tool(self):
        """Create SDK-compatible contract creation tool"""
        async def create_contract(params: ContractCreateParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Create a new contract for an existing client"""
            try:
                # Convert Pydantic model to dict for existing tool
                contract_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    contract_params['context'] = context

                # Call existing tool
                result = await smart_create_contract_tool(SmartContractParams(**contract_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Contract creation failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error creating contract: {str(e)}"
                )

        return {
            "function": create_contract,
            "name": "create_contract",
            "description": "Create a new contract for an existing client with specified terms and conditions",
            "parameters": ContractCreateParams
        }

    def _create_get_contract_details_tool(self):
        """Create SDK-compatible contract details retrieval tool"""
        async def get_contract_details(contract_id: int, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get detailed information about a specific contract"""
            try:
                # Call existing tool
                result = await get_contract_details_tool(contract_id=contract_id)

                if result.success:
                    contract = result.data.get("contract", {})
                    if contract:
                        details = f"""Contract Details:
ID: {contract['contract_id']}
Client: {contract['client_name']}
Type: {contract['contract_type']}
Status: {contract['status']}
Amount: ${contract['original_amount']:,.2f} ({contract['billing_frequency']})
Dates: {contract['start_date']} to {contract['end_date']}
Notes: {contract['notes'] or 'None'}"""

                        if contract.get('document_filename'):
                            details += f"\nDocument: {contract['document_filename']}"

                        return ContractToolResult(
                            success=True,
                            message=details,
                            data={"contract": contract}
                        )
                    else:
                        return ContractToolResult(
                            success=False,
                            message="Contract not found."
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Failed to get contract details: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting contract details: {str(e)}"
                )

        return {
            "function": get_contract_details,
            "name": "get_contract_details",
            "description": "Get detailed information about a specific contract by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_id": {
                        "type": "integer",
                        "description": "The contract ID to retrieve details for"
                    }
                },
                "required": ["contract_id"]
            }
        }

    def _create_get_client_contracts_tool(self):
        """Create SDK-compatible client contracts retrieval tool"""
        async def get_client_contracts(client_name: str, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get all contracts for a specific client"""
            try:
                # Call existing tool
                result = await get_contracts_by_client_tool(client_name)

                if result.success:
                    contracts = result.data.get("contracts", [])
                    if contracts:
                        contract_summaries = []
                        for contract in contracts:
                            summary = f"""Contract ID {contract['contract_id']}:
- Type: {contract['contract_type']}
- Status: {contract['status']}
- Amount: ${contract['original_amount']:,.2f} ({contract['billing_frequency']})
- Dates: {contract['start_date']} to {contract['end_date']}"""

                            if contract.get('document_filename'):
                                summary += f"\n- Document: {contract['document_filename']}"

                            contract_summaries.append(summary)

                        # Create a clean, user-friendly format
                        contract_list = []
                        for i, contract in enumerate(contracts, 1):
                            amount = f"${contract['original_amount']:,.2f}" if contract['original_amount'] else "N/A"
                            status = contract['status'].lower()
                            start_date = contract.get('start_date', 'Not set')
                            contract_list.append(f"{i}. Contract ID {contract['contract_id']}: {contract['contract_type']} ({amount}) - {status}, start date ({start_date})")

                        message = f"{client_name} has {len(contracts)} contracts. Here are the details:\n\n" + "\n".join(contract_list)

                        if len(contracts) > 1:
                            message += f"\n\nPlease specify which contract ID you want to upload the document for (e.g., \"upload document for {client_name} contract {contracts[0]['contract_id']}\")."

                        return message
                    else:
                        return f"No contracts found for client '{client_name}'."
                else:
                    return f"Failed to get client contracts: {result.message}"

            except Exception as e:
                return f"Error getting client contracts: {str(e)}"

        return {
            "function": get_client_contracts,
            "name": "get_client_contracts",
            "description": "Get all contracts associated with a specific client",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "The name of the client to get contracts for"
                    }
                },
                "required": ["client_name"]
            }
        }

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a tool by name"""
        return self.tools.get(tool_name)

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools"""
        return list(self.tools.values())

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self.tools.keys())

    # Employee Tool Creation Methods
    def _create_employee_tool(self):
        """Create SDK-compatible employee creation tool"""
        async def create_employee(params: CreateEmployeeParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Create a new employee record"""
            try:
                # Convert Pydantic model to dict for existing tool
                employee_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    employee_params['context'] = context

                # Call existing tool
                result = await create_employee_tool(CreateEmployeeParams(**employee_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Employee creation failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error creating employee: {str(e)}"
                )

        return {
            "function": create_employee,
            "name": "create_employee",
            "description": "Create a new employee record with job details, compensation, and employment information",
            "parameters": CreateEmployeeParams
        }

    def _create_update_employee_tool(self):
        """Create SDK-compatible employee update tool"""
        async def update_employee(params: UpdateEmployeeParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Update an existing employee record"""
            try:
                # Convert Pydantic model to dict for existing tool
                update_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    update_params['context'] = context

                # Call existing tool
                result = await update_employee_tool(UpdateEmployeeParams(**update_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Employee update failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error updating employee: {str(e)}"
                )

        return {
            "function": update_employee,
            "name": "update_employee",
            "description": "Update employee information including job title, department, compensation, and employment details",
            "parameters": UpdateEmployeeParams
        }

    def _create_search_employees_tool(self):
        """Create SDK-compatible employee search tool"""
        async def search_employees(search_term: str, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Search for employees by name, job title, department, or employee number"""
            try:
                # Call existing tool
                result = await search_employees_tool(search_term)

                if result.success:
                    employees = result.data.get("employees", [])
                    if employees:
                        employee_summaries = []
                        for emp in employees[:5]:  # Limit to 5 results
                            summary = f"- {emp['profile']['full_name']}: {emp['job_title']} in {emp['department']}"
                            if emp.get('employee_number'):
                                summary += f" (ID: {emp['employee_number']})"
                            employee_summaries.append(summary)

                        return ContractToolResult(
                            success=True,
                            message=f"Found {len(employees)} employees:",
                            data={"employees": employees, "count": len(employees)}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No matching employees found for your criteria.",
                            data={"employees": [], "count": 0}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Search failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error searching employees: {str(e)}"
                )

        return {
            "function": search_employees,
            "name": "search_employees",
            "description": "Search for employees by name, job title, department, or employee number",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Search term for employee name, job title, department, or employee number"
                    }
                },
                "required": ["search_term"]
            }
        }

    def _create_get_employee_details_tool(self):
        """Create SDK-compatible employee details tool"""
        async def get_employee_details(employee_id: int, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get detailed information about a specific employee"""
            try:
                # Call existing tool
                result = await get_employee_details_tool(employee_id)

                if result.success:
                    employee = result.data
                    if employee:
                        details = f"""Employee Details:
Name: {employee['profile']['full_name']}
Employee ID: {employee['employee_id']}
Employee Number: {employee['employee_number']}
Job Title: {employee['job_title']}
Department: {employee['department']}
Employment Type: {employee['employment_type']}
Work Schedule: {employee['full_time_part_time']}
Hire Date: {employee['hire_date'] or 'Not specified'}
Rate: {employee['rate']} ({employee['rate_type']})"""

                        return ContractToolResult(
                            success=True,
                            message=details,
                            data={"employee": employee}
                        )
                    else:
                        return ContractToolResult(
                            success=False,
                            message="Employee not found."
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Failed to get employee details: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting employee details: {str(e)}"
                )

        return {
            "function": get_employee_details,
            "name": "get_employee_details",
            "description": "Get detailed information about a specific employee by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "integer",
                        "description": "The employee ID to retrieve details for"
                    }
                },
                "required": ["employee_id"]
            }
        }

    def _create_delete_employee_tool(self):
        """Create SDK-compatible employee deletion tool"""
        async def delete_employee(params: DeleteEmployeeParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Delete an employee record"""
            try:
                # Convert Pydantic model to dict for existing tool
                delete_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    delete_params['context'] = context

                # Call existing tool
                result = await delete_employee_tool(DeleteEmployeeParams(**delete_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Employee deletion failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error deleting employee: {str(e)}"
                )

        return {
            "function": delete_employee,
            "name": "delete_employee",
            "description": "Delete an employee record by ID, profile ID, employee number, or name",
            "parameters": DeleteEmployeeParams
        }

    def _create_check_employee_exists_tool(self):
        """Create SDK-compatible employee existence check tool"""
        async def check_employee_exists(profile_id: str, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Check if an employee record exists for a given profile"""
            try:
                # Call existing tool
                result = await check_employee_exists_tool(profile_id)

                if result.success:
                    exists = result.data.get("exists", False)
                    if exists:
                        employee = result.data.get("employee", {})
                        return ContractToolResult(
                            success=True,
                            message=f"Employee record exists for profile: {employee.get('profile_name', 'Unknown')}",
                            data={"exists": True, "employee": employee}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No employee record found for this profile",
                            data={"exists": False}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Check failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error checking employee existence: {str(e)}"
                )

        return {
            "function": check_employee_exists,
            "name": "check_employee_exists",
            "description": "Check if an employee record already exists for a given profile ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile_id": {
                        "type": "string",
                        "description": "The profile ID to check for employee record existence"
                    }
                },
                "required": ["profile_id"]
            }
        }

    def _create_search_profiles_tool(self):
        """Create SDK-compatible profile search tool"""
        async def search_profiles(search_name: str, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Search for user profiles by name"""
            try:
                # Call existing tool
                result = await search_profiles_by_name_tool(search_name)

                if result.success:
                    profiles = result.data.get("profiles", [])
                    if profiles:
                        profile_summaries = []
                        for profile in profiles[:5]:  # Limit to 5 results
                            summary = f"- {profile['first_name']} {profile['last_name']} ({profile['email']})"
                            profile_summaries.append(summary)

                        return ContractToolResult(
                            success=True,
                            message=f"Found {len(profiles)} profiles:\n" + "\n".join(profile_summaries),
                            data={"profiles": profiles, "count": len(profiles)}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No profiles found matching the search criteria.",
                            data={"profiles": [], "count": 0}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Search failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error searching profiles: {str(e)}"
                )

        return {
            "function": search_profiles,
            "name": "search_profiles",
            "description": "Search for user profiles by name to find profile IDs for employee creation",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_name": {
                        "type": "string",
                        "description": "Name to search for in user profiles"
                    }
                },
                "required": ["search_name"]
            }
        }

    def _create_get_all_employees_tool(self):
        """Create SDK-compatible get all employees tool"""
        async def get_all_employees(context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get all employees with basic information"""
            try:
                # Call existing tool
                result = await get_all_employees_tool()

                if result.success:
                    employees = result.data.get("employees", [])
                    if employees:
                        employee_summaries = []
                        for emp in employees[:10]:  # Limit to 10 results
                            summary = f"- {emp['profile']['full_name']}: {emp['job_title']} ({emp['department']})"
                            employee_summaries.append(summary)

                        return ContractToolResult(
                            success=True,
                            message=f"All {len(employees)} employees:\n" + "\n".join(employee_summaries),
                            data={"employees": employees, "count": len(employees)}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No employees found in the system.",
                            data={"employees": [], "count": 0}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Failed to get employees: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting all employees: {str(e)}"
                )

        return {
            "function": get_all_employees,
            "name": "get_all_employees",
            "description": "Get a list of all employees with basic information",
            "parameters": {}
        }

    def _create_get_employees_by_committed_hours_tool(self):
        """Create SDK-compatible get employees by committed hours tool"""
        async def get_employees_by_committed_hours(min_hours: int, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get employees with committed hours greater than or equal to min_hours"""
            try:
                # Call existing tool
                result = await get_employees_by_committed_hours_tool(min_hours)

                if result.success:
                    employees = result.data.get("employees", [])
                    if employees:
                        employee_summaries = []
                        for emp in employees:
                            employee_summaries.append({
                                "employee_id": emp.get("employee_id"),
                                "employee_name": emp.get("employee_name"),
                                "job_title": emp.get("job_title"),
                                "department": emp.get("department"),
                                "committed_hours": emp.get("committed_hours"),
                                "employment_type": emp.get("employment_type"),
                                "full_time_part_time": emp.get("full_time_part_time")
                            })
                        
                        return ContractToolResult(
                            success=True,
                            message=f"📋 Found {len(employee_summaries)} employees with committed hours >= {min_hours}",
                            data={
                                "employees": employee_summaries,
                                "count": len(employee_summaries),
                                "min_hours": min_hours
                            }
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message=f"📋 Found 0 employees with committed hours >= {min_hours}",
                            data={
                                "employees": [],
                                "count": 0,
                                "min_hours": min_hours
                            }
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=result.message
                    )
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting employees by committed hours: {str(e)}"
                )

        return {
            "function": get_employees_by_committed_hours,
            "name": "get_employees_by_committed_hours",
            "description": "Get employees with committed hours greater than or equal to the specified minimum hours",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_hours": {
                        "type": "integer",
                        "description": "Minimum committed hours per week to filter by"
                    }
                },
                "required": ["min_hours"]
            }
        }

    def _create_upload_employee_document_tool(self):
        """Create SDK-compatible employee document upload tool"""
        async def upload_employee_document(params: UploadEmployeeDocumentParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Upload NDA or contract documents for employees"""
            try:
                # Convert Pydantic model to dict for existing tool
                upload_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    upload_params['context'] = context

                # Call existing tool
                result = await upload_employee_document_tool(UploadEmployeeDocumentParams(**upload_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Document upload failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error uploading employee document: {str(e)}"
                )

        return {
            "function": upload_employee_document,
            "name": "upload_employee_document",
            "description": "Upload NDA or contract documents for employees with file handling",
            "parameters": UploadEmployeeDocumentParams
        }

    def _create_delete_employee_document_tool(self):
        """Create SDK-compatible employee document deletion tool"""
        async def delete_employee_document(params: DeleteEmployeeDocumentParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Delete NDA or contract documents for employees"""
            try:
                # Convert Pydantic model to dict for existing tool
                delete_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    delete_params['context'] = context

                # Call existing tool
                result = await delete_employee_document_tool(DeleteEmployeeDocumentParams(**delete_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Document deletion failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error deleting employee document: {str(e)}"
                )

        return {
            "function": delete_employee_document,
            "name": "delete_employee_document",
            "description": "Delete NDA or contract documents for employees",
            "parameters": DeleteEmployeeDocumentParams
        }

    def _create_get_employee_document_tool(self):
        """Create SDK-compatible employee document retrieval tool"""
        async def get_employee_document(params: GetEmployeeDocumentParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get information about employee documents"""
            try:
                # Convert Pydantic model to dict for existing tool
                get_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    get_params['context'] = context

                # Call existing tool
                result = await get_employee_document_tool(GetEmployeeDocumentParams(**get_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Document retrieval failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting employee document: {str(e)}"
                )

        return {
            "function": get_employee_document,
            "name": "get_employee_document",
            "description": "Get information and download URLs for employee documents",
            "parameters": GetEmployeeDocumentParams
        }

    # User Tool Creation Methods
    def _create_user_tool(self):
        """Create SDK-compatible user creation tool"""
        async def create_user(params: CreateUserParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Create a new user account"""
            try:
                # Convert Pydantic model to dict for existing tool
                user_params = params.model_dump(exclude_unset=True)

                # Call existing tool
                result = await create_user_tool(CreateUserParams(**user_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"User creation failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error creating user: {str(e)}"
                )

        return {
            "function": create_user,
            "name": "create_user",
            "description": "Create a new user account with email, name, role, and status",
            "parameters": CreateUserParams
        }

    def _create_get_user_details_tool(self):
        """Create SDK-compatible user details tool"""
        async def get_user_details(params: GetUserDetailsParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get detailed information about a specific user"""
            try:
                # Convert Pydantic model to dict for existing tool
                user_params = params.model_dump(exclude_unset=True)

                # Call existing tool
                result = await get_user_details_tool(GetUserDetailsParams(**user_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"User details retrieval failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting user details: {str(e)}"
                )

        return {
            "function": get_user_details,
            "name": "get_user_details",
            "description": "Get detailed information about a specific user by profile ID",
            "parameters": GetUserDetailsParams
        }

    def _create_update_user_tool(self):
        """Create SDK-compatible user update tool"""
        async def update_user(params: UpdateUserParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Update an existing user account"""
            try:
                # Convert Pydantic model to dict for existing tool
                update_params = params.model_dump(exclude_unset=True)

                # Add context if available
                if context:
                    update_params['context'] = context

                # Call existing tool
                result = await update_user_tool(UpdateUserParams(**update_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"User update failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error updating user: {str(e)}"
                )

        return {
            "function": update_user,
            "name": "update_user",
            "description": "Update user account information including email, name, role, and status",
            "parameters": UpdateUserParams
        }

    def _create_delete_user_tool(self):
        """Create SDK-compatible user deletion tool"""
        async def delete_user(params: DeleteUserParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Delete a user account"""
            try:
                # Convert Pydantic model to dict for existing tool
                delete_params = params.model_dump(exclude_unset=True)

                # Call existing tool
                result = await delete_user_tool(DeleteUserParams(**delete_params))

                if result.success:
                    return ContractToolResult(
                        success=True,
                        message=result.message,
                        data=result.data
                    )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"User deletion failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error deleting user: {str(e)}"
                )

        return {
            "function": delete_user,
            "name": "delete_user",
            "description": "Delete a user account by profile ID",
            "parameters": DeleteUserParams
        }

    def _create_search_users_tool(self):
        """Create SDK-compatible user search tool"""
        async def search_users(params: SearchUsersParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Search for users by various criteria"""
            try:
                # Convert Pydantic model to dict for existing tool
                search_params = params.model_dump(exclude_unset=True)

                # Call existing tool
                result = await search_users_tool(SearchUsersParams(**search_params))

                if result.success:
                    users = result.data
                    if users:
                        user_summaries = []
                        for user in users[:5]:  # Limit to 5 results
                            summary = f"- {user.get('first_name', '')} {user.get('last_name', '')} ({user.get('email', '')}) - {user.get('role', '')}"
                            user_summaries.append(summary)

                        return ContractToolResult(
                            success=True,
                            message=f"Found {len(users)} users:\n" + "\n".join(user_summaries),
                            data={"users": users, "count": len(users)}
                        )
                    else:
                        return ContractToolResult(
                            success=True,
                            message="No users found matching the search criteria.",
                            data={"users": [], "count": 0}
                        )
                else:
                    return ContractToolResult(
                        success=False,
                        message=f"Search failed: {result.message}"
                    )

            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error searching users: {str(e)}"
                )

        return {
            "function": search_users,
            "name": "search_users",
            "description": "Search for users by email, name, role, or status",
            "parameters": SearchUsersParams
        }

    def _create_get_all_clients_with_contracts_tool(self):
        """Create SDK-compatible get all clients with contracts tool"""
        async def get_all_clients_with_contracts(context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get all clients with their contracts information"""
            try:
                # Call existing tool
                result = await get_all_clients_with_contracts_tool()
                    
                return result
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting all clients with contracts: {str(e)}"
                )

        return {
            "function": get_all_clients_with_contracts,
            "name": "get_all_clients_with_contracts",
            "description": "Get all clients in the system with their contract information",
            "parameters": {}
        }

    def _create_get_contracts_for_next_month_billing_tool(self):
        """Create SDK-compatible get contracts for next month billing tool"""
        
        class BillingContractsParams(BaseModel):
            client_name: Optional[str] = Field(None, description="Client name to filter contracts (optional, if not provided shows all clients)")

        async def get_contracts_for_next_month_billing(params: Optional[BillingContractsParams] = None, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get contracts with upcoming billing dates in the next month"""
            try:
                client_name = None
                if params:
                    client_name = params.client_name
                
                print(f"🔍 BILLING QUERY DEBUG: SDK tool called with client_name='{client_name}', context keys: {list(context.keys()) if context else 'None'}")
                
                # Call existing tool
                result = await get_contracts_for_next_month_billing_tool(client_name=client_name, context=context)
                
                print(f"🔍 BILLING QUERY DEBUG: Tool result success={result.success}, message length={len(result.message) if result.message else 0}")
                
                return result
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting contracts for next month billing: {str(e)}"
                )

        return {
            "function": get_contracts_for_next_month_billing,
            "name": "get_contracts_for_next_month_billing", 
            "description": "Get contracts with upcoming billing dates in the next month. If client_name is provided, filters to that client only. If not provided, shows all clients.",
            "parameters": BillingContractsParams
        }

    def _create_get_contracts_by_amount_tool(self):
        """Create SDK-compatible get contracts by amount tool"""
        
        class ContractsByAmountParams(BaseModel):
            min_amount: Optional[float] = Field(None, description="Minimum contract amount to filter by")
            max_amount: Optional[float] = Field(None, description="Maximum contract amount to filter by")
            client_name: Optional[str] = Field(None, description="Client name to filter contracts (optional)")

        async def get_contracts_by_amount(params: Optional[ContractsByAmountParams] = None, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
            """Get contracts filtered by amount range"""
            try:
                min_amount = None
                max_amount = None
                client_name = None
                
                if params:
                    min_amount = params.min_amount
                    max_amount = params.max_amount
                    client_name = params.client_name
                
                # Call existing tool
                result = await get_contracts_by_amount_tool(min_amount=min_amount, max_amount=max_amount, client_name=client_name, context=context)
                
                return result
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"Error getting contracts by amount: {str(e)}"
                )

        return {
            "function": get_contracts_by_amount,
            "name": "get_contracts_by_amount",
            "description": "Get contracts filtered by amount range. Use min_amount for 'more than' queries, max_amount for 'less than' queries, or both for range queries.",
            "parameters": ContractsByAmountParams
        }
