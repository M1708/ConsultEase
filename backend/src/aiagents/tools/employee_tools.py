from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database.core.database import get_db
from src.database.core.models import Employee, User
from src.database.core.schemas import EmployeeCreate, EmployeeUpdate
from datetime import datetime, date
from decimal import Decimal

class EmployeeToolResult:
    """Result object for employee tool operations"""
    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data

class CreateEmployeeParams(BaseModel):
    profile_id: str
    employee_number: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    employment_type: str  # permanent, contract, intern, consultant
    full_time_part_time: str  # full_time, part_time
    committed_hours: Optional[int] = None
    hire_date: Optional[str] = None  # YYYY-MM-DD format, defaults to today
    termination_date: Optional[str] = None
    rate_type: Optional[str] = None  # hourly, salary, project_based
    rate: Optional[float] = None
    currency: str = "USD"
    nda_file_link: Optional[str] = None
    contract_file_link: Optional[str] = None

class UpdateEmployeeParams(BaseModel):
    employee_id: Optional[int] = None
    employee_number: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    full_time_part_time: Optional[str] = None
    committed_hours: Optional[int] = None
    hire_date: Optional[str] = None
    termination_date: Optional[str] = None
    rate_type: Optional[str] = None
    rate: Optional[float] = None
    currency: Optional[str] = None
    nda_file_link: Optional[str] = None
    contract_file_link: Optional[str] = None

def check_employee_exists_tool(profile_id: str, db: Session = None) -> EmployeeToolResult:
    """Tool for checking if an employee record already exists for a given profile"""
    try:
        if db is None:
            db = next(get_db())
        
        # Check if employee record exists
        existing_employee = db.query(Employee).filter(Employee.profile_id == profile_id).first()
        
        if existing_employee:
            # Get profile information
            profile = db.query(User).filter(User.user_id == profile_id).first()
            profile_name = f"{profile.first_name} {profile.last_name}" if profile and profile.first_name and profile.last_name else "Unknown"
            
            return EmployeeToolResult(
                success=True,
                message=f"✅ Employee record found for {profile_name}",
                data={
                    "exists": True,
                    "employee": {
                        "employee_id": existing_employee.employee_id,
                        "profile_id": str(existing_employee.profile_id),
                        "profile_name": profile_name,
                        "job_title": existing_employee.job_title,
                        "department": existing_employee.department,
                        "employment_type": existing_employee.employment_type,
                        "full_time_part_time": existing_employee.full_time_part_time,
                        "hire_date": str(existing_employee.hire_date) if existing_employee.hire_date else None,
                        "status": "Active"
                    }
                }
            )
        else:
            return EmployeeToolResult(
                success=True,
                message="✅ No employee record found for this profile",
                data={
                    "exists": False,
                    "employee": None
                }
            )
        
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to check employee existence: {str(e)}"
        )
    finally:
        if db:
            db.close()

def search_profiles_by_name_tool(search_name: str, db: Session = None) -> EmployeeToolResult:
    """Tool for searching user profiles by name to find profile_id for employee creation"""
    try:
        if db is None:
            db = next(get_db())
        
        # Clean and extract the actual name from the search string
        # Remove common prefixes and suffixes that might be in the message
        cleaned_name = search_name.strip()
        
        # Remove common prefixes like "Create an employee record for"
        prefixes_to_remove = [
            "create an employee record for",
            "create employee record for",
            "add employee record for",
            "new employee record for",
            "hire",
            "onboard"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned_name.lower().startswith(prefix.lower()):
                cleaned_name = cleaned_name[len(prefix):].strip()
                break
        
        # Remove common suffixes like "as a part-time", "in the engineering department", etc.
        suffixes_to_remove = [
            "as a",
            "in the",
            "department",
            "permanent",
            "full-time",
            "part-time",
            "software engineer",
            "engineering"
        ]
        
        for suffix in suffixes_to_remove:
            if cleaned_name.lower().endswith(suffix.lower()):
                cleaned_name = cleaned_name[:-len(suffix)].strip()
                break
        
        # Split the cleaned name into parts
        name_parts = cleaned_name.split()
        
        if len(name_parts) < 2:
            # Try to find profiles with just the single name
            search_pattern = f"%{cleaned_name}%"
            profiles = db.query(User).filter(
                (User.first_name.ilike(search_pattern)) |
                (User.last_name.ilike(search_pattern))
            ).all()
        else:
            # Search for profiles with first and last name combinations
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            # Try different combinations
            profiles = db.query(User).filter(
                # Exact first + last name match
                (User.first_name.ilike(f"%{first_name}%") & User.last_name.ilike(f"%{last_name}%")) |
                # First name contains the first part
                (User.first_name.ilike(f"%{first_name}%")) |
                # Last name contains the last part
                (User.last_name.ilike(f"%{last_name}%")) |
                # Full name contains the search term
                (User.first_name + ' ' + User.last_name).ilike(f"%{cleaned_name}%")
            ).all()
        
        if not profiles:
            # Close session before returning
            if db:
                db.close()
            return EmployeeToolResult(
                success=False,
                message=f"❌ No user profiles found matching '{cleaned_name}'. Please create a user profile first before creating an employee record.",
                data={"profiles": [], "count": 0}
            )
        
        profile_list = []
        for profile in profiles:
            profile_list.append({
                "profile_id": str(profile.user_id),
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "email": profile.email,
                "role": profile.role
            })
        
        # Close session before returning
        if db:
            db.close()
        
        return EmployeeToolResult(
            success=True,
            message=f"✅ Found {len(profile_list)} profile(s) matching '{cleaned_name}'",
            data={
                "profiles": profile_list,
                "count": len(profile_list)
            }
        )
        
    except Exception as e:
        # Ensure session is closed on error
        if db:
            try:
                db.rollback()
                db.close()
            except:
                pass
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to search profiles: {str(e)}"
        )

def create_employee_tool(params: CreateEmployeeParams, context: Dict[str, Any] = None, db: Session = None) -> EmployeeToolResult:
    """Tool for creating a new employee record"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Extract user_id from context
        if not context or 'user_id' not in context:
            return EmployeeToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        
        # Check if profile exists - use the profile_id directly instead of User object
        profile_exists = db.query(User).filter(User.user_id == params.profile_id).first()
        if not profile_exists:
            return EmployeeToolResult(
                success=False,
                message=f"❌ Profile with ID '{params.profile_id}' not found."
            )
        
        # Check if employee record already exists for this profile
        existing_employee = db.query(Employee).filter(Employee.profile_id == params.profile_id).first()
        if existing_employee:
            return EmployeeToolResult(
                success=False,
                message=f"❌ Employee record already exists for this profile. Employee ID: {existing_employee.employee_id}, Job Title: {existing_employee.job_title}, Department: {existing_employee.department}"
            )
        
        # Check if employee number already exists
        if params.employee_number:
            existing_employee = db.query(Employee).filter(Employee.employee_number == params.employee_number).first()
            if existing_employee:
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Employee number '{params.employee_number}' already exists."
                )
        
        # Parse dates
        hire_date = datetime.utcnow().date()
        if params.hire_date:
            try:
                hire_date = datetime.strptime(params.hire_date, "%Y-%m-%d").date()
            except ValueError:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Invalid hire date format. Please use YYYY-MM-DD format."
                )
        
        termination_date = None
        if params.termination_date:
            try:
                termination_date = datetime.strptime(params.termination_date, "%Y-%m-%d").date()
                if termination_date <= hire_date:
                    return EmployeeToolResult(
                        success=False,
                        message="❌ Termination date must be after hire date."
                    )
            except ValueError:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Invalid termination date format. Please use YYYY-MM-DD format."
                )
        
        # Create employee record
        db_employee = Employee(
            profile_id=params.profile_id,
            employee_number=params.employee_number,
            job_title=params.job_title,
            department=params.department,
            employment_type=params.employment_type,
            full_time_part_time=params.full_time_part_time,
            committed_hours=params.committed_hours,
            hire_date=hire_date,
            termination_date=termination_date,
            rate_type=params.rate_type,
            rate=Decimal(str(params.rate)) if params.rate else None,
            currency=params.currency,
            nda_file_link=params.nda_file_link,
            contract_file_link=params.contract_file_link,
            created_by=user_id,
            updated_by=user_id
        )
        
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        
        # Close the database session
        db.close()
        
        return EmployeeToolResult(
            success=True,
            message=f"✅ Employee record created successfully",
            data={
                "employee_id": db_employee.employee_id,
                "profile_id": str(db_employee.profile_id),
                "employee_number": db_employee.employee_number,
                "job_title": db_employee.job_title,
                "department": db_employee.department,
                "employment_type": db_employee.employment_type,
                "full_time_part_time": db_employee.full_time_part_time,
                "hire_date": str(db_employee.hire_date),
                "status": "Active"
            }
        )
        
    except Exception as e:
        # Ensure session is closed on error
        if db:
            try:
                db.rollback()
                db.close()
            except:
                pass
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to create employee: {str(e)}"
        )

def update_employee_tool(params: UpdateEmployeeParams, context: Dict[str, Any] = None, db: Session = None) -> EmployeeToolResult:
    """Tool for updating an existing employee record"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Extract user_id from context
        if not context or 'user_id' not in context:
            return EmployeeToolResult(
                success=False,
                message="❌ User context not available. Please ensure you're authenticated."
            )
        
        user_id = context['user_id']
        
        # Find employee by ID
        if not params.employee_id:
            return EmployeeToolResult(
                success=False,
                message="❌ Employee ID is required for updates."
            )
        
        employee = db.query(Employee).filter(Employee.employee_id == params.employee_id).first()
        if not employee:
            return EmployeeToolResult(
                success=False,
                message=f"❌ Employee with ID {params.employee_id} not found."
            )
        
        # Check if employee number already exists (if being updated)
        if params.employee_number and params.employee_number != employee.employee_number:
            existing_employee = db.query(Employee).filter(Employee.employee_number == params.employee_number).first()
            if existing_employee:
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Employee number '{params.employee_number}' already exists."
                )
        
        # Update fields
        update_fields = []
        
        if params.employee_number is not None:
            employee.employee_number = params.employee_number
            update_fields.append("employee_number")
        
        if params.job_title is not None:
            employee.job_title = params.job_title
            update_fields.append("job_title")
        
        if params.department is not None:
            employee.department = params.department
            update_fields.append("department")
        
        if params.employment_type is not None:
            employee.employment_type = params.employment_type
            update_fields.append("employment_type")
        
        if params.full_time_part_time is not None:
            employee.full_time_part_time = params.full_time_part_time
            update_fields.append("full_time_part_time")
        
        if params.committed_hours is not None:
            employee.committed_hours = params.committed_hours
            update_fields.append("committed_hours")
        
        if params.hire_date is not None:
            try:
                hire_date = datetime.strptime(params.hire_date, "%Y-%m-%d").date()
                employee.hire_date = hire_date
                update_fields.append("hire_date")
            except ValueError:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Invalid hire date format. Please use YYYY-MM-DD format."
                )
        
        if params.termination_date is not None:
            try:
                termination_date = datetime.strptime(params.termination_date, "%Y-%m-%d").date()
                if termination_date <= employee.hire_date:
                    return EmployeeToolResult(
                        success=False,
                        message="❌ Termination date must be after hire date."
                    )
                employee.termination_date = termination_date
                update_fields.append("termination_date")
            except ValueError:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Invalid termination date format. Please use YYYY-MM-DD format."
                )
        
        if params.rate_type is not None:
            employee.rate_type = params.rate_type
            update_fields.append("rate_type")
        
        if params.rate is not None:
            employee.rate = Decimal(str(params.rate))
            update_fields.append("rate")
        
        if params.currency is not None:
            employee.currency = params.currency
            update_fields.append("currency")
        
        if params.nda_file_link is not None:
            employee.nda_file_link = params.nda_file_link
            update_fields.append("nda_file_link")
        
        if params.contract_file_link is not None:
            employee.contract_file_link = params.contract_file_link
            update_fields.append("contract_file_link")
        
        if not update_fields:
            return EmployeeToolResult(
                success=False,
                message=f"❌ No fields to update for employee ID {params.employee_id}."
            )
        
        # Set audit fields
        employee.updated_by = user_id
        employee.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        db.refresh(employee)
        
        # Close the database session
        try:
            db.close()
        except Exception as close_error:
            print(f"🔧 update_employee_tool: Error closing database session: {close_error}")
        
        return EmployeeToolResult(
            success=True,
            message=f"✅ Successfully updated employee ID {params.employee_id}. Updated fields: {', '.join(update_fields)}",
            data={
                "employee_id": employee.employee_id,
                "updated_fields": update_fields,
                "employee_number": employee.employee_number,
                "job_title": employee.job_title,
                "department": employee.department
            }
        )
        
    except Exception as e:
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
        except Exception as close_error:
            print(f"🔧 update_employee_tool: Error closing database session on error: {close_error}")
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to update employee: {str(e)}"
        )

def search_employees_tool(search_term: str, limit: int = 50, db: Session = None) -> EmployeeToolResult:
    """Tool for searching employees by name, job title, department, or employee number"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Search across multiple fields
        query = db.query(Employee).join(User, Employee.profile_id == User.user_id)
        
        search_filter = (
            User.first_name.ilike(f"%{search_term}%") |
            User.last_name.ilike(f"%{search_term}%") |
            Employee.job_title.ilike(f"%{search_term}%") |
            Employee.department.ilike(f"%{search_term}%") |
            Employee.employee_number.ilike(f"%{search_term}%")
        )
        
        employees = query.filter(search_filter).limit(limit).all()
        
        # Format results
        employee_list = []
        for emp in employees:
            profile = db.query(User).filter(User.user_id == emp.profile_id).first()
            employee_list.append({
                "employee_id": emp.employee_id,
                "profile_id": str(emp.profile_id),  # Add profile_id to results
                "employee_number": emp.employee_number,
                "job_title": emp.job_title,
                "department": emp.department,
                "employment_type": emp.employment_type,
                "full_time_part_time": emp.full_time_part_time,
                "hire_date": str(emp.hire_date) if emp.hire_date else None,
                "termination_date": str(emp.termination_date) if emp.termination_date else None,
                "rate_type": emp.rate_type,
                "rate": float(emp.rate) if emp.rate else None,
                "currency": emp.currency,
                "profile": {
                    "first_name": profile.first_name if profile else None,
                    "last_name": profile.last_name if profile else None,
                    "email": profile.email if profile else None,
                    "full_name": profile.full_name if profile else "Unknown"
                } if profile else {
                    "first_name": None,
                    "last_name": None,
                    "email": None,
                    "full_name": "Unknown"
                }
            })
        
        # Close the database session
        try:
            db.close()
        except Exception as close_error:
            print(f"🔧 search_employees_tool: Error closing database session: {close_error}")
        
        return EmployeeToolResult(
            success=True,
            message=f"📋 Found {len(employee_list)} employees matching '{search_term}'",
            data={
                "employees": employee_list,
                "count": len(employee_list),
                "search_term": search_term
            }
        )
        
    except Exception as e:
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
        except Exception as close_error:
            print(f"🔧 search_employees_tool: Error closing database session on error: {close_error}")
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to search employees: {str(e)}"
        )

def get_employee_details_tool(employee_id: int, db: Session = None) -> EmployeeToolResult:
    """Tool for getting detailed employee information"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Find employee by ID
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            # Close the database session
            try:
                db.close()
            except Exception as close_error:
                print(f"🔧 get_employee_details_tool: Error closing database session: {close_error}")
            
            return EmployeeToolResult(
                success=False,
                message=f"❌ Employee with ID {employee_id} not found."
            )
        
        # Get profile information
        profile = db.query(User).filter(User.user_id == employee.profile_id).first()
        
        # Close the database session
        try:
            db.close()
        except Exception as close_error:
            print(f"🔧 get_employee_details_tool: Error closing database session: {close_error}")
        
        return EmployeeToolResult(
            success=True,
            message=f"📋 Employee details for {profile.full_name if profile else 'Unknown'}",
            data={
                "employee_id": employee.employee_id,
                "employee_number": employee.employee_number,
                "job_title": employee.job_title,
                "department": employee.department,
                "employment_type": employee.employment_type,
                "full_time_part_time": employee.full_time_part_time,
                "committed_hours": employee.committed_hours,
                "hire_date": str(employee.hire_date) if employee.hire_date else None,
                "termination_date": str(employee.termination_date) if employee.termination_date else None,
                "rate_type": employee.rate_type,
                "rate": float(employee.rate) if employee.rate else None,
                "currency": employee.currency,
                "nda_file_link": employee.nda_file_link,
                "contract_file_link": employee.contract_file_link,
                "profile": {
                    "first_name": profile.first_name if profile else None,
                    "last_name": profile.last_name if profile else None,
                    "email": profile.email if profile else None,
                    "full_name": profile.full_name if profile else "Unknown"
                } if profile else {
                    "first_name": None,
                    "last_name": None,
                    "email": None,
                    "full_name": "Unknown"
                },
                "created_at": str(employee.created_at) if employee.created_at else None,
                "updated_at": str(employee.updated_at) if employee.updated_at else None
            }
        )
        
    except Exception as e:
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
        except Exception as close_error:
            print(f"🔧 get_employee_details_tool: Error closing database session on error: {close_error}")
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to get employee details: {str(e)}"
        )

def get_all_employees_tool(db: Session = None) -> EmployeeToolResult:
    """Tool for getting all employees with basic information"""
    try:
        # Always create a fresh database session to avoid session closure issues
        db = next(get_db())
        
        # Get all employees with profile information
        employees = db.query(Employee).join(User, Employee.profile_id == User.user_id).all()
        
        # Format results
        employee_list = []
        for emp in employees:
            # Get profile information for each employee
            profile = db.query(User).filter(User.user_id == emp.profile_id).first()
            
            employee_list.append({
                "employee_id": emp.employee_id,
                "profile_id": str(emp.profile_id),  # Add profile_id to results
                "employee_number": emp.employee_number,
                "job_title": emp.job_title,
                "department": emp.department,
                "employment_type": emp.employment_type,
                "full_time_part_time": emp.full_time_part_time,
                "hire_date": str(emp.hire_date) if emp.hire_date else None,
                "termination_date": str(emp.termination_date) if emp.termination_date else None,
                "rate_type": emp.rate_type,
                "rate": float(emp.rate) if emp.rate else None,
                "currency": emp.currency,
                "profile": {
                    "first_name": profile.first_name if profile else None,
                    "last_name": profile.last_name if profile else None,
                    "email": profile.email if profile else None,
                    "full_name": profile.full_name if profile else "Unknown"
                } if profile else {
                    "first_name": None,
                    "last_name": None,
                    "email": None,
                    "full_name": "Unknown"
                }
            })
        
        # Close the database session
        try:
            db.close()
        except Exception as close_error:
            print(f"🔧 get_all_employees_tool: Error closing database session: {close_error}")
        
        return EmployeeToolResult(
            success=True,
            message=f"📋 Found {len(employee_list)} employees in the system",
            data={
                "employees": employee_list,
                "count": len(employee_list)
            }
        )
        
    except Exception as e:
        # Ensure database session is closed even on error
        try:
            if 'db' in locals() and db is not None:
                db.close()
        except Exception as close_error:
            print(f"🔧 get_all_employees_tool: Error closing database session on error: {close_error}")
        
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to get all employees: {str(e)}"
        )
