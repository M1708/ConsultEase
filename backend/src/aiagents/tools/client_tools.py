from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from pydantic import BaseModel
from src.database.core.models import Client, User
from src.database.api.clients import get_client_by_name
from datetime import datetime
from src.database.core.database import get_ai_db
import uuid



class ClientToolResult(BaseModel):
    """Result object for client tool operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class UpdateClientParams(BaseModel):
    client_name: str
    industry: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    company_size: Optional[str] = None
    notes: Optional[str] = None

async def update_client_tool(params: UpdateClientParams, context: Dict[str, Any] = None) -> ClientToolResult:
    """Tool for updating existing client information"""
    try:
        print(f"🔍 DEBUG: Update CLIENT tool called (this should NOT be called for contract operations)")
        print(f"🔍 DEBUG: Params: {params}")
        print(f"🔍 DEBUG: Context: {context}")
        
        async with get_ai_db() as session:
        
            if not context or 'user_id' not in context:
                return ClientToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ClientToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found."
                )
            
            update_fields = []
            if params.industry:
                client.industry = params.industry
                update_fields.append("industry")
            
            if params.primary_contact_name:
                client.primary_contact_name = params.primary_contact_name
                update_fields.append("primary_contact_name")
            
            if params.primary_contact_email:
                client.primary_contact_email = params.primary_contact_email
                update_fields.append("primary_contact_email")
            
            if params.company_size:
                client.company_size = params.company_size
                update_fields.append("company_size")
            
            if params.notes:
                client.notes = params.notes
                update_fields.append("notes")
            

            
            if not update_fields:
                return ClientToolResult(
                    success=False,
                    message=f"❌ No fields to update for client '{params.client_name}'."
                )
            
            
            if isinstance(user_id, int):
                client.updated_by = uuid.UUID(int=user_id)
            elif isinstance(user_id, str):
                try:
                    client.updated_by = uuid.UUID(user_id)
                except ValueError:
                    client.updated_by = uuid.uuid5(uuid.NAMESPACE_OID, user_id)
            else:
                client.updated_by = user_id
            client.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(client)
            
            return ClientToolResult(
                success=True,
                message=f"✅ Successfully updated client '{client.client_name}'. Updated fields: {', '.join(update_fields)}",
                data={
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "updated_fields": update_fields,
                }
            )
        
    except Exception as e:
        return ClientToolResult(
            success=False,
            message=f"❌ Failed to update client for {params.client_name}: {str(e)}"
        )
    

async def get_client_details_tool(client_name: str) -> ClientToolResult:
    """Tool for getting detailed client information with rich formatting"""
    
    try:
        async with get_ai_db() as session:
            # Get client information
            client = await get_client_by_name(client_name, session)
            if not client:
                return ClientToolResult(
                    success=False,
                    message=f"❌ Client '{client_name}' not found."
                )
            
            # Get client's contracts for complete view
            from sqlalchemy import select
            from src.database.core.models import Contract
            contracts_temp = await session.execute(select(Contract).filter(Contract.client_id == client.client_id))
            contracts = contracts_temp.scalars().all()
            
            # Format rich client information (same style as get_contracts_by_client_tool)
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
                        document_info = "No document"
                    
                    contract_details += f"""
**Contract {i} (ID: {contract.contract_id}):**

- **Type:** {contract.contract_type}
- **Status:** {status}  
- **Original Amount:** {amount}
- **Current Amount:** {current_amount}
- **Start Date:** {start_date}
- **End Date:** {end_date}
- **Billing Frequency:** {billing_freq}
- **Next Billing Date:** {next_billing}
- **Termination Date:** {termination}
- **Notes:** {notes}
- **Document:** {document_info}
"""
                client_info += contract_details
            else:
                client_info += "\n\n**Contract Details:**\nNo contracts found for this client."
            
            return ClientToolResult(
                success=True,
                message=client_info,
                data={
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "notes": client.notes,
                    "created_at": str(client.created_at) if client.created_at else None,
                    "updated_at": str(client.updated_at) if client.updated_at else None,
                    "contracts": [
                        {
                            "contract_id": contract.contract_id,
                            "contract_type": contract.contract_type,
                            "status": contract.status,
                            "original_amount": float(contract.original_amount) if contract.original_amount else None,
                            "current_amount": float(contract.current_amount) if contract.current_amount else None,
                            "billing_frequency": contract.billing_frequency,
                            "start_date": str(contract.start_date) if contract.start_date else None,
                            "end_date": str(contract.end_date) if contract.end_date else None,
                            "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                            "termination_date": str(contract.termination_date) if contract.termination_date else None,
                            "notes": contract.notes,
                            "document_filename": contract.document_filename,
                            "document_file_size": contract.document_file_size,
                            "document_uploaded_at": str(contract.document_uploaded_at) if contract.document_uploaded_at else None,
                        } for contract in contracts
                    ]
                }
            )
        
    except Exception as e:
        return ClientToolResult(
            success=False,
            message=f"❌ Failed to get client details: {str(e)}"
        )
    
