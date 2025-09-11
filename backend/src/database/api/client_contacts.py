from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.core.database import get_db
from src.database.core.models import ClientContact, Client
from src.database.core.schemas import ClientContactCreate, ClientContactUpdate, ClientContactResponse
from src.auth.dependencies import get_current_user, AuthenticatedUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


@router.post("/", response_model=ClientContactResponse)
async def create_client_contact(
    contact: ClientContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new client contact"""
    # Verify client exists
    result = await db.execute(select(Client).filter(Client.client_id == contact.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Auto-populate client_name if not provided
    if not contact.client_name:
        contact.client_name = client.client_name
    
    db_contact = ClientContact(
        **contact.model_dump(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

async def create_client_contact_internal(contact: ClientContactCreate, db: AsyncSession, user_id: str) -> ClientContact:
    """Internal function to create client contact (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    # Verify client exists
    result = await db.execute(select(Client).filter(Client.client_id == contact.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Auto-populate client_name if not provided
    if not contact.client_name:
        contact.client_name = client.client_name
    
    db_contact = ClientContact(
        **contact.model_dump(),
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@router.get("/", response_model=List[ClientContactResponse])
async def get_client_contacts(db: AsyncSession = Depends(get_db)):
    """Get all client contacts"""
    result = await db.execute(select(ClientContact))
    return result.scalars().all()

@router.get("/client/{client_id}", response_model=List[ClientContactResponse])
async def get_contacts_by_client(
    client_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Get all contacts for a specific client"""
    result = await db.execute(select(ClientContact).filter(ClientContact.client_id == client_id))
    return result.scalars().all()

@router.get("/{contact_id}", response_model=ClientContactResponse)
async def get_client_contact(
    contact_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Get a specific client contact"""
    result = await db.execute(select(ClientContact).filter(ClientContact.contact_id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}", response_model=ClientContactResponse)
async def update_client_contact(
    contact_id: int,
    contact_update: ClientContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a client contact"""
    result = await db.execute(select(ClientContact).filter(ClientContact.contact_id == contact_id))
    db_contact = result.scalar_one_or_none()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    for field, value in contact_update.model_dump(exclude_unset=True).items():
        setattr(db_contact, field, value)
    
    # Set updated_by to current user
    db_contact.updated_by = current_user.user_id
    
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@router.delete("/{contact_id}")
async def delete_client_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a client contact"""
    result = await db.execute(select(ClientContact).filter(ClientContact.contact_id == contact_id))
    db_contact = result.scalar_one_or_none()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    await db.delete(db_contact)
    await db.commit()
    return {"message": "Contact deleted successfully"}

# @router.post("/", response_model=ClientContactResponse)
# def create_client_contact(
#     contact: ClientContactCreate,
#     db: Session = Depends(get_db),
#     current_user: AuthenticatedUser = Depends(get_current_user)
# ):
#     """Create a new client contact"""
#     # Verify client exists
#     client = db.query(Client).filter(Client.client_id == contact.client_id).first()
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
    
#     # Auto-populate client_name if not provided
#     if not contact.client_name:
#         contact.client_name = client.client_name
    
#     db_contact = ClientContact(
#         **contact.model_dump(),
#         created_by=current_user.user_id,
#         updated_by=current_user.user_id
#     )
#     db.add(db_contact)
#     db.commit()
#     db.refresh(db_contact)
#     return db_contact

# def create_client_contact_internal(contact: ClientContactCreate, db: Session, user_id: str) -> ClientContact:
#     """Internal function to create client contact (for use by AI agents and tools)"""
#     # AI agents must provide the actual user_id from the authenticated session
#     if not user_id:
#         raise ValueError("user_id is required for AI agent operations")
    
#     # Verify client exists
#     client = db.query(Client).filter(Client.client_id == contact.client_id).first()
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
    
#     # Auto-populate client_name if not provided
#     if not contact.client_name:
#         contact.client_name = client.client_name
    
#     db_contact = ClientContact(
#         **contact.model_dump(),
#         created_by=user_id,
#         updated_by=user_id
#     )
#     db.add(db_contact)
#     db.commit()
#     db.refresh(db_contact)
#     return db_contact

# @router.get("/", response_model=List[ClientContactResponse])
# def get_client_contacts(db: Session = Depends(get_db)):
#     """Get all client contacts"""
#     return db.query(ClientContact).all()

# @router.get("/client/{client_id}", response_model=List[ClientContactResponse])
# def get_contacts_by_client(client_id: int, db: Session = Depends(get_db)):
#     """Get all contacts for a specific client"""
#     return db.query(ClientContact).filter(ClientContact.client_id == client_id).all()

# @router.get("/{contact_id}", response_model=ClientContactResponse)
# def get_client_contact(contact_id: int, db: Session = Depends(get_db)):
#     """Get a specific client contact"""
#     contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
#     if not contact:
#         raise HTTPException(status_code=404, detail="Contact not found")
#     return contact

# @router.put("/{contact_id}", response_model=ClientContactResponse)
# def update_client_contact(
#     contact_id: int,
#     contact_update: ClientContactUpdate,
#     db: Session = Depends(get_db),
#     current_user: AuthenticatedUser = Depends(get_current_user)
# ):
#     """Update a client contact"""
#     db_contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
#     if not db_contact:
#         raise HTTPException(status_code=404, detail="Contact not found")
    
#     for field, value in contact_update.model_dump(exclude_unset=True).items():
#         setattr(db_contact, field, value)
    
#     # Set updated_by to current user
#     db_contact.updated_by = current_user.user_id
    
#     db.commit()
#     db.refresh(db_contact)
#     return db_contact

# @router.delete("/{contact_id}")
# def delete_client_contact(
#     contact_id: int, 
#     db: Session = Depends(get_db),
#     current_user: AuthenticatedUser = Depends(get_current_user)
# ):
#     """Delete a client contact"""
#     db_contact = db.query(ClientContact).filter(ClientContact.contact_id == contact_id).first()
#     if not db_contact:
#         raise HTTPException(status_code=404, detail="Contact not found")
    
#     db.delete(db_contact)
#     db.commit()
#     return {"message": "Contact deleted successfully"}
