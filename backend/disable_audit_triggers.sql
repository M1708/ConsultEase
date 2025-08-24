-- Disable audit triggers that are causing conflicts with application-level authentication
-- The application now properly handles created_by and updated_by fields through authenticated API endpoints

-- Drop all audit triggers
DROP TRIGGER IF EXISTS audit_clients ON clients;
DROP TRIGGER IF EXISTS audit_client_contacts ON client_contacts;
DROP TRIGGER IF EXISTS audit_contracts ON contracts;
DROP TRIGGER IF EXISTS audit_deliverables ON deliverables;
DROP TRIGGER IF EXISTS audit_time_entries ON time_entries;
DROP TRIGGER IF EXISTS audit_expenses ON expenses;
DROP TRIGGER IF EXISTS audit_users ON users;
DROP TRIGGER IF EXISTS audit_profiles ON profiles;
DROP TRIGGER IF EXISTS audit_employees ON employees;
DROP TRIGGER IF EXISTS audit_availability ON availability;
DROP TRIGGER IF EXISTS audit_client_assignments ON client_assignments;
DROP TRIGGER IF EXISTS audit_billing ON billing;

-- Drop the problematic audit function
DROP FUNCTION IF EXISTS set_audit_fields();

-- Note: The application code now handles audit fields properly through:
-- 1. Authenticated API endpoints that use current_user.user_id
-- 2. Internal functions that require explicit user_id parameter
-- 3. AI agent tools that extract user_id from authenticated context
-- 
-- This eliminates the need for database-level triggers and resolves the
-- "UndefinedColumn: profile_id" error since the trigger was trying to access
-- a field that doesn't exist in non-profile tables.
