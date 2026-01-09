import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables FIRST before importing utils
load_dotenv()

# Now import utils after env vars are loaded
from utils import TEST_ROLE_ID

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to check member roles
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_commands():
    """Load all command modules"""
    commands_to_load = [
        "commands.ping",
        "commands.registration"
    ]
    
    for command in commands_to_load:
        try:
            await bot.load_extension(command)
            print(f"✓ Loaded: {command}")
        except Exception as e:
            print(f"✗ Failed to load {command}: {e}")

@bot.event
async def on_ready():
    """Event triggered when bot successfully connects to Discord"""
    print(f"Bot is online")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print("=" * 50)
    
    # Load commands
    await load_commands()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Send registration message on startup (if channel ID is configured)
    registration_channel_id = os.getenv("REGISTRATION_CHANNEL_ID")
    if registration_channel_id:
        try:
            channel_id = int(registration_channel_id)
            registration_cog = bot.get_cog("RegistrationCog")
            if registration_cog:
                await registration_cog.send_registration_message(channel_id)
        except ValueError:
            print("❌ Invalid REGISTRATION_CHANNEL_ID in .env file")
        except Exception as e:
            print(f"❌ Error sending registration message: {e}")
    else:
        print("⚠️  REGISTRATION_CHANNEL_ID not set - skipping registration message")

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
        exit(1)
    
    if TEST_ROLE_ID:
        print(f"Role-based access control enabled (Role ID: {TEST_ROLE_ID})")
    else:
        print("WARNING: TEST_ROLE_ID not set. All users can use the bot!")
    
    bot.run(TOKEN)
