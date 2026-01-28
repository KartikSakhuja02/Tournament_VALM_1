# Registration Lock System - Testing Guide

## Quick Test Workflow

### Step 1: Setup
```bash
# Run the migration (choose one based on your OS)
# Linux/Mac:
./setup_registration_lock.sh

# Windows PowerShell:
.\setup_registration_lock.ps1

# Or manually:
psql -h localhost -U tournament_bot -d valorant_tournament -f database/migrations/010_registration_lock.sql
```

### Step 2: Restart Bot
```bash
# Stop the bot
sudo systemctl stop tournament-manager

# Start the bot
sudo systemctl start tournament-manager

# Check status
sudo systemctl status tournament-manager
```

### Step 3: Test Lock Functionality

#### Test 1: Lock Registrations
1. In Discord, run: `/admin-lock-registrations`
   - Expected: Green embed confirming lock
   - Shows who locked it
   - Shows default lock message

2. Try clicking any registration button:
   - "Register for yourself" (player)
   - "Register Your Team" (team)
   - "Register as Manager" (manager)
   - "Register as Coach" (coach)
   
   **Expected Result:**
   - Red embed: "🔒 Registrations Locked"
   - Custom message shown
   - Button: "🔕 Get Notified When Registrations Open"

#### Test 2: Subscribe to Notifications
1. Click "🔕 Get Notified When Registrations Open"
   
   **Expected Result:**
   - Green embed: "✅ Subscribed to Notifications"
   - Button changes to: "🔔 Unsubscribe from Notifications"
   - Message: "You will receive a DM when registrations open again!"

#### Test 3: Unsubscribe
1. Click "🔔 Unsubscribe from Notifications"
   
   **Expected Result:**
   - Red embed back to locked message
   - Button changes back to: "🔕 Get Notified When Registrations Open"

#### Test 4: Unlock and Notify
1. Subscribe again (using button from registration)
2. In Discord, run: `/admin-unlock-registrations`
   
   **Expected Result:**
   - Green embed confirming unlock
   - Shows who unlocked it
   - Shows notification count: "✅ 1 users notified"
   
3. Check your DMs
   
   **Expected Result:**
   - DM from bot with green embed
   - Title: "🔓 Registrations Are Now Open!"
   - Message about registrations being unlocked

#### Test 5: Verify Unlock Works
1. Try clicking any registration button
   
   **Expected Result:**
   - Normal registration flow works
   - Thread created for player registration
   - Team selection shown for team/manager/coach registration
   - NO lock message

#### Test 6: Custom Lock Message
1. Run: `/admin-lock-registrations message: Season 2 starts February 1st! Get ready!`
   
   **Expected Result:**
   - Lock confirmed
   - Shows custom message in confirmation

2. Try registration button
   
   **Expected Result:**
   - Red embed shows YOUR custom message
   - Not the default message

#### Test 7: Multiple Subscribers
1. Have 2-3 test users subscribe to notifications
2. Run `/admin-unlock-registrations`
   
   **Expected Result:**
   - Shows "✅ 3 users notified" (or however many subscribed)
   - All users receive DMs
   - If any fail, shows "❌ X failed"

#### Test 8: Re-lock (Notification Reset)
1. Lock registrations again
2. Try registration button
   
   **Expected Result:**
   - Lock message shown
   - Notification button shows "🔕 Get Notified" (NOT subscribed)
   - Previous subscription was cleared after notification

## Database Verification

### Check Lock Status
```sql
SELECT * FROM registration_status;
```

**Expected Columns:**
- `id`: 1
- `is_locked`: true/false
- `locked_at`: timestamp or null
- `locked_by`: admin Discord ID or null
- `unlocked_at`: timestamp or null
- `unlocked_by`: admin Discord ID or null
- `lock_message`: custom message or default

### Check Subscribers
```sql
SELECT * FROM registration_notifications;
```

**Expected Columns:**
- `discord_id`: User's Discord ID
- `subscribed_at`: When they subscribed
- `notified`: false (before unlock), true (after unlock)

### Check Subscriber Count
```sql
SELECT COUNT(*) FROM registration_notifications WHERE notified = FALSE;
```

This shows how many users will be notified on next unlock.

## Common Issues & Solutions

### Issue: Lock message shows but button missing
**Cause:** View timeout (5 minutes)
**Solution:** Click registration button again to get new view

### Issue: Notification not received
**Possible Causes:**
1. DMs disabled in privacy settings
2. User not in server
3. Bot doesn't have permission to DM user

**Solution:** Check `/admin-unlock-registrations` output for failed count

### Issue: Lock/unlock not working
**Cause:** Bot not restarted after migration
**Solution:** Restart bot service

### Issue: Multiple lock messages
**Cause:** Multiple views created (rapid clicking)
**Solution:** Normal behavior, users should use the latest view

## Performance Testing

### Load Test: Many Subscribers
```sql
-- Simulate 100 subscribers
INSERT INTO registration_notifications (discord_id, notified)
SELECT generate_series(1000000000000000000, 1000000000000000099), FALSE;

-- Unlock will try to notify all 100
-- Check notification time and success rate
```

### Cleanup Test Data
```sql
-- Remove test subscribers
DELETE FROM registration_notifications 
WHERE discord_id >= 1000000000000000000 
AND discord_id <= 1000000000000000099;
```

## Success Criteria

✅ All tests pass if:
1. Lock prevents all 4 registration types
2. Custom messages display correctly
3. Notification subscription toggles work
4. DMs sent on unlock
5. Subscribers cleared after notification
6. Multiple subscribers all notified
7. No errors in bot logs
8. Database queries return expected results

## Rollback (If Needed)

If something goes wrong and you need to rollback:

```sql
-- Remove the tables
DROP TABLE IF EXISTS registration_notifications;
DROP TABLE IF EXISTS registration_status;

-- Restart bot to revert code changes
sudo systemctl restart tournament-manager
```

Then use `git checkout` to revert code files if needed.
