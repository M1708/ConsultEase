import pytest
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from langchain_core.messages import HumanMessage

# Load environment variables BEFORE importing any modules
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# It's better to set the python path to avoid relative import issues
import sys
# Add the backend directory to the python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aiagents.graph.graph import app as agent_app

# --- Database Setup ---

@pytest.fixture(scope="module")
def db_session():
    """Creates a new database session for a test module."""
    # Load the .env file from the correct location (backend/.env)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL not found in backend/.env file. Please ensure it is set.")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        # Clean up tables before each test
        db.execute(text("DELETE FROM contracts;"))
        db.execute(text("DELETE FROM clients;"))
        db.execute(text("DELETE FROM employees;"))
        db.execute(text("DELETE FROM profiles;"))
        db.commit()
        yield db
    finally:
        db.close()

# --- Helper Function ---

async def invoke_graph(message: str, db_session):
    """Helper function to invoke the graph and print all events."""
    print(f"\n--- Running Test Scenario: '{message}' ---")
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "data": {"database": db_session}
    }
    
    # Stream all events from the graph run using async
    async for event in agent_app.astream(initial_state):
        print(event)
        print("---")
    print(f"--- Scenario Finished: '{message}' ---")

# --- Test Scenarios ---

@pytest.mark.asyncio
async def test_scenario_1_find_contracts(db_session):
    """Test finding contracts for an existing client."""
    # First, ensure a client and contract exist to be found.
    db_session.execute(text("INSERT INTO clients (client_name, industry) VALUES ('TestCorp', 'Tech');"))
    client_id = db_session.execute(text("SELECT client_id FROM clients WHERE client_name = 'TestCorp'")).scalar_one()
    db_session.execute(text(f"INSERT INTO contracts (client_id, contract_type, original_amount) VALUES ({client_id}, 'Fixed', 5000);"))
    db_session.commit()
    
    await invoke_graph("Find contracts for TestCorp", db_session)

@pytest.mark.asyncio
async def test_scenario_2_update_contract(db_session):
    """Test updating a contract for an existing client."""
    # Assumes the client and contract from scenario 1 exist.
    contract_id = db_session.execute(text("SELECT c.contract_id FROM contracts c JOIN clients cl ON c.client_id = cl.client_id WHERE cl.client_name = 'TestCorp' LIMIT 1")).scalar_one()
    message = f"Update contract {contract_id} for TestCorp to have a status of 'completed'"
    await invoke_graph(message, db_session)

@pytest.mark.asyncio
async def test_scenario_3_create_contract_for_new_client(db_session):
    """Test creating a contract for a client that does not yet exist."""
    # Ensure the client does not exist before running the test
    client_name = "New Galactic Ventures"
    db_session.execute(text(f"DELETE FROM contracts WHERE client_id IN (SELECT client_id FROM clients WHERE client_name = '{client_name}');"))
    db_session.execute(text(f"DELETE FROM clients WHERE client_name = '{client_name}';"))
    db_session.commit()

    message = f"First, create a new client called '{client_name}' in the 'Space Exploration' industry. Then, draft a retainer contract for them for $100,000 per month."
    await invoke_graph(message, db_session)

@pytest.mark.asyncio
async def test_scenario_4_create_contract_for_existing_client(db_session):
    """Test creating a contract for a client that already exists."""
    # This test uses the client created in scenario 3.
    client_name = "New Galactic Ventures"
    message = f"Draft a new fixed-price contract for our existing client, '{client_name}', for a total of $500,000."
    await invoke_graph(message, db_session)

@pytest.mark.asyncio
async def test_scenario_5_create_employee(db_session):
    """Test creating a new employee."""
    # Ensure a profile exists for the employee
    db_session.execute(text("INSERT INTO profiles (profile_id, email, first_name, role, status) VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'john.doe@example.com', 'John', 'employee', 'active');"))
    db_session.commit()

    message = "Create a new employee named John Doe, email john.doe@example.com, as a permanent full-time employee with job title Software Engineer in the Engineering department, hired on 2023-01-15."
    await invoke_graph(message, db_session)

@pytest.mark.asyncio
async def test_scenario_6_update_employee(db_session):
    """Test updating an existing employee."""
    # Ensure an employee exists to be updated
    db_session.execute(text("INSERT INTO profiles (profile_id, email, first_name, role, status) VALUES ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'jane.smith@example.com', 'Jane', 'employee', 'active');"))
    db_session.execute(text("INSERT INTO employees (employee_id, profile_id, job_title, department, employment_type, full_time_part_time, hire_date) VALUES (1, 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'QA Engineer', 'Testing', 'permanent', 'full_time', '2022-03-01');"))
    db_session.commit()

    message = "Update Jane Smith's job title to Senior QA Engineer and department to Quality Assurance."
    await invoke_graph(message, db_session)

@pytest.mark.asyncio
async def test_scenario_7_search_employee(db_session):
    """Test searching for an employee."""
    # Ensure employees exist to be searched
    db_session.execute(text("INSERT INTO profiles (profile_id, email, first_name, role, status) VALUES ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'alice.johnson@example.com', 'Alice', 'employee', 'active');"))
    db_session.execute(text("INSERT INTO employees (employee_id, profile_id, job_title, department, employment_type, full_time_part_time, hire_date) VALUES (2, 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'Project Manager', 'Operations', 'permanent', 'full_time', '2021-06-10');"))
    db_session.commit()

    message = "Search for employees in the Operations department."
    await invoke_graph(message, db_session)
