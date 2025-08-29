from datetime import date, datetime
from decimal import Decimal
from src.database.core.models import TimeEntry
from src.database.core.schemas import TimeEntryCreate
from src.database.core.database import get_db
from src.database.api.time_entries import create_time_entry
from src.database.api.deliverables import get_deliverable_by_name, search_deliverables_with_client_info
from src.database.api.clients import get_client_by_name
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from  src.aiagents.tools.contract_tools import ContractToolResult


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

def create_time_entry_tool(params: CreateTimeEntryParams, db: Session = None) -> ContractToolResult:
    """Tool for creating time entries"""
    try:
        # Validate hours worked
        if params.hours_worked > 16:
            return ContractToolResult(
                success=False,
                message="⚠️ Hours worked exceeds 16 hours. Manager approval required.",
                requires_confirmation=True
            )
        
        if db is None:
            db = next(get_db())
        
        time_entry_data = TimeEntryCreate(**params.model_dump())
        result = create_time_entry(time_entry_data, db)
        
        return ContractToolResult(
            success=True,
            message=f"✅ Time entry logged: {params.hours_worked} hours",
            data={
                "time_entry_id": result.time_entry_id,
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

def get_timesheet_tool(employee_id: int, start_date: date, end_date: date, db: Session = None) -> ContractToolResult:
    """Tool for retrieving timesheet data"""
    try:
        if db is None:
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

def search_projects_tool(search_term: str, db: Session = None) -> ContractToolResult:
    """Tool for searching projects/deliverables by name"""
    try:
        if db is None:
            db = next(get_db())
        
        # Use the API function to search deliverables with client info
        projects = search_deliverables_with_client_info(search_term, db)
        
        return ContractToolResult(
            success=True,
            message=f"🔍 Found {len(projects)} projects matching '{search_term}'",
            data={
                "projects": projects,
                "count": len(projects)
            }
        )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to search projects: {str(e)}"
        )

class SmartTimeEntryParams(BaseModel):
    project_name: str
    hours_worked: Decimal
    description_of_work: str
    employee_id: int = 1  # Default employee
    date: Optional[str] = None  # Will default to today
    billable: bool = True

def smart_create_time_entry_tool(params: SmartTimeEntryParams, db: Session = None) -> ContractToolResult:
    """Smart tool for creating time entries by project name instead of technical IDs"""
    try:
        if db is None:
            db = next(get_db())
        
        # Validate hours worked
        if params.hours_worked > 16:
            return ContractToolResult(
                success=False,
                message="⚠️ Hours worked exceeds 16 hours. Manager approval required.",
                requires_confirmation=True
            )
        
        # Use the API function to find the project/deliverable by name
        deliverable = get_deliverable_by_name(params.project_name, db)
        
        if not deliverable:
            # Smart search: Check if we can find clients that match the project name
            from  src.database.core.models import Contract, Deliverable as DeliverableModel, Client
            
            # Search for multiple clients that might match (e.g., "Solana" → "Solana Inc", "Solana Corp")
            search_words = params.project_name.lower().split()
            matching_clients = []
            
            # Optimized search - use database LIKE query instead of loading all clients
            for word in search_words:
                search_pattern = f"%{word}%"
                word_clients = db.query(Client).filter(
                    Client.client_name.ilike(search_pattern)
                ).limit(5).all()
                matching_clients.extend(word_clients)
            
            if len(matching_clients) == 1:
                # Single client found - proceed with existing logic
                client = matching_clients[0]
                client_deliverables = db.query(DeliverableModel).join(Contract).filter(
                    Contract.client_id == client.client_id
                ).all()
                
                if client_deliverables:
                    # Client has projects - list them
                    project_names = [d.name for d in client_deliverables if d.name]
                    return ContractToolResult(
                        success=False,
                        message=f"✅ Found client '{client.client_name}' but no project named '{params.project_name}'. Available projects for {client.client_name}: {', '.join(project_names)}. Please specify which project you'd like to log time for."
                    )
                else:
                    # Client exists but has no projects
                    return ContractToolResult(
                        success=False,
                        message=f"✅ Found client '{client.client_name}' but they don't have any active projects/deliverables yet. Please create a project for this client first, or contact your project manager to set up deliverables for {client.client_name}."
                    )
            
            elif len(matching_clients) > 1:
                # Multiple clients found - ask user to clarify
                client_options = []
                for i, client in enumerate(matching_clients, 1):
                    # Check if client has projects
                    client_deliverables = db.query(DeliverableModel).join(Contract).filter(
                        Contract.client_id == client.client_id
                    ).all()
                    project_count = len(client_deliverables)
                    
                    client_info = f"{i}. **{client.client_name}**"
                    if client.industry:
                        client_info += f" (Industry: {client.industry})"
                    if project_count > 0:
                        client_info += f" - {project_count} active project(s)"
                    else:
                        client_info += " - No active projects"
                    
                    client_options.append(client_info)
                
                return ContractToolResult(
                    success=False,
                    message=f"🔍 Found multiple clients matching '{params.project_name}'. Please specify which client you meant:\n\n" + 
                           "\n".join(client_options) + 
                           f"\n\nPlease rephrase your request with the full client name (e.g., 'Log {params.hours_worked} hours for [Full Client Name] project')."
                )
            
            # No client match either - try to find similar projects
            similar_projects = search_deliverables_with_client_info(params.project_name.split()[0], db)
            
            if similar_projects:
                suggestions = []
                for p in similar_projects[:3]:  # Limit to 3 suggestions
                    suggestions.append(f"'{p['name']}' (Client: {p['client_name']})")
                
                return ContractToolResult(
                    success=False,
                    message=f"❌ Project '{params.project_name}' not found. Did you mean one of these: {', '.join(suggestions)}?"
                )
            else:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Project '{params.project_name}' not found. Please check the project name, verify the client exists, or create a new deliverable first."
                )
        
        # Parse date or use today
        entry_date = date.today()
        if params.date:
            try:
                entry_date = date.fromisoformat(params.date)
            except ValueError:
                entry_date = date.today()
        
        # Create time entry with resolved IDs using the existing API
        time_entry_params = CreateTimeEntryParams(
            employee_id=params.employee_id,
            contract_id=deliverable.contract_id,
            client_id=deliverable.contract.client_id,
            deliverable_id=deliverable.deliverable_id,
            date=entry_date,
            hours_worked=params.hours_worked,
            description_of_work=params.description_of_work,
            billable=params.billable
        )
        
        result = create_time_entry_tool(time_entry_params, db)
        
        if result.success:
            # Enhance the response with project context
            enhanced_data = result.data.copy()
            enhanced_data.update({
                "project_name": deliverable.name,
                "client_name": deliverable.contract.client.client_name,
                "contract_type": deliverable.contract.contract_type
            })
            
            return ContractToolResult(
                success=True,
                message=f"✅ Time logged successfully for project '{deliverable.name}' (Client: {deliverable.contract.client.client_name})",
                data=enhanced_data
            )
        else:
            return result
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to log time: {str(e)}"
        )
