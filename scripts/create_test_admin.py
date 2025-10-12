#!/usr/bin/env python3
"""
Create test admin user for mini-webui (for development only)
"""

import sys
import os
import uuid
import time

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mini_webui.internal.db import get_db
from mini_webui.models.users import User
from mini_webui.utils.security import get_password_hash

def create_test_admin():
    """Create a test admin user"""
    try:
        with get_db() as db:
            # Check if admin already exists
            existing_admin = db.query(User).filter(User.role == "admin").first()
            if existing_admin:
                print(f"Admin user already exists: {existing_admin.email}")
                return True
            
            # Create new admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                name="Admin User",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                role="admin",
                profile_image_url="/user.png",
                is_active=True,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                last_active_at=int(time.time())
            )
            
            db.add(admin_user)
            db.commit()
            
            print(f"✅ Test admin user created successfully!")
            print(f"   Email: {admin_user.email}")
            print(f"   Password: admin123")
            print(f"   Role: {admin_user.role}")
            
            return True
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

if __name__ == "__main__":
    success = create_test_admin()
    sys.exit(0 if success else 1)
