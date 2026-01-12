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
    
    # Team operations
    
    async def create_team(
        self,
        team_name: str,
        captain_discord_id: int,
        region: str
    ) -> Dict:
        """Create a new team"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO teams (team_name, captain_discord_id, region)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                team_name, captain_discord_id, region
            )
            return dict(row)
    
    async def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """Get team by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE id = $1",
                team_id
            )
            return dict(row) if row else None
    
    async def get_team_by_name(self, team_name: str) -> Optional[Dict]:
        """Get team by name (case insensitive)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE LOWER(team_name) = LOWER($1)",
                team_name
            )
            return dict(row) if row else None
    
    async def get_all_teams(self, region: Optional[str] = None) -> List[Dict]:
        """Get all teams, optionally filtered by region"""
        async with self.pool.acquire() as conn:
            if region:
                rows = await conn.fetch(
                    "SELECT * FROM teams WHERE region = $1 ORDER BY created_at DESC",
                    region
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM teams ORDER BY created_at DESC"
                )
            return [dict(row) for row in rows]
    
    async def get_teams_with_manager_slots(self) -> List[Dict]:
        """Get teams that have available manager slots (less than 2 managers)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*,
                    COALESCE(COUNT(tm.id) FILTER (WHERE tm.role = 'manager'), 0) as manager_count
                FROM teams t
                LEFT JOIN team_members tm ON t.id = tm.team_id AND tm.role = 'manager'
                GROUP BY t.id
                HAVING COALESCE(COUNT(tm.id) FILTER (WHERE tm.role = 'manager'), 0) < 2
                ORDER BY t.created_at DESC
                """
            )
            return [dict(row) for row in rows]
    
    # Team member operations
    
    async def add_team_member(
        self,
        team_id: int,
        discord_id: int,
        role: str
    ) -> Dict:
        """Add a member to a team"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO team_members (team_id, discord_id, role)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                team_id, discord_id, role
            )
            return dict(row)
    
    async def remove_team_member(
        self,
        team_id: int,
        discord_id: int,
        role: str
    ) -> bool:
        """Remove a member from a team"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM team_members WHERE team_id = $1 AND discord_id = $2 AND role = $3",
                team_id, discord_id, role
            )
            return result == "DELETE 1"
    
    async def get_team_members(
        self,
        team_id: int,
        role: Optional[str] = None
    ) -> List[Dict]:
        """Get all members of a team, optionally filtered by role"""
        async with self.pool.acquire() as conn:
            if role:
                rows = await conn.fetch(
                    "SELECT * FROM team_members WHERE team_id = $1 AND role = $2 ORDER BY joined_at",
                    team_id, role
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM team_members WHERE team_id = $1 ORDER BY joined_at",
                    team_id
                )
            return [dict(row) for row in rows]
    
    async def get_member_teams(self, discord_id: int) -> List[Dict]:
        """Get all teams a user is part of"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, tm.role
                FROM teams t
                JOIN team_members tm ON t.id = tm.team_id
                WHERE tm.discord_id = $1
                ORDER BY tm.joined_at DESC
                """,
                discord_id
            )
            return [dict(row) for row in rows]
    
    async def is_team_member(
        self,
        team_id: int,
        discord_id: int,
        role: Optional[str] = None
    ) -> bool:
        """Check if a user is a member of a team"""
        async with self.pool.acquire() as conn:
            if role:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM team_members WHERE team_id = $1 AND discord_id = $2 AND role = $3)",
                    team_id, discord_id, role
                )
            else:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM team_members WHERE team_id = $1 AND discord_id = $2)",
                    team_id, discord_id
                )
            return result
    
    async def get_team_role_count(self, team_id: int, role: str) -> int:
        """Get count of members with specific role in a team"""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM team_members WHERE team_id = $1 AND role = $2",
                team_id, role
            )
            return count
    
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
