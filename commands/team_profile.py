"""
Team profile commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from database.db import db
import os


class TeamProfile(commands.Cog):
    """Team profile command cog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="team-profile", description="View a team's profile")
    @app_commands.describe(team_name="The name of the team to view")
    async def team_profile(self, interaction: discord.Interaction, team_name: str):
        """View team profile with stats"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get team by name
            team_data = await db.get_team_by_name(team_name)
            
            if not team_data:
                embed = discord.Embed(
                    title="❌ Team Not Found",
                    description=f"No team found with the name `{team_name}`.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get full team profile
            profile = await db.get_team_profile(team_data['id'])
            
            if not profile:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to load team profile.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Calculate win rate
            if profile['matches_played'] > 0:
                winrate = round((profile['wins'] / profile['matches_played']) * 100, 1)
            else:
                winrate = 0.0
            
            # Create team profile embed
            embed = discord.Embed(
                title=f"🏆 {profile['team_name']}",
                description=f"**[{profile['team_tag']}]** • {profile['region']}",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            
            # Set team logo if available
            if profile['logo_url']:
                # Check if it's a local file path
                if os.path.exists(profile['logo_url']):
                    # For local files, we can't attach them to embeds directly
                    # We would need to upload them somewhere or use attachments
                    pass
                else:
                    # If it's a URL, use it directly
                    embed.set_thumbnail(url=profile['logo_url'])
            
            # Leadership Section
            leadership_text = ""
            
            # Captain
            if profile['captain']:
                captain_user = self.bot.get_user(profile['captain']['discord_id'])
                captain_name = captain_user.mention if captain_user else f"<@{profile['captain']['discord_id']}>"
                leadership_text += f"**Captain:** {captain_name}\n"
            
            # Managers
            if profile['managers']:
                manager_mentions = []
                for manager in profile['managers']:
                    manager_user = self.bot.get_user(manager['discord_id'])
                    manager_mention = manager_user.mention if manager_user else f"<@{manager['discord_id']}>"
                    manager_mentions.append(manager_mention)
                leadership_text += f"**Manager{'s' if len(manager_mentions) > 1 else ''}:** {', '.join(manager_mentions)}\n"
            
            # Coach
            if profile['coach']:
                coach_user = self.bot.get_user(profile['coach']['discord_id'])
                coach_name = coach_user.mention if coach_user else f"<@{profile['coach']['discord_id']}>"
                leadership_text += f"**Coach:** {coach_name}\n"
            
            if leadership_text:
                embed.add_field(
                    name="👥 Leadership",
                    value=leadership_text,
                    inline=False
                )
            
            # Roster Section
            if profile['players']:
                roster_text = f"**Total Players:** {len(profile['players'])}\n\n"
                for idx, player in enumerate(profile['players'], 1):
                    player_user = self.bot.get_user(player['discord_id'])
                    player_name = player_user.name if player_user else f"User#{player['discord_id']}"
                    ign = player['ign'] if player['ign'] else "N/A"
                    roster_text += f"`{idx}.` **{player_name}** • `{ign}`\n"
            else:
                roster_text = "*No players registered yet*"
            
            embed.add_field(
                name="🎮 Roster",
                value=roster_text,
                inline=False
            )
            
            # Team Stats Section
            stats_text = (
                f"**Wins:** `{profile['wins']}`\n"
                f"**Losses:** `{profile['losses']}`\n"
                f"**Total Matches:** `{profile['matches_played']}`\n"
                f"**Win Rate:** `{winrate}%`"
            )
            
            embed.add_field(
                name="📊 Team Stats",
                value=stats_text,
                inline=False
            )
            
            # Footer
            embed.set_footer(text=f"Team created on {profile['created_at'].strftime('%b %d, %Y')}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in team-profile command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching the team profile. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TeamProfile(bot))
