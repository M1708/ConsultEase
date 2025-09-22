from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from src.database.core.database import get_db
from src.database.core.models import Client, Contract
from src.database.core.schemas import ClientCreate, ClientResponse, ClientWithContracts, ContractResponse
from src.auth.dependencies import get_current_user, AuthenticatedUser

router = APIRouter()

@router.post("/", response_model=ClientResponse)
async def create_client(
    client: ClientCreate,
    db: AsyncSession = Depends(get_db),  # Change to async dependency
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new client"""
    db_client = Client(
        **client.model_dump(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)

@router.get("/", response_model=List[ClientResponse])
async def get_clients(db: AsyncSession = Depends(get_db)):
    """Get all clients"""
    result = await db.execute(select(Client))
    return result.scalars().all()   

@router.get("/search/{search_term}", response_model=List[ClientResponse])
async def search_clients_by_name(search_term: str, db: AsyncSession = Depends(get_db)):
    """Search clients by name or industry"""
    result = await db.execute(
        select(Client).filter(
            text("lower(client_name) LIKE lower(:search_term) OR lower(industry) LIKE lower(:search_term)")
            .params(search_term=f"%{search_term}%")
        )
    )
    return result.scalars().all()

async def get_client_by_name(client_name: str, session: AsyncSession) -> Client:
    """Helper function to get client by name (for use in tools)"""
    # First try exact match
    result = await session.execute(
        select(Client).filter(text("lower(client_name) = lower(:client_name)").params(client_name=client_name))
    )
    client = result.scalar_one_or_none()
    
    if client:
        return client
    
    # If no exact match, try case-insensitive partial match
    result = await session.execute(
        select(Client).filter(text("lower(client_name) LIKE lower(:client_name)").params(client_name=f"%{client_name}%"))
    )
    clients = result.scalars().all()
    
    if not clients:
        return None
    elif len(clients) == 1:
        return clients[0]
    else:
        # Multiple clients found - return the most recent one
        print(f"🔍 DEBUG: Multiple clients found for '{client_name}', returning most recent")
        return max(clients, key=lambda c: c.created_at or c.updated_at)

async def create_client_internal(client: ClientCreate, session: AsyncSession, user_id: str) -> Client:
    """Internal function to create client (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    db_client = Client(
        **client.model_dump(),
        created_by=user_id,
        updated_by=user_id
    )
    session.add(db_client)
    await session.commit()
    await session.refresh(db_client)
    return db_client

@router.get("/{client_id}", response_model=ClientWithContracts)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific client with their contracts"""
    result = await db.execute(select(Client).filter(Client.client_id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_update: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a client"""
    result = await db.execute(select(Client).filter(Client.client_id == client_id))
    db_client = result.scalar_one_or_none()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update fields
    for field, value in client_update.model_dump(exclude_unset=True).items():
        setattr(db_client, field, value)
    
    # Set updated_by to current user
    db_client.updated_by = current_user.user_id
    
    await db.commit()
    await db.refresh(db_client)
    return db_client

@router.delete("/{client_id}")
async def delete_client(
    client_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a client"""
    result = await db.execute(select(Client).filter(Client.client_id == client_id))
    db_client = result.scalar_one_or_none()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.delete(db_client)
    await db.commit()
    return {"message": "Client deleted successfully"}