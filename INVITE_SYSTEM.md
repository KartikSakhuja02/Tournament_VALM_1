# Team Invite System - Implementation Summary

## What Was Implemented

### 1. **New `/invite` Command**
- **Location**: `commands/team_management.py` (new file)
- **Usage**: `/invite @playername`
- **Purpose**: Captains and managers can invite registered players to their teams
- **Restrictions**: Command can only be used in the designated commands channel

### 2. **Features**

#### **Command Validation**
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

### 3. **Command Channel Restriction**
- **New File**: `utils/checks.py`
- **New Decorator**: `@commands_channel_only()`
- **Configuration**: Add `COMMANDS_CHANNEL_ID` to your `.env` file
- **Behavior**: 
  - If `COMMANDS_CHANNEL_ID` is set, commands only work in that channel
  - If not set, commands work everywhere
  - Shows error message with channel mention if used in wrong channel

### 4. **Database Operations**
- Uses existing `db.get_user_teams_by_role()` to get captain/manager teams
- Uses existing `db.get_player_by_discord_id()` to verify registration
- Uses existing `db.get_team_members()` to check for duplicates
- Uses existing `db.add_team_member()` to add player to team
- Uses existing `db.get_team_by_id()` for logging

## How It Works

### Flow Diagram

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

## Configuration

### Required Environment Variables

Add to your `.env` file:
```env
COMMANDS_CHANNEL_ID=your_commands_channel_id_here
```

### Optional Behavior
- If `COMMANDS_CHANNEL_ID` is not set, commands work in all channels
- If set, commands are restricted to that specific channel only

## Key Differences from "Register Your Player"

| Feature | Register Your Player | Invite Player |
|---------|---------------------|---------------|
| **Purpose** | Help lazy players get registered | Invite already-registered players |
| **Player State** | Player is NOT registered yet | Player MUST be registered |
| **Consent** | Both can fill form, player added automatically | Player chooses to accept/decline |
| **Registration** | Creates new player record | No registration, just team join |
| **Use Case** | "My player is lazy, let me register them" | "Join my team!" |

## Files Modified/Created

### New Files
1. ✅ `commands/team_management.py` - Team invite command and views (328 lines)
2. ✅ `utils/checks.py` - Command channel restriction decorator (27 lines)

### Modified Files
1. ✅ `main.py` - Added team_management to cog loading
2. ✅ `.env.example` - Added COMMANDS_CHANNEL_ID

## Testing Checklist

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
- [ ] Command only works in COMMANDS_CHANNEL_ID
- [ ] Proper error if DMs disabled

## Usage Examples

### Example 1: Single Team Captain
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

### Example 3: Wrong Channel
```
Player: /invite @Someone
Bot: ❌ Commands can only be used in #bot-commands
```

## Notes

- Invite system is completely separate from "Register Your Player"
- Players added via invite have role='player' in team_members table
- No limit on how many teams a player can join (implement if needed)
- Invites don't expire (persistent view with timeout=None)
- DM privacy is respected - graceful error if DMs disabled
- All team actions are logged to BOT_LOGS_CHANNEL

## Future Enhancements (Optional)

- Add `/leave` command for players to leave teams
- Add `/kick` command for captains/managers to remove players
- Add `/roster` command to view team members
- Add invite expiration (e.g., 24 hours)
- Add limit on number of teams per player
- Add team capacity limits
