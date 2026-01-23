-- Add points column to player_stats table
ALTER TABLE player_stats
ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;
