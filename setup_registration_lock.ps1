# Registration Lock System - Quick Setup Script (PowerShell)
# This script sets up the registration lock feature

Write-Host "🔧 Setting up Registration Lock System..." -ForegroundColor Cyan
Write-Host ""

# Database connection details
$DB_HOST = "localhost"
$DB_USER = "tournament_bot"
$DB_NAME = "valorant_tournament"
$MIGRATION_FILE = "database\migrations\010_registration_lock.sql"

# Check if psql is available
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "❌ Error: psql command not found" -ForegroundColor Red
    Write-Host "Please install PostgreSQL client tools" -ForegroundColor Yellow
    exit 1
}

# Check if migration file exists
if (-not (Test-Path $MIGRATION_FILE)) {
    Write-Host "❌ Error: Migration file not found: $MIGRATION_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "📊 Running database migration..." -ForegroundColor Cyan
Write-Host ""

# Run migration
$env:PGPASSWORD = Read-Host "Enter database password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($env:PGPASSWORD)
$env:PGPASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

& psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $MIGRATION_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Migration completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Verifying setup..." -ForegroundColor Cyan
    
    # Verify tables were created
    & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d registration_status" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ registration_status table created" -ForegroundColor Green
    } else {
        Write-Host "✗ registration_status table missing" -ForegroundColor Red
    }
    
    & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d registration_notifications" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ registration_notifications table created" -ForegroundColor Green
    } else {
        Write-Host "✗ registration_notifications table missing" -ForegroundColor Red
    }
    
    # Check current lock status
    Write-Host ""
    Write-Host "📌 Current registration status:" -ForegroundColor Cyan
    & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT is_locked, lock_message FROM registration_status WHERE id = 1;"
    
    Write-Host ""
    Write-Host "✅ Setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📖 Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Restart your Discord bot"
    Write-Host "  2. Test with /admin-lock-registrations"
    Write-Host "  3. Try clicking registration buttons (should show lock message)"
    Write-Host "  4. Subscribe to notifications"
    Write-Host "  5. Test with /admin-unlock-registrations"
    Write-Host ""
    Write-Host "For detailed documentation, see REGISTRATION_LOCK_GUIDE.md" -ForegroundColor Yellow
    
} else {
    Write-Host ""
    Write-Host "❌ Migration failed!" -ForegroundColor Red
    Write-Host "Please check the error messages above" -ForegroundColor Yellow
    exit 1
}

# Clear password from environment
$env:PGPASSWORD = $null
