# Registration Lock System - Implementation Summary

## Changes Made

### 1. Database Schema (New Files)

#### `database/migrations/010_registration_lock.sql`
- **Table: `registration_status`**
  - Singleton table (CHECK constraint: id = 1)
  - Tracks lock state, messages, and who locked/unlocked
  - Initialized with `is_locked = FALSE` by default

- **Table: `registration_notifications`**
  - Stores user subscriptions
  - Tracks notification delivery status
  - Index on `notified = FALSE` for performance

### 2. Database Methods (Modified)

#### `database/db.py`
Added 7 new methods before line 537:

| Method | Purpose |
|--------|---------|
| `is_registration_locked()` | Quick boolean check for lock status |
| `get_registration_status()` | Get full status dictionary |
| `lock_registrations(admin_id, message)` | Lock with custom message |
| `unlock_registrations(admin_id)` | Unlock and return subscriber IDs |
| `subscribe_registration_notification(discord_id)` | Add user to notifications |
| `unsubscribe_registration_notification(discord_id)` | Remove user from notifications |
| `is_subscribed_to_notifications(discord_id)` | Check subscription status |

### 3. Admin Commands (Modified)

#### `commands/admin.py`
Added 2 new admin commands after line 2195:

- **`/admin-lock-registrations`**
  - Optional parameter: `message` (custom lock message)
  - Records who locked and when
  - Shows confirmation embed

- **`/admin-unlock-registrations`**
  - No parameters
  - Notifies all subscribers via DM
  - Shows success/failure count
  - Marks subscribers as notified

### 4. Registration Lock Checks (Modified)

Added lock check to ALL registration buttons BEFORE any other logic:

#### `commands/registration.py`
- **New Class: `NotificationToggleView`**
  - Lines 13-84
  - Dynamic button based on subscription status
  - Handles subscribe/unsubscribe callbacks
  - 5-minute timeout

- **Modified: `RegistrationButtons.register()`**
  - Lines 860-882
  - Lock check at the very start
  - Shows lock embed with notification toggle
  - Returns early if locked

#### `commands/team_registration.py`
- **Modified: `TeamRegistrationButtons.register_team()`**
  - Lines 1128-1156
  - Same lock check pattern
  - Imports `NotificationToggleView` from registration module

#### `commands/manager_registration.py`
- **Modified: `ManagerRegistrationButtons.register_manager()`**
  - Lines 16-46
  - Lock check before ban check
  - Imports `NotificationToggleView`

#### `commands/coach_registration.py`
- **Modified: `CoachRegistrationButtons.register_coach()`**
  - Lines 16-46
  - Lock check before ban check
  - Imports `NotificationToggleView`

### 5. Documentation (New Files)

#### `REGISTRATION_LOCK_GUIDE.md`
- Complete feature documentation
- Admin command reference
- User experience flow
- Database schema explanation
- Troubleshooting guide

#### `TESTING_REGISTRATION_LOCK.md`
- Step-by-step testing instructions
- 8 test scenarios
- Database verification queries
- Common issues and solutions
- Performance testing guide

#### `setup_registration_lock.sh`
- Bash script for Linux/Mac
- Automated migration execution
- Verification checks
- Status reporting

#### `setup_registration_lock.ps1`
- PowerShell script for Windows
- Same functionality as bash version
- Password prompt for security

## File Changes Summary

### New Files (7)
1. `database/migrations/010_registration_lock.sql` - Database schema
2. `REGISTRATION_LOCK_GUIDE.md` - Feature documentation
3. `TESTING_REGISTRATION_LOCK.md` - Testing guide
4. `setup_registration_lock.sh` - Linux/Mac setup script
5. `setup_registration_lock.ps1` - Windows setup script

### Modified Files (5)
1. `database/db.py` - Added 7 new database methods
2. `commands/admin.py` - Added 2 new admin commands
3. `commands/registration.py` - Added NotificationToggleView + lock check
4. `commands/team_registration.py` - Added lock check
5. `commands/manager_registration.py` - Added lock check
6. `commands/coach_registration.py` - Added lock check

## Deployment Steps

### Step 1: Pull Changes
```bash
cd /home/pi/tournament-bot
git pull origin main
```

### Step 2: Run Migration
```bash
# Option A: Use setup script
./setup_registration_lock.sh

# Option B: Manual
psql -h localhost -U tournament_bot -d valorant_tournament \
  -f database/migrations/010_registration_lock.sql
```

### Step 3: Restart Bot
```bash
sudo systemctl restart tournament-manager
sudo systemctl status tournament-manager
```

### Step 4: Verify
```bash
# Check commands loaded
# In Discord: type / and look for admin-lock-registrations

# Check database
psql -h localhost -U tournament_bot -d valorant_tournament \
  -c "SELECT * FROM registration_status;"
```

### Step 5: Test
Follow `TESTING_REGISTRATION_LOCK.md` for complete test suite.

## Feature Flow Diagram

```
User Clicks Registration Button
         │
         ├─→ Check: Is Locked?
         │   ├─→ YES
         │   │   └─→ Show Lock Message
         │   │       └─→ Show Notification Toggle Button
         │   │           ├─→ User Subscribes
         │   │           │   └─→ DM sent when unlocked
         │   │           └─→ User Doesn't Subscribe
         │   │               └─→ No notification
         │   │
         │   └─→ NO
         │       └─→ Normal Registration Flow
         │           └─→ Create thread/show form
         │
Admin Unlocks Registrations
         │
         ├─→ Get all subscribers (notified = FALSE)
         ├─→ Send DM to each subscriber
         ├─→ Mark as notified = TRUE
         └─→ Show admin success/failure count
```

## Code Quality Notes

### Design Patterns Used
1. **Singleton Pattern**: `registration_status` table with CHECK constraint
2. **Observer Pattern**: Notification subscription system
3. **Strategy Pattern**: Dynamic button behavior based on state

### Best Practices Followed
- ✅ Early returns for lock checks (fail fast)
- ✅ Centralized NotificationToggleView (DRY principle)
- ✅ Database indexes for performance
- ✅ Comprehensive error handling
- ✅ User feedback for all actions
- ✅ Audit trail (who/when locked/unlocked)
- ✅ Idempotent operations (can run safely multiple times)

### Performance Considerations
- Lock check is a single row query (fast)
- Index on `notified = FALSE` for efficient subscriber queries
- DM sending in sequence (could be parallelized for 100+ subscribers)
- View timeout of 5 minutes to prevent memory leaks

## Rollback Plan

If issues arise:

### Quick Rollback
```bash
# Revert code changes
git checkout HEAD~1

# Drop new tables (optional - keeps data if you fix issues later)
psql -h localhost -U tournament_bot -d valorant_tournament \
  -c "DROP TABLE IF EXISTS registration_notifications, registration_status;"

# Restart bot
sudo systemctl restart tournament-manager
```

### Data Preservation
To keep subscriber data during rollback:
```sql
-- Just disable lock without dropping tables
UPDATE registration_status SET is_locked = FALSE WHERE id = 1;
```

Then fix code issues and redeploy without running migration again.

## Future Enhancements

Discussed in `REGISTRATION_LOCK_GUIDE.md`:
- Scheduled lock/unlock
- Granular locks (per registration type)
- Multiple notification groups
- Analytics dashboard
- Subscriber management commands

## Support

For issues:
1. Check bot logs: `sudo journalctl -u tournament-manager -f`
2. Verify database: `SELECT * FROM registration_status;`
3. Test lock status: Try registration buttons
4. Check documentation: `REGISTRATION_LOCK_GUIDE.md`
5. Run test suite: `TESTING_REGISTRATION_LOCK.md`
