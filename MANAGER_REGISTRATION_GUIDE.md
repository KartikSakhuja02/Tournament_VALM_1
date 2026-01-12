# Manager Registration Setup Guide

## Overview
The manager registration system allows users to register as managers for existing teams. The system includes:
- Manager registration UI with button
- Team selection dropdown showing only teams with available manager slots (max 2 per team)
- Captain/manager approval workflow
- Private thread-based registration process
- Automated logging to bot-logs channel

## Database Setup

### 1. Apply Schema Updates

The new tables needed:
- `teams` - Stores team information (name, captain, region)
- `team_members` - Tracks all team members (players, managers, coaches)

**Option A: Using PostgreSQL psql (if psql is in PATH)**
```bash
psql -U tournament_bot -d valorant_tournament -h localhost -f database/schema.sql
# When prompted, enter: your_password
```

**Option B: Using the Python script**
```bash
# Update the password in create_teams_tables.py if needed
python create_teams_tables.py
```

**Option C: Manual SQL execution**
Connect to your database and run:
```sql
-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(50) UNIQUE NOT NULL,
    captain_discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    region VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    discord_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, discord_id, role)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_teams_captain ON teams(captain_discord_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_discord ON team_members(discord_id);
```

### 2. Verify Tables
Check that the tables were created:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- players
- player_stats
- teams
- team_members

## Bot Setup

### 1. Start the Bot
```bash
python main.py
```

You should see:
```
✓ Loaded: commands.ping
✓ Loaded: commands.registration
✓ Loaded: commands.manager_registration
```

### 2. Setup Manager Registration UI
In Discord, run:
```
/setup_manager_registration
```

Or specify a channel:
```
/setup_manager_registration channel:#manager-registration
```

This will create a message with:
- Information embed explaining manager registration
- "Register as Manager" button

## How It Works

### Registration Flow

1. **User clicks "Register as Manager"**
   - Bot checks if user is already a player (blocks if yes)
   - Bot checks if user is already a manager (blocks if yes)
   - Creates a private thread
   - Adds user, staff, head mods, and administrators to thread

2. **Team Selection**
   - Bot fetches teams with available manager slots (< 2 managers)
   - Shows dropdown with available teams
   - If no teams: Shows "No teams found" option with instructions

3. **Captain Approval**
   - After team selection, bot adds team captain and existing managers to thread
   - Shows approval UI with Approve/Reject buttons
   - Only captain or existing managers can click buttons

4. **Approval**
   - If approved: User is added as manager in database
   - Success message sent in thread
   - Registration logged to bot-logs channel

5. **Rejection**
   - If rejected: User is notified
   - Can try registering for a different team

### Database Structure

**Teams Table:**
- `id` - Unique team ID
- `team_name` - Team name (unique)
- `captain_discord_id` - Discord ID of team captain
- `region` - Team's region (NA, EU, AP, India, BR, LATAM, KR, CN)
- `created_at` / `updated_at` - Timestamps

**Team Members Table:**
- `id` - Unique record ID
- `team_id` - Foreign key to teams table
- `discord_id` - Discord ID of member
- `role` - Member role (player, manager, coach)
- `joined_at` - Timestamp

**Constraints:**
- Maximum 2 managers per team (enforced in queries)
- Maximum 6 players per team (will be enforced in team registration)
- Maximum 1 coach per team (will be enforced in team registration)
- Users can only be in one team with one role

## Testing

### Create Test Data

Before testing manager registration, you need at least one team. Manually insert test data:

```sql
-- First, ensure you have a registered player to be captain
-- Get a player's discord_id from the players table
SELECT discord_id, ign FROM players LIMIT 1;

-- Insert a test team (replace 123456789 with actual discord_id)
INSERT INTO teams (team_name, captain_discord_id, region)
VALUES ('Test Team Alpha', 123456789, 'NA');

-- Verify team was created
SELECT * FROM teams;
```

### Test Manager Registration

1. Use a different Discord account (not registered as player)
2. Click "Register as Manager" button
3. Select "Test Team Alpha" from dropdown
4. Captain should see approval request in thread
5. Captain clicks "Approve"
6. Manager should be added successfully

### Verify Manager was Added

```sql
-- Check team_members table
SELECT tm.*, p.ign 
FROM team_members tm
LEFT JOIN players p ON tm.discord_id = p.discord_id
WHERE role = 'manager';
```

## Troubleshooting

### "No teams found" always shows
- Check if teams exist: `SELECT * FROM teams;`
- Check if teams have manager slots: `SELECT id, team_name FROM teams WHERE id NOT IN (SELECT team_id FROM team_members WHERE role = 'manager' GROUP BY team_id HAVING COUNT(*) >= 2);`

### Captain not added to thread
- Verify captain_discord_id exists in Discord server
- Check bot has permission to add members to private threads

### Database connection fails
- Verify DATABASE_URL in .env file is correct
- Test connection: `python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DATABASE_URL'))"`
- Ensure PostgreSQL is running

### Approval buttons don't work
- Check if clicking user is captain or existing manager
- Verify team_id and discord_ids are correct in database

## Next Steps

The following features still need to be implemented:

1. **Team Registration** (for captains)
   - Captain registration command
   - Team name and region selection
   - Automatically set captain as first player

2. **Player Team Registration** (join existing teams)
   - Players can request to join teams
   - Captain/manager approval
   - Enforce 6-player limit

3. **Coach Registration**
   - Similar to manager registration
   - Maximum 1 coach per team

4. **Team Management Commands**
   - View team roster
   - Remove team members
   - Transfer captain role
   - Disband team

## File Structure

```
commands/
├── manager_registration.py  # Manager registration system
├── registration.py          # Player registration system
└── ping.py                  # Test command

database/
├── db.py                    # Database operations
└── schema.sql              # Database schema

apply_schema.py             # Script to apply schema updates
create_teams_tables.py      # Script to create teams tables
main.py                     # Bot entry point
```

## Logging

Manager registrations are logged to the bot-logs channel with format:
- Title: "New Manager Registration (Thread - Manual)"
- User mention and details
- Team name and region
- Who approved the request
- Timestamp

Example log:
```
New Manager Registration (Thread - Manual)

User: @JohnDoe
Team: Test Team Alpha
Region: NA
Approved By: @TeamCaptain

User ID: 123456789
Method: Manual
Timestamp: 2024-01-15 10:30:00
```
