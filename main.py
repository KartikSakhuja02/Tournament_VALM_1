import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables FIRST before ANY imports that need them
load_dotenv()

# Now import modules that depend on environment variables
from utils import TEST_ROLE_ID
from database.db import db
from utils.thread_manager import on_presence_update as handle_presence_update

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to check member roles
intents.presences = True  # Required for checking online status
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_commands():
    """Load all command modules"""
    commands_to_load = [
        "commands.ping",
        "commands.registration",
        "commands.team_registration",
        "commands.manager_registration",
        "commands.coach_registration",
        "commands.team_management",
        "commands.admin",
        "commands.profile",
        "commands.team_profile",
        "commands.announce"
    ]
    
    for command in commands_to_load:
        try:
            await bot.load_extension(command)
            print(f"✓ Loaded: {command}")
        except Exception as e:
            print(f"✗ Failed to load {command}: {e}")

@bot.event
async def setup_hook():
    """Setup hook - runs before bot connects to Discord"""
    print("⚙️  Starting bot setup...")
    
    # Connect to database first
    try:
        await db.connect()
        print("✓ Database connected")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Bot will continue without database functionality")
    
    # Load command extensions
    await load_commands()
    
    # Sync slash commands to guild ONLY (faster updates, no command limit)
    try:
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)
            print(f"✓ Synced {len(synced)} command(s) to guild {guild_id}")
        else:
            print("⚠️  GUILD_ID not set - commands will not sync automatically")
            print("   Add GUILD_ID to .env and restart, or use /sync command")
    except Exception as e:
        print(f"✗ Failed to sync commands: {e}")
    
    print("✅ Bot setup complete!")

@bot.event
async def on_ready():
    """Event triggered when bot successfully connects to Discord"""
    print(f"🟢 Bot is online")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print("=" * 50)
    
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
    
    # Send team registration message on startup (if channel ID is configured)
    team_registration_channel_id = os.getenv("TEAM_REGISTRATION_CHANNEL_ID")
    if team_registration_channel_id:
        try:
            channel_id = int(team_registration_channel_id)
            team_registration_cog = bot.get_cog("TeamRegistrationCog")
            if team_registration_cog:
                await team_registration_cog.send_team_registration_message(channel_id)
        except ValueError:
            print("❌ Invalid TEAM_REGISTRATION_CHANNEL_ID in .env file")
        except Exception as e:
            print(f"❌ Error sending team registration message: {e}")
    else:
        print("⚠️  TEAM_REGISTRATION_CHANNEL_ID not set - skipping team registration message")
    
    # Send manager registration message on startup (if channel ID is configured)
    manager_registration_channel_id = os.getenv("MANAGER_REGISTRATION_CHANNEL_ID")
    if manager_registration_channel_id:
        try:
            channel_id = int(manager_registration_channel_id)
            manager_registration_cog = bot.get_cog("ManagerRegistrationCog")
            if manager_registration_cog:
                await manager_registration_cog.send_manager_registration_message(channel_id)
        except ValueError:
            print("❌ Invalid MANAGER_REGISTRATION_CHANNEL_ID in .env file")
        except Exception as e:
            print(f"❌ Error sending manager registration message: {e}")
    else:
        print("⚠️  MANAGER_REGISTRATION_CHANNEL_ID not set - skipping manager registration message")
    
    # Send coach registration message on startup (if channel ID is configured)
    coach_registration_channel_id = os.getenv("COACH_REGISTRATION_CHANNEL_ID")
    if coach_registration_channel_id:
        try:
            channel_id = int(coach_registration_channel_id)
            coach_registration_cog = bot.get_cog("CoachRegistrationCog")
            if coach_registration_cog:
                await coach_registration_cog.send_registration_message(channel_id)
        except ValueError:
            print("❌ Invalid COACH_REGISTRATION_CHANNEL_ID in .env file")
        except Exception as e:
            print(f"❌ Error sending coach registration message: {e}")
    else:
        print("⚠️  COACH_REGISTRATION_CHANNEL_ID not set - skipping coach registration message")

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    """Handle presence updates - used for adding HeadMods to waiting threads"""
    await handle_presence_update(before, after)

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
    
    try:
        bot.run(TOKEN)
    finally:
        # Close database connection on shutdown
        asyncio.run(db.close())
