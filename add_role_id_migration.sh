#!/bin/bash
# Script to add role_id column to teams table

echo "Adding role_id column to teams table..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Missing required environment variables"
    exit 1
fi

echo "Connecting to database: $DB_NAME at $DB_HOST:$DB_PORT"

# Run the migration
export PGPASSWORD=$DB_PASSWORD
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "database/migrations/007_add_role_id_to_teams.sql"

if [ $? -eq 0 ]; then
    echo "✓ Successfully added role_id column to teams table"
else
    echo "✗ Migration failed"
    exit 1
fi

echo ""
echo "Migration complete!"
