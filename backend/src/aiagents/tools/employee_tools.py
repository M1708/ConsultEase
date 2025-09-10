from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.exc import IntegrityError
import re
import calendar
import string
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from src.database.core.database import get_ai_db
from src.database.core.models import Employee, User
from src.database.core.schemas import EmployeeCreate, EmployeeUpdate
from datetime import datetime, date
from decimal import Decimal
from datetime import datetime
# Import storage service to get download URL
from src.services.storage_service import SupabaseStorageService
import base64
from io import BytesIO
                
# Import caching functionality
from ..performance.cache_decorators import (
    cached_employee_operation,
    cached_search_operation,
    cache_profile_lookup,
    cache_employee_lookup,
    performance_tracked
)
from ..performance.employee_cache import (
    cache_employee_data,
    cache_employee_search_results,
    cache_profile_data,
    invalidate_employee_cache,
    get_cached_employee_by_id,
    get_cached_employee_by_profile_id,
    get_cached_employee_by_number,
    get_cached_employee_search,
    get_cached_profile_by_name
)

class EmployeeToolResult(BaseModel):
    """Result object for employee tool operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class CreateEmployeeParams(BaseModel):
    employee_name: Optional[str] = None
    profile_id: Optional[str] = None
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
    salary: Optional[float] = None
    currency: str = "USD"
    nda_file_link: Optional[str] = None
    contract_file_link: Optional[str] = None

class UpdateEmployeeParams(BaseModel):
    employee_id: Optional[int] = None
    profile_id: Optional[str] = None  # TODO: OPTIMIZATION - Support profile_id to eliminate nested sessions
    employee_name: Optional[str] = None  # TODO: OPTIMIZATION - Support employee_name for inline profile search
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


class DeleteEmployeeParams(BaseModel):
    employee_id: Optional[int] = None
    profile_id: Optional[str] = None
    employee_number: Optional[str] = None
    employee_name: Optional[str] = None

def get_date_range(relative_str, today=None):
    """Get date range for relative date strings"""
    if today is None:
        today = datetime.now().date()
    
    # Dictionary mapping for simple cases
    date_handlers = {
        "this month": lambda: _get_month_range(today),
        "this year": lambda: _get_year_range(today),
        "last month": lambda: _get_month_range(today - relativedelta(months=1)),
        "last year": lambda: _get_year_range(today - relativedelta(years=1)),
        "next month": lambda: _get_month_range(today + relativedelta(months=1)),
        "next year": lambda: _get_year_range(today + relativedelta(years=1)),
    }
    
    # Check simple cases first
    if relative_str in date_handlers:
        return date_handlers[relative_str]()
    
    # Next year + specific month
    month_mapping = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
        'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }
    
    # Next year in specific month
    next_year_month_pattern = r"next year.*?(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)"
    match = re.search(next_year_month_pattern, relative_str.lower())
    if match:
        month_name = match.group(1)
        month_num = month_mapping[month_name]
        next_year = today + relativedelta(years=1)
        return _get_specific_month_range(next_year.year, month_num)
    
    # Last N months/years
    last_period_pattern = r"last (\d+) (months?|years?)"
    match = re.search(last_period_pattern, relative_str.lower())
    if match:
        count = int(match.group(1))
        period = match.group(2)
        if 'month' in period:
            start_date = (today - relativedelta(months=count)).replace(day=1)
            end_date = (today - relativedelta(months=1)).replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        else:  # years
            start_date = (today - relativedelta(years=count)).replace(month=1, day=1)
            end_date = (today - relativedelta(years=1)).replace(month=12, day=31)
        return start_date, end_date
    
    # Next N months
    next_period_pattern = r"next (\d+) months?"
    match = re.search(next_period_pattern, relative_str.lower())
    if match:
        count = int(match.group(1))
        start_date = (today + relativedelta(months=1)).replace(day=1)
        end_date = today + relativedelta(months=count)
        return start_date, end_date
    
    # Fallback
    return None, None

def _get_month_range(date):
    """Get first and last day of month for given date"""
    start_date = date.replace(day=1)
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    return start_date, end_date

def _get_year_range(date):
    """Get first and last day of year for given date"""
    start_date = date.replace(month=1, day=1)
    end_date = date.replace(month=12, day=31)
    return start_date, end_date

def _get_specific_month_range(year, month):
    """Get first and last day of specific month/year"""
    start_date = datetime(year, month, 1).date()
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day).date()
    return start_date, end_date

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

@cached_employee_operation(cache_ttl=180, invalidate_on_update=True, track_performance=True)
async def check_employee_exists_tool(profile_id: str) -> EmployeeToolResult:
    """Tool for checking if an employee record already exists for a given profile"""
    try:
        async with get_ai_db() as session:
        # Check if employee record exists
            result = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
            existing_employee = result.scalar_one_or_none()
            #existing_employee = db.query(Employee).filter(Employee.profile_id == profile_id).first()
        
        if existing_employee:
            # Get profile information
            check_profile = await session.execute(select(User).filter(User.user_id == profile_id))
            profile = check_profile.scalar_one_or_none()
            #profile = db.query(User).filter(User.user_id == profile_id).first()
                    
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

def parse_employee_details_from_message(message: str) -> Dict[str, Any]:
    """Enhanced parser for employee details from natural language user message"""
    details = {}
    
    # Parse employment type with more variations
    message_lower = message.lower()
    if any(word in message_lower for word in ["permanent", "is permanent", "permanent employee"]):
        details["employment_type"] = "permanent"
    elif any(word in message_lower for word in ["contract", "contractor", "contract worker"]):
        details["employment_type"] = "contract"
    elif any(word in message_lower for word in ["intern", "internship", "intern position"]):
        details["employment_type"] = "intern"
    elif any(word in message_lower for word in ["consultant", "consulting", "freelancer"]):
        details["employment_type"] = "consultant"
    
    # Parse full-time/part-time with more variations
    if any(word in message_lower for word in ["fulltime", "full-time", "full time", "is fulltime"]):
        details["full_time_part_time"] = "full_time"
    elif any(word in message_lower for word in ["part-time", "parttime", "part time", "is part-time"]):
        details["full_time_part_time"] = "part_time"
    
    # Enhanced job title extraction
    job_title_patterns = [
        r'(?:is a|as a|as an|is an|works as|position as|role as|job title is|title is)\s+([a-zA-Z\s]+?)(?:\s*,|\s*in|\s*at|\s*for|\s*with|\s*and|$)',
        r'(?:senior|junior|lead|principal|chief|head of|director of)\s+([a-zA-Z\s]+?)(?:\s*,|\s*in|\s*at|\s*for|\s*with|\s*and|$)',
        r'([a-zA-Z\s]*(?:researcher|scientist|engineer|manager|developer|analyst|specialist|coordinator|assistant|director|lead))\s*(?:,|\s*in|\s*at|\s*for|\s*with|\s*and|$)'
    ]
    
    for pattern in job_title_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            job_title = match.group(1).strip()
            # Clean up common words that shouldn't be in job titles
            job_title = re.sub(r'\b(the|and|or|in|at|for|with|is|a|an)\b', '', job_title, flags=re.IGNORECASE).strip()
            if job_title and len(job_title) > 2:
                details["job_title"] = ' '.join(word.capitalize() for word in job_title.split())
                break
    
    # Enhanced department extraction
    department_patterns = [
        r'(?:in|works in|department is|dept is|from)\s+(?:the\s+)?([a-zA-Z\s]+?)\s+department',
        r'department[:\s]+([a-zA-Z\s]+?)(?:\s*,|\s*and|\s*with|$)',
        r'(?:research|marketing|engineering|sales|hr|human resources|finance|operations|it|technology)\b'
    ]
    
    for pattern in department_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if len(match.groups()) > 0:
                department = match.group(1).strip()
            else:
                department = match.group(0).strip()
            
            # Clean and capitalize department name
            department = re.sub(r'\b(the|and|or|in|at|for|with|is|a|an)\b', '', department, flags=re.IGNORECASE).strip()
            if department and len(department) > 1:
                details["department"] = ' '.join(word.capitalize() for word in department.split())
                break
    
    # Enhanced salary/rate parsing with more patterns
    salary_patterns = [
        r'(?:monthly salary|salary|monthly)\s+(?:is|of)?\s*\$?([\d,]+)',
        r'\$?([\d,]+)\s*(?:per month|monthly|/month)',
        r'\$?([\d,]+)\s*(?:per hour|hourly|/hour|/hr)',
        r'\$?([\d,]+)\s*(monthly|yearly|hourly|annually)'
    ]
    
    for pattern in salary_patterns:
        salary_match = re.search(pattern, message_lower)
        if salary_match:
            amount = float(salary_match.group(1).replace(',', ''))
            
            # Determine rate type from context
            if len(salary_match.groups()) > 1:
                period = salary_match.group(2)
            else:
                # Infer from context
                if any(word in message_lower for word in ["monthly", "per month", "/month"]):
                    period = "monthly"
                elif any(word in message_lower for word in ["hourly", "per hour", "/hour", "/hr"]):
                    period = "hourly"
                elif any(word in message_lower for word in ["yearly", "annually", "per year"]):
                    period = "yearly"
                else:
                    period = "monthly"  # default
            
            details["rate"] = amount
            if period in ["monthly", "salary"]:
                details["rate_type"] = "salary"
            elif period == "yearly":
                details["rate_type"] = "salary"
                details["rate"] = amount / 12  # Convert yearly to monthly
            elif period == "hourly":
                details["rate_type"] = "hourly"
            break
    
    # Enhanced hire date parsing with multiple patterns
    date_patterns = [
        r'(?:joined us on|hired on|starting|starts|hire date|start date|begins)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})',
        r'(?:joined us on|hired on|starting|starts|hire date|start date|begins)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})',
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})'
    ]
    
    month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                 "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
    
    for pattern in date_patterns:
        date_match = re.search(pattern, message, re.IGNORECASE)
        if date_match:
            groups = date_match.groups()
            
            # Handle different group orders
            if groups[0].isdigit():  # Day first pattern
                day = groups[0]
                month = groups[1]
                year = groups[2]
            else:  # Month first pattern
                month = groups[0]
                day = groups[1]
                year = groups[2]
            
            month_num = month_map.get(month.lower()[:3])
            if month_num:
                details["hire_date"] = f"{year}-{month_num}-{day.zfill(2)}"
                break
    
    # Parse employee number if mentioned
    emp_number_patterns = [
        r'(?:employee number|emp number|employee id|emp id|staff id)\s*:?\s*([A-Z]*\d+)',
        r'(?:as|with id|id)\s+([A-Z]{2,4}\d+)',
        r'\b([A-Z]{2,4}\d{2,4})\b'
    ]
    
    for pattern in emp_number_patterns:
        emp_match = re.search(pattern, message, re.IGNORECASE)
        if emp_match:
            details["employee_number"] = emp_match.group(1).upper()
            break
    
    return details

@cache_profile_lookup(cache_ttl=600)  # Cache profiles for 10 minutes
@performance_tracked("search_profiles_by_name")
async def search_profiles_by_name_tool(search_name: str) -> EmployeeToolResult:
    """Tool for searching user profiles by name to find profile_id for employee creation"""
    try:
        async with get_ai_db() as session:
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
            
            name_parts = cleaned_name.split()
            
            if len(name_parts) < 2:
                # Single name search - use async/await consistently
                search_pattern = f"%{cleaned_name}%"
                result = await session.execute(select(User).filter(
                    or_(
                        User.first_name.ilike(search_pattern),
                        User.last_name.ilike(search_pattern)
                    )
                ))
                profiles = result.scalars().all()
            else:
                # Multi-name search - optimized with better logic
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                # Build search conditions more efficiently - PgBouncer compatible
                conditions = [
                    # Exact first + last name match (highest priority)
                    and_(
                        User.first_name.ilike(f"%{first_name}%"),
                        User.last_name.ilike(f"%{last_name}%")
                    )
                    # Remove func.concat to avoid PgBouncer prepared statement issues
                ]
                
                # Add individual name matches only if they're different from the full name search
                if len(cleaned_name) > len(first_name):  # Avoid redundant searches
                    conditions.extend([
                        User.first_name.ilike(f"%{first_name}%"),
                        User.last_name.ilike(f"%{last_name}%")
                    ])
                
                result = await session.execute(select(User).filter(or_(*conditions)))
                profiles = result.scalars().all()

                # Optional: Add result ranking/sorting for better matches
                # profiles = sorted(profiles, key=lambda p: name_match_score(p, cleaned_name), reverse=True)
                # profiles = result.scalars().all()

            if not profiles:
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
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to search profiles: {str(e)}"
        )

async def create_employee_tool(params: CreateEmployeeParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for creating a new employee record"""
    
    try:
        # Always create a fresh database session to avoid session closure issues
        async with get_ai_db() as session:
        
            # Extract user_id from context
            if not context or 'user_id' not in context:
                return EmployeeToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            resolved_profile_id = params.profile_id
            
            # TODO: OPTIMIZATION - Efficient profile search with indexed fields only
            # If employee_name is provided but no profile_id, search for the profile inline
            if params.employee_name and params.profile_id is None:
                # TODO: OPTIMIZATION - Use efficient search strategy
                # Search for profiles inline to avoid nested database sessions
                cleaned_name = params.employee_name.strip()
                
                # TODO: OPTIMIZATION - Prioritize indexed fields for better performance
                # Use email first (likely indexed), then name fields
                # Avoid expensive func.concat operations and multiple ilike conditions
                conditions = [
                    User.email.ilike(f"%{cleaned_name}%"),  # Email search (likely indexed)
                    User.first_name.ilike(f"%{cleaned_name}%"),  # First name search
                    User.last_name.ilike(f"%{cleaned_name}%")  # Last name search
                ]
                
                # TODO: OPTIMIZATION - Add full name search only if needed
                # Use simpler approach than func.concat for better performance
                if ' ' in cleaned_name:
                    # Split name and search for both parts
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        conditions.extend([
                            User.first_name.ilike(f"%{name_parts[0]}%"),
                            User.last_name.ilike(f"%{name_parts[-1]}%")
                        ])
                
                # Execute profile search in the same session
                result = await session.execute(select(User).filter(or_(*conditions)))
                profiles = result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No user profile found for '{params.employee_name}'. Please create a user profile first before creating an employee record."
                    )
                
                if len(profiles) > 1:
                    # Multiple profiles found - ask for clarification
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple profiles found for '{params.employee_name}': {', '.join(profile_names)}. Please specify which profile to use."
                    )
                
                # Use the found profile
                resolved_profile_id = profiles[0].user_id
            
            # Check if profile exists - use the resolved profile_id
            if not resolved_profile_id:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either profile_id or employee_name must be provided."
                )
            
            check_profile = await session.execute(select(User).filter(User.user_id == resolved_profile_id))
            profile_exists = check_profile.scalar_one_or_none()
            if not profile_exists:
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Profile with ID '{resolved_profile_id}' not found."
                )
            
            # Check if employee record already exists for this profile
            check_employee = await session.execute(select(Employee).filter(Employee.profile_id == resolved_profile_id))
            existing_employee = check_employee.scalar_one_or_none()
            
            if existing_employee:
                # Get employee name from profile for better error message
                employee_name = f"{profile_exists.first_name} {profile_exists.last_name}" if profile_exists and profile_exists.first_name and profile_exists.last_name else "Unknown"
                
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Employee record already exists for this profile. Please present the existing employee information in a user-friendly format, showing all available fields in a clear, organized manner.",
                    data={
                        "employee_id": existing_employee.employee_id,
                        "employee_name": employee_name,
                        "profile_id": str(existing_employee.profile_id),
                        "employee_number": existing_employee.employee_number,
                        "job_title": existing_employee.job_title,
                        "department": existing_employee.department,
                        "employment_type": existing_employee.employment_type,
                        "full_time_part_time": existing_employee.full_time_part_time,
                        "committed_hours": existing_employee.committed_hours,
                        "hire_date": str(existing_employee.hire_date) if existing_employee.hire_date else None,
                        "termination_date": str(existing_employee.termination_date) if existing_employee.termination_date else None,
                        "rate_type": existing_employee.rate_type,
                        "rate": float(existing_employee.rate) if existing_employee.rate else None,
                        "currency": existing_employee.currency,
                        "email": profile_exists.email,
                        "nda_file_link": existing_employee.nda_file_link,
                        "contract_file_link": existing_employee.contract_file_link,
                        "status": "Active"
                    }
                )
            
            # Check if employee number already exists
            if params.employee_number:
                check_emp = await session.execute(select(Employee).filter(Employee.employee_number == params.employee_number))
                existing_employee = check_emp.scalar_one_or_none()
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
            
            # Initialize rate variables outside conditional blocks
            final_rate = params.rate
            final_rate_type = params.rate_type
            
            # If salary is provided, use it as the rate with salary type
            if params.salary:
                final_rate = params.salary
                final_rate_type = "salary"
            
            # TODO: OPTIMIZATION - Employee name will be handled in the success response
            # We'll use the profile data from the search above
            db_employee = Employee(
                profile_id=resolved_profile_id,
                employee_number=params.employee_number,
                job_title=params.job_title,
                department=params.department,
                employment_type=params.employment_type,
                full_time_part_time=params.full_time_part_time,
                committed_hours=params.committed_hours,
                hire_date=hire_date,
                termination_date=termination_date,
                rate_type=final_rate_type,
                rate=Decimal(str(final_rate)) if final_rate else None,
                currency=params.currency,
                nda_file_link=params.nda_file_link,
                contract_file_link=params.contract_file_link,
                created_by=user_id,
                updated_by=user_id
            )
            
            # TODO: OPTIMIZATION - Handle database constraints efficiently
            # Let database handle duplicate checks and other constraints
            try:
                session.add(db_employee)
                await session.commit()
                await session.refresh(db_employee)
                
                # Get the employee name from the profile for the success message
                employee_name = f"{profile_exists.first_name} {profile_exists.last_name}" if profile_exists and profile_exists.first_name and profile_exists.last_name else "Unknown"
                
                return EmployeeToolResult(
                success=True,
                message=f"✅ Employee record created successfully for {employee_name} (Employee ID: {db_employee.employee_id})",
                data={
                    "employee_id": db_employee.employee_id,
                    "employee_name": employee_name,
                    "profile_id": str(db_employee.profile_id),
                    "employee_number": db_employee.employee_number,
                    "job_title": db_employee.job_title,
                    "department": db_employee.department,
                    "employment_type": db_employee.employment_type,
                    "full_time_part_time": db_employee.full_time_part_time,
                    "hire_date": str(db_employee.hire_date),
                    "rate_type": db_employee.rate_type,
                    "rate": float(db_employee.rate) if db_employee.rate else None,
                    "currency": db_employee.currency,
                    "committed_hours": db_employee.committed_hours,
                    "email": profile_exists.email,
                    "nda_file_link": db_employee.nda_file_link,
                    "contract_file_link": db_employee.contract_file_link,
                    "status": "Active"
                }
            )

            except IntegrityError as e:
                # TODO: OPTIMIZATION - Handle database constraint violations efficiently
                # Database handles duplicate checks, we just need to parse the error message
                await session.rollback()
                error_message = str(e).lower()
                if "employee_number" in error_message or "duplicate" in error_message:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Employee number '{params.employee_number}' already exists."
                    )
                elif "profile_id" in error_message:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Employee record already exists for this profile."
                    )
                else:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Database constraint violation: {str(e)}"
                    )
            
            
        
    except Exception as e:
        # Ensure session is closed on error
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to create employee: {str(e)}"
        )

@cached_employee_operation(cache_ttl=300, invalidate_on_update=True, track_performance=True)
async def update_employee_tool(params: UpdateEmployeeParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for updating an existing employee record"""
    try:
        # Always create a fresh database session to avoid session closure issues
        async with get_ai_db() as session:
            # Extract user_id from context
            if not context or 'user_id' not in context:
                return EmployeeToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # TODO: OPTIMIZATION - Support employee_id, profile_id, or employee_name to eliminate nested sessions
            # Find employee by ID, profile_id, or employee_name (with inline profile search)
            if params.employee_id:
                check_employee = await session.execute(select(Employee).filter(Employee.employee_id == params.employee_id))
                employee = check_employee.scalar_one_or_none()
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Employee with ID {params.employee_id} not found."
                    )
            elif params.profile_id:
                check_employee = await session.execute(select(Employee).filter(Employee.profile_id == params.profile_id))
                employee = check_employee.scalar_one_or_none()
                
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee record found for profile ID {params.profile_id}. The profile exists but no employee record has been created."
                    )
            elif params.employee_name:
                # TODO: OPTIMIZATION - Efficient profile search with indexed fields only
                # Search for profiles inline to avoid nested database sessions
                cleaned_name = params.employee_name.strip()
                
                # TODO: OPTIMIZATION - Prioritize indexed fields for better performance
                # Use email first (likely indexed), then name fields
                # Avoid expensive func.concat operations and multiple ilike conditions
                conditions = [
                    User.email.ilike(f"%{cleaned_name}%"),  # Email search (likely indexed)
                    User.first_name.ilike(f"%{cleaned_name}%"),  # First name search
                    User.last_name.ilike(f"%{cleaned_name}%")  # Last name search
                ]
                
                # TODO: OPTIMIZATION - Add full name search only if needed
                # Use simpler approach than func.concat for better performance
                if ' ' in cleaned_name:
                    # Split name and search for both parts
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        conditions.extend([
                            User.first_name.ilike(f"%{name_parts[0]}%"),
                            User.last_name.ilike(f"%{name_parts[-1]}%")
                        ])
                
                # Execute profile search in the same session
                result = await session.execute(select(User).filter(or_(*conditions)))
                profiles = result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No user profile found for '{params.employee_name}'. Please check the name and try again."
                    )
                
                if len(profiles) > 1:
                    # Multiple profiles found - ask for clarification
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple profiles found for '{params.employee_name}': {', '.join(profile_names)}. Please be more specific."
                    )
                
                # Use the found profile to get the employee record
                profile_id = str(profiles[0].user_id)
                check_employee = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
                employee = check_employee.scalar_one_or_none()
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee record found for '{params.employee_name}'. The profile exists but no employee record has been created."
                    )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either employee_id, profile_id, or employee_name is required for updates."
                )
            
            # TODO: OPTIMIZATION - Let database handle duplicate check via constraints
            # This eliminates an extra database query and improves performance
            # The database will raise IntegrityError if employee_number already exists
            
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
            
            # TODO: OPTIMIZATION - Handle database constraints and eliminate redundant lookup
            # Let database handle duplicate checks and use existing data for response
            try:
                # Commit changes - database will raise IntegrityError if constraints violated
                await session.commit()
                await session.refresh(employee)
                
                # TODO: OPTIMIZATION - Minimal profile lookup for name only
                # We only need the name for formatting, not all profile data
                # This is a minimal query compared to the previous full profile lookup
                check_profile = await session.execute(select(User.first_name, User.last_name).filter(User.user_id == employee.profile_id))
                profile_name = check_profile.first()
                
                # Return success response using existing employee data
                return EmployeeToolResult(
                    success=True,
                    message=f"✅ Successfully updated employee. Updated fields: {', '.join(update_fields)}. Please present the employee information in a user-friendly format, showing only non-null fields in a clear, organized manner.",
                    data={
                        "updated_fields": update_fields,
                        "employee": {
                            "employee_id": employee.employee_id,
                            "employee_number": employee.employee_number,
                            "profile_id": str(employee.profile_id),
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
                            "created_at": str(employee.created_at) if employee.created_at else None,
                            "updated_at": str(employee.updated_at) if employee.updated_at else None
                        },
                        # TODO: OPTIMIZATION - Minimal profile data for formatting only
                        # We only include the name needed for response formatting
                        "profile": {
                            "profile_id": str(employee.profile_id),
                            "first_name": profile_name.first_name if profile_name else None,
                            "last_name": profile_name.last_name if profile_name else None,
                            "full_name": f"{profile_name.first_name} {profile_name.last_name}".strip() if profile_name and profile_name.first_name and profile_name.last_name else "Employee"
                        }
                    }
                )
                        
            except IntegrityError as e:
                # TODO: OPTIMIZATION - Handle database constraint violations efficiently
                # Database handles duplicate checks, we just need to parse the error message
                await session.rollback()
                error_message = str(e).lower()
                if "employee_number" in error_message or "duplicate" in error_message:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Employee number '{params.employee_number}' already exists."
                    )
                else:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Database constraint violation: {str(e)}"
                    )
        
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to update employee: {str(e)}"
        )

@cached_search_operation(cache_ttl=180, track_performance=True)
async def search_employees_tool(search_term: str, limit: int = 50) -> EmployeeToolResult:
    """Tool for searching employees by name, job title, department, or employee number"""

    try:
        async with get_ai_db() as session:
            # Check if this is a person name lookup (First Last format)
            import re
            person_name_pattern = r'^[A-Z][a-z]+\s+[A-Z][a-z]+$'
            is_person_name = re.match(person_name_pattern, search_term.strip())
            
            if is_person_name:
                # Split the name
                name_parts = search_term.strip().split()
                first_name = name_parts[0]
                last_name = name_parts[1]
                
                # Look up the profile first
                profile_query = select(User).filter(
                    User.first_name.ilike(f"%{first_name}%"),
                    User.last_name.ilike(f"%{last_name}%")
                )
                profile_result = await session.execute(profile_query)
                profile = profile_result.scalar_one_or_none()
                
                if profile:
                    # Now search for employee with this specific profile_id
                    employee_query = select(Employee).filter(Employee.profile_id == profile.user_id)
                    employee_result = await session.execute(employee_query)
                    employee = employee_result.scalar_one_or_none()
                    
                    if employee:
                        # Build the employee data
                        employee_list = [{
                            "employee_id": employee.employee_id,
                            "profile_id": str(employee.profile_id),
                            "employee_number": employee.employee_number,
                            "job_title": employee.job_title,
                            "department": employee.department,
                            "employment_type": employee.employment_type,
                            "full_time_part_time": employee.full_time_part_time,
                            "hire_date": str(employee.hire_date) if employee.hire_date else None,
                            "termination_date": str(employee.termination_date) if employee.termination_date else None,
                            "rate_type": employee.rate_type,
                            "rate": float(employee.rate) if employee.rate else None,
                            "currency": employee.currency,
                            "profile": {
                                "first_name": profile.first_name,
                                "last_name": profile.last_name,
                                "email": profile.email,
                                "full_name": f"{profile.first_name} {profile.last_name}"
                            }
                        }]
                        
                        return EmployeeToolResult(
                            success=True,
                            message=f"📋 Found 1 employee matching '{search_term}'. Please format this data to include ALL fields: Employee Number, Job Title, Department, Employment Type, Work Schedule, Hire Date, Rate, and Email address from the profile data.",
                            data={
                                "employees": employee_list,
                                "count": 1,
                                "search_term": search_term
                            }
                        )
                    else:
                        return EmployeeToolResult(
                            success=True,
                            message=f"📋 Found profile for '{search_term}' but no employee record exists.",
                            data={
                                "employees": [],
                                "count": 0,
                                "search_term": search_term
                            }
                        )
                else:
                    # Fall through to regular search
                    pass
            
            # Search across multiple fields
            # Handle inconsistent database values for part-time/full-time
            search_term_variations = [search_term]
            if search_term.lower() == "part-time":
                search_term_variations.extend(["part_time", "part time"])
            elif search_term.lower() == "full-time":
                search_term_variations.extend(["full_time", "full time"])
            elif search_term.lower() == "part_time":
                search_term_variations.extend(["part-time", "part time"])
            elif search_term.lower() == "full_time":
                search_term_variations.extend(["full-time", "full time"])
            
            # Build search filter with variations
            # TODO: If employee queries become incomplete, revert this rate_type field addition
            search_conditions = []
            
            # Handle date-based searches
            if search_term.startswith("start_date:"):
                # TODO: If employee queries become incomplete, revert this date search addition
                date_str = search_term.replace("start_date:", "").strip()
                try:
                    # Try to parse various date formats
                    date_formats = [
                        "%b %d %Y",      # Jan 1 2026
                        "%B %d %Y",      # January 1 2026
                        "%b %dst %Y",    # Jan 1st 2026
                        "%b %dnd %Y",    # Jan 2nd 2026
                        "%b %drd %Y",    # Jan 3rd 2026
                        "%b %dth %Y",    # Jan 4th 2026
                        "%B %dst %Y",    # January 1st 2026
                        "%B %dnd %Y",    # January 2nd 2026
                        "%B %drd %Y",    # January 3rd 2026
                        "%B %dth %Y",    # January 4th 2026
                        "%Y-%m-%d",      # 2026-01-01
                        "%m/%d/%Y",      # 01/01/2026
                        "%d/%m/%Y"       # 01/01/2026
                    ]
                    
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date:
                        # Search for exact hire date match
                        search_filter = Employee.hire_date == parsed_date
                    else:
                        # Fallback to text search if date parsing fails
                        search_filter = Employee.hire_date.ilike(f"%{date_str}%")
                except Exception as e:
                    print(f"Date parsing error: {e}")
                    # Fallback to text search
                    search_filter = Employee.hire_date.ilike(f"%{date_str}%")
            elif search_term.startswith("start_relative:"):
                # TODO: If employee queries become incomplete, revert this relative date search addition
                relative_str = search_term.replace("start_relative:", "").strip()
                try:
                    start_date, end_date = get_date_range(relative_str)
                    if start_date and end_date:
                        search_filter = Employee.hire_date.between(start_date, end_date)
                    else:
                        search_filter = Employee.hire_date.ilike(f"%{relative_str}%")    

                except Exception as e:
                    print(f"Relative date parsing error: {e}")
                    # Fallback to text search
                    search_filter = Employee.hire_date.ilike(f"%{relative_str}%")
            else:
                # Regular text-based search
                for term in search_term_variations:
                    search_conditions.extend([
                        User.first_name.ilike(f"%{term}%"),
                        User.last_name.ilike(f"%{term}%"),
                        Employee.job_title.ilike(f"%{term}%"),
                        Employee.department.ilike(f"%{term}%"),
                        Employee.employee_number.ilike(f"%{term}%"),
                        Employee.employment_type.ilike(f"%{term}%"),
                        Employee.full_time_part_time.ilike(f"%{term}%"),
                        Employee.rate_type.ilike(f"%{term}%")  # 🚀 FIX: Add rate_type search for hourly/salary queries
                    ])
                
                search_filter = or_(*search_conditions)
        
            # Step 1: Get employees with their profiles in a single query with filters
            final_join_query = select(Employee, User).join(User, Employee.profile_id == User.user_id, isouter=True).filter(search_filter).limit(limit)
            employees_with_profiles = await session.execute(final_join_query)
            # Convert to list to get actual count
            employees_list = list(employees_with_profiles)

            # Replace the entire employee processing section with this:
            employee_list = []
            for emp, profile in employees_list:
                # Build employee data with profile information
                employee_data = {
                "employee_id": emp.employee_id,
                    "profile_id": str(emp.profile_id),  # Keep for internal operations
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
                        "first_name": profile.first_name,
                        "last_name": profile.last_name,
                        "email": profile.email,
                        "full_name": f"{profile.first_name} {profile.last_name}" if profile.first_name and profile.last_name else profile.first_name or profile.last_name or "Unknown"
                    }
                }
                # Add to employee list without any additional filtering
                employee_list.append(employee_data)
        
        return EmployeeToolResult(
            success=True,
                message=f"📋 Found {len(employee_list)} employees matching '{search_term}'. Please format this data to include ALL fields: Employee Number, Job Title, Department, Employment Type, Work Schedule, Hire Date, Rate, and Email address from the profile data.",
            data={
                "employees": employee_list,
                "count": len(employee_list),
                "search_term": search_term
            }
        )
        
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to search employees: {str(e)}"
        )

@cached_employee_operation(cache_ttl=300, invalidate_on_update=True, track_performance=True)
async def get_employee_details_tool(employee_id: int) -> EmployeeToolResult:
    """Tool for getting detailed employee information"""
    try:
        # Always create a fresh database session to avoid session closure issues
        async with get_ai_db() as session:
        
        # Find employee by ID
            check_employee = await session.execute(select(Employee).filter(Employee.employee_id == employee_id))
            employee = check_employee.scalar_one_or_none()
            
            if not employee:
                return EmployeeToolResult(
                success=False,
                message=f"❌ Employee with ID {employee_id} not found."
            )
        
        # Get profile information
            check_profile = await session.execute(select(User).filter(User.user_id == employee.profile_id))
            profile = check_profile.scalar_one_or_none()
        
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
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to get employee details: {str(e)}"
        )


@cached_search_operation(cache_ttl=300, track_performance=True)
async def get_all_employees_tool() -> EmployeeToolResult:
    """Tool for getting all employees with basic information"""
    try:
        # Always create a fresh database session to avoid session closure issues
        async with get_ai_db() as session:
        
        # Get all employees with profile information
            check_employees = await session.execute(select(Employee).join(User, Employee.profile_id == User.user_id))
            employees = check_employees.scalars().all()
            
            # Step 1: Get all profile IDs that we need
            profile_ids = [emp.profile_id for emp in employees if emp.profile_id]

            # Step 2: Fetch all profiles in one query
            profiles_result = await session.execute(
                select(User).filter(User.user_id.in_(profile_ids))
            )
            profiles_dict = {profile.user_id: profile for profile in profiles_result.scalars().all()}

            # Step 3: Build employee list using the profiles dictionary
            employee_list = []
            for emp in employees:
                profile = profiles_dict.get(emp.profile_id)
            
            employee_list.append({
                "employee_id": emp.employee_id,
                    "profile_id": str(emp.profile_id),  # Keep for internal operations
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
        
        return EmployeeToolResult(
            success=True,
            message=f"📋 Found {len(employee_list)} employees in the system",
            data={
                "employees": employee_list,
                "count": len(employee_list)
            }
        )
        
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to get all employees: {str(e)}"
        )


@cached_employee_operation(cache_ttl=300, invalidate_on_update=True, track_performance=True)
async def delete_employee_tool(params: DeleteEmployeeParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for deleting an employee record"""
    try:
        async with get_ai_db() as session:
            # Extract user_id from context
            if not context or 'user_id' not in context:
                return EmployeeToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # Find employee by ID, profile_id, or employee_number
            employee = None
            if params.employee_id:
                result = await session.execute(select(Employee).filter(Employee.employee_id == params.employee_id))
                employee = result.scalar_one_or_none()
            elif params.profile_id:
                result = await session.execute(select(Employee).filter(Employee.profile_id == params.profile_id))
                employee = result.scalar_one_or_none()
            elif params.employee_number:
                result = await session.execute(select(Employee).filter(Employee.employee_number == params.employee_number))
                employee = result.scalar_one_or_none()
            elif params.employee_name:
                # Search for employee by name through profile lookup
                cleaned_name = params.employee_name.strip()
                
                # Search for profiles matching the name
                name_conditions = [
                    User.first_name.ilike(f"%{cleaned_name}%"),
                    User.last_name.ilike(f"%{cleaned_name}%")
                ]
                
                # Handle full name search
                if ' ' in cleaned_name:
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        name_conditions.extend([
                            and_(
                                User.first_name.ilike(f"%{name_parts[0]}%"),
                                User.last_name.ilike(f"%{name_parts[-1]}%")
                            )
                        ])
                
                profile_result = await session.execute(select(User).filter(or_(*name_conditions)))
                profiles = profile_result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee found with name '{params.employee_name}'."
                    )
                
                if len(profiles) > 1:
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple employees found with name '{params.employee_name}': {', '.join(profile_names)}. Please be more specific or use employee ID."
                    )
                
                # Find employee record for the matched profile
                profile_id = str(profiles[0].user_id)
                result = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
                employee = result.scalar_one_or_none()
                
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Profile found for '{params.employee_name}' but no employee record exists."
                    )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either employee_id, profile_id, employee_number, or employee_name must be provided for deletion."
                )
            
            # Check if employee was found
            if not employee:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Employee not found."
                )
            
            # Store employee details for response
            employee_name = "Unknown"
            if hasattr(employee, 'profile') and employee.profile:
                employee_name = f"{employee.profile.first_name} {employee.profile.last_name}"
            
            # Delete the employee record
            await session.delete(employee)
            await session.commit()
            
            return EmployeeToolResult(
                success=True,
                message=f"✅ Employee '{employee_name}' (ID: {employee.employee_id}) has been successfully deleted.",
                data={
                    "employee_id": employee.employee_id,
                    "employee_name": employee_name,
                    "deleted_at": datetime.utcnow().isoformat()
                }
            )
                    
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to delete employee: {str(e)}"
        )


# Add these new parameter classes after the existing parameter classes (around line 85):

class UploadEmployeeDocumentParams(BaseModel):
    """Parameters for uploading employee documents with file data"""
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    document_type: str  # "nda" or "contract"
    file_data: str  # Base64 encoded file content
    filename: str
    file_size: int
    mime_type: str

class DeleteEmployeeDocumentParams(BaseModel):
    """Parameters for deleting employee documents"""
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    document_type: str  # "nda" or "contract"

class GetEmployeeDocumentParams(BaseModel):
    """Parameters for getting employee document information"""
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    document_type: str  # "nda" or "contract"

# Add these new tool functions at the end of the file (before the last function):
@cached_employee_operation(cache_ttl=300, invalidate_on_update=True, track_performance=True)
async def upload_employee_document_tool(params: UploadEmployeeDocumentParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for uploading NDA or contract documents for employees with file handling"""
    try:
        print(f"🔍 DEBUG: upload_employee_document_tool called with employee_name='{params.employee_name}', document_type='{params.document_type}'")
        print(f"🔍 DEBUG: Tool params: {params}")
        # Add this right after the function starts, around line 1458:
        print(f"🔍 DEBUG: File_data type: {type(params.file_data)}")
        print(f"🔍 DEBUG: File_data length: {len(params.file_data)}")   
        
        # Validate that employee_name is not a filename (common error pattern)
        if params.employee_name and ('.' in params.employee_name and len(params.employee_name.split('.')) == 2):
            # This looks like a filename (e.g., "PRD.docx")
            file_extensions = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg']
            if any(params.employee_name.lower().endswith(ext) for ext in file_extensions):
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Error: '{params.employee_name}' appears to be a filename, not an employee name. Please extract the actual employee name from the user's message. For example, if the user said 'this nda document is for employee Steve York', the employee name should be 'Steve York', not the filename."
                )
        
        async with get_ai_db() as session:
            # Extract user_id from context
            if not context or 'user_id' not in context:
                return EmployeeToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # Find employee by ID or name with proper error handling to prevent recursion
            employee = None
            if params.employee_id:
                result = await session.execute(select(Employee).filter(Employee.employee_id == params.employee_id))
                employee = result.scalar_one_or_none()
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee found with ID {params.employee_id}. Please check the employee ID and try again."
                    )
            elif params.employee_name:
                # Search for employee by name through profile lookup
                cleaned_name = params.employee_name.strip()
                name_conditions = [
                    User.first_name.ilike(f"%{cleaned_name}%"),
                    User.last_name.ilike(f"%{cleaned_name}%")
                ]
                
                if ' ' in cleaned_name:
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        name_conditions.extend([
                            and_(
                                User.first_name.ilike(f"%{name_parts[0]}%"),
                                User.last_name.ilike(f"%{name_parts[-1]}%")
                            )
                        ])
                
                profile_result = await session.execute(select(User).filter(or_(*name_conditions)))
                profiles = profile_result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee found with name '{params.employee_name}'. Please check the employee name and ensure they have a profile in the system."
                    )
                
                if len(profiles) > 1:
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple employees found with name '{params.employee_name}': {', '.join(profile_names)}. Please be more specific with the employee name."
                    )
                
                # Find employee record for the matched profile
                profile_id = str(profiles[0].user_id)
                result = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
                employee = result.scalar_one_or_none()
                
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee record found for '{params.employee_name}'. The profile exists but no employee record has been created. Please create an employee record first."
                    )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either employee_id or employee_name must be provided for document upload."
                )
            
            # Final check to ensure employee was found (prevents recursion)
            if not employee:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Employee not found. Please verify the employee information and try again."
                )
            
            # Handle file upload if file_data is provided
            if params.file_data:
                
                storage_service = SupabaseStorageService()
                
                # Validate and decode base64 file data
                try:
                    # Check if file_data is a valid base64 string
                    if not params.file_data or len(params.file_data) < 10:
                        return EmployeeToolResult(
                            success=False,
                            message="❌ File data is empty or too short. Please ensure the file was properly uploaded."
                        )
                    
                    # Remove any data URL prefix if present (e.g., "data:application/pdf;base64,")
                    file_data_clean = params.file_data
                    if file_data_clean.startswith('data:'):
                        # Split on comma and take the base64 part
                        parts = file_data_clean.split(',', 1)
                        if len(parts) == 2:
                            file_data_clean = parts[1]
                        else:
                            return EmployeeToolResult(
                                success=False,
                                message="❌ Invalid data URL format in file data."
                            )
                    
                    # Clean up base64 string - remove all whitespace and newlines
                    file_data_clean = ''.join(file_data_clean.split())
                    
                    # Enhanced validation and debugging
                    print(f"🔍 DEBUG: File data length: {len(file_data_clean)}")
                    print(f"🔍 DEBUG: Expected file size: {params.file_size}")
                    
                    # Validate base64 string length and characters
                    if len(file_data_clean) < 4:
                        return EmployeeToolResult(
                            success=False,
                            message="❌ Base64 data too short. Please ensure the complete file data is provided."
                        )
                    
                    # Check for valid base64 characters
                    
                    valid_chars = string.ascii_letters + string.digits + '+/='
                    invalid_chars = [c for c in file_data_clean if c not in valid_chars]
                    if invalid_chars:
                        print(f"🔍 DEBUG: Invalid base64 characters found: {set(invalid_chars)}")
                        # Try to clean the string
                        file_data_clean = ''.join(c for c in file_data_clean if c in valid_chars)
                        print(f"🔍 DEBUG: Cleaned data length: {len(file_data_clean)}")
                    
                    # Add proper padding if missing
                    missing_padding = len(file_data_clean) % 4
                    if missing_padding:
                        file_data_clean += '=' * (4 - missing_padding)
                        print(f"🔍 DEBUG: Added {4 - missing_padding} padding characters")
                    
                    # Try multiple decoding approaches
                    file_content = None
                    decode_attempts = [
                        ("Standard base64 without validation", lambda: base64.b64decode(file_data_clean, validate=False)),
                        ("URL-safe base64", lambda: base64.urlsafe_b64decode(file_data_clean)),
                        ("Standard base64 with validation", lambda: base64.b64decode(file_data_clean, validate=True)),
                    ]
                    
                    for attempt_name, decode_func in decode_attempts:
                        try:
                            print(f"🔍 DEBUG: Trying {attempt_name} decoding...")
                            file_content = decode_func()
                            print(f"🔍 DEBUG: {attempt_name} decoding successful! Decoded {len(file_content)} bytes")
                            break
                        except Exception as e:
                            print(f"🔍 DEBUG: {attempt_name} failed: {str(e)}")
                            continue
                    
                    if file_content is None:
                        return EmployeeToolResult(
                            success=False,
                            message="❌ Failed to decode base64 data with all attempted methods. Please ensure the file data is properly base64 encoded."
                        )
                    
                    # Validate file size matches
                    if len(file_content) != params.file_size:
                        print(f"🔍 DEBUG: File size mismatch - decoded: {len(file_content)}, expected: {params.file_size}")
                        # Don't fail on size mismatch, just log it as the frontend might calculate differently
                    
                    print(f"🔍 DEBUG: Successfully decoded {len(file_content)} bytes of file data")
                    
                except Exception as e:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Failed to decode file data: {str(e)}. Please ensure the file is properly base64 encoded."
                    )
                
                # Create a temporary file-like object
                file_obj = BytesIO(file_content)
                file_obj.name = params.filename
                
                # Upload to storage
                if params.document_type == "nda":
                    upload_result = await storage_service.upload_employee_nda_document(file_obj, employee.employee_id)
                elif params.document_type == "contract":
                    upload_result = await storage_service.upload_employee_contract_document(file_obj, employee.employee_id)
                else:
                    return EmployeeToolResult(
                        success=False,
                        message="❌ Invalid document type. Must be 'nda' or 'contract'."
                    )
                
                if not upload_result["success"]:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Failed to upload {params.document_type} document to storage"
                    )
                
                # Update employee record with upload result
                file_path = upload_result["file_path"]
                file_size = upload_result["file_size"]
                uploaded_at = upload_result["uploaded_at"]
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ No file data provided for upload"
                )
            
            # Update employee record with document metadata
            if params.document_type == "nda":
                employee.nda_document_bucket_name = "employee-nda-documents"
                employee.nda_document_file_size = file_size
                employee.nda_document_mime_type = params.mime_type
                employee.nda_document_uploaded_at = uploaded_at
                employee.nda_file_link = file_path  # Keep legacy field
                # Update new metadata fields
                employee.nda_document_filename = params.filename
                employee.nda_document_file_path = file_path
            elif params.document_type == "contract":
                employee.contract_document_bucket_name = "employee-contract-documents"
                employee.contract_document_file_size = file_size
                employee.contract_document_mime_type = params.mime_type
                employee.contract_document_uploaded_at = uploaded_at
                employee.contract_file_link = file_path  # Keep legacy field
                # Update new metadata fields
                employee.contract_document_filename = params.filename
                employee.contract_document_file_path = file_path
            
            employee.updated_by = user_id
            employee.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(employee)
            
            # Get employee name for response
            profile_result = await session.execute(select(User).filter(User.user_id == employee.profile_id))
            profile = profile_result.scalar_one_or_none()
            employee_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
            
            # Get download URL
            download_url = ""
            if params.document_type == "nda":
                download_url = storage_service.get_employee_nda_document_url(file_path)
            elif params.document_type == "contract":
                download_url = storage_service.get_employee_contract_document_url(file_path)
            
            return EmployeeToolResult(
                success=True,
                message=f"✅ {params.document_type.upper()} document uploaded successfully for {employee_name}\n📄 File: [{params.filename}]({download_url}) ({format_file_size(file_size)})",
                data={
                    "employee_id": employee.employee_id,
                    "employee_name": employee_name,
                    "document_type": params.document_type,
                    "filename": params.filename,
                    "file_path": file_path,
                    "file_size": file_size,
                    "mime_type": params.mime_type,
                    "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
                    "download_url": download_url
                }
            )
            
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to upload {params.document_type} document: {str(e)}"
        )

@cached_employee_operation(cache_ttl=300, invalidate_on_update=True, track_performance=True)
async def delete_employee_document_tool(params: DeleteEmployeeDocumentParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for deleting NDA or contract documents for employees"""
    try:
        async with get_ai_db() as session:
            # Extract user_id from context
            if not context or 'user_id' not in context:
                return EmployeeToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            # Find employee by ID or name (same logic as upload)
            employee = None
            if params.employee_id:
                result = await session.execute(select(Employee).filter(Employee.employee_id == params.employee_id))
                employee = result.scalar_one_or_none()
            elif params.employee_name:
                # Search for employee by name through profile lookup
                cleaned_name = params.employee_name.strip()
                name_conditions = [
                    User.first_name.ilike(f"%{cleaned_name}%"),
                    User.last_name.ilike(f"%{cleaned_name}%")
                ]
                
                if ' ' in cleaned_name:
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        name_conditions.extend([
                            and_(
                                User.first_name.ilike(f"%{name_parts[0]}%"),
                                User.last_name.ilike(f"%{name_parts[-1]}%")
                            )
                        ])
                
                profile_result = await session.execute(select(User).filter(or_(*name_conditions)))
                profiles = profile_result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee found with name '{params.employee_name}'."
                    )
                
                if len(profiles) > 1:
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple employees found with name '{params.employee_name}': {', '.join(profile_names)}. Please be more specific."
                    )
                
                # Find employee record for the matched profile
                profile_id = str(profiles[0].user_id)
                result = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
                employee = result.scalar_one_or_none()
                
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee record found for '{params.employee_name}'. The profile exists but no employee record has been created."
                    )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either employee_id or employee_name must be provided."
                )
            
            if not employee:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Employee not found."
                )
            
            # Check if document exists
            if params.document_type == "nda" and not employee.nda_file_link:
                return EmployeeToolResult(
                    success=False,
                    message="❌ No NDA document found for this employee."
                )
            elif params.document_type == "contract" and not employee.contract_file_link:
                return EmployeeToolResult(
                    success=False,
                    message="❌ No contract document found for this employee."
                )
            
            # Delete from storage
            storage_service = SupabaseStorageService()
            
            file_path = employee.nda_file_link if params.document_type == "nda" else employee.contract_file_link
            delete_success = False
            
            if params.document_type == "nda":
                delete_success = await storage_service.delete_employee_nda_document(file_path)
            elif params.document_type == "contract":
                delete_success = await storage_service.delete_employee_contract_document(file_path)
            
            if not delete_success:
                return EmployeeToolResult(
                    success=False,
                    message=f"❌ Failed to delete {params.document_type} document from storage"
                )
            
            # Clear document fields
            if params.document_type == "nda":
                employee.nda_file_link = None
                employee.nda_document_bucket_name = None
                employee.nda_document_file_size = None
                employee.nda_document_mime_type = None
                employee.nda_document_uploaded_at = None
                employee.nda_ocr_extracted_data = None
                # Clear new metadata fields
                employee.nda_document_filename = None
                employee.nda_document_file_path = None
            elif params.document_type == "contract":
                employee.contract_file_link = None
                employee.contract_document_bucket_name = None
                employee.contract_document_file_size = None
                employee.contract_document_mime_type = None
                employee.contract_document_uploaded_at = None
                employee.contract_ocr_extracted_data = None
                # Clear new metadata fields
                employee.contract_document_filename = None
                employee.contract_document_file_path = None
            
            employee.updated_by = user_id
            employee.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Get employee name for response
            profile_result = await session.execute(select(User).filter(User.user_id == employee.profile_id))
            profile = profile_result.scalar_one_or_none()
            employee_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
            
            return EmployeeToolResult(
                success=True,
                message=f"✅ {params.document_type.upper()} document deleted successfully for {employee_name}",
                data={
                    "employee_id": employee.employee_id,
                    "employee_name": employee_name,
                    "document_type": params.document_type,
                    "deleted_at": datetime.utcnow().isoformat()
                }
            )
            
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to delete {params.document_type} document: {str(e)}"
        )

@cached_employee_operation(cache_ttl=300, track_performance=True)
async def get_employee_document_tool(params: GetEmployeeDocumentParams, context: Dict[str, Any] = None) -> EmployeeToolResult:
    """Tool for retrieving document information and download URLs for employees"""
    try:
        async with get_ai_db() as session:
            # Find employee by ID or name (same logic as upload)
            employee = None
            if params.employee_id:
                result = await session.execute(select(Employee).filter(Employee.employee_id == params.employee_id))
                employee = result.scalar_one_or_none()
            elif params.employee_name:
                # Search for employee by name through profile lookup
                cleaned_name = params.employee_name.strip()
                name_conditions = [
                    User.first_name.ilike(f"%{cleaned_name}%"),
                    User.last_name.ilike(f"%{cleaned_name}%")
                ]
                
                if ' ' in cleaned_name:
                    name_parts = cleaned_name.split()
                    if len(name_parts) >= 2:
                        name_conditions.extend([
                            and_(
                                User.first_name.ilike(f"%{name_parts[0]}%"),
                                User.last_name.ilike(f"%{name_parts[-1]}%")
                            )
                        ])
                
                profile_result = await session.execute(select(User).filter(or_(*name_conditions)))
                profiles = profile_result.scalars().all()
                
                if not profiles:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee found with name '{params.employee_name}'."
                    )
                
                if len(profiles) > 1:
                    profile_names = [f"{p.first_name} {p.last_name} ({p.email})" for p in profiles]
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ Multiple employees found with name '{params.employee_name}': {', '.join(profile_names)}. Please be more specific."
                    )
                
                # Find employee record for the matched profile
                profile_id = str(profiles[0].user_id)
                result = await session.execute(select(Employee).filter(Employee.profile_id == profile_id))
                employee = result.scalar_one_or_none()
                
                if not employee:
                    return EmployeeToolResult(
                        success=False,
                        message=f"❌ No employee record found for '{params.employee_name}'. The profile exists but no employee record has been created."
                    )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Either employee_id or employee_name must be provided."
                )
            
            if not employee:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Employee not found."
                )
            
            # Get employee name
            profile_result = await session.execute(select(User).filter(User.user_id == employee.profile_id))
            profile = profile_result.scalar_one_or_none()
            employee_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
            
            # Check if document exists and build response
            storage_service = SupabaseStorageService()
            if params.document_type == "nda":
                if not employee.nda_file_link:
                    return EmployeeToolResult(
                        success=True,
                        message=f"❌ No NDA document found for {employee_name}",
                        data={
                            "employee_id": employee.employee_id,
                            "employee_name": employee_name,
                            "document_type": "nda",
                            "has_document": False
                        }
                    )
                
                download_url = storage_service.get_employee_nda_document_url(employee.nda_file_link)
                
                return EmployeeToolResult(
                    success=True,
                    message=f"✅ NDA document information retrieved for {employee_name}",
                    data={
                        "employee_id": employee.employee_id,
                        "employee_name": employee_name,
                        "document_type": "nda",
                        "has_document": True,
                        "filename": employee.nda_document_mime_type.split('/')[-1] if employee.nda_document_mime_type else "nda_document",
                        "file_path": employee.nda_file_link,
                        "file_size": employee.nda_document_file_size,
                        "mime_type": employee.nda_document_mime_type,
                        "uploaded_at": employee.nda_document_uploaded_at,
                        "download_url": download_url,
                        "ocr_extracted_data": employee.nda_ocr_extracted_data
                    }
                )
                
            elif params.document_type == "contract":
                if not employee.contract_file_link:
                    return EmployeeToolResult(
                        success=True,
                        message=f"❌ No contract document found for {employee_name}",
                        data={
                            "employee_id": employee.employee_id,
                            "employee_name": employee_name,
                            "document_type": "contract",
                            "has_document": False
                        }
                    )
                
                download_url = storage_service.get_employee_contract_document_url(employee.contract_file_link)
                
                return EmployeeToolResult(
                    success=True,
                    message=f"✅ Contract document information retrieved for {employee_name}",
                    data={
                        "employee_id": employee.employee_id,
                        "employee_name": employee_name,
                        "document_type": "contract",
                        "has_document": True,
                        "filename": employee.contract_document_mime_type.split('/')[-1] if employee.contract_document_mime_type else "contract_document",
                        "file_path": employee.contract_file_link,
                        "file_size": employee.contract_document_file_size,
                        "mime_type": employee.contract_document_mime_type,
                        "uploaded_at": employee.contract_document_uploaded_at,
                        "download_url": download_url,
                        "ocr_extracted_data": employee.contract_ocr_extracted_data
                    }
                )
            else:
                return EmployeeToolResult(
                    success=False,
                    message="❌ Invalid document type. Must be 'nda' or 'contract'."
                )
            
    except Exception as e:
        return EmployeeToolResult(
            success=False,
            message=f"❌ Failed to get {params.document_type} document: {str(e)}"
        )
