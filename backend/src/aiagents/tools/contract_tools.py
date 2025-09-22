from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, text
from sqlalchemy.orm import selectinload
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from src.database.core.database import get_db
from src.database.core.models import Client, Contract, ClientContact
from src.database.core.schemas import ClientCreate, ContractCreate, ClientContactCreate
from src.database.api.clients import create_client_internal, get_client_by_name
from src.database.api.contracts import create_contract_internal
from src.database.api.client_contacts import create_client_contact
from src.database.core.database import get_ai_db
import re
from src.services.storage_service import SupabaseStorageService
from datetime import datetime
import base64
from io import BytesIO

class CreateClientParams(BaseModel):
    client_name: str
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None

class ContractToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False

class SmartContractParams(BaseModel):
    client_name: str
    contract_type: str  # "Fixed", "Hourly", "Retainer"
    original_amount: Optional[Decimal] = None
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None
    billing_frequency: Optional[str] = None  # "Monthly", "Weekly", "One-time"
    notes: Optional[str] = None

class ContractDocumentParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None  # If not provided, will find latest contract for client
    document_action: str  # "upload" or "update"

class UploadContractDocumentParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None
    file_data: str  # Base64 encoded file content
    filename: str
    file_size: int
    mime_type: str
    user_confirmed: Optional[bool] = False  # TODO: CONFIRMATION FIX - Add confirmation parameter

class UpdateContractParams(BaseModel):
    client_name: str 
    contract_id: Optional[int] = None
    user_response: Optional[str] = None  # User's response to contract selection prompt
    update_all: Optional[bool] = False  # Whether to update all contracts for the client
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_type: Optional[str] = None
    original_amount: Optional[float] = None
    current_amount: Optional[float] = None  # Add current_amount field
    billing_frequency: Optional[str] = None
    billing_prompt_next_date: Optional[str] = None
    status: Optional[str] = None
    termination_date: Optional[str] = None  # Add termination_date field
    amendments: Optional[str] = None  # Add amendments field
    notes: Optional[str] = None

async def update_specific_contract(contract: Contract, params: UpdateContractParams, session) -> ContractToolResult:
    """Update a specific contract with the provided parameters"""
    try:
        updated_fields = []
        
        # Update contract fields if provided
        if params.start_date:
            contract.start_date = datetime.strptime(params.start_date, "%Y-%m-%d").date()
            updated_fields.append("start_date")
        if params.end_date:
            contract.end_date = datetime.strptime(params.end_date, "%Y-%m-%d").date()
            updated_fields.append("end_date")
        if params.contract_type:
            contract.contract_type = params.contract_type
            updated_fields.append("contract_type")
        if params.original_amount is not None:
            contract.original_amount = params.original_amount
            contract.current_amount = params.original_amount  # Update current amount too
            updated_fields.append("original_amount")
        if params.current_amount is not None:
            contract.current_amount = params.current_amount
            updated_fields.append("current_amount")
        if params.billing_frequency:
            contract.billing_frequency = params.billing_frequency
            updated_fields.append("billing_frequency")
        if params.billing_prompt_next_date:
            contract.billing_prompt_next_date = datetime.strptime(params.billing_prompt_next_date, "%Y-%m-%d").date()
            updated_fields.append("billing_prompt_next_date")
        if params.status:
            contract.status = params.status
            updated_fields.append("status")
        if params.termination_date:
            contract.termination_date = datetime.strptime(params.termination_date, "%Y-%m-%d").date()
            updated_fields.append("termination_date")
        if params.amendments is not None:
            contract.amendments = params.amendments
            updated_fields.append("amendments")
        if params.notes is not None:
            contract.notes = params.notes
            updated_fields.append("notes")
        
        # Update the updated_at timestamp
        contract.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # Build user-friendly success message
        def get_friendly_field_name(field):
            field_mapping = {
                'billing_prompt_next_date': 'billing date',
                'billing_frequency': 'billing frequency',
                'original_amount': 'contract amount',
                'current_amount': 'current amount',
                'contract_type': 'contract type',
                'status': 'status',
                'start_date': 'start date',
                'end_date': 'end date',
                'termination_date': 'end date',
                'amendments': 'amendments',
                'notes': 'notes'
            }
            return field_mapping.get(field, field.replace('_', ' '))
        
        message = f"✅ Successfully updated contract {contract.contract_id} for {contract.client.client_name}"
        if updated_fields:
            if len(updated_fields) == 1:
                friendly_field = get_friendly_field_name(updated_fields[0])
                message += f". Updated: {friendly_field}."
            else:
                friendly_fields = [get_friendly_field_name(field) for field in updated_fields]
                if len(friendly_fields) == 2:
                    message += f". Updated: {friendly_fields[0]} and {friendly_fields[1]}."
                else:
                    last_field = friendly_fields[-1]
                    other_fields = ', '.join(friendly_fields[:-1])
                    message += f". Updated: {other_fields}, and {last_field}."
        
        return ContractToolResult(
            success=True,
            message=message,
            data={
                "contract": {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": contract.original_amount,
                    "current_amount": contract.current_amount,
                    "start_date": contract.start_date.isoformat() if contract.start_date else None,
                    "end_date": contract.end_date.isoformat() if contract.end_date else None,
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": contract.billing_prompt_next_date.isoformat() if contract.billing_prompt_next_date else None,
                    "notes": contract.notes
                }
            }
        )
    except Exception as e:
        await session.rollback()
        return ContractToolResult(
            success=False,
            message=f"❌ Error updating contract: {str(e)}"
        )

async def update_contract_tool(params: UpdateContractParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for updating existing contracts by client name"""
    try:
        async with get_ai_db() as session:
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # If we have a specific contract_id, update that contract directly
            if params.contract_id:
                contract_result = await session.execute(select(Contract).options(
                    selectinload(Contract.client)
                ).filter(Contract.contract_id == params.contract_id))
                
                contract = contract_result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract with ID {params.contract_id} not found."
                    )
                
                # If client_name is provided, validate that the contract belongs to that client
                if params.client_name:
                    if contract.client.client_name.lower() != params.client_name.lower():
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Contract {params.contract_id} belongs to '{contract.client.client_name}', not '{params.client_name}'. Please specify the correct client."
                        )
                
                # Update the specific contract
                return await update_specific_contract(contract, params, session)
            
            # If no contract_id provided, we need client_name to find contracts
            if not params.client_name:
                return ContractToolResult(
                    success=False,
                    message="❌ Either contract_id or client_name must be provided."
                )
            
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found."
                )
            
            # Get all contracts for the client
            contracts_result = await session.execute(select(Contract).options(
                selectinload(Contract.client)
            ).filter(
                Contract.client_id == client.client_id
            ).order_by(Contract.created_at.desc()))
            contracts = contracts_result.scalars().all()
            
            if not contracts:
                return ContractToolResult(
                    success=False,
                    message=f"❌ No contracts found for client '{client.client_name}'."
                )
            
            contract = None
            if params.contract_id:
                # Use specific contract ID
                for c in contracts:
                    if c.contract_id == params.contract_id:
                        contract = c
                        break
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract with ID {params.contract_id} not found for client '{client.client_name}'."
                    )
            elif params.user_response and params.user_response.strip():
                # User responded with contract selection
                user_input = params.user_response.strip().lower()
                requested_id = None
                
                
                # Check for "all", "both", "for all", "for both" responses
                if any(phrase in user_input for phrase in ["all", "both", "for all", "for both", "every", "each"]):
                    # User wants to update all contracts
                    params.update_all = True
                    # Skip individual contract selection logic
                    contract = None
                else:
                    # Parse various formats: "108", "Contract 108", "contract id 108", "id 108", "1", "2", etc.
                    if user_input.isdigit():
                        # Check if it's a contract ID or a list number
                        num = int(user_input)
                        if num <= len(contracts):
                            # It's a list number (1-based)
                            contract = contracts[num - 1]
                        else:
                            # It might be a contract ID
                            for c in contracts:
                                if c.contract_id == num:
                                    contract = c
                                    break
                            if not contract:
                                return ContractToolResult(
                                    success=False,
                                    message=f"❌ Contract ID {num} not found for client '{client.client_name}'."
                                )
                    elif "contract id" in user_input:
                        parts = user_input.split("contract id")
                        if len(parts) > 1:
                            number_part = parts[1].strip()
                            if number_part.isdigit():
                                requested_id = int(number_part)
                    elif "contract" in user_input:
                        parts = user_input.split("contract")
                        if len(parts) > 1:
                            number_part = parts[1].strip()
                            if number_part.isdigit():
                                requested_id = int(number_part)
                    elif "id" in user_input:
                        parts = user_input.split("id")
                        if len(parts) > 1:
                            number_part = parts[1].strip()
                            if number_part.isdigit():
                                requested_id = int(number_part)
                    
                    if requested_id:
                        for c in contracts:
                            if c.contract_id == requested_id:
                                contract = c
                                break
                        if not contract:
                            return ContractToolResult(
                                success=False,
                                message=f"❌ Contract ID {requested_id} not found for client '{client.client_name}'."
                            )
                    
                    if not contract and not params.update_all:
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Could not extract contract ID from '{params.user_response}'. Please provide a valid contract ID number, or say 'all' to update all contracts."
                        )
            
            # Check if user wants to update all contracts
            if params.update_all:
                # User wants to update all contracts - proceed with update
                # contracts_to_update will be set to all contracts below
                pass
            elif len(contracts) == 1:
                # Only one contract, use it directly
                contract = contracts[0]
            else:
                # Multiple contracts - ask user to choose
                contract_list = []
                for i, c in enumerate(contracts, 1):
                    amount = f"${c.original_amount:,.2f}" if c.original_amount else "N/A"
                    status = c.status.lower()
                    start_date = str(c.start_date) if c.start_date else "Not set"
                    contract_info = f"{i}. **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {status} (Start: {start_date})"
                    contract_list.append(contract_info)
                
                
                return ContractToolResult(
                    success=False,
                    message=f"🔍 Found {len(contracts)} contracts for client '{client.client_name}'. Please specify which contract you want to update:\n\n" + 
                           "\n".join(contract_list) + 
                           f"\n\nPlease provide the contract ID (e.g., 'update contract {contracts[0].contract_id} for {client.client_name}'), use the contract number, or say 'all' to update all contracts."
                )
            
            # Determine which contracts to update
            contracts_to_update = []
            if params.update_all:
                contracts_to_update = contracts
            else:
                contracts_to_update = [contract]
            
            update_fields = []
            updated_contracts = []
            
            # Apply updates to all selected contracts using bulk update to avoid prepared statement conflicts
            if params.update_all and len(contracts_to_update) > 1:
                # Use bulk update for multiple contracts to avoid prepared statement conflicts
                contract_ids = [c.contract_id for c in contracts_to_update]
                
                # Build update data dictionary
                update_data = {"updated_by": user_id}
                
                if params.start_date:
                    try:
                        update_data["start_date"] = datetime.strptime(params.start_date, "%Y-%m-%d").date()
                        update_fields.append("start_date")
                    except ValueError:
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Invalid start date format. Please use YYYY-MM-DD format."
                        )
                
                if params.end_date:
                    try:
                        update_data["end_date"] = datetime.strptime(params.end_date, "%Y-%m-%d").date()
                        update_fields.append("end_date")
                    except ValueError:
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Invalid end date format. Please use YYYY-MM-DD format."
                        )
                
                if params.contract_type:
                    update_data["contract_type"] = params.contract_type
                    update_fields.append("contract_type")
                
                if params.original_amount is not None:
                    update_data["original_amount"] = params.original_amount
                    update_fields.append("original_amount")
                
                if params.current_amount is not None:
                    update_data["current_amount"] = params.current_amount
                    update_fields.append("current_amount")
                
                if params.billing_frequency:
                    update_data["billing_frequency"] = params.billing_frequency
                    update_fields.append("billing_frequency")
                
                if params.billing_prompt_next_date:
                    try:
                        update_data["billing_prompt_next_date"] = datetime.strptime(params.billing_prompt_next_date, "%Y-%m-%d").date()
                        update_fields.append("billing_prompt_next_date")
                    except ValueError:
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Invalid billing prompt date format. Please use YYYY-MM-DD format."
                        )
                
                if params.status:
                    update_data["status"] = params.status
                    update_fields.append("status")
                
                if params.termination_date:
                    try:
                        update_data["termination_date"] = datetime.strptime(params.termination_date, "%Y-%m-%d").date()
                        update_fields.append("termination_date")
                    except ValueError:
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Invalid termination date format. Please use YYYY-MM-DD format."
                        )
                
                if params.amendments:
                    update_data["amendments"] = params.amendments
                    update_fields.append("amendments")
                
                if params.notes:
                    update_data["notes"] = params.notes
                    update_fields.append("notes")
                
                # Perform bulk update
                if update_data:
                    from sqlalchemy import update
                    stmt = update(Contract).where(Contract.contract_id.in_(contract_ids)).values(**update_data)
                    await session.execute(stmt)
                    
                    # Build updated contracts list for response
                    for contract_id in contract_ids:
                        updated_contracts.append({
                            "contract_id": contract_id,
                            "updated_fields": update_fields
                        })
            else:
                # Use individual updates for single contract or when update_all is False
                for contract_to_update in contracts_to_update:
                    contract_updated_fields = []
                    
                    if params.start_date:
                        try:
                            contract_to_update.start_date = datetime.strptime(params.start_date, "%Y-%m-%d").date()
                            contract_updated_fields.append("start_date")
                        except ValueError:
                            return ContractToolResult(
                                success=False,
                                message=f"❌ Invalid start date format. Please use YYYY-MM-DD format."
                            )
                
                    if params.end_date:
                        try:
                            contract_to_update.end_date = datetime.strptime(params.end_date, "%Y-%m-%d").date()
                            contract_updated_fields.append("end_date")
                        except ValueError:
                            return ContractToolResult(
                                success=False,
                                message=f"❌ Invalid end date format. Please use YYYY-MM-DD format."
                            )
                    
                    if params.contract_type:
                        contract_to_update.contract_type = params.contract_type
                        contract_updated_fields.append("contract_type")
                    
                    if params.original_amount is not None:
                        contract_to_update.original_amount = params.original_amount
                        contract_updated_fields.append("original_amount")
                    
                    if params.current_amount is not None:
                        contract_to_update.current_amount = params.current_amount
                        contract_updated_fields.append("current_amount")
                    
                    if params.billing_frequency:
                        contract_to_update.billing_frequency = params.billing_frequency
                        contract_updated_fields.append("billing_frequency")
                    
                    if params.billing_prompt_next_date:
                        try:
                            contract_to_update.billing_prompt_next_date = datetime.strptime(params.billing_prompt_next_date, "%Y-%m-%d").date()
                            contract_updated_fields.append("billing_prompt_next_date")
                        except ValueError:
                            return ContractToolResult(
                                success=False,
                                message=f"❌ Invalid billing prompt date format. Please use YYYY-MM-DD format."
                            )
                    
                    if params.status:
                        contract_to_update.status = params.status
                        contract_updated_fields.append("status")
                    
                    if params.termination_date:
                        try:
                            contract_to_update.termination_date = datetime.strptime(params.termination_date, "%Y-%m-%d").date()
                            contract_updated_fields.append("termination_date")
                        except ValueError:
                            return ContractToolResult(
                                success=False,
                                message=f"❌ Invalid termination date format. Please use YYYY-MM-DD format."
                            )
                    
                    if params.amendments:
                        contract_to_update.amendments = params.amendments
                        contract_updated_fields.append("amendments")
                    
                    if params.notes:
                        contract_to_update.notes = params.notes
                        contract_updated_fields.append("notes")
                    
                    contract_to_update.updated_by = user_id
                    updated_contracts.append({
                        "contract_id": contract_to_update.contract_id,
                        "updated_fields": contract_updated_fields
                    })
                    
                    # Track unique update fields across all contracts
                    for field in contract_updated_fields:
                        if field not in update_fields:
                            update_fields.append(field)
            
            await session.commit()
            
            # Refresh all updated contracts (only needed for individual updates)
            if not (params.update_all and len(contracts_to_update) > 1):
                for contract_to_update in contracts_to_update:
                    await session.refresh(contract_to_update)
            
            # Build user-friendly success message
            def get_friendly_field_name(field):
                field_mapping = {
                    'billing_prompt_next_date': 'billing date',
                    'billing_frequency': 'billing frequency',
                    'original_amount': 'contract amount',
                    'current_amount': 'current amount',
                    'contract_type': 'contract type',
                    'status': 'status',
                    'start_date': 'start date',
                    'end_date': 'end date',
                    'termination_date': 'end date',
                    'amendments': 'amendments',
                    'notes': 'notes'
                }
                return field_mapping.get(field, field.replace('_', ' '))
            
            if params.update_all:
                if len(update_fields) == 1:
                    friendly_field = get_friendly_field_name(update_fields[0])
                    message = f"✅ Successfully updated {len(contracts_to_update)} contracts for '{client.client_name}'. Updated: {friendly_field}."
                else:
                    friendly_fields = [get_friendly_field_name(field) for field in update_fields]
                    if len(friendly_fields) == 2:
                        message = f"✅ Successfully updated {len(contracts_to_update)} contracts for '{client.client_name}'. Updated: {friendly_fields[0]} and {friendly_fields[1]}."
                    else:
                        last_field = friendly_fields[-1]
                        other_fields = ', '.join(friendly_fields[:-1])
                        message = f"✅ Successfully updated {len(contracts_to_update)} contracts for '{client.client_name}'. Updated: {other_fields}, and {last_field}."
            else:
                # Include contract ID in single contract update message
                contract_id = contracts_to_update[0].contract_id if contracts_to_update else "Unknown"
                if len(update_fields) == 1:
                    friendly_field = get_friendly_field_name(update_fields[0])
                    message = f"✅ Successfully updated contract {contract_id} for '{client.client_name}'. Updated: {friendly_field}."
                else:
                    friendly_fields = [get_friendly_field_name(field) for field in update_fields]
                    if len(friendly_fields) == 2:
                        message = f"✅ Successfully updated contract {contract_id} for '{client.client_name}'. Updated: {friendly_fields[0]} and {friendly_fields[1]}."
                    else:
                        last_field = friendly_fields[-1]
                        other_fields = ', '.join(friendly_fields[:-1])
                        message = f"✅ Successfully updated contract {contract_id} for '{client.client_name}'. Updated: {other_fields}, and {last_field}."
            
            
            return ContractToolResult(
                success=True,
                message=message,
                data={
                    "contracts_updated": len(contracts_to_update),
                    "client_name": client.client_name,
                    "updated_fields": update_fields,
                    "contracts": updated_contracts,
                    "update_all": params.update_all
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to update contract for {params.client_name}: {str(e)}"
        )
    

async def smart_contract_document_tool(params: ContractDocumentParams) -> ContractToolResult:
    """Smart tool for handling contract documents by client name"""
    try:
        async with get_ai_db() as session:
            contract = None
            
            if params.contract_id:
                # Use specific contract ID
                result = await session.execute(select(Contract).filter(Contract.contract_id == params.contract_id))
                contract = result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract with ID {params.contract_id} not found."
                    )
            else:
                # Find client and their latest contract
                client = await get_client_by_name(params.client_name, session)
                if not client:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{params.client_name}' not found."
                    )
                
                # Get the most recent contract for this client
                contract_temp = await session.execute(select(Contract).filter(
                    Contract.client_id == client.client_id
                ).order_by(Contract.created_at.desc()))
                contract = contract_temp.scalar_one_or_none()
                
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{client.client_name}'. Please create a contract first."
                    )
            
            # Return contract information and instructions for document upload
            return ContractToolResult(
                success=True,
                message=f"✅ Found contract {contract.contract_id} for client '{contract.client.client_name}'. To upload a document, use the file upload endpoint: POST /contracts/{contract.contract_id}/upload-document",
                data={
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "has_document": bool(contract.document_filename),
                    "document_filename": contract.document_filename,
                    "upload_endpoint": f"/contracts/{contract.contract_id}/upload-document"
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to process contract document: {str(e)}"
        )


async def upload_contract_document_tool(params: UploadContractDocumentParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
    """Upload contract document for a client's contract"""
    try:
        async with get_ai_db() as session:
            # Find contract (same logic as smart_contract_document_tool)
            contract = None
            if params.contract_id:
                result = await session.execute(select(Contract).options(
                    selectinload(Contract.client)
                ).filter(Contract.contract_id == params.contract_id))
                contract = result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract with ID {params.contract_id} not found."
                    )
                # Define variables needed later in the code
                client = contract.client
                contracts = [contract]
            else:
                # Find by client name
                client = await get_client_by_name(params.client_name, session)
                if not client:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{params.client_name}' not found."
                    )

                # Get all contracts for the client
                contracts_result = await session.execute(select(Contract).options(
                    selectinload(Contract.client)
                ).filter(
                    Contract.client_id == client.client_id
                ).order_by(Contract.created_at.desc()))
                contracts = contracts_result.scalars().all()
                
                # Initialize contract variable
                contract = None

                if not contracts:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{client.client_name}'. Please create a contract first."
                    )

                # If multiple contracts, check if this is a "create + upload" workflow
                if len(contracts) > 1:
                    # Check if there's a recently created contract in session context (within last 2 minutes)
                    last_created_contract = None
                    if context and 'last_created_contract' in context:
                        last_created = context['last_created_contract']
                        if (last_created.get('client_name') == client.client_name and
                            last_created.get('contract_id')):

                            # Check if the contract was created recently (within 2 minutes)
                            from datetime import datetime, timedelta
                            if last_created.get('created_at'):
                                try:
                                    created_at = datetime.fromisoformat(last_created['created_at'])
                                    time_since_creation = datetime.now() - created_at
                                    if time_since_creation.total_seconds() < 120:  # 2 minutes
                                        # Find the contract that matches the last created one
                                        for c in contracts:
                                            if c.contract_id == last_created['contract_id']:
                                                last_created_contract = c
                                                break
                                except (ValueError, TypeError) as e:
                                    # Invalid date format, ignore context
                                    pass

                    if last_created_contract:
                        # Use the recently created contract from session context
                        contract = last_created_contract
                    else:
                        # Ask for clarification - show all contracts for the client
                        contract_list = []
                        for i, c in enumerate(contracts, 1):
                            amount = f"${c.original_amount:,.2f}" if c.original_amount else "N/A"
                            status = c.status.lower()
                            start_date = str(c.start_date) if c.start_date else "Not set"
                            
                            # Check if contract has existing document
                            document_info = ""
                            if c.document_filename:
                                if c.document_file_size and c.document_file_size > 0:
                                    file_size_mb = c.document_file_size / (1024 * 1024)
                                    file_size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{c.document_file_size} bytes"
                                else:
                                    file_size_display = "Unknown"
                                uploaded_date = c.document_uploaded_at.strftime('%B %d, %Y') if c.document_uploaded_at else "N/A"
                                
                                # Create download URL for existing document
                                storage_service = SupabaseStorageService()
                                download_url = storage_service.get_contract_document_url(c.document_file_path) if c.document_file_path else f"/contracts/{c.contract_id}/document"
                                
                                document_info = f" 📄 *Has contract document: [{c.document_filename}]({download_url}) ({file_size_display}, uploaded {uploaded_date})*"
                            
                            contract_list.append(f"{i}. **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {status} (Start: {start_date}){document_info}")

                        # Check if any contracts have existing documents
                        has_existing_documents = any(c.document_filename for c in contracts)
                        overwrite_warning = "\n\n⚠️ **Note:** If a contract already has a document, uploading a new document will overwrite the existing one." if has_existing_documents else ""
                        
                        # Create the response
                        response_message = f"📋 {client.client_name} has {len(contracts)} contracts. Here are the details:\n\n" + "\n".join(contract_list) + f"\n\nPlease specify which contract ID you want to upload the document for (e.g., \"upload document for {client.client_name} contract {contracts[0].contract_id}\").{overwrite_warning}"
                        
                        return ContractToolResult(
                            success=False,
                            message=response_message
                        )

        # If we have a specific contract (from contract_id) or only one contract from client search
        if contract or len(contracts) == 1:
            if not contract:
                contract = contracts[0]
            
            # TODO: CONFIRMATION FIX - Check if user has confirmed the replacement
            # Also check if the last user message was a confirmation
            is_confirmation = params.user_confirmed
            print(f"🔍 DEBUG CONFIRMATION: params.user_confirmed = {params.user_confirmed}")
            
            # TODO: CONFIRMATION FIX - If not explicitly confirmed, check if last user message was "yes" or a contract ID
            if not is_confirmation and context:
                messages = context.get('messages', [])
                print(f"🔍 DEBUG CONFIRMATION: Found {len(messages)} messages in context")
                if messages:
                    last_message = messages[-1]
                    print(f"🔍 DEBUG CONFIRMATION: Last message type: {type(last_message)}")
                    if isinstance(last_message, dict) and last_message.get('role') == 'user':
                        content = last_message.get('content', '').lower().strip()
                        print(f"🔍 DEBUG CONFIRMATION: Last user message content: '{content}'")
                        
                        # Check for confirmation words
                        if content in ['yes', 'y', 'ok', 'okay', 'confirm', 'proceed', 'go ahead', 'sure', 'alright']:
                            is_confirmation = True
                            print(f"🔍 DEBUG CONFIRMATION: ✅ Detected confirmation from last user message: '{content}'")
                        # TODO: CONFIRMATION FIX - Also check if this is a contract ID response in upload workflow
                        elif content.isdigit() and params.contract_id and str(params.contract_id) == content:
                            # This is a contract ID response in an upload workflow - treat as confirmation
                            is_confirmation = True
                            print(f"🔍 DEBUG CONFIRMATION: ✅ Detected contract ID response as confirmation: '{content}'")
                        else:
                            print(f"🔍 DEBUG CONFIRMATION: ❌ Not a confirmation word or contract ID: '{content}'")
                    else:
                        print(f"🔍 DEBUG CONFIRMATION: Last message is not a user message or not dict")
                else:
                    print(f"🔍 DEBUG CONFIRMATION: No messages found in context")
            else:
                print(f"🔍 DEBUG CONFIRMATION: is_confirmation already True or no context")
            
            print(f"🔍 DEBUG CONFIRMATION: Final is_confirmation = {is_confirmation}")
            
            # Check if contract already has a document
            if contract.document_filename and not is_confirmation:
                # Show existing document information and ask for confirmation
                if contract.document_file_size and contract.document_file_size > 0:
                    existing_file_size_mb = contract.document_file_size / (1024 * 1024)
                    existing_file_size_display = f"{existing_file_size_mb:.2f} MB" if existing_file_size_mb >= 1 else f"{contract.document_file_size} bytes"
                else:
                    existing_file_size_display = "Unknown"
                
                # Create download URL for existing document
                storage_service = SupabaseStorageService()
                existing_download_url = storage_service.get_contract_document_url(contract.document_file_path) if contract.document_file_path else f"/contracts/{contract.contract_id}/document"
                
                existing_message = f"📄 **Contract {contract.contract_id} already has a contract document uploaded:**\n\n- **Filename:** [{contract.document_filename}]({existing_download_url})\n- **File Size:** {existing_file_size_display}\n- **Uploaded At:** {contract.document_uploaded_at.strftime('%B %d, %Y, %I:%M %p') if contract.document_uploaded_at else 'N/A'}\n\n⚠️ **Uploading a new contract document will replace the existing one.**\n\n**Please confirm:** Enter 'yes' to continue and replace the existing contract document, or 'no' to cancel."
                
                # Return the existing document info first with confirmation needed status
                return ContractToolResult(
                    success=False,  # Set to False to indicate action needed
                    message=existing_message,
                    data={
                        "contract_id": contract.contract_id,
                        "client_name": contract.client.client_name,
                        "confirmation_needed": True,
                        "current_workflow": "upload",  # Set workflow for confirmation handling
                        "existing_document": {
                            "filename": contract.document_filename,
                            "file_size": contract.document_file_size,
                            "file_size_display": existing_file_size_display,
                            "uploaded_at": contract.document_uploaded_at.isoformat() if contract.document_uploaded_at else None,
                            "download_url": existing_download_url
                        }
                    }
                )
            
            # TODO: CONFIRMATION FIX - If user confirmed, proceed with upload
            if is_confirmation:
                print(f"🔍 DEBUG: User confirmed replacement, proceeding with upload")
            
            # Upload document using storage service
            storage_service = SupabaseStorageService()
            
            # Convert base64 to file-like object
            try:
                # Validate base64 data before decoding
                if not params.file_data or len(params.file_data) < 10:
                    return ContractToolResult(
                        success=False,
                        message="❌ File data is empty or too short. Please ensure the file was properly uploaded."
                    )
                
                # Clean up base64 string - remove any whitespace and data URL prefixes
                file_data_clean = params.file_data
                if file_data_clean.startswith('data:'):
                    # Split on comma and take the base64 part
                    parts = file_data_clean.split(',', 1)
                    if len(parts) == 2:
                        file_data_clean = parts[1]
                    else:
                        return ContractToolResult(
                            success=False,
                            message="❌ Invalid data URL format in file data."
                        )
                
                # Remove all whitespace and newlines
                file_data_clean = ''.join(file_data_clean.split())
                
                # Add padding if needed for base64 decoding
                missing_padding = len(file_data_clean) % 4
                if missing_padding:
                    file_data_clean += '=' * (4 - missing_padding)
                
                print(f"🔍 DEBUG: Base64 data length: {len(file_data_clean)}")
                print(f"🔍 DEBUG: Base64 data preview: {file_data_clean[:50]}...")
                
                # Try to decode directly instead of regex validation
                try:
                    test_decode = base64.b64decode(file_data_clean, validate=True)
                    print(f"🔍 DEBUG: Base64 decode successful, {len(test_decode)} bytes")
                except Exception as e:
                    print(f"🔍 DEBUG: Base64 decode failed: {e}")
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Invalid base64 format: {str(e)}. Please ensure the file was properly encoded."
                    )
                
                file_content = base64.b64decode(file_data_clean)
                file_obj = BytesIO(file_content)
                file_obj.filename = params.filename
                file_obj.content_type = params.mime_type
                
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Failed to decode file data: {str(e)}. Please ensure the file was properly uploaded and encoded."
                )
            
            # Perform upload
            upload_result = await storage_service.upload_contract_document(file_obj, contract.contract_id)
            
            if upload_result.get("success"):
                # Update contract record
                contract.document_filename = upload_result.get("filename")
                contract.document_file_path = upload_result.get("file_path")
                contract.document_bucket_name = "contract-documents"
                contract.document_file_size = upload_result.get("file_size")
                contract.document_mime_type = upload_result.get("mime_type")
                contract.document_uploaded_at = upload_result.get("uploaded_at")

                # Persist changes
                session.add(contract)
                await session.commit()
                
                # Format file size for display
                if contract.document_file_size and contract.document_file_size > 0:
                    file_size_mb = contract.document_file_size / (1024 * 1024)
                    file_size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{contract.document_file_size} bytes"
                else:
                    file_size_display = "Unknown"
                
                # Create download URL - use signed URL from storage service
                file_path = upload_result.get("file_path")
                if file_path:
                    download_url = storage_service.get_contract_document_url(file_path)
                else:
                    download_url = f"/contracts/{contract.contract_id}/document"
                
                # Check if this was auto-selected from session context
                context_note = ""
                if (context and 'last_created_contract' in context and 
                    context['last_created_contract'].get('contract_id') == contract.contract_id):
                    context_note = "\n\n💡 *Document uploaded to the recently created contract*"
                
                # Create the final message
                final_message = f"✅ Contract document uploaded successfully for **{contract.client.client_name}**\n\n📄 **Contract Document Details:**\n- **Filename:** [{contract.document_filename}]({download_url})\n- **File Size:** {file_size_display}\n- **Contract ID:** {contract.contract_id}\n- **Uploaded At:** {contract.document_uploaded_at.strftime('%B %d, %Y, %I:%M %p') if contract.document_uploaded_at else 'N/A'}{context_note}"
                
                return ContractToolResult(
                    success=True,
                    message=final_message,
                    data={
                        "contract_id": contract.contract_id,
                        "client_name": contract.client.client_name,
                        "document_filename": contract.document_filename,
                        "file_size": contract.document_file_size,
                        "file_size_display": file_size_display,
                        "uploaded_at": contract.document_uploaded_at.isoformat() if contract.document_uploaded_at else None,
                        "download_url": download_url
                    }
                )
            else:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Document upload failed: {upload_result.get('error', 'Unknown error')}"
                )
                
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to upload contract document: {str(e)}"
        )
    

async def smart_create_contract_tool(params: SmartContractParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Smart tool for creating contracts by client name instead of client_id"""
    try:
        async with get_ai_db() as session:
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found. Please create the client first."
                )
            
            start_date_obj = None
            end_date_obj = None
            
            if params.start_date:
                try:
                    start_date_obj = date.fromisoformat(params.start_date)
                except ValueError:
                    start_date_obj = date.today()
            
            if params.end_date:
                try:
                    end_date_obj = date.fromisoformat(params.end_date)
                except ValueError:
                    pass
            
            contract_data = ContractCreate(
                client_id=client.client_id,
                contract_type=params.contract_type,
                start_date=start_date_obj,
                end_date=end_date_obj,
                original_amount=params.original_amount,
                current_amount=params.original_amount,
                billing_frequency=params.billing_frequency,
                status="draft",
                notes=params.notes
            )
            
            result = await create_contract_internal(contract_data, session, user_id)
            
            # Store the created contract in session context for document upload
            # CRITICAL FIX: Ensure all values are hashable/serializable to prevent unhashable type errors
            if context:
                # Convert all values to strings to ensure hashability
                context['last_created_contract'] = {
                    'contract_id': str(result.contract_id),
                    'client_name': str(client.client_name),
                    'created_at': result.created_at.isoformat() if result.created_at else None
                }
            
            return ContractToolResult(
                success=True,
                message=f"✅ Contract created successfully for client '{client.client_name}' (Contract ID: {result.contract_id})",
                data={
                    "contract_id": result.contract_id,
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "contract_type": result.contract_type,
                    "status": result.status,
                    "original_amount": float(result.original_amount) if result.original_amount else None
                }
            )
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to create contract: {str(e)}"
        )
    


async def create_client_tool(params: CreateClientParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for creating new clients"""
    
    try:
        async with get_ai_db() as session:
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # Proceed directly with client creation (similarity check removed)
            client_data = ClientCreate(**params.model_dump())
            result = await create_client_internal(client_data, session, user_id)
            
            return ContractToolResult(
                success=True,
                message=f"✅ Successfully created client: {result.client_name}",
                data={
                    "client_id": result.client_id,
                    "client_name": result.client_name,
                    "industry": result.industry
                }
            )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to create client: {str(e)}"
        )

async def search_clients_tool(search_term: Optional[str] = None, limit: int = 10) -> ContractToolResult:
    """Tool for searching existing clients"""
    try:
        async with get_ai_db() as session:
            query = select(Client)
            if search_term:
                # Use text() to avoid prepared statement conflicts with PgBouncer
                from sqlalchemy import text
                query = query.filter(
                    text("lower(client_name) LIKE lower(:search_term) OR lower(industry) LIKE lower(:search_term)")
                    .params(search_term=f"%{search_term}%")
                )
            
            # Execute the query with limit
            result = await session.execute(query.limit(limit))
            clients = result.scalars().all()
            client_list = [
                {
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "notes": client.notes
                } for client in clients
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(client_list)} clients",
                data={"clients": client_list, "count": len(client_list)}
            )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to search clients: {str(e)}"
        )
    

async def get_contract_details_tool(contract_id: Optional[int] = None, client_name: Optional[str] = None) -> ContractToolResult:
    """Tool for getting detailed contract information"""
    try:
        async with get_ai_db() as session:
            if contract_id:
                result = await session.execute(select(Contract).filter(Contract.contract_id == contract_id))
                contract = result.scalar_one_or_none()
            elif client_name:
                client = await get_client_by_name(client_name, session)
                if not client:
                    return ContractToolResult(success=False, message=f"❌ Client '{client_name}' not found.")
                
                result = await session.execute(
                    select(Contract)
                    .filter(Contract.client_id == client.client_id)
                    .order_by(Contract.created_at.desc())
                )
                contract = result.scalar_one_or_none()
            else:
                return ContractToolResult(success=False, message="❌ Please provide either contract_id or client_name.")

            if not contract:
                return ContractToolResult(success=False, message="❌ Contract not found for the specified criteria.")

            result = await session.execute(select(Client).filter(Client.client_id == contract.client_id))
            client = result.scalar_one_or_none()
            
            # Format file size for display
            file_size_str = None
            if contract.document_file_size:
                if contract.document_file_size < 1024:
                    file_size_str = f"{contract.document_file_size} bytes"
                elif contract.document_file_size < 1024 * 1024:
                    file_size_str = f"{contract.document_file_size / 1024:.1f} KB"
                else:
                    file_size_str = f"{contract.document_file_size / (1024 * 1024):.1f} MB"
            
            contract_details = {
                "contract_id": contract.contract_id,
                "client_name": client.client_name if client else "Unknown",
                "contract_type": contract.contract_type,
                "status": contract.status,
                "original_amount": float(contract.original_amount) if contract.original_amount else None,
                "current_amount": float(contract.current_amount) if contract.current_amount else (float(contract.original_amount) if contract.original_amount else None),
                "billing_frequency": contract.billing_frequency,
                "start_date": str(contract.start_date) if contract.start_date else None,
                "end_date": str(contract.end_date) if contract.end_date else None,
                "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                "termination_date": str(contract.termination_date) if contract.termination_date else None,
                "notes": contract.notes,
                # Document information
                "document_filename": contract.document_filename,
                "document_file_size": file_size_str,
                "document_uploaded_at": str(contract.document_uploaded_at) if contract.document_uploaded_at else None,
                "document_download_url": f"/contracts/{contract.contract_id}/document" if contract.document_filename else None,
            }
            
            return ContractToolResult(
                success=True,
                message=f"✅ Found contract details for '{contract_details['client_name']}'",
                data={"contract": contract_details}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contract details: {str(e)}")
    

async def get_contracts_by_client_tool(client_name: str, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
    """Tool for getting all contracts for a specific client by name"""
    try:
        async with get_ai_db() as session:
            
            client = await get_client_by_name(client_name, session)
            if not client:
                return ContractToolResult(success=False, message=f"❌ Client '{client_name}' not found.")
            
            contracts_temp = await session.execute(select(Contract).filter(Contract.client_id == client.client_id))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else (float(contract.original_amount) if contract.original_amount else None),
                    "billing_frequency": contract.billing_frequency,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "termination_date": str(contract.termination_date) if contract.termination_date else None,
                    "notes": contract.notes,
                    # Document information
                    "document_filename": contract.document_filename,
                    "document_file_size": contract.document_file_size,
                    "document_uploaded_at": str(contract.document_uploaded_at) if contract.document_uploaded_at else None,
                    "document_download_url": f"/contracts/{contract.contract_id}/document" if contract.document_filename else None,
                } for contract in contracts
            ]

            client_details = {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "industry": client.industry,
                "primary_contact_name": client.primary_contact_name,
                "primary_contact_email": client.primary_contact_email,
                "company_size": client.company_size,
                "notes": client.notes,
                "created_at": str(client.created_at) if client.created_at else None,
                "updated_at": str(client.updated_at) if client.updated_at else None
            }

            # Format detailed client information
            client_info = f"""**Client Details:**
- **Name:** {client.client_name}
- **Industry:** {client.industry or 'Not specified'}
- **Primary Contact:** {client.primary_contact_name or 'Not specified'}
- **Email:** {client.primary_contact_email or 'Not specified'}
- **Company Size:** {client.company_size or 'Not specified'}
- **Notes:** {client.notes or 'None'}
- **Created:** {client.created_at.strftime('%B %d, %Y') if client.created_at else 'Not available'}
- **Last Updated:** {client.updated_at.strftime('%B %d, %Y') if client.updated_at else 'Not available'}"""

            # Format detailed contract information
            if contracts:
                contract_details = f"\n\n**Contract Details ({len(contracts)} contracts):**\n"
                for i, contract in enumerate(contracts, 1):
                    amount = f"${contract.original_amount:,.2f}" if contract.original_amount else "Not set"
                    current_amount = f"${contract.current_amount:,.2f}" if contract.current_amount else "Not set"
                    status = contract.status.title()
                    start_date = contract.start_date.strftime('%B %d, %Y') if contract.start_date else "Not set"
                    end_date = contract.end_date.strftime('%B %d, %Y') if contract.end_date else "Not set"
                    billing_freq = contract.billing_frequency or "Not set"
                    next_billing = contract.billing_prompt_next_date.strftime('%B %d, %Y') if contract.billing_prompt_next_date else "Not set"
                    termination = contract.termination_date.strftime('%B %d, %Y') if contract.termination_date else "Not set"
                    notes = contract.notes or "None"
                    if contract.document_filename:
                        # Get the actual download URL from storage service
                        try:
                            from src.services.storage_service import SupabaseStorageService
                            storage_service = SupabaseStorageService()
                            download_url = storage_service.get_document_url(contract.document_file_path)
                            # Use only the filename as display text, hide the long URL
                            document_info = f"📄 [{contract.document_filename}]({download_url})"
                        except Exception as e:
                            print(f"🔍 DEBUG: Failed to get download URL for contract {contract.contract_id}: {e}")
                            # Fallback to API endpoint
                            document_url = f"/api/contracts/{contract.contract_id}/document"
                            document_info = f"📄 [{contract.document_filename}]({document_url})"
                    else:
                        document_info = "No contract document"
                    
                    contract_details += f"""
**Contract {i} (ID: {contract.contract_id}):**
- **Type:** {contract.contract_type}
- **Status:** {status}
- **Original Amount:** {amount}
- **Current Amount:** {current_amount}
- **Billing Frequency:** {billing_freq}
- **Start Date:** {start_date}
- **End Date:** {end_date}
- **Next Billing Date:** {next_billing}
- **Termination Date:** {termination}
- **Contract Document:** {document_info}
- **Notes:** {notes}
"""
            else:
                contract_details = "\n\n**No contracts found for this client.**"
            
            full_message = client_info + contract_details
            
            print(f"🔍 DEBUG: get_contracts_by_client_tool - full message length: {len(full_message)}")
            print(f"🔍 DEBUG: get_contracts_by_client_tool - message preview: {full_message[:300]}...")
            
            return ContractToolResult(
                success=True,
                message=full_message,
                data={
                    "client": client_details,
                    "contracts": contract_list
                }
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts: {str(e)}")
    

async def get_all_contracts_tool() -> ContractToolResult:
    """Tool for getting all contracts across all clients"""
    try:
        async with get_ai_db() as session:
            contracts_temp = await session.execute(select(Contract).join(Client).options(selectinload(Contract.client)).order_by(Contract.created_at.desc()))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    # Document information
                    "document_filename": contract.document_filename,
                    "document_file_size": contract.document_file_size,
                    "document_uploaded_at": str(contract.document_uploaded_at) if contract.document_uploaded_at else None,
                    "document_download_url": f"/contracts/{contract.contract_id}/document" if contract.document_filename else None,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts across all clients",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get all contracts: {str(e)}")
 

async def get_contracts_by_status_tool(status: str) -> ContractToolResult:
    """Tool for getting contracts by status (e.g., 'active', 'ongoing', 'draft', 'terminated')"""

    try:
        async with get_ai_db() as session:
            if status.lower() in ['ongoing', 'active']:
                query_status = 'active'
            else:
                query_status = status
                
            contracts_temp = await session.execute(select(Contract).join(Client).options(selectinload(Contract.client)).filter(Contract.status.ilike(f'%{query_status}%')))
            contracts = contracts_temp.scalars().all()
            
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with status '{status}'",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts by status: {str(e)}")
    

async def get_contracts_with_null_billing_date_tool() -> ContractToolResult:
    """Tool for getting all contracts where the billing prompt date is null"""
    try:
        async with get_ai_db() as session:
            contracts_temp = await session.execute(select(Contract).join(Client).options(selectinload(Contract.client)).filter(Contract.billing_prompt_next_date.is_(None)))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with a null billing prompt date.",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts with null billing date: {str(e)}")
    

async def get_contracts_for_next_month_billing_tool(client_name: str = None, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for getting contracts with a billing prompt date in the next month or later in the current month."""
    try:
        async with get_ai_db() as session:
            today = context.get('today', date.today()) if context else date.today()
            
            # Use provided client_name parameter or fall back to context
            if not client_name and context:
                client_name = context.get('current_client')
            
            # Only show contracts with billing dates in the future (tomorrow onwards)
            tomorrow = today + timedelta(days=1)
            
            # End of next month for reasonable range
            start_of_this_month = today.replace(day=1)
            end_of_next_month = (start_of_this_month + relativedelta(months=2)) - timedelta(days=1)
            
            print(f"🔍 DEBUG: get_contracts_for_next_month_billing - today: {today}, tomorrow: {tomorrow}, end_of_next_month: {end_of_next_month}")
            print(f"🔍 DEBUG: get_contracts_for_next_month_billing - client_name: {client_name}")
            
            stmt = (
                    select(Contract)
                    .join(Client)
                    .options(selectinload(Contract.client))
                    .where(
                        Contract.billing_prompt_next_date.isnot(None),
                        Contract.billing_prompt_next_date >= tomorrow,  # Only future dates
                        Contract.billing_prompt_next_date <= end_of_next_month
                    )
                    .order_by(Contract.billing_prompt_next_date.asc())
    )
            
            # Add client filter if specified
            if client_name:
                from sqlalchemy import text
                stmt = stmt.where(text("lower(client_name) LIKE lower(:client_name)").params(client_name=f"%{client_name}%"))
                print(f"🔍 DEBUG: get_contracts_for_next_month_billing - filtered by client: {client_name}")
            contracts_temp = await session.execute(stmt)
            contracts = contracts_temp.scalars().all()
            # 🔧 ENHANCED OUTPUT: Added more contract details for better billing information
            # TODO: If this change doesn't fix the issue, revert to the original 3-field output
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else (float(contract.original_amount) if contract.original_amount else None),
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date),
                    # 🔧 CLIENT CONTACT INFO: Added for billing communication
                    "primary_contact_name": contract.client.primary_contact_name,
                    "primary_contact_email": contract.client.primary_contact_email,
                } for contract in contracts
            ]
            
            null_billing_date_count_result = await session.execute(select(Contract).filter(Contract.billing_prompt_next_date.is_(None)))
            null_billing_date_count = len(null_billing_date_count_result.scalars().all())
            
            # Format detailed contract information like other tools
            if client_name:
                message = f"📋 **Contracts for {client_name} with upcoming billing dates ({today.strftime('%Y-%m-%d')} to {end_of_next_month.strftime('%Y-%m-%d')}):**\n"
            else:
                message = f"📋 **All contracts with upcoming billing dates ({today.strftime('%Y-%m-%d')} to {end_of_next_month.strftime('%Y-%m-%d')}):**\n"
            
            if contract_list:
                for i, contract in enumerate(contracts, 1):
                    amount = f"${contract.original_amount:,.2f}" if contract.original_amount else "Not set"
                    current_amount = f"${contract.current_amount:,.2f}" if contract.current_amount else amount
                    status = contract.status.title()
                    billing_date = contract.billing_prompt_next_date.strftime('%B %d, %Y') if contract.billing_prompt_next_date else "Not set"
                    
                    message += f"\n**Contract {i} (ID: {contract.contract_id}) - {contract.client.client_name}:**"
                    message += f"\n- **Type:** {contract.contract_type}"
                    message += f"\n- **Status:** {status}"
                    message += f"\n- **Original Amount:** {amount}"
                    message += f"\n- **Current Amount:** {current_amount}"
                    message += f"\n- **Billing Frequency:** {contract.billing_frequency or 'Not set'}"
                    message += f"\n- **Next Billing Date:** {billing_date}"
                    message += f"\n- **Contact:** {contract.client.primary_contact_name or 'Not specified'} ({contract.client.primary_contact_email or 'Not specified'})"
                    message += f"\n"
            else:
                message += "\nNo contracts found with upcoming billing dates in the specified period."
            
            if null_billing_date_count > 0:
                if client_name:
                    message += f"\n*Note: There may be additional contracts for {client_name} with no billing prompt date set.*"
                else:
                    message += f"\n*Note: {null_billing_date_count} contracts have no billing prompt date set.*"

            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts for next month's billing: {str(e)}")

async def get_contracts_with_null_billing_tool(client_name: str = None, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for getting contracts with null billing prompt dates."""
    try:
        async with get_ai_db() as session:
            # Use provided client_name parameter or fall back to context
            if not client_name and context:
                client_name = context.get('current_client')
            
            stmt = (
                select(Contract)
                .join(Client)
                .options(selectinload(Contract.client))
                .where(Contract.billing_prompt_next_date.is_(None))
                .order_by(Contract.created_at.desc())
            )
            
            # Add client filter if specified
            if client_name:
                stmt = stmt.where(text("lower(client_name) LIKE lower(:client_name)").params(client_name=f"%{client_name}%"))
            
            contracts_result = await session.execute(stmt)
            contracts = contracts_result.scalars().all()
            
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else (float(contract.original_amount) if contract.original_amount else None),
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": None,
                    "primary_contact_name": contract.client.primary_contact_name,
                    "primary_contact_email": contract.client.primary_contact_email,
                } for contract in contracts
            ]
            
            # Format detailed contract information
            if client_name:
                message = f"📋 **Contracts for {client_name} with no billing prompt date set:**\n"
            else:
                message = f"📋 **All contracts with no billing prompt date set:**\n"
            
            if contract_list:
                # Group contracts by client name
                contracts_by_client = {}
                for contract in contracts:
                    client_name_key = contract.client.client_name
                    if client_name_key not in contracts_by_client:
                        contracts_by_client[client_name_key] = []
                    contracts_by_client[client_name_key].append(contract)
                
                # Display contracts grouped by client
                contract_counter = 1
                for client_name_key, client_contracts in contracts_by_client.items():
                    # Show client header only if there are multiple clients
                    if not client_name and len(contracts_by_client) > 1:
                        message += f"\n**{client_name_key}:**\n"
                    
                    for contract in client_contracts:
                        amount = f"${contract.original_amount:,.2f}" if contract.original_amount else "Not set"
                        current_amount = f"${contract.current_amount:,.2f}" if contract.current_amount else amount
                        status = contract.status.title()
                        
                        # Show client name in contract header only if there's a single client or if client_name is specified
                        if client_name or len(contracts_by_client) == 1:
                            message += f"\n**Contract {contract_counter} (ID: {contract.contract_id}) - {contract.client.client_name}:**"
                        else:
                            message += f"\n**Contract {contract_counter} (ID: {contract.contract_id}):**"
                        
                        message += f"\n- **Type:** {contract.contract_type}"
                        message += f"\n- **Status:** {status}"
                        message += f"\n- **Original Amount:** {amount}"
                        message += f"\n- **Current Amount:** {current_amount}"
                        message += f"\n- **Billing Frequency:** {contract.billing_frequency or 'Not set'}"
                        message += f"\n- **Next Billing Date:** Not set"
                        
                        # Show contact info only if there are multiple clients or if client_name is specified
                        if not client_name and len(contracts_by_client) > 1:
                            message += f"\n- **Contact:** {contract.client.primary_contact_name or 'Not specified'} ({contract.client.primary_contact_email or 'Not specified'})"
                        elif client_name:
                            message += f"\n- **Contact:** {contract.client.primary_contact_name or 'Not specified'} ({contract.client.primary_contact_email or 'Not specified'})"
                        
                        message += f"\n"
                        contract_counter += 1
            else:
                message += "\nNo contracts found with null billing prompt dates."
            
            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts with null billing dates: {str(e)}")

async def get_contracts_by_amount_tool(min_amount: float = None, max_amount: float = None, client_name: str = None, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for getting contracts filtered by amount range."""
    try:
        async with get_ai_db() as session:
            # Use provided client_name parameter or fall back to context
            if not client_name and context:
                client_name = context.get('current_client')
            
            stmt = (
                select(Contract)
                .join(Client)
                .options(selectinload(Contract.client))
                .where(Contract.original_amount.isnot(None))
                .order_by(Contract.original_amount.desc())
            )
            
            # Add amount filters
            if min_amount is not None:
                stmt = stmt.where(Contract.original_amount >= min_amount)
            if max_amount is not None:
                stmt = stmt.where(Contract.original_amount <= max_amount)
            
            # Add client filter if specified
            if client_name:
                stmt = stmt.where(text("lower(client_name) LIKE lower(:client_name)").params(client_name=f"%{client_name}%"))
            
            contracts_result = await session.execute(stmt)
            contracts = contracts_result.scalars().all()
            
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else (float(contract.original_amount) if contract.original_amount else None),
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "primary_contact_name": contract.client.primary_contact_name,
                    "primary_contact_email": contract.client.primary_contact_email,
                } for contract in contracts
            ]
            
            # Format detailed contract information
            amount_filter = ""
            if min_amount is not None and max_amount is not None:
                amount_filter = f" with amount between ${min_amount:,.2f} and ${max_amount:,.2f}"
            elif min_amount is not None:
                amount_filter = f" with amount greater than ${min_amount:,.2f}"
            elif max_amount is not None:
                amount_filter = f" with amount less than ${max_amount:,.2f}"
            
            if client_name:
                message = f"📋 **Contracts for {client_name}{amount_filter}:**\n"
            else:
                message = f"📋 **All contracts{amount_filter}:**\n"
            
            if contract_list:
                for i, contract in enumerate(contracts, 1):
                    amount = f"${contract.original_amount:,.2f}" if contract.original_amount else "Not set"
                    current_amount = f"${contract.current_amount:,.2f}" if contract.current_amount else amount
                    status = contract.status.title()
                    billing_date = contract.billing_prompt_next_date.strftime('%B %d, %Y') if contract.billing_prompt_next_date else "Not set"
                    
                    message += f"\n**Contract {i} (ID: {contract.contract_id}) - {contract.client.client_name}:**"
                    message += f"\n- **Type:** {contract.contract_type}"
                    message += f"\n- **Status:** {status}"
                    message += f"\n- **Original Amount:** {amount}"
                    message += f"\n- **Current Amount:** {current_amount}"
                    message += f"\n- **Billing Frequency:** {contract.billing_frequency or 'Not set'}"
                    message += f"\n- **Next Billing Date:** {billing_date}"
                    message += f"\n- **Contact:** {contract.client.primary_contact_name or 'Not specified'} ({contract.client.primary_contact_email or 'Not specified'})"
                    message += f"\n"
            else:
                message += f"\nNo contracts found{amount_filter}."
            
            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts by amount: {str(e)}")

class SearchContractsParams(BaseModel):
    client_name: Optional[str] = None
    status: Optional[str] = None
    billing_date_next_month: Optional[bool] = False
    billing_date_is_null: Optional[bool] = False
    # TODO: If contract search becomes slow or unreliable, revert these new search parameters
    billing_frequency: Optional[str] = None  # Monthly, Weekly, One-time
    contract_type: Optional[str] = None  # Fixed, Hourly, Retainer
    min_amount: Optional[float] = None  # Minimum contract amount
    max_amount: Optional[float] = None  # Maximum contract amount
    start_date_from: Optional[str] = None  # Filter contracts starting from this date (YYYY-MM-DD)
    start_date_to: Optional[str] = None  # Filter contracts starting before this date (YYYY-MM-DD)

async def search_contracts_tool(params: SearchContractsParams, context: Dict[str, Any]) -> ContractToolResult:
    """Flexible tool for searching contracts by client, status, or billing date."""
    # 🚀 PERFORMANCE OPTIMIZATION: Track contract search execution
    try:
        async with get_ai_db() as session:
        
            filters_applied = []

            stmt = select(Contract).join(Client).options(selectinload(Contract.client))

            if params.client_name:
                stmt = stmt.where(Client.client_name.ilike(f"%{params.client_name}%"))
                filters_applied.append(f"client name matching '{params.client_name}'")

            if params.status:
                if params.status.lower() in ['ongoing', 'active']:
                    stmt = stmt.where(Contract.status.ilike('active'))
                    filters_applied.append("status is 'ongoing'")
                else:
                    stmt = stmt.where(Contract.status.ilike(f"%{params.status}%"))
                    filters_applied.append(f"status is '{params.status}'")

            if params.billing_date_next_month:
                today = context.get('today', date.today()) if context else date.today()
                end_of_next_month = (today.replace(day=1) + relativedelta(months=2)) - timedelta(days=1)
                print(f"🔍 DEBUG: Filtering billing dates - today: {today}, end_of_next_month: {end_of_next_month}")
                stmt = stmt.where(
                    Contract.billing_prompt_next_date.isnot(None),
                    Contract.billing_prompt_next_date >= today,
                    Contract.billing_prompt_next_date <= end_of_next_month
                )
                filters_applied.append(f"billing date is from {today} to {end_of_next_month}")

            if params.billing_date_is_null:
                stmt = stmt.where(Contract.billing_prompt_next_date.is_(None))
                filters_applied.append("billing date is not set")

            if params.billing_frequency:
                stmt = stmt.where(Contract.billing_frequency.ilike(f"%{params.billing_frequency}%"))
                filters_applied.append(f"billing frequency is '{params.billing_frequency}'")

            if params.contract_type:
                stmt = stmt.where(Contract.contract_type.ilike(f"%{params.contract_type}%"))
                filters_applied.append(f"contract type is '{params.contract_type}'")

            if params.min_amount is not None:
                stmt = stmt.where(Contract.original_amount >= params.min_amount)
                filters_applied.append(f"amount greater than ${params.min_amount:,.2f}")

            if params.max_amount is not None:
                stmt = stmt.where(Contract.original_amount <= params.max_amount)
                filters_applied.append(f"amount less than ${params.max_amount:,.2f}")

            if params.start_date_from:
                try:
                    start_date = datetime.strptime(params.start_date_from, "%Y-%m-%d").date()
                    stmt = stmt.where(Contract.start_date >= start_date)
                    filters_applied.append(f"start date >= {params.start_date_from}")
                except ValueError:
                    pass

            if params.start_date_to:
                try:
                    end_date = datetime.strptime(params.start_date_to, "%Y-%m-%d").date()
                    stmt = stmt.where(Contract.start_date <= end_date)
                    filters_applied.append(f"start date <= {params.start_date_to}")
                except ValueError:
                    pass

            stmt = stmt.order_by(Contract.created_at.desc())

            # Execute the statement
            result = await session.execute(stmt)
            contracts = result.scalars().all()

            print(f"🔍 DEBUG: Found {len(contracts)} contracts after filtering")
            for contract in contracts:
                print(f"🔍 DEBUG: Contract {contract.contract_id} - billing_date: {contract.billing_prompt_next_date}, client: {contract.client.client_name}")

            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                    "contract_type": contract.contract_type,
                    "billing_frequency": contract.billing_frequency,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else 'Not set',
                } for contract in contracts
            ]

            message = f"📋 Found {len(contract_list)} contracts"
            if filters_applied:
                message += " where " + " and ".join(filters_applied)
            message += "."

            if not params.billing_date_is_null:
                count_stmt = select(func.count()).select_from(Contract).where(
                    Contract.billing_prompt_next_date.is_(None)
                )
                count_result = await session.execute(count_stmt)
                null_billing_date_count = count_result.scalar()

                if null_billing_date_count > 0:
                    message += f" (Note: {null_billing_date_count} contracts have no billing prompt date set.)"

            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to search contracts: {str(e)}")
    

async def get_all_clients_tool() -> ContractToolResult:
    """Tool for getting all clients in the system with basic information"""
    try:
        # Get all clients
        async with get_ai_db() as session:
            stmt = select(Client).order_by(Client.client_name)
            result = await session.execute(stmt)
            clients = result.scalars().all()
                
            client_list = []
            for client in clients:
                client_list.append({
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "created_at": str(client.created_at) if client.created_at else None
                })
            
            # Format rich client information
            message = f"📋 **All Clients ({len(client_list)} clients):**\n\n"
            
            for i, client in enumerate(client_list, 1):
                message += f"**{i}. {client['client_name']}**\n"
                message += f"- **Industry:** {client['industry'] or 'Not specified'}\n"
                message += f"- **Primary Contact:** {client['primary_contact_name'] or 'Not specified'}\n"
                message += f"- **Email:** {client['primary_contact_email'] or 'Not specified'}\n"
                message += f"- **Company Size:** {client['company_size'] or 'Not specified'}\n"
                if client['created_at']:
                    try:
                        created_date = datetime.fromisoformat(client['created_at'].replace('Z', '+00:00'))
                        message += f"- **Created:** {created_date.strftime('%B %d, %Y')}\n"
                    except:
                        message += f"- **Created:** {client['created_at']}\n"
                message += f"\n"
            
            # Add summary
            industries = list(set(c["industry"] for c in client_list if c["industry"]))
            has_contacts = len([c for c in client_list if c["primary_contact_name"] or c["primary_contact_email"]])
            
            message += f"**Summary:**\n"
            message += f"- **Total Clients:** {len(client_list)}\n"
            message += f"- **Clients with Contact Info:** {has_contacts}\n"
            if industries:
                message += f"- **Industries:** {', '.join(industries)}\n"

            return ContractToolResult(
                success=True,
                message=message,
                data={
                    "clients": client_list,
                    "count": len(client_list),
                    "summary": {
                        "total_clients": len(client_list),
                        "industries": industries,
                        "has_contacts": has_contacts
                    }
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get all clients: {str(e)}"
        )

async def get_all_clients_with_contracts_tool() -> ContractToolResult:
    """Tool for getting all clients with their contracts - comprehensive view"""
    try:
        # Get all clients
        async with get_ai_db() as session:
            stmt = select(Client).order_by(Client.client_name)
            result = await session.execute(stmt)
            clients = result.scalars().all()
            
            clients_with_contracts = []
            total_contracts = 0
            
            for client in clients:
                # Get all contracts for this client
                contracts = await session.execute(select(Contract).filter(Contract.client_id == client.client_id))
                contracts = contracts.scalars().all()
                
                contract_list = []
                for contract in contracts:
                    contract_list.append({
                        "contract_id": contract.contract_id,
                        "contract_type": contract.contract_type,
                        "status": contract.status,
                        "original_amount": float(contract.original_amount) if contract.original_amount else None,
                        "current_amount": float(contract.current_amount) if contract.current_amount else None,
                        "billing_frequency": contract.billing_frequency,
                        "start_date": str(contract.start_date) if contract.start_date else None,
                        "end_date": str(contract.end_date) if contract.end_date else None,
                        "created_at": str(contract.created_at) if contract.created_at else None
                    })
                
                total_contracts += len(contract_list)
                
                clients_with_contracts.append({
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "created_at": str(client.created_at) if client.created_at else None,
                    "contracts": contract_list,
                    "contract_count": len(contract_list)
                })
            
            # Format rich client information similar to get_contracts_by_client_tool
            message = f"📋 **All Clients Overview ({len(clients_with_contracts)} clients, {total_contracts} total contracts):**\n\n"
            
            for i, client in enumerate(clients_with_contracts, 1):
                message += f"**{i}. {client['client_name']}**\n"
                message += f"- **Industry:** {client['industry'] or 'Not specified'}\n"
                message += f"- **Primary Contact:** {client['primary_contact_name'] or 'Not specified'}\n"
                message += f"- **Email:** {client['primary_contact_email'] or 'Not specified'}\n"
                message += f"- **Company Size:** {client['company_size'] or 'Not specified'}\n"
                message += f"- **Contracts:** {client['contract_count']} contract(s)\n"
                
                if client['contracts']:
                    message += f"  **Contract Details:**\n"
                    for j, contract in enumerate(client['contracts'], 1):
                        amount = f"${contract['original_amount']:,.2f}" if contract['original_amount'] else "Not set"
                        status = contract['status'].title() if contract['status'] else "Unknown"
                        message += f"    {j}. Contract {contract['contract_id']} - {contract['contract_type']} ({status}) - {amount}\n"
                else:
                    message += f"  *No contracts*\n"
                message += f"\n"
            
            # Add summary
            clients_with_contracts_count = len([c for c in clients_with_contracts if c["contract_count"] > 0])
            clients_without_contracts_count = len([c for c in clients_with_contracts if c["contract_count"] == 0])
            industries = list(set(c["industry"] for c in clients_with_contracts if c["industry"]))
            
            message += f"**Summary:**\n"
            message += f"- **Total Clients:** {len(clients_with_contracts)}\n"
            message += f"- **Clients with Contracts:** {clients_with_contracts_count}\n"
            message += f"- **Clients without Contracts:** {clients_without_contracts_count}\n"
            message += f"- **Total Contracts:** {total_contracts}\n"
            if industries:
                message += f"- **Industries:** {', '.join(industries)}\n"

            return ContractToolResult(
                success=True,
                message=message,
                data={
                    "clients_with_contracts": clients_with_contracts,
                    "summary": {
                        "total_clients": len(clients_with_contracts),
                        "total_contracts": total_contracts,
                        "clients_with_contracts": clients_with_contracts_count,
                        "clients_without_contracts": clients_without_contracts_count,
                        "industries": industries
                    }
                }
            )
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get clients with contracts: {str(e)}"
        )


async def analyze_contract_tool(contract_text: str) -> ContractToolResult:
    """Tool for analyzing contract content"""
    try:
        # Simple keyword-based analysis (placeholder for advanced AI analysis)
        analysis = {
            "contract_type": "Unknown",
            "key_terms": [],
            "amounts": [],
            "dates": [],
            "risks": [],
            "confidence": 0.7
        }
        
        # Basic keyword detection
        if "fixed price" in contract_text.lower():
            analysis["contract_type"] = "Fixed Price"
        elif "hourly" in contract_text.lower():
            analysis["contract_type"] = "Hourly"
        elif "retainer" in contract_text.lower():
            analysis["contract_type"] = "Retainer"
        
        # Extract potential amounts
        
        amounts = re.findall(r'\$[\d,]+\.?\d*', contract_text)
        analysis["amounts"] = amounts[:5]  # Limit to first 5 amounts
        
        return ContractToolResult(
            success=True,
            message="✅ Contract analysis completed",
            data={"analysis": analysis}
        )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to analyze contract: {str(e)}"
        )

async def get_contracts_by_billing_date_tool(start_date: str, end_date: str) -> ContractToolResult:
    """Tool for getting contracts with billing prompt dates within a specific range"""
    
    try:
        async with get_ai_db() as session:
        
        # Parse the date range
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return ContractToolResult(
                    success=False,
                    message="❌ Invalid date format. Please use YYYY-MM-DD format."
                )
            
            # Get contracts with billing prompt dates in the specified range

            contracts_temp = await session.execute(select(Contract).join(Client).options(selectinload(Contract.client)).filter(
                Contract.billing_prompt_next_date.isnot(None),
                Contract.billing_prompt_next_date >= start_dt,
                Contract.billing_prompt_next_date <= end_dt
            ).order_by(Contract.billing_prompt_next_date.asc()))
            contracts = contracts_temp.scalars().all()


            contract_list = []
            for contract in contracts:
                contract_list.append({
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else None,
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "termination_date": str(contract.termination_date) if contract.termination_date else None,
                    "amendments": contract.amendments,
                    "notes": contract.notes,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "has_document": bool(contract.document_filename),
                    "document_filename": contract.document_filename,
                    "document_file_size": contract.document_file_size,
                    "document_uploaded_at": str(contract.document_uploaded_at) if contract.document_uploaded_at else None,
                    "document_download_url": f"/contracts/{contract.contract_id}/document" if contract.document_filename else None,
                })
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with billing prompt dates between {start_date} and {end_date}",
                data={
                    "contracts": contract_list,
                    "count": len(contract_list),
                    "date_range": {
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get contracts by billing date: {str(e)}"
        )


class DeleteContractDocumentParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None

class DeleteContractParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None
    delete_all: bool = False  # For handling "all" command
    user_response: Optional[str] = None  # For handling contract ID responses like "1", "2", etc.

class DeleteClientParams(BaseModel):
    client_name: str
    confirm_deletion: bool = False
    user_response: Optional[str] = None  # For handling "yes" responses

async def delete_contract_document_tool(params: DeleteContractDocumentParams) -> ContractToolResult:
    """Delete contract document for a client"""
    try:
        async with get_ai_db() as session:
            # Get client
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found"
                )
            
            # Get contract
            if params.contract_id:
                # Delete specific contract document
                contract_result = await session.execute(
                    select(Contract).filter(
                        Contract.contract_id == params.contract_id,
                        Contract.client_id == client.client_id
                    )
                )
                contract = contract_result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract ID {params.contract_id} not found for client '{params.client_name}'"
                    )
                contracts = [contract]
            else:
                # Get only contracts that have documents uploaded
                contract_result = await session.execute(
                    select(Contract).options(
                        selectinload(Contract.client)
                    ).filter(
                        and_(
                            Contract.client_id == client.client_id,
                            Contract.document_filename.isnot(None),
                            Contract.document_filename != ""
                        )
                    )
                )
                contracts = contract_result.scalars().all()
                
                # Handle case where no contracts have documents
                if not contracts:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts with uploaded documents found for client '{params.client_name}'.\n\nAll contracts for this client either have no contract documents uploaded or the documents have been removed."
                    )
                
                # If multiple contracts with documents, ask user to specify which one
                if len(contracts) > 1:
                    contract_list = []
                    storage_service = SupabaseStorageService()
                    
                    for i, c in enumerate(contracts, 1):
                        amount = f"${c.original_amount:,.2f}" if c.original_amount else "N/A"
                        status = c.status.lower()
                        start_date = str(c.start_date) if c.start_date else "Not set"
                        
                        # Add download link for the document
                        if c.document_filename:
                            download_url = storage_service.get_contract_document_url(c.document_file_path) if c.document_file_path else f"/contracts/{c.contract_id}/document"
                            document_info = f"📄 [Download: {c.document_filename}]({download_url})"
                        else:
                            document_info = "No contract document"
                        
                        contract_info = f"{i}. **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {status} (Start: {start_date})\n   {document_info}"
                        contract_list.append(contract_info)
                    
                    return ContractToolResult(
                        success=False,
                        message=f"🔍 **Contracts with uploaded documents for '{client.client_name}' (select one to delete):**\n\n" + "\n".join(contract_list) + f"\n\nPlease specify which contract ID you want to delete the document for (e.g., 'delete contract document for {client.client_name} contract {contracts[0].contract_id}')"
                    )
            
            # Delete documents
            deleted_count = 0
            storage_service = SupabaseStorageService()
            
            for contract in contracts:
                if contract.document_file_path:
                    try:
                        deleted = await storage_service.delete_contract_document(contract.document_file_path)
                        if deleted:
                            # Clear document fields in database
                            contract.document_filename = None
                            contract.document_file_path = None
                            contract.document_bucket_name = None
                            contract.document_file_size = None
                            contract.document_mime_type = None
                            contract.document_uploaded_at = None
                            contract.ocr_extracted_data = None
                            deleted_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to delete document for contract {contract.contract_id}: {str(e)}")
            
            if deleted_count > 0:
                await session.commit()
                return ContractToolResult(
                    success=True,
                    message=f"✅ Successfully deleted {deleted_count} contract document(s) for **{client.client_name}**"
                )
            else:
                return ContractToolResult(
                    success=False,
                    message=f"❌ No contract documents found to delete for **{client.client_name}**"
                )
                
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to delete contract document: {str(e)}"
        )


async def delete_contract_tool(params: DeleteContractParams, context: Optional[Dict[str, Any]] = None) -> ContractToolResult:
    """Delete a contract for a client"""
    try:
        async with get_ai_db() as session:
            
            # Get client
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found"
                )
            
            # Get contract(s)
            if params.contract_id:
                # Delete specific contract
                contract_result = await session.execute(
                    select(Contract).options(
                        selectinload(Contract.client)
                    ).filter(
                        Contract.contract_id == params.contract_id,
                        Contract.client_id == client.client_id
                    )
                )
                contract = contract_result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract ID {params.contract_id} not found for client '{params.client_name}'"
                    )
                contracts = [contract]
            elif params.user_response and params.user_response.strip():
                # User responded with a contract ID - extract number from various formats
                user_input = params.user_response.strip().lower()
                requested_id = None
                
                # Use stored client context if available
                if context and 'current_client' in context and not params.client_name:
                    params.client_name = context['current_client']
                
                # Handle various formats: "106", "contract 106", "contract id 106", "id 106"
                if user_input.isdigit():
                    requested_id = int(user_input)
                elif "contract id" in user_input:
                    # Extract number after "contract id"
                    parts = user_input.split("contract id")
                    if len(parts) > 1:
                        number_part = parts[1].strip()
                        if number_part.isdigit():
                            requested_id = int(number_part)
                elif "contract" in user_input:
                    # Extract number after "contract"
                    parts = user_input.split("contract")
                    if len(parts) > 1:
                        number_part = parts[1].strip()
                        if number_part.isdigit():
                            requested_id = int(number_part)
                elif "id" in user_input:
                    # Extract number after "id"
                    parts = user_input.split("id")
                    if len(parts) > 1:
                        number_part = parts[1].strip()
                        if number_part.isdigit():
                            requested_id = int(number_part)
                
                if not requested_id:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Could not extract contract ID from '{params.user_response}'. Please provide a valid contract ID number."
                    )
                contract_result = await session.execute(
                    select(Contract).options(
                        selectinload(Contract.client)
                    ).filter(
                        Contract.contract_id == requested_id,
                        Contract.client_id == client.client_id
                    )
                )
                contract = contract_result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract ID {requested_id} not found for client '{params.client_name}'"
                    )
                contracts = [contract]
            else:
                # Check if client has multiple contracts
                contracts_result = await session.execute(
                    select(Contract).options(
                        selectinload(Contract.client)
                    ).filter(Contract.client_id == client.client_id)
                )
                contracts = contracts_result.scalars().all()
                
                if not contracts:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{params.client_name}'"
                    )
                
                # If multiple contracts, check if user wants to delete all
                if len(contracts) > 1:
                    if params.delete_all:
                        # User wants to delete all contracts - proceed with deletion
                        pass
                    else:
                        # Ask user to specify which one or use "all"
                        contract_list = []
                        for i, c in enumerate(contracts, 1):
                            amount = f"${c.original_amount:,.2f}" if c.original_amount else "N/A"
                            status = c.status.lower()
                            start_date = str(c.start_date) if c.start_date else "Not set"
                            contract_info = f"{i}. **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {status} (Start: {start_date})"
                            contract_list.append(contract_info)
                        
                        # Store current client in context
                        # CRITICAL FIX: Ensure all values are hashable/serializable to prevent unhashable type errors
                        if context:
                            context['current_client'] = str(client.client_name)
                        
                        return ContractToolResult(
                            success=False,
                            message=f"🔍 {client.client_name} has {len(contracts)} contracts. Here are the details:\n\n" + "\n".join(contract_list) + f"\n\nPlease specify which contract ID you want to delete (e.g., 'delete contract for {client.client_name} contract {contracts[0].contract_id}') or 'delete all contracts for {client.client_name}'"
                        )
            
            # Delete contract(s) and their documents
            deleted_count = 0
            storage_service = SupabaseStorageService()
            
            for contract in contracts:
                try:
                    # Delete associated document if it exists
                    if contract.document_file_path:
                        try:
                            await storage_service.delete_contract_document(contract.document_file_path)
                        except Exception as e:
                            print(f"Warning: Failed to delete document for contract {contract.contract_id}: {str(e)}")
                    
                    # Delete contract from database
                    await session.delete(contract)
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"Warning: Failed to delete contract {contract.contract_id}: {str(e)}")
            
            await session.commit()
            
            if deleted_count > 0:
                # Include contract ID in success message if deleting specific contract
                if len(contracts) == 1 and params.contract_id:
                    contract_id = contracts[0].contract_id
                    message = f"✅ Successfully deleted contract {contract_id} and associated documents for **{client.client_name}**"
                else:
                    message = f"✅ Successfully deleted {deleted_count} contract(s) and associated documents for **{client.client_name}**"
                
                return ContractToolResult(
                    success=True,
                    message=message
                )
            else:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Failed to delete any contracts for **{client.client_name}**"
                )
                
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to delete contract: {str(e)}"
        )
    
async def delete_client_tool(params: DeleteClientParams) -> ContractToolResult:
    """Delete a client and all associated contracts and documents"""
    try:
        async with get_ai_db() as session:
            # Get client - handle multiple results gracefully
            try:
                client = await get_client_by_name(params.client_name, session)
            except Exception as e:
                # If there's a database error (like multiple results), treat as client not found
                print(f"Database error in delete_client_tool: {e}")
                client = None
            
            if not client:
                # Client not found - simply inform the user
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found in the system. Please check the client name and try again."
                )
            
            # Get all contracts for this client
            contracts_result = await session.execute(
                select(Contract).options(
                    selectinload(Contract.client)
                ).filter(Contract.client_id == client.client_id)
            )
            contracts = contracts_result.scalars().all()
            
            # Check if user is confirming with "yes" or similar responses
            confirmation_keywords = ['yes', 'y', 'confirm', 'ok', 'okay', 'alright', 'go ahead', 'proceed', 'delete', 'sure']
            user_confirmed = (params.user_response and 
                            any(keyword in params.user_response.lower().strip() for keyword in confirmation_keywords))
            
            # Also check if confirm_deletion is explicitly set to true
            if params.confirm_deletion:
                user_confirmed = True
            
            # Check if user explicitly said to delete with contracts (skip confirmation)
            skip_confirmation = ('and all' in params.client_name.lower() or 
                               'and all its' in params.client_name.lower() or
                               'and all contracts' in params.client_name.lower())
            
            if not contracts:
                # No contracts, show confirmation first
                if user_confirmed or skip_confirmation or params.confirm_deletion:
                    # User confirmed, proceed with deletion
                    pass  # Will continue to deletion code below
                else:
                    return ContractToolResult(
                        success=True,
                        message=(
                            f"⚠️ **Confirm deletion of client '{client.client_name}'**\n\n"
                            f"**This will permanently delete:**\n"
                            f"- All client contact information\n"
                            f"- All billing history\n\n"
                            f"Type 'yes' to confirm deletion or 'no' to cancel."
                        )
                    )
            else:
                # Has contracts, check if user confirmed
                if user_confirmed or skip_confirmation or params.confirm_deletion:
                    # User confirmed, proceed with deletion
                    pass  # Will continue to deletion code below
                else:
                    # Show confirmation with contract details
                    contract_list = []
                    for c in contracts:
                        amount = f"${c.original_amount:,.2f}" if c.original_amount else "N/A"
                        contract_list.append(f"- **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {c.status}")
                    
                    return ContractToolResult(
                        success=True,
                        message=(
                            f"⚠️ **Confirm deletion of client '{client.client_name}'**\n\n"
                            f"**This will permanently delete:**\n"
                            f"- {len(contracts)} contract(s) and their documents\n"
                            f"- All client contact information\n"
                            f"- All billing history\n\n"
                            f"**Contracts to be deleted:**\n" + "\n".join(contract_list) + "\n\n"
                            f"Type 'yes' to confirm deletion or 'no' to cancel."
                        )
                    )
            
            # Proceed with deletion (only reached if user confirmed or skip_confirmation is True)
            deleted_contracts = 0
            deleted_documents = 0
            storage_service = SupabaseStorageService()
            
            # Delete all contracts and their documents
            for contract in contracts:
                try:
                    # Delete associated document if it exists
                    if contract.document_file_path:
                        try:
                            await storage_service.delete_contract_document(contract.document_file_path)
                            deleted_documents += 1
                        except Exception as e:
                            print(f"Warning: Failed to delete document for contract {contract.contract_id}: {str(e)}")
                    
                    # Delete contract from database
                    await session.delete(contract)
                    deleted_contracts += 1
                    
                except Exception as e:
                    print(f"Warning: Failed to delete contract {contract.contract_id}: {str(e)}")
            
            # Delete client contacts
            contacts_result = await session.execute(
                select(ClientContact).filter(ClientContact.client_id == client.client_id)
            )
            contacts = contacts_result.scalars().all()
            deleted_contacts = 0
            
            for contact in contacts:
                try:
                    await session.delete(contact)
                    deleted_contacts += 1
                except Exception as e:
                    print(f"Warning: Failed to delete contact {contact.contact_id}: {str(e)}")
            
            # Finally, delete the client
            await session.delete(client)
            await session.commit()
            
            return ContractToolResult(
                success=True,
                message=f"✅ Successfully deleted client **{client.client_name}** and all associated data:\n- {deleted_contracts} contract(s)\n- {deleted_documents} document(s)\n- {deleted_contacts} contact(s)"                              
            )
                
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to delete client: {str(e)}"
        )


async def get_contracts_with_documents_tool(params: SearchContractsParams, context: Dict[str, Any]) -> ContractToolResult:
    """Get contracts that have documents uploaded for a specific client or all clients"""
    try:
        async with get_ai_db() as session:
            # Build query for contracts with documents
            query = select(Contract).options(
                selectinload(Contract.client)
            ).filter(
                Contract.document_filename.isnot(None),
                Contract.document_filename != ""
            )
            
            # Filter by client if specified
            if params.client_name:
                client = await get_client_by_name(params.client_name, session)
                if not client:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{params.client_name}' not found."
                    )
                query = query.filter(Contract.client_id == client.client_id)
            
            # Execute query
            result = await session.execute(query.order_by(Contract.created_at.desc()))
            contracts = result.scalars().all()
            
            if not contracts:
                client_msg = f" for client '{params.client_name}'" if params.client_name else ""
                return ContractToolResult(
                    success=True,
                    message=f"📄 No contracts with uploaded documents found{client_msg}."
                )
            
            # Format the results
            contract_list = []
            for contract in contracts:
                # Format file size
                if contract.document_file_size and contract.document_file_size > 0:
                    file_size_mb = contract.document_file_size / (1024 * 1024)
                    file_size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{contract.document_file_size} bytes"
                else:
                    file_size_display = "Unknown"
                
                # Format amount
                amount = f"${contract.original_amount:,.2f}" if contract.original_amount else "N/A"
                
                # Format dates
                start_date = contract.start_date.strftime('%B %d, %Y') if contract.start_date else "Not set"
                uploaded_date = contract.document_uploaded_at.strftime('%B %d, %Y, %I:%M %p') if contract.document_uploaded_at else "N/A"
                
                contract_info = f"**Contract ID {contract.contract_id}** - {contract.client.client_name}\n"
                contract_info += f"- **Type:** {contract.contract_type}\n"
                contract_info += f"- **Status:** {contract.status}\n"
                contract_info += f"- **Amount:** {amount}\n"
                contract_info += f"- **Start Date:** {start_date}\n"
                
                # Create download URL for document
                storage_service = SupabaseStorageService()
                download_url = storage_service.get_contract_document_url(contract.document_file_path) if contract.document_file_path else f"/contracts/{contract.contract_id}/document"
                
                contract_info += f"- **Contract Document:** [{contract.document_filename}]({download_url})\n"
                contract_info += f"- **File Size:** {file_size_display}\n"
                contract_info += f"- **Uploaded:** {uploaded_date}\n"
                
                contract_list.append(contract_info)
            
            # Create response message
            client_msg = f" for **{params.client_name}**" if params.client_name else ""
            response_message = f"📄 **Contracts with uploaded contract documents{client_msg}:**\n\n" + "\n\n".join(contract_list)
            
            return ContractToolResult(
                success=True,
                message=response_message,
                data={
                    "contracts_with_documents": len(contracts),
                    "client_name": params.client_name,
                    "contracts": [
                        {
                            "contract_id": contract.contract_id,
                            "client_name": contract.client.client_name,
                            "contract_type": contract.contract_type,
                            "status": contract.status,
                            "original_amount": float(contract.original_amount) if contract.original_amount else None,
                            "start_date": contract.start_date.isoformat() if contract.start_date else None,
                            "document_filename": contract.document_filename,
                            "document_file_size": contract.document_file_size,
                            "document_uploaded_at": contract.document_uploaded_at.isoformat() if contract.document_uploaded_at else None
                        }
                        for contract in contracts
                    ]
                }
            )
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get contracts with documents: {str(e)}"
        )
