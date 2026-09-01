#!/usr/bin/env python3
"""
Script to reset admin password
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import text
from app.core.database import SessionLocal, engine

def reset_admin_password():
    """Reset admin password using direct bcrypt"""
    # Generate hash using bcrypt directly
    password = 'admin123'
    new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    print(f"Generated hash: {new_hash[:30]}...")
    
    # Update using raw SQL to avoid model loading issues
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET hashed_password = :hash WHERE username = 'admin'"),
            {"hash": new_hash}
        )
        conn.commit()
        print(f"Rows updated: {result.rowcount}")
    
    # Verify the update
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT username, LEFT(hashed_password, 30) as hash_start, LENGTH(hashed_password) as hash_len FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        if row:
            print(f"Verification - Username: {row[0]}, Hash start: {row[1]}, Hash length: {row[2]}")
            
            # Test password verification
            stored_hash = conn.execute(
                text("SELECT hashed_password FROM users WHERE username = 'admin'")
            ).fetchone()[0]
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                print("✓ Password verification successful!")
                print("✓ Admin password is now: admin123")
            else:
                print("✗ Password verification failed!")
        else:
            print("✗ Admin user not found!")

if __name__ == "__main__":
    reset_admin_password()
