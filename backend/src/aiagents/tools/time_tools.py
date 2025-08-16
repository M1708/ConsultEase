from datetime import date, datetime
from decimal import Decimal
from backend.src.database.core.models import TimeEntry
from backend.src.database.core.schemas import TimeEntryCreate
from pydantic import BaseModel
from typing import Optional
from backend.src.aiagents.tools.contract_tools import ContractToolResult


class CreateTimeEntryParams(BaseModel):
    employee_id: int
    contract_id: int
    client_id: int
    deliverable_id: Optional[int] = None
    date: date
    hours_worked: Decimal
    description_of_work: str
    billable: bool = True
    billing_rate: Optional[Decimal] = None

def create_time_entry_tool(params: CreateTimeEntryParams) -> ContractToolResult:
    """Tool for creating time entries"""
    try:
        # Validate hours worked
        if params.hours_worked > 16:
            return ContractToolResult(
                success=False,
                message="⚠️ Hours worked exceeds 16 hours. Manager approval required.",
                requires_confirmation=True
            )
        
        db = next(get_db())
        
        time_entry_data = TimeEntryCreate(**params.dict())
        # Use your existing time entry creation logic here
        
        return ContractToolResult(
            success=True,
            message=f"✅ Time entry logged: {params.hours_worked} hours",
            data={
                "hours": float(params.hours_worked),
                "date": str(params.date),
                "billable": params.billable
            }
        )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to log time: {str(e)}"
        )

def get_timesheet_tool(employee_id: int, start_date: date, end_date: date) -> ContractToolResult:
    """Tool for retrieving timesheet data"""
    try:
        db = next(get_db())
        
        time_entries = db.query(TimeEntry).filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.date >= start_date,
            TimeEntry.date <= end_date
        ).all()
        
        total_hours = sum(entry.hours_worked or 0 for entry in time_entries)
        billable_hours = sum(entry.hours_worked or 0 for entry in time_entries if entry.billable)
        
        return ContractToolResult(
            success=True,
            message=f"📊 Timesheet retrieved: {len(time_entries)} entries",
            data={
                "entries": len(time_entries),
                "total_hours": float(total_hours),
                "billable_hours": float(billable_hours),
                "period": f"{start_date} to {end_date}"
            }
        )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to retrieve timesheet: {str(e)}"
        )