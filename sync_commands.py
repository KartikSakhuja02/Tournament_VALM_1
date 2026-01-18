"""
Command Sync Utility

This script helps with syncing slash commands to Discord.
Run this when you add new commands or they're not appearing.

Usage:
    python sync_commands.py          # Sync globally (takes up to 1 hour)
    python sync_commands.py <guild_id>  # Sync to specific guild (instant)
"""

import asyncio
import discord
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    try:
        # Check if guild ID was provided
        if len(sys.argv) > 1:
            guild_id = int(sys.argv[1])
            guild = discord.Object(id=guild_id)
            
            # Sync to specific guild (instant)
            print(f"Syncing commands to guild {guild_id}...")
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to guild {guild_id}")
            print("Commands should appear instantly in that server!")
        else:
            # Sync globally (takes up to 1 hour)
            print("Syncing commands globally...")
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} commands globally")
            print("⏳ Commands will appear globally within 1 hour")
        
        print("\nSynced commands:")
        for cmd in synced:
            print(f"  - /{cmd.name}: {cmd.description}")
        
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    await bot.close()

async def main():
    try:
        # Load cogs to register commands
        await bot.load_extension("commands.team_management")
        print("✓ Loaded team_management cog")
    except Exception as e:
        print(f"✗ Failed to load cog: {e}")
    
    # Start bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    print("=" * 50)
    print("Discord Slash Command Sync Utility")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        print(f"Mode: Guild-specific sync (Guild ID: {sys.argv[1]})")
        print("This will sync instantly to that guild only\n")
    else:
        print("Mode: Global sync")
        print("This will take up to 1 hour to propagate\n")
        print("Tip: For instant sync, run: python sync_commands.py <your_guild_id>\n")
    
    asyncio.run(main())
