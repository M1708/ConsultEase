from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import date
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Expense, Client
from backend.src.database.core.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse

router = APIRouter()

@router.post("/", response_model=ExpenseResponse)
def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db)
):
    """Create a new expense"""
    # Verify client exists
    client = db.query(Client).filter(Client.client_id == expense.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_expense = Expense(
        **expense.model_dump(),
        entered_by="system",
        entry_timestamp=func.now(),
        created_by="00000000-0000-0000-0000-000000000000",
        updated_by="00000000-0000-0000-0000-000000000000"
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.get("/", response_model=List[ExpenseResponse])
def get_expenses(db: Session = Depends(get_db)):
    """Get all expenses"""
    return db.query(Expense).all()

@router.get("/employee/{employee_id}", response_model=List[ExpenseResponse])
def get_expenses_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get all expenses for a specific employee"""
    return db.query(Expense).filter(Expense.employee_id == employee_id).all()

@router.get("/client/{client_id}", response_model=List[ExpenseResponse])
def get_expenses_by_client(client_id: int, db: Session = Depends(get_db)):
    """Get all expenses for a specific client"""
    return db.query(Expense).filter(Expense.client_id == client_id).all()

@router.get("/date-range", response_model=List[ExpenseResponse])
def get_expenses_by_date_range(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Get expenses within a date range"""
    return db.query(Expense).filter(
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    """Get a specific expense"""
    expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db)
):
    """Update an expense"""
    db_expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for field, value in expense_update.dict(exclude_unset=True).items():
        setattr(db_expense, field, value)
    
    db_expense.last_modified_by = "system"
    db_expense.last_modified_timestamp = func.now()
    db_expense.updated_by = "00000000-0000-0000-0000-000000000000"
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete an expense"""
    db_expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(db_expense)
    db.commit()
    return {"message": "Expense deleted successfully"}