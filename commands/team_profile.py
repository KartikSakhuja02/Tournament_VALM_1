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
    @app_commands.describe(
        user="View this user's team profile",
        team_name="View team by name"
    )
    async def team_profile(
        self, 
        interaction: discord.Interaction, 
        user: discord.User = None,
        team_name: str = None
    ):
        """View team profile with stats"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            team_data = None
            
            # Determine which team to show
            if team_name:
                # Search by team name
                team_data = await db.get_team_by_name(team_name)
                if not team_data:
                    embed = discord.Embed(
                        title="❌ Team Not Found",
                        description=f"No team found with the name `{team_name}`.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            elif user:
                # Get the mentioned user's team (any role)
                target_id = user.id
                # Check all roles to find their team
                for role in ['captain', 'player', 'manager', 'coach']:
                    teams = await db.get_user_teams_by_role(target_id, role)
                    if teams:
                        team_data = teams[0]  # Get first team
                        break
                
                if not team_data:
                    embed = discord.Embed(
                        title="❌ No Team Found",
                        description=f"{user.mention} is not part of any team.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            else:
                # No arguments provided - show user's own team
                target_id = interaction.user.id
                # Check all roles to find their team
                for role in ['captain', 'player', 'manager', 'coach']:
                    teams = await db.get_user_teams_by_role(target_id, role)
                    if teams:
                        team_data = teams[0]  # Get first team
                        break
                
                if not team_data:
                    embed = discord.Embed(
                        title="❌ No Team Found",
                        description="You are not part of any team. Join or create a team first!",
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
            
            # Leadership Section (Managers and Coach only)
            leadership_text = ""
            
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
            
            # Roster Section (including Captain)
            roster_list = []
            
            # Add captain first with (Captain) suffix
            if profile['captain']:
                captain_ign = profile['captain']['ign'] if profile['captain']['ign'] else "N/A"
                roster_list.append({
                    'discord_id': profile['captain']['discord_id'],
                    'ign': captain_ign,
                    'is_captain': True
                })
            
            # Add other players
            for player in profile['players']:
                # Skip if this player is also the captain (shouldn't happen but just in case)
                if profile['captain'] and player['discord_id'] == profile['captain']['discord_id']:
                    continue
                roster_list.append({
                    'discord_id': player['discord_id'],
                    'ign': player['ign'] if player['ign'] else "N/A",
                    'is_captain': False
                })
            
            if roster_list:
                roster_text = f"**Total Players:** {len(roster_list)}\n\n"
                for idx, player in enumerate(roster_list, 1):
                    ign = player['ign']
                    captain_suffix = " (Captain)" if player['is_captain'] else ""
                    roster_text += f"`{idx}.` **{ign}**{captain_suffix}\n"
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
