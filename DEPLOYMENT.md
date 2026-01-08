# Raspberry Pi Deployment Guide

## Quick Answer: Running Multiple Bots

**Yes, you can run multiple Discord bots on the same Raspberry Pi!** Each bot needs:
- Its own directory (e.g., `~/valorant-tournament`, `~/other-bot`)
- Its own virtual environment
- Its own systemd service with a unique name
- Its own Discord bot token
- Unique port if using web services (not applicable for this bot)

The bots run independently and won't interfere with each other.

---

## Deployment Steps for Raspberry Pi

### 1. Prepare Environment (if not already done)

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip
```

### 2. Set up SSH for GitHub (recommended)

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "raspi-github" -f ~/.ssh/id_ed25519 -N ""

# Display public key
cat ~/.ssh/id_ed25519.pub
```

Copy the key and add it to GitHub: Settings → SSH and GPG keys → New SSH key

Test connection:
```bash
ssh -T git@github.com
```

### 3. Clone Repository

```bash
# Go to home directory
cd ~

# Clone with SSH (recommended)
git clone git@github.com/<your-username>/<your-repo>.git valorant-tournament

# OR clone with HTTPS
git clone https://github.com/<your-username>/<your-repo>.git valorant-tournament

# Enter the directory
cd valorant-tournament
```

### 4. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Edit and add your Discord bot token:
```
DISCORD_BOT_TOKEN=your_actual_token_here
```

Save (Ctrl+X, Y, Enter)

### 6. Test Run

```bash
source venv/bin/activate
python main.py
```

Expected output:
```
Bot is online
Logged in as: YourBotName (123456789)
==================================================
✓ Loaded: commands.ping
Synced 1 command(s)
```

Test `/ping` in Discord, then stop with Ctrl+C.

### 7. Install Systemd Service (24/7 Auto-Start)

The repository includes a service file. First, check your username and home directory:

```bash
whoami
pwd
```

If your username is NOT `kartiksakhuja02`, edit the service file:
```bash
nano tournament-manager.service
# Change User= and WorkingDirectory= paths to match your username
```

Then install it:
```bash
sudo cp tournament-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tournament-manager
sudo systemctl start tournament-manager
```

### 8. Manage the Service

```bash
# Check status
systemctl status tournament-manager

# View live logs
journalctl -u tournament-manager -f

# Stop the bot
sudo systemctl stop tournament-manager

# Restart the bot
sudo systemctl restart tournament-manager

# Disable auto-start
sudo systemctl disable tournament-manager
```

### 9. Update Bot from GitHub

When you push changes from your development machine:

```bash
cd ~/valorant-tournament
git pull
sudo systemctl restart tournament-manager
```

For safety, check logs after restart:
```bash
journalctl -u tournament-manager -f
```

---

## Troubleshooting

### Bot won't start
```bash
# Check service status
systemctl status tournament-manager

# View detailed logs
journalctl -u tournament-manager -n 50 --no-pager
```

### Command sync issues
- Wait 1-2 minutes after bot starts
- Commands may take time to appear in Discord
- Try kicking and re-inviting the bot

### Permission errors
- Ensure `.env` is readable: `chmod 600 .env`
- Verify service runs as correct user in service file

### Python/venv issues
```bash
# Recreate venv if needed
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Service Names on Same Pi

This bot uses: `tournament-manager.service`

If you have other bots, give them unique names:
- `tournament-manager.service` (this one)
- `valorant-bot.service` (your existing one)
- `other-bot.service`
- etc.

Each runs independently with no conflicts.
