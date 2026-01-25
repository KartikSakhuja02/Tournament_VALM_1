-- Add unique constraint to prevent duplicate team members
-- A player can only be on a team once with a specific role

-- First, remove any duplicates that might exist
DELETE FROM team_members a
USING team_members b
WHERE a.id > b.id
  AND a.team_id = b.team_id
  AND a.discord_id = b.discord_id;

-- Add unique constraint
ALTER TABLE team_members
ADD CONSTRAINT unique_team_member UNIQUE (team_id, discord_id);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_team_members_lookup ON team_members(team_id, discord_id);
