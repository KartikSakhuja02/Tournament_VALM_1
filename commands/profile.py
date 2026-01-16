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
            gif_path = self.imports_dir / f"{agent.lower()}.gif"
            
            if gif_path.exists():
                # Send GIF with embed to make it display larger
                gif_file = discord.File(gif_path, filename=f"{agent.lower()}.gif")
                
                # Create minimal embed to display image larger
                embed = discord.Embed(color=discord.Color.red())
                embed.set_image(url=f"attachment://{agent.lower()}.gif")
                
                await interaction.followup.send(embed=embed, file=gif_file)
            else:
                # GIF not found
                await interaction.followup.send(
                    f"❌ Profile GIF not found for agent: **{agent}**\n"
                    f"Expected file: `{gif_path.name}`",
                    ephemeral=True
                )
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
