from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Contract, Client
from backend.src.database.core.schemas import ContractCreate, ContractUpdate, ContractResponse, ContractDocumentResponse
from backend.src.services.storage_service import SupabaseStorageService
from backend.src.auth.dependencies import get_current_user, AuthenticatedUser

router = APIRouter()

@router.post("/{contract_id}/upload-document", response_model=ContractDocumentResponse)
async def upload_contract_document(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload a document for a contract"""
    try:
        # Verify contract exists
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Validate file type
        allowed_types = ['application/pdf', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Only PDF and DOC files are allowed")
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Reset file pointer
        await file.seek(0)
        
        # Upload to Supabase Storage
        try:
            storage_service = SupabaseStorageService()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Storage service configuration error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize storage service: {str(e)}")
        
        upload_result = await storage_service.upload_contract_document(file, contract_id)
        
        # Add debug logging
        print(f"Upload result: {upload_result}")
        print(f"Upload result type: {type(upload_result)}")
        
        if upload_result.get("success"):
            # Update contract record with document info
            contract.document_filename = upload_result.get("filename")
            contract.document_file_path = upload_result.get("file_path")
            contract.document_bucket_name = "contract-documents"
            contract.document_file_size = upload_result.get("file_size")
            contract.document_mime_type = upload_result.get("mime_type")
            contract.document_uploaded_at = upload_result.get("uploaded_at")
            contract.updated_by = current_user.user_id
            
            db.commit()
            db.refresh(contract)
            
            return ContractDocumentResponse(
                success=True,
                message=f"Document uploaded successfully for contract {contract_id}",
                document_filename=contract.document_filename,
                document_file_path=contract.document_file_path,
                file_size=contract.document_file_size,
                uploaded_at=contract.document_uploaded_at
            )
        else:
            error_message = upload_result.get("error", "Unknown upload error")
            raise HTTPException(status_code=500, detail=f"Upload failed: {error_message}")
            
    except Exception as e:
        import traceback
        error_details = f"Upload failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_details)  # Log to console for debugging
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/{contract_id}/document")
async def get_contract_document(contract_id: int, db: Session = Depends(get_db)):
    """Get contract document information and download URL"""
    try:
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        if not contract.document_file_path:
            raise HTTPException(status_code=404, detail="No document found for this contract")
        
        # Generate signed URL for secure access
        storage_service = SupabaseStorageService()
        signed_url = storage_service.get_document_url(contract.document_file_path)
        
        return {
            "contract_id": contract_id,
            "document_filename": contract.document_filename,
            "file_size": contract.document_file_size,
            "mime_type": contract.document_mime_type,
            "uploaded_at": contract.document_uploaded_at,
            "download_url": signed_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.delete("/{contract_id}/document")
async def delete_contract_document(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete contract document"""
    try:
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        if not contract.document_file_path:
            raise HTTPException(status_code=404, detail="No document found for this contract")
        
        # Delete from Supabase Storage
        storage_service = SupabaseStorageService()
        deleted = await storage_service.delete_contract_document(contract.document_file_path)
        
        if deleted:
            # Clear document fields in database
            contract.document_filename = None
            contract.document_file_path = None
            contract.document_file_size = None
            contract.document_mime_type = None
            contract.document_uploaded_at = None
            contract.updated_by = current_user.user_id
            
            db.commit()
            
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document from storage")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/", response_model=ContractResponse)
def create_contract(
    contract: ContractCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new contract"""
    # Verify client exists
    client = db.query(Client).filter(Client.client_id == contract.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_contract = Contract(
        **contract.model_dump(),
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract

def create_contract_internal(contract: ContractCreate, db: Session, user_id: str) -> Contract:
    """Internal function to create contract (for use by AI agents and tools)"""
    # AI agents must provide the actual user_id from the authenticated session
    if not user_id:
        raise ValueError("user_id is required for AI agent operations")
    
    # Verify client exists
    client = db.query(Client).filter(Client.client_id == contract.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_contract = Contract(
        **contract.model_dump(),
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract

@router.get("/", response_model=List[ContractResponse])
def get_contracts(db: Session = Depends(get_db)):
    """Get all contracts"""
    return db.query(Contract).all()

@router.get("/client/{client_id}", response_model=List[ContractResponse])
def get_contracts_by_client(client_id: int, db: Session = Depends(get_db)):
    """Get all contracts for a specific client"""
    return db.query(Contract).filter(Contract.client_id == client_id).all()

@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    """Get a specific contract"""
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@router.put("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: int,
    contract_update: ContractCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a contract"""
    db_contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Update fields
    for field, value in contract_update.model_dump(exclude_unset=True).items():
        setattr(db_contract, field, value)
    
    # Set updated_by to current user
    db_contract.updated_by = current_user.user_id
    
    db.commit()
    db.refresh(db_contract)
    return db_contract

@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a contract"""
    db_contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db.delete(db_contract)
    db.commit()
    return {"message": "Contract deleted successfully"}

# Additional contract-specific endpoints
@router.get("/status/{status}", response_model=List[ContractResponse])
def get_contracts_by_status(status: str, db: Session = Depends(get_db)):
    """Get all contracts by status (draft, active, completed, terminated)"""
    return db.query(Contract).filter(Contract.status == status).all()

@router.get("/billing/upcoming", response_model=List[ContractResponse])
def get_upcoming_billing(db: Session = Depends(get_db)):
    """Get contracts with upcoming billing dates"""
    from datetime import date, timedelta
    
    # Get contracts with billing dates in the next 30 days
    upcoming_date = date.today() + timedelta(days=30)
    return db.query(Contract).filter(
        Contract.billing_prompt_next_date <= upcoming_date,
        Contract.billing_prompt_next_date >= date.today(),
        Contract.status == "active"
    ).all()

@router.patch("/{contract_id}/status")
def update_contract_status(
    contract_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update contract status specifically"""
    valid_statuses = ["draft", "active", "completed", "terminated"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    db_contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db_contract.status = status
    db_contract.updated_by = current_user.user_id
    
    # If terminating, set termination date
    if status == "terminated":
        from datetime import date
        db_contract.termination_date = date.today()
    
    db.commit()
    db.refresh(db_contract)
    return {"message": f"Contract status updated to {status}", "contract": db_contract}
