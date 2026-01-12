"""
Create teams tables as postgres superuser
"""
import asyncio
import asyncpg

async def create_tables():
    """Create teams tables"""
    # Connect as postgres superuser
    conn = await asyncpg.connect(
        user='postgres',
        password='valorantmobileindia',  # Replace with actual postgres password if different
        database='valorant_tournament',
        host='localhost'
    )
    
    try:
        print("✓ Connected to database")
        
        # Create teams table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                team_name VARCHAR(50) UNIQUE NOT NULL,
                captain_discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
                region VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Created teams table")
        
        # Create team_members table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                discord_id BIGINT NOT NULL,
                role VARCHAR(20) NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, discord_id, role)
            )
        """)
        print("✓ Created team_members table")
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_discord_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_team_members_discord ON team_members(discord_id)")
        print("✓ Created indexes")
        
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
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("\n✓ Connection closed")

if __name__ == "__main__":
    asyncio.run(create_tables())
