from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Employee, User
from backend.src.database.core.schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeSearch
from backend.src.auth.dependencies import get_current_user
from backend.src.auth.dependencies import AuthenticatedUser
from datetime import datetime

router = APIRouter(prefix="/employees", tags=["employees"])

def get_employee_by_id(employee_id: int, db: Session) -> Optional[Employee]:
    """Helper function to get employee by ID"""
    return db.query(Employee).filter(Employee.employee_id == employee_id).first()

def get_employee_by_number(employee_number: str, db: Session) -> Optional[Employee]:
    """Helper function to get employee by employee number"""
    return db.query(Employee).filter(Employee.employee_number == employee_number).first()

@router.post("/", response_model=EmployeeResponse)
async def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new employee record"""
    try:
        # Check if employee number already exists
        if employee.employee_number:
            existing_employee = get_employee_by_number(employee.employee_number, db)
            if existing_employee:
                raise HTTPException(status_code=400, detail="Employee number already exists")
        
        # Check if profile exists
        profile = db.query(User).filter(User.user_id == employee.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        db_employee = Employee(
            **employee.dict(),
            created_by=current_user.user_id,
            updated_by=current_user.user_id
        )
        
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        
        return db_employee
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create employee: {str(e)}")

@router.get("/", response_model=List[EmployeeResponse])
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    full_time_part_time: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all employees with optional filtering"""
    try:
        query = db.query(Employee)
        
        if department:
            query = query.filter(Employee.department.ilike(f"%{department}%"))
        if employment_type:
            query = query.filter(Employee.employment_type == employment_type)
        if full_time_part_time:
            query = query.filter(Employee.full_time_part_time == full_time_part_time)
        
        employees = query.offset(skip).limit(limit).all()
        return employees
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve employees: {str(e)}")

@router.get("/search", response_model=List[EmployeeResponse])
async def search_employees(
    search_term: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Search employees by name, job title, department, or employee number"""
    try:
        query = db.query(Employee).join(User, Employee.profile_id == User.user_id)
        
        # Search across multiple fields
        search_filter = (
            User.first_name.ilike(f"%{search_term}%") |
            User.last_name.ilike(f"%{search_term}%") |
            Employee.job_title.ilike(f"%{search_term}%") |
            Employee.department.ilike(f"%{search_term}%") |
            Employee.employee_number.ilike(f"%{search_term}%")
        )
        
        employees = query.filter(search_filter).limit(limit).all()
        return employees
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search employees: {str(e)}")

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get a specific employee by ID"""
    try:
        employee = get_employee_by_id(employee_id, db)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return employee
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve employee: {str(e)}")

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update an existing employee"""
    try:
        db_employee = get_employee_by_id(employee_id, db)
        if not db_employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check if employee number already exists (if being updated)
        if employee_update.employee_number and employee_update.employee_number != db_employee.employee_number:
            existing_employee = get_employee_by_number(employee_update.employee_number, db)
            if existing_employee:
                raise HTTPException(status_code=400, detail="Employee number already exists")
        
        # Update fields
        update_data = employee_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_employee, field, value)
        
        db_employee.updated_by = current_user.user_id
        db_employee.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_employee)
        
        return db_employee
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update employee: {str(e)}")

@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete an employee record"""
    try:
        db_employee = get_employee_by_id(employee_id, db)
        if not db_employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        db.delete(db_employee)
        db.commit()
        
        return {"message": "Employee deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete employee: {str(e)}")

@router.get("/department/{department}", response_model=List[EmployeeResponse])
async def get_employees_by_department(
    department: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all employees in a specific department"""
    try:
        employees = db.query(Employee).filter(Employee.department.ilike(f"%{department}%")).all()
        return employees
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve employees by department: {str(e)}")

@router.get("/employment-type/{employment_type}", response_model=List[EmployeeResponse])
async def get_employees_by_employment_type(
    employment_type: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all employees by employment type"""
    try:
        employees = db.query(Employee).filter(Employee.employment_type == employment_type).all()
        return employees
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve employees by employment type: {str(e)}")
