#!/usr/bin/env python3
"""
Verify database setup for mini-webui
"""

import sys
import os
import sqlite3

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mini_webui.internal.db import get_db
from mini_webui.models.users import User
from mini_webui.models.chats import Chat
from mini_webui.models.messages import Message
from mini_webui.models.settings import Setting

def verify_database():
    """Verify database setup and models"""
    print("🔍 Verifying mini-webui Database Setup")
    print("=" * 50)
    
    # Check database file exists
    db_path = "data/webui.db"
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return False
    
    print(f"✅ Database file exists: {db_path}")
    
    # Check tables exist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    expected_tables = ['user', 'chat', 'message', 'setting', 'alembic_version']
    missing_tables = [table for table in expected_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False
    
    print(f"✅ All required tables exist: {expected_tables}")
    
    # Test model operations
    try:
        with get_db() as db:
            # Test User model
            user_count = db.query(User).count()
            print(f"✅ User model working - {user_count} users in database")
            
            # Test Chat model
            chat_count = db.query(Chat).count()
            print(f"✅ Chat model working - {chat_count} chats in database")
            
            # Test Message model
            message_count = db.query(Message).count()
            print(f"✅ Message model working - {message_count} messages in database")
            
            # Test Setting model
            setting_count = db.query(Setting).count()
            print(f"✅ Setting model working - {setting_count} settings in database")
            
            # Check for admin user
            admin_user = db.query(User).filter(User.role == "admin").first()
            if admin_user:
                print(f"✅ Admin user exists: {admin_user.email}")
            else:
                print("⚠️  No admin user found - run scripts/create_test_admin.py")
            
    except Exception as e:
        print(f"❌ Database model error: {e}")
        return False
    
    print("\n🎉 Database setup verification completed successfully!")
    print("\nNext steps:")
    print("- Task 1.3: Implement authentication system")
    print("- Add password hashing and JWT tokens")
    print("- Create authentication API endpoints")
    
    return True

if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)