from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import date
from src.database.core.database import get_db
from src.database.core.models import TimeEntry, Contract, Client
from src.database.core.schemas import TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse
from src.auth.dependencies import get_current_user, AuthenticatedUser

router = APIRouter()

@router.post("/", response_model=TimeEntryResponse)
def create_time_entry(
    time_entry: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new time entry"""
    # Verify related entities exist
    contract = db.query(Contract).filter(Contract.contract_id == time_entry.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    client = db.query(Client).filter(Client.client_id == time_entry.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_time_entry = TimeEntry(
        **time_entry.model_dump(),
        entered_by="system",
        entry_timestamp=func.now(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_time_entry)
    db.commit()
    db.refresh(db_time_entry)
    return db_time_entry

def create_time_entry_internal(time_entry: TimeEntryCreate, db: Session, user_id: str) -> TimeEntry:
    """Internal function to create time entry (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    # Verify related entities exist
    contract = db.query(Contract).filter(Contract.contract_id == time_entry.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    client = db.query(Client).filter(Client.client_id == time_entry.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_time_entry = TimeEntry(
        **time_entry.model_dump(),
        entered_by="system",
        entry_timestamp=func.now(),
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_time_entry)
    db.commit()
    db.refresh(db_time_entry)
    return db_time_entry

@router.get("/", response_model=List[TimeEntryResponse])
def get_time_entries(db: Session = Depends(get_db)):
    """Get all time entries"""
    return db.query(TimeEntry).all()

@router.get("/employee/{employee_id}", response_model=List[TimeEntryResponse])
def get_time_entries_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get all time entries for a specific employee"""
    return db.query(TimeEntry).filter(TimeEntry.employee_id == employee_id).all()

@router.get("/contract/{contract_id}", response_model=List[TimeEntryResponse])
def get_time_entries_by_contract(contract_id: int, db: Session = Depends(get_db)):
    """Get all time entries for a specific contract"""
    return db.query(TimeEntry).filter(TimeEntry.contract_id == contract_id).all()

@router.get("/date-range", response_model=List[TimeEntryResponse])
def get_time_entries_by_date_range(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Get time entries within a date range"""
    return db.query(TimeEntry).filter(
        TimeEntry.date >= start_date,
        TimeEntry.date <= end_date
    ).all()

@router.get("/{time_entry_id}", response_model=TimeEntryResponse)
def get_time_entry(time_entry_id: int, db: Session = Depends(get_db)):
    """Get a specific time entry"""
    time_entry = db.query(TimeEntry).filter(TimeEntry.time_entry_id == time_entry_id).first()
    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return time_entry

@router.put("/{time_entry_id}", response_model=TimeEntryResponse)
def update_time_entry(
    time_entry_id: int,
    time_entry_update: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a time entry"""
    db_time_entry = db.query(TimeEntry).filter(TimeEntry.time_entry_id == time_entry_id).first()
    if not db_time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    for field, value in time_entry_update.model_dump(exclude_unset=True).items():
        setattr(db_time_entry, field, value)
    
    db_time_entry.last_modified_by = current_user.user_id
    db_time_entry.last_modified_timestamp = func.now()
    # Set updated_by to current user
    db_time_entry.updated_by = current_user.user_id
    
    db.commit()
    db.refresh(db_time_entry)
    return db_time_entry

@router.delete("/{time_entry_id}")
def delete_time_entry(
    time_entry_id: int, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a time entry"""
    db_time_entry = db.query(TimeEntry).filter(TimeEntry.time_entry_id == time_entry_id).first()
    if not db_time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    db.delete(db_time_entry)
    db.commit()
    return {"message": "Time entry deleted successfully"}
