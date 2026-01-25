-- Allow NULL captain_discord_id for manager-created teams
-- When a manager creates a team, they are not the captain, so captain_discord_id should be NULL
-- The captain will be assigned later when a player joins and is promoted to captain

ALTER TABLE teams ALTER COLUMN captain_discord_id DROP NOT NULL;

-- Create index for faster lookups of teams without captains
CREATE INDEX IF NOT EXISTS idx_teams_no_captain ON teams(id) WHERE captain_discord_id IS NULL;
