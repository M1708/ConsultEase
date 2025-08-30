#!/usr/bin/env python3

"""
Test script to update billing prompt date for Acme contract
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aiagents.tools.contract_tools import update_contract_tool, UpdateContractParams, get_contracts_by_client_tool
from src.database.core.database import get_db

def test_acme_billing_update():
    """Test updating billing prompt date for Acme contract"""
    
    print("🔍 Testing Acme contract billing prompt date update...")
    
    # Test context (simulating authenticated user)
    test_context = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID format
        "session_id": "test-session-123"
    }
    
    try:
        # First, let's check what Acme contracts exist
        print("\n1. Checking existing Acme contracts...")
        
        db = next(get_db())
        result = get_contracts_by_client_tool("Acme", db)
        
        if result.success:
            print(f"✅ {result.message}")
            if result.data and result.data.get("contracts"):
                contracts = result.data["contracts"]
                print(f"Found {len(contracts)} contracts for Acme:")
                for contract in contracts:
                    print(f"  - Contract ID: {contract['contract_id']}")
                    print(f"    Type: {contract['contract_type']}")
                    print(f"    Status: {contract['status']}")
                    print(f"    Current billing prompt date: {contract['billing_prompt_next_date']}")
                    print()
            else:
                print("No contracts found for Acme")
                return
        else:
            print(f"❌ {result.message}")
            return
        
        # Now test the update
        print("2. Testing billing prompt date update...")
        
        update_params = UpdateContractParams(
            client_name="Acme",
            billing_prompt_next_date="2025-09-01"  # September 1st, 2025
        )
        
        result = update_contract_tool(update_params, test_context, db)
        
        if result.success:
            print(f"✅ {result.message}")
            if result.data:
                print(f"Updated contract ID: {result.data['contract_id']}")
                print(f"Updated fields: {result.data['updated_fields']}")
        else:
            print(f"❌ {result.message}")
            return
        
        # Verify the update
        print("\n3. Verifying the update...")
        
        # Create a fresh database session to verify
        db_verify = next(get_db())
        verify_result = get_contracts_by_client_tool("Acme", db_verify)
        
        if verify_result.success and verify_result.data:
            contracts = verify_result.data["contracts"]
            print("Updated Acme contracts:")
            for contract in contracts:
                print(f"  - Contract ID: {contract['contract_id']}")
                print(f"    Type: {contract['contract_type']}")
                print(f"    Status: {contract['status']}")
                print(f"    Updated billing prompt date: {contract['billing_prompt_next_date']}")
                
                if contract['billing_prompt_next_date'] == "2025-09-01":
                    print("    ✅ Billing prompt date updated successfully!")
                else:
                    print("    ❌ Billing prompt date was not updated correctly")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
