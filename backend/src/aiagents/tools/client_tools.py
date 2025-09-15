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
    """Tool for getting detailed client information"""
    
    try:
        async with get_ai_db() as session:
            client = await get_client_by_name(client_name, session)
            if not client:
                return ClientToolResult(
                    success=False,
                    message=f"❌ Client '{client_name}' not found."
                )
            
            return ClientToolResult(
                success=True,
                message=f"📋 Client details for '{client.client_name}'",
                data={
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
            )
        
    except Exception as e:
        return ClientToolResult(
            success=False,
            message=f"❌ Failed to get client details: {str(e)}"
        )
    
