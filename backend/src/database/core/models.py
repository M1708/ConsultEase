from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, Numeric, BigInteger, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.core.database import Base
from enum import Enum

class Client(Base):
    __tablename__ = "clients"
    
    client_id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    primary_contact_name = Column(String)
    primary_contact_email = Column(String)
    company_size = Column(String)  # e.g., "10-50", "50-200", "200+"
    industry = Column(String)
    notes = Column(Text)
    created_by = Column(String)  # Will connect to user system later
    updated_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to contracts
    contracts = relationship("Contract", back_populates="client")
    contacts = relationship("ClientContact", back_populates="client")

class Contract(Base):
    __tablename__ = "contracts"
    
    contract_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    contract_type = Column(String)  # e.g., "Fixed", "Hourly", "Retainer"
    start_date = Column(Date)
    end_date = Column(Date)
    original_amount = Column(Numeric(12, 2))  # Supports currency with 2 decimal places
    current_amount = Column(Numeric(12, 2))   # Current contract value
    billing_frequency = Column(String)  # e.g., "Monthly", "Weekly", "One-time"
    status = Column(String, default="draft")  # e.g., "draft", "active", "completed", "terminated"
    billing_prompt_next_date = Column(Date)  # Next billing reminder date
    termination_date = Column(Date)
    amendments = Column(Text)  # Contract amendments/changes
    notes = Column(Text)
    document_filename = Column(String(255))
    document_file_path = Column(Text)
    document_bucket_name = Column(String(50), default='contract-documents')
    document_file_size = Column(BigInteger)
    document_mime_type = Column(String(100))
    document_uploaded_at = Column(DateTime)
    ocr_extracted_data = Column(JSON)  # Use JSON type for JSONB
    ai_analysis_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String)
    updated_by = Column(String)
    
    # Relationship to client
    client = relationship("Client", back_populates="contracts")
    deliverables = relationship("Deliverable", back_populates="contract")

class ClientContact(Base):
    __tablename__ = "client_contacts"
    
    contact_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))  # valid_email constraint handled in validation
    role = Column(String(100))
    last_interaction_summary = Column(Text)
    client_name = Column(String(255))  # Denormalized for AI queries
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    
    # Relationship
    client = relationship("Client", back_populates="contacts")

class Deliverable(Base):
    __tablename__ = "deliverables"
    
    deliverable_id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.contract_id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    assigned_employees = Column(Integer, nullable=False)  # Assuming this references employee_id
    start_date = Column(Date)
    due_date = Column(Date)
    completion_date = Column(Date)
    status = Column(String(20))
    billing_basis = Column(String(50))
    billing_amount = Column(Numeric(12, 2))
    notes = Column(Text)
    client_name = Column(String(255))  # Denormalized for AI queries
    assigned_employee_name = Column(String(255))  # Denormalized for AI queries
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    
    # Relationship
    contract = relationship("Contract", back_populates="deliverables")

class TimeEntry(Base):
    __tablename__ = "time_entries"
    
    time_entry_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)  # References employees table
    contract_id = Column(Integer, ForeignKey("contracts.contract_id"), nullable=False)
    deliverable_id = Column(Integer, ForeignKey("deliverables.deliverable_id"))
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    date = Column(Date, nullable=False)
    hours_worked = Column(Numeric(8, 2))
    description_of_work = Column(Text)
    billable = Column(Boolean, default=False)
    billing_rate = Column(Numeric(10, 2))
    billed = Column(Boolean, default=False)
    invoice_id = Column(String(20))
    entered_by = Column(String(10))
    entry_timestamp = Column(DateTime(timezone=True))
    last_modified_by = Column(String(10))
    last_modified_timestamp = Column(DateTime(timezone=True))
    source = Column(String(20))
    employee_name = Column(String(255))  # Denormalized for AI queries
    deliverable_name = Column(String(255))  # Denormalized for AI queries
    client_name = Column(String(255))  # Denormalized for AI queries
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    
    # Relationships
    contract = relationship("Contract")
    deliverable = relationship("Deliverable")
    client = relationship("Client")

class Expense(Base):
    __tablename__ = "expenses"
    
    expense_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)  # References employees table
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    deliverable_id = Column(Integer, ForeignKey("deliverables.deliverable_id"))
    date = Column(Date, nullable=False)
    expense_category = Column(String(50))
    description = Column(Text)
    amount = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')
    billable_to_client = Column(Boolean, default=False)
    reimbursable = Column(Boolean, default=False)
    receipt_link = Column(Text)
    status = Column(String(20))
    entered_by = Column(String(10))
    entry_timestamp = Column(DateTime(timezone=True))
    last_modified_by = Column(String(10))
    last_modified_timestamp = Column(DateTime(timezone=True))
    source = Column(String(20))
    # Document fields
    document_filename = Column(String(255))
    document_bucket_name = Column(String(50), default='expense-documents')
    document_file_size = Column(Integer)  # Changed from BIGINT to Integer for SQLAlchemy compatibility
    document_mime_type = Column(String(100))
    document_uploaded_at = Column(DateTime(timezone=True))
    ocr_extracted_data = Column(JSONB)
    ai_analysis_data = Column(JSONB)
    # Denormalized fields
    employee_name = Column(String(255))  # Denormalized for AI queries
    client_name = Column(String(255))  # Denormalized for AI queries
    deliverable_name = Column(String(255))  # Denormalized for AI queries
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    
    # Relationships
    client = relationship("Client")
    deliverable = relationship("Deliverable")

class UserRole(str, Enum):
    super_admin = "super_admin"
    admin = "admin"
    manager = "manager"
    employee = "employee"
    client = "client"
    viewer = "viewer"

class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    pending = "pending"

class Employee(Base):
    __tablename__ = "employees"
    
    employee_id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"), nullable=False)
    employee_number = Column(String(50), unique=True)
    job_title = Column(String(100))
    department = Column(String(100))
    employment_type = Column(String(20), nullable=False)  # permanent, contract, intern, consultant
    full_time_part_time = Column(String(10), nullable=False)  # full_time, part_time
    committed_hours = Column(Integer)  # hours per week/month
    hire_date = Column(Date, nullable=True)  # Defaults to today's date in the tool
    termination_date = Column(Date)
    
    # Compensation
    rate_type = Column(String(20))  # hourly, salary, project_based
    rate = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')
    
    # Documents - Legacy fields (kept for backward compatibility)
    nda_file_link = Column(String(500))
    contract_file_link = Column(String(500))
    
    # Document fields for NDA - Enhanced storage with metadata
    nda_document_bucket_name = Column(String(50), default='employee-nda-documents')
    nda_document_file_size = Column(BigInteger)
    nda_document_mime_type = Column(String(100))
    nda_document_uploaded_at = Column(DateTime(timezone=True))
    nda_ocr_extracted_data = Column(JSONB)
    
    # Document fields for Contract - Enhanced storage with metadata
    contract_document_bucket_name = Column(String(50), default='employee-contract-documents')
    contract_document_file_size = Column(BigInteger)
    contract_document_mime_type = Column(String(100))
    contract_document_uploaded_at = Column(DateTime(timezone=True))
    contract_ocr_extracted_data = Column(JSONB)
    
    # Additional document metadata fields
    nda_document_filename = Column(String(255))
    nda_document_file_path = Column(Text)
    contract_document_filename = Column(String(255))
    contract_document_file_path = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"))
    updated_by = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"))
    
    # Relationships
    profile = relationship("User", foreign_keys=[profile_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])

class User(Base):
    __tablename__ = "profiles"
    
    user_id = Column("profile_id", UUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(SQLEnum(UserRole), nullable=False, default="viewer")
    status = Column(SQLEnum(UserStatus), nullable=False, default="active")
    phone = Column(String)
    last_login = Column(DateTime(timezone=True))
    password_reset_required = Column("password_reset", Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email
