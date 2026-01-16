# Database Migration Instructions - Add Agent Column

## Overview
This migration adds an `agent` column to the `players` table to store each player's preferred VALORANT agent.

## Steps to Update Your Database

### 1. Run the Migration Script

```bash
python add_agent_column.py
```

This script will:
- Connect to your PostgreSQL database
- Check if the `agent` column already exists
- Add the column if it doesn't exist (VARCHAR(50), nullable)
- Display the current table structure

### 2. Expected Output

```
============================================================
Database Migration: Add Agent Column
============================================================
Connecting to database...
✅ Successfully added 'agent' column to players table

📋 Current players table structure:
------------------------------------------------------------
  id                             bigint               NOT NULL
  discord_id                     bigint               NOT NULL
  ign                            character varying    NOT NULL
  player_id                      character varying    NOT NULL
  region                         character varying    NOT NULL
  agent                          character varying    NULL
  tournament_notifications       boolean              NOT NULL
  created_at                     timestamp            NOT NULL
  updated_at                     timestamp            NOT NULL
------------------------------------------------------------

✅ Database connection closed

✅ Migration complete!
```

### 3. Verify the Migration

After running the script, verify the column was added:

```sql
-- Connect to your database and run:
\d players

-- Or check the data:
SELECT id, ign, agent FROM players LIMIT 5;
```

## What Changed

### Database Schema
- **Table:** `players`
- **New Column:** `agent` (VARCHAR(50), nullable)
- **Purpose:** Store player's preferred VALORANT agent

### Code Changes
1. **Registration Flow:** Added agent selection step after region selection
2. **Agent Options:** 23 agents available (Sage, Phoenix, Reyna, etc.)
3. **Database Method:** Updated `create_player()` to accept `agent` parameter
4. **Works For:** Both regular registration and manager/captain-assisted registration

## Available Agents

Sage, Phoenix, Reyna, Sova, Brimstone, Raze, Skye, Jett, Viper, Breach, Cypher, 
Killjoy, Omen, Yoru, Astra, KAYO, Chamber, Neon, Fade, Gecko, Iso, Clove, Tejo

## Rollback (if needed)

If you need to remove the column:

```sql
ALTER TABLE players DROP COLUMN agent;
```

## Notes

- The `agent` column is nullable (NULL allowed) so existing players won't have issues
- New registrations will require agent selection
- The agent data can be used for team composition analysis, statistics, etc.
