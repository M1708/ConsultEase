
import json
from sre_parse import ANY
from typing import Dict, Any, List, Optional
import re
from datetime import datetime
from sqlalchemy import select
import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta
      
from src.database.core.models import Client, Contract
from src.aiagents.graph.state import AgentState
from src.database.core.database import get_ai_db, get_db

# --- Import all tool functions and params from the existing tool files ---
from src.aiagents.tools.contract_tools import (
    create_client_tool, search_clients_tool, get_all_clients_tool,
    get_contract_details_tool, analyze_contract_tool, smart_create_contract_tool,
    smart_contract_document_tool, upload_contract_document_tool, delete_contract_document_tool, delete_contract_tool, delete_client_tool, get_contracts_by_client_tool, get_all_contracts_tool,
    get_all_clients_with_contracts_tool, get_contracts_by_billing_date_tool, update_contract_tool, 
    search_contracts_tool, get_contracts_for_next_month_billing_tool, get_contracts_with_null_billing_tool, get_contracts_by_amount_tool, get_contracts_with_documents_tool,
    CreateClientParams, SmartContractParams, ContractDocumentParams, UploadContractDocumentParams, DeleteContractDocumentParams, DeleteContractParams, DeleteClientParams, UpdateContractParams, SearchContractsParams, ContractToolResult
)
from  src.aiagents.tools.client_tools import (
    update_client_tool as update_client_tool_client, UpdateClientParams as UpdateClientParamsClient, ClientToolResult,
    get_client_details_tool
)
from src.aiagents.tools.employee_tools import (
    create_employee_tool, update_employee_tool, search_employees_tool,
    get_employee_details_tool, get_all_employees_tool, search_profiles_by_name_tool,
    delete_employee_tool, CreateEmployeeParams, UpdateEmployeeParams, DeleteEmployeeParams
)
from src.database.core.models import Employee
# ... import other tools for other agents as they are integrated

# --- Tool Wrappers (migrated from ContractAgent) ---
# These wrappers handle the messy work of unpacking arguments and calling the core tool function.

async def _create_client_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = CreateClientParams(**kwargs)
    result = await create_client_tool(params, context)
    return result.model_dump()

async def _get_all_clients_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    result = await get_all_clients_tool()
    return result.model_dump()

async def _get_contract_details_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    contract_id = kwargs.get("contract_id")
    client_name = kwargs.get("client_name")
    result = await get_contract_details_tool(contract_id, client_name)
    return result.model_dump()

async def _get_client_details_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = await get_client_details_tool(client_name)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

async def _search_clients_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    limit = kwargs.get("limit", 10)
    result = await search_clients_tool(search_term, limit)
    return result.model_dump()

async def _analyze_contract_wrapper(**kwargs) -> Dict[str, Any]:
    contract_text = kwargs.get("contract_text")
    result = await analyze_contract_tool(contract_text)
    return result.model_dump()

async def _smart_create_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating contracts with comprehensive response details"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    # Ensure contract_type is set - infer from context if missing
    if not kwargs.get('contract_type'):
        if kwargs.get('original_amount'):
            kwargs['contract_type'] = 'Fixed'  # Default for contracts with specific amounts
        else:
            kwargs['contract_type'] = 'Fixed'  # Default fallback
    
    params = SmartContractParams(**kwargs)
    print(f"🔍 DEBUG: _smart_create_contract_wrapper - creating contract for client: {kwargs.get('client_name')}")
    result = await smart_create_contract_tool(params, context)
    print(f"🔍 DEBUG: _smart_create_contract_wrapper - base tool result: success={getattr(result, 'success', None)}")
    
    # If successful, enhance the response with comprehensive details
    if result and getattr(result, 'success', False) and getattr(result, 'data', None):
        contract_data = result.data
        print(f"🔍 DEBUG: _smart_create_contract_wrapper - contract_data keys: {list(contract_data.keys())}")
        
        # Get additional client information for context
        try:
            async with get_ai_db() as session:
            # Get the created contract for full details
                contract_id = contract_data.get('contract_id')
                if not contract_id:
                    # Sometimes contract_id is nested or typed as str in base tool
                    nested_id = (contract_data.get('contract', {}) or {}).get('contract_id')
                    contract_id = nested_id or contract_id
                print(f"🔍 DEBUG: _smart_create_contract_wrapper - resolved contract_id: {contract_id}")
                if contract_id:
                # Fetch contract
                    contract_stmt = select(Contract).where(Contract.contract_id == contract_id)
                    contract_result = await session.execute(contract_stmt)
                    contract = contract_result.scalars().first()

                    # Fetch client
                    client = None
                    if contract:
                        client_stmt = select(Client).where(Client.client_id == contract.client_id)
                        client_result = await session.execute(client_stmt)
                        client = client_result.scalars().first()
                    
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
                        
                        print(f"🔍 DEBUG: _smart_create_contract_wrapper - returning enhanced payload with contract_id={contract.contract_id}")
                        return {
                            "success": True,
                            "message": f"✅ Successfully created contract for '{client.client_name}'. Contract ID: {contract.contract_id}",
                            "data": enhanced_data
                        }
        except Exception as e:
            # If enhancement fails, fall back to original response but log the error
            print(f"Warning: Could not enhance contract response: {str(e)}")
    # Return original response if enhancement fails or if not successful
    try:
        fallback = result.model_dump()
        print(f"🔍 DEBUG: _smart_create_contract_wrapper - returning fallback payload (not enhanced)")
        return fallback
    except Exception:
        # Last resort
        print("❌ DEBUG: _smart_create_contract_wrapper - no valid result to return, returning error")
        return {"success": False, "message": "Failed to create contract", "data": None}

async def _get_contracts_by_client_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = await get_contracts_by_client_tool(client_name)
    return result.model_dump()

async def _get_all_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    result = await get_all_contracts_tool()
    return result.model_dump()

async def _get_contracts_by_billing_date_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    result = await get_contracts_by_billing_date_tool(start_date, end_date)
    return result.model_dump()

async def _update_contract_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    # Extract field from original user request if available
    if context and context.get('original_user_request'):
        print(f"🔍 FIELD EXTRACTION: Original user request: {context['original_user_request']}")
        
        # Import the field extraction function
        from src.aiagents.agents_sdk.tool_definitions import _extract_field_from_request
        extracted_field = _extract_field_from_request(context['original_user_request'])
        if extracted_field:
            print(f"🔍 FIELD EXTRACTION: Extracted field: {extracted_field}")
            # Update kwargs with extracted field
            kwargs.update(extracted_field)
            print(f"🔍 FIELD EXTRACTION: Updated kwargs with extracted field: {extracted_field}")
        else:
            print(f"🔍 FIELD EXTRACTION: No field extracted from request")
    else:
        print(f"🔍 FIELD EXTRACTION: No original_user_request in context")
    
    params = UpdateContractParams(**kwargs)
    result = await update_contract_tool(params, context)
    return result.model_dump()

async def _get_contracts_for_next_month_billing_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    client_name = kwargs.pop('client_name', None)
    if context is None:
        from datetime import date
        context = {'today': date.today()}
    result = await get_contracts_for_next_month_billing_tool(client_name=client_name, context=context)
    return result.model_dump()

async def _get_contracts_with_null_billing_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    client_name = kwargs.pop('client_name', None)
    if context is None:
        context = {}
    result = await get_contracts_with_null_billing_tool(client_name=client_name, context=context)
    return result.model_dump()

async def _get_contracts_by_amount_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    client_name = kwargs.pop('client_name', None)
    min_amount = kwargs.pop('min_amount', None)
    max_amount = kwargs.pop('max_amount', None)
    if context is None:
        context = {}
    result = await get_contracts_by_amount_tool(min_amount=min_amount, max_amount=max_amount, client_name=client_name, context=context)
    return result.model_dump()

async def _get_contracts_with_documents_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    client_name = kwargs.pop('client_name', None)
    if context is None:
        context = {}
    params = SearchContractsParams(client_name=client_name)
    result = await get_contracts_with_documents_tool(params, context)
    return result.model_dump()


async def _update_client_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateClientParamsClient(**kwargs)
    result = await update_client_tool_client(params, context)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

async def _smart_contract_document_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    params = ContractDocumentParams(**kwargs)
    result = await smart_contract_document_tool(params)
    return result.model_dump()

async def _upload_contract_document_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for uploading contract documents with file data replacement"""
    # REVERT: If parameter handling issues persist, revert to original logic
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    print(f"🔍 DEBUG: upload_contract_document_wrapper - context has file_info: {context and 'file_info' in context}")

    # ENHANCED PARAMETER HANDLING: Better file data replacement and validation
    file_info = (context or {}).get('file_info')

    # Gracefully handle the case when the user didn't upload a file
    if (not file_info) and (
        not kwargs.get('file_data') or kwargs.get('file_data') in ["<base64_encoded_data>", "[USE_ACTUAL_FILE_DATA_FROM_CONTEXT]"]
    ):
        # Only the client name is required to start the flow; ask user to attach file
        if not kwargs.get('client_name'):
            return {
                "success": False,
                "message": "❌ Please specify the client name to upload a document for.",
                "data": None
            }
        return {
            "success": False,
            "message": (
                "📎 **No document attached.**\n\n"
                "To upload a contract document, please:\n"
                "1. Use the file upload button to attach your document\n"
                "2. Or drag and drop the file into the chat\n"
                "3. Then send your message again\n\n"
                "Example: 'upload contract document for {client_name}' with a file attached."
            ).format(client_name=kwargs.get('client_name')),
            "data": None
        }

    if file_info:
        # Replace placeholders with actual file data from context
        if kwargs.get('file_data') in ["<base64_encoded_data>", "[USE_ACTUAL_FILE_DATA_FROM_CONTEXT]"] or not kwargs.get('file_data'):
            kwargs['file_data'] = file_info.get('file_data')
            kwargs['filename'] = file_info.get('filename', kwargs.get('filename'))
            kwargs['file_size'] = file_info.get('file_size', kwargs.get('file_size'))
            kwargs['mime_type'] = file_info.get('mime_type', kwargs.get('mime_type'))

    # Ensure required params
    required_params = ['client_name']
    missing_params = [param for param in required_params if not kwargs.get(param)]
    if missing_params:
        return {
            "success": False,
            "message": f"❌ Missing required parameters: {', '.join(missing_params)}.",
            "data": None
        }

    # Validate file data format if present
    if kwargs.get('file_data') and not isinstance(kwargs['file_data'], str):
        return {
            "success": False,
            "message": "❌ File data must be a base64 encoded string",
            "data": None
        }

    params = UploadContractDocumentParams(**kwargs)
    result = await upload_contract_document_tool(params, context)
    return result.model_dump()

async def _delete_contract_document_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for deleting contract documents"""
    kwargs.pop('db', None)
    params = DeleteContractDocumentParams(**kwargs)
    result = await delete_contract_document_tool(params)
    return result.model_dump()

async def _delete_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for deleting contracts"""
    kwargs.pop('db', None)
    params = DeleteContractParams(**kwargs)
    result = await delete_contract_tool(params)
    return result.model_dump()

async def _delete_client_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for deleting clients"""
    kwargs.pop('db', None)
    params = DeleteClientParams(**kwargs)
    result = await delete_client_tool(params)
    return result.model_dump()

async def _get_all_clients_with_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    kwargs.pop('db', None)
    result = await get_all_clients_with_contracts_tool()
    return result.model_dump()

async def _create_client_and_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating a client and then a contract in sequence with comprehensive response"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    # Replace placeholders with actual file data from context
    if context and 'file_info' in context:
        file_info = context['file_info']
        
        if kwargs.get('file_data') == "<base64_encoded_data>":
            kwargs['file_data'] = file_info.get('file_data')
            kwargs['filename'] = file_info.get('filename', kwargs.get('filename'))
            kwargs['file_size'] = file_info.get('file_size', kwargs.get('file_size'))
            kwargs['mime_type'] = file_info.get('mime_type', kwargs.get('mime_type'))
            print(f"🔍 DEBUG: create_client_and_contract - Replaced placeholder with real file data: {len(kwargs['file_data'])} chars, size: {kwargs['file_size']}")
        else:
            print(f"🔍 DEBUG: create_client_and_contract - Using provided file data: {len(kwargs.get('file_data', ''))} chars")
    else:
        print(f"🔍 DEBUG: create_client_and_contract - No file_info in context")
    
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
        
        client_result = await create_client_tool(client_params, context)
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
        
        contract_result = await smart_create_contract_tool(contract_params, context)
        
        # Handle document upload if provided
        document_result = None
        if (contract_result.success and 
            kwargs.get('file_data') and 
            kwargs.get('filename') and 
            kwargs.get('file_size') and 
            kwargs.get('mime_type')):
            
            # Upload document for the newly created contract
            upload_params = UploadContractDocumentParams(
                client_name=kwargs.get('client_name'),
                contract_id=contract_result.data.get('contract_id'),
                file_data=kwargs.get('file_data'),
                filename=kwargs.get('filename'),
                file_size=kwargs.get('file_size'),
                mime_type=kwargs.get('mime_type')
            )
            
            document_result = await upload_contract_document_tool(upload_params, context)
        
        # Enhanced response with comprehensive details
        if contract_result.success:
            # Extract all client details
            client_data = client_result.data or {}
            contract_data = contract_result.data or {}
            
            # Build success message with document status
            success_message = f"✅ Successfully created client '{kwargs.get('client_name')}' and contract. Client ID: {client_data.get('client_id')}, Contract ID: {contract_data.get('contract_id')}"
            
            if document_result:
                if document_result.success:
                    success_message += f"\n\n📄 **Document uploaded successfully:** {document_result.data.get('document_filename', 'Unknown')}"
                else:
                    success_message += f"\n\n⚠️ **Document upload failed:** {document_result.message}"
            
            return {
                "success": True,
                "message": success_message,
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
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Calculate the difference in months
        diff = relativedelta(end, start)
        return diff.years * 12 + diff.months
    except:
        return None

async def _update_contract_by_id_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating contract by ID instead of client name"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    contract_id = kwargs.get('contract_id')
    
    try:
        async with get_ai_db() as session:
            result = await session.execute(select(Contract).where(Contract.contract_id == contract_id))
            contract = result.scalar_one_or_none()
            
            if not contract:
                return {
                    "success": False,
                    "message": f"❌ Contract with ID {contract_id} not found."
                }
        
        # Get the client name
            result = await session.execute(select(Client).where(Client.client_id == contract.client_id))
            client = result.scalar_one_or_none()
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
            
            result = await update_contract_tool(params, context)
            return result.model_dump()
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to update contract by ID: {str(e)}"
        }

async def _search_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching contracts by various criteria"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = SearchContractsParams(**kwargs)
    result = await search_contracts_tool(params, context)
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

# --- Employee Tool Wrappers ---
async def _create_employee_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for creating a new employee record with enhanced natural language processing"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # If employee_name is provided, first search for the profile
        if kwargs.get('employee_name') and not kwargs.get('profile_id'):
            # Search for the profile first
            search_result = await search_profiles_by_name_tool(kwargs['employee_name'])
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
        result = await create_employee_tool(params, context)
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create employee: {str(e)}",
            "data": None
        }

async def _update_employee_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating an existing employee record"""
    # Remove db parameter (not needed with async sessions)
    context = kwargs.pop('context', None)
    kwargs.pop('db', None)  # Remove but ignore
    
    params = UpdateEmployeeParams(**kwargs)
    result = await update_employee_tool(params, context)
    return result.model_dump()

async def _search_employees_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching employees by various criteria"""
    kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    limit = kwargs.get("limit", 50)
    result = await search_employees_tool(search_term, limit)
    return result.model_dump()

async def _get_employee_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for getting detailed employee information"""
    kwargs.pop('db', None)
    employee_id = kwargs.get("employee_id")
    result = await get_employee_details_tool(employee_id)
    return result.model_dump()

async def _get_all_employees_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for getting all employees in the system"""
    kwargs.pop('db', None)
    result = await get_all_employees_tool()
    return result.dict()

async def _delete_employee_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for deleting an employee"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', {})
    
    # Extract parameters
    employee_id = kwargs.get('employee_id')
    profile_id = kwargs.get('profile_id')
    employee_number = kwargs.get('employee_number')
    employee_name = kwargs.get('employee_name')
    
    # Create DeleteEmployeeParams
    params = DeleteEmployeeParams(
        employee_id=employee_id,
        profile_id=profile_id,
        employee_number=employee_number,
        employee_name=employee_name
    )
    
    result = await delete_employee_tool(params, context)
    return result.dict()

async def _search_profiles_by_name_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching user profiles by name"""
    kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    result = await search_profiles_by_name_tool(search_term)
    return result.dict()

async def _update_employee_from_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating employee from natural language details - complete solution for employee updates"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First search for the employee by name
        employee_name = kwargs.get('employee_name')
        
        if not employee_name:
            return {
                "success": False,
                "message": "❌ Employee name is required."
            }
        
        # TODO: OPTIMIZATION - Pass employee_name to update_employee_tool for inline profile search
        # This eliminates the nested database session from profile search
        # The update_employee_tool will handle profile search internally
        
        # TODO: OPTIMIZATION - Eliminate nested database session
        # Instead of creating our own session, we'll pass the profile_id to update_employee_tool
        # and let it handle the employee lookup internally
        # This prevents nested sessions and connection pool exhaustion
        
        # Handle hire date parsing from natural language
        hire_date = kwargs.get('hire_date')
        
        if hire_date and not hire_date.count('-') == 2:
            # Try to parse natural language date like "15th Aug 2025"
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
        # TODO: OPTIMIZATION - Pass employee_name instead of profile_id to eliminate nested session
        employee_params_dict = {
            'employee_name': employee_name,  # Pass employee_name for inline profile search
            'profile_id': None,  # Explicitly set to None to ensure inline search is used
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
        result = await update_employee_tool(employee_params, context)
        
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to update employee from details: {str(e)}",
            "data": None
        }

async def _create_employee_from_details_wrapper(**kwargs) -> Dict[str, Any]:
    """Enhanced wrapper for creating employee from natural language details - complete solution for employee creation"""
    kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First search for the employee profile by name
        employee_name = kwargs.get('employee_name')
        
        if not employee_name:
            return {
                "success": False,
                "message": "❌ Employee name is required."
            }
        
        # TODO: OPTIMIZATION - Pass employee_name to create_employee_tool for inline profile search
        # This eliminates the nested database session from profile search
        # The create_employee_tool will handle profile search internally
        
        # TODO: OPTIMIZATION - Simplify wrapper processing for better performance
        # Direct parameter extraction instead of synthetic message creation
        # This eliminates unnecessary string concatenation and parsing overhead
        
        # TODO: OPTIMIZATION - Extract parameters directly from kwargs
        # Avoid synthetic message creation and parsing for better performance
        job_title = kwargs.get('job_title')
        employment_type = kwargs.get('employment_type')
        full_time_part_time = kwargs.get('full_time_part_time')
        department = kwargs.get('department')
        salary = kwargs.get('salary')
        rate = kwargs.get('rate')
        rate_type = kwargs.get('rate_type')
        hire_date = kwargs.get('hire_date')
        
        # Enhanced hire date parsing from natural language
        hire_date = kwargs.get('hire_date')
        if hire_date and not (hire_date.count('-') == 2):
            # Try multiple date parsing pattern
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
        
        # TODO: OPTIMIZATION - Direct parameter processing without fallback parsing
        # All parameters should be provided directly in kwargs for better performance
        # This eliminates the need for synthetic message parsing and fallback logic
        
        # CRITICAL: If document data contains placeholders, get the real data from context
        if context and 'file_info' in context:
            file_info = context['file_info']
            
            # Replace NDA document placeholders
            if kwargs.get('nda_document_data') == "<base64_encoded_data>":
                kwargs['nda_document_data'] = file_info.get('file_data')
                kwargs['nda_document_filename'] = file_info.get('filename', kwargs.get('nda_document_filename'))
                kwargs['nda_document_size'] = file_info.get('file_size', kwargs.get('nda_document_size'))
                kwargs['nda_document_mime_type'] = file_info.get('mime_type', kwargs.get('nda_document_mime_type'))
            
            # Replace contract document placeholders
            if kwargs.get('contract_document_data') == "<base64_encoded_data>":
                kwargs['contract_document_data'] = file_info.get('file_data')
                kwargs['contract_document_filename'] = file_info.get('filename', kwargs.get('contract_document_filename'))
                kwargs['contract_document_size'] = file_info.get('file_size', kwargs.get('contract_document_size'))
                kwargs['contract_document_mime_type'] = file_info.get('mime_type', kwargs.get('contract_document_mime_type'))
        
        # Create employee using the existing create_employee tool
        # TODO: OPTIMIZATION - Pass employee_name instead of profile_id to eliminate nested session
        employee_params_dict = {
            'employee_name': employee_name,  # Pass employee_name for inline profile search
            'profile_id': None,  # Explicitly set to None to ensure inline search is used
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
            'contract_file_link': kwargs.get('contract_file_link'),
            # Add document upload parameters
            'nda_document_data': kwargs.get('nda_document_data'),
            'nda_document_filename': kwargs.get('nda_document_filename'),
            'nda_document_size': kwargs.get('nda_document_size'),
            'nda_document_mime_type': kwargs.get('nda_document_mime_type'),
            'contract_document_data': kwargs.get('contract_document_data'),
            'contract_document_filename': kwargs.get('contract_document_filename'),
            'contract_document_size': kwargs.get('contract_document_size'),
            'contract_document_mime_type': kwargs.get('contract_document_mime_type')
        }
        
        # Remove None values to avoid validation errors
        employee_params_dict = {k: v for k, v in employee_params_dict.items() if v is not None}
        
        employee_params = CreateEmployeeParams(**employee_params_dict)
        result = await create_employee_tool(employee_params, context)
        
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create employee from details: {str(e)}",
            "data": None
        }

# Employee Document Management Tool Wrappers
async def _upload_employee_document_wrapper(**kwargs) -> dict:
    """Wrapper for uploading employee documents (NDA or contract)"""
    try:
        # Import here to avoid circular imports
        from src.aiagents.tools.employee_tools import upload_employee_document_tool, UploadEmployeeDocumentParams
        
        kwargs.pop('db', None)
        context = kwargs.pop('context', {})
        
        # Extract parameters
        employee_id = kwargs.get('employee_id')
        employee_name = kwargs.get('employee_name')
        document_type = kwargs.get('document_type')
        file_data = kwargs.get('file_data')
        filename = kwargs.get('filename')
        file_size = kwargs.get('file_size')
        mime_type = kwargs.get('mime_type')
        
        # CRITICAL: If file_data is a placeholder, get the real data from context
        if file_data == "<base64_encoded_data>":
            if context and 'file_info' in context:
                file_data = context['file_info'].get('file_data')
                filename = context['file_info'].get('filename', filename)
                file_size = context['file_info'].get('file_size', file_size)
                mime_type = context['file_info'].get('mime_type', mime_type)
                print(f"🔍 DEBUG: Tool wrapper - Using real file data from context: {len(file_data)} chars, size: {file_size}")
            else:
                print(f"🔍 DEBUG: Tool wrapper - No file_info in context, using placeholder data")
        
        # TODO: If this name validation causes issues with legitimate uploads, remove this section
        # Additional validation: ensure employee_name is not a filename
        if employee_name and not employee_id:
            # Check if employee_name looks like a filename
            if '.' in employee_name and len(employee_name.split('.')) == 2:
                file_extensions = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg']
                if any(employee_name.lower().endswith(ext) for ext in file_extensions):
                    return {
                        "success": False,
                        "message": f"❌ Error: '{employee_name}' appears to be a filename, not an employee name. The agent should extract the actual employee name from the user message (e.g., 'Steve York' from 'for employee Steve York').",
                        "data": None
                    }
        
        # Create UploadEmployeeDocumentParams
        params = UploadEmployeeDocumentParams(
            employee_id=employee_id,
            employee_name=employee_name,
            document_type=document_type,
            file_data=file_data,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type
        )
        
        result = await upload_employee_document_tool(params, context)
        return result.dict()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to upload employee document: {str(e)}",
            "data": None
        }

async def _delete_employee_document_wrapper(**kwargs) -> dict:
    """Wrapper for deleting employee documents (NDA or contract)"""
    try:
        # Import here to avoid circular imports
        from src.aiagents.tools.employee_tools import delete_employee_document_tool, DeleteEmployeeDocumentParams
        
        kwargs.pop('db', None)
        context = kwargs.pop('context', {})
        
        # Extract parameters
        employee_id = kwargs.get('employee_id')
        employee_name = kwargs.get('employee_name')
        document_type = kwargs.get('document_type')
        
        # Create DeleteEmployeeDocumentParams
        params = DeleteEmployeeDocumentParams(
            employee_id=employee_id,
            employee_name=employee_name,
            document_type=document_type
        )
        
        result = await delete_employee_document_tool(params, context)
        return result.dict()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to delete employee document: {str(e)}",
            "data": None
        }

async def _get_employee_document_wrapper(**kwargs) -> dict:
    """Wrapper for getting employee document information and download URLs"""
    try:
        # Import here to avoid circular imports
        from src.aiagents.tools.employee_tools import get_employee_document_tool, GetEmployeeDocumentParams
        
        kwargs.pop('db', None)
        context = kwargs.pop('context', {})
        
        # Extract parameters
        employee_id = kwargs.get('employee_id')
        employee_name = kwargs.get('employee_name')
        document_type = kwargs.get('document_type')
        
        # Create GetEmployeeDocumentParams
        params = GetEmployeeDocumentParams(
            employee_id=employee_id,
            employee_name=employee_name,
            document_type=document_type
        )
        
        result = await get_employee_document_tool(params, context)
        return result.dict()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to get employee document: {str(e)}",
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
    "get_contracts_with_null_billing": _get_contracts_with_null_billing_wrapper,
    "get_contracts_by_amount": _get_contracts_by_amount_wrapper,
    "get_contracts_with_documents": _get_contracts_with_documents_wrapper,
    "update_client": _update_client_wrapper,
    "manage_contract_document": _smart_contract_document_wrapper,
    "upload_contract_document": _upload_contract_document_wrapper,
    "delete_contract_document": _delete_contract_document_wrapper,
    "delete_contract": _delete_contract_wrapper,
    "delete_client": _delete_client_wrapper,
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
    "delete_employee": _delete_employee_wrapper,
    
    # Employee Document Management Tools
    "upload_employee_document": _upload_employee_document_wrapper,
    "delete_employee_document": _delete_employee_document_wrapper,
    "get_employee_document": _get_employee_document_wrapper,

    
    # Other tools will be registered here
}

async def tool_executor_node(state: AgentState) -> Dict:
    """
    Executes tools requested by an agent. This node is the central tool handler for the entire graph.
    It takes tool calls from the last message in the state, executes them, and returns the results.
    """
    last_message = state['messages'][-1]
    
    # Handle both dict messages (serialized) and object messages
    if isinstance(last_message, dict):
        tool_calls = last_message.get('tool_calls', [])
    else:
        tool_calls = getattr(last_message, 'tool_calls', [])

    if not tool_calls:
        return {"messages": []}

    # CRITICAL: Extract context from the last user message before tool execution
    # This ensures we have the latest client information for tool correction
    try:
        from .context_extractor import ContextExtractor
        context_extractor = ContextExtractor()
        
        # Find the last user message
        user_messages = [msg for msg in state['messages'] if isinstance(msg, dict) and msg.get('role') == 'user']
        if user_messages:
            last_user_message = user_messages[-1].get('content', '')
            if last_user_message:
                print(f"🔍 DEBUG: Tool executor - extracting context from: {last_user_message}")
                existing_data = state.get('data', {})
                user_context = await context_extractor.extract_context_from_user_message(last_user_message, existing_data)
                if user_context:
                    print(f"🔍 DEBUG: Tool executor - extracted context: {user_context}")
                    context_extractor.update_state_with_context(state, user_context)
                    print(f"🔍 DEBUG: Tool executor - updated state data: {state.get('data', {})}")
    except Exception as e:
        print(f"🔍 DEBUG: Tool executor - context extraction failed: {e}")

    # The database session should be in the state's data payload, but context is in state.context
    #db_session = state.get('data', {}).get('database')
    context = state.get('context', {})

    results = []
    update_all_used = False  # Track if update_all=true has been used
    
    for i, tool_call in enumerate(tool_calls):
        
        # Handle both dict and object tool calls
        if isinstance(tool_call, dict):
            tool_name = tool_call['function']['name']
            tool_call_id = tool_call['id']
            arguments_str = tool_call['function']['arguments']
        else:
            tool_name = tool_call.function.name
            tool_call_id = tool_call.id
            arguments_str = tool_call.function.arguments
            
        print(f"🔍 TOOL: {tool_name}")
        
        # Skip redundant individual contract calls if update_all=true was already used
        if tool_name == 'update_contract':
            args = json.loads(arguments_str)
            if args.get('update_all') == True:
                update_all_used = True
            elif update_all_used and 'contract_id' in args:
                continue

        if tool_name not in TOOL_REGISTRY:
            print(f"🔍 DEBUG: Tool executor - tool {tool_name} not in registry")
            result_content = json.dumps({"error": f"Tool '{tool_name}' not found in registry."})
        else:
            try:
                # Validate and correct tool selection
                validated_tool_name = validate_and_correct_tool(tool_name, state)
                if validated_tool_name != tool_name:
                    print(f"🔍 DEBUG: Tool corrected from {tool_name} to {validated_tool_name}")
                    tool_name = validated_tool_name

                tool_function = TOOL_REGISTRY[tool_name]
                args = json.loads(arguments_str)

                # Enhance context with extracted context from state['data']
                enhanced_context = context.copy() if context else {}
                if 'data' in state and state['data']:
                    enhanced_context.update(state['data'])

                args['context'] = enhanced_context

                output = await tool_function(**args)

                # Handle JSON serialization with Decimal support
                def json_serializer(obj):
                    if hasattr(obj, '__dict__'):
                        return obj.__dict__
                    elif hasattr(obj, '_asdict'):  # namedtuple
                        return obj._asdict()
                    elif hasattr(obj, 'isoformat'):  # datetime
                        return obj.isoformat()
                    elif str(type(obj)) == "<class 'decimal.Decimal'>":
                        return float(obj)
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

                # Format the response as a user-friendly message instead of raw JSON
                if isinstance(output, dict) and 'message' in output:
                    result_content = output['message']
                    print(f"🔍 DEBUG: Tool executor - formatted message length: {len(result_content)}")
                    print(f"🔍 DEBUG: Tool executor - message preview: {result_content[:200]}...")
                else:
                    result_content = json.dumps(output, default=json_serializer)
                    print(f"🔍 DEBUG: Tool executor - result content length: {len(result_content)}")
                
                # 🔧 FIX: Check if we need to execute upload_contract_document after create_contract
                has_file_info = bool(state.get('context', {}).get('file_info'))
                original_request = state.get('data', {}).get('original_user_request', '')
                user_wants_upload = 'upload' in original_request.lower()
                print(f"🔧 FIX: Sequential execution check - tool: {tool_name}, has_file: {has_file_info}, wants_upload: {user_wants_upload}")
                
                if (tool_name == "create_contract" and 
                    has_file_info and
                    user_wants_upload):
                    
                    print("🔧 FIX: Executing upload_contract_document after create_contract")
                    
                    # Extract client name and contract ID from the create_contract result
                    client_name = args.get('client_name', 'Unknown')
                    
                    # Get contract ID directly from the tool output data
                    contract_id = None
                    if isinstance(output, dict) and 'data' in output:
                        # Check multiple possible locations for contract_id
                        data = output['data']
                        contract_id = (
                            data.get('contract_id') or  # Direct contract_id
                            data.get('contract', {}).get('contract_id') or  # Nested in contract
                            data.get('operation') == 'create_contract' and data.get('contract', {}).get('contract_id')
                        )
                        print(f"🔧 FIX: Found contract ID {contract_id} from tool output data")
                    else:
                        print(f"🔧 FIX: No contract ID found in tool output data")
                    
                    if contract_id:
                        # Execute upload_contract_document with contract ID and actual file data
                        file_info = state.get('context', {}).get('file_info', {})
                        upload_args = {
                            'client_name': client_name,
                            'contract_id': int(contract_id),
                            'file_data': file_info.get('file_data', ''),
                            'filename': file_info.get('filename', ''),
                            'file_size': file_info.get('file_size', 0),
                            'mime_type': file_info.get('mime_type', ''),
                            'context': enhanced_context
                        }
                        
                        print(f"🔧 FIX: Upload args - client: {client_name}, contract_id: {contract_id}, filename: {file_info.get('filename', '')}")
                        
                        try:
                            upload_tool = TOOL_REGISTRY['upload_contract_document']
                            upload_output = await upload_tool(**upload_args)
                            
                            # Combine the results
                            if isinstance(upload_output, dict) and 'message' in upload_output:
                                upload_message = upload_output['message']
                                result_content = f"{result_content}\n\n{upload_message}"
                                print(f"🔧 FIX: Combined result: {result_content[:200]}...")
                            else:
                                result_content = f"{result_content}\n\nDocument uploaded successfully."
                                print(f"🔧 FIX: Added upload confirmation")
                                
                        except Exception as e:
                            print(f"🔧 FIX: Upload failed: {e}")
                            result_content = f"{result_content}\n\nNote: Document upload failed - {str(e)}"
                    else:
                        print(f"🔧 FIX: Could not extract contract ID from tool output data")
                        result_content = f"{result_content}\n\nNote: Could not upload document - contract ID not found in tool output"

            except Exception as e:
                print(f"❌ Tool executor - error calling {tool_name}: {e}")
                import traceback
                print(f"❌ Tool executor - full traceback: {traceback.format_exc()}")
                
                # Handle JSON serialization with Decimal support for error cases too
                def json_serializer(obj):
                    if hasattr(obj, '__dict__'):
                        return obj.__dict__
                    elif hasattr(obj, '_asdict'):  # namedtuple
                        return obj._asdict()
                    elif hasattr(obj, 'isoformat'):  # datetime
                        return obj.isoformat()
                    elif str(type(obj)) == "<class 'decimal.Decimal'>":
                        return float(obj)
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                result_content = json.dumps({"error": str(e), "tool_name": tool_name}, default=json_serializer)

        results.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": tool_name,
            "content": result_content,
        })

    print(f"🔍 DEBUG: Tool executor - returning {len(results)} results")
    return {"messages": results}

def validate_and_correct_tool(tool_name: str, state: AgentState) -> str:
    """Validate and correct tool selection based on current workflow."""
    # REVERT: If infinite loop issues persist, revert to original validation logic

    # Define allowed tools for each workflow
    ALLOWED_TOOLS = {
        'update': ['update_contract', 'update_contract_by_id'],
        'delete': ['delete_contract', 'delete_contract_document', 'delete_client'],
        'create': ['create_contract', 'create_client_and_contract', 'create_client', 'upload_contract_document'],
        'upload': ['get_client_contracts', 'upload_contract_document'],
        'show': ['get_contracts_by_client', 'get_client_details', 'get_contract_details'],
        'search': ['search_contracts', 'search_clients']
    }

    # Get current workflow from state
    current_workflow = state.get('data', {}).get('user_operation', '').split('_')[0]  # Extract 'update' from 'update_contract'
    allowed_tools = ALLOWED_TOOLS.get(current_workflow, [])

    print(f"🔍 DEBUG: Tool validation - tool: {tool_name}, workflow: {current_workflow}, allowed: {allowed_tools}")

    # If tool is not in allowed list, correct it
    if allowed_tools and tool_name not in allowed_tools:
        # Special case: if agent calls delete_contract but should upload, correct it
        if tool_name == "delete_contract" and current_workflow == "upload":
            corrected_tool = "upload_contract_document"
        else:
            corrected_tool = allowed_tools[0]  # Use first allowed tool
        print(f"🔍 DEBUG: Tool corrected from {tool_name} to {corrected_tool}")
        return corrected_tool
     
    
    # PARAMETER CORRECTION: Fix common parameter issues that could cause infinite loops
    # REVERT: If parameter correction causes issues, revert to basic tool validation
    if tool_name == "update_contract" and not (state.get("data", {}).get("client_name") or state.get("data", {}).get("current_client")):
        # Check if this is a response to a previous update request (like "all")
        user_operation = state.get("data", {}).get("user_operation", "")
        if user_operation and user_operation.startswith("update"):
            # This is a response to an update request, don't switch to search
            print(f"🔍 DEBUG: Parameter correction - preserving {tool_name} for update operation response")
            return tool_name
        else:
            # If updating contract but no client specified, switch to search mode
            print(f"🔍 DEBUG: Parameter correction - switching {tool_name} to search_contracts due to missing client_name")
            print(f"🔍 DEBUG: State data for debugging: {state.get('data', {})}")
            return "search_contracts"
    
    if tool_name == "upload_contract_document" and not state.get("data", {}).get("file_info"):
        # If uploading document but no file info, this could cause issues
        print(f"🔍 DEBUG: Parameter correction - upload_contract_document missing file_info")
        # Let it proceed but log the issue
    
    # WORKFLOW CONSISTENCY: Ensure tool selection matches user intent
    user_intent = state.get("data", {}).get("user_operation", "")
    if user_intent.startswith("create") and tool_name.startswith("update"):
        corrected_tool = "create_contract" if "contract" in user_intent else "create_client"
        print(f"🔍 DEBUG: Workflow correction - changing {tool_name} to {corrected_tool} for {user_intent}")
        return corrected_tool
    
    if user_intent.startswith("update") and tool_name.startswith("create"):
        corrected_tool = "update_contract" if "contract" in user_intent else "update_client"
        print(f"🔍 DEBUG: Workflow correction - changing {tool_name} to {corrected_tool} for {user_intent}")
        return corrected_tool
    
    return tool_name
# REVERT MARKERS ADDED - All infinite loop fixes include rollback instructions
