import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def check_schema():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    print("=" * 60)
    print("TEAMS TABLE STRUCTURE:")
    print("=" * 60)
    teams = await conn.fetch("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'teams'
        ORDER BY ordinal_position;
    """)
    for col in teams:
        print(f"{col['column_name']:20} {col['data_type']:15} nullable={col['is_nullable']}")
    
    print("\n" + "=" * 60)
    print("TEAM_MEMBERS TABLE STRUCTURE:")
    print("=" * 60)
    team_members = await conn.fetch("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'team_members'
        ORDER BY ordinal_position;
    """)
    for col in team_members:
        print(f"{col['column_name']:20} {col['data_type']:15} nullable={col['is_nullable']}")
    
    await conn.close()

asyncio.run(check_schema())
