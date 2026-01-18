"""Utils package for VALORANT Tournament Bot"""

import os
from discord import app_commands
import discord

# Get test role ID from environment
TEST_ROLE_ID = int(os.getenv("TEST_ROLE_ID", 0))

def has_test_role():
    """Decorator to check if user has the test role"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not TEST_ROLE_ID:
            # If no role ID is set, allow all users (fallback)
            return True
        
        # Check if user has the test role
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member and any(role.id == TEST_ROLE_ID for role in member.roles):
                return True
        
        # Send error message if user doesn't have the role
        await interaction.response.send_message(
            "❌ You don't have permission to use this bot. You need the test role.",
            ephemeral=True
        )
        return False
    
    return app_commands.check(predicate)

from .checks import commands_channel_only

__all__ = ['TEST_ROLE_ID', 'has_test_role', 'commands_channel_only']
