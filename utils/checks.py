import discord
from discord.ext import commands
from discord import app_commands
import os


def commands_channel_only():
    """Decorator to restrict commands to a specific channel"""
    async def predicate(interaction: discord.Interaction) -> bool:
        commands_channel_id = os.getenv("COMMANDS_CHANNEL_ID")
        
        # If not configured, allow everywhere
        if not commands_channel_id:
            return True
        
        # Check if command is used in the designated channel
        if interaction.channel_id != int(commands_channel_id):
            commands_channel = interaction.guild.get_channel(int(commands_channel_id))
            channel_mention = commands_channel.mention if commands_channel else f"<#{commands_channel_id}>"
            
            await interaction.response.send_message(
                f"❌ Commands can only be used in {channel_mention}",
                ephemeral=True
            )
            return False
        
        return True
    
    return app_commands.check(predicate)
