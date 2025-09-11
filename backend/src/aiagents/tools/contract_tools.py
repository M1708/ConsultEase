from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from src.database.core.database import get_db
from src.database.core.models import Client, Contract, ClientContact
from src.database.core.schemas import ClientCreate, ContractCreate, ClientContactCreate
from src.database.api.clients import create_client_internal, get_client_by_name
from src.database.api.contracts import create_contract_internal
from src.database.api.client_contacts import create_client_contact
from src.database.core.database import get_ai_db
import re
from datetime import datetime

class CreateClientParams(BaseModel):
    client_name: str
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None

class ContractToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False

class SmartContractParams(BaseModel):
    client_name: str
    contract_type: str  # "Fixed", "Hourly", "Retainer"
    original_amount: Optional[Decimal] = None
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None
    billing_frequency: Optional[str] = None  # "Monthly", "Weekly", "One-time"
    notes: Optional[str] = None

class ContractDocumentParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None  # If not provided, will find latest contract for client
    document_action: str  # "upload" or "update"

class UpdateContractParams(BaseModel):
    client_name: str
    contract_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_type: Optional[str] = None
    original_amount: Optional[float] = None
    billing_frequency: Optional[str] = None
    billing_prompt_next_date: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

async def update_contract_tool(params: UpdateContractParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for updating existing contracts by client name"""
    try:
        async with get_ai_db() as session:
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found."
                )
            
            contract = None
            if params.contract_id:
                contract_result = await session.execute(select(Contract).filter(
                    Contract.contract_id == params.contract_id,
                    Contract.client_id == client.client_id
                ))
                contract = contract_result.scalar_one_or_none()
            else:
                result = await session.execute(select(Contract)
                                                .filter(Contract.client_id == client.client_id)
                                                .order_by(Contract.created_at.desc()))
                contract = result.scalar_one_or_none()
            
            if not contract:
                return ContractToolResult(
                    success=False,
                    message=f"❌ No contracts found for client '{client.client_name}'."
                )
            
            update_fields = []
            if params.start_date:
                try:
                    contract.start_date = datetime.strptime(params.start_date, "%Y-%m-%d").date()
                    update_fields.append("start_date")
                except ValueError:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Invalid start date format. Please use YYYY-MM-DD format."
                    )
            
            if params.end_date:
                try:
                    contract.end_date = datetime.strptime(params.end_date, "%Y-%m-%d").date()
                    update_fields.append("end_date")
                except ValueError:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Invalid end date format. Please use YYYY-MM-DD format."
                    )
            
            if params.contract_type:
                contract.contract_type = params.contract_type
                update_fields.append("contract_type")
            
            if params.original_amount is not None:
                contract.original_amount = params.original_amount
                update_fields.append("original_amount")
            
            if params.billing_frequency:
                contract.billing_frequency = params.billing_frequency
                update_fields.append("billing_frequency")
            
            if params.billing_prompt_next_date:
                try:
                    contract.billing_prompt_next_date = datetime.strptime(params.billing_prompt_next_date, "%Y-%m-%d").date()
                    update_fields.append("billing_prompt_next_date")
                except ValueError:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Invalid billing prompt date format. Please use YYYY-MM-DD format."
                    )
            
            if params.status:
                contract.status = params.status
                update_fields.append("status")
            
            if params.notes:
                contract.notes = params.notes
                update_fields.append("notes")
            
            contract.updated_by = user_id
            contract.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(contract)
            
            return ContractToolResult(
                success=True,
                message=f"✅ Successfully updated contract for '{client.client_name}'. Updated fields: {', '.join(update_fields)}",
                data={
                    "contract_id": contract.contract_id,
                    "client_name": client.client_name,
                    "updated_fields": update_fields,
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to update contract for {params.client_name}: {str(e)}"
        )
    

async def smart_contract_document_tool(params: ContractDocumentParams) -> ContractToolResult:
    """Smart tool for handling contract documents by client name"""
    try:
        async with get_ai_db() as session:
            contract = None
            
            if params.contract_id:
                # Use specific contract ID
                result = await session.execute(select(Contract).filter(Contract.contract_id == params.contract_id))
                contract = result.scalar_one_or_none()
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Contract with ID {params.contract_id} not found."
                    )
            else:
                # Find client and their latest contract
                client = get_client_by_name(params.client_name, session)
                if not client:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ Client '{params.client_name}' not found."
                    )
                
                # Get the most recent contract for this client
                contract_temp = await session.execute(select(Contract).filter(
                    Contract.client_id == client.client_id
                ).order_by(Contract.created_at.desc()))
                contract = contract_temp.scalar_one_or_none()
                
                if not contract:
                    return ContractToolResult(
                        success=False,
                        message=f"❌ No contracts found for client '{client.client_name}'. Please create a contract first."
                    )
            
            # Return contract information and instructions for document upload
            return ContractToolResult(
                success=True,
                message=f"✅ Found contract {contract.contract_id} for client '{contract.client.client_name}'. To upload a document, use the file upload endpoint: POST /contracts/{contract.contract_id}/upload-document",
                data={
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "has_document": bool(contract.document_filename),
                    "document_filename": contract.document_filename,
                    "upload_endpoint": f"/contracts/{contract.contract_id}/upload-document"
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to process contract document: {str(e)}"
        )
    

async def smart_create_contract_tool(params: SmartContractParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Smart tool for creating contracts by client name instead of client_id"""
    try:
        async with get_ai_db() as session:
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            
            user_id = context['user_id']
            
            client = await get_client_by_name(params.client_name, session)
            if not client:
                return ContractToolResult(
                    success=False,
                    message=f"❌ Client '{params.client_name}' not found. Please create the client first."
                )
            
            start_date_obj = None
            end_date_obj = None
            
            if params.start_date:
                try:
                    start_date_obj = date.fromisoformat(params.start_date)
                except ValueError:
                    start_date_obj = date.today()
            
            if params.end_date:
                try:
                    end_date_obj = date.fromisoformat(params.end_date)
                except ValueError:
                    pass
            
            contract_data = ContractCreate(
                client_id=client.client_id,
                contract_type=params.contract_type,
                start_date=start_date_obj,
                end_date=end_date_obj,
                original_amount=params.original_amount,
                current_amount=params.original_amount,
                billing_frequency=params.billing_frequency,
                status="draft",
                notes=params.notes
            )
            
            result = create_contract_internal(contract_data, session, user_id)
            
            return ContractToolResult(
                success=True,
                message=f"✅ Contract created successfully for client '{client.client_name}' (Contract ID: {result.contract_id})",
                data={
                    "contract_id": result.contract_id,
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "contract_type": result.contract_type,
                    "status": result.status,
                    "original_amount": float(result.original_amount) if result.original_amount else None
                }
            )
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to create contract: {str(e)}"
        )
    

async def create_client_tool(params: CreateClientParams, context: Dict[str, Any] = None) -> ContractToolResult:
    """Tool for creating new clients"""
    
    try:
        async with get_ai_db() as session:
            client_data = ClientCreate(**params.model_dump())
            if not context or 'user_id' not in context:
                return ContractToolResult(
                    success=False,
                    message="❌ User context not available. Please ensure you're authenticated."
                )
            user_id = context['user_id']
            result = create_client_internal(client_data, session, user_id)
            return ContractToolResult(
                success=True,
                message=f"✅ Successfully created client: {result.client_name}",
                data={
                    "client_id": result.client_id,
                    "client_name": result.client_name,
                    "industry": result.industry
                }
            )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to create client: {str(e)}"
        )

async def search_clients_tool(search_term: Optional[str] = None, limit: int = 10) -> ContractToolResult:
    """Tool for searching existing clients"""
    try:
        async with get_ai_db() as session:
            query = select(Client)
            if search_term:
                query = query.filter(
                    Client.client_name.ilike(f"%{search_term}%") |
                    Client.industry.ilike(f"%{search_term}%")
                )
            
            # Execute the query with limit
            result = await session.execute(query.limit(limit))
            clients = result.scalars().all()
            client_list = [
                {
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "notes": client.notes
                } for client in clients
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(client_list)} clients",
                data={"clients": client_list, "count": len(client_list)}
            )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to search clients: {str(e)}"
        )
    

async def get_contract_details_tool(contract_id: Optional[int] = None, client_name: Optional[str] = None) -> ContractToolResult:
    """Tool for getting detailed contract information"""
    try:
        async with get_ai_db() as session:
            if contract_id:
                result = await session.execute(select(Contract).filter(Contract.contract_id == contract_id))
                contract = result.scalar_one_or_none()
            elif client_name:
                client = await get_client_by_name(client_name, session)
                if not client:
                    return ContractToolResult(success=False, message=f"❌ Client '{client_name}' not found.")
                
                result = await session.execute(
                    select(Contract)
                    .filter(Contract.client_id == client.client_id)
                    .order_by(Contract.created_at.desc())
                )
                contract = result.scalar_one_or_none()
            else:
                return ContractToolResult(success=False, message="❌ Please provide either contract_id or client_name.")

            if not contract:
                return ContractToolResult(success=False, message="❌ Contract not found for the specified criteria.")

            result = await session.execute(select(Client).filter(Client.client_id == contract.client_id))
            client = result.scalar_one_or_none()
            
            contract_details = {
                "contract_id": contract.contract_id,
                "client_name": client.client_name if client else "Unknown",
                "status": contract.status,
                "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
            }
            
            return ContractToolResult(
                success=True,
                message=f"✅ Found contract details for '{contract_details['client_name']}'",
                data={"contract": contract_details}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contract details: {str(e)}")
    

async def get_contracts_by_client_tool(client_name: str) -> ContractToolResult:
    """Tool for getting all contracts for a specific client by name"""
    try:
        async with get_ai_db() as session:
            client = get_client_by_name(client_name, session)
            if not client:
                return ContractToolResult(success=False, message=f"❌ Client '{client_name}' not found.")
            
            contracts_temp = await session.execute(select(Contract).filter(Contract.client_id == client.client_id))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else contract.original_amount,
                    "billing_frequency": contract.billing_frequency,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "termination_date": str(contract.termination_date) if contract.termination_date else None,
                    "notes": contract.notes,
                } for contract in contracts
            ]

            client_details = {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "industry": client.industry,
                "primary_contact_name": client.primary_contact_name,
                "primary_contact_email": client.primary_contact_email,
                "company_size": client.company_size,
                "notes": client.notes,
                "created_at": str(client.created_at) if client.created_at else None,
                "updated_at": str(client.updated_at) if client.updated_at else None
            }

            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts for client '{client.client_name}'",
                data={
                    "client": client_details,
                    "contracts": contract_list
                }
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts: {str(e)}")
    

async def get_all_contracts_tool() -> ContractToolResult:
    """Tool for getting all contracts across all clients"""
    try:
        async with get_ai_db() as session:
            contracts_temp = await session.execute(select(Contract).join(Client).order_by(Contract.created_at.desc()))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts across all clients",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get all contracts: {str(e)}")
 

async def get_contracts_by_status_tool(status: str) -> ContractToolResult:
    """Tool for getting contracts by status (e.g., 'active', 'ongoing', 'draft', 'terminated')"""

    try:
        async with get_ai_db() as session:
            if status.lower() in ['ongoing', 'active']:
                query_status = 'active'
            else:
                query_status = status
                
            contracts_temp = await session.execute(select(Contract).join(Client).filter(Contract.status.ilike(f'%{query_status}%')))
            contracts = contracts_temp.scalars().all()
            
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with status '{status}'",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts by status: {str(e)}")
    

async def get_contracts_with_null_billing_date_tool() -> ContractToolResult:
    """Tool for getting all contracts where the billing prompt date is null"""
    try:
        async with get_ai_db() as session:
            contracts_temp = await session.execute(select(Contract).join(Client).filter(Contract.billing_prompt_next_date.is_(None)))
            contracts = contracts_temp.scalars().all()
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                } for contract in contracts
            ]
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with a null billing prompt date.",
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts with null billing date: {str(e)}")
    

async def get_contracts_for_next_month_billing_tool(context: Dict[str, Any]) -> ContractToolResult:
    """Tool for getting contracts with a billing prompt date in the next month or later in the current month."""
    try:
        async with get_ai_db() as session:
            today = context.get('today', date.today())
            
            # Start of current month
            start_of_this_month = today.replace(day=1)
            
            # End of next month
            end_of_next_month = (start_of_this_month + relativedelta(months=2)) - timedelta(days=1)
            stmt = (
                    select(Contract)
                    .join(Client)
                    .where(
                        Contract.billing_prompt_next_date.isnot(None),
                        Contract.billing_prompt_next_date >= today,
                        Contract.billing_prompt_next_date <= end_of_next_month
                    )
                    .order_by(Contract.billing_prompt_next_date.asc())
    )
            contracts_temp = await session.execute(stmt)
            contracts = contracts_temp.scalars().all()
            # 🔧 ENHANCED OUTPUT: Added more contract details for better billing information
            # TODO: If this change doesn't fix the issue, revert to the original 3-field output
            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else contract.original_amount,
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date),
                    # 🔧 CLIENT CONTACT INFO: Added for billing communication
                    "primary_contact_name": contract.client.primary_contact_name,
                    "primary_contact_email": contract.client.primary_contact_email,
                } for contract in contracts
            ]
            
            null_billing_date_count = db.query(Contract).filter(Contract.billing_prompt_next_date.is_(None)).count()
            
            message = f"📋 Found {len(contract_list)} contracts with billing dates from {today.strftime('%Y-%m-%d')} to {end_of_next_month.strftime('%Y-%m-%d')}."
            if null_billing_date_count > 0:
                message += f" Additionally, {null_billing_date_count} contracts have no billing prompt date set."

            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to get contracts for next month's billing: {str(e)}")

class SearchContractsParams(BaseModel):
    client_name: Optional[str] = None
    status: Optional[str] = None
    billing_date_next_month: Optional[bool] = False
    billing_date_is_null: Optional[bool] = False
    # TODO: If contract search becomes slow or unreliable, revert these new search parameters
    billing_frequency: Optional[str] = None  # Monthly, Weekly, One-time
    contract_type: Optional[str] = None  # Fixed, Hourly, Retainer
    min_amount: Optional[float] = None  # Minimum contract amount
    max_amount: Optional[float] = None  # Maximum contract amount
    start_date_from: Optional[str] = None  # Filter contracts starting from this date (YYYY-MM-DD)
    start_date_to: Optional[str] = None  # Filter contracts starting before this date (YYYY-MM-DD)

async def search_contracts_tool(params: SearchContractsParams, context: Dict[str, Any]) -> ContractToolResult:
    """Flexible tool for searching contracts by client, status, or billing date."""
    # 🚀 PERFORMANCE OPTIMIZATION: Track contract search execution
    try:
        async with get_ai_db() as session:
        
            filters_applied = []

            stmt = select(Contract).join(Client)

            if params.client_name:
                stmt = stmt.where(Client.client_name.ilike(f"%{params.client_name}%"))
                filters_applied.append(f"client name matching '{params.client_name}'")

            if params.status:
                if params.status.lower() in ['ongoing', 'active']:
                    stmt = stmt.where(Contract.status.ilike('active'))
                    filters_applied.append("status is 'ongoing'")
                else:
                    stmt = stmt.where(Contract.status.ilike(f"%{params.status}%"))
                    filters_applied.append(f"status is '{params.status}'")

            if params.billing_date_next_month:
                today = context.get('today', date.today())
                end_of_next_month = (today.replace(day=1) + relativedelta(months=2)) - timedelta(days=1)
                stmt = stmt.where(
                    Contract.billing_prompt_next_date.isnot(None),
                    Contract.billing_prompt_next_date >= today,
                    Contract.billing_prompt_next_date <= end_of_next_month
                )
                filters_applied.append("billing date is in the next month or later this month")

            if params.billing_date_is_null:
                stmt = stmt.where(Contract.billing_prompt_next_date.is_(None))
                filters_applied.append("billing date is not set")

            if params.billing_frequency:
                stmt = stmt.where(Contract.billing_frequency.ilike(f"%{params.billing_frequency}%"))
                filters_applied.append(f"billing frequency is '{params.billing_frequency}'")

            if params.contract_type:
                stmt = stmt.where(Contract.contract_type.ilike(f"%{params.contract_type}%"))
                filters_applied.append(f"contract type is '{params.contract_type}'")

            if params.min_amount is not None:
                stmt = stmt.where(Contract.original_amount >= params.min_amount)
                filters_applied.append(f"amount >= ${params.min_amount:,.2f}")

            if params.max_amount is not None:
                stmt = stmt.where(Contract.original_amount <= params.max_amount)
                filters_applied.append(f"amount <= ${params.max_amount:,.2f}")

            if params.start_date_from:
                try:
                    start_date = datetime.strptime(params.start_date_from, "%Y-%m-%d").date()
                    stmt = stmt.where(Contract.start_date >= start_date)
                    filters_applied.append(f"start date >= {params.start_date_from}")
                except ValueError:
                    pass

            if params.start_date_to:
                try:
                    end_date = datetime.strptime(params.start_date_to, "%Y-%m-%d").date()
                    stmt = stmt.where(Contract.start_date <= end_date)
                    filters_applied.append(f"start date <= {params.start_date_to}")
                except ValueError:
                    pass

            stmt = stmt.order_by(Contract.created_at.desc())

            # Execute the statement
            result = await session.execute(stmt)
            contracts = result.scalars().all()

            contract_list = [
                {
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "status": contract.status,
                    "contract_type": contract.contract_type,
                    "billing_frequency": contract.billing_frequency,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else 'Not set',
                } for contract in contracts
            ]

            message = f"📋 Found {len(contract_list)} contracts"
            if filters_applied:
                message += " where " + " and ".join(filters_applied)
            message += "."

            if not params.billing_date_is_null:
                count_stmt = select(func.count()).select_from(Contract).where(
                    Contract.billing_prompt_next_date.is_(None)
                )
                count_result = await session.execute(count_stmt)
                null_billing_date_count = count_result.scalar()

                if null_billing_date_count > 0:
                    message += f" (Note: {null_billing_date_count} contracts have no billing prompt date set.)"

            return ContractToolResult(
                success=True,
                message=message,
                data={"contracts": contract_list, "count": len(contract_list)}
            )
    except Exception as e:
        return ContractToolResult(success=False, message=f"❌ Failed to search contracts: {str(e)}")
    

async def get_all_clients_tool() -> ContractToolResult:
    """Tool for getting all clients in the system with basic information"""
    try:
        # Get all clients
        async with get_ai_db() as session:
            stmt = select(Client).order_by(Client.client_name)
            result = await session.execute(stmt)
            clients = result.scalars().all()
                
            client_list = []
            for client in clients:
                client_list.append({
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "created_at": str(client.created_at) if client.created_at else None
                })
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(client_list)} clients in the system",
                data={
                    "clients": client_list,
                    "count": len(client_list),
                    "summary": {
                        "total_clients": len(client_list),
                        "industries": list(set(c["industry"] for c in client_list if c["industry"])),
                        "has_contacts": len([c for c in client_list if c["primary_contact_name"] or c["primary_contact_email"]])
                    }
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get all clients: {str(e)}"
        )

async def get_all_clients_with_contracts_tool() -> ContractToolResult:
    """Tool for getting all clients with their contracts - comprehensive view"""
    try:
        # Get all clients
        async with get_ai_db() as session:
            stmt = select(Client).order_by(Client.client_name)
            result = await session.execute(stmt)
            clients = result.scalars().all()
        
            clients_with_contracts = []
            total_contracts = 0
            
            for client in clients:
                # Get all contracts for this client
                contracts = await session.execute(select(Contract).filter(Contract.client_id == client.client_id))
                contracts = contracts.scalars().all()
                
                contract_list = []
                for contract in contracts:
                    contract_list.append({
                        "contract_id": contract.contract_id,
                        "contract_type": contract.contract_type,
                        "status": contract.status,
                        "original_amount": float(contract.original_amount) if contract.original_amount else None,
                        "current_amount": float(contract.current_amount) if contract.current_amount else None,
                        "billing_frequency": contract.billing_frequency,
                        "start_date": str(contract.start_date) if contract.start_date else None,
                        "end_date": str(contract.end_date) if contract.end_date else None,
                        "created_at": str(contract.created_at) if contract.created_at else None
                    })
                
                total_contracts += len(contract_list)
                
                clients_with_contracts.append({
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "created_at": str(client.created_at) if client.created_at else None,
                    "contracts": contract_list,
                    "contract_count": len(contract_list)
                })
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(clients_with_contracts)} clients with {total_contracts} total contracts",
                data={
                    "clients_with_contracts": clients_with_contracts,
                    "summary": {
                        "total_clients": len(clients_with_contracts),
                        "total_contracts": total_contracts,
                        "clients_with_contracts": len([c for c in clients_with_contracts if c["contract_count"] > 0]),
                        "clients_without_contracts": len([c for c in clients_with_contracts if c["contract_count"] == 0]),
                        "industries": list(set(c["industry"] for c in clients_with_contracts if c["industry"]))
                    }
                }
            )
            
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get clients with contracts: {str(e)}"
        )


async def analyze_contract_tool(contract_text: str) -> ContractToolResult:
    """Tool for analyzing contract content"""
    try:
        # Simple keyword-based analysis (placeholder for advanced AI analysis)
        analysis = {
            "contract_type": "Unknown",
            "key_terms": [],
            "amounts": [],
            "dates": [],
            "risks": [],
            "confidence": 0.7
        }
        
        # Basic keyword detection
        if "fixed price" in contract_text.lower():
            analysis["contract_type"] = "Fixed Price"
        elif "hourly" in contract_text.lower():
            analysis["contract_type"] = "Hourly"
        elif "retainer" in contract_text.lower():
            analysis["contract_type"] = "Retainer"
        
        # Extract potential amounts
        
        amounts = re.findall(r'\$[\d,]+\.?\d*', contract_text)
        analysis["amounts"] = amounts[:5]  # Limit to first 5 amounts
        
        return ContractToolResult(
            success=True,
            message="✅ Contract analysis completed",
            data={"analysis": analysis}
        )
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to analyze contract: {str(e)}"
        )

async def get_contracts_by_billing_date_tool(start_date: str, end_date: str) -> ContractToolResult:
    """Tool for getting contracts with billing prompt dates within a specific range"""
    
    try:
        async with get_ai_db() as session:
        
        # Parse the date range
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return ContractToolResult(
                    success=False,
                    message="❌ Invalid date format. Please use YYYY-MM-DD format."
                )
            
            # Get contracts with billing prompt dates in the specified range

            contracts_temp = await session.execute(select(Contract).join(Client).filter(
                Contract.billing_prompt_next_date.isnot(None),
                Contract.billing_prompt_next_date >= start_dt,
                Contract.billing_prompt_next_date <= end_dt
            ).order_by(Contract.billing_prompt_next_date.asc()))
            contracts = contracts_temp.scalars().all()


            contract_list = []
            for contract in contracts:
                contract_list.append({
                    "contract_id": contract.contract_id,
                    "client_name": contract.client.client_name,
                    "contract_type": contract.contract_type,
                    "status": contract.status,
                    "original_amount": float(contract.original_amount) if contract.original_amount else None,
                    "current_amount": float(contract.current_amount) if contract.current_amount else None,
                    "billing_frequency": contract.billing_frequency,
                    "billing_prompt_next_date": str(contract.billing_prompt_next_date) if contract.billing_prompt_next_date else None,
                    "termination_date": str(contract.termination_date) if contract.termination_date else None,
                    "amendments": contract.amendments,
                    "notes": contract.notes,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "end_date": str(contract.end_date) if contract.end_date else None,
                    "has_document": bool(contract.document_filename),
                    "document_filename": contract.document_filename
                })
            
            return ContractToolResult(
                success=True,
                message=f"📋 Found {len(contract_list)} contracts with billing prompt dates between {start_date} and {end_date}",
                data={
                    "contracts": contract_list,
                    "count": len(contract_list),
                    "date_range": {
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            )
        
    except Exception as e:
        return ContractToolResult(
            success=False,
            message=f"❌ Failed to get contracts by billing date: {str(e)}"
        )
    