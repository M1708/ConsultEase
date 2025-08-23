-- Complete ConsultEase Database Schema for Supabase PostgreSQL
-- Generated from EffiScale_Agentic_AI_App_Tables-V1.xlsx
-- Optimized for AI agent conversational UI with RBAC and email validation

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- CUSTOM DATA TYPES AND CONSTRAINTS
-- =============================================

-- Create email validation domain
CREATE DOMAIN valid_email AS VARCHAR(255)
CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Create user role enum
CREATE TYPE public.user_role AS ENUM (
    'super_admin',
    'admin', 
    'manager',
    'employee',
    'client',
    'viewer'
);

-- Create user status enum
CREATE TYPE user_status AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending'
);

-- =============================================
-- USERS TABLE WITH RBAC (Created First)
-- =============================================


CREATE TABLE profiles (
    profile_id UUID PRIMARY KEY,
    email valid_email UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role user_role NOT NULL DEFAULT 'viewer',
    status user_status NOT NULL DEFAULT 'active', -- active, inactive, suspended
    last_login TIMESTAMP,
    password_reset BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id)
  
);

-- Create indexes for Profiles table
CREATE INDEX idx_users_email ON profiles(email);
CREATE INDEX idx_users_role ON profiles(role);
CREATE INDEX idx_users_status ON profiles(status);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON profiles(last_login);


-- =============================================
-- ROLE PERMISSIONS TABLE
-- =============================================

CREATE TABLE role_permissions (
    permission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role user_role NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    conditions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_role_permissions_unique ON role_permissions(role, resource, action);


-- =============================================
-- 1. CLIENTS TABLE
-- =============================================
CREATE TABLE clients (
    client_id SERIAL PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    primary_contact_name VARCHAR(255),
    primary_contact_email valid_email,
    company_size VARCHAR(50),
    industry VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id)
);

-- Add indexes for better performance
CREATE INDEX idx_clients_name ON clients(client_name);
CREATE INDEX idx_clients_industry ON clients(industry);
CREATE INDEX idx_clients_company_size ON clients(company_size);
CREATE INDEX idx_clients_created_by ON clients(created_by);

-- =============================================
-- 2. CLIENT CONTACTS TABLE
-- =============================================
CREATE TABLE client_contacts (
    contact_id SERIAL PRIMARY KEY,
    client_id SERIAL NOT NULL,
    name VARCHAR(255) NOT NULL,
    email valid_email,
    role VARCHAR(100),
    last_interaction_summary TEXT,
    client_name VARCHAR(255), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraint
    CONSTRAINT fk_client_contacts_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_client_contacts_client_id ON client_contacts(client_id);
CREATE INDEX idx_client_contacts_email ON client_contacts(email);
CREATE INDEX idx_client_contacts_created_by ON client_contacts(created_by);

-- =============================================
-- 3. CONTRACTS TABLE
-- =============================================
CREATE TABLE contracts (
    contract_id SERIAL PRIMARY KEY,
    client_id SERIAL NOT NULL,
    contract_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    original_amount DECIMAL(12,2),
    current_amount DECIMAL(12,2),
    billing_frequency VARCHAR(20),
    status VARCHAR(20),
    billing_prompt_next_date DATE,
    termination_date DATE,
    amendments TEXT,
    notes TEXT,
    document_filename VARCHAR(255),
    document_file_path TEXT,
    document_bucket_name VARCHAR(50) DEFAULT 'contract-documents',
    document_file_size BIGINT,
    document_mime_type VARCHAR(100),
    document_uploaded_at TIMESTAMP WITH TIME ZONE,
    ocr_extracted_data JSONB,
    ai_analysis_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraint
    CONSTRAINT fk_contracts_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_contracts_client_id ON contracts(client_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_start_date ON contracts(start_date);
CREATE INDEX idx_contracts_end_date ON contracts(end_date);
CREATE INDEX idx_contracts_created_by ON contracts(created_by);
CREATE INDEX idx_contracts_document_uploaded_at ON contracts(document_uploaded_at);

-- =============================================
-- 4. EMPLOYEES TABLE
-- =============================================
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    employee_number VARCHAR(50) UNIQUE, -- Optional employee ID
    job_title VARCHAR(100),
    department VARCHAR(100),
    employment_type VARCHAR(20) NOT NULL, -- permanent, contract, intern, consultant
    full_time_part_time VARCHAR(10) NOT NULL, -- full_time, part_time
    committed_hours INTEGER, -- hours per week/month
    hire_date DATE NOT NULL,
    termination_date DATE,
    
    -- Compensation
    rate_type VARCHAR(20), -- hourly, salary, project_based
    rate DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Documents
    nda_file_link VARCHAR(500),
    contract_file_link VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id)
);
 
ALTER TABLE employees ADD CONSTRAINT uk_employees_profile_id UNIQUE(profile_id);
ALTER TABLE employees ADD CONSTRAINT uk_employees_employee_number UNIQUE(employee_number);
ALTER TABLE employees ADD CONSTRAINT chk_employment_type CHECK (LOWER(employment_type) IN ('permanent', 'contract', 'intern', 'consultant'));
ALTER TABLE employees ADD CONSTRAINT chk_rate_type CHECK (LOWER(rate_type) IN ('hourly', 'salary', 'project_based'));
ALTER TABLE employees ADD CONSTRAINT chk_full_time_part_time 
CHECK (LOWER(full_time_part_time) IN ('full_time', 'part_time', 'full-time', 'part-time'));

--ALTER TABLE employees DROP CONSTRAINT chk_employment_type;

-- Add indexes separately
CREATE INDEX idx_employees_user_id ON employees(profile_id);
CREATE INDEX idx_employees_department ON employees(department);
CREATE INDEX idx_employees_employment_type ON employees(employment_type);
CREATE INDEX idx_employees_hire_date ON employees(hire_date);
    

-- =============================================
-- 5. AVAILABILITY TABLE
-- =============================================
CREATE TABLE availability (
    availability_id SERIAL PRIMARY KEY,
    employee_id SERIAL NOT NULL,
    start_date DATE,
    end_date DATE,
    available_hours_per_day INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraint
    CONSTRAINT fk_availability_employee_id 
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_availability_employee_id ON availability(employee_id);
CREATE INDEX idx_availability_start_date ON availability(start_date);
CREATE INDEX idx_availability_end_date ON availability(end_date);
CREATE INDEX idx_availability_created_by ON availability(created_by);

-- =============================================
-- 6. CLIENT ASSIGNMENTS TABLE
-- =============================================
CREATE TABLE client_assignments (
    assignment_id SERIAL PRIMARY KEY,
    employee_id SERIAL NOT NULL,
    client_id SERIAL NOT NULL,
    start_date DATE,
    end_date DATE,
    role VARCHAR(100),
    employee_name VARCHAR(255), -- Denormalized for AI queries
    client_name VARCHAR(255), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraints
    CONSTRAINT fk_client_assignments_employee_id 
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    CONSTRAINT fk_client_assignments_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_client_assignments_employee_id ON client_assignments(employee_id);
CREATE INDEX idx_client_assignments_client_id ON client_assignments(client_id);
CREATE INDEX idx_client_assignments_start_date ON client_assignments(start_date);
CREATE INDEX idx_client_assignments_created_by ON client_assignments(created_by);

-- =============================================
-- 7. DELIVERABLES TABLE
-- =============================================
CREATE TABLE deliverables (
    deliverable_id SERIAL PRIMARY KEY,
    contract_id SERIAL NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    assigned_employees SERIAL NOT NULL,
    start_date DATE,
    due_date DATE,
    completion_date DATE,
    status VARCHAR(20),
    billing_basis VARCHAR(50),
    billing_amount DECIMAL(12,2),
    notes TEXT,
    client_name VARCHAR(255), -- Denormalized for AI queries
    assigned_employee_name VARCHAR(255), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraint
    CONSTRAINT fk_deliverables_contract_id 
        FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE,
    CONSTRAINT fk_assigned_emp_id
        FOREIGN KEY (assigned_employees) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_deliverables_contract_id ON deliverables(contract_id);
CREATE INDEX idx_deliverables_status ON deliverables(status);
CREATE INDEX idx_deliverables_start_date ON deliverables(start_date);
CREATE INDEX idx_deliverables_due_date ON deliverables(due_date);
CREATE INDEX idx_deliverables_created_by ON deliverables(created_by);

-- =============================================
-- 8. TIME ENTRIES TABLE
-- =============================================
CREATE TABLE time_entries (
    time_entry_id SERIAL PRIMARY KEY,
    employee_id SERIAL NOT NULL,
    contract_id SERIAL NOT NULL,
    deliverable_id SERIAL,
    client_id SERIAL NOT NULL,
    date DATE NOT NULL,
    hours_worked DECIMAL(8,2),
    description_of_work TEXT,
    billable BOOLEAN DEFAULT FALSE,
    billing_rate DECIMAL(10,2),
    billed BOOLEAN DEFAULT FALSE,
    invoice_id VARCHAR(20),
    entered_by VARCHAR(10),
    entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_modified_by VARCHAR(10),
    last_modified_timestamp TIMESTAMP WITH TIME ZONE,
    source VARCHAR(20),
    employee_name VARCHAR(255), -- Denormalized for AI queries
    deliverable_name VARCHAR(255), -- Denormalized for AI queries
    client_name VARCHAR(255), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraints
    CONSTRAINT fk_time_entries_employee_id 
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    CONSTRAINT fk_time_entries_contract_id 
        FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE,
    CONSTRAINT fk_time_entries_deliverable_id 
        FOREIGN KEY (deliverable_id) REFERENCES deliverables(deliverable_id) ON DELETE SET NULL,
    CONSTRAINT fk_time_entries_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_time_entries_employee_id ON time_entries(employee_id);
CREATE INDEX idx_time_entries_contract_id ON time_entries(contract_id);
CREATE INDEX idx_time_entries_deliverable_id ON time_entries(deliverable_id);
CREATE INDEX idx_time_entries_client_id ON time_entries(client_id);
CREATE INDEX idx_time_entries_date ON time_entries(date);
CREATE INDEX idx_time_entries_billable ON time_entries(billable);
CREATE INDEX idx_time_entries_billed ON time_entries(billed);
CREATE INDEX idx_time_entries_created_by ON time_entries(created_by);

-- =============================================
-- 9. BILLING TABLE
-- =============================================
CREATE TABLE billing (
    invoice_id SERIAL PRIMARY KEY,
    client_id SERIAL NOT NULL,
    contract_id SERIAL NOT NULL,
    billing_period_start DATE,
    billing_period_end DATE,
    invoice_date DATE,
    time_entry_ids TEXT,
    total_hours DECIMAL(8,2),
    total_amount DECIMAL(12,2),
    status VARCHAR(20),
    invoice_file_link TEXT,
    notes TEXT,
    client_name VARCHAR(255), -- Denormalized for AI queries
    contract_type VARCHAR(50), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraints
    CONSTRAINT fk_billing_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_contract_id 
        FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX idx_billing_client_id ON billing(client_id);
CREATE INDEX idx_billing_contract_id ON billing(contract_id);
CREATE INDEX idx_billing_status ON billing(status);
CREATE INDEX idx_billing_invoice_date ON billing(invoice_date);
CREATE INDEX idx_billing_period_start ON billing(billing_period_start);
CREATE INDEX idx_billing_period_end ON billing(billing_period_end);
CREATE INDEX idx_billing_created_by ON billing(created_by);

-- =============================================
-- 10. EXPENSES TABLE
-- =============================================
CREATE TABLE expenses (
    expense_id SERIAL PRIMARY KEY,
    employee_id SERIAL NOT NULL,
    client_id SERIAL NOT NULL,
    deliverable_id SERIAL,
    date DATE NOT NULL,
    expense_category VARCHAR(50),
    description TEXT,
    amount DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    billable_to_client BOOLEAN DEFAULT FALSE,
    reimbursable BOOLEAN DEFAULT FALSE,
    receipt_link TEXT,
    document_filename VARCHAR(255),
    document_bucket_name VARCHAR(50) DEFAULT 'expense-documents',
    document_file_size BIGINT,
    document_mime_type VARCHAR(100),
    document_uploaded_at TIMESTAMP WITH TIME ZONE,
    ocr_extracted_data JSONB,
    ai_analysis_data JSONB,
    status VARCHAR(20),
    entered_by VARCHAR(10),
    entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_modified_by VARCHAR(10),
    last_modified_timestamp TIMESTAMP WITH TIME ZONE,
    source VARCHAR(20),
    employee_name VARCHAR(255), -- Denormalized for AI queries
    client_name VARCHAR(255), -- Denormalized for AI queries
    deliverable_name VARCHAR(255), -- Denormalized for AI queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(profile_id),
    updated_by UUID REFERENCES profiles(profile_id),
    
    -- Foreign key constraints
    CONSTRAINT fk_expenses_employee_id 
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    CONSTRAINT fk_expenses_client_id 
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE,
    CONSTRAINT fk_expenses_deliverable_id 
        FOREIGN KEY (deliverable_id) REFERENCES deliverables(deliverable_id) ON DELETE SET NULL
);

-- Add indexes
CREATE INDEX idx_expenses_employee_id ON expenses(employee_id);
CREATE INDEX idx_expenses_client_id ON expenses(client_id);
CREATE INDEX idx_expenses_deliverable_id ON expenses(deliverable_id);
CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_expenses_category ON expenses(expense_category);
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_expenses_billable ON expenses(billable_to_client);
CREATE INDEX idx_expenses_created_by ON expenses(created_by);
CREATE INDEX idx_expenses_document_uploaded_at ON expenses(document_uploaded_at);

-- =============================================
-- INSERT DEFAULT ROLE PERMISSIONS
-- =============================================

-- Super Admin permissions (full access to everything)
INSERT INTO role_permissions (role, resource, action) VALUES
('super_admin', 'profiles', 'create'),
('super_admin', 'profiles', 'read'),
('super_admin', 'profiles', 'update'),
('super_admin', 'profiles', 'delete'),
('super_admin', 'clients', 'create'),
('super_admin', 'clients', 'read'),
('super_admin', 'clients', 'update'),
('super_admin', 'clients', 'delete'),
('super_admin', 'employees', 'create'),
('super_admin', 'employees', 'read'),
('super_admin', 'employees', 'update'),
('super_admin', 'employees', 'delete'),
('super_admin', 'contracts', 'create'),
('super_admin', 'contracts', 'read'),
('super_admin', 'contracts', 'update'),
('super_admin', 'contracts', 'delete'),
('super_admin', 'deliverables', 'create'),
('super_admin', 'deliverables', 'read'),
('super_admin', 'deliverables', 'update'),
('super_admin', 'deliverables', 'delete'),
('super_admin', 'time_entries', 'create'),
('super_admin', 'time_entries', 'read'),
('super_admin', 'time_entries', 'update'),
('super_admin', 'time_entries', 'delete'),
('super_admin', 'billing', 'create'),
('super_admin', 'billing', 'read'),
('super_admin', 'billing', 'update'),
('super_admin', 'billing', 'delete'),
('super_admin', 'expenses', 'create'),
('super_admin', 'expenses', 'read'),
('super_admin', 'expenses', 'update'),
('super_admin', 'expenses', 'delete');

-- Admin permissions (most access except user management)
INSERT INTO role_permissions (role, resource, action) VALUES
('admin', 'clients', 'create'),
('admin', 'clients', 'read'),
('admin', 'clients', 'update'),
('admin', 'clients', 'delete'),
('admin', 'employees', 'read'),
('admin', 'employees', 'update'),
('admin', 'contracts', 'create'),
('admin', 'contracts', 'read'),
('admin', 'contracts', 'update'),
('admin', 'contracts', 'delete'),
('admin', 'deliverables', 'create'),
('admin', 'deliverables', 'read'),
('admin', 'deliverables', 'update'),
('admin', 'deliverables', 'delete'),
('admin', 'time_entries', 'create'),
('admin', 'time_entries', 'read'),
('admin', 'time_entries', 'update'),
('admin', 'time_entries', 'delete'),
('admin', 'billing', 'create'),
('admin', 'billing', 'read'),
('admin', 'billing', 'update'),
('admin', 'billing', 'delete'),
('admin', 'expenses', 'read'),
('admin', 'expenses', 'update');

-- Manager permissions (project and team management)
INSERT INTO role_permissions (role, resource, action) VALUES
('manager', 'clients', 'read'),
('manager', 'employees', 'read'),
('manager', 'contracts', 'read'),
('manager', 'deliverables', 'create'),
('manager', 'deliverables', 'read'),
('manager', 'deliverables', 'update'),
('manager', 'time_entries', 'read'),
('manager', 'time_entries', 'update'),
('manager', 'billing', 'read'),
('manager', 'expenses', 'read');

-- Employee permissions (own data and assigned work)
INSERT INTO role_permissions (role, resource, action) VALUES
('employee', 'clients', 'read'),
('employee', 'deliverables', 'read'),
('employee', 'time_entries', 'create'),
('employee', 'time_entries', 'read'),
('employee', 'time_entries', 'update'),
('employee', 'expenses', 'create'),
('employee', 'expenses', 'read'),
('employee', 'expenses', 'update');

-- Client permissions (limited to their own data)
INSERT INTO role_permissions (role, resource, action) VALUES
('client', 'contracts', 'read'),
('client', 'deliverables', 'read'),
('client', 'billing', 'read');

-- Viewer permissions (read-only access to basic data)
INSERT INTO role_permissions (role, resource, action) VALUES
('viewer', 'clients', 'read'),
('viewer', 'deliverables', 'read');

-- =============================================
-- RBAC HELPER FUNCTIONS
-- =============================================

-- Function to check if a user has permission for a specific action
CREATE OR REPLACE FUNCTION user_has_permission(
    user_uuid UUID,
    resource_name VARCHAR,
    action_name VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    user_role_val user_role;
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Get user role
    SELECT role INTO user_role_val FROM profiles WHERE profile_id = user_uuid;
    
    -- Check if role has permission
    SELECT EXISTS(
        SELECT 1 FROM role_permissions 
        WHERE role = user_role_val 
        AND resource = resource_name 
        AND action = action_name
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user role
CREATE OR REPLACE FUNCTION get_user_role(user_uuid UUID) RETURNS user_role AS $$
DECLARE
    user_role_val user_role;
BEGIN
    SELECT role INTO user_role_val FROM profiles WHERE profile_id = user_uuid;
    RETURN user_role_val;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get current user's UUID from auth context
CREATE OR REPLACE FUNCTION get_current_profile_id() RETURNS UUID AS $$
BEGIN
    RETURN (
        SELECT profile_id FROM profiles
        WHERE profile_id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 

CREATE OR REPLACE FUNCTION get_current_profile_id() RETURNS UUID AS $$
BEGIN
    RETURN auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 

/*
CREATE OR REPLACE FUNCTION public.get_current_profile_id() 
RETURNS UUID AS $$
BEGIN
    RETURN auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 

CREATE OR REPLACE FUNCTION public.get_current_profile_id() 
RETURNS UUID AS $$
BEGIN
    RETURN auth.uid();
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error getting current user ID: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;*/

-- =============================================
-- AUTOMATIC TIMESTAMP AND AUDIT UPDATES
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to automatically set created_by and updated_by fields
-- Modify the audit function to handle new user creation
CREATE OR REPLACE FUNCTION set_audit_fields()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- For user creation via trigger, use the profile_id itself
    -- For normal inserts, use auth.uid() if available
    NEW.created_by = COALESCE(auth.uid(), NEW.profile_id);
    NEW.updated_by = COALESCE(auth.uid(), NEW.profile_id);
    NEW.created_at = COALESCE(NEW.created_at, NOW());
    NEW.updated_at = COALESCE(NEW.updated_at, NOW());
  ELSIF TG_OP = 'UPDATE' THEN
    -- For updates, try to use auth.uid(), fallback to existing value
    NEW.updated_by = COALESCE(auth.uid(), OLD.updated_by);
    NEW.updated_at = NOW();
    -- Keep original created_by and created_at
    NEW.created_by = OLD.created_by;
    NEW.created_at = OLD.created_at;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/*

CREATE OR REPLACE FUNCTION set_audit_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.created_by = get_current_profile_id();
        NEW.updated_by = get_current_profile_id();
        NEW.created_at = NOW();
        NEW.updated_at = NOW();
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        NEW.updated_by = get_current_profile_id();
        NEW.updated_at = NOW();
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
*/

-- Create audit triggers for all tables
CREATE TRIGGER audit_users BEFORE INSERT OR UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_clients BEFORE INSERT OR UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_client_contacts BEFORE INSERT OR UPDATE ON client_contacts FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_contracts BEFORE INSERT OR UPDATE ON contracts FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_employees BEFORE INSERT OR UPDATE ON employees FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_availability BEFORE INSERT OR UPDATE ON availability FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_client_assignments BEFORE INSERT OR UPDATE ON client_assignments FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_deliverables BEFORE INSERT OR UPDATE ON deliverables FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_time_entries BEFORE INSERT OR UPDATE ON time_entries FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_billing BEFORE INSERT OR UPDATE ON billing FOR EACH ROW EXECUTE FUNCTION set_audit_fields();
CREATE TRIGGER audit_expenses BEFORE INSERT OR UPDATE ON expenses FOR EACH ROW EXECUTE FUNCTION set_audit_fields();

-- =============================================
-- ENABLE ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deliverables ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;

-- Policy 1: Allow authenticated contract uploads 
CREATE POLICY "Allow authenticated contract uploads" ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'contract-documents' 
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Allow authenticated contract reads" ON storage.objects
FOR SELECT USING (
  bucket_id = 'contract-documents'
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Allow authenticated contract deletes" ON storage.objects
FOR DELETE USING (
  bucket_id = 'contract-documents'
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Allow authenticated expense uploads" ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'expense-documents' 
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Allow authenticated expense reads" ON storage.objects
FOR SELECT USING (
  bucket_id = 'expense-documents'
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Allow authenticated expense deletes" ON storage.objects
FOR DELETE USING (
  bucket_id = 'expense-documents'
  AND auth.role() = 'authenticated'
);

-- Drop existing policy if it exists
--DROP POLICY IF EXISTS "Allow authenticated contract uploads" ON storage.objects;

-- Create with explicit WITH CHECK clause
-- CREATE POLICY "Allow authenticated contract uploads" ON storage.objects
-- FOR INSERT 
-- TO authenticated
-- WITH CHECK (bucket_id = 'contract-documents');

-- =============================================
-- RBAC POLICIES FOR ALL TABLES
-- =============================================

-- Users table policies
CREATE POLICY "Users can view own profile or admins can view all" ON profiles
    FOR SELECT USING (
        profile_id = get_current_profile_id() OR
        user_has_permission(get_current_profile_id(), 'profiles', 'read')
    );

CREATE POLICY "Only admins can create users" ON profiles
    FOR INSERT WITH CHECK (
        user_has_permission(get_current_profile_id(), 'profiles', 'create')
    );

CREATE POLICY "Users can update own profile or admins can update any" ON profiles
    FOR UPDATE USING (
        profile_id = get_current_profile_id() OR
        user_has_permission(get_current_profile_id(), 'profiles', 'update')
    );

CREATE POLICY "Only super admins can delete users" ON profiles
    FOR DELETE USING (
        user_has_permission(get_current_profile_id(), 'profiles', 'delete')
    );

-- Role permissions policies
CREATE POLICY "Only super admins can manage role permissions" ON role_permissions
    FOR ALL USING (
        get_user_role(get_current_profile_id()) = 'super_admin'
    );

-- Clients policies
CREATE POLICY "RBAC clients select" ON clients
    FOR SELECT USING (user_has_permission(get_current_profile_id(), 'clients', 'read'));

CREATE POLICY "RBAC clients insert" ON clients
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'clients', 'create'));

CREATE POLICY "RBAC clients update" ON clients
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'clients', 'update'));

CREATE POLICY "RBAC clients delete" ON clients
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'clients', 'delete'));

-- Client contacts policies
CREATE POLICY "RBAC client_contacts select" ON client_contacts
    FOR SELECT USING (user_has_permission(get_current_profile_id(), 'clients', 'read'));

CREATE POLICY "RBAC client_contacts insert" ON client_contacts
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'clients', 'create'));

CREATE POLICY "RBAC client_contacts update" ON client_contacts
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'clients', 'update'));

CREATE POLICY "RBAC client_contacts delete" ON client_contacts
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'clients', 'delete'));

-- Contracts policies
CREATE POLICY "RBAC contracts select" ON contracts
    FOR SELECT USING (user_has_permission(get_current_profile_id(), 'contracts', 'read'));

CREATE POLICY "RBAC contracts insert" ON contracts
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'contracts', 'create'));

CREATE POLICY "RBAC contracts update" ON contracts
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'contracts', 'update'));

CREATE POLICY "RBAC contracts delete" ON contracts
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'contracts', 'delete'));

-- Employees policies
CREATE POLICY "RBAC employees select" ON employees
    FOR SELECT USING (
        user_has_permission(get_current_profile_id(), 'employees', 'read') OR
        profile_id = get_current_profile_id()
    );

CREATE POLICY "RBAC employees insert" ON employees
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'employees', 'create'));

CREATE POLICY "RBAC employees update" ON employees
    FOR UPDATE USING (
        user_has_permission(get_current_profile_id(), 'employees', 'update') OR
        profile_id = get_current_profile_id()
    );

CREATE POLICY "RBAC employees delete" ON employees
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'employees', 'delete'));

-- Availability policies
CREATE POLICY "RBAC availability select" ON availability
    FOR SELECT USING (
        user_has_permission(get_current_profile_id(), 'employees', 'read') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = availability.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC availability insert" ON availability
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'employees', 'create'));

CREATE POLICY "RBAC availability update" ON availability
    FOR UPDATE USING (
        user_has_permission(get_current_profile_id(), 'employees', 'update') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = availability.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC availability delete" ON availability
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'employees', 'delete'));

-- Client assignments policies
CREATE POLICY "RBAC client_assignments select" ON client_assignments
    FOR SELECT USING (
        user_has_permission(get_current_profile_id(), 'employees', 'read') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = client_assignments.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC client_assignments insert" ON client_assignments
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'employees', 'create'));

CREATE POLICY "RBAC client_assignments update" ON client_assignments
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'employees', 'update'));

CREATE POLICY "RBAC client_assignments delete" ON client_assignments
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'employees', 'delete'));

-- Deliverables policies
CREATE POLICY "RBAC deliverables select" ON deliverables
    FOR SELECT USING (user_has_permission(get_current_profile_id(), 'deliverables', 'read'));

CREATE POLICY "RBAC deliverables insert" ON deliverables
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'deliverables', 'create'));

CREATE POLICY "RBAC deliverables update" ON deliverables
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'deliverables', 'update'));

CREATE POLICY "RBAC deliverables delete" ON deliverables
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'deliverables', 'delete'));

-- Time entries policies
CREATE POLICY "RBAC time_entries select" ON time_entries
    FOR SELECT USING (
        user_has_permission(get_current_profile_id(), 'time_entries', 'read') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = time_entries.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC time_entries insert" ON time_entries
    FOR INSERT WITH CHECK (
        user_has_permission(get_current_profile_id(), 'time_entries', 'create') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = time_entries.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC time_entries update" ON time_entries
    FOR UPDATE USING (
        user_has_permission(get_current_profile_id(), 'time_entries', 'update') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = time_entries.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC time_entries delete" ON time_entries
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'time_entries', 'delete'));

-- Billing policies
CREATE POLICY "RBAC billing select" ON billing
    FOR SELECT USING (user_has_permission(get_current_profile_id(), 'billing', 'read'));

CREATE POLICY "RBAC billing insert" ON billing
    FOR INSERT WITH CHECK (user_has_permission(get_current_profile_id(), 'billing', 'create'));

CREATE POLICY "RBAC billing update" ON billing
    FOR UPDATE USING (user_has_permission(get_current_profile_id(), 'billing', 'update'));

CREATE POLICY "RBAC billing delete" ON billing
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'billing', 'delete'));

-- Expenses policies
CREATE POLICY "RBAC expenses select" ON expenses
    FOR SELECT USING (
        user_has_permission(get_current_profile_id(), 'expenses', 'read') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = expenses.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC expenses insert" ON expenses
    FOR INSERT WITH CHECK (
        user_has_permission(get_current_profile_id(), 'expenses', 'create') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = expenses.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC expenses update" ON expenses
    FOR UPDATE USING (
        user_has_permission(get_current_profile_id(), 'expenses', 'update') OR
        EXISTS(SELECT 1 FROM employees WHERE employee_id = expenses.employee_id AND profile_id = get_current_profile_id())
    );

CREATE POLICY "RBAC expenses delete" ON expenses
    FOR DELETE USING (user_has_permission(get_current_profile_id(), 'expenses', 'delete'));

-- =============================================
-- AI AGENT HELPER VIEWS FOR CONVERSATIONAL QUERIES
-- =============================================

-- Comprehensive client overview for AI queries
CREATE VIEW client_overview AS
SELECT 
    c.client_id,
    c.client_name,
    c.primary_contact_name,
    c.primary_contact_email,
    c.company_size,
    c.industry,
    c.notes,
    COUNT(DISTINCT ct.contract_id) as active_contracts,
    COUNT(DISTINCT ca.assignment_id) as active_assignments,
    COALESCE(SUM(ct.current_amount), 0) as total_contract_value,
    c.created_at
FROM clients c
LEFT JOIN contracts ct ON c.client_id = ct.client_id AND ct.status = 'Active'
LEFT JOIN client_assignments ca ON c.client_id = ca.client_id AND (ca.end_date IS NULL OR ca.end_date >= CURRENT_DATE)
LEFT JOIN profiles u ON c.created_by = u.profile_id
GROUP BY c.client_id, c.client_name, c.primary_contact_name, c.primary_contact_email, c.company_size, c.industry, c.notes, c.created_at;

-- Employee workload summary for AI queries
CREATE VIEW employee_workload AS
SELECT 
    e.employee_id,
    e.name as employee_name,
    e.employment_type,
    e.status,
    e.rate,
    u.role as user_role,
    u.department,
    COUNT(DISTINCT ca.client_id) as active_clients,
    COUNT(DISTINCT d.deliverable_id) as active_deliverables,
    COALESCE(SUM(te.hours_worked), 0) as total_hours_this_month
FROM employees e
LEFT JOIN profiles u ON e.profile_id = u.profile_id
LEFT JOIN client_assignments ca ON e.employee_id = ca.employee_id AND (ca.end_date IS NULL OR ca.end_date >= CURRENT_DATE)
LEFT JOIN deliverables d ON e.employee_id = d.assigned_employees AND d.status IN ('In Progress', 'Active')
LEFT JOIN time_entries te ON e.employee_id = te.employee_id AND DATE_TRUNC('month', te.date) = DATE_TRUNC('month', CURRENT_DATE)
WHERE e.status = 'Active'
GROUP BY e.employee_id, e.name, e.employment_type, e.status, e.rate, u.role, u.department;

-- User management view with role information
CREATE VIEW user_management AS
SELECT 
    u.profile_id,
    u.email,
    u.full_name,
    u.role,
    u.status,
    u.department,
    u.job_title,
    u.hire_date,
    u.last_login,
    u.created_at,
    e.employee_id,
    e.name as employee_name,
    e.employment_type
FROM profiles u
LEFT JOIN employees e ON u.profile_id = e.profile_id;

-- Role permissions summary view
CREATE VIEW role_permissions_summary AS
SELECT 
    role,
    resource,
    array_agg(action ORDER BY action) as actions
FROM role_permissions
GROUP BY role, resource
ORDER BY role, resource;

-- Recent activity summary for AI queries
CREATE VIEW recent_activity AS
SELECT 
    'time_entry' as activity_type,
    te.time_entry_id as record_id,
    te.employee_name,
    te.client_name,
    te.description_of_work as description,
    te.date as activity_date,
    te.hours_worked::text as details,
    u.full_name as created_by_name
FROM time_entries te
LEFT JOIN profiles u ON te.created_by = u.profile_id
WHERE te.date >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT 
    'billing' as activity_type,
    b.invoice_id as record_id,
    'System' as employee_name,
    b.client_name,
    'Invoice generated' as description,
    b.invoice_date as activity_date,
    b.total_amount::text as details,
    u.full_name as created_by_name
FROM billing b
LEFT JOIN profiles u ON b.created_by = u.profile_id
WHERE b.invoice_date >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT 
    'expense' as activity_type,
    ex.expense_id as record_id,
    ex.employee_name,
    ex.client_name,
    ex.description,
    ex.date as activity_date,
    ex.amount::text as details,
    u.full_name as created_by_name
FROM expenses ex
LEFT JOIN profiles u ON ex.created_by = u.profile_id
WHERE ex.date >= CURRENT_DATE - INTERVAL '30 days'

ORDER BY activity_date DESC;

-- Project status summary for AI queries
CREATE VIEW project_status AS
SELECT 
    d.deliverable_id,
    d.name as deliverable_name,
    d.client_name,
    d.assigned_employee_name,
    d.status,
    d.start_date,
    d.due_date,
    d.completion_date,
    d.billing_amount,
    CASE 
        WHEN d.completion_date IS NOT NULL THEN 'Completed'
        WHEN d.due_date < CURRENT_DATE AND d.completion_date IS NULL THEN 'Overdue'
        WHEN d.due_date <= CURRENT_DATE + INTERVAL '7 days' THEN 'Due Soon'
        ELSE 'On Track'
    END as urgency_status,
    COALESCE(SUM(te.hours_worked), 0) as total_hours_logged,
    u.full_name as created_by_name
FROM deliverables d
LEFT JOIN time_entries te ON d.deliverable_id = te.deliverable_id
LEFT JOIN profiles u ON d.created_by = u.profile_id
GROUP BY d.deliverable_id, d.name, d.client_name, d.assigned_employee_name, d.status, d.start_date, d.due_date, d.completion_date, d.billing_amount, u.full_name;


-- Function to automatically create user record when auth user is created

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (
    profile_id,
    email
  ) VALUES (
    NEW.id,
    NEW.email
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

--RBAC function    

CREATE OR REPLACE FUNCTION user_has_permission(
    user_uuid UUID,
    resource_name VARCHAR,
    action_name VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    user_role_val user_role;
    has_permission BOOLEAN := FALSE;
BEGIN
    SELECT role INTO user_role_val FROM profiles WHERE profile_id = user_uuid;
    
    SELECT EXISTS(
        SELECT 1 FROM role_permissions 
        WHERE role = user_role_val 
        AND resource = resource_name 
        AND action = action_name
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_user_role(user_uuid UUID) RETURNS user_role AS $$
DECLARE
    user_role_val user_role;
BEGIN
    SELECT role INTO user_role_val FROM profiles WHERE profile_id = user_uuid;
    RETURN user_role_val;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

=========================================================

INSERT INTO public.profiles (
    profile_id,
    email,
    first_name,
    role,
    status,
    created_at,
    created_by,
    updated_by
)
SELECT 
    au.id AS profile_id,
    au.email,
    INITCAP(
        REGEXP_REPLACE(
            SPLIT_PART(au.email, '@', 1), 
            '[^a-zA-Z]', 
            '', 
            'g'
        )
    ) AS first_name,
    'viewer' AS role,
    'active' AS status,
    au.created_at,
    au.id AS created_by,
    au.id AS updated_by
FROM 
    auth.users au
WHERE 
    NOT EXISTS (
        SELECT 1 
        FROM public.profiles p 
        WHERE p.profile_id = au.id
    )
ON CONFLICT (profile_id) DO NOTHING;



=================================
/*SELECT 
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers 
WHERE event_object_table = 'profiles';
*/

select * from profiles