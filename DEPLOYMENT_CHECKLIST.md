# Registration Lock System - Deployment Checklist

## Pre-Deployment

- [ ] Review all changes in [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- [ ] Read feature documentation in [REGISTRATION_LOCK_GUIDE.md](REGISTRATION_LOCK_GUIDE.md)
- [ ] Familiarize yourself with testing procedures in [TESTING_REGISTRATION_LOCK.md](TESTING_REGISTRATION_LOCK.md)

## Files to Deploy

### Modified Files (6)
- [ ] `database/db.py` - New database methods
- [ ] `commands/admin.py` - New admin commands
- [ ] `commands/registration.py` - Lock check + NotificationToggleView
- [ ] `commands/team_registration.py` - Lock check
- [ ] `commands/manager_registration.py` - Lock check
- [ ] `commands/coach_registration.py` - Lock check

### New Files (5)
- [ ] `database/migrations/010_registration_lock.sql` - Database schema
- [ ] `REGISTRATION_LOCK_GUIDE.md` - Documentation
- [ ] `TESTING_REGISTRATION_LOCK.md` - Testing guide
- [ ] `setup_registration_lock.sh` - Linux/Mac setup script
- [ ] `setup_registration_lock.ps1` - Windows setup script

## Deployment Steps

### 1. Backup Current State
```bash
# On RPI
cd /home/pi/tournament-bot

# Create backup
sudo systemctl stop tournament-manager
cp -r . ../tournament-bot-backup-$(date +%Y%m%d)

# Backup database
pg_dump -h localhost -U tournament_bot valorant_tournament > backup.sql
```

- [ ] Bot stopped
- [ ] Files backed up
- [ ] Database backed up

### 2. Pull Changes
```bash
# Ensure clean state
git status

# Pull latest changes
git pull origin main

# Verify all files updated
git log --oneline -5
```

- [ ] Git pull successful
- [ ] All modified files show in git log
- [ ] No merge conflicts

### 3. Run Database Migration
```bash
# Option A: Using setup script (recommended)
chmod +x setup_registration_lock.sh
./setup_registration_lock.sh

# Option B: Manual execution
psql -h localhost -U tournament_bot -d valorant_tournament \
  -f database/migrations/010_registration_lock.sql
```

- [ ] Migration executed successfully
- [ ] Tables created: `registration_status`, `registration_notifications`
- [ ] Default row inserted in `registration_status`
- [ ] Verification query passed

**Verification:**
```sql
-- Should return 1 row with is_locked = FALSE
SELECT * FROM registration_status;

-- Should show table structure
\d registration_notifications
```

### 4. Restart Bot
```bash
sudo systemctl start tournament-manager
sudo systemctl status tournament-manager

# Check logs for startup
sudo journalctl -u tournament-manager -f --lines=50
```

- [ ] Bot started successfully
- [ ] No errors in startup logs
- [ ] Commands loaded (look for "Synced X commands")

### 5. Verify Commands in Discord
In your Discord server:
- [ ] Type `/admin-lock-registrations` - command appears
- [ ] Type `/admin-unlock-registrations` - command appears
- [ ] Total admin commands should increase by 2

### 6. Basic Functionality Test

#### Quick Test (5 minutes)
1. [ ] Run `/admin-lock-registrations` in Discord
   - Expect: Success message with green embed

2. [ ] Click "Register for yourself" button
   - Expect: Red lock message with notification toggle button

3. [ ] Click notification subscribe button
   - Expect: Green confirmation, button changes to unsubscribe

4. [ ] Run `/admin-unlock-registrations`
   - Expect: Success message showing "1 users notified"

5. [ ] Check your DMs
   - Expect: Message from bot about registrations opening

6. [ ] Click "Register for yourself" again
   - Expect: Normal registration flow (thread created)

**If all 6 steps pass → Deployment Successful! ✅**

## Post-Deployment

### Monitor for Issues
```bash
# Watch logs for errors
sudo journalctl -u tournament-manager -f
```

Watch for:
- [ ] No database connection errors
- [ ] No import errors
- [ ] No Discord API errors
- [ ] Users successfully using registration buttons

### Extended Testing (Optional)

For thorough validation, follow [TESTING_REGISTRATION_LOCK.md](TESTING_REGISTRATION_LOCK.md):
- [ ] Test 1: Lock Registrations
- [ ] Test 2: Subscribe to Notifications
- [ ] Test 3: Unsubscribe
- [ ] Test 4: Unlock and Notify
- [ ] Test 5: Verify Unlock Works
- [ ] Test 6: Custom Lock Message
- [ ] Test 7: Multiple Subscribers
- [ ] Test 8: Re-lock (Notification Reset)

### Database Health Check
```sql
-- Check registration status
SELECT is_locked, locked_by, unlocked_by, 
       locked_at, unlocked_at, lock_message 
FROM registration_status;

-- Check subscribers count
SELECT COUNT(*) as total_subscribers,
       COUNT(*) FILTER (WHERE notified = FALSE) as pending_notifications
FROM registration_notifications;
```

- [ ] Registration status shows expected values
- [ ] Subscriber count matches Discord users who subscribed

## Rollback Procedure (If Needed)

### Quick Rollback
If you encounter issues:

```bash
# Stop bot
sudo systemctl stop tournament-manager

# Restore backup
cd /home/pi
rm -rf tournament-bot
cp -r tournament-bot-backup-YYYYMMDD tournament-bot

# Restore database (optional - preserves new tables for later)
psql -h localhost -U tournament_bot -d valorant_tournament < backup.sql

# Restart bot
cd tournament-bot
sudo systemctl start tournament-manager
```

- [ ] Backup restored
- [ ] Bot running on old version
- [ ] Issue documented for review

### Partial Rollback (Keep Database)
If code works but has minor issues:

```bash
# Just disable the lock
psql -h localhost -U tournament_bot -d valorant_tournament \
  -c "UPDATE registration_status SET is_locked = FALSE WHERE id = 1;"

# Keep tables for future fix
```

This ensures registrations work while you fix code issues.

## Success Criteria

Deployment is successful when:
- [x] ✅ All files deployed without errors
- [x] ✅ Database migration completed
- [x] ✅ Bot restarts successfully
- [x] ✅ Both new admin commands appear in Discord
- [x] ✅ Lock message shows when clicking registration buttons
- [x] ✅ Notification subscription works
- [x] ✅ Unlock command sends DMs to subscribers
- [x] ✅ Normal registration flow works when unlocked
- [x] ✅ No errors in bot logs

## Support & Documentation

If you encounter issues:

1. **Check Logs:**
   ```bash
   sudo journalctl -u tournament-manager -f
   ```

2. **Database Status:**
   ```sql
   SELECT * FROM registration_status;
   SELECT COUNT(*) FROM registration_notifications;
   ```

3. **Documentation:**
   - Feature guide: [REGISTRATION_LOCK_GUIDE.md](REGISTRATION_LOCK_GUIDE.md)
   - Testing procedures: [TESTING_REGISTRATION_LOCK.md](TESTING_REGISTRATION_LOCK.md)
   - Implementation details: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

4. **Common Issues:**
   - Lock not working? → Restart bot
   - DMs not received? → Check user privacy settings
   - Button timeout? → Click registration button again
   - Database errors? → Verify migration ran successfully

## Post-Deployment Notes

Record your deployment:

**Deployment Date:** _______________

**Deployed By:** _______________

**Migration Status:** ⬜ Success ⬜ Partial ⬜ Failed

**Notes:**
_________________________________
_________________________________
_________________________________

**Issues Encountered:**
_________________________________
_________________________________
_________________________________

**Next Steps:**
_________________________________
_________________________________
_________________________________
