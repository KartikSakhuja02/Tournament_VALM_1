"""
Database service module for PostgreSQL operations
"""

import asyncpg
import os
from typing import Optional, Dict, List
from datetime import datetime


class Database:
    """PostgreSQL database handler"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv("DATABASE_URL")
    
    async def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            print("✓ Database connected successfully")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            print("✓ Database connection closed")
    
    # Player operations
    
    async def get_player_by_discord_id(self, discord_id: int) -> Optional[Dict]:
        """Get player by Discord ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM players WHERE discord_id = $1",
                discord_id
            )
            return dict(row) if row else None
    
    async def get_player_by_ign(self, ign: str) -> Optional[Dict]:
        """Get player by IGN (case insensitive)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM players WHERE LOWER(ign) = LOWER($1)",
                ign
            )
            return dict(row) if row else None
    
    async def create_player(
        self,
        discord_id: int,
        ign: str,
        player_id: str,
        region: str,
        tournament_notifications: bool = True
    ) -> Dict:
        """Create a new player"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO players (discord_id, ign, player_id, region, tournament_notifications)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                discord_id, ign, player_id, region, tournament_notifications
            )
            return dict(row)
    
    async def update_player(
        self,
        discord_id: int,
        **kwargs
    ) -> Optional[Dict]:
        """Update player information"""
        if not kwargs:
            return None
        
        # Build SET clause dynamically
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())])
        values = [discord_id] + list(kwargs.values())
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE players
                SET {set_clause}
                WHERE discord_id = $1
                RETURNING *
                """,
                *values
            )
            return dict(row) if row else None
    
    async def delete_player(self, discord_id: int) -> bool:
        """Delete a player"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM players WHERE discord_id = $1",
                discord_id
            )
            return result == "DELETE 1"
    
    async def get_all_players(self, region: Optional[str] = None) -> List[Dict]:
        """Get all players, optionally filtered by region"""
        async with self.pool.acquire() as conn:
            if region:
                rows = await conn.fetch(
                    "SELECT * FROM players WHERE region = $1 ORDER BY registered_at DESC",
                    region
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM players ORDER BY registered_at DESC"
                )
            return [dict(row) for row in rows]
    
    async def get_players_with_notifications(self) -> List[Dict]:
        """Get all players who consented to tournament notifications"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM players WHERE tournament_notifications = TRUE ORDER BY registered_at DESC"
            )
            return [dict(row) for row in rows]
    
    # Player stats operations
    
    async def get_player_stats(self, discord_id: int) -> Optional[Dict]:
        """Get player statistics"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM player_stats WHERE discord_id = $1",
                discord_id
            )
            return dict(row) if row else None
    
    async def create_player_stats(self, discord_id: int) -> Dict:
        """Create initial stats for a player"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO player_stats (discord_id)
                VALUES ($1)
                RETURNING *
                """,
                discord_id
            )
            return dict(row)
    
    async def update_player_stats(
        self,
        discord_id: int,
        **kwargs
    ) -> Optional[Dict]:
        """Update player statistics"""
        if not kwargs:
            return None
        
        # Build SET clause dynamically
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())])
        values = [discord_id] + list(kwargs.values())
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE player_stats
                SET {set_clause}
                WHERE discord_id = $1
                RETURNING *
                """,
                *values
            )
            return dict(row) if row else None
    
    async def get_leaderboard(
        self,
        stat: str = "kills",
        region: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get leaderboard sorted by a stat"""
        valid_stats = ["kills", "deaths", "assists", "wins", "mvps", "matches_played"]
        if stat not in valid_stats:
            stat = "kills"
        
        async with self.pool.acquire() as conn:
            if region:
                rows = await conn.fetch(
                    f"""
                    SELECT p.*, ps.*
                    FROM players p
                    JOIN player_stats ps ON p.discord_id = ps.discord_id
                    WHERE p.region = $1
                    ORDER BY ps.{stat} DESC
                    LIMIT $2
                    """,
                    region, limit
                )
            else:
                rows = await conn.fetch(
                    f"""
                    SELECT p.*, ps.*
                    FROM players p
                    JOIN player_stats ps ON p.discord_id = ps.discord_id
                    ORDER BY ps.{stat} DESC
                    LIMIT $1
                    """,
                    limit
                )
            return [dict(row) for row in rows]
    
    # Utility operations
    
    async def get_player_count(self, region: Optional[str] = None) -> int:
        """Get total number of registered players"""
        async with self.pool.acquire() as conn:
            if region:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM players WHERE region = $1",
                    region
                )
            else:
                count = await conn.fetchval("SELECT COUNT(*) FROM players")
            return count


# Global database instance
db = Database()
