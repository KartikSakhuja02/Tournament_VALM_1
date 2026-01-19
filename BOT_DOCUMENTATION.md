# VALORANT Mobile India Tournament Bot - Complete Guide

## Overview

This is a comprehensive Discord bot designed to manage VALORANT Mobile India Community tournaments. The bot handles player registration, team management, role assignments, and tournament operations through an intuitive interface with buttons, modals, and slash commands.

---

## 🎮 Core Features

### 1. **Player Registration System**
- Players can register themselves for tournaments
- Captains/Managers can register players on their behalf (assisted registration)
- Collects: In-Game Name (IGN), Player ID, Region, and Agent preference
- Creates private threads for each registration with staff oversight
- Automatic team assignment for assisted registrations

### 2. **Team Registration System**
- Team captains/managers can register their teams
- Collects: Team Name, Team Tag, Region
- Option to upload team logo (saved locally) or skip
- Automatically adds captain to team_members table
- Region-based role assignment (India ↔ APAC equivalent)

### 3. **Manager Registration System**
- Players can apply to become team managers (max 2 per team)
- Team dropdown shows only teams with available manager slots
- Requires approval from team captain AND existing managers
- Approval/decline workflow in private threads
- Automatic role assignment upon approval

### 4. **Coach Registration System**
- Players can apply to become team coaches (max 1 per team)
- Similar to manager registration but limited to one coach
- Requires approval from captain AND managers
- UI matches screenshot requirements with proper formatting

### 5. **Team Management Commands**
Five slash commands for complete team control:

#### `/invite @player`
- **Who can use**: Captains, Managers
- **Purpose**: Invite registered players to join your team
- **How it works**:
  1. Captain/Manager mentions a player
  2. Bot checks if player is registered
  3. If multi-team → dropdown to select which team
  4. Bot sends DM to player with team info and Accept/Decline buttons
  5. If accepted → player added to team, both notified, action logged
  6. If declined → both notified

#### `/leave`
- **Who can use**: Any team member (captain, manager, player, coach)
- **Purpose**: Leave a team you're part of
- **How it works**:
  1. User runs command
  2. If multi-team → dropdown to select which team
  3. Bot sends DM confirmation with team details
  4. User clicks "Confirm Leave" or "Cancel"
  5. If confirmed → removed from team, captains/managers notified, logged

#### `/kick @player`
- **Who can use**: Captains, Managers
- **Purpose**: Remove a player from your team
- **How it works**:
  1. Captain/Manager mentions a player
  2. Bot checks if player is on their team
  3. Cannot kick captains (protection)
  4. If multi-team → dropdown to select which team
  5. Player removed, kicked player receives DM, action logged

#### `/disband`
- **Who can use**: Captains, Managers
- **Purpose**: Permanently delete a team
- **How it works**:
  1. Captain/Manager runs command
  2. If multi-team → dropdown to select which team
  3. Shows confirmation with member count and ⚠️ warnings
  4. User clicks "⚠️ DISBAND TEAM" or "Cancel"
  5. If confirmed → all members notified via DM, team deleted, logged

#### `/transfer-captainship`
- **Who can use**: Captains only
- **Purpose**: Transfer captainship to another team member
- **How it works**:
  1. Captain runs command (ephemeral - only they see it)
  2. If multi-team → dropdown to select which team
  3. Bot sends DM with dropdown of eligible members (players/managers)
  4. Captain selects new captain
  5. Old captain becomes manager, new captain promoted
  6. Both notified, action logged

### 6. **Smart Thread Management**
- **Administrators**: Always added to registration threads (regardless of online status)
- **Bot Access**: Only added if online
  - If no Bot Access member is online → thread waits
  - When a Bot Access member comes online → automatically added to waiting threads
- Requires **Presence Intent** enabled in Discord Developer Portal

### 7. **Command Channel Restriction**
- All slash commands restricted to designated channel
- Configure via `COMMANDS_CHANNEL_ID` in .env
- Error message shows channel mention if used in wrong channel

---

## 📋 Registration Flow Details

### **Player Self-Registration**
1. User clicks "Register" button in registration channel
2. Bot checks if already registered (prevents duplicates)
3. Creates private thread with user + staff
4. User clicks "Fill Form" button in thread
5. Modal appears with fields: IGN, Player ID, Region
6. User selects agent preference from dropdown (23 agents)
7. User views consent with region-appropriate role
8. User clicks "I Consent" → registered + role assigned + logged

### **Assisted Player Registration** (Manager/Captain helps player)
1. Manager/Captain clicks "Register Your Player" button
2. Modal appears to search for player by username
3. Bot checks if player already registered
4. Creates thread with target player + manager/captain + staff
5. **Either player OR manager/captain** can fill the form
6. Player follows same flow (region → agent → consent)
7. Upon consent → player registered AND automatically added to manager/captain's teams
8. Success message shows which teams player was added to

### **Team Registration**
1. Captain clicks "Register Your Team" button
2. Bot checks if user already has a team
3. Creates private thread with captain + staff
4. Captain selects role: Captain or Manager
5. Modal appears for team details (name, tag)
6. Validation: Team name/tag must be unique
7. Captain selects region from dropdown
8. Logo upload: Captain can upload logo OR click "Skip Logo"
9. Logo saved as "teamname.png" in team_logos/ directory
10. Team created → captain added as team member → logged

### **Manager Registration**
1. User clicks "Register as Manager" button
2. Bot checks if user already a team member (prevents duplicates)
3. Creates private thread with user + staff
4. Dropdown shows teams with <2 managers
5. "My Team is Not Listed" option always available
6. User selects team and submits
7. Thread adds captain + existing managers
8. Captain/Managers see Approve/Decline buttons
9. Approval → user added as manager + logged
10. Decline → thread deleted after 3 seconds

### **Coach Registration**
1. User clicks "Register as Coach" button
2. Bot checks if user already a team member
3. Creates private thread with user + staff
4. Dropdown shows teams with 0 coaches
5. User selects team
6. Thread adds captain + managers
7. Captain/Managers see Approve/Decline buttons
8. Approval → user added as coach + logged
9. Decline → thread deleted after 3 seconds

---

## 🗄️ Database Structure

### **Tables**

#### `players`
- `id` (Primary Key)
- `discord_id` (Unique)
- `ign` (In-Game Name)
- `player_id` (VALORANT Player ID)
- `region` (AMERICAS, EMEA, India, APAC, CN)
- `agent` (Selected agent preference)
- `tournament_notifications` (Boolean)
- `created_at`, `updated_at`

#### `teams`
- `id` (Primary Key)
- `team_name` (Unique)
- `team_tag` (Unique, 2-5 chars)
- `captain_discord_id`
- `region`
- `logo_url` (Local file path)
- `created_at`, `updated_at`

#### `team_members`
- `id` (Primary Key)
- `team_id` (Foreign Key → teams.id, CASCADE DELETE)
- `discord_id`
- `role` ('captain', 'manager', 'player', 'coach')
- `joined_at`

#### `player_stats`
- Links to players table
- Stores additional player statistics

### **Key Database Operations**
- **LEFT JOIN** for team members (includes non-player members like managers/coaches)
- **CASCADE DELETE** on team deletion (automatically removes team_members)
- **Unique constraints** on team names, tags, and player discord IDs
- **Region mapping**: India and APAC treated as equivalent

---

## 🎯 Special Features

### **1. Region Role Assignment**
- Bot assigns Discord roles based on selected region
- India and APAC roles are interchangeable
- Roles: AMERICAS, EMEA, India, APAC, CN
- Configured via role IDs in .env file

### **2. Agent Selection**
23 agents available:
- Sage, Phoenix, Reyna, Sova, Brimstone, Raze, Skye, Jett
- Viper, Breach, Cypher, Killjoy, Omen, Yoru, Astra, KAYO
- Chamber, Neon, Fade, Gecko, Iso, Clove, Tejo

### **3. Multi-Team Support**
- Captains/Managers can manage multiple teams
- Dropdowns appear when actions involve multiple teams
- Each action isolated to selected team

### **4. Logging System**
All actions logged to BOT_LOGS_CHANNEL:
- Player registrations
- Team registrations
- Manager approvals/declines
- Coach approvals/declines
- Team invites (accepted)
- Team leaves
- Player kicks
- Team disbands
- Captainship transfers

Logs include:
- User details (mention + name)
- Team details (name + tag)
- Timestamps
- Relevant IDs for tracking

### **5. DM Notifications**
Used for:
- Team invites
- Leave confirmations
- Kick notifications
- Disband notifications (all members)
- Captainship transfer notifications
- Approval requests

Graceful error handling if DMs disabled.

### **6. Validation & Safety**
- **Before thread creation**: Check if already registered/member
- **Before team creation**: Validate team name/tag uniqueness
- **Manager limit**: Max 2 per team
- **Coach limit**: Max 1 per team
- **Cannot kick captains**: Protection against team hijacking
- **Disband warnings**: Clear PERMANENT ACTION warnings
- **Ephemeral messages**: Sensitive commands only visible to user

---

## ⚙️ Bot Configuration

### **Environment Variables (.env)**

```env
# Bot Token
DISCORD_BOT_TOKEN=your_bot_token_here

# Role IDs
TEST_ROLE_ID=role_id                    # Optional: Restrict bot to specific role
BOT_ACCESS_ROLE_ID=role_id              # Bot Access - added to threads when online
ADMINISTRATOR_ROLE_ID=role_id           # Administrators - always added to threads

# Region Role IDs
AMERICAS_ROLE_ID=role_id
EMEA_ROLE_ID=role_id
INDIA_ROLE_ID=role_id
APAC_ROLE_ID=role_id
CN_ROLE_ID=role_id

# Channel IDs
REGISTRATION_CHANNEL_ID=channel_id      # Player registration
TEAM_REGISTRATION_CHANNEL_ID=channel_id # Team registration
MANAGER_REGISTRATION_CHANNEL_ID=channel_id
COACH_REGISTRATION_CHANNEL_ID=channel_id
BOT_LOGS_CHANNEL_ID=channel_id          # All logs
COMMANDS_CHANNEL_ID=channel_id          # Where slash commands work

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

### **Required Discord Intents**
- ✅ **Message Content Intent**
- ✅ **Server Members Intent**
- ✅ **Presence Intent** (for online status detection)

Enable in Discord Developer Portal → Bot → Privileged Gateway Intents

---

## 🔧 Technical Architecture

### **Bot Structure**
```
main.py                          # Bot entry point, event handlers
commands/
  ├── ping.py                   # Test command
  ├── registration.py           # Player registration (1087 lines)
  ├── team_registration.py      # Team registration (782 lines)
  ├── manager_registration.py   # Manager registration (501 lines)
  ├── coach_registration.py     # Coach registration (512 lines)
  └── team_management.py        # All 5 slash commands (1360+ lines)
database/
  └── db.py                     # PostgreSQL operations (395 lines)
utils/
  ├── __init__.py               # TEST_ROLE_ID, has_test_role()
  ├── checks.py                 # commands_channel_only() decorator
  └── thread_manager.py         # Smart staff addition to threads
```

### **Key Technologies**
- **discord.py 2.3.2**: Discord API wrapper
- **PostgreSQL**: Database (asyncpg)
- **aiohttp**: Async HTTP for logo downloads
- **Python 3.13**: Runtime environment

### **Design Patterns**
- **Cog-based architecture**: Modular command organization
- **Persistent views**: Buttons survive bot restarts
- **Modal forms**: Clean data collection
- **Private threads**: Isolated registration processes
- **Async/await**: Non-blocking operations
- **setup_hook**: Fast bot initialization before Discord connection

---

## 📊 Bot Startup Sequence

1. **Load environment variables** (.env)
2. **Connect to PostgreSQL database**
3. **Load all cogs** (command modules)
4. **Sync slash commands** to Discord
5. **Connect to Discord** (login)
6. **Purge registration channels** (remove old messages)
7. **Send registration UI messages**:
   - Player registration (Register + Register Your Player buttons)
   - Team registration (Register Your Team button)
   - Manager registration (Register as Manager button)
   - Coach registration (Register as Coach button)
8. **Start monitoring presence updates** (for HeadMod waiting threads)

---

## 🎨 User Interface Elements

### **Buttons**
- Primary (Blue): Main actions (Register, Fill Form)
- Success (Green): Accept/Approve actions
- Danger (Red): Decline/Kick/Leave/Disband
- Secondary (Gray): Cancel actions

### **Dropdowns**
- Team selection (when managing multiple teams)
- Agent selection (23 agents)
- Region selection (5 regions)
- Member selection (for captainship transfer)

### **Modals**
- Player registration form (IGN, Player ID, Region)
- Player search form (for assisted registration)
- Team registration form (Team Name, Team Tag)

### **Embeds**
- Color-coded: Blue (info), Green (success), Red (error/danger), Orange (warning), Gold (promotion)
- Consistent formatting with team details, user mentions
- Timestamps on all actions

---

## 🔐 Permission System

### **Role Hierarchy**
1. **Administrators**: Full access, always added to threads
2. **Bot Access**: Oversight, added to threads when online (waits if none online)
3. **Captains**: Team control (invite, kick, disband, transfer captainship)
4. **Managers**: Team management (invite, kick, disband)
5. **Players**: Basic team membership
6. **Coaches**: Team support, cannot become captain

### **Command Permissions**
- `/invite`: Captains, Managers
- `/leave`: Any team member
- `/kick`: Captains, Managers (cannot kick captains)
- `/disband`: Captains, Managers
- `/transfer-captainship`: Captains only

---

## 📝 Common Workflows

### **New Player Joins Tournament**
1. Player clicks "Register" → fills form → selects agent → consents
2. Gets region role assigned
3. Receives confirmation message
4. Action logged to bot logs
5. Player now visible in system for team invites

### **Team Captain Builds Roster**
1. Captain registers team
2. Captain invites players via `/invite @player`
3. Players accept invites
4. Captain adds managers via manager registration approval
5. Captain adds coach via coach registration approval
6. Full roster assembled

### **Player Switches Teams**
1. Player runs `/leave` on old team
2. Captains/managers of old team notified
3. New team captain runs `/invite @player`
4. Player accepts
5. Player now on new team

### **Captain Transfers Leadership**
1. Captain runs `/transfer-captainship`
2. Receives DM with member dropdown
3. Selects new captain (must be player or manager)
4. Old captain becomes manager
5. New captain promoted with responsibilities notification
6. Both captains notified, action logged

### **Team Disbands**
1. Captain/Manager runs `/disband`
2. Sees confirmation with member count
3. Confirms with "⚠️ DISBAND TEAM" button
4. All members receive DM notification
5. Team deleted from database
6. Action logged with statistics

---

## 🚨 Error Handling

- **DMs disabled**: Graceful messages, suggests enabling DMs
- **Invalid data**: Clear validation messages
- **Duplicate registrations**: Prevents with checks before thread creation
- **Concurrent operations**: Database transactions handle conflicts
- **Thread access**: Only allowed users can interact with registration forms
- **Missing roles/channels**: Informative error messages in console
- **Command sync failures**: Retry logic and clear error logging

---

## 📈 Scalability Features

- **Database connection pooling** (1-10 connections)
- **Async operations** (non-blocking I/O)
- **Command timeout handling** (300 seconds default)
- **Automatic thread archiving** (60 minutes)
- **Efficient role caching** (Discord.py internal)
- **Batch operations** (multiple team member additions)
- **Smart presence monitoring** (only tracks HeadMod status changes)

---

## 🔍 Debugging & Monitoring

### **Console Output**
```
✓ Database connected
✓ Loaded: commands.registration
✓ Synced 5 command(s)
🟢 Bot is online
✓ Added admin John#1234 to thread
⏳ No Bot Access members online. Thread will wait...
✓ Bot Access member came online!
✓ Player123 registered successfully
✓ Team Phoenix created
```

### **Bot Logs Channel**
All actions logged with embeds:
- User mentions and IDs
- Team details
- Timestamps
- Action results

---

## 💡 Best Practices

1. **Always enable required intents** in Discord Developer Portal
2. **Set COMMANDS_CHANNEL_ID** to prevent command spam
3. **Configure all role IDs** for proper role assignment
4. **Enable DMs** for users (team invites, notifications)
5. **Regular database backups** (player/team data)
6. **Monitor bot logs channel** for issues
7. **Test in development server** before production
8. **Keep team logos organized** in team_logos/ directory

---

## 🎯 Summary

This bot provides a **complete tournament management solution** with:
- ✅ Player registration (self + assisted)
- ✅ Team registration with logo support
- ✅ Manager & coach registration with approval
- ✅ 5 powerful team management commands
- ✅ Smart thread management with online detection
- ✅ Comprehensive logging and notifications
- ✅ Multi-team support for captains/managers
- ✅ Region-based role assignment
- ✅ Database-backed persistence
- ✅ Safety features and validation

**Total Lines of Code**: ~5000+ lines across all modules
**Supported Roles**: Captain, Manager, Player, Coach
**Slash Commands**: 5 (invite, leave, kick, disband, transfer-captainship)
**Registration Types**: 4 (player, team, manager, coach)
**Database Tables**: 4 (players, teams, team_members, player_stats)
