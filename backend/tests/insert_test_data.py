#!/usr/bin/env python3
"""
Script to insert test data into the database for testing client update functionality
"""
import asyncio
from sqlalchemy.orm import Session
from src.database.core.database import get_db
from src.database.core.models import Client, Contract
from datetime import date, datetime
from decimal import Decimal

def insert_test_data():
    """Insert test clients and contracts"""
    try:
        # Get database session
        db = next(get_db())
        
        print("🔧 Inserting test data...")
        
        # Insert test clients
        clients_data = [
            {
                "client_id": 1,
                "client_name": "TechCorp",
                "primary_contact_name": "John Smith",
                "primary_contact_email": "john.smith@techcorp.com",
                "company_size": "Mid-size",
                "industry": "Technology",
                "notes": "Technology consulting client",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            },
            {
                "client_id": 2,
                "client_name": "Acme Corporation",
                "primary_contact_name": "Jane Doe",
                "primary_contact_email": "jane.doe@acme.com",
                "company_size": "Large",
                "industry": "Manufacturing",
                "notes": "Manufacturing client with multiple projects",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            },
            {
                "client_id": 3,
                "client_name": "Global Retail Co",
                "primary_contact_name": "Sarah Wilson",
                "primary_contact_email": "sarah.wilson@globalretail.com",
                "company_size": "Large",
                "industry": "Retail",
                "notes": "Enterprise retail client",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            }
        ]
        
        # Insert clients
        for client_data in clients_data:
            # Check if client already exists
            existing_client = db.query(Client).filter(Client.client_id == client_data["client_id"]).first()
            if not existing_client:
                client = Client(**client_data)
                db.add(client)
                print(f"✅ Added client: {client_data['client_name']}")
            else:
                print(f"⚠️ Client already exists: {client_data['client_name']}")
        
        # Insert test contracts
        contracts_data = [
            {
                "contract_id": 1,
                "client_id": 1,  # TechCorp
                "contract_type": "Time & Material",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 12, 31),
                "original_amount": Decimal("150000.00"),
                "current_amount": Decimal("150000.00"),
                "billing_frequency": "Monthly",
                "status": "active",
                "billing_prompt_next_date": date(2024, 9, 1),
                "notes": "Technology consulting contract",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            },
            {
                "contract_id": 2,
                "client_id": 2,  # Acme Corporation
                "contract_type": "Fixed Price",
                "start_date": date(2024, 2, 1),
                "end_date": date(2024, 11, 30),
                "original_amount": Decimal("200000.00"),
                "current_amount": Decimal("200000.00"),
                "billing_frequency": "Monthly",
                "status": "active",
                "billing_prompt_next_date": date(2024, 9, 1),
                "notes": "Manufacturing process optimization",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            },
            {
                "contract_id": 3,
                "client_id": 3,  # Global Retail Co
                "contract_type": "Time & Material",
                "start_date": date(2024, 3, 1),
                "end_date": date(2025, 2, 28),
                "original_amount": Decimal("300000.00"),
                "current_amount": Decimal("300000.00"),
                "billing_frequency": "Monthly",
                "status": "active",
                "billing_prompt_next_date": date(2024, 9, 1),
                "notes": "Retail operations consulting",
                "created_by": "7615479c-2785-4695-853c-1a898d1b7dc5",
                "updated_by": "7615479c-2785-4695-853c-1a898d1b7dc5"
            }
        ]
        
        # Insert contracts
        for contract_data in contracts_data:
            # Check if contract already exists
            existing_contract = db.query(Contract).filter(Contract.contract_id == contract_data["contract_id"]).first()
            if not existing_contract:
                contract = Contract(**contract_data)
                db.add(contract)
                print(f"✅ Added contract: {contract_data['contract_id']} for client_id {contract_data['client_id']}")
            else:
                print(f"⚠️ Contract already exists: {contract_data['contract_id']}")
        
        # Commit all changes
        db.commit()
        print("✅ All test data inserted successfully!")
        
        # Verify the data
        clients = db.query(Client).all()
        contracts = db.query(Contract).all()
        
        print(f"\n📊 Database now contains:")
        print(f"   - {len(clients)} clients")
        print(f"   - {len(contracts)} contracts")
        
        print(f"\n📋 Clients:")
        for client in clients:
            print(f"   - {client.client_name} (ID: {client.client_id})")
        
        print(f"\n📋 Contracts:")
        for contract in contracts:
            client_name = contract.client.client_name if contract.client else "Unknown"
            print(f"   - Contract {contract.contract_id} for {client_name}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error inserting test data: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

if __name__ == "__main__":
    success = insert_test_data()
    if success:
        print("✅ Test data insertion completed successfully!")
    else:
        print("❌ Test data insertion failed!")
