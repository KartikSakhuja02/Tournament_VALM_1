#!/usr/bin/env pwsh
# Script to add role_id column to teams table

Write-Host "Adding role_id column to teams table..." -ForegroundColor Cyan

# Load environment variables
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    exit 1
}

$DB_NAME = $env:DB_NAME
$DB_USER = $env:DB_USER
$DB_PASSWORD = $env:DB_PASSWORD
$DB_HOST = $env:DB_HOST
$DB_PORT = $env:DB_PORT

if (-not $DB_NAME -or -not $DB_USER -or -not $DB_PASSWORD) {
    Write-Host "Error: Missing required environment variables" -ForegroundColor Red
    exit 1
}

Write-Host "Connecting to database: $DB_NAME at $DB_HOST:$DB_PORT" -ForegroundColor Yellow

# Run the migration
$env:PGPASSWORD = $DB_PASSWORD
$result = psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "database/migrations/007_add_role_id_to_teams.sql" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Successfully added role_id column to teams table" -ForegroundColor Green
} else {
    Write-Host "✗ Migration failed: $result" -ForegroundColor Red
    exit 1
}

Write-Host "`nMigration complete!" -ForegroundColor Green
