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
        agent: str = None,
        tournament_notifications: bool = True
    ) -> Dict:
        """Create a new player"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO players (discord_id, ign, player_id, region, agent, tournament_notifications)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                discord_id, ign, player_id, region, agent, tournament_notifications
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
    
    # Team operations
    
    async def get_team_by_name(self, team_name: str) -> Optional[Dict]:
        """Get team by name (case insensitive)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE LOWER(team_name) = LOWER($1)",
                team_name
            )
            return dict(row) if row else None
    
    async def get_team_by_tag(self, team_tag: str) -> Optional[Dict]:
        """Get team by tag (case insensitive)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE LOWER(team_tag) = LOWER($1)",
                team_tag
            )
            return dict(row) if row else None
    
    async def get_team_by_captain(self, captain_discord_id: int) -> Optional[Dict]:
        """Get team by captain Discord ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE captain_discord_id = $1",
                captain_discord_id
            )
            return dict(row) if row else None
    
    async def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """Get team by team ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM teams WHERE id = $1",
                team_id
            )
            return dict(row) if row else None
    
    async def get_all_teams(self) -> List[Dict]:
        """Get all teams"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM teams ORDER BY created_at DESC"
            )
            return [dict(row) for row in rows]
    
    async def create_team(
        self,
        team_name: str,
        team_tag: str,
        region: str,
        captain_discord_id: int,
        logo_url: Optional[str] = None
    ) -> Dict:
        """Create a new team"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO teams (team_name, team_tag, region, captain_discord_id, logo_url)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                team_name, team_tag, region, captain_discord_id, logo_url
            )
            return dict(row)
    
    async def update_team(self, team_id: int, **kwargs) -> Optional[Dict]:
        """Update team information"""
        if not kwargs:
            return None
        
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())])
        values = [team_id] + list(kwargs.values())
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE teams
                SET {set_clause}
                WHERE id = $1
                RETURNING *
                """,
                *values
            )
            return dict(row) if row else None
    
    async def get_team_members(self, team_id: int) -> List[Dict]:
        """Get all members of a team"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tm.*, p.ign, p.player_id
                FROM team_members tm
                LEFT JOIN players p ON tm.discord_id = p.discord_id
                WHERE tm.team_id = $1
                ORDER BY 
                    CASE tm.role
                        WHEN 'captain' THEN 1
                        WHEN 'player' THEN 2
                        WHEN 'manager' THEN 3
                        WHEN 'coach' THEN 4
                    END
                """,
                team_id
            )
            return [dict(row) for row in rows]
    
    async def add_team_member(
        self,
        team_id: int,
        discord_id: int,
        role: str = 'player'
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
    
    async def remove_team_member(self, team_id: int, discord_id: int) -> bool:
        """Remove a member from a team"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM team_members WHERE team_id = $1 AND discord_id = $2",
                team_id, discord_id
            )
            return result == "DELETE 1"
    
    async def get_user_teams_by_role(self, discord_id: int, role: str) -> List[Dict]:
        """Get all teams where user has a specific role"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, tm.role
                FROM teams t
                JOIN team_members tm ON t.id = tm.team_id
                WHERE tm.discord_id = $1 AND tm.role = $2
                """,
                discord_id, role
            )
            return [dict(row) for row in rows]
    
    async def delete_team(self, team_id: int) -> bool:
        """Delete a team (this will cascade delete team_members due to foreign key constraint)"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM teams WHERE id = $1",
                team_id
            )
            return result == "DELETE 1"
    
    # Ban operations
    
    async def ban_player(self, discord_id: int, banned_by: int, reason: str = None) -> bool:
        """Ban a player from registering"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO banned_players (discord_id, banned_by, reason, banned_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (discord_id) DO UPDATE
                    SET banned_by = $2, reason = $3, banned_at = NOW()
                    """,
                    discord_id, banned_by, reason
                )
                return True
            except Exception as e:
                print(f"❌ Error banning player: {e}")
                return False
    
    async def unban_player(self, discord_id: int) -> bool:
        """Unban a player"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM banned_players WHERE discord_id = $1",
                discord_id
            )
            return result == "DELETE 1"
    
    async def is_player_banned(self, discord_id: int) -> Optional[Dict]:
        """Check if a player is banned"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM banned_players WHERE discord_id = $1",
                discord_id
            )
            return dict(row) if row else None
    
    async def get_all_banned_players(self) -> List[Dict]:
        """Get all banned players"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM banned_players ORDER BY banned_at DESC")
            return [dict(row) for row in rows]


# Global database instance
db = Database()
