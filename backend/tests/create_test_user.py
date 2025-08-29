#!/usr/bin/env python3
"""
Script to create a test user in the profiles table
"""
import uuid
from sqlalchemy.orm import Session
from src.database.core.database import get_db
from src.database.core.models import User, UserRole, UserStatus

def create_test_user():
    """Create test user in profiles table"""
    try:
        # Get database session
        db = next(get_db())
        
        print("🔧 Creating test user...")
        
        # User ID to create
        user_id = "7615479c-2785-4695-853c-1a898d1b7dc5"
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        if existing_user:
            print(f"⚠️ User already exists: {existing_user.email}")
            db.close()
            return True
        
        # Create test user
        test_user = User(
            user_id=uuid.UUID(user_id),
            email="test.user@consultease.com",
            first_name="Test",
            last_name="User",
            role=UserRole.admin,
            status=UserStatus.active,
            phone="+1-555-0123"
        )
        
        db.add(test_user)
        db.commit()
        
        print(f"✅ Created test user: {test_user.email} (ID: {test_user.user_id})")
        
        # Verify the user was created
        verification_user = db.query(User).filter(User.user_id == user_id).first()
        if verification_user:
            print(f"✅ User verification successful: {verification_user.full_name}")
        else:
            print("❌ User verification failed")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

if __name__ == "__main__":
    success = create_test_user()
    if success:
        print("✅ Test user creation completed successfully!")
    else:
        print("❌ Test user creation failed!")
