# VALORANT Tournament Bot

Discord bot for managing regional scrim tournaments.

## Step 1 Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token

### Getting Your Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Reset Token" to get your bot token (save it securely)
5. Enable these Privileged Gateway Intents:
   - MESSAGE CONTENT INTENT
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select bot permissions: `Send Messages`, `Use Slash Commands`
9. Copy the generated URL and open it to invite the bot to your server

### Installation Steps

1. **Clone/Download the project**

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create .env file**
   - Copy `.env.example` to `.env`
   - Replace `your_bot_token_here` with your actual bot token
   ```
   DISCORD_BOT_TOKEN=your_actual_token_here
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

### Expected Output

When the bot starts successfully, you should see:
```
Bot is online
Logged in as: YourBotName (123456789)
==================================================
Synced 1 command(s)
```

### Testing

In your Discord server, type `/ping` and the bot should respond with `pong`.

## Current Features (Step 1)
- ✅ Bot connects to Discord
- ✅ Logs "Bot is online" message
- ✅ Responds to `/ping` command

## Next Steps
- Awaiting approval for Step 2
