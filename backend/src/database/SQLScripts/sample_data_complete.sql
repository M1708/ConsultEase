-- Sample Data for Complete ConsultEase Database Schema
-- Run this after executing complete_database_schema.sql
-- This includes sample users, roles, and all business data

-- =============================================
-- SAMPLE USERS DATA
-- =============================================

-- Insert sample users (these would normally be created through Supabase Auth)
-- Note: In production, these would be created via the application's signup process
INSERT INTO users (user_id, email, first_name, last_name, role, status, department, job_title, hire_date, phone) VALUES
(uuid_generate_v4(), 'admin@consultease.com', 'System', 'Administrator', 'super_admin', 'active', 'IT', 'System Administrator', '2024-01-01', '+1-555-0001'),
(uuid_generate_v4(), 'manager@consultease.com', 'Project', 'Manager', 'manager', 'active', 'Operations', 'Project Manager', '2024-01-15', '+1-555-0002'),
(uuid_generate_v4(), 'alice.johnson@consultease.com', 'Alice', 'Johnson', 'employee', 'active', 'Consulting', 'Senior Consultant', '2024-02-01', '+1-555-0003'),
(uuid_generate_v4(), 'bob.smith@consultease.com', 'Bob', 'Smith', 'employee', 'active', 'Consulting', 'Business Analyst', '2024-02-15', '+1-555-0004'),
(uuid_generate_v4(), 'jane.doe@acme.com', 'Jane', 'Doe', 'client', 'active', 'Operations', 'COO', '2024-03-01', '+1-555-1001'),
(uuid_generate_v4(), 'viewer@consultease.com', 'Demo', 'Viewer', 'viewer', 'active', 'Sales', 'Sales Representative', '2024-03-15', '+1-555-0005');

-- =============================================
-- SAMPLE CLIENTS DATA
-- =============================================

INSERT INTO clients (client_id, client_name, primary_contact_name, primary_contact_email, company_size, industry, notes) VALUES
('CL001', 'Acme Corporation', 'Jane Doe', 'jane.doe@acme.com', 'Mid-size', 'Manufacturing', 'Key strategic client with multiple ongoing projects'),
('CL002', 'TechStart Inc', 'John Smith', 'john.smith@techstart.com', 'Small', 'Technology', 'Fast-growing startup, potential for expansion'),
('CL003', 'Global Retail Co', 'Sarah Wilson', 'sarah.wilson@globalretail.com', 'Large', 'Retail', 'Enterprise client with complex requirements'),
('CL004', 'Healthcare Plus', 'Dr. Michael Brown', 'michael.brown@healthcareplus.com', 'Mid-size', 'Healthcare', 'Compliance-focused healthcare organization'),
('CL005', 'Finance Solutions', 'Lisa Chen', 'lisa.chen@financesolutions.com', 'Small', 'Financial Services', 'Boutique financial advisory firm');

-- =============================================
-- SAMPLE CLIENT CONTACTS DATA
-- =============================================

INSERT INTO client_contacts (contact_id, client_id, name, email, role, last_interaction_summary, client_name) VALUES
('CC001', 'CL001', 'Jane Doe', 'jane.doe@acme.com', 'COO', 'Discussed Q3 roadmap and resource allocation on 2024-06-10', 'Acme Corporation'),
('CC002', 'CL001', 'Mark Johnson', 'mark.johnson@acme.com', 'IT Director', 'Technical requirements review for new system implementation', 'Acme Corporation'),
('CC003', 'CL002', 'John Smith', 'john.smith@techstart.com', 'CEO', 'Initial consultation meeting about process optimization', 'TechStart Inc'),
('CC004', 'CL003', 'Sarah Wilson', 'sarah.wilson@globalretail.com', 'VP Operations', 'Supply chain analysis project kickoff meeting', 'Global Retail Co'),
('CC005', 'CL004', 'Dr. Michael Brown', 'michael.brown@healthcareplus.com', 'Chief Medical Officer', 'Compliance audit preparation discussion', 'Healthcare Plus'),
('CC006', 'CL005', 'Lisa Chen', 'lisa.chen@financesolutions.com', 'Managing Partner', 'Risk management framework consultation', 'Finance Solutions');

-- =============================================
-- SAMPLE EMPLOYEES DATA
-- =============================================

INSERT INTO employees (employee_id, user_id, name, employment_type, status, full_time_part_time, committed_hours_per_week, rate_type, rate, start_date, email, nda_file_link, contract_file_link) VALUES
('E001', (SELECT user_id FROM users WHERE email = 'alice.johnson@consultease.com'), 'Alice Johnson', 'Full-time', 'Active', 'Full-Time', 40, 'Salary', 95000.00, '2024-02-01', 'alice.johnson@consultease.com', 'https://docs.example.com/nda-alice.pdf', 'https://docs.example.com/contract-alice.pdf'),
('E002', (SELECT user_id FROM users WHERE email = 'bob.smith@consultease.com'), 'Bob Smith', 'Full-time', 'Active', 'Full-Time', 40, 'Salary', 85000.00, '2024-02-15', 'bob.smith@consultease.com', 'https://docs.example.com/nda-bob.pdf', 'https://docs.example.com/contract-bob.pdf'),
('E003', NULL, 'Carol Davis', 'Contractor', 'Active', 'Part-Time', 20, 'Per Hour', 75.00, '2024-03-01', 'carol.davis@freelance.com', 'https://docs.example.com/nda-carol.pdf', 'https://docs.example.com/contract-carol.pdf'),
('E004', NULL, 'David Wilson', 'Contractor', 'Active', 'Part-Time', 25, 'Per Hour', 80.00, '2024-03-15', 'david.wilson@consultant.com', 'https://docs.example.com/nda-david.pdf', 'https://docs.example.com/contract-david.pdf');

-- =============================================
-- SAMPLE CONTRACTS DATA
-- =============================================

INSERT INTO contracts (contract_id, client_id, contract_type, start_date, end_date, original_amount, current_amount, billing_frequency, status, billing_prompt_next_date, amendments, notes) VALUES
('CT001', 'CL001', 'Time & Material', '2024-01-01', '2024-12-31', 150000.00, 150000.00, 'Monthly', 'Active', '2024-09-01', 'None', 'Includes optional extension clause for 2025'),
('CT002', 'CL002', 'Fixed Price', '2024-03-01', '2024-08-31', 75000.00, 75000.00, 'Milestone', 'Active', '2024-09-15', 'Scope expanded in Amendment 1', 'Process optimization project'),
('CT003', 'CL003', 'Time & Material', '2024-02-15', '2025-02-14', 200000.00, 180000.00, 'Monthly', 'Active', '2024-09-01', 'Budget reduced by 10%', 'Supply chain analysis and optimization'),
('CT004', 'CL004', 'Fixed Price', '2024-04-01', '2024-10-31', 120000.00, 120000.00, 'Monthly', 'Active', '2024-09-01', 'None', 'Compliance audit and framework implementation'),
('CT005', 'CL005', 'Time & Material', '2024-05-01', '2024-11-30', 90000.00, 90000.00, 'Monthly', 'Active', '2024-09-01', 'None', 'Risk management consulting');

-- =============================================
-- SAMPLE AVAILABILITY DATA
-- =============================================

INSERT INTO availability (availability_id, employee_id, start_date, end_date, available_hours_per_day, notes) VALUES
('A001', 'E001', '2024-08-01', '2024-08-31', 8, 'Full availability for August'),
('A002', 'E002', '2024-08-01', '2024-08-31', 8, 'Full availability for August'),
('A003', 'E003', '2024-08-15', '2024-08-31', 4, 'Part-time availability due to other commitments'),
('A004', 'E004', '2024-08-01', '2024-08-15', 6, 'Reduced hours due to training'),
('A005', 'E001', '2024-09-01', '2024-09-30', 6, 'Reduced availability due to vacation planning');

-- =============================================
-- SAMPLE CLIENT ASSIGNMENTS DATA
-- =============================================

INSERT INTO client_assignments (assignment_id, employee_id, client_id, start_date, end_date, role, employee_name, client_name) VALUES
('AS001', 'E001', 'CL001', '2024-01-15', '2024-12-15', 'Lead Consultant', 'Alice Johnson', 'Acme Corporation'),
('AS002', 'E002', 'CL001', '2024-02-01', '2024-12-15', 'Business Analyst', 'Bob Smith', 'Acme Corporation'),
('AS003', 'E001', 'CL003', '2024-02-15', '2025-02-14', 'Senior Consultant', 'Alice Johnson', 'Global Retail Co'),
('AS004', 'E003', 'CL002', '2024-03-01', '2024-08-31', 'Process Consultant', 'Carol Davis', 'TechStart Inc'),
('AS005', 'E004', 'CL004', '2024-04-01', '2024-10-31', 'Compliance Specialist', 'David Wilson', 'Healthcare Plus'),
('AS006', 'E002', 'CL005', '2024-05-01', '2024-11-30', 'Risk Analyst', 'Bob Smith', 'Finance Solutions');

-- =============================================
-- SAMPLE DELIVERABLES DATA
-- =============================================

INSERT INTO deliverables (deliverable_id, contract_id, name, description, assigned_employees, start_date, due_date, completion_date, status, billing_basis, billing_amount, notes, client_name, assigned_employee_name) VALUES
('D001', 'CT001', 'Process Audit', 'Comprehensive audit of current business processes and identification of optimization opportunities', 'E001,E002', '2024-02-01', '2024-03-31', '2024-03-28', 'Complete', 'Milestone', 25000.00, 'Delivered ahead of schedule with excellent client feedback', 'Acme Corporation', 'Alice Johnson'),
('D002', 'CT001', 'System Integration Plan', 'Detailed plan for integrating new ERP system with existing infrastructure', 'E001', '2024-04-01', '2024-05-31', NULL, 'In Progress', 'Milestone', 30000.00, 'Currently in development phase', 'Acme Corporation', 'Alice Johnson'),
('D003', 'CT002', 'Process Optimization Framework', 'Development of standardized process optimization framework for startup operations', 'E003', '2024-03-01', '2024-06-30', NULL, 'In Progress', 'Fixed Price', 75000.00, 'On track for completion', 'TechStart Inc', 'Carol Davis'),
('D004', 'CT003', 'Supply Chain Analysis', 'Analysis of current supply chain processes and recommendations for improvement', 'E001', '2024-02-15', '2024-08-15', NULL, 'In Progress', 'Time & Material', 0.00, 'Ongoing analysis with monthly reports', 'Global Retail Co', 'Alice Johnson'),
('D005', 'CT004', 'Compliance Framework', 'Implementation of healthcare compliance framework and audit procedures', 'E004', '2024-04-01', '2024-09-30', NULL, 'In Progress', 'Fixed Price', 120000.00, 'Phase 1 completed successfully', 'Healthcare Plus', 'David Wilson');

-- =============================================
-- SAMPLE TIME ENTRIES DATA
-- =============================================

INSERT INTO time_entries (time_entry_id, employee_id, contract_id, deliverable_id, client_id, date, hours_worked, description_of_work, billable, billing_rate, billed, invoice_id, entered_by, entry_timestamp, last_modified_by, last_modified_timestamp, source, employee_name, deliverable_name, client_name) VALUES
('TE001', 'E001', 'CT001', 'D001', 'CL001', '2024-02-15', 8.00, 'Initial process mapping and stakeholder interviews', true, 125.00, true, 'INV001', 'E001', '2024-02-15 18:00:00+00', 'E001', '2024-02-15 18:00:00+00', 'Manual', 'Alice Johnson', 'Process Audit', 'Acme Corporation'),
('TE002', 'E002', 'CT001', 'D001', 'CL001', '2024-02-16', 6.00, 'Data collection and analysis for process audit', true, 100.00, true, 'INV001', 'E002', '2024-02-16 17:30:00+00', 'E002', '2024-02-16 17:30:00+00', 'Manual', 'Bob Smith', 'Process Audit', 'Acme Corporation'),
('TE003', 'E001', 'CT001', 'D002', 'CL001', '2024-04-10', 8.00, 'ERP system requirements gathering and documentation', true, 125.00, false, NULL, 'E001', '2024-04-10 18:00:00+00', 'E001', '2024-04-10 18:00:00+00', 'Manual', 'Alice Johnson', 'System Integration Plan', 'Acme Corporation'),
('TE004', 'E003', 'CT002', 'D003', 'CL002', '2024-03-20', 4.00, 'Process optimization framework design', true, 75.00, false, NULL, 'E003', '2024-03-20 16:00:00+00', 'E003', '2024-03-20 16:00:00+00', 'Manual', 'Carol Davis', 'Process Optimization Framework', 'TechStart Inc'),
('TE005', 'E001', 'CT003', 'D004', 'CL003', '2024-07-15', 8.00, 'Supply chain process analysis and documentation', true, 125.00, false, NULL, 'E001', '2024-07-15 18:00:00+00', 'E001', '2024-07-15 18:00:00+00', 'Manual', 'Alice Johnson', 'Supply Chain Analysis', 'Global Retail Co'),
('TE006', 'E004', 'CT004', 'D005', 'CL004', '2024-06-10', 6.00, 'Compliance framework development and testing', true, 80.00, false, NULL, 'E004', '2024-06-10 17:00:00+00', 'E004', '2024-06-10 17:00:00+00', 'Manual', 'David Wilson', 'Compliance Framework', 'Healthcare Plus'),
('TE007', 'E002', 'CT005', NULL, 'CL005', '2024-07-20', 4.00, 'Risk assessment methodology development', true, 100.00, false, NULL, 'E002', '2024-07-20 16:00:00+00', 'E002', '2024-07-20 16:00:00+00', 'Manual', 'Bob Smith', NULL, 'Finance Solutions');

-- =============================================
-- SAMPLE BILLING DATA
-- =============================================

INSERT INTO billing (invoice_id, client_id, contract_id, billing_period_start, billing_period_end, invoice_date, time_entry_ids, total_hours, total_amount, status, invoice_file_link, notes, client_name, contract_type) VALUES
('INV001', 'CL001', 'CT001', '2024-02-01', '2024-02-29', '2024-03-05', 'TE001,TE002', 14.00, 1600.00, 'Paid', 'https://docs.example.com/invoices/INV001.pdf', 'Process audit milestone payment', 'Acme Corporation', 'Time & Material'),
('INV002', 'CL001', 'CT001', '2024-03-01', '2024-03-31', '2024-04-05', 'TE001,TE002', 32.00, 4000.00, 'Paid', 'https://docs.example.com/invoices/INV002.pdf', 'Completion of process audit deliverable', 'Acme Corporation', 'Time & Material'),
('INV003', 'CL002', 'CT002', '2024-03-01', '2024-03-31', '2024-04-05', 'TE004', 16.00, 1200.00, 'Sent', 'https://docs.example.com/invoices/INV003.pdf', 'Initial milestone for process optimization', 'TechStart Inc', 'Fixed Price'),
('INV004', 'CL003', 'CT003', '2024-07-01', '2024-07-31', '2024-08-05', 'TE005', 24.00, 3000.00, 'Pending', NULL, 'Monthly billing for supply chain analysis', 'Global Retail Co', 'Time & Material'),
('INV005', 'CL004', 'CT004', '2024-06-01', '2024-06-30', '2024-07-05', 'TE006', 24.00, 1920.00, 'Sent', 'https://docs.example.com/invoices/INV005.pdf', 'Compliance framework development phase', 'Healthcare Plus', 'Fixed Price');

-- =============================================
-- SAMPLE EXPENSES DATA
-- =============================================

INSERT INTO expenses (expense_id, employee_id, client_id, deliverable_id, date, expense_category, description, amount, currency, billable_to_client, reimbursable, receipt_link, status, entered_by, entry_timestamp, last_modified_by, last_modified_timestamp, source, employee_name, client_name, deliverable_name) VALUES
('EX001', 'E001', 'CL001', 'D001', '2024-02-20', 'Travel', 'Taxi to client site for stakeholder interviews', 45.00, 'USD', true, true, 'https://docs.example.com/receipts/EX001.jpg', 'Approved', 'E001', '2024-02-20 20:00:00+00', 'E001', '2024-02-20 20:00:00+00', 'Mobile', 'Alice Johnson', 'Acme Corporation', 'Process Audit'),
('EX002', 'E002', 'CL001', 'D001', '2024-02-22', 'Meals', 'Client lunch meeting during process review', 85.00, 'USD', true, true, 'https://docs.example.com/receipts/EX002.jpg', 'Approved', 'E002', '2024-02-22 19:30:00+00', 'E002', '2024-02-22 19:30:00+00', 'Mobile', 'Bob Smith', 'Acme Corporation', 'Process Audit'),
('EX003', 'E003', 'CL002', 'D003', '2024-03-25', 'Software', 'Process modeling software license', 299.00, 'USD', true, false, 'https://docs.example.com/receipts/EX003.pdf', 'Approved', 'E003', '2024-03-25 16:00:00+00', 'E003', '2024-03-25 16:00:00+00', 'Web', 'Carol Davis', 'TechStart Inc', 'Process Optimization Framework'),
('EX004', 'E001', 'CL003', 'D004', '2024-07-18', 'Travel', 'Flight to client location for supply chain site visit', 450.00, 'USD', true, true, 'https://docs.example.com/receipts/EX004.pdf', 'Pending', 'E001', '2024-07-18 21:00:00+00', 'E001', '2024-07-18 21:00:00+00', 'Mobile', 'Alice Johnson', 'Global Retail Co', 'Supply Chain Analysis'),
('EX005', 'E004', 'CL004', 'D005', '2024-06-15', 'Training', 'Healthcare compliance certification course', 750.00, 'USD', false, true, 'https://docs.example.com/receipts/EX005.pdf', 'Approved', 'E004', '2024-06-15 18:00:00+00', 'E004', '2024-06-15 18:00:00+00', 'Web', 'David Wilson', 'Healthcare Plus', 'Compliance Framework');

-- =============================================
-- VERIFICATION QUERIES
-- =============================================

-- Count records in each table
SELECT 'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'role_permissions', COUNT(*) FROM role_permissions
UNION ALL
SELECT 'clients', COUNT(*) FROM clients
UNION ALL
SELECT 'client_contacts', COUNT(*) FROM client_contacts
UNION ALL
SELECT 'contracts', COUNT(*) FROM contracts
UNION ALL
SELECT 'employees', COUNT(*) FROM employees
UNION ALL
SELECT 'availability', COUNT(*) FROM availability
UNION ALL
SELECT 'client_assignments', COUNT(*) FROM client_assignments
UNION ALL
SELECT 'deliverables', COUNT(*) FROM deliverables
UNION ALL
SELECT 'time_entries', COUNT(*) FROM time_entries
UNION ALL
SELECT 'billing', COUNT(*) FROM billing
UNION ALL
SELECT 'expenses', COUNT(*) FROM expenses
ORDER BY table_name;

-- Test the AI helper views
SELECT 'Testing client_overview view' as test_name;
SELECT * FROM client_overview LIMIT 3;

SELECT 'Testing employee_workload view' as test_name;
SELECT * FROM employee_workload LIMIT 3;

SELECT 'Testing user_management view' as test_name;
SELECT * FROM user_management LIMIT 3;

SELECT 'Testing role_permissions_summary view' as test_name;
SELECT * FROM role_permissions_summary WHERE role IN ('super_admin', 'employee') LIMIT 10;

SELECT 'Testing recent_activity view' as test_name;
SELECT * FROM recent_activity LIMIT 5;

SELECT 'Testing project_status view' as test_name;
SELECT * FROM project_status LIMIT 3;

-- Test RBAC functions
SELECT 'Testing RBAC functions' as test_name;
SELECT 
    u.email,
    u.role,
    user_has_permission(u.user_id, 'clients', 'read') as can_read_clients,
    user_has_permission(u.user_id, 'users', 'create') as can_create_users,
    user_has_permission(u.user_id, 'time_entries', 'create') as can_create_time_entries
FROM users u
WHERE u.email IN ('admin@consultease.com', 'alice.johnson@consultease.com', 'jane.doe@acme.com')
LIMIT 3;

-- Test foreign key relationships
SELECT 'Testing foreign key relationships' as test_name;
SELECT 
    c.client_name,
    COUNT(DISTINCT ct.contract_id) as contracts,
    COUNT(DISTINCT ca.assignment_id) as assignments,
    COUNT(DISTINCT te.time_entry_id) as time_entries,
    COUNT(DISTINCT b.invoice_id) as invoices
FROM clients c
LEFT JOIN contracts ct ON c.client_id = ct.client_id
LEFT JOIN client_assignments ca ON c.client_id = ca.client_id
LEFT JOIN time_entries te ON c.client_id = te.client_id
LEFT JOIN billing b ON c.client_id = b.client_id
GROUP BY c.client_id, c.client_name
ORDER BY c.client_name;

-- Test email validation
SELECT 'Testing email validation' as test_name;
-- This should work
SELECT 'Valid email test: ' || 'test@example.com'::valid_email as test_result;

-- Uncomment the following line to test invalid email (should fail)
-- SELECT 'Invalid email test: ' || 'invalid-email'::valid_email as test_result;
