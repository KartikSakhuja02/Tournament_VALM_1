"""
Apply database schema updates
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def apply_schema():
    """Apply schema updates to database"""
    database_url = os.getenv("DATABASE_URL")
    
    # Read schema file
    with open("database/schema.sql", "r") as f:
        schema = f.read()
    
    # Connect and execute
    conn = await asyncpg.connect(database_url)
    try:
        print("✓ Connected to database")
        
        # Execute schema
        await conn.execute(schema)
        print("✓ Schema applied successfully")
        
        # Verify tables
        tables = await conn.fetch(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        
        print("\n📋 Current tables:")
        for table in tables:
            print(f"  • {table['table_name']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await conn.close()
        print("\n✓ Connection closed")

if __name__ == "__main__":
    asyncio.run(apply_schema())
