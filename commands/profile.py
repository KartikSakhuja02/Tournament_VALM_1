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
        """Display player profile with agent video"""
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
        
        # Get player stats
        stats = await db.get_player_stats(target_user.id)
        
        # Create profile embed
        embed = discord.Embed(
            title=f"Player Profile: {player['ign']}",
            description=f"**Region:** {player['region']}",
            color=discord.Color.red()
        )
        
        # Add basic info
        embed.add_field(name="Discord", value=target_user.mention, inline=True)
        embed.add_field(name="Player ID", value=f"`{player['player_id']}`", inline=True)
        embed.add_field(name="Main Agent", value=player.get('agent', 'Not Set'), inline=True)
        
        # Add stats if available
        if stats:
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            matches_played = stats.get('matches_played', 0)
            
            # Calculate win rate
            win_rate = (wins / matches_played * 100) if matches_played > 0 else 0.0
            
            embed.add_field(
                name="Statistics",
                value=(
                    f"**Matches Played:** {matches_played}\n"
                    f"**Wins:** {wins}\n"
                    f"**Losses:** {losses}\n"
                    f"**Win Rate:** {win_rate:.1f}%"
                ),
                inline=False
            )
        
        # Add tournament notifications status
        notif_status = "✅ Enabled" if player.get('tournament_notifications', False) else "❌ Disabled"
        embed.add_field(name="Tournament Notifications", value=notif_status, inline=False)
        
        # Set user avatar as thumbnail
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Add timestamp
        embed.timestamp = player.get('created_at')
        embed.set_footer(text=f"Registered on")
        
        # Check if agent video exists
        agent = player.get('agent')
        if agent:
            video_path = self.imports_dir / f"{agent.lower()}.mp4"
            
            if video_path.exists():
                # Send embed with video
                video_file = discord.File(video_path, filename=f"{agent.lower()}.mp4")
                await interaction.followup.send(embed=embed, file=video_file)
            else:
                # Video not found, just send embed
                await interaction.followup.send(
                    content=f"⚠️ Agent video not found: `{video_path.name}`",
                    embed=embed
                )
        else:
            # No agent set, just send embed
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(ProfileCog(bot))
    print("✓ Loaded: commands.profile")
