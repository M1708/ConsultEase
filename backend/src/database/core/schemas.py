from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID


# Client Schemas
class ClientCreate(BaseModel):
    #client_id: str
    client_name: str
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None

class ClientResponse(BaseModel):
    client_id: int
    client_name: str
    primary_contact_name: Optional[str]
    primary_contact_email: Optional[str]
    company_size: Optional[str]
    industry: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ClientWithContracts(ClientResponse):
    contracts: List['ContractResponse'] = []

# Contract Schemas
class ContractCreate(BaseModel):
    client_id: int
    #contract_id: int
    contract_type: Optional[str] = None  # "Fixed", "Hourly", "Retainer"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    billing_frequency: Optional[str] = None  # "Monthly", "Weekly", "One-time"
    status: Optional[str] = "draft"  # "draft", "active", "completed", "terminated"
    billing_prompt_next_date: Optional[date] = None
    termination_date: Optional[date] = None
    amendments: Optional[str] = None
    notes: Optional[str] = None

class ContractUpdate(BaseModel):
    contract_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    billing_frequency: Optional[str] = None
    status: Optional[str] = None
    billing_prompt_next_date: Optional[date] = None
    termination_date: Optional[date] = None
    amendments: Optional[str] = None
    notes: Optional[str] = None

class ContractDocumentUpload(BaseModel):
    contract_id: int
    filename: str
    file_size: int
    mime_type: str

class ContractDocumentResponse(BaseModel):
    success: bool
    message: str
    document_filename: Optional[str] = None
    document_file_path: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: Optional[datetime] = None

class ContractResponse(BaseModel):
    contract_id: int
    client_id: int
    contract_type: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    original_amount: Optional[Decimal]
    current_amount: Optional[Decimal]
    billing_frequency: Optional[str]
    status: Optional[str]
    billing_prompt_next_date: Optional[date]
    termination_date: Optional[date]
    amendments: Optional[str]
    notes: Optional[str]
    document_filename: Optional[str] = None
    document_file_path: Optional[str] = None
    document_file_size: Optional[int] = None
    document_mime_type: Optional[str] = None
    document_uploaded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    
    class Config:
        from_attributes = True


# Forward-referencing for relationships
ClientWithContracts.model_rebuild()

class ClientContactCreate(BaseModel):
    client_id: int
    name: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, max_length=100)
    last_interaction_summary: Optional[str] = None
    client_name: Optional[str] = None

class ClientContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, max_length=100)
    last_interaction_summary: Optional[str] = None

class ClientContactResponse(BaseModel):
    contact_id: int
    client_id: int
    name: str
    email: Optional[str]
    role: Optional[str]
    last_interaction_summary: Optional[str]
    client_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Deliverable Schemas
class DeliverableCreate(BaseModel):
    contract_id: int
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_employees: int
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=20)
    billing_basis: Optional[str] = Field(None, max_length=50)
    billing_amount: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    assigned_employee_name: Optional[str] = None

class DeliverableUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_employees: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=20)
    billing_basis: Optional[str] = Field(None, max_length=50)
    billing_amount: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    assigned_employee_name: Optional[str] = None

class DeliverableResponse(BaseModel):
    deliverable_id: int
    contract_id: int
    name: str
    description: Optional[str]
    assigned_employees: int
    start_date: Optional[date]
    due_date: Optional[date]
    completion_date: Optional[date]
    status: Optional[str]
    billing_basis: Optional[str]
    billing_amount: Optional[Decimal]
    notes: Optional[str]
    client_name: Optional[str]
    assigned_employee_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Time Entry Schemas
class TimeEntryCreate(BaseModel):
    employee_id: int
    contract_id: int
    deliverable_id: Optional[int] = None
    client_id: int
    date: date
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=24)
    description_of_work: Optional[str] = None
    billable: bool = False
    billing_rate: Optional[Decimal] = Field(None, ge=0)
    billed: bool = False
    invoice_id: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=20)

class TimeEntryUpdate(BaseModel):
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=24)
    description_of_work: Optional[str] = None
    billable: Optional[bool] = None
    billing_rate: Optional[Decimal] = Field(None, ge=0)
    billed: Optional[bool] = None
    invoice_id: Optional[str] = Field(None, max_length=20)

class TimeEntryResponse(BaseModel):
    time_entry_id: int
    employee_id: int
    contract_id: int
    deliverable_id: Optional[int]
    client_id: int
    date: date
    hours_worked: Optional[Decimal]
    description_of_work: Optional[str]
    billable: bool
    billing_rate: Optional[Decimal]
    billed: bool
    invoice_id: Optional[str]
    employee_name: Optional[str]
    deliverable_name: Optional[str]
    client_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Expense Schemas
class ExpenseCreate(BaseModel):
    employee_id: int
    client_id: int
    deliverable_id: Optional[int] = None
    date: date
    expense_category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default='USD', max_length=3)
    billable_to_client: bool = False
    reimbursable: bool = False
    receipt_link: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=20)

class ExpenseUpdate(BaseModel):
    expense_category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    billable_to_client: Optional[bool] = None
    reimbursable: Optional[bool] = None
    receipt_link: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)

class ExpenseResponse(BaseModel):
    expense_id: int
    employee_id: int
    client_id: int
    deliverable_id: Optional[int]
    date: date
    expense_category: Optional[str]
    description: Optional[str]
    amount: Optional[Decimal]
    currency: str
    billable_to_client: bool
    reimbursable: bool
    receipt_link: Optional[str]
    status: Optional[str]
    document_filename: Optional[str]
    document_file_size: Optional[int]
    document_mime_type: Optional[str]
    document_uploaded_at: Optional[datetime]
    employee_name: Optional[str]
    client_name: Optional[str]
    deliverable_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExpenseDocumentUpload(BaseModel):
    expense_id: int
    filename: str
    file_size: int
    mime_type: str

class ExpenseDocumentResponse(BaseModel):
    success: bool
    message: str
    document_filename: Optional[str] = None
    receipt_link: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: Optional[datetime] = None

# Employee Schemas
class EmployeeBase(BaseModel):
    employee_number: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    employment_type: str = Field(..., max_length=20)  # permanent, contract, intern, consultant
    full_time_part_time: str = Field(..., max_length=10)  # full_time, part_time
    committed_hours: Optional[int] = Field(None, ge=0, le=168)  # max 168 hours per week
    hire_date: date
    termination_date: Optional[date] = None
    rate_type: Optional[str] = Field(None, max_length=20)  # hourly, salary, project_based
    rate: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    # Legacy fields removed - using nda_document_file_path and contract_document_file_path

    @validator('employment_type')
    def validate_employment_type(cls, v):
        valid_types = ['permanent', 'contract', 'intern', 'consultant']
        if v not in valid_types:
            raise ValueError(f'employment_type must be one of: {valid_types}')
        return v

    @validator('full_time_part_time')
    def validate_full_time_part_time(cls, v):
        valid_types = ['full_time', 'part_time']
        if v not in valid_types:
            raise ValueError(f'full_time_part_time must be one of: {valid_types}')
        return v

    @validator('rate_type')
    def validate_rate_type(cls, v):
        if v is not None:
            valid_types = ['hourly', 'salary', 'project_based']
            if v not in valid_types:
                raise ValueError(f'rate_type must be one of: {valid_types}')
        return v

    @validator('termination_date')
    def validate_termination_date(cls, v, values):
        if v and 'hire_date' in values and values['hire_date']:
            if v <= values['hire_date']:
                raise ValueError('termination_date must be after hire_date')
        return v

class EmployeeCreate(EmployeeBase):
    profile_id: UUID

class EmployeeUpdate(BaseModel):
    employee_number: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    employment_type: Optional[str] = Field(None, max_length=20)
    full_time_part_time: Optional[str] = Field(None, max_length=10)
    committed_hours: Optional[int] = Field(None, ge=0, le=168)
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    rate_type: Optional[str] = Field(None, max_length=20)
    rate: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    # Legacy fields removed - using nda_document_file_path and contract_document_file_path
    # Enhanced document fields for NDA
    nda_document_bucket_name: Optional[str] = Field(None, max_length=50)
    nda_document_file_size: Optional[int] = Field(None, ge=0)
    nda_document_mime_type: Optional[str] = Field(None, max_length=100)
    nda_document_uploaded_at: Optional[datetime] = None
    nda_ocr_extracted_data: Optional[dict] = None
    # Enhanced document fields for Contract
    contract_document_bucket_name: Optional[str] = Field(None, max_length=50)
    contract_document_file_size: Optional[int] = Field(None, ge=0)
    contract_document_mime_type: Optional[str] = Field(None, max_length=100)
    contract_document_uploaded_at: Optional[datetime] = None
    contract_ocr_extracted_data: Optional[dict] = None

class EmployeeResponse(EmployeeBase):
    employee_id: int
    profile_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True

class EmployeeSearch(BaseModel):
    search_term: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    full_time_part_time: Optional[str] = None
    rate_type: Optional[str] = None
    limit: int = Field(default=50, le=100)

# User (Profile) Schemas
class UserCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = "viewer" # Assuming default role
    status: Optional[str] = "active" # Assuming default status

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class UserResponse(BaseModel):
    profile_id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Employee Document Management Schemas
class EmployeeDocumentUploadResponse(BaseModel):
    """Response model for employee document upload operations"""
    success: bool
    message: str
    document_type: str  # "nda" or "contract"
    document_filename: Optional[str] = None
    document_file_path: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: Optional[datetime] = None

class EmployeeDocumentInfo(BaseModel):
    """Information about an employee document"""
    document_type: str  # "nda" or "contract"
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    has_document: bool = False
    download_url: Optional[str] = None
    ocr_extracted_data: Optional[dict] = None

class EmployeeDocumentsResponse(BaseModel):
    """Response model for getting all employee documents"""
    employee_id: int
    employee_name: Optional[str] = None
    nda_document: Optional[EmployeeDocumentInfo] = None
    contract_document: Optional[EmployeeDocumentInfo] = None