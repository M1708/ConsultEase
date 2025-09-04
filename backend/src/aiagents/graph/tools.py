
import json
from typing import Dict, Any, List

from src.aiagents.graph.state import AgentState

# --- Import all tool functions and params from the existing tool files ---
from src.aiagents.tools.contract_tools import (
    create_client_tool, search_clients_tool, get_all_clients_tool,
    get_contract_details_tool, analyze_contract_tool, smart_create_contract_tool,
    smart_contract_document_tool, get_contracts_by_client_tool, get_all_contracts_tool,
    get_all_clients_with_contracts_tool, get_contracts_by_billing_date_tool, update_contract_tool, 
    search_contracts_tool, get_contracts_for_next_month_billing_tool,
    CreateClientParams, SmartContractParams, ContractDocumentParams, UpdateContractParams, SearchContractsParams, ContractToolResult
)
from  src.aiagents.tools.client_tools import (
    update_client_tool as update_client_tool_client, UpdateClientParams as UpdateClientParamsClient, ClientToolResult,
    get_client_details_tool
)
from src.aiagents.tools.employee_tools import (
    create_employee_tool, update_employee_tool, search_employees_tool,
    get_employee_details_tool, get_all_employees_tool, search_profiles_by_name_tool,
    CreateEmployeeParams, UpdateEmployeeParams
)
# ... import other tools for other agents as they are integrated

# --- Tool Wrappers (migrated from ContractAgent) ---
# These wrappers handle the messy work of unpacking arguments and calling the core tool function.

def _create_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = CreateClientParams(**kwargs)
    result = create_client_tool(params, context, db)
    return result.model_dump()

def _get_all_clients_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_clients_tool(db)
    return result.model_dump()

def _get_contract_details_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    contract_id = kwargs.get("contract_id")
    client_name = kwargs.get("client_name")
    result = get_contract_details_tool(contract_id, client_name, db)
    return result.model_dump()

def _get_client_details_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = get_client_details_tool(client_name, db)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

def _search_clients_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    limit = kwargs.get("limit", 10)
    result = search_clients_tool(search_term, limit, db)
    return result.model_dump()

def _analyze_contract_wrapper(**kwargs) -> Dict[str, Any]:
    contract_text = kwargs.get("contract_text")
    result = analyze_contract_tool(contract_text)
    return result.model_dump()

def _smart_create_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating contracts with comprehensive response details"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = SmartContractParams(**kwargs)
    result = smart_create_contract_tool(params, context, db)
    
    # If successful, enhance the response with comprehensive details
    if result.success and result.data:
        contract_data = result.data
        
        # Get additional client information for context
        try:
            if db is None:
                from src.database.core.database import get_db
                db = next(get_db())
            
            from src.database.core.models import Client, Contract
            
            # Get the created contract for full details
            contract_id = contract_data.get('contract_id')
            if contract_id:
                contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
                client = db.query(Client).filter(Client.client_id == contract.client_id).first() if contract else None
                
                if contract and client:
                    enhanced_data = {
                        "operation": "create_contract",
                        "contract": {
                            "contract_id": contract.contract_id,
                            "client_id": contract.client_id,
                            "client_name": client.client_name,
                            "contract_type": contract.contract_type,
                            "status": contract.status,
                            "original_amount": float(contract.original_amount) if contract.original_amount else None,
                            "current_amount": float(contract.current_amount) if contract.current_amount else None,
                            "billing_frequency": contract.billing_frequency,
                            "start_date": contract.start_date.strftime("%Y-%m-%d") if contract.start_date else None,
                            "end_date": contract.end_date.strftime("%Y-%m-%d") if contract.end_date else None,
                            "billing_prompt_next_date": contract.billing_prompt_next_date.strftime("%Y-%m-%d") if contract.billing_prompt_next_date else None,
                            "notes": contract.notes,
                            "created_at": contract.created_at.strftime("%Y-%m-%d %H:%M:%S") if contract.created_at else None,
                            "updated_at": contract.updated_at.strftime("%Y-%m-%d %H:%M:%S") if contract.updated_at else None
                        },
                        "client": {
                            "client_id": client.client_id,
                            "client_name": client.client_name,
                            "industry": client.industry,
                            "company_size": client.company_size,
                            "primary_contact_name": client.primary_contact_name,
                            "primary_contact_email": client.primary_contact_email
                        },
                        "summary": {
                            "total_contract_value": float(contract.original_amount) if contract.original_amount else None,
                            "contract_duration_months": _calculate_contract_duration(
                                contract.start_date.strftime("%Y-%m-%d") if contract.start_date else None,
                                contract.end_date.strftime("%Y-%m-%d") if contract.end_date else None
                            ),
                            "next_billing_date": contract.billing_prompt_next_date.strftime("%Y-%m-%d") if contract.billing_prompt_next_date else None,
                            "billing_frequency": contract.billing_frequency,
                            "contract_status": contract.status
                        }
                    }
                    
                    return {
                        "success": True,
                        "message": f"✅ Successfully created contract for '{client.client_name}'. Contract ID: {contract.contract_id}",
                        "data": enhanced_data
                    }
        except Exception as e:
            # If enhancement fails, fall back to original response but log the error
            print(f"Warning: Could not enhance contract response: {str(e)}")
    
    # Return original response if enhancement fails or if not successful
    return result.model_dump()

def _get_contracts_by_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = get_contracts_by_client_tool(client_name, db)
    return result.model_dump()

def _get_all_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_contracts_tool(db)
    return result.model_dump()

def _get_contracts_by_billing_date_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    result = get_contracts_by_billing_date_tool(start_date, end_date, db)
    return result.model_dump()

def _update_contract_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateContractParams(**kwargs)

def _get_contracts_for_next_month_billing_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    result = get_contracts_for_next_month_billing_tool(context, db)
    return result.model_dump()

def _update_contract_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateContractParams(**kwargs)
    result = update_contract_tool(params, context, db)
    return result.model_dump()

def _update_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateClientParamsClient(**kwargs)
    result = update_client_tool_client(params, context, db)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

def _smart_contract_document_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    params = ContractDocumentParams(**kwargs)
    result = smart_contract_document_tool(params, db)
    return result.model_dump()

def _get_all_clients_with_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_clients_with_contracts_tool(db)
    return result.model_dump()

def _create_client_and_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating a client and then a contract in sequence with comprehensive response"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First create the client
        client_params = CreateClientParams(
            client_name=kwargs.get('client_name'),
            primary_contact_name=kwargs.get('primary_contact_name'),
            primary_contact_email=kwargs.get('primary_contact_email'),
            industry=kwargs.get('industry', 'Manufacturing'),  # Default to Manufacturing for business clients
            company_size=kwargs.get('company_size', 'Large'),  # Infer from context if not provided
            notes=kwargs.get('notes')
        )
        
        client_result = create_client_tool(client_params, context, db)
        if not client_result.success:
            return client_result.model_dump()
        
        # Then create the contract with enhanced parameters
        contract_params = SmartContractParams(
            client_name=kwargs.get('client_name'),
            contract_type=kwargs.get('contract_type', 'Fixed'),
            original_amount=kwargs.get('original_amount'),
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
            billing_frequency=kwargs.get('billing_frequency', 'Monthly'),
            billing_prompt_next_date=kwargs.get('billing_prompt_next_date'),
            notes=kwargs.get('contract_notes')
        )
        
        contract_result = smart_create_contract_tool(contract_params, context, db)
        
        # Enhanced response with comprehensive details
        if contract_result.success:
            # Extract all client details
            client_data = client_result.data or {}
            contract_data = contract_result.data or {}
            
            return {
                "success": True,
                "message": f"✅ Successfully created client '{kwargs.get('client_name')}' and contract. Client ID: {client_data.get('client_id')}, Contract ID: {contract_data.get('contract_id')}",
                "data": {
                    "operation": "create_client_and_contract",
                    "client": {
                        "client_id": client_data.get('client_id'),
                        "client_name": client_data.get('client_name'),
                        "industry": client_data.get('industry'),
                        "primary_contact_name": kwargs.get('primary_contact_name'),
                        "primary_contact_email": kwargs.get('primary_contact_email'),
                        "company_size": kwargs.get('company_size', 'Large'),
                        "notes": kwargs.get('notes'),
                        "status": "Active"
                    },
                    "contract": {
                        "contract_id": contract_data.get('contract_id'),
                        "client_id": client_data.get('client_id'),
                        "client_name": contract_data.get('client_name'),
                        "contract_type": contract_data.get('contract_type'),
                        "status": contract_data.get('status', 'draft'),
                        "original_amount": float(contract_data.get('original_amount')) if contract_data.get('original_amount') else kwargs.get('original_amount'),
                        "current_amount": float(contract_data.get('original_amount')) if contract_data.get('original_amount') else kwargs.get('original_amount'),
                        "billing_frequency": kwargs.get('billing_frequency', 'Monthly'),
                        "start_date": kwargs.get('start_date'),
                        "end_date": kwargs.get('end_date'),
                        "billing_prompt_next_date": kwargs.get('billing_prompt_next_date'),
                        "notes": kwargs.get('contract_notes')
                    },
                    "summary": {
                        "total_contract_value": float(contract_data.get('original_amount')) if contract_data.get('original_amount') else kwargs.get('original_amount'),
                        "contract_duration_months": _calculate_contract_duration(kwargs.get('start_date'), kwargs.get('end_date')),
                        "next_billing_date": kwargs.get('billing_prompt_next_date'),
                        "created_records": ["client", "contract"]
                    }
                }
            }
        else:
            return contract_result.model_dump()
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create client and contract: {str(e)}"
        }

def _calculate_contract_duration(start_date: str, end_date: str) -> int:
    """Helper function to calculate contract duration in months"""
    try:
        if not start_date or not end_date:
            return None
        
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Calculate the difference in months
        diff = relativedelta(end, start)
        return diff.years * 12 + diff.months
    except:
        return None

def _update_contract_by_id_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating contract by ID instead of client name"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    contract_id = kwargs.get('contract_id')
    
    try:
        if db is None:
            from src.database.core.database import get_db
            db = next(get_db())
        
        # Find the contract by ID
        from src.database.core.models import Contract, Client
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        
        if not contract:
            return {
                "success": False,
                "message": f"❌ Contract with ID {contract_id} not found."
            }
        
        # Get the client name
        client = db.query(Client).filter(Client.client_id == contract.client_id).first()
        if not client:
            return {
                "success": False,
                "message": f"❌ Client for contract ID {contract_id} not found."
            }
        
        # Use the existing update_contract_tool with client name
        params = UpdateContractParams(
            client_name=client.client_name,
            contract_id=contract_id,
            billing_prompt_next_date=kwargs.get('billing_prompt_next_date'),
            status=kwargs.get('status'),
            notes=kwargs.get('notes')
        )
        
        result = update_contract_tool(params, context, db)
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to update contract by ID: {str(e)}"
        }

def _search_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching contracts by various criteria"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = SearchContractsParams(**kwargs)
    result = search_contracts_tool(params, db)
    return result.model_dump()

# --- Employee Tool Wrappers ---
def _create_employee_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for creating a new employee record with enhanced natural language processing"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # If employee_name is provided, first search for the profile
        if kwargs.get('employee_name') and not kwargs.get('profile_id'):
            # Search for the profile first
            search_result = search_profiles_by_name_tool(kwargs['employee_name'], db)
            if search_result.success and search_result.data.get('profiles'):
                profiles = search_result.data['profiles']
                if len(profiles) == 1:
                    # Use the found profile
                    kwargs['profile_id'] = profiles[0]['profile_id']
                elif len(profiles) > 1:
                    # Multiple profiles found - return error with options
                    profile_names = [f"{p['first_name']} {p['last_name']} ({p['email']})" for p in profiles]
                    return {
                        "success": False,
                        "message": f"❌ Multiple profiles found for '{kwargs['employee_name']}': {', '.join(profile_names)}. Please specify which profile to use.",
                        "data": {"profiles": profiles}
                    }
                else:
                    # No profiles found
                    return {
                        "success": False,
                        "message": f"❌ No user profile found for '{kwargs['employee_name']}'. Please create a user profile first before creating an employee record.",
                        "data": {"profiles": []}
                    }
        
        # Handle hire date parsing from natural language
        if kwargs.get('hire_date') and not kwargs['hire_date'].count('-') == 2:
            # Try to parse natural language date like "15th Aug 2025"
            import re
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', kwargs['hire_date'], re.IGNORECASE)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3)
                month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                             "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                month_num = month_map.get(month.lower()[:3])
                if month_num:
                    kwargs['hire_date'] = f"{year}-{month_num}-{day.zfill(2)}"
        
        params = CreateEmployeeParams(**kwargs)
        result = create_employee_tool(params, context, db)
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create employee: {str(e)}",
            "data": None
        }

def _update_employee_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating an existing employee record"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateEmployeeParams(**kwargs)
    result = update_employee_tool(params, context, db)
    return result.model_dump()

def _search_employees_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching employees by various criteria"""
    db = kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    limit = kwargs.get("limit", 50)
    result = search_employees_tool(search_term, limit, db)
    return result.model_dump()



def _get_employee_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for getting detailed employee information"""
    db = kwargs.pop('db', None)
    employee_id = kwargs.get("employee_id")
    result = get_employee_details_tool(employee_id, db)
    return result.model_dump()

def _get_all_employees_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for getting all employees in the system"""
    db = kwargs.pop('db', None)
    result = get_all_employees_tool(db)
    return result.model_dump()

def _search_profiles_by_name_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching user profiles by name"""
    db = kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    result = search_profiles_by_name_tool(search_term, db)
    return result.model_dump()

def _update_employee_from_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating employee from natural language details - complete solution for employee updates"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First search for the employee by name
        employee_name = kwargs.get('employee_name')
        
        if not employee_name:
            return {
                "success": False,
                "message": "❌ Employee name is required."
            }
        
        # FIXED: First search for the profile by name to get profile_id
        profile_search_result = search_profiles_by_name_tool(employee_name, db)
        
        if not profile_search_result.success or not profile_search_result.data.get('profiles'):
            return {
                "success": False,
                "message": f"❌ No user profile found for '{employee_name}'. Please check the name and try again."
            }
        
        profiles = profile_search_result.data['profiles']
        
        if len(profiles) > 1:
            # Multiple profiles found - ask for clarification
            profile_names = [f"{p['first_name']} {p['last_name']} ({p['email']})" for p in profiles]
            return {
                "success": False,
                "message": f"❌ Multiple profiles found for '{employee_name}': {', '.join(profile_names)}. Please be more specific."
            }
        
        # Use the found profile to get the employee record
        profile_id = profiles[0]['profile_id']
        
        # Now search for the employee using the profile_id
        if db is None:
            from src.database.core.database import get_db
            db = next(get_db())
        
        from src.database.core.models import Employee
        employee = db.query(Employee).filter(Employee.profile_id == profile_id).first()
        
        if not employee:
            return {
                "success": False,
                "message": f"❌ No employee record found for '{employee_name}'. The profile exists but no employee record has been created."
            }
        
        # Use the found employee
        employee_id = employee.employee_id
        
        # Handle hire date parsing from natural language
        hire_date = kwargs.get('hire_date')
        
        if hire_date and not hire_date.count('-') == 2:
            # Try to parse natural language date like "15th Aug 2025"
            import re
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', hire_date, re.IGNORECASE)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3)
                month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                             "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                month_num = month_map.get(month.lower()[:3])
                if month_num:
                    hire_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        # Handle termination date parsing from natural language
        termination_date = kwargs.get('termination_date')
        
        if termination_date and not termination_date.count('-') == 2:
            # Try to parse natural language date
            import re
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', termination_date, re.IGNORECASE)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3)
                month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                             "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                month_num = month_map.get(month.lower()[:3])
                if month_num:
                    termination_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        # Update employee using the existing update_employee tool
        employee_params_dict = {
            'employee_id': employee_id,
            'employee_number': kwargs.get('employee_number'),
            'job_title': kwargs.get('job_title'),
            'department': kwargs.get('department'),
            'employment_type': kwargs.get('employment_type'),
            'full_time_part_time': kwargs.get('full_time_part_time'),
            'committed_hours': kwargs.get('committed_hours'),
            'hire_date': hire_date,
            'termination_date': termination_date,
            'rate_type': kwargs.get('rate_type'),
            'rate': kwargs.get('rate'),
            'currency': kwargs.get('currency'),
            'nda_file_link': kwargs.get('nda_file_link'),
            'contract_file_link': kwargs.get('contract_file_link')
        }
        
        # Remove None values to avoid updating fields that weren't specified
        employee_params_dict = {k: v for k, v in employee_params_dict.items() if v is not None}
        
        employee_params = UpdateEmployeeParams(**employee_params_dict)
        result = update_employee_tool(employee_params, context, db)
        
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to update employee from details: {str(e)}",
            "data": None
        }

def _create_employee_from_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating employee from natural language details - complete solution for employee creation"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First search for the employee profile by name
        employee_name = kwargs.get('employee_name')
        
        if not employee_name:
            return {
                "success": False,
                "message": "❌ Employee name is required."
            }
        
        # Search for the profile
        profile_search_result = search_profiles_by_name_tool(employee_name, db)
        
        if not profile_search_result.success or not profile_search_result.data.get('profiles'):
            return {
                "success": False,
                "message": f"❌ No user profile found for '{employee_name}'. Please create a user profile first before creating an employee record."
            }
        
        profiles = profile_search_result.data['profiles']
        
        if len(profiles) > 1:
            # Multiple profiles found - ask for clarification
            profile_names = [f"{p['first_name']} {p['last_name']} ({p['email']})" for p in profiles]
            return {
                "success": False,
                "message": f"❌ Multiple profiles found for '{employee_name}': {', '.join(profile_names)}. Please specify which profile to use."
            }
        
        # Use the found profile
        profile_id = profiles[0]['profile_id']
        
        # ENHANCED: Use the existing parse_employee_details_from_message function for better NLP
        from src.aiagents.tools.employee_tools import parse_employee_details_from_message
        
        # Create a synthetic message from the provided parameters for parsing
        synthetic_message = f"Create employee {employee_name}"
        if kwargs.get('job_title'):
            synthetic_message += f" as {kwargs.get('job_title')}"
        if kwargs.get('employment_type'):
            synthetic_message += f" {kwargs.get('employment_type')}"
        if kwargs.get('full_time_part_time'):
            synthetic_message += f" {kwargs.get('full_time_part_time').replace('_', '-')}"
        if kwargs.get('department'):
            synthetic_message += f" in {kwargs.get('department')} department"
        if kwargs.get('salary'):
            synthetic_message += f" with monthly salary ${kwargs.get('salary')}"
        elif kwargs.get('rate') and kwargs.get('rate_type'):
            if kwargs.get('rate_type') == 'hourly':
                synthetic_message += f" at ${kwargs.get('rate')} hourly"
            else:
                synthetic_message += f" with ${kwargs.get('rate')} {kwargs.get('rate_type')}"
        if kwargs.get('hire_date'):
            synthetic_message += f" starting {kwargs.get('hire_date')}"
        
        # Parse additional details from the synthetic message
        parsed_details = parse_employee_details_from_message(synthetic_message)
        
        # Enhanced hire date parsing from natural language
        hire_date = kwargs.get('hire_date')
        if hire_date and not (hire_date.count('-') == 2):
            # Try multiple date parsing patterns
            import re
            from datetime import datetime
            
            # Pattern 1: "15th Aug 2025", "1st January 2026"
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', hire_date, re.IGNORECASE)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3)
                month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                             "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                month_num = month_map.get(month.lower()[:3])
                if month_num:
                    hire_date = f"{year}-{month_num}-{day.zfill(2)}"
            
            # Pattern 2: "January 1st 2026", "August 15th 2025"
            elif re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})', hire_date, re.IGNORECASE):
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})', hire_date, re.IGNORECASE)
                month = date_match.group(1)
                day = date_match.group(2)
                year = date_match.group(3)
                month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                             "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
                month_num = month_map.get(month.lower()[:3])
                if month_num:
                    hire_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        # Enhanced job title processing
        job_title = kwargs.get('job_title')
        if job_title:
            # Capitalize job titles properly
            job_title = ' '.join(word.capitalize() for word in job_title.split())
        
        # Enhanced employment type processing
        employment_type = kwargs.get('employment_type')
        if employment_type:
            employment_type = employment_type.lower()
        
        # Enhanced full_time_part_time processing
        full_time_part_time = kwargs.get('full_time_part_time')
        if full_time_part_time:
            if full_time_part_time.lower() in ['fulltime', 'full-time', 'full_time']:
                full_time_part_time = 'full_time'
            elif full_time_part_time.lower() in ['parttime', 'part-time', 'part_time']:
                full_time_part_time = 'part_time'
        
        # Enhanced rate and salary processing
        final_rate = kwargs.get('rate')
        final_rate_type = kwargs.get('rate_type')
        
        # If salary is provided, use it as the rate with salary type
        if kwargs.get('salary'):
            final_rate = kwargs.get('salary')
            final_rate_type = "salary"
        
        # Use parsed details as fallbacks if not provided in kwargs
        if not final_rate_type and parsed_details.get('rate_type'):
            final_rate_type = parsed_details['rate_type']
        if not final_rate and parsed_details.get('rate'):
            final_rate = parsed_details['rate']
        if not employment_type and parsed_details.get('employment_type'):
            employment_type = parsed_details['employment_type']
        if not full_time_part_time and parsed_details.get('full_time_part_time'):
            full_time_part_time = parsed_details['full_time_part_time']
        if not hire_date and parsed_details.get('hire_date'):
            hire_date = parsed_details['hire_date']
        
        # Create employee using the existing create_employee tool
        employee_params_dict = {
            'profile_id': profile_id,
            'employee_number': kwargs.get('employee_number'),
            'job_title': job_title,
            'department': kwargs.get('department'),
            'employment_type': employment_type,
            'full_time_part_time': full_time_part_time,
            'committed_hours': kwargs.get('committed_hours'),
            'hire_date': hire_date,
            'termination_date': kwargs.get('termination_date'),
            'rate_type': final_rate_type,
            'rate': final_rate,
            'currency': kwargs.get('currency', 'USD'),
            'nda_file_link': kwargs.get('nda_file_link'),
            'contract_file_link': kwargs.get('contract_file_link')
        }
        
        # Remove None values to avoid validation errors
        employee_params_dict = {k: v for k, v in employee_params_dict.items() if v is not None}
        
        employee_params = CreateEmployeeParams(**employee_params_dict)
        result = create_employee_tool(employee_params, context, db)
        
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create employee from details: {str(e)}",
            "data": None
        }



# --- Central Tool Registry ---
TOOL_REGISTRY = {
    "create_client": _create_client_wrapper,
    "search_clients": _search_clients_wrapper,
    "get_all_clients": _get_all_clients_wrapper,
    "get_all_clients_with_contracts": _get_all_clients_with_contracts_wrapper,
    "get_client_details": _get_client_details_wrapper,
    "analyze_contract": _analyze_contract_wrapper,
    "create_contract": _smart_create_contract_wrapper,
    "get_client_contracts": _get_contracts_by_client_wrapper,
    "get_all_contracts": _get_all_contracts_wrapper,
    "get_contract_details": _get_contract_details_wrapper,
    "get_contracts_by_billing_date": _get_contracts_by_billing_date_wrapper,
    "search_contracts": _search_contracts_wrapper,
    "update_contract": _update_contract_wrapper,
    "get_contracts_for_next_month_billing": _get_contracts_for_next_month_billing_wrapper,
    "update_client": _update_client_wrapper,
    "manage_contract_document": _smart_contract_document_wrapper,
    "create_client_and_contract": _create_client_and_contract_wrapper,
    "update_contract_by_id": _update_contract_by_id_wrapper,
    
    # Employee tools
    "create_employee": _create_employee_wrapper,
    "create_employee_from_details": _create_employee_from_details_wrapper,
    "update_employee": _update_employee_wrapper,
    "update_employee_from_details": _update_employee_from_details_wrapper,
    "search_employees": _search_employees_wrapper,
    "get_employee_details": _get_employee_details_wrapper,
    "get_all_employees": _get_all_employees_wrapper,
    "search_profiles_by_name": _search_profiles_by_name_wrapper,

    
    # Other tools will be registered here
}

def tool_executor_node(state: AgentState) -> Dict:
    """
    Executes tools requested by an agent. This node is the central tool handler for the entire graph.
    It takes tool calls from the last message in the state, executes them, and returns the results.
    """
    last_message = state['messages'][-1]
    tool_calls = getattr(last_message, 'tool_calls', [])
    
    if not tool_calls:
        return {"messages": []}

    # The database session should be in the state's data payload, but context is in state.context
    db_session = state.get('data', {}).get('database')
    context = state.get('context', {})

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name

        if tool_name not in TOOL_REGISTRY:
            result_content = json.dumps({"error": f"Tool '{tool_name}' not found in registry."})
        else:
            try:
                tool_function = TOOL_REGISTRY[tool_name]
                args = json.loads(tool_call.function.arguments)
                
                # Add the database session and context to the arguments for the wrapper
                args['db'] = db_session
                args['context'] = context
                
                output = tool_function(**args)
                result_content = json.dumps(output)

            except Exception as e:
                result_content = json.dumps({"error": str(e), "tool_name": tool_name})

        results.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": tool_name,
            "content": result_content,
        })

    return {"messages": results}
