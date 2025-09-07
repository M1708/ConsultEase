#!/usr/bin/env python3
"""
Test script for async database connection with pgbouncer compatibility
"""
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_connection():
    """Test the async database connection"""
    try:
        from src.database.core.database import test_async_connection
        
        print("🔧 Testing async database connection...")
        success = await test_async_connection()
        
        if success:
            print("✅ Async database connection test PASSED")
            return True
        else:
            print("❌ Async database connection test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error during connection test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting async database connection test...")
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
