from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from src.database.core.database import get_db
from src.database.core.models import Employee, User
from src.database.core.schemas import (
    EmployeeCreate, 
    EmployeeUpdate, 
    EmployeeResponse, 
    EmployeeDocumentUploadResponse,
    EmployeeDocumentInfo,
    EmployeeDocumentsResponse
)
from src.services.storage_service import SupabaseStorageService
from src.auth.dependencies import get_current_user, AuthenticatedUser
from sqlalchemy import select, or_, and_
from sqlalchemy.sql import func
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Employee Document Management Endpoints

@router.post("/{employee_id}/upload-nda", response_model=EmployeeDocumentUploadResponse)
async def upload_employee_nda(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload NDA document for employee with enhanced metadata tracking"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate file type
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/jpg',
            'image/png'
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Only PDF, DOC, DOCX, JPG, and PNG files are allowed for NDA documents"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Reset file pointer
        await file.seek(0)
        
        # Upload to Supabase Storage
        storage_service = SupabaseStorageService()
        upload_result = await storage_service.upload_employee_nda_document(file, employee_id)
        
        if upload_result["success"]:
            # Update employee record with NDA document info
            # Bucket name is defaulted in database, no need to set
            employee.nda_document_file_size = upload_result["file_size"]
            employee.nda_document_mime_type = upload_result["mime_type"]
            employee.nda_document_uploaded_at = upload_result["uploaded_at"]
            # Legacy field removed - using nda_document_file_path only
            employee.updated_by = current_user.user_id
            employee.updated_at = func.now()
            
            db.commit()
            db.refresh(employee)
            
            return EmployeeDocumentUploadResponse(
                success=True,
                message=f"NDA document uploaded successfully for employee {employee_id}",
                document_type="nda",
                document_filename=upload_result["filename"],
                document_file_path=upload_result["file_path"],
                file_size=upload_result["file_size"],
                uploaded_at=upload_result["uploaded_at"]
            )
        else:
            raise HTTPException(status_code=500, detail="NDA upload failed")
            
    except Exception as e:
        logger.error(f"NDA upload failed for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"NDA upload failed: {str(e)}")

@router.post("/{employee_id}/upload-contract", response_model=EmployeeDocumentUploadResponse)
async def upload_employee_contract(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload contract document for employee with enhanced metadata tracking"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate file type
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/jpg',
            'image/png'
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Only PDF, DOC, DOCX, JPG, and PNG files are allowed for contract documents"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Reset file pointer
        await file.seek(0)
        
        # Upload to Supabase Storage
        storage_service = SupabaseStorageService()
        upload_result = await storage_service.upload_employee_contract_document(file, employee_id)
        
        if upload_result["success"]:
            # Update employee record with contract document info
            # Bucket name is defaulted in database, no need to set
            employee.contract_document_file_size = upload_result["file_size"]
            employee.contract_document_mime_type = upload_result["mime_type"]
            employee.contract_document_uploaded_at = upload_result["uploaded_at"]
            # Legacy field removed - using contract_document_file_path only
            employee.updated_by = current_user.user_id
            employee.updated_at = func.now()
            
            db.commit()
            db.refresh(employee)
            
            return EmployeeDocumentUploadResponse(
                success=True,
                message=f"Contract document uploaded successfully for employee {employee_id}",
                document_type="contract",
                document_filename=upload_result["filename"],
                document_file_path=upload_result["file_path"],
                file_size=upload_result["file_size"],
                uploaded_at=upload_result["uploaded_at"]
            )
        else:
            raise HTTPException(status_code=500, detail="Contract upload failed")
            
    except Exception as e:
        logger.error(f"Contract upload failed for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Contract upload failed: {str(e)}")

@router.delete("/{employee_id}/nda")
async def delete_employee_nda(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete NDA document for employee"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.nda_document_file_path:
            raise HTTPException(status_code=404, detail="No NDA document found for this employee")
        
        # Delete from storage
        storage_service = SupabaseStorageService()
        delete_success = await storage_service.delete_employee_nda_document(employee.nda_document_file_path)
        
        if delete_success:
            # Clear document fields
            # Legacy field removed - using nda_document_file_path only
            # Bucket name is defaulted in database, no need to clear
            employee.nda_document_file_size = None
            employee.nda_document_mime_type = None
            employee.nda_document_uploaded_at = None
            employee.nda_ocr_extracted_data = None
            employee.updated_by = current_user.user_id
            employee.updated_at = func.now()
            
            db.commit()
            
            return {"success": True, "message": f"NDA document deleted successfully for employee {employee_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete NDA document from storage")
            
    except Exception as e:
        logger.error(f"NDA deletion failed for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"NDA deletion failed: {str(e)}")

@router.delete("/{employee_id}/contract")
async def delete_employee_contract(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete contract document for employee"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.contract_document_file_path:
            raise HTTPException(status_code=404, detail="No contract document found for this employee")
        
        # Delete from storage
        storage_service = SupabaseStorageService()
        delete_success = await storage_service.delete_employee_contract_document(employee.contract_document_file_path)
        
        if delete_success:
            # Clear document fields
            # Legacy field removed - using contract_document_file_path only
            # Bucket name is defaulted in database, no need to clear
            employee.contract_document_file_size = None
            employee.contract_document_mime_type = None
            employee.contract_document_uploaded_at = None
            employee.contract_ocr_extracted_data = None
            employee.updated_by = current_user.user_id
            employee.updated_at = func.now()
            
            db.commit()
            
            return {"success": True, "message": f"Contract document deleted successfully for employee {employee_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete contract document from storage")
            
    except Exception as e:
        logger.error(f"Contract deletion failed for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Contract deletion failed: {str(e)}")

@router.get("/{employee_id}/documents", response_model=EmployeeDocumentsResponse)
async def get_employee_documents(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get all document information for employee with download URLs"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Get employee name
        profile = db.query(User).filter(User.user_id == employee.profile_id).first()
        employee_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
        
        storage_service = SupabaseStorageService()
        
        # Build NDA document info
        nda_document = None
        if employee.nda_document_file_path:
            download_url = storage_service.get_employee_nda_document_url(employee.nda_document_file_path)
            nda_document = EmployeeDocumentInfo(
                document_type="nda",
                filename=employee.nda_document_mime_type.split('/')[-1] if employee.nda_document_mime_type else None,
                file_path=employee.nda_document_file_path,
                file_size=employee.nda_document_file_size,
                mime_type=employee.nda_document_mime_type,
                uploaded_at=employee.nda_document_uploaded_at,
                has_document=True,
                download_url=download_url,
                ocr_extracted_data=employee.nda_ocr_extracted_data
            )
        else:
            nda_document = EmployeeDocumentInfo(
                document_type="nda",
                has_document=False
            )
        
        # Build contract document info
        contract_document = None
        if employee.contract_document_file_path:
            download_url = storage_service.get_employee_contract_document_url(employee.contract_document_file_path)
            contract_document = EmployeeDocumentInfo(
                document_type="contract",
                filename=employee.contract_document_mime_type.split('/')[-1] if employee.contract_document_mime_type else None,
                file_path=employee.contract_document_file_path,
                file_size=employee.contract_document_file_size,
                mime_type=employee.contract_document_mime_type,
                uploaded_at=employee.contract_document_uploaded_at,
                has_document=True,
                download_url=download_url,
                ocr_extracted_data=employee.contract_ocr_extracted_data
            )
        else:
            contract_document = EmployeeDocumentInfo(
                document_type="contract",
                has_document=False
            )
        
        return EmployeeDocumentsResponse(
            employee_id=employee_id,
            employee_name=employee_name,
            nda_document=nda_document,
            contract_document=contract_document
        )
        
    except Exception as e:
        logger.error(f"Failed to get documents for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get employee documents: {str(e)}")

@router.get("/{employee_id}/nda")
async def get_employee_nda(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get NDA document download URL for employee"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.nda_document_file_path:
            raise HTTPException(status_code=404, detail="No NDA document found for this employee")
        
        # Get download URL
        storage_service = SupabaseStorageService()
        download_url = storage_service.get_employee_nda_document_url(employee.nda_document_file_path)
        
        if not download_url:
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
        
        return {
            "success": True,
            "employee_id": employee_id,
            "document_type": "nda",
            "download_url": download_url,
            "filename": employee.nda_document_mime_type.split('/')[-1] if employee.nda_document_mime_type else "nda_document",
            "file_size": employee.nda_document_file_size,
            "uploaded_at": employee.nda_document_uploaded_at
        }
        
    except Exception as e:
        logger.error(f"Failed to get NDA for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get NDA document: {str(e)}")

@router.get("/{employee_id}/contract")
async def get_employee_contract(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get contract document download URL for employee"""
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.contract_document_file_path:
            raise HTTPException(status_code=404, detail="No contract document found for this employee")
        
        # Get download URL
        storage_service = SupabaseStorageService()
        download_url = storage_service.get_employee_contract_document_url(employee.contract_document_file_path)
        
        if not download_url:
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
        
        return {
            "success": True,
            "employee_id": employee_id,
            "document_type": "contract",
            "download_url": download_url,
            "filename": employee.contract_document_mime_type.split('/')[-1] if employee.contract_document_mime_type else "contract_document",
            "file_size": employee.contract_document_file_size,
            "uploaded_at": employee.contract_document_uploaded_at
        }
        
    except Exception as e:
        logger.error(f"Failed to get contract for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get contract document: {str(e)}")