"""
Migration script to add team_tag and logo_url columns to teams table
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def add_columns():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        # Add team_tag column
        print("Adding team_tag column...")
        await conn.execute("""
            ALTER TABLE teams 
            ADD COLUMN IF NOT EXISTS team_tag VARCHAR(5) UNIQUE;
        """)
        print("✓ team_tag column added")
        
        # Add logo_url column
        print("Adding logo_url column...")
        await conn.execute("""
            ALTER TABLE teams 
            ADD COLUMN IF NOT EXISTS logo_url TEXT;
        """)
        print("✓ logo_url column added")
        
        # Show updated schema
        print("\n" + "=" * 60)
        print("UPDATED TEAMS TABLE STRUCTURE:")
        print("=" * 60)
        columns = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'teams'
            ORDER BY ordinal_position;
        """)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
            print(f"{col['column_name']:25} {col['data_type']}{max_len:15} {nullable}")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_columns())
