#!/bin/bash

# Registration Lock System - Quick Setup Script
# This script sets up the registration lock feature

echo "🔧 Setting up Registration Lock System..."
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql command not found"
    echo "Please install PostgreSQL client tools"
    exit 1
fi

# Database connection details
DB_HOST="localhost"
DB_USER="tournament_bot"
DB_NAME="valorant_tournament"

echo "📊 Running database migration..."
echo ""

# Run migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/migrations/010_registration_lock.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📋 Verifying setup..."
    
    # Verify tables were created
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d registration_status" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ registration_status table created"
    else
        echo "✗ registration_status table missing"
    fi
    
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d registration_notifications" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ registration_notifications table created"
    else
        echo "✗ registration_notifications table missing"
    fi
    
    # Check current lock status
    echo ""
    echo "📌 Current registration status:"
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT is_locked, lock_message FROM registration_status WHERE id = 1;"
    
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📖 Next steps:"
    echo "  1. Restart your Discord bot"
    echo "  2. Test with /admin-lock-registrations"
    echo "  3. Try clicking registration buttons (should show lock message)"
    echo "  4. Subscribe to notifications"
    echo "  5. Test with /admin-unlock-registrations"
    echo ""
    echo "For detailed documentation, see REGISTRATION_LOCK_GUIDE.md"
    
else
    echo ""
    echo "❌ Migration failed!"
    echo "Please check the error messages above"
    exit 1
fi
