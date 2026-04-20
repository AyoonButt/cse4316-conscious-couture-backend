#!/usr/bin/env python3
"""
Create sample users for the clothing swap application.
"""

import sys
import hashlib
from datetime import date
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session, init_db
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
            "location": "New York, NY",
            "birth_date": "1995-06-14",
            "address_line1": "111 Main St",
            "address_line2": "Apt 4B",
            "phone_number": "+12125550101",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "US",
        },
        {
            "username": "jane_smith", 
            "email": "jane.smith@example.com",
            "password": "password123",
            "display_name": "Jane Smith",
            "location": "Los Angeles, CA",
            "birth_date": "1993-02-19",
            "address_line1": "245 Sunset Blvd",
            "address_line2": None,
            "phone_number": "+13235550102",
            "city": "Los Angeles",
            "state": "CA",
            "postal_code": "90028",
            "country": "US",
        },
        {
            "username": "mike_johnson",
            "email": "mike.johnson@example.com", 
            "password": "password123",
            "display_name": "Mike Johnson",
            "location": "Chicago, IL",
            "birth_date": "1990-11-03",
            "address_line1": "780 Lakeshore Dr",
            "address_line2": "Unit 12",
            "phone_number": "+13125550103",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country": "US",
        },
        {
            "username": "sarah_wilson",
            "email": "sarah.wilson@example.com",
            "password": "password123", 
            "display_name": "Sarah Wilson",
            "location": "Austin, TX",
            "birth_date": "1998-08-22",
            "address_line1": "1002 Baylor St",
            "address_line2": None,
            "phone_number": "+15125550104",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78703",
            "country": "US",
        },
        {
            "username": "alex_brown",
            "email": "alex.brown@example.com",
            "password": "password123",
            "display_name": "Alex Brown", 
            "location": "Seattle, WA",
            "birth_date": "1992-04-10",
            "address_line1": "901 Pine St",
            "address_line2": "Suite 7",
            "phone_number": "+12065550105",
            "city": "Seattle",
            "state": "WA",
            "postal_code": "98101",
            "country": "US",
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
            birth_date=date.fromisoformat(user_data["birth_date"]),
            address_line1=user_data["address_line1"],
            address_line2=user_data["address_line2"],
            phone_number=user_data["phone_number"],
            city=user_data["city"],
            state=user_data["state"],
            postal_code=user_data["postal_code"],
            country=user_data["country"],
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
        init_db()
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