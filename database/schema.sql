-- VALORANT Tournament Database Schema

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    ign VARCHAR(50) UNIQUE NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    region VARCHAR(10) NOT NULL,
    tournament_notifications BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Player statistics table
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    matches_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    mvps INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(50) UNIQUE NOT NULL,
    captain_discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    region VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team members table (players, managers, coach)
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    discord_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'player', 'manager', 'coach'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, discord_id, role)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id);
CREATE INDEX IF NOT EXISTS idx_players_ign ON players(ign);
CREATE INDEX IF NOT EXISTS idx_players_region ON players(region);
CREATE INDEX IF NOT EXISTS idx_player_stats_discord_id ON player_stats(discord_id);
CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_discord_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_discord ON team_members(discord_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_player_stats_updated_at BEFORE UPDATE ON player_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tournament_bot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tournament_bot;
