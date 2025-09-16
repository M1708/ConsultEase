from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
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

class UpdateContractParams(BaseModel):
    client_name: str 
    contract_id: Optional[int] = None
    user_response: Optional[str] = None  # User's response to contract selection prompt
    update_all: Optional[bool] = False  # Whether to update all contracts for the client
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_type: Optional[str] = None
    original_amount: Optional[float] = None
    billing_frequency: Optional[str] = None
    billing_prompt_next_date: Optional[str] = None
    status: Optional[str] = None
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
        if params.billing_frequency:
            contract.billing_frequency = params.billing_frequency
            updated_fields.append("billing_frequency")
        if params.billing_prompt_next_date:
            contract.billing_prompt_next_date = datetime.strptime(params.billing_prompt_next_date, "%Y-%m-%d").date()
            updated_fields.append("billing_prompt_next_date")
        if params.status:
            contract.status = params.status
            updated_fields.append("status")
        if params.notes is not None:
            contract.notes = params.notes
            updated_fields.append("notes")
        
        # Update the updated_at timestamp
        contract.updated_at = datetime.utcnow()
        
        await session.commit()
        
        message = f"✅ Successfully updated contract {contract.contract_id} for {contract.client.client_name}"
        if updated_fields:
            message += f". Updated fields: {', '.join(updated_fields)}"
        
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
                    # We'll handle this after the contract selection logic
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
                    contract_info = f"{i}. Contract ID {c.contract_id}: {c.contract_type} ({amount}) - {status}, start date ({start_date})"
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
            
            # Apply updates to all selected contracts
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
            
            # Refresh all updated contracts
            for contract_to_update in contracts_to_update:
                await session.refresh(contract_to_update)
            
            # Build success message
            if params.update_all:
                message = f"✅ Successfully updated {len(contracts_to_update)} contracts for '{client.client_name}'. Updated fields: {', '.join(update_fields)}"
            else:
                message = f"✅ Successfully updated contract for '{client.client_name}'. Updated fields: {', '.join(update_fields)}"
            
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
                            contract_list.append(f"{i}. **Contract ID {c.contract_id}**: {c.contract_type} ({amount}) - {status} (Start: {start_date})")

                        # Create the response
                        response_message = f"📋 {client.client_name} has {len(contracts)} contracts. Here are the details:\n\n" + "\n".join(contract_list) + f"\n\nPlease specify which contract ID you want to upload the document for (e.g., \"upload document for {client.client_name} contract {contracts[0].contract_id}\")."
                        
                        return ContractToolResult(
                            success=False,
                            message=response_message
                        )

        # If we have a specific contract (from contract_id) or only one contract from client search
        if contract or len(contracts) == 1:
            if not contract:
                contract = contracts[0]
            
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
                
                # Validate base64 string
                if len(file_data_clean) % 4 != 0:
                    return ContractToolResult(
                        success=False,
                        message="❌ Invalid base64 string length. Please ensure the file was properly encoded."
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
                file_size_mb = contract.document_file_size / (1024 * 1024) if contract.document_file_size else 0
                file_size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{contract.document_file_size} bytes"
                
                # Create download URL - use signed URL from storage service
                file_path = upload_result.get("file_path")
                print(f"🔗 URL DEBUG: File path from upload result: {file_path}")
                
                if file_path:
                    download_url = storage_service.get_contract_document_url(file_path)
                    print(f"🔗 URL DEBUG: Generated signed URL: {download_url}")
                    print(f"🔗 URL DEBUG: URL length: {len(download_url)} characters")
                    print(f"🔗 URL DEBUG: URL starts with: {download_url[:50]}...")
                else:
                    download_url = f"/contracts/{contract.contract_id}/document"
                    print(f"🔗 URL DEBUG: Using fallback URL: {download_url}")
                
                # Check if this was auto-selected from session context
                context_note = ""
                if (context and 'last_created_contract' in context and 
                    context['last_created_contract'].get('contract_id') == contract.contract_id):
                    context_note = "\n\n💡 *Document uploaded to the recently created contract*"
                
                # Create the final message
                final_message = f"✅ Contract document uploaded successfully for **{contract.client.client_name}**\n\n📄 **Document Details:**\n- **Filename:** [{contract.document_filename}]({download_url})\n- **File Size:** {file_size_display}\n- **Contract ID:** {contract.contract_id}\n- **Uploaded At:** {contract.document_uploaded_at.strftime('%B %d, %Y, %I:%M %p') if contract.document_uploaded_at else 'N/A'}{context_note}"
                
                print(f"🔗 URL DEBUG: Final message being sent to frontend:")
                print(f"🔗 URL DEBUG: Message length: {len(final_message)} characters")
                print(f"🔗 URL DEBUG: Contains markdown link: {'[' in final_message and '](' in final_message}")
                print(f"🔗 URL DEBUG: Markdown format: [{contract.document_filename}]({download_url})")
                print(f"🔗 URL DEBUG: Message preview: {final_message[:200]}...")
                
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
                query = query.filter(
                    Client.client_name.ilike(f"%{search_term}%") |
                    Client.industry.ilike(f"%{search_term}%")
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

            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts for client '{client.client_name}'",
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
    

async def get_contracts_for_next_month_billing_tool(context: Dict[str, Any]) -> ContractToolResult:
    """Tool for getting contracts with a billing prompt date in the next month or later in the current month."""
    try:
        async with get_ai_db() as session:
            today = context.get('today', date.today())
            
            # Start of current month
            start_of_this_month = today.replace(day=1)
            
            # End of next month
            end_of_next_month = (start_of_this_month + relativedelta(months=2)) - timedelta(days=1)
            stmt = (
                    select(Contract)
                    .join(Client)
                    .options(selectinload(Contract.client))
                    .where(
                        Contract.billing_prompt_next_date.isnot(None),
                        Contract.billing_prompt_next_date >= today,
                        Contract.billing_prompt_next_date <= end_of_next_month
                    )
                    .order_by(Contract.billing_prompt_next_date.asc())
    )
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
            
            message = f"📋 Found {len(contract_list)} contracts with billing dates from {today.strftime('%Y-%m-%d')} to {end_of_next_month.strftime('%Y-%m-%d')}."
            if null_billing_date_count > 0:
                message += f" Additionally, {null_billing_date_count} contracts have no billing prompt date set."

            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts for next month's billing: {str(e)}")

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
                stmt = stmt.where(
                    Contract.billing_prompt_next_date.isnot(None),
                    Contract.billing_prompt_next_date >= today,
                    Contract.billing_prompt_next_date <= end_of_next_month
                )
                filters_applied.append("billing date is in the next month or later this month")

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
                filters_applied.append(f"amount >= ${params.min_amount:,.2f}")

            if params.max_amount is not None:
                stmt = stmt.where(Contract.original_amount <= params.max_amount)
                filters_applied.append(f"amount <= ${params.max_amount:,.2f}")

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
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(client_list)} clients in the system",
                data={
                    "clients": client_list,
                    "count": len(client_list),
                    "summary": {
                        "total_clients": len(client_list),
                        "industries": list(set(c["industry"] for c in client_list if c["industry"])),
                        "has_contacts": len([c for c in client_list if c["primary_contact_name"] or c["primary_contact_email"]])
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
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(clients_with_contracts)} clients with {total_contracts} total contracts",
                data={
                    "clients_with_contracts": clients_with_contracts,
                    "summary": {
                        "total_clients": len(clients_with_contracts),
                        "total_contracts": total_contracts,
                        "clients_with_contracts": len([c for c in clients_with_contracts if c["contract_count"] > 0]),
                        "clients_without_contracts": len([c for c in clients_with_contracts if c["contract_count"] == 0]),
                        "industries": list(set(c["industry"] for c in clients_with_contracts if c["industry"]))
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
                # Get all contracts for client to show list
                contract_result = await session.execute(
                    select(Contract).options(
                        selectinload(Contract.client)
                    ).filter(Contract.client_id == client.client_id)
                )
                contracts = contract_result.scalars().all()
                if not contracts:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{params.client_name}'"
                    )
                
                # If multiple contracts, ask user to specify which one
                if len(contracts) > 1:
                    contract_list = []
                    for c in contracts:
                        contract_list.append(f"- Contract ID {c.contract_id}: {c.contract_type} (${c.original_amount:,.2f}) - {c.status}")
                    
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{client.client_name}' has {len(contracts)} contracts. Please specify which contract ID you want to delete the document for:\n\n" + "\n".join(contract_list) + "\n\nUse: 'delete contract document for [client] contract [ID]'"
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
                        for c in contracts:
                            contract_list.append(f"- Contract ID {c.contract_id}: {c.contract_type} (${c.original_amount:,.2f}) - {c.status}")
                        
                        # Store current client in context
                        # CRITICAL FIX: Ensure all values are hashable/serializable to prevent unhashable type errors
                        if context:
                            context['current_client'] = str(client.client_name)
                        
                        return ContractToolResult(
                            success=False,
                            message=f"❌ Client '{client.client_name}' has {len(contracts)} contracts. Please specify which contract ID you want to delete:\n\n" + "\n".join(contract_list) + "\n\nUse: 'delete contract for [client] contract [ID]' or 'delete all contracts for [client]'"
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
                return ContractToolResult(
                    success=True,
                    message=f"✅ Successfully deleted {deleted_count} contract(s) and associated documents for **{client.client_name}**"
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
            # Get client
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found"
                )
            
            # Get all contracts for this client
            contracts_result = await session.execute(
                select(Contract).options(
                    selectinload(Contract.client)
                ).filter(Contract.client_id == client.client_id)
            )
            contracts = contracts_result.scalars().all()
            
            # Check if user is confirming with "yes" or similar responses
            if params.user_response and params.user_response.lower().strip() in ['yes', 'y', 'confirm', 'ok', 'proceed', 'delete']:
                # User confirmed, proceed with deletion
                pass
            elif not params.confirm_deletion:
                # Show confirmation with contract details
                if not contracts:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{client.client_name}' has no contracts. Are you sure you want to delete this client?\n\n**Respond with 'yes' to confirm deletion.**"
                    )
                
                contract_list = []
                for c in contracts:
                    contract_list.append(f"- Contract ID {c.contract_id}: {c.contract_type} (${c.original_amount:,.2f}) - {c.status}")
                
                return ContractToolResult(
                    success=False,
                    message=f"⚠️ **WARNING: This will permanently delete client '{client.client_name}' and ALL associated data!**\n\n**Contracts to be deleted ({len(contracts)}):**\n" + "\n".join(contract_list) + f"\n\n**This action will also delete:**\n- All contract documents\n- All client contact information\n- All billing history\n\n**Respond with 'yes' to confirm deletion.**"
                )
            
            # Proceed with deletion
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
