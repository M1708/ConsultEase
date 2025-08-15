import os
import uuid
from datetime import datetime
from supabase import create_client, Client
from fastapi import UploadFile, HTTPException
import logging
from typing import Dict, Any

class SupabaseStorageService:
    def __init__(self):
        logger = logging.getLogger("StorageService")
        #logger.setLevel(logging.INFO")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = "contract-documents"
    
    async def upload_contract_document(self, file: UploadFile, contract_id: int) -> Dict[str, Any]:
        """Upload contract document to Supabase Storage"""
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
            unique_filename = f"contract_{contract_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = f"contracts/{contract_id}/{unique_filename}"
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to Supabase Storage
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": file.content_type,
                    "upsert": False
                }
            )

            if hasattr(response, 'path'):  # UploadResponse object has 'path' attribute
                # Success - this is an UploadResponse object
                pass
            # Check if upload was successful - Supabase returns None on success or error dict on failure
            elif response is not None and hasattr(response, 'get') and response.get('error'):
                raise HTTPException(status_code=500, detail=f"Upload failed: {response['error']}")
            elif response is not None and not hasattr(response, 'get'):
                # If response is not None but doesn't have get method, it might be an error object
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(response)}")
            
            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "public_url": public_url,
                "filename": file.filename,
                "file_size": file_size,
                "mime_type": file.content_type,
                "uploaded_at": datetime.utcnow()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def delete_contract_document(self, file_path: str) -> bool:
        """Delete contract document from Supabase Storage"""
        try:
            response = self.supabase.storage.from_(self.bucket_name).remove([file_path])
                        # Check if delete was successful - Supabase returns None on success or error dict on failure
            if response is not None and hasattr(response, 'get'):
                return not response.get('error')
            else:
                # If response is None, it means success
                return True
        except Exception:
            return False


    def get_document_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get signed URL for private document access"""
        try:
            response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            # Check if response has get method and contains signedURL
            if response is not None and hasattr(response, 'get'):
                return response.get('signedURL', '')
            else:
                # If response doesn't have get method, try to access directly or return empty
                return getattr(response, 'signedURL', '') if response else ''
        except Exception:
            return ''
        

    async def upload_expense_document(self, file: UploadFile, expense_id: int) -> Dict[str, Any]:
        """Upload expense document (receipt/invoice) to Supabase Storage"""
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
            unique_filename = f"expense_{expense_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = f"expenses/{expense_id}/{unique_filename}"
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to Supabase Storage (using existing bucket)
            bucket_name = "expense-documents"  # Use existing bucket
            response = self.supabase.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": file.content_type,
                    "upsert": False
                }
            )
            
            if hasattr(response, 'path'):  # UploadResponse object has 'path' attribute
                # Success - this is an UploadResponse object
                pass
            # Check if upload was successful - Supabase returns None on success or error dict on failure
            elif response is not None and hasattr(response, 'get') and response.get('error'):
                raise HTTPException(status_code=500, detail=f"Upload failed: {response['error']}")
            elif response is not None and not hasattr(response, 'get'):
                # If response is not None but doesn't have get method, it might be an error object
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(response)}")
            
            # Get public URL
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "public_url": public_url,
                "filename": file.filename,
                "file_size": file_size,
                "mime_type": file.content_type,
                "uploaded_at": datetime.utcnow()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    #async def delete_expense_document(self, file_path: str) -> bool:
    #    """Delete expense document from Supabase Storage"""
    #    try:
    #        bucket_name = "expense-documents"
    #        response = self.supabase.storage.from_(bucket_name).remove([file_path])
    #        return not response.get('error')
    #    except Exception:
    #        return False

    async def delete_expense_document(self, file_path: str) -> bool:
        """Delete expense document from Supabase Storage"""
        try:
            bucket_name = "expense-documents"
            print(f"Attempting to delete: {file_path} from bucket: {bucket_name}")  # Debug
            
            response = self.supabase.storage.from_(bucket_name).remove([file_path])
            print(f"Delete response: {response}")  # Debug
            
            # Check if deletion was successful
            if hasattr(response, 'error') and response.error:
                print(f"Delete error: {response.error}")  # Debug
                return False
            elif isinstance(response, list) and len(response) > 0:
                # Supabase typically returns a list of deleted objects
                return True
            else:
                print(f"Unexpected response format: {type(response)}")  # Debug
                return False
                
        except Exception as e:
            print(f"Exception during delete: {str(e)}")  # Debug
            return False
        
    def get_expense_document_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get signed URL for expense document access"""
        try:
            bucket_name = "expense-documents"
            response = self.supabase.storage.from_(bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return response.get('signedURL', '')
        except Exception:
            return ''
