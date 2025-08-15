from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Deliverable, Contract
from backend.src.database.core.schemas import DeliverableCreate, DeliverableUpdate, DeliverableResponse

router = APIRouter()

@router.post("/", response_model=DeliverableResponse)
def create_deliverable(
    deliverable: DeliverableCreate,
    db: Session = Depends(get_db)
):
    """Create a new deliverable"""
    # Verify contract exists
    contract = db.query(Contract).filter(Contract.contract_id == deliverable.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db_deliverable = Deliverable(
        **deliverable.model_dump(),
        created_by="00000000-0000-0000-0000-000000000000",
        updated_by="00000000-0000-0000-0000-000000000000"
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
    db: Session = Depends(get_db)
):
    """Update a deliverable"""
    db_deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()
    if not db_deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    for field, value in deliverable_update.dict(exclude_unset=True).items():
        setattr(db_deliverable, field, value)
    
    db_deliverable.updated_by = "00000000-0000-0000-0000-000000000000"
    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable

@router.delete("/{deliverable_id}")
def delete_deliverable(deliverable_id: int, db: Session = Depends(get_db)):
    """Delete a deliverable"""
    db_deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()
    if not db_deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    db.delete(db_deliverable)
    db.commit()
    return {"message": "Deliverable deleted successfully"}