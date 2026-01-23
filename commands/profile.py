"""
Profile commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from database.db import db


class Profile(commands.Cog):
    """Profile command cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="profile", description="View your player profile")
    async def profile(self, interaction: discord.Interaction):
        """View player profile with stats"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get player profile
            profile = await db.get_player_profile(interaction.user.id)
            
            if not profile:
                embed = discord.Embed(
                    title="❌ Profile Not Found",
                    description="You are not registered as a player. Use `/register` to register.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Calculate KDR
            if profile['deaths'] > 0:
                kdr = round(profile['kills'] / profile['deaths'], 2)
            else:
                kdr = profile['kills']  # If no deaths, KDR = kills
            
            # Calculate Winrate
            if profile['matches_played'] > 0:
                winrate = round((profile['wins'] / profile['matches_played']) * 100, 1)
            else:
                winrate = 0.0
            
            # Create profile embed
            embed = discord.Embed(
                title=f"📊 Player Profile",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # Player Info Section
            embed.add_field(
                name="👤 Player Info",
                value=f"**Discord:** {interaction.user.mention}\n"
                      f"**Discord ID:** `{interaction.user.id}`",
                inline=False
            )
            
            # Game Info Section
            embed.add_field(
                name="🎮 Game Info",
                value=f"**IGN:** `{profile['ign']}`\n"
                      f"**Rank:** `-`\n"
                      f"**Points:** `{profile['points']}`\n"
                      f"**MVP:** `{profile['mvps']}`\n"
                      f"**Region:** `{profile['region']}`",
                inline=False
            )
            
            # Stats Section
            embed.add_field(
                name="📈 Stats",
                value=f"**Kills:** `{profile['kills']}`\n"
                      f"**KDR:** `{kdr}`\n"
                      f"**Deaths:** `{profile['deaths']}`\n"
                      f"**Winrate:** `{winrate}%`\n"
                      f"**Matches:** `{profile['matches_played']}`",
                inline=False
            )
            
            # Set thumbnail to user avatar
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Footer
            embed.set_footer(text=f"Registered on {profile['registered_at'].strftime('%b %d, %Y')}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in profile command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching your profile. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Profile(bot))
