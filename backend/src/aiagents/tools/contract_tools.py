from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Client, Contract, ClientContact
from backend.src.database.core.schemas import ClientCreate, ContractCreate, ClientContactCreate
from backend.src.database.api.clients import create_client, get_client_by_name
from backend.src.database.api.contracts import create_contract
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

def create_client_tool(params: CreateClientParams, db: Session = None) -> ContractToolResult:
    """Tool for creating new clients"""
    try:
        if db is None:
            db = next(get_db())
        
        client_data = ClientCreate(**params.dict())
        result = create_client(client_data, db)
        
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

def smart_create_contract_tool(params: SmartContractParams, db: Session = None) -> ContractToolResult:
    """Smart tool for creating contracts by client name instead of client_id"""
    try:
        if db is None:
            db = next(get_db())
        
        # Search for clients that match the client name - more precise matching
        matching_clients = []
        
        all_clients = db.query(Client).all()
        for client in all_clients:
            client_name_lower = client.client_name.lower()
            search_name_lower = params.client_name.lower()
            
            # Exact match first
            if client_name_lower == search_name_lower:
                matching_clients = [client]  # Exact match takes priority
                break
            
            # Partial match - but more restrictive
            # Only match if the search term is a significant part of the client name
            if (search_name_lower in client_name_lower or 
                client_name_lower in search_name_lower or
                # Check if major words match (length > 3 to avoid matching short words like "Inc")
                any(word in client_name_lower for word in search_name_lower.split() if len(word) > 3)):
                matching_clients.append(client)
        
        if len(matching_clients) == 0:
            # Client not found - automatically create new client
            # Extract any industry information from the contract context
            industry = None
            if "tech" in params.client_name.lower():
                industry = "Technology"
            elif "corp" in params.client_name.lower():
                industry = "Corporate"
            elif "inc" in params.client_name.lower():
                industry = "Business Services"
            
            # Create new client automatically
            try:
                client_data = CreateClientParams(
                    client_name=params.client_name,
                    industry=industry,
                    notes=f"Auto-created during contract creation for {params.contract_type} contract"
                )
                
                client_result = create_client_tool(client_data, db)
                
                if not client_result.success:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Failed to create new client '{params.client_name}': {client_result.message}"
                    )
                
                # Use the newly created client
                new_client_id = client_result.data["client_id"]
                client_name = client_result.data["client_name"]
                
                # Continue with contract creation using the new client
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
                    client_id=new_client_id,
                    contract_type=params.contract_type,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    original_amount=params.original_amount,
                    current_amount=params.original_amount,
                    billing_frequency=params.billing_frequency,
                    status="draft",
                    notes=params.notes
                )
                
                contract_result = create_contract(contract_data, db)
                
                return ContractToolResult(
                    success=True,
                    message=f"✅ New client '{client_name}' created and contract created successfully (Contract ID: {contract_result.contract_id}). Note: Please update client details like contact information and industry if needed.",
                    data={
                        "contract_id": contract_result.contract_id,
                        "client_id": new_client_id,
                        "client_name": client_name,
                        "contract_type": contract_result.contract_type,
                        "status": contract_result.status,
                        "original_amount": float(contract_result.original_amount) if contract_result.original_amount else None,
                        "new_client_created": True
                    }
                )
                
            except Exception as e:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Failed to create client and contract: {str(e)}"
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
        
        result = create_contract(contract_data, db)
        
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
