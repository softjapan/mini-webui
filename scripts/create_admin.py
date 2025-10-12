#!/usr/bin/env python3
"""
Create initial admin user for mini-webui
"""

import sys
import os
import uuid
import time
from getpass import getpass

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mini_webui.internal.db import get_db
from mini_webui.models.users import User
from mini_webui.utils.security import get_password_hash

def create_admin_user():
    """Create an admin user interactively"""
    print("Creating initial admin user for mini-webui")
    print("=" * 50)
    
    # Get user input
    name = input("Admin name: ").strip()
    if not name:
        print("Error: Name is required")
        return False
    
    email = input("Admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return False
    
    password = getpass("Admin password: ")
    if not password:
        print("Error: Password is required")
        return False
    
    confirm_password = getpass("Confirm password: ")
    if password != confirm_password:
        print("Error: Passwords do not match")
        return False
    
    # Create user in database
    try:
        with get_db() as db:
            # Check if admin already exists
            existing_admin = db.query(User).filter(User.role == "admin").first()
            if existing_admin:
                print(f"Admin user already exists: {existing_admin.email}")
                return False
            
            # Create new admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                name=name,
                email=email,
                password_hash=get_password_hash(password),
                role="admin",
                profile_image_url="/user.png",
                is_active=True,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                last_active_at=int(time.time())
            )
            
            db.add(admin_user)
            db.commit()
            
            print(f"\n✅ Admin user created successfully!")
            print(f"   ID: {admin_user.id}")
            print(f"   Name: {admin_user.name}")
            print(f"   Email: {admin_user.email}")
            print(f"   Role: {admin_user.role}")
            print(f"\nNote: Password hashing: bcrypt")
            
            return True
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
