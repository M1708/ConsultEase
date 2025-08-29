from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.core.database import get_db
from src.database.core.models import Client, Contract
from src.database.core.schemas import ClientCreate, ClientResponse, ClientWithContracts, ContractResponse
from src.auth.dependencies import get_current_user, AuthenticatedUser

router = APIRouter()

@router.post("/", response_model=ClientResponse)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new client"""
    db_client = Client(
        **client.model_dump(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/", response_model=List[ClientResponse])
def get_clients(db: Session = Depends(get_db)):
    """Get all clients"""
    return db.query(Client).all()

@router.get("/search/{search_term}", response_model=List[ClientResponse])
def search_clients_by_name(search_term: str, db: Session = Depends(get_db)):
    """Search clients by name or industry"""
    return db.query(Client).filter(
        Client.client_name.ilike(f"%{search_term}%") |
        Client.industry.ilike(f"%{search_term}%")
    ).all()

def get_client_by_name(client_name: str, db: Session) -> Client:
    """Helper function to get client by name (for use in tools)"""
    return db.query(Client).filter(Client.client_name.ilike(f"%{client_name}%")).first()

def create_client_internal(client: ClientCreate, db: Session, user_id: str) -> Client:
    """Internal function to create client (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    db_client = Client(
        **client.model_dump(),
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/{client_id}", response_model=ClientWithContracts)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a specific client with their contracts"""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_update: ClientCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a client"""
    db_client = db.query(Client).filter(Client.client_id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update fields
    for field, value in client_update.model_dump(exclude_unset=True).items():
        setattr(db_client, field, value)
    
    # Set updated_by to current user
    db_client.updated_by = current_user.user_id
    
    db.commit()
    db.refresh(db_client)
    return db_client

@router.delete("/{client_id}")
def delete_client(
    client_id: int, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a client"""
    db_client = db.query(Client).filter(Client.client_id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(db_client)
    db.commit()
    return {"message": "Client deleted successfully"}
