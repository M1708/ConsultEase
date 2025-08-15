from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import date
from backend.src.database.core.database import get_db
from backend.src.database.core.models import Expense, Client
from backend.src.database.core.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseDocumentResponse
from backend.src.services.storage_service import SupabaseStorageService


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

@router.post("/{expense_id}/upload-document", response_model=ExpenseDocumentResponse)
async def upload_expense_document(
    expense_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a receipt/invoice document for an expense"""
    try:
        # Verify expense exists
        expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Validate file type (receipts can be images or PDFs)
        allowed_types = [
            'application/pdf',
            'image/jpeg', 
            'image/jpg',
            'image/png',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Only PDF, DOC, JPG, and PNG files are allowed"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Reset file pointer
        await file.seek(0)
        
        # Upload to Supabase Storage
        storage_service = SupabaseStorageService()
        upload_result = await storage_service.upload_expense_document(file, expense_id)
        
        if upload_result["success"]:
            # Update expense record with document info
            expense.document_filename = upload_result["filename"]
            expense.receipt_link = upload_result["file_path"]  # Use existing receipt_link field
            expense.document_bucket_name = "expense-documents"
            expense.document_file_size = upload_result["file_size"]
            expense.document_mime_type = upload_result["mime_type"]
            expense.document_uploaded_at = upload_result["uploaded_at"]
            expense.last_modified_by = "system"
            expense.last_modified_timestamp = func.now()
            expense.updated_by = "00000000-0000-0000-0000-000000000000"
            
            db.commit()
            db.refresh(expense)
            
            return ExpenseDocumentResponse(
                success=True,
                message=f"Document uploaded successfully for expense {expense_id}",
                document_filename=expense.document_filename,
                receipt_link=expense.receipt_link,
                file_size=expense.document_file_size,
                uploaded_at=expense.document_uploaded_at
            )
        else:
            raise HTTPException(status_code=500, detail="Upload failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/{expense_id}/document")
async def get_expense_document(expense_id: int, db: Session = Depends(get_db)):
    """Get expense document information and download URL"""
    try:
        expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        if not expense.receipt_link:
            raise HTTPException(status_code=404, detail="No document found for this expense")
        
        # Generate signed URL for secure access
        storage_service = SupabaseStorageService()
        signed_url = storage_service.get_expense_document_url(expense.receipt_link)
        
        return {
            "expense_id": expense_id,
            "document_filename": expense.document_filename,
            "file_size": expense.document_file_size,
            "mime_type": expense.document_mime_type,
            "uploaded_at": expense.document_uploaded_at,
            "download_url": signed_url,
            "expense_category": expense.expense_category,
            "amount": expense.amount,
            "date": expense.date
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.delete("/{expense_id}/document")
async def delete_expense_document(expense_id: int, db: Session = Depends(get_db)):
    """Delete expense document"""
    try:
        expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        if not expense.receipt_link:
            raise HTTPException(status_code=404, detail="No document found for this expense")
        
        # Delete from Supabase Storage
        storage_service = SupabaseStorageService()
        deleted = await storage_service.delete_expense_document(expense.receipt_link)
        
        if deleted:
            # Clear document fields in database
            expense.document_filename = None
            expense.receipt_link = None
            expense.document_file_size = None
            expense.document_mime_type = None
            expense.document_uploaded_at = None
            expense.ocr_extracted_data = None
            expense.ai_analysis_data = None
            expense.last_modified_by = "system"
            expense.last_modified_timestamp = func.now()
            expense.updated_by = "00000000-0000-0000-0000-000000000000"
            
            db.commit()
            
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document from storage")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/{expense_id}/analyze-document")
async def analyze_expense_document(expense_id: int, db: Session = Depends(get_db)):
    """Analyze uploaded expense document using OCR and AI"""
    try:
        expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        if not expense.receipt_link:
            raise HTTPException(status_code=404, detail="No document found for this expense")
        
        # TODO: Implement OCR and AI analysis
        # This is a placeholder for future OCR implementation
        
        # For now, return a mock analysis
        mock_analysis = {
            "vendor": "Sample Vendor",
            "amount": float(expense.amount) if expense.amount else 0.0,
            "date": str(expense.date),
            "category": expense.expense_category or "Unknown",
            "confidence": 0.85,
            "extracted_text": "Mock OCR extraction - implement actual OCR service",
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # Store analysis in database
        expense.ai_analysis_data = mock_analysis
        expense.last_modified_by = "system"
        expense.last_modified_timestamp = func.now()
        expense.updated_by = "00000000-0000-0000-0000-000000000000"
        
        db.commit()
        
        return {
            "message": "Document analysis completed",
            "expense_id": expense_id,
            "analysis": mock_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")