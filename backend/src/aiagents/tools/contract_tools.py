from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Client, Contract, ClientContact
from backend.src.database.core.schemas import ClientCreate, ContractCreate, ClientContactCreate
from backend.src.database.api.clients import create_client
from backend.src.database.api.contracts import create_contract
from backend.src.database.api.client_contacts import create_client_contact

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

def create_client_tool(params: CreateClientParams) -> ContractToolResult:
    """Tool for creating new clients"""
    try:
        db = next(get_db())
        
        client_data = ClientCreate(**params.dict())
        result = create_client(client_data, db)
        
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

def search_clients_tool(search_term: Optional[str] = None, limit: int = 10) -> ContractToolResult:
    """Tool for searching existing clients"""
    try:
        db = next(get_db())
        
        query = db.query(Client)
        if search_term:
            search_lower = search_term.lower()
            query = query.filter(
                Client.client_name.ilike(f"%{search_term}%") |
                Client.industry.ilike(f"%{search_term}%")
            )
        
        clients = query.limit(limit).all()
        
        client_list = []
        for client in clients:
            client_list.append({
                "client_id": client.client_id,
                "client_name": client.client_name,
                "industry": client.industry,
                "primary_contact_name": client.primary_contact_name
            })
        
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

def analyze_contract_tool(contract_text: str) -> ContractToolResult:
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
        import re
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