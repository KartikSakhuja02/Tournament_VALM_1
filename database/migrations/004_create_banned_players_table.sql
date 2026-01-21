-- Create banned_players table
CREATE TABLE IF NOT EXISTS banned_players (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    banned_by BIGINT NOT NULL,
    reason TEXT,
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on discord_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_banned_players_discord_id ON banned_players(discord_id);
