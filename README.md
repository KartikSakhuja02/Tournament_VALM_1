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
   - SERVER MEMBERS INTENT (required for role checking)
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select bot permissions: `Send Messages`, `Use Slash Commands`
9. Copy the generated URL and open it to invite the bot to your server

### Getting Your Test Role ID

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Enable "Developer Mode"
2. Right-click on the role in your server settings
3. Click "Copy ID"
4. Use this ID in your `.env` file

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
   - Replace `your_test_role_id_here` with your test role ID
   ```
   DISCORD_BOT_TOKEN=your_actual_token_here
   TEST_ROLE_ID=your_test_role_id_here
   ```
   - **Important:** Only users with this role will be able to use the bot commands!

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
