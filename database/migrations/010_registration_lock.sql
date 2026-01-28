-- Migration 010: Add registration lock and notification system

-- Create table for registration lock status
CREATE TABLE IF NOT EXISTS registration_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    is_locked BOOLEAN DEFAULT FALSE,
    locked_at TIMESTAMP,
    locked_by BIGINT,
    unlocked_at TIMESTAMP,
    unlocked_by BIGINT,
    lock_message TEXT DEFAULT 'Registrations are currently closed. We will open them soon!',
    CHECK (id = 1) -- Only one row allowed
);

-- Insert default unlocked state
INSERT INTO registration_status (id, is_locked)
VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;

-- Create table for notification subscriptions
CREATE TABLE IF NOT EXISTS registration_notifications (
    discord_id BIGINT PRIMARY KEY,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_registration_notifications_subscribed 
ON registration_notifications(discord_id) 
WHERE notified = FALSE;
