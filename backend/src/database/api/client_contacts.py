from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.src.database.core.database import get_db
from backend.src.database.core.models import ClientContact, Client
from backend.src.database.core.schemas import ClientContactCreate, ClientContactUpdate, ClientContactResponse

router = APIRouter()

@router.post("/", response_model=ClientContactResponse)
def create_client_contact(
    contact: ClientContactCreate,
    db: Session = Depends(get_db)
):
    """Create a new client contact"""
    # Verify client exists
    client = db.query(Client).filter(Client.client_id == contact.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Auto-populate client_name if not provided
    if not contact.client_name:
        contact.client_name = client.client_name
    
    db_contact = ClientContact(
        **contact.model_dump(),
        created_by="00000000-0000-0000-0000-000000000000",
        updated_by="00000000-0000-0000-0000-000000000000"
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.get("/", response_model=List[ClientContactResponse])
def get_client_contacts(db: Session = Depends(get_db)):
    """Get all client contacts"""
    return db.query(ClientContact).all()

@router.get("/client/{client_id}", response_model=List[ClientContactResponse])
def get_contacts_by_client(client_id: int, db: Session = Depends(get_db)):
    """Get all contacts for a specific client"""
    return db.query(ClientContact).filter(ClientContact.client_id == client_id).all()

@router.get("/{contact_id}", response_model=ClientContactResponse)
def get_client_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific client contact"""
    contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}", response_model=ClientContactResponse)
def update_client_contact(
    contact_id: int,
    contact_update: ClientContactUpdate,
    db: Session = Depends(get_db)
):
    """Update a client contact"""
    db_contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    for field, value in contact_update.dict(exclude_unset=True).items():
        setattr(db_contact, field, value)
    
    db_contact.updated_by = "00000000-0000-0000-0000-000000000000"
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.delete("/{contact_id}")
def delete_client_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a client contact"""
    db_contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db.delete(db_contact)
    db.commit()
    return {"message": "Contact deleted successfully"}