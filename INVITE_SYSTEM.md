# Team Management System - Complete Documentation

## What Was Implemented

### Commands Overview

| Command | Who Can Use | Purpose |
|---------|------------|---------|
| `/invite @player` | Captains, Managers | Invite registered players to team |
| `/leave` | Any team member | Leave a team you're part of |
| `/kick @player` | Captains, Managers | Remove a player from your team |
| `/disband` | Captains, Managers | Permanently delete your team |
| `/transfer-captainship` | Captains only | Transfer captainship to another member |

All commands are restricted to the designated commands channel (configurable via `COMMANDS_CHANNEL_ID`).

---

## 1. `/invite @player` Command

### Features
- Only captains and managers can send invites
- Invited player must be registered already
- Cannot invite yourself
- Cannot invite someone already on the team
- Checks for duplicate team membership

#### **Multi-Team Support**
- If captain/manager has multiple teams, they choose which team to invite the player to
- Dropdown selection shows team name, tag, and region

#### **DM Invite System**
- Bot sends a DM to the invited player with:
  - Team information (name, tag, region)
  - Who invited them
  - Accept/Decline buttons
  
#### **Response Handling**
- **Accept**: 
  - Player is added to team with role='player'
  - Success message sent to player
  - Inviter gets notified via DM
  - Bot logs the join to BOT_LOGS_CHANNEL
  - Buttons are disabled
  
- **Decline**: 
  - Player sees decline confirmation
  - Inviter gets notified via DM
  - Buttons are disabled

#### **Error Handling**
- Gracefully handles DMs disabled (notifies inviter to tell player to enable DMs)
- Checks if player already member before adding
- Proper error messages for all edge cases

---

## 2. `/leave` Command

### Features
- Any team member (captain, manager, player, coach) can leave their team
- Multi-team support: If member of multiple teams, dropdown to choose which to leave
- Sends DM confirmation before leaving
- Accept/Cancel buttons in DM for safety
- Logs all leaves to BOT_LOGS_CHANNEL

### Flow
1. User runs `/leave`
2. Bot checks which teams user is part of
3. If multiple teams → dropdown to select which to leave
4. Bot sends DM with team info and confirmation buttons
5. User clicks "Confirm Leave" or "Cancel"
6. If confirmed → removed from team, logged

### Safety Features
- Cannot accidentally leave (requires DM confirmation)
- Shows team name, tag, region, and your role before confirming
- Warning that action cannot be undone
- Cancel option available

---

## 3. `/kick @player` Command

### Features
- Only captains and managers can kick players
- Cannot kick team captains (protection)
- Cannot kick yourself (use `/leave` instead)
- Multi-team support: Choose which team to kick player from
- Kicked player receives DM notification
- Logs all kicks to BOT_LOGS_CHANNEL

### Flow
1. Captain/Manager runs `/kick @player`
2. Bot checks kicker's permissions
3. Bot finds which teams both kicker and target player share
4. If multiple teams → dropdown to select which team
5. Player is removed from team
6. Kicked player gets DM notification
7. Action is logged

### Safety Features
- Cannot kick captains (prevents team hijacking)
- Kicker must be captain/manager of the team
- Both kicker and kicked player get confirmation
- All kicks are logged for moderation

---

## 5. `/transfer-captainship` Command

### Features
- Only team captains can transfer captainship
- Multi-team support: Choose which team if captain of multiple
- Can transfer to players or managers only (not coaches)
- Sends DM with dropdown of eligible members
- Old captain automatically becomes a manager
- New captain receives notification of promotion
- Comprehensive logging to BOT_LOGS_CHANNEL

### Flow
1. Captain runs `/transfer-captainship`
2. If multiple teams → dropdown to select which team
3. Bot sends DM with list of eligible members (players/managers)
4. Captain selects new captain from dropdown
5. Database updated:
   - Team captain changed to new member
   - Old captain becomes manager
   - New captain's role updated to captain
6. Both captains notified
7. Action is logged

### Safety Features
- Only captains can transfer captainship
- Can only transfer to players or managers (not coaches)
- Current captain cannot select themselves
- New captain gets detailed notification of responsibilities
- All transfers are logged for accountability

---

## Command Channel Restriction

### Features
- Only captains and managers can disband teams
- Multi-team support: Choose which team to disband if managing multiple
- Shows team info and member count before confirming
- **ALL team members** are notified via DM
- Team and all team_members entries are permanently deleted
- Comprehensive logging to BOT_LOGS_CHANNEL

### Flow
1. Captain/Manager runs `/disband`
2. If multiple teams → dropdown to select which team
3. Bot shows confirmation with warnings
4. User clicks "⚠️ DISBAND TEAM" or "Cancel"
5. If confirmed:
   - All team members removed
   - Each member gets DM notification
   - Team is deleted from database
   - Action is logged with member count

### Safety Features
- ⚠️ **PERMANENT ACTION** warning in confirmation
- Shows member count before disbanding
- Clear explanation that action cannot be undone
- All members are notified
- Cancel option available
- Counts how many members were successfully notified

---

## Command Channel Restriction

### 3. **Command Channel Restriction**
- **New File**: `utils/checks.py`
- **New Decorator**: `@commands_channel_only()`
- **Configuration**: Add `COMMANDS_CHANNEL_ID` to your `.env` file
- **Behavior**: 
  - If `COMMANDS_CHANNEL_ID` is set, commands only work in that channel
  - If not set, commands work everywhere
  - Shows error message with channel mention if used in wrong channel

---

## Database Operations

### New Methods Added
- ✅ `db.delete_team(team_id)` - Deletes team (cascades to team_members)

### Existing Methods Used
- `db.get_user_teams_by_role()` - Get teams where user has specific role
- `db.get_player_by_discord_id()` - Verify player registration
- `db.get_team_members()` - Check team membership and get all members
- `db.add_team_member()` - Add player to team
- `db.remove_team_member()` - Remove player from team
- `db.get_team_by_id()` - Get team details for logging

---

## How It Works - Complete Flow Diagrams

### `/invite` Flow

### `/invite` Flow

```
/invite @player
    ↓
Check if user is captain/manager
    ↓
Check if player is registered
    ↓
[If multiple teams] → Show team selection dropdown
    ↓
Check if player already on team
    ↓
Send DM with invite to player
    ↓
Player clicks Accept or Decline
    ↓
[Accept] → Add to team → Notify both → Log
[Decline] → Notify both → End
```

### `/leave` Flow

```
/leave
    ↓
Check which teams user is part of
    ↓
[If multiple teams] → Show team selection dropdown
    ↓
Send DM confirmation to user
    ↓
User clicks "Confirm Leave" or "Cancel"
    ↓
[Confirm] → Remove from team → Log → Success message
[Cancel] → Cancel message → End
```

### `/kick` Flow

```
/kick @player
    ↓
Check if user is captain/manager
    ↓
Check if target player is on any of user's teams
    ↓
Check if target is a captain (cannot kick captains)
    ↓
[If multiple shared teams] → Show team selection dropdown
    ↓
Remove player from team
    ↓
Send DM to kicked player → Notify kicker → Log
```

### `/disband` Flow

```
/disband
    ↓
Check if user is captain/manager
    ↓
[If multiple teams] → Show team selection dropdown
    ↓
Show confirmation with team info & member count
    ↓
User clicks "⚠️ DISBAND TEAM" or "Cancel"
    ↓
[Confirm] → Get all team members
           → Delete team from database
           → Send DM to each member
           → Log with stats
           → Success message
[Cancel] → Cancel message → End
```

---

## Configuration

### Required Environment Variables

Add to your `.env` file:
```env
COMMANDS_CHANNEL_ID=your_commands_channel_id_here
```

### Optional Behavior
- If `COMMANDS_CHANNEL_ID` is not set, commands work in all channels
- If set, commands are restricted to that specific channel only

---

## Comparison: Assisted Registration vs Invite

| Feature | Register Your Player | Invite Player |
|---------|---------------------|---------------|
| **Purpose** | Help lazy players get registered | Invite already-registered players |
| **Player State** | Player is NOT registered yet | Player MUST be registered |
| **Consent** | Both can fill form, player added automatically | Player chooses to accept/decline |
| **Registration** | Creates new player record | No registration, just team join |
| **Use Case** | "My player is lazy, let me register them" | "Join my team!" |

---

## Files Modified/Created

### New Files
1. ✅ `commands/team_management.py` - All team management commands (787 lines)
   - `/invite` - Invite players to teams
   - `/leave` - Leave a team
   - `/kick` - Remove players from teams
   - `/disband` - Delete teams permanently
2. ✅ `utils/checks.py` - Command channel restriction decorator
3. ✅ `utils/__init__.py` - Utils package initialization

### Modified Files
1. ✅ `main.py` - Added team_management to cog loading
2. ✅ `.env.example` - Added COMMANDS_CHANNEL_ID
3. ✅ `database/db.py` - Added `delete_team()` method

---

## Testing Checklist

### `/invite` Command
- [ ] Captain can send `/invite` command
- [ ] Manager can send `/invite` command
- [ ] Non-captain/manager cannot send invites
- [ ] Cannot invite unregistered players
- [ ] Cannot invite yourself
- [ ] Multi-team users see team selection dropdown
- [ ] DM is sent to invited player with correct info
- [ ] Accept button adds player to team
- [ ] Decline button notifies inviter
- [ ] Inviter gets DM notification on accept/decline
- [ ] Bot logs channel receives join log
- [ ] Buttons disable after response
- [ ] Proper error if DMs disabled

### `/leave` Command
- [ ] Any team member can use `/leave`
- [ ] Multi-team members see dropdown
- [ ] DM confirmation sent with team details
- [ ] Confirm button removes from team
- [ ] Cancel button keeps in team
- [ ] Bot logs channel receives leave log
- [ ] Buttons disable after response
- [ ] Works for captains, managers, players, coaches

### `/kick` Command
- [ ] Only captains/managers can kick
- [ ] Cannot kick captains
- [ ] Cannot kick yourself
- [ ] Multi-team selection works
- [ ] Kicked player receives DM
- [ ] Kicker receives confirmation
- [ ] Bot logs channel receives kick log
- [ ] Player is actually removed from database

### `/disband` Command
- [ ] Only captains/managers can disband
- [ ] Multi-team selection works
- [ ] Shows member count before confirming
- [ ] ⚠️ Warning message displays
- [ ] All members receive DM notification
- [ ] Team deleted from database
- [ ] Team_members entries deleted (cascade)
- [ ] Bot logs channel receives disband log
- [ ] Cancel button works
- [ ] Success message shows notification count

### General
- [ ] Command only works in COMMANDS_CHANNEL_ID
- [ ] Proper error if used in wrong channel
- [ ] All DM failures handled gracefully

---

## Usage Examples

### Example 1: `/invite` - Single Team Captain
```
Captain: /invite @Player123
Bot: ✅ Team invite sent to @Player123 via DM!

[Player123 receives DM]
Team: Phoenix Strikers [PHX]
Region: APAC
Invited by: @Captain

[Player clicks Accept]
Player: ✅ You have successfully joined Phoenix Strikers!
Captain: [DM] @Player123 has accepted your invite!
```

### Example 2: Multi-Team Manager
```
Manager: /invite @Player456
Bot: Select which team you want to invite the player to:
     [Dropdown]
     - Team Alpha [ALPHA] (Region: EMEA)
     - Team Beta [BETA] (Region: AMERICAS)

Manager: [Selects Team Alpha]
Bot: ✅ Team invite sent to @Player456 via DM!

[Rest follows same flow as Example 1]
```

### Example 3: `/leave` - Multi-Team Player
```
Player: /leave
Bot: Select which team you want to leave:
     [Dropdown]
     - Team Alpha [ALPHA] (Role: Player | Region: EMEA)
     - Team Beta [BETA] (Role: Player | Region: AMERICAS)

Player: [Selects Team Alpha]
Bot: ✅ Leave confirmation sent to your DMs!

[Player receives DM]
Team: Team Alpha [ALPHA]
Region: EMEA
Your Role: Player
⚠️ This action cannot be undone.

[Player clicks "Confirm Leave"]
Player: ✅ You have successfully left Team Alpha.
```

### Example 4: `/kick` - Manager Kicks Player
```
Manager: /kick @Player789
Bot: ✅ @Player789 has been kicked from Phoenix Strikers!

[Player789 receives DM]
You have been removed from Phoenix Strikers [PHX].
Removed by: @Manager
Team Region: APAC
```

### Example 5: `/disband` - Captain Disbands Team
```
Captain: /disband
Bot: ⚠️ Are you sure you want to disband Phoenix Strikers?
     Team Tag: PHX
     Region: APAC
     Members: 7
     ⚠️ This action is PERMANENT and cannot be undone!
     
[Captain clicks "⚠️ DISBAND TEAM"]
Bot: ✅ Phoenix Strikers has been successfully disbanded.
     • Team members notified: 6/6
     • All team data has been deleted

[All 6 members receive DM]
Phoenix Strikers [PHX] has been disbanded.
Disbanded by: @Captain
The team no longer exists and all members have been removed.
```

### Example 6: Wrong Channel
```
Player: /invite @Someone
Bot: ❌ Commands can only be used in #bot-commands
```

---

## Important Notes

### Permissions & Safety
- Only captains and managers can: `/invite`, `/kick`, `/disband`
- Any team member can: `/leave`
- Captains CANNOT be kicked (protection against team hijacking)
- `/disband` is PERMANENT - team and all data deleted forever

### DM Requirements
- All commands that notify players use DMs
- If a player has DMs disabled, they won't receive notifications
- Commands fail gracefully if DMs are disabled
- Encourage users to enable DMs from server members

### Database Behavior
- `/disband` triggers CASCADE DELETE on team_members table
- Team logo files are NOT deleted from filesystem (manual cleanup may be needed)
- Player records remain intact after leaving/being kicked
- Only team and team_member entries are affected

### Multi-Team Support
- All commands support users managing/being part of multiple teams
- Dropdown selections appear when multiple teams are involved
- Each action is isolated to the selected team only

### Logging
- All team actions logged to BOT_LOGS_CHANNEL
- Logs include: team info, user info, timestamps, IDs
- Disband logs include member count
- Color-coded: Green (join), Orange (leave), Red (kick), Dark Red (disband)

---

## Future Enhancements (Optional)

- Add `/roster` command to view team members
- Add invite expiration (e.g., 24 hours)
- Add limit on number of teams per player
- Add team capacity limits
- Add `/promote` command to change member roles
- Cleanup team logo files when team is disbanded

