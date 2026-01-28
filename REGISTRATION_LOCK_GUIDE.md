# Registration Lock System

## Overview
This feature allows admins to lock and unlock all registrations (player, team, manager, coach) with a notification system for users.

## Setup

### 1. Run the Database Migration
```bash
psql -h localhost -U tournament_bot -d valorant_tournament -f database/migrations/010_registration_lock.sql
```

This creates two tables:
- `registration_status` - Stores lock/unlock state (singleton table)
- `registration_notifications` - Tracks users who want notifications

### 2. Initialize Registration Status
After running the migration, the registration status defaults to unlocked. The system is ready to use immediately.

## Admin Commands

### `/admin-lock-registrations`
Locks all registration types (player, team, manager, coach).

**Parameters:**
- `message` (optional) - Custom message shown to users when locked
  - Default: "We are not accepting registrations at the moment. We will open registrations soon. Stay tuned!"

**Example:**
```
/admin-lock-registrations message: Season 2 registrations will open on February 1st!
```

**What happens:**
- Sets `is_locked = TRUE` in database
- Records who locked it and when
- Stores the custom message (if provided)
- All registration buttons now show lock message with notification toggle

### `/admin-unlock-registrations`
Unlocks all registrations and notifies subscribers.

**What happens:**
- Sets `is_locked = FALSE` in database
- Records who unlocked it and when
- Sends DMs to all subscribed users
- Marks subscribers as "notified"
- Shows count of successful/failed notifications

## User Experience

### When Locked
When a user clicks any registration button while locked:

1. **Shows Lock Message**
   - Red embed with custom message or default
   - "🔒 Registrations Locked" title

2. **Notification Toggle Button**
   - Unsubscribed: "🔕 Get Notified When Registrations Open"
   - Subscribed: "🔔 Unsubscribe from Notifications"

3. **Subscription**
   - User clicks button to subscribe
   - Green confirmation: "✅ Subscribed to Notifications"
   - Button changes to unsubscribe option
   - User can toggle on/off anytime

### When Unlocked
When admin runs `/admin-unlock-registrations`:

1. **Subscribers Receive DM**
   ```
   🔓 Registrations Are Now Open!
   
   The tournament registrations have been unlocked.
   You can now register for the tournament!
   
   You received this notification because you subscribed to registration updates.
   ```

2. **Notifications Reset**
   - All subscribers marked as "notified"
   - If registrations lock again, users must re-subscribe
   - This prevents spam from multiple unlock events

## Database Methods

New methods added to `database/db.py`:

| Method | Description |
|--------|-------------|
| `is_registration_locked()` | Returns `True` if locked, `False` if unlocked |
| `get_registration_status()` | Returns full status dict (locked, message, who, when) |
| `lock_registrations(admin_id, message)` | Lock with optional custom message |
| `unlock_registrations(admin_id)` | Unlock and return list of subscriber IDs |
| `subscribe_registration_notification(discord_id)` | Subscribe user to notifications |
| `unsubscribe_registration_notification(discord_id)` | Unsubscribe user |
| `is_subscribed_to_notifications(discord_id)` | Check if user is subscribed |

## Implementation Details

### Registration Lock Check
All registration buttons check lock status FIRST:
1. `commands/registration.py` - Player registration
2. `commands/team_registration.py` - Team registration
3. `commands/manager_registration.py` - Manager registration
4. `commands/coach_registration.py` - Coach registration

### Notification Toggle View
- Class: `NotificationToggleView` in `commands/registration.py`
- Timeout: 5 minutes
- Dynamic button label based on subscription status
- Imported by other registration modules to maintain consistency

### Singleton Pattern
The `registration_status` table uses a CHECK constraint to ensure only one row:
```sql
CHECK (id = 1)
```
This guarantees system-wide lock state consistency.

### Performance
- Index on `registration_notifications.notified` for fast query filtering
- Single query to check lock status (cached in single row)
- Efficient notification lookup using WHERE clause on indexed column

## Testing Checklist

- [ ] Run migration successfully
- [ ] Lock registrations with custom message
- [ ] Try all 4 registration types while locked - should show lock message
- [ ] Subscribe to notifications (should change button label)
- [ ] Unsubscribe from notifications (should revert button)
- [ ] Subscribe again
- [ ] Unlock registrations as admin
- [ ] Verify DM received
- [ ] Try registration after unlock - should work normally
- [ ] Lock again
- [ ] Verify previous subscribers don't auto-get notifications (need to re-subscribe)
- [ ] Unlock with multiple subscribers - check notification count

## Troubleshooting

### Users not receiving notifications
- Check DM privacy settings (user might have DMs disabled)
- Verify bot has permission to DM users
- Check `/admin-unlock-registrations` output for failed count

### Lock not working
- Verify migration ran successfully: `SELECT * FROM registration_status;`
- Check `is_locked` column value
- Restart bot to ensure code changes loaded

### Duplicate notifications
- Each unlock event only notifies users with `notified = FALSE`
- After notification, flag is set to `TRUE`
- Users must re-subscribe if registrations lock again

## Future Enhancements

Potential improvements:
- Scheduled lock/unlock with cron jobs
- Lock specific registration types (e.g., only lock player registrations)
- Multiple notification groups (e.g., notify when specific tournaments open)
- Admin command to view subscriber count
- Analytics on lock/unlock events
