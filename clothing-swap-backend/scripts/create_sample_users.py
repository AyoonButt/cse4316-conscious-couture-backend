#!/usr/bin/env python3
"""
Create sample users for the clothing swap application.
"""

import sys
import hashlib
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session
from app.models.user import User


def hash_password(password: str) -> str:
    """Simple password hashing for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_sample_users(session):
    """Create sample users for testing."""
    
    sample_users = [
        {
            "username": "john_doe",
            "email": "john.doe@example.com",
            "password": "password123",
            "display_name": "John Doe",
            "location": "New York, NY"
        },
        {
            "username": "jane_smith", 
            "email": "jane.smith@example.com",
            "password": "password123",
            "display_name": "Jane Smith",
            "location": "Los Angeles, CA"
        },
        {
            "username": "mike_johnson",
            "email": "mike.johnson@example.com", 
            "password": "password123",
            "display_name": "Mike Johnson",
            "location": "Chicago, IL"
        },
        {
            "username": "sarah_wilson",
            "email": "sarah.wilson@example.com",
            "password": "password123", 
            "display_name": "Sarah Wilson",
            "location": "Austin, TX"
        },
        {
            "username": "alex_brown",
            "email": "alex.brown@example.com",
            "password": "password123",
            "display_name": "Alex Brown", 
            "location": "Seattle, WA"
        }
    ]
    
    created_users = []
    
    for user_data in sample_users:
        # Check if user already exists
        existing_user = session.query(User).filter(
            (User.username == user_data["username"]) | 
            (User.email == user_data["email"])
        ).first()
        
        if existing_user:
            print(f"✅ User {user_data['username']} already exists, skipping...")
            created_users.append(existing_user)
            continue
        
        # Create new user
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            display_name=user_data["display_name"],
            location=user_data["location"],
            profile_public=True,
            share_stats=True
        )
        
        session.add(user)
        created_users.append(user)
        print(f"✅ Created user: {user_data['username']} ({user_data['display_name']})")
    
    session.commit()
    
    # Refresh to get IDs
    for user in created_users:
        session.refresh(user)
    
    return created_users


def main():
    """Main function."""
    
    print("🚀 Creating sample users...")
    
    try:
        session = get_database_session()
        
        users = create_sample_users(session)
        
        print(f"\n📊 Summary:")
        print(f"Created/Found {len(users)} users:")
        for user in users:
            print(f"  • {user.username} (ID: {user.user_id}) - {user.display_name}")
        
        print(f"\n✅ Sample users setup complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'session' in locals():
            session.close()
    
    return True


if __name__ == "__main__":
    main()