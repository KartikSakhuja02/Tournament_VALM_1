-- Add role_id column to teams table to store Discord role ID
ALTER TABLE teams ADD COLUMN IF NOT EXISTS role_id BIGINT;

-- Add index for role_id lookups
CREATE INDEX IF NOT EXISTS idx_teams_role_id ON teams(role_id);
