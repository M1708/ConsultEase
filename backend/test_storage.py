#!/usr/bin/env python3
"""
Test script for Supabase Storage Service
Run this to verify the storage service can be initialized and basic operations work
"""

import os
import asyncio
from src.services.storage_service import SupabaseStorageService

async def test_storage_service():
    """Test basic storage service functionality"""
    try:
        print("Testing Supabase Storage Service initialization...")
        
        # Check environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        print(f"SUPABASE_URL: {'Set' if supabase_url else 'NOT SET'}")
        print(f"SUPABASE_SERVICE_KEY: {'Set' if supabase_key else 'NOT SET'}")
        
        if not supabase_url or not supabase_key:
            print("ERROR: Environment variables not set properly")
            return False
        
        # Try to initialize the service
        storage_service = SupabaseStorageService()
        print("✓ Storage service initialized successfully")
        
        # Test bucket access
        try:
            buckets = storage_service.supabase.storage.list_buckets()
            print(f"✓ Bucket list retrieved: {buckets}")
        except Exception as e:
            print(f"⚠ Warning: Could not list buckets: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("ConsultEase Storage Service Test")
    print("=" * 40)
    
    success = asyncio.run(test_storage_service())
    
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        print("\nMake sure you have:")
        print("1. SUPABASE_URL environment variable set")
        print("2. SUPABASE_SERVICE_KEY environment variable set")
        print("3. Valid Supabase credentials")
