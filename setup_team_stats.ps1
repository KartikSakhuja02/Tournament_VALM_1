# PowerShell script to create team_stats table on Raspberry Pi
# Run this: .\setup_team_stats.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up team_stats table" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$DB_USER = "tournament_bot"
$DB_NAME = "tournament_db"
$DB_HOST = "localhost"

# Prompt for password
$DB_PASSWORD = Read-Host "Enter database password for $DB_USER" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Set environment variable for psql
$env:PGPASSWORD = $PlainPassword

# SQL commands
$SqlCommands = @"
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
"@

# Execute SQL
try {
    $SqlCommands | psql -U $DB_USER -h $DB_HOST -d $DB_NAME
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Setup complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    # Clear password from environment
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
