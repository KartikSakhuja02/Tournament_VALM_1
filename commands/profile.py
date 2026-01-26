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
    @app_commands.describe(user="The user whose profile to view (optional)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        """View player profile with stats"""
        await interaction.response.defer(ephemeral=True)
        
        # Use provided user or default to the command user
        target_user = user if user else interaction.user
        
        try:
            # Get player profile
            profile = await db.get_player_profile(target_user.id)
            
            if not profile:
                # Check if user is a manager of any team
                manager_teams = await db.get_user_teams_by_role(target_user.id, 'manager')
                
                if manager_teams:
                    # Show manager profile instead
                    await self.show_manager_profile(interaction, manager_teams, target_user)
                    return
                
                embed = discord.Embed(
                    title="❌ Profile Not Found",
                    description=f"{'You are' if target_user == interaction.user else f'{target_user.mention} is'} not registered as a player.",
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
                value=f"**Discord:** {target_user.mention}\n"
                      f"**Discord ID:** `{target_user.id}`",
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
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
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
    
    async def show_manager_profile(self, interaction: discord.Interaction, manager_teams: list, target_user: discord.Member):
        """Show manager profile with team information"""
        # For now, show info for the first team (we can expand to multiple teams later)
        team = manager_teams[0]
        
        # Get team members
        team_members = await db.get_team_members(team['id'])
        
        # Find captain
        captain = None
        for member in team_members:
            if member['role'] == 'captain':
                captain = member
                break
        
        # Create manager profile embed
        embed = discord.Embed(
            title=f"👔 Manager Profile",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        
        # Manager Info Section
        embed.add_field(
            name="👤 Manager Info",
            value=f"**Discord:** {target_user.mention}\n"
                  f"**Discord ID:** `{target_user.id}`\n"
                  f"**Role:** Team Manager",
            inline=False
        )
        
        # Team Info Section
        captain_display = f"<@{captain['discord_id']}>" if captain else "⚠️ *No captain yet - First invited player will become captain*"
        
        embed.add_field(
            name="🏆 Team Information",
            value=f"**Team Name:** {team['team_name']}\n"
                  f"**Team Tag:** [{team['team_tag']}]\n"
                  f"**Region:** {team['region']}\n"
                  f"**Captain:** {captain_display}\n"
                  f"**Members:** {len(team_members)}/5",
            inline=False
        )
        
        # Team Logo
        if team.get('logo_url'):
            embed.set_thumbnail(url=team['logo_url'])
        else:
            embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Footer with info note
        if not captain:
            embed.set_footer(text="💡 Tip: Invite a player to your team - they'll automatically become the captain!")
        else:
            embed.set_footer(text=f"Team created on {team['created_at'].strftime('%b %d, %Y')}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)



async def setup(bot):
    await bot.add_cog(Profile(bot))
