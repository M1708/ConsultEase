from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Client, Contract, Deliverable
from backend.src.database.core.schemas import DeliverableCreate
from backend.src.database.api.clients import get_client_by_name
from backend.src.database.api.deliverables import create_deliverable

class DeliverableToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False

class SmartDeliverableParams(BaseModel):
    client_name: str
    deliverable_name: str
    description: Optional[str] = None
    contract_id: Optional[int] = None  # If not provided, will find latest contract for client
    due_date: Optional[str] = None  # YYYY-MM-DD format
    billing_basis: Optional[str] = "Fixed"  # "Fixed", "Hourly", "Milestone"
    assigned_employees: Optional[int] = 1  # Default to 1 employee
    assigned_employee_name: Optional[str] = None
    billing_amount: Optional[Decimal] = None

def smart_create_deliverable_tool(params: SmartDeliverableParams, db: Session = None) -> DeliverableToolResult:
    """Smart tool for creating deliverables by client name and contract reference"""
    try:
        if db is None:
            db = next(get_db())
        
        contract = None
        
        if params.contract_id:
            # Use specific contract ID
            contract = db.query(Contract).filter(Contract.contract_id == params.contract_id).first()
            if not contract:
                return DeliverableToolResult(
                    success=False,
                    message=f"❌ Contract with ID {params.contract_id} not found."
                )
        else:
            # Find client and their latest active contract
            # Search for clients that match the client name
            matching_clients = []
            
            all_clients = db.query(Client).all()
            for client in all_clients:
                client_name_lower = client.client_name.lower()
                search_name_lower = params.client_name.lower()
                
                # Exact match first
                if client_name_lower == search_name_lower:
                    matching_clients = [client]
                    break
                
                # Partial match
                if (search_name_lower in client_name_lower or 
                    client_name_lower in search_name_lower or
                    any(word in client_name_lower for word in search_name_lower.split() if len(word) > 3)):
                    matching_clients.append(client)
            
            if len(matching_clients) == 0:
                return DeliverableToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found. Please create the client and contract first."
                )
            
            elif len(matching_clients) > 1:
                # Multiple clients found - ask user to clarify
                client_options = []
                for i, client in enumerate(matching_clients, 1):
                    # Count contracts for each client
                    contract_count = db.query(Contract).filter(Contract.client_id == client.client_id).count()
                    client_info = f"{i}. **{client.client_name}**"
                    if client.industry:
                        client_info += f" (Industry: {client.industry})"
                    client_info += f" - {contract_count} contract(s)"
                    client_options.append(client_info)
                
                return DeliverableToolResult(
                    success=False,
                    message=f"🔍 Found multiple clients matching '{params.client_name}'. Please specify which client you meant:\n\n" + 
                           "\n".join(client_options) + 
                           f"\n\nPlease rephrase your request with the full client name (e.g., 'Add deliverable \"{params.deliverable_name}\" for [Full Client Name]')."
                )
            
            # Single client found
            client = matching_clients[0]
            
            # Get the most recent active contract for this client
            contract = db.query(Contract).filter(
                Contract.client_id == client.client_id,
                Contract.status.in_(["draft", "active"])
            ).order_by(Contract.created_at.desc()).first()
            
            if not contract:
                # Check if client has any contracts at all
                any_contract = db.query(Contract).filter(Contract.client_id == client.client_id).first()
                if any_contract:
                    return DeliverableToolResult(
                        success=False,
                        message=f"❌ Client '{client.client_name}' has contracts but none are active. Please activate a contract or create a new one first."
                    )
                else:
                    return DeliverableToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{client.client_name}'. Please create a contract first before adding deliverables."
                    )
        
        # Parse due date
        due_date_obj = None
        if params.due_date:
            try:
                due_date_obj = date.fromisoformat(params.due_date)
            except ValueError:
                pass
        
        # Create deliverable using the existing API
        deliverable_data = DeliverableCreate(
            contract_id=contract.contract_id,
            name=params.deliverable_name,
            description=params.description,
            assigned_employees=params.assigned_employees or 1,
            due_date=due_date_obj,
            billing_basis=params.billing_basis,
            billing_amount=params.billing_amount,
            assigned_employee_name=params.assigned_employee_name,
            status="Not Started"
        )
        
        result = create_deliverable(deliverable_data, db)
        
        return DeliverableToolResult(
            success=True,
            message=f"✅ Deliverable '{params.deliverable_name}' created successfully for client '{contract.client.client_name}' (Contract ID: {contract.contract_id}, Deliverable ID: {result.deliverable_id})",
            data={
                "deliverable_id": result.deliverable_id,
                "deliverable_name": result.name,
                "contract_id": contract.contract_id,
                "client_id": contract.client_id,
                "client_name": contract.client.client_name,
                "contract_type": contract.contract_type,
                "billing_basis": result.billing_basis,
                "status": result.status,
                "due_date": str(result.due_date) if result.due_date else None,
                "assigned_employees": result.assigned_employees,
                "billing_amount": float(result.billing_amount) if result.billing_amount else None
            }
        )
        
    except Exception as e:
        return DeliverableToolResult(
            success=False,
            message=f"❌ Failed to create deliverable: {str(e)}"
        )

def get_deliverables_by_client_tool(client_name: str, db: Session = None) -> DeliverableToolResult:
    """Tool for getting all deliverables for a specific client by name"""
    try:
        if db is None:
            db = next(get_db())
        
        # Find client by name using the same smart matching
        matching_clients = []
        
        all_clients = db.query(Client).all()
        for client in all_clients:
            client_name_lower = client.client_name.lower()
            search_name_lower = client_name.lower()
            
            # Exact match first
            if client_name_lower == search_name_lower:
                matching_clients = [client]
                break
            
            # Partial match
            if (search_name_lower in client_name_lower or 
                client_name_lower in search_name_lower or
                any(word in client_name_lower for word in search_name_lower.split() if len(word) > 3)):
                matching_clients.append(client)
        
        if len(matching_clients) == 0:
            return DeliverableToolResult(
                success=False,
                message=f"❌ Client '{client_name}' not found."
            )
        
        elif len(matching_clients) > 1:
            client_options = []
            for i, client in enumerate(matching_clients, 1):
                deliverable_count = db.query(Deliverable).join(Contract).filter(Contract.client_id == client.client_id).count()
                client_info = f"{i}. **{client.client_name}**"
                if client.industry:
                    client_info += f" (Industry: {client.industry})"
                client_info += f" - {deliverable_count} deliverable(s)"
                client_options.append(client_info)
            
            return DeliverableToolResult(
                success=False,
                message=f"🔍 Found multiple clients matching '{client_name}'. Please specify which client you meant:\n\n" + 
                       "\n".join(client_options)
            )
        
        # Single client found
        client = matching_clients[0]
        
        # Get all deliverables for this client across all contracts
        deliverables = db.query(Deliverable).join(Contract).filter(Contract.client_id == client.client_id).all()
        
        deliverable_list = []
        for deliverable in deliverables:
            deliverable_list.append({
                "deliverable_id": deliverable.deliverable_id,
                "name": deliverable.name,
                "description": deliverable.description,
                "contract_id": deliverable.contract_id,
                "contract_type": deliverable.contract.contract_type,
                "status": deliverable.status,
                "billing_basis": deliverable.billing_basis,
                "due_date": str(deliverable.due_date) if deliverable.due_date else None,
                "assigned_employees": deliverable.assigned_employees,
                "billing_amount": float(deliverable.billing_amount) if deliverable.billing_amount else None
            })
        
        return DeliverableToolResult(
            success=True,
            message=f"📋 Found {len(deliverable_list)} deliverables for client '{client.client_name}'",
            data={
                "client_name": client.client_name,
                "deliverables": deliverable_list,
                "count": len(deliverable_list)
            }
        )
        
    except Exception as e:
        return DeliverableToolResult(
            success=False,
            message=f"❌ Failed to get deliverables: {str(e)}"
        )

def get_deliverables_by_contract_tool(client_name: str, contract_id: Optional[int] = None, db: Session = None) -> DeliverableToolResult:
    """Tool for getting deliverables for a specific contract by client name and optional contract ID"""
    try:
        if db is None:
            db = next(get_db())
        
        contract = None
        
        if contract_id:
            # Use specific contract ID
            contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
            if not contract:
                return DeliverableToolResult(
                    success=False,
                    message=f"❌ Contract with ID {contract_id} not found."
                )
        else:
            # Find client and their latest contract
            client = get_client_by_name(client_name, db)
            if not client:
                return DeliverableToolResult(
                    success=False,
                    message=f"❌ Client '{client_name}' not found."
                )
            
            # Get the most recent contract for this client
            contract = db.query(Contract).filter(
                Contract.client_id == client.client_id
            ).order_by(Contract.created_at.desc()).first()
            
            if not contract:
                return DeliverableToolResult(
                    success=False,
                    message=f"❌ No contracts found for client '{client.client_name}'."
                )
        
        # Get all deliverables for this specific contract
        deliverables = db.query(Deliverable).filter(Deliverable.contract_id == contract.contract_id).all()
        
        deliverable_list = []
        for deliverable in deliverables:
            deliverable_list.append({
                "deliverable_id": deliverable.deliverable_id,
                "name": deliverable.name,
                "description": deliverable.description,
                "status": deliverable.status,
                "billing_basis": deliverable.billing_basis,
                "due_date": str(deliverable.due_date) if deliverable.due_date else None,
                "assigned_employees": deliverable.assigned_employees,
                "billing_amount": float(deliverable.billing_amount) if deliverable.billing_amount else None
            })
        
        return DeliverableToolResult(
            success=True,
            message=f"📋 Found {len(deliverable_list)} deliverables for contract {contract.contract_id} (Client: {contract.client.client_name})",
            data={
                "contract_id": contract.contract_id,
                "client_name": contract.client.client_name,
                "contract_type": contract.contract_type,
                "deliverables": deliverable_list,
                "count": len(deliverable_list)
            }
        )
        
    except Exception as e:
        return DeliverableToolResult(
            success=False,
            message=f"❌ Failed to get contract deliverables: {str(e)}"
        )

def search_deliverables_tool(search_term: str, db: Session = None) -> DeliverableToolResult:
    """Tool for searching deliverables by name, description, or client name"""
    try:
        if db is None:
            db = next(get_db())
        
        # Use the existing API function for smart search
        from backend.src.database.api.deliverables import search_deliverables_with_client_info
        
        deliverables = search_deliverables_with_client_info(search_term, db)
        
        # Convert date objects to strings to avoid JSON serialization issues
        for deliverable in deliverables:
            if deliverable.get('due_date') and hasattr(deliverable['due_date'], 'isoformat'):
                deliverable['due_date'] = deliverable['due_date'].isoformat()
        
        return DeliverableToolResult(
            success=True,
            message=f"🔍 Found {len(deliverables)} deliverables matching '{search_term}'",
            data={
                "deliverables": deliverables,
                "count": len(deliverables),
                "search_term": search_term
            }
        )
        
    except Exception as e:
        return DeliverableToolResult(
            success=False,
            message=f"❌ Failed to search deliverables: {str(e)}"
        )
