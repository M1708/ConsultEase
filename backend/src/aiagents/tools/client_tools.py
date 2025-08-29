from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database.core.database import get_db
from src.database.core.models import Client, User
from src.aiagents.tools.contract_tools import get_client_by_name

class ClientToolResult:
    """Result object for client tool operations"""
    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data

class UpdateClientParams(BaseModel):
    client_name: str
    industry: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    company_size: Optional[str] = None
    notes: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

def update_client_tool(params: UpdateClientParams, context: Dict[str, Any] = None, db: Session = None) -> ClientToolResult:
    """Tool for updating existing client information"""
    try:
        from datetime import datetime
        
        # Always create a fresh database session to avoid session closure issues
        print(f"🔧 update_client_tool: Creating fresh database session")
        try:
            db = next(get_db())
            print(f"🔧 update_client_tool: Created fresh database session successfully")
        except Exception as session_error:
            print(f"🔧 update_client_tool: Failed to create database session: {session_error}")
            import traceback
            traceback.print_exc()
            return ClientToolResult(
                success=False,
                message=f"❌ Failed to establish database connection for {params.client_name}. Please try again later."
            )
        
        print(f"🔧 update_client_tool: Database session info - is_active: {db.is_active}")
        print(f"🔧 update_client_tool: Database session type: {type(db)}")
        
        # Test database connection
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            print(f"🔧 update_client_tool: Database connection test successful")
        except Exception as conn_error:
            print(f"🔧 update_client_tool: Database connection test failed: {conn_error}")
            print(f"🔧 update_client_tool: Connection error type: {type(conn_error)}")
            import traceback
            traceback.print_exc()
            return ClientToolResult(
                success=False,
                message=f"❌ Database connection failed while attempting to update the client information for {params.client_name}. Please try again later."
            )
        
        # Extract user_id from context
        print(f"🔧 update_client_tool: Context received: {context is not None}")
        if context:
            print(f"🔧 update_client_tool: Context keys: {list(context.keys())}")
            print(f"🔧 update_client_tool: Context contains user_id: {bool(context.get('user_id'))}")
        
        if not context or 'user_id' not in context:
            return ClientToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        print(f"🔧 update_client_tool: User authenticated successfully")
        
        # Find client by name
        client = get_client_by_name(params.client_name, db)
        if not client:
            return ClientToolResult(
                success=False,
                message=f"❌ Client '{params.client_name}' not found."
            )
        
        # Update client fields
        update_fields = []
        
        if params.industry:
            client.industry = params.industry
            update_fields.append("industry")
            print(f"🔧 update_client_tool: Setting industry to '{params.industry}'")
        
        if params.primary_contact_name:
            client.primary_contact_name = params.primary_contact_name
            update_fields.append("primary_contact_name")
            print(f"🔧 update_client_tool: Setting primary_contact_name to '{params.primary_contact_name}'")
        
        if params.primary_contact_email:
            client.primary_contact_email = params.primary_contact_email
            update_fields.append("primary_contact_email")
            print(f"🔧 update_client_tool: Setting primary_contact_email to '{params.primary_contact_email}'")
        
        if params.company_size:
            client.company_size = params.company_size
            update_fields.append("company_size")
            print(f"🔧 update_client_tool: Setting company_size to '{params.company_size}'")
        
        if params.notes:
            client.notes = params.notes
            update_fields.append("notes")
            print(f"🔧 update_client_tool: Setting notes to '{params.notes}'")
        
        if params.address:
            client.address = params.address
            update_fields.append("address")
            print(f"🔧 update_client_tool: Setting address to '{params.address}'")
        
        if params.phone:
            client.phone = params.phone
            update_fields.append("phone")
            print(f"🔧 update_client_tool: Setting phone to '{params.phone}'")
        
        if params.website:
            client.website = params.website
            update_fields.append("website")
            print(f"🔧 update_client_tool: Setting website to '{params.website}'")
        
        if not update_fields:
            return ClientToolResult(
                success=False,
                message=f"❌ No fields to update for client '{params.client_name}'."
            )
        
        # Set audit fields - convert user_id to UUID if needed
        import uuid
        if isinstance(user_id, int):
            # For testing, create a deterministic UUID from the integer
            client.updated_by = uuid.UUID(int=user_id)
        elif isinstance(user_id, str):
            try:
                client.updated_by = uuid.UUID(user_id)
            except ValueError:
                # If it's not a valid UUID string, create one from hash
                client.updated_by = uuid.uuid5(uuid.NAMESPACE_OID, user_id)
        else:
            client.updated_by = user_id
        client.updated_at = datetime.utcnow()
        
        print(f"🔧 update_client_tool: About to commit changes. Update fields: {update_fields}")
        print(f"🔧 update_client_tool: Database session info - is_active: {db.is_active}, is_modified: {db.is_modified(client)}")
        
        # Commit changes
        try:
            print(f"🔧 update_client_tool: About to commit. Session info - is_active: {db.is_active}")
            db.commit()
            print(f"🔧 update_client_tool: Changes committed successfully")
        except Exception as commit_error:
            print(f"🔧 update_client_tool: Commit failed: {commit_error}")
            print(f"🔧 update_client_tool: Commit error type: {type(commit_error)}")
            import traceback
            traceback.print_exc()
            try:
                db.rollback()
                print(f"🔧 update_client_tool: Rollback successful")
            except Exception as rollback_error:
                print(f"🔧 update_client_tool: Rollback failed: {rollback_error}")
            raise commit_error
        
        db.refresh(client)
        print(f"🔧 update_client_tool: Client refreshed successfully")
        
        # Verify the change is visible in the current session
        verification_client = db.query(Client).filter(Client.client_id == client.client_id).first()
        print(f"🔧 update_client_tool: Verification query successful")
        
        # Close the database session
        try:
            db.close()
            print(f"🔧 update_client_tool: Database session closed successfully")
        except Exception as close_error:
            print(f"🔧 update_client_tool: Error closing database session: {close_error}")
        
        return ClientToolResult(
            success=True,
            message=f"✅ Successfully updated client '{client.client_name}'. Updated fields: {', '.join(update_fields)}",
            data={
                "client_id": client.client_id,
                "client_name": client.client_name,
                "updated_fields": update_fields,
                "primary_contact_email": client.primary_contact_email,
                "primary_contact_name": client.primary_contact_name,
                "industry": client.industry,
                "company_size": client.company_size,
                "notes": client.notes
            }
        )
        
    except Exception as e:
        print(f"🔧 update_client_tool: General exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
                print(f"🔧 update_client_tool: Database session closed on error")
        except Exception as close_error:
            print(f"🔧 update_client_tool: Error closing database session on error: {close_error}")
        
        return ClientToolResult(
            success=False,
            message=f"❌ Failed to update client for {params.client_name}: {str(e)}"
        )

def get_client_details_tool(client_name: str, db: Session = None) -> ClientToolResult:
    """Tool for getting detailed client information"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Find client by name
        client = get_client_by_name(client_name, db)
        if not client:
            # Close the database session
            try:
                db.close()
            except Exception as close_error:
                print(f"🔧 get_client_details_tool: Error closing database session: {close_error}")
            
            return ClientToolResult(
                success=False,
                message=f"❌ Client '{client_name}' not found."
            )
        
        # Close the database session
        try:
            db.close()
        except Exception as close_error:
            print(f"🔧 get_client_details_tool: Error closing database session: {close_error}")
        
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
                "address": client.address,
                "phone": client.phone,
                "website": client.website,
                "created_at": str(client.created_at) if client.created_at else None,
                "updated_at": str(client.updated_at) if client.updated_at else None
            }
        )
        
    except Exception as e:
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
        except Exception as close_error:
            print(f"🔧 get_client_details_tool: Error closing database session on error: {close_error}")
        
        return ClientToolResult(
            success=False,
            message=f"❌ Failed to get client details: {str(e)}"
        )
