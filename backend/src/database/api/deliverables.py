from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.core.database import get_db
from src.database.core.models import Deliverable, Client, Contract
from src.database.core.schemas import DeliverableCreate, DeliverableUpdate, DeliverableResponse
from src.auth.dependencies import get_current_user, AuthenticatedUser

router = APIRouter()

@router.post("/", response_model=DeliverableResponse)
def create_deliverable(
    deliverable: DeliverableCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new deliverable"""
    # Verify contract exists
    contract = db.query(Contract).filter(Contract.contract_id == deliverable.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db_deliverable = Deliverable(
        **deliverable.model_dump(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_deliverable)
    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable

def create_deliverable_internal(deliverable: DeliverableCreate, db: Session, user_id: str) -> Deliverable:
    """Internal function to create deliverable (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    # Verify contract exists
    contract = db.query(Contract).filter(Contract.contract_id == deliverable.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db_deliverable = Deliverable(
        **deliverable.model_dump(),
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_deliverable)
    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable

@router.get("/", response_model=List[DeliverableResponse])
def get_deliverables(db: Session = Depends(get_db)):
    """Get all deliverables"""
    return db.query(Deliverable).all()

@router.get("/contract/{contract_id}", response_model=List[DeliverableResponse])
def get_deliverables_by_contract(contract_id: int, db: Session = Depends(get_db)):
    """Get all deliverables for a specific contract"""
    return db.query(Deliverable).filter(Deliverable.contract_id == contract_id).all()

@router.get("/search/{search_term}", response_model=List[DeliverableResponse])
def search_deliverables(search_term: str, db: Session = Depends(get_db)):
    """Search deliverables by name or description"""
    return db.query(Deliverable).filter(
        Deliverable.name.ilike(f"%{search_term}%") |
        Deliverable.description.ilike(f"%{search_term}%")
    ).all()

def get_deliverable_by_name(deliverable_name: str, db: Session) -> Deliverable:
    """Helper function to get deliverable by name (for use in tools) - with intelligent client name matching"""
    from  src.database.core.models import Client, Contract
    
    # First try direct deliverable name match
    deliverable = db.query(Deliverable).filter(Deliverable.name.ilike(f"%{deliverable_name}%")).first()
    if deliverable:
        return deliverable
    
    # If no direct match, try searching by client name
    # This handles cases like "Solana project" matching "Solana Inc" client
    search_words = deliverable_name.lower().split()
    
    deliverables = db.query(Deliverable).join(Contract).join(Client).all()
    
    for deliverable in deliverables:
        client_name = deliverable.contract.client.client_name.lower()
        deliverable_name_lower = (deliverable.name or "").lower()
        
        # Check if any search word matches client name or deliverable name
        for word in search_words:
            if (word in client_name or 
                word in deliverable_name_lower or
                # Check if client name contains the search word (e.g., "Solana" matches "Solana Inc")
                any(word in client_word for client_word in client_name.split())):
                return deliverable
    
    return None

def search_deliverables_with_client_info(search_term: str, db: Session) -> List[dict]:
    """Helper function to search deliverables with client and contract information"""
    from  src.database.core.models import Client, Contract
    
    # More flexible search - split search term into words for better matching
    search_words = search_term.lower().split()
    
    deliverables = db.query(Deliverable).join(Contract).join(Client).all()
    
    result = []
    for deliverable in deliverables:
        # Check if any search word matches client name, deliverable name, or description
        client_name = deliverable.contract.client.client_name.lower()
        deliverable_name = (deliverable.name or "").lower()
        deliverable_desc = (deliverable.description or "").lower()
        
        # More intelligent matching
        match_found = False
        for word in search_words:
            if (word in client_name or 
                word in deliverable_name or 
                word in deliverable_desc or
                # Check if client name contains the search word (e.g., "Solana" matches "Solana Inc")
                any(word in client_word for client_word in client_name.split())):
                match_found = True
                break
        
        if match_found:
            result.append({
                "deliverable_id": deliverable.deliverable_id,
                "name": deliverable.name,
                "description": deliverable.description,
                "contract_id": deliverable.contract_id,
                "client_id": deliverable.contract.client_id,
                "client_name": deliverable.contract.client.client_name,
                "status": deliverable.status,
                "due_date": deliverable.due_date,
                "billing_basis": deliverable.billing_basis
            })
    
    return result

@router.get("/{deliverable_id}", response_model=DeliverableResponse)
def get_deliverable(deliverable_id: int, db: Session = Depends(get_db)):
    """Get a specific deliverable"""
    deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return deliverable

@router.put("/{deliverable_id}", response_model=DeliverableResponse)
def update_deliverable(
    deliverable_id: int,
    deliverable_update: DeliverableUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a deliverable"""
    db_deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()
    if not db_deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    for field, value in deliverable_update.model_dump(exclude_unset=True).items():
        setattr(db_deliverable, field, value)
    
    # Set updated_by to current user
    db_deliverable.updated_by = current_user.user_id
    
    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable

@router.delete("/{deliverable_id}")
def delete_deliverable(
    deliverable_id: int, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a deliverable"""
    db_deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()
    if not db_deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    db.delete(db_deliverable)
    db.commit()
    return {"message": "Deliverable deleted successfully"}
