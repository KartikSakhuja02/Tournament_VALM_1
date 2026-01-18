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
    
    @app_commands.command(name="leave", description="Leave one of your teams")
    @commands_channel_only()
    async def leave_team(self, interaction: discord.Interaction):
        """Leave a team you're part of"""
        await interaction.response.defer(ephemeral=True)
        
        # Get all teams the user is part of (any role)
        all_teams = []
        for role in ['captain', 'manager', 'player', 'coach']:
            teams = await db.get_user_teams_by_role(interaction.user.id, role)
            for team in teams:
                # Add role info to team dict
                team['user_role'] = role
                # Avoid duplicates if user has multiple roles
                if not any(t['id'] == team['id'] for t in all_teams):
                    all_teams.append(team)
        
        if not all_teams:
            await interaction.followup.send(
                "❌ You are not part of any team!",
                ephemeral=True
            )
            return
        
        # If user is part of multiple teams, let them choose which to leave
        if len(all_teams) > 1:
            view = TeamLeaveSelectView(
                user_id=interaction.user.id,
                teams=all_teams,
                guild=interaction.guild
            )
            await interaction.followup.send(
                "Select which team you want to leave:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, send leave confirmation directly
            team = all_teams[0]
            await self.send_leave_confirmation(interaction, team)
    
    async def send_leave_confirmation(self, interaction: discord.Interaction, team: dict):
        """Send leave confirmation DM to the user"""
        leave_embed = discord.Embed(
            title="Leave Team Confirmation",
            description=(
                f"Are you sure you want to leave this team?\n\n"
                f"**Team:** {team['team_name']} [{team['team_tag']}]\n"
                f"**Region:** {team['region']}\n"
                f"**Your Role:** {team['user_role'].title()}\n\n"
                f"⚠️ This action cannot be undone. You will need to be re-invited to join again."
            ),
            color=discord.Color.orange()
        )
        
        view = TeamLeaveConfirmView(
            team_id=team['id'],
            team_name=team['team_name'],
            user_role=team['user_role'],
            guild=interaction.guild
        )
        
        try:
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send(embed=leave_embed, view=view)
            
            await interaction.followup.send(
                "✅ Leave confirmation sent to your DMs!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Could not send DM. Please enable DMs from server members.",
                ephemeral=True
            )
    
    @app_commands.command(name="kick", description="Kick a player from your team")
    @app_commands.describe(player="The player to kick from your team")
    @commands_channel_only()
    async def kick_player(self, interaction: discord.Interaction, player: discord.Member):
        """Kick a player from your team"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is a captain or manager
        manager_teams = await db.get_user_teams_by_role(interaction.user.id, 'manager')
        captain_teams = await db.get_user_teams_by_role(interaction.user.id, 'captain')
        user_teams = manager_teams + captain_teams
        
        if not user_teams:
            await interaction.followup.send(
                "❌ You must be a team captain or manager to kick players!",
                ephemeral=True
            )
            return
        
        # Cannot kick yourself
        if player.id == interaction.user.id:
            await interaction.followup.send(
                "❌ You cannot kick yourself! Use `/leave` instead.",
                ephemeral=True
            )
            return
        
        # Get all teams the target player is part of
        player_teams = []
        for role in ['captain', 'manager', 'player', 'coach']:
            teams = await db.get_user_teams_by_role(player.id, role)
            for team in teams:
                team['player_role'] = role
                if not any(t['id'] == team['id'] for t in player_teams):
                    player_teams.append(team)
        
        if not player_teams:
            await interaction.followup.send(
                f"❌ {player.mention} is not part of any team!",
                ephemeral=True
            )
            return
        
        # Find teams where kicker is captain/manager AND target player is member
        kickable_teams = []
        for team in player_teams:
            if any(t['id'] == team['id'] for t in user_teams):
                kickable_teams.append(team)
        
        if not kickable_teams:
            await interaction.followup.send(
                f"❌ {player.mention} is not in any of your teams!",
                ephemeral=True
            )
            return
        
        # Cannot kick captains
        for team in kickable_teams:
            if team['player_role'] == 'captain':
                await interaction.followup.send(
                    f"❌ You cannot kick the team captain! Captain: {player.mention}",
                    ephemeral=True
                )
                return
        
        # If multiple teams, let them choose
        if len(kickable_teams) > 1:
            view = TeamKickSelectView(
                kicker_id=interaction.user.id,
                kicker_name=interaction.user.name,
                target_player=player,
                teams=kickable_teams,
                guild=interaction.guild
            )
            await interaction.followup.send(
                f"Select which team to kick {player.mention} from:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, kick directly
            team = kickable_teams[0]
            await self.execute_kick(interaction, player, team)
    
    async def execute_kick(self, interaction: discord.Interaction, player: discord.Member, team: dict):
        """Execute the kick action"""
        try:
            # Remove player from team
            await db.remove_team_member(team['id'], player.id)
            
            # Notify the kicker
            await interaction.followup.send(
                f"✅ {player.mention} has been kicked from **{team['team_name']}**!",
                ephemeral=True
            )
            
            # Notify the kicked player
            try:
                kick_embed = discord.Embed(
                    title="Kicked from Team",
                    description=(
                        f"You have been removed from **{team['team_name']}** [{team['team_tag']}].\n\n"
                        f"**Removed by:** {interaction.user.mention}\n"
                        f"**Team Region:** {team['region']}"
                    ),
                    color=discord.Color.red()
                )
                dm_channel = await player.create_dm()
                await dm_channel.send(embed=kick_embed)
            except:
                pass  # Silently fail if can't DM
            
            # Log to bot logs channel
            await self.log_kick(interaction, player, team)
            
            print(f"✓ {player.name} kicked from team {team['team_name']} by {interaction.user.name}")
            
        except Exception as e:
            print(f"Error kicking player: {e}")
            await interaction.followup.send(
                f"❌ Failed to kick player: {e}",
                ephemeral=True
            )
    
    async def log_kick(self, interaction: discord.Interaction, player: discord.Member, team: dict):
        """Log kick to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="Player Kicked from Team",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Kicked Player**\n{player.mention} ({player.name})\n\n"
                    f"**Kicked By**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Team ID:** {team['id']} | **Player ID:** {player.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=discord.Color.red(),
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Kick logged to bot logs")
            
        except Exception as e:
            print(f"Error logging kick: {e}")
    
    @app_commands.command(name="disband", description="Disband your team")
    @commands_channel_only()
    async def disband_team(self, interaction: discord.Interaction):
        """Disband a team (captain or manager only)"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is a captain or manager
        manager_teams = await db.get_user_teams_by_role(interaction.user.id, 'manager')
        captain_teams = await db.get_user_teams_by_role(interaction.user.id, 'captain')
        user_teams = manager_teams + captain_teams
        
        if not user_teams:
            await interaction.followup.send(
                "❌ You must be a team captain or manager to disband teams!",
                ephemeral=True
            )
            return
        
        # If multiple teams, let them choose which to disband
        if len(user_teams) > 1:
            view = TeamDisbandSelectView(
                user_id=interaction.user.id,
                user_name=interaction.user.name,
                teams=user_teams,
                guild=interaction.guild
            )
            await interaction.followup.send(
                "⚠️ Select which team to disband:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, show disband confirmation
            team = user_teams[0]
            await self.show_disband_confirmation(interaction, team)
    
    async def show_disband_confirmation(self, interaction: discord.Interaction, team: dict):
        """Show disband confirmation"""
        # Get team members
        team_members = await db.get_team_members(team['id'])
        member_count = len(team_members)
        
        confirm_embed = discord.Embed(
            title="⚠️ Disband Team Confirmation",
            description=(
                f"Are you sure you want to disband **{team['team_name']}**?\n\n"
                f"**Team Tag:** {team['team_tag']}\n"
                f"**Region:** {team['region']}\n"
                f"**Members:** {member_count}\n\n"
                f"⚠️ **This action is PERMANENT and cannot be undone!**\n"
                f"• All team data will be deleted\n"
                f"• All members will be removed\n"
                f"• All members will be notified via DM"
            ),
            color=discord.Color.dark_red()
        )
        
        view = TeamDisbandConfirmView(
            team_id=team['id'],
            team_name=team['team_name'],
            team_tag=team['team_tag'],
            disbander_id=interaction.user.id,
            disbander_name=interaction.user.name,
            guild=interaction.guild
        )
        
        await interaction.followup.send(
            embed=confirm_embed,
            view=view,
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


class TeamLeaveSelectView(discord.ui.View):
    """View for selecting which team to leave"""
    
    def __init__(self, user_id: int, teams: list, guild: discord.Guild):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.teams = teams
        self.guild = guild
        self.add_item(TeamLeaveSelect(user_id, teams, guild))


class TeamLeaveSelect(discord.ui.Select):
    """Dropdown for team selection when leaving"""
    
    def __init__(self, user_id: int, teams: list, guild: discord.Guild):
        self.user_id = user_id
        self.teams = teams
        self.guild = guild
        
        options = []
        for team in teams:
            options.append(
                discord.SelectOption(
                    label=f"{team['team_name']} [{team['team_tag']}]",
                    value=str(team['id']),
                    description=f"Role: {team['user_role'].title()} | Region: {team['region']}"
                )
            )
        
        super().__init__(
            placeholder="Select a team to leave...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your selection.", ephemeral=True)
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
                await cog.send_leave_confirmation(interaction, selected_team)


class TeamLeaveConfirmView(discord.ui.View):
    """View with confirm/cancel buttons for leaving team"""
    
    def __init__(self, team_id: int, team_name: str, user_role: str, guild: discord.Guild):
        super().__init__(timeout=None)
        self.team_id = team_id
        self.team_name = team_name
        self.user_role = user_role
        self.guild = guild
    
    @discord.ui.button(label="Confirm Leave", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Get team details before removing
            team = await db.get_team_by_id(self.team_id)
            
            # Get all captains and managers to notify
            captains = await db.get_user_teams_by_role(team['captain_discord_id'], 'captain')
            managers = await db.get_team_members(self.team_id)
            
            # Collect captain/manager IDs
            leadership_ids = [team['captain_discord_id']]
            for member in managers:
                if member['role'] in ['manager'] and member['discord_id'] not in leadership_ids:
                    leadership_ids.append(member['discord_id'])
            
            # Remove user from team
            await db.remove_team_member(self.team_id, interaction.user.id)
            
            success_embed = discord.Embed(
                title="✅ Left Team",
                description=f"You have successfully left **{self.team_name}**.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed)
            
            # Notify all captains and managers
            for leader_id in leadership_ids:
                if leader_id == interaction.user.id:
                    continue  # Don't notify if they're leaving their own team as captain/manager
                
                try:
                    leader = self.guild.get_member(leader_id)
                    if leader:
                        notify_embed = discord.Embed(
                            title="Team Member Left",
                            description=(
                                f"{interaction.user.mention} has left **{self.team_name}** [{team['team_tag']}].\n\n"
                                f"**Previous Role:** {self.user_role.title()}"
                            ),
                            color=discord.Color.orange()
                        )
                        await leader.send(embed=notify_embed)
                except:
                    pass  # Silently fail if can't DM
            
            # Log to bot logs
            await self.log_leave(interaction)
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            print(f"✓ {interaction.user.name} left team {self.team_name}")
            
        except Exception as e:
            print(f"Error leaving team: {e}")
            await interaction.followup.send(f"❌ Failed to leave team: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        cancel_embed = discord.Embed(
            title="Leave Cancelled",
            description=f"You have not left **{self.team_name}**.",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=cancel_embed)
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
    
    async def log_leave(self, interaction: discord.Interaction):
        """Log team leave to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            team = await db.get_team_by_id(self.team_id)
            if not team:
                return
            
            log_embed = discord.Embed(
                title="Player Left Team",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Player**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Previous Role:** {self.user_role.title()}\n\n"
                    f"**Team ID:** {team['id']} | **Player ID:** {interaction.user.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=discord.Color.orange(),
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Leave logged to bot logs")
            
        except Exception as e:
            print(f"Error logging leave: {e}")


class TeamKickSelectView(discord.ui.View):
    """View for selecting which team to kick player from"""
    
    def __init__(self, kicker_id: int, kicker_name: str, target_player: discord.Member, teams: list, guild: discord.Guild):
        super().__init__(timeout=300)
        self.kicker_id = kicker_id
        self.kicker_name = kicker_name
        self.target_player = target_player
        self.teams = teams
        self.guild = guild
        self.add_item(TeamKickSelect(kicker_id, kicker_name, target_player, teams, guild))


class TeamKickSelect(discord.ui.Select):
    """Dropdown for team selection when kicking"""
    
    def __init__(self, kicker_id: int, kicker_name: str, target_player: discord.Member, teams: list, guild: discord.Guild):
        self.kicker_id = kicker_id
        self.kicker_name = kicker_name
        self.target_player = target_player
        self.teams = teams
        self.guild = guild
        
        options = []
        for team in teams:
            options.append(
                discord.SelectOption(
                    label=f"{team['team_name']} [{team['team_tag']}]",
                    value=str(team['id']),
                    description=f"Player's Role: {team['player_role'].title()}"
                )
            )
        
        super().__init__(
            placeholder="Select team to kick from...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.kicker_id:
            await interaction.response.send_message("This is not your action.", ephemeral=True)
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
                await cog.execute_kick(interaction, self.target_player, selected_team)


class TeamDisbandSelectView(discord.ui.View):
    """View for selecting which team to disband"""
    
    def __init__(self, user_id: int, user_name: str, teams: list, guild: discord.Guild):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_name = user_name
        self.teams = teams
        self.guild = guild
        self.add_item(TeamDisbandSelect(user_id, user_name, teams, guild))


class TeamDisbandSelect(discord.ui.Select):
    """Dropdown for team selection when disbanding"""
    
    def __init__(self, user_id: int, user_name: str, teams: list, guild: discord.Guild):
        self.user_id = user_id
        self.user_name = user_name
        self.teams = teams
        self.guild = guild
        
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
            placeholder="⚠️ Select team to disband...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your action.", ephemeral=True)
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
                await cog.show_disband_confirmation(interaction, selected_team)


class TeamDisbandConfirmView(discord.ui.View):
    """View with confirm/cancel buttons for disbanding team"""
    
    def __init__(self, team_id: int, team_name: str, team_tag: str, disbander_id: int, disbander_name: str, guild: discord.Guild):
        super().__init__(timeout=None)
        self.team_id = team_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.disbander_id = disbander_id
        self.disbander_name = disbander_name
        self.guild = guild
    
    @discord.ui.button(label="⚠️ DISBAND TEAM", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Get all team members before deletion
            team_members = await db.get_team_members(self.team_id)
            team = await db.get_team_by_id(self.team_id)
            
            # Delete team (this should cascade delete team_members)
            await db.delete_team(self.team_id)
            
            # Notify all members
            notified_count = 0
            for member in team_members:
                if member['discord_id'] == interaction.user.id:
                    continue  # Skip the disbander
                
                try:
                    user = self.guild.get_member(member['discord_id'])
                    if user:
                        disband_embed = discord.Embed(
                            title="Team Disbanded",
                            description=(
                                f"**{self.team_name}** [{self.team_tag}] has been disbanded.\n\n"
                                f"**Disbanded by:** <@{self.disbander_id}>\n\n"
                                f"The team no longer exists and all members have been removed."
                            ),
                            color=discord.Color.dark_red()
                        )
                        dm_channel = await user.create_dm()
                        await dm_channel.send(embed=disband_embed)
                        notified_count += 1
                except:
                    pass  # Silently fail if can't DM
            
            # Success message to disbander
            success_embed = discord.Embed(
                title="✅ Team Disbanded",
                description=(
                    f"**{self.team_name}** has been successfully disbanded.\n\n"
                    f"• Team members notified: {notified_count}/{len(team_members) - 1}\n"
                    f"• All team data has been deleted"
                ),
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed)
            
            # Log to bot logs
            await self.log_disband(interaction, team, len(team_members))
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            print(f"✓ Team {self.team_name} disbanded by {interaction.user.name}")
            
        except Exception as e:
            print(f"Error disbanding team: {e}")
            await interaction.followup.send(f"❌ Failed to disband team: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        cancel_embed = discord.Embed(
            title="Disband Cancelled",
            description=f"**{self.team_name}** has not been disbanded.",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=cancel_embed)
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
    
    async def log_disband(self, interaction: discord.Interaction, team: dict, member_count: int):
        """Log team disband to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="Team Disbanded",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Disbanded By**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Region:** {team['region']}\n"
                    f"**Members Removed:** {member_count}\n\n"
                    f"**Team ID:** {team['id']} | **Disbander ID:** {interaction.user.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=discord.Color.dark_red(),
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Disband logged to bot logs")
            
        except Exception as e:
            print(f"Error logging disband: {e}")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(TeamManagementCog(bot))
    print("✓ Team management cog loaded")
