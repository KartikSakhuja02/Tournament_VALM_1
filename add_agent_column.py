#!/usr/bin/env python3
"""
Migration script to add 'agent' column to players table
Run this once to update your database schema
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def add_agent_column():
    """Add agent column to players table"""
    
    # Database connection
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if column already exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'players' 
                AND column_name = 'agent'
            )
        """)
        
        if exists:
            print("✅ Column 'agent' already exists in players table")
        else:
            # Add the agent column
            await conn.execute("""
                ALTER TABLE players
                ADD COLUMN agent VARCHAR(50)
            """)
            print("✅ Successfully added 'agent' column to players table")
        
        # Show current table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'players'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 Current players table structure:")
        print("-" * 60)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"  {col['column_name']:<30} {col['data_type']:<20} {nullable}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("\n✅ Database connection closed")

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add Agent Column")
    print("=" * 60)
    asyncio.run(add_agent_column())
    print("\n✅ Migration complete!")
