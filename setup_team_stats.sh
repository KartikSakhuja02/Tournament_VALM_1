#!/bin/bash
# Script to create team_stats table on Raspberry Pi
# Run this on your Raspberry Pi: bash setup_team_stats.sh

echo "========================================"
echo "Setting up team_stats table"
echo "========================================"

# Make sure to set your database credentials
DB_USER="tournament_bot"
DB_NAME="tournament_db"
DB_HOST="localhost"

# Prompt for password
echo -n "Enter database password for $DB_USER: "
read -s DB_PASSWORD
echo ""

# Run the migration
export PGPASSWORD="$DB_PASSWORD"

psql -U "$DB_USER" -h "$DB_HOST" -d "$DB_NAME" << 'EOF'

-- Add team_stats table
CREATE TABLE IF NOT EXISTS team_stats (
    id SERIAL PRIMARY KEY,
    team_id INTEGER UNIQUE NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    matches_played INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_team_stats_team_id ON team_stats(team_id);

-- Create trigger for updated_at (function should already exist from schema.sql)
CREATE TRIGGER update_team_stats_updated_at BEFORE UPDATE ON team_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Show the new table structure
\d team_stats

-- Show confirmation
SELECT 'team_stats table created successfully!' as status;

EOF

unset PGPASSWORD

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
