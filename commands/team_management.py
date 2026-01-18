import discord
from discord.ext import commands
from discord import app_commands
import os
from database.db import db
from utils.checks import commands_channel_only


class TeamManagementCog(commands.Cog):
    """Team management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="invite", description="Invite a player to your team")
    @app_commands.describe(player="The player to invite to your team")
    @commands_channel_only()
    async def invite_player(self, interaction: discord.Interaction, player: discord.Member):
        """Invite a player to join your team"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is a captain or manager of any team
        manager_teams = await db.get_user_teams_by_role(interaction.user.id, 'manager')
        captain_teams = await db.get_user_teams_by_role(interaction.user.id, 'captain')
        
        user_teams = manager_teams + captain_teams
        
        if not user_teams:
            await interaction.followup.send(
                "❌ You must be a team captain or manager to invite players.\n"
                "Only captains and managers can send team invites.",
                ephemeral=True
            )
            return
        
        # Check if the invited player is registered
        invited_player = await db.get_player_by_discord_id(player.id)
        if not invited_player:
            await interaction.followup.send(
                f"❌ {player.mention} is not registered yet.\n"
                "Players must be registered before they can be invited to teams.",
                ephemeral=True
            )
            return
        
        # Check if player is the same as the inviter
        if player.id == interaction.user.id:
            await interaction.followup.send(
                "❌ You cannot invite yourself!",
                ephemeral=True
            )
            return
        
        # If user is part of multiple teams, let them choose which team to invite to
        if len(user_teams) > 1:
            # Show team selection dropdown
            view = TeamInviteSelectView(
                inviter_id=interaction.user.id,
                invited_player=player,
                teams=user_teams
            )
            
            await interaction.followup.send(
                "Select which team you want to invite the player to:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, send invite directly
            team = user_teams[0]
            await self.send_team_invite(interaction, player, team)
    
    async def send_team_invite(self, interaction: discord.Interaction, player: discord.Member, team: dict):
        """Send the actual team invite DM to the player"""
        # Check if player is already a member of this team
        team_members = await db.get_team_members(team['id'])
        if any(m['discord_id'] == player.id for m in team_members):
            await interaction.followup.send(
                f"❌ {player.mention} is already a member of **{team['team_name']}**!",
                ephemeral=True
            )
            return
        
        # Create invite embed for DM
        invite_embed = discord.Embed(
            title="Team Invite",
            description=(
                f"**{interaction.user.name}** has invited you to join their team!\n\n"
                f"**Team:** {team['team_name']} [{team['team_tag']}]\n"
                f"**Region:** {team['region']}\n"
                f"**Invited by:** {interaction.user.mention}\n\n"
                "Would you like to join this team?"
            ),
            color=discord.Color.blue()
        )
        
        # Create view with accept/decline buttons
        invite_view = TeamInviteResponseView(
            team_id=team['id'],
            team_name=team['team_name'],
            inviter_id=interaction.user.id,
            inviter_name=interaction.user.name,
            guild=interaction.guild
        )
        
        # Try to send DM
        try:
            dm_channel = await player.create_dm()
            await dm_channel.send(embed=invite_embed, view=invite_view)
            
            await interaction.followup.send(
                f"✅ Team invite sent to {player.mention} via DM!",
                ephemeral=True
            )
            
            print(f"✓ Sent team invite to {player.name} for team {team['team_name']}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Could not send DM to {player.mention}.\n"
                "They may have DMs disabled. Please ask them to enable DMs from server members.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error sending team invite DM: {e}")
            await interaction.followup.send(
                f"❌ Failed to send invite: {e}",
                ephemeral=True
            )


class TeamInviteSelectView(discord.ui.View):
    """View for selecting which team to invite player to"""
    
    def __init__(self, inviter_id: int, invited_player: discord.Member, teams: list):
        super().__init__(timeout=300)
        self.inviter_id = inviter_id
        self.invited_player = invited_player
        self.teams = teams
        
        # Add team selection dropdown
        self.add_item(TeamInviteSelect(inviter_id, invited_player, teams))


class TeamInviteSelect(discord.ui.Select):
    """Dropdown for team selection when inviting"""
    
    def __init__(self, inviter_id: int, invited_player: discord.Member, teams: list):
        self.inviter_id = inviter_id
        self.invited_player = invited_player
        self.teams = teams
        
        options = []
        for team in teams:
            options.append(
                discord.SelectOption(
                    label=f"{team['team_name']} [{team['team_tag']}]",
                    value=str(team['id']),
                    description=f"Region: {team['region']}"
                )
            )
        
        super().__init__(
            placeholder="Select a team...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle team selection"""
        if interaction.user.id != self.inviter_id:
            await interaction.response.send_message("This is not your invite.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        team_id = int(self.values[0])
        selected_team = None
        for team in self.teams:
            if team['id'] == team_id:
                selected_team = team
                break
        
        if selected_team:
            cog = interaction.client.get_cog("TeamManagementCog")
            if cog:
                await cog.send_team_invite(interaction, self.invited_player, selected_team)


class TeamInviteResponseView(discord.ui.View):
    """View with accept/decline buttons for team invite"""
    
    def __init__(self, team_id: int, team_name: str, inviter_id: int, inviter_name: str, guild: discord.Guild):
        super().__init__(timeout=None)  # No timeout for DM invites
        self.team_id = team_id
        self.team_name = team_name
        self.inviter_id = inviter_id
        self.inviter_name = inviter_name
        self.guild = guild
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept team invite"""
        await interaction.response.defer()
        
        try:
            # Check if player is already a member
            team_members = await db.get_team_members(self.team_id)
            if any(m['discord_id'] == interaction.user.id for m in team_members):
                await interaction.followup.send(
                    f"❌ You are already a member of **{self.team_name}**!",
                    ephemeral=True
                )
                return
            
            # Add player to team
            await db.add_team_member(
                team_id=self.team_id,
                discord_id=interaction.user.id,
                role='player'
            )
            
            # Success message
            success_embed = discord.Embed(
                title="✅ Team Invite Accepted!",
                description=(
                    f"You have successfully joined **{self.team_name}**!\n\n"
                    "Welcome to the team!"
                ),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed)
            
            # Notify the inviter
            try:
                inviter = self.guild.get_member(self.inviter_id)
                if inviter:
                    notify_embed = discord.Embed(
                        title="Team Invite Accepted",
                        description=(
                            f"{interaction.user.mention} has accepted your invite!\n"
                            f"They are now a member of **{self.team_name}**."
                        ),
                        color=discord.Color.green()
                    )
                    await inviter.send(embed=notify_embed)
            except:
                pass  # Silently fail if can't notify inviter
            
            # Log to bot logs channel
            await self.log_team_join(interaction)
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            print(f"✓ {interaction.user.name} accepted invite to team {self.team_name}")
            
        except Exception as e:
            print(f"Error accepting team invite: {e}")
            await interaction.followup.send(
                f"❌ Failed to join team: {e}",
                ephemeral=True
            )
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline team invite"""
        await interaction.response.defer()
        
        decline_embed = discord.Embed(
            title="Team Invite Declined",
            description=f"You have declined the invite to join **{self.team_name}**.",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=decline_embed)
        
        # Notify the inviter
        try:
            inviter = self.guild.get_member(self.inviter_id)
            if inviter:
                notify_embed = discord.Embed(
                    title="Team Invite Declined",
                    description=(
                        f"{interaction.user.mention} has declined your invite to join **{self.team_name}**."
                    ),
                    color=discord.Color.red()
                )
                await inviter.send(embed=notify_embed)
        except:
            pass  # Silently fail if can't notify inviter
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        print(f"✓ {interaction.user.name} declined invite to team {self.team_name}")
    
    async def log_team_join(self, interaction: discord.Interaction):
        """Log team join to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            # Get team details
            team = await db.get_team_by_id(self.team_id)
            if not team:
                return
            
            log_embed = discord.Embed(
                title="Player Joined Team (Invite)",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Player**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Invited By**\n<@{self.inviter_id}> ({self.inviter_name})\n\n"
                    f"**Team ID:** {team['id']} | **Player ID:** {interaction.user.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=0x5865F2,  # Discord blurple
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Player join logged: {interaction.user.name} to {team['team_name']}")
            
        except Exception as e:
            print(f"Error logging team join: {e}")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(TeamManagementCog(bot))
    print("✓ Team management cog loaded")
