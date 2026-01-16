import discord
from discord.ext import commands
from discord import app_commands
import os
from pathlib import Path
from database.db import db


class ProfileCog(commands.Cog):
    """Player profile system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.imports_dir = Path(__file__).parent.parent / "imports"
    
    @app_commands.command(name="profile", description="View your player profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        """Display player profile with agent GIF"""
        # Defer the response since we might need to fetch files
        await interaction.response.defer()
        
        # Get target user (self or mentioned member)
        target_user = member if member else interaction.user
        
        # Get player data from database
        player = await db.get_player_by_discord_id(target_user.id)
        
        if not player:
            await interaction.followup.send(
                f"❌ {target_user.mention} is not registered!\n"
                "Please use the player registration first.",
                ephemeral=True
            )
            return
        
        # Check if agent GIF exists
        agent = player.get('agent')
        if agent:
            # For now, using direct Giphy URL (you can create a mapping later)
            gif_url = "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExanpna29xZXp2a29ncjAzd3Rha25sZWw4Mm4xaHN0bnkxOGd0M241bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/AGaIxp4zV38RIxsUMT/giphy.gif"
            
            # Create embed with Giphy URL
            embed = discord.Embed(color=discord.Color.red())
            embed.set_image(url=gif_url)
            
            await interaction.followup.send(embed=embed)
        else:
            # No agent set
            await interaction.followup.send(
                f"❌ {target_user.mention} has not set a main agent yet.",
                ephemeral=True
            )


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(ProfileCog(bot))
    print("✓ Loaded: commands.profile")
