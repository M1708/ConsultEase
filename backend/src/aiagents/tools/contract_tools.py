from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Client, Contract, ClientContact
from backend.src.database.core.schemas import ClientCreate, ContractCreate, ClientContactCreate
from backend.src.database.api.clients import create_client_internal, get_client_by_name
from backend.src.database.api.contracts import create_contract_internal
from backend.src.database.api.client_contacts import create_client_contact

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

def create_client_tool(params: CreateClientParams, context: Dict[str, Any] = None, db: Session = None) -> ContractToolResult:
    """Tool for creating new clients"""
    try:
        if db is None:
            db = next(get_db())
        
        # Use model_dump() for Pydantic v2 compatibility
        client_data = ClientCreate(**params.model_dump())
        
        # Extract user_id from context
        if not context or 'user_id' not in context:
            return ContractToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        result = create_client_internal(client_data, db, user_id)
        
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
        print(f"🛠️ create_client_tool: Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        error_result = ContractToolResult(
            success=False,
            message=f"❌ Failed to create client: {str(e)}"
        )
        print(f"🛠️ create_client_tool: Returning error result: {error_result}")
        return error_result

def search_clients_tool(search_term: Optional[str] = None, limit: int = 10, db: Session = None) -> ContractToolResult:
    """Tool for searching existing clients"""
    try:
        if db is None:
            db = next(get_db())
        
        query = db.query(Client)
        if search_term:
            search_lower = search_term.lower()
            query = query.filter(
                Client.client_name.ilike(f"%{search_term}%") |
                Client.industry.ilike(f"%{search_term}%")
            )
        
        clients = query.limit(limit).all()
        
        client_list = []
        for client in clients:
            client_list.append({
                "client_id": client.client_id,
                "client_name": client.client_name,
                "industry": client.industry,
                "primary_contact_name": client.primary_contact_name
            })
        
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

def analyze_contract_tool(contract_text: str) -> ContractToolResult:
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
        import re
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

class SmartContractParams(BaseModel):
    client_name: str
    contract_type: str  # "Fixed", "Hourly", "Retainer"
    original_amount: Optional[Decimal] = None
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None
    billing_frequency: Optional[str] = None  # "Monthly", "Weekly", "One-time"
    notes: Optional[str] = None

def smart_create_contract_tool(params: SmartContractParams, context: Dict[str, Any] = None, db: Session = None) -> ContractToolResult:
    """Smart tool for creating contracts by client name instead of client_id"""
    try:
        print(f"🔍 smart_create_contract_tool: Starting contract creation for client: {params.client_name}")
        
        if db is None:
            db = next(get_db())
        
        # Extract user_id from context
        if not context or 'user_id' not in context:
            return ContractToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        print(f"🔍 smart_create_contract_tool: Using user_id: {user_id}")
        
        # Search for clients that match the client name - more precise matching
        # First refresh the session to ensure we see any recently created clients
        db.flush()  # Ensure any pending changes are written
        
        matching_clients = []
        search_name_lower = params.client_name.lower()
        
        # Optimized query - search by name pattern instead of loading all clients
        search_pattern = f"%{params.client_name}%"
        potential_clients = db.query(Client).filter(
            Client.client_name.ilike(search_pattern)
        ).limit(10).all()  # Limit to 10 most likely matches
        
        for client in potential_clients:
            client_name_lower = client.client_name.lower()
            print(f"🔍 smart_create_contract_tool: Checking client: '{client.client_name}' (id: {client.client_id})")
            
            # Exact match first
            if client_name_lower == search_name_lower:
                matching_clients = [client]  # Exact match takes priority
                print(f"🔍 smart_create_contract_tool: Found exact match: {client.client_name}")
                break
            
            # Partial match - but more restrictive
            # Only match if the search term is a significant part of the client name
            if (search_name_lower in client_name_lower or 
                client_name_lower in search_name_lower or
                # Check if major words match (length > 3 to avoid matching short words like "Inc")
                any(word in client_name_lower for word in search_name_lower.split() if len(word) > 3)):
                matching_clients.append(client)
                print(f"🔍 smart_create_contract_tool: Found partial match: {client.client_name}")
        
        print(f"🔍 smart_create_contract_tool: Total matching clients found: {len(matching_clients)}")
        
        if len(matching_clients) == 0:
            # Client not found - return error asking agent to create client first
            return ContractToolResult(
                success=False,
                message=f"❌ Client '{params.client_name}' not found. Please create the client first using the create_client function, then create the contract."
            )
        
        elif len(matching_clients) > 1:
            # Multiple clients found - ask user to clarify
            client_options = []
            for i, client in enumerate(matching_clients, 1):
                client_info = f"{i}. **{client.client_name}**"
                if client.industry:
                    client_info += f" (Industry: {client.industry})"
                if client.primary_contact_name:
                    client_info += f" - Contact: {client.primary_contact_name}"
                client_options.append(client_info)
            
            return ContractToolResult(
                success=False,
                message=f"🔍 Found multiple clients matching '{params.client_name}'. Please specify which client you meant:\n\n" + 
                       "\n".join(client_options) + 
                       f"\n\nPlease rephrase your request with the full client name (e.g., 'Create {params.contract_type} contract for [Full Client Name]')."
            )
        
        # Single client found - proceed with contract creation
        client = matching_clients[0]
        
        # Parse dates
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
        
        # Create contract using the existing API
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
        
        result = create_contract_internal(contract_data, db, user_id)
        
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

class ContractDocumentParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None  # If not provided, will find latest contract for client
    document_action: str  # "upload" or "update"

def smart_contract_document_tool(params: ContractDocumentParams, db: Session = None) -> ContractToolResult:
    """Smart tool for handling contract documents by client name"""
    try:
        if db is None:
            db = next(get_db())
        
        contract = None
        
        if params.contract_id:
            # Use specific contract ID
            contract = db.query(Contract).filter(Contract.contract_id == params.contract_id).first()
            if not contract:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Contract with ID {params.contract_id} not found."
                )
        else:
            # Find client and their latest contract
            client = get_client_by_name(params.client_name, db)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found."
                )
            
            # Get the most recent contract for this client
            contract = db.query(Contract).filter(
                Contract.client_id == client.client_id
            ).order_by(Contract.created_at.desc()).first()
            
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

def get_contracts_by_client_tool(client_name: str, db: Session = None) -> ContractToolResult:
    """Tool for getting all contracts for a specific client by name"""
    try:
        if db is None:
            db = next(get_db())
        
        # Find client by name
        client = get_client_by_name(client_name, db)
        if not client:
            return ContractToolResult(
                success=False,
                message=f"❌ Client '{client_name}' not found."
            )
        
        # Get all contracts for this client
        contracts = db.query(Contract).filter(Contract.client_id == client.client_id).all()
        
        contract_list = []
        for contract in contracts:
            contract_list.append({
                "contract_id": contract.contract_id,
                "contract_type": contract.contract_type,
                "status": contract.status,
                "original_amount": float(contract.original_amount) if contract.original_amount else None,
                "start_date": str(contract.start_date) if contract.start_date else None,
                "end_date": str(contract.end_date) if contract.end_date else None,
                "has_document": bool(contract.document_filename),
                "document_filename": contract.document_filename
            })
        
        return ContractToolResult(
            success=True,
            message=f"📋 Found {len(contract_list)} contracts for client '{client.client_name}'",
            data={
                "client_name": client.client_name,
                "contracts": contract_list,
                "count": len(contract_list)
            }
        )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get contracts: {str(e)}"
        )

def get_all_contracts_tool(db: Session = None) -> ContractToolResult:
    """Tool for getting all contracts across all clients"""
    try:
        if db is None:
            db = next(get_db())
        
        # Get all contracts with client information
        contracts = db.query(Contract).join(Client).order_by(Contract.created_at.desc()).all()
        
        contract_list = []
        for contract in contracts:
            contract_list.append({
                "contract_id": contract.contract_id,
                "client_name": contract.client.client_name,
                "contract_type": contract.contract_type,
                "status": contract.status,
                "original_amount": float(contract.original_amount) if contract.original_amount else None,
                "start_date": str(contract.start_date) if contract.start_date else None,
                "end_date": str(contract.end_date) if contract.end_date else None,
                "has_document": bool(contract.document_filename),
                "document_filename": contract.document_filename
            })
        
        return ContractToolResult(
            success=True,
            message=f"📋 Found {len(contract_list)} contracts across all clients",
            data={
                "contracts": contract_list,
                "count": len(contract_list),
                "total_clients": len(set(c["client_name"] for c in contract_list))
            }
        )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get all contracts: {str(e)}"
        )

class UpdateContractParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_type: Optional[str] = None
    original_amount: Optional[float] = None
    billing_frequency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

def update_contract_tool(params: UpdateContractParams, context: Dict[str, Any] = None, db: Session = None) -> ContractToolResult:
    """Tool for updating existing contracts by client name"""
    try:
        from datetime import datetime
        
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        print(f"🔧 update_contract_tool: Created fresh database session")
        print(f"🔧 update_contract_tool: Database session info - is_active: {db.is_active}")
        
        # Test database connection
        try:
            db.execute("SELECT 1")
            print(f"🔧 update_contract_tool: Database connection test successful")
        except Exception as conn_error:
            print(f"🔧 update_contract_tool: Database connection test failed: {conn_error}")
            return ContractToolResult(
                success=False,
                message=f"❌ Database connection failed: {str(conn_error)}"
            )
        
        # Extract user_id from context
        if not context or 'user_id' not in context:
            return ContractToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        
        # Find client by name
        client = get_client_by_name(params.client_name, db)
        if not client:
            return ContractToolResult(
                success=False,
                message=f"❌ Client '{params.client_name}' not found."
            )
        
        # Find the contract to update
        contract = None
        if params.contract_id:
            # Use specific contract ID
            contract = db.query(Contract).filter(
                Contract.contract_id == params.contract_id,
                Contract.client_id == client.client_id
            ).first()
        else:
            # Get the most recent contract for this client
            contract = db.query(Contract).filter(
                Contract.client_id == client.client_id
            ).order_by(Contract.created_at.desc()).first()
        
        if not contract:
            return ContractToolResult(
                success=False,
                message=f"❌ No contracts found for client '{client.client_name}'."
            )
        
        # Update contract fields
        update_fields = []
        if params.start_date:
            try:
                contract.start_date = datetime.strptime(params.start_date, "%Y-%m-%d").date()
                update_fields.append("start_date")
            except ValueError:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Invalid start date format. Please use YYYY-MM-DD format."
                )
        
        if params.end_date:
            try:
                contract.end_date = datetime.strptime(params.end_date, "%Y-%m-%d").date()
                update_fields.append("end_date")
            except ValueError:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Invalid end date format. Please use YYYY-MM-DD format."
                )
        
        if params.contract_type:
            contract.contract_type = params.contract_type
            update_fields.append("contract_type")
        
        if params.original_amount is not None:
            contract.original_amount = params.original_amount
            update_fields.append("original_amount")
        
        if params.billing_frequency:
            print(f"🔧 update_contract_tool: Setting billing_frequency from '{contract.billing_frequency}' to '{params.billing_frequency}'")
            contract.billing_frequency = params.billing_frequency
            update_fields.append("billing_frequency")
        
        if params.status:
            contract.status = params.status
            update_fields.append("status")
        
        if params.notes:
            contract.notes = params.notes
            update_fields.append("notes")
        
        # Set audit fields
        contract.updated_by = user_id
        contract.updated_at = datetime.utcnow()
        
        print(f"🔧 update_contract_tool: About to commit changes. Update fields: {update_fields}")
        print(f"🔧 update_contract_tool: Contract billing_frequency before commit: {contract.billing_frequency}")
        print(f"🔧 update_contract_tool: Database session info - is_active: {db.is_active}, is_modified: {db.is_modified(contract)}")
        
        # Commit changes
        try:
            print(f"🔧 update_contract_tool: About to commit. Session info - is_active: {db.is_active}")
            db.commit()
            print(f"🔧 update_contract_tool: Changes committed successfully")
        except Exception as commit_error:
            print(f"🔧 update_contract_tool: Commit failed: {commit_error}")
            print(f"🔧 update_contract_tool: Commit error type: {type(commit_error)}")
            import traceback
            traceback.print_exc()
            try:
                db.rollback()
                print(f"🔧 update_contract_tool: Rollback successful")
            except Exception as rollback_error:
                print(f"🔧 update_contract_tool: Rollback failed: {rollback_error}")
            raise commit_error
        
        db.refresh(contract)
        print(f"🔧 update_contract_tool: Contract refreshed. billing_frequency after refresh: {contract.billing_frequency}")
        
        # Verify the change is visible in the current session
        verification_contract = db.query(Contract).filter(Contract.contract_id == contract.contract_id).first()
        print(f"🔧 update_contract_tool: Verification query - billing_frequency: {verification_contract.billing_frequency if verification_contract else 'None'}")
        
        return ContractToolResult(
            success=True,
            message=f"✅ Successfully updated contract for '{client.client_name}'. Updated fields: {', '.join(update_fields)}",
            data={
                "contract_id": contract.contract_id,
                "client_name": client.client_name,
                "updated_fields": update_fields,
                "start_date": str(contract.start_date) if contract.start_date else None,
                "end_date": str(contract.end_date) if contract.end_date else None,
                "contract_type": contract.contract_type,
                "status": contract.status
            }
        )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to update contract: {str(e)}"
        )
