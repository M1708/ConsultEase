from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal


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