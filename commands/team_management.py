import discord
from discord.ext import commands
from discord import app_commands
import os
import re
from database.db import db
from utils.checks import commands_channel_only


class TeamManagementCog(commands.Cog):
    """Team management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="invite", description="Invite one or more players to your team")
    @app_commands.describe(players="The players to invite (mention them: @player1 @player2 ...)")
    async def invite_player(self, interaction: discord.Interaction, players: str):
        """Invite one or more players to join your team"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has Captain or Manager role
        captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
        manager_role_id = os.getenv('MANAGER_ROLE_ID')
        
        user_role_ids = [role.id for role in interaction.user.roles]
        has_permission = False
        
        if captain_role_id and int(captain_role_id) in user_role_ids:
            has_permission = True
        if manager_role_id and int(manager_role_id) in user_role_ids:
            has_permission = True
        
        if not has_permission:
            await interaction.followup.send(
                "❌ You need the Captain or Manager role to use this command.",
                ephemeral=True
            )
            return
        
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
        
        # Parse mentions from the input
        # Discord mentions are in format <@USER_ID> or <@!USER_ID>
        mention_pattern = r'<@!?(\d+)>'
        user_ids = re.findall(mention_pattern, players)
        
        if not user_ids:
            await interaction.followup.send(
                "❌ Please mention at least one player to invite.\n"
                "Example: `/invite @player1 @player2 @player3`",
                ephemeral=True
            )
            return
        
        # Get member objects for all mentioned users
        mentioned_members = []
        for user_id in user_ids:
            member = interaction.guild.get_member(int(user_id))
            if member:
                mentioned_members.append(member)
        
        if not mentioned_members:
            await interaction.followup.send(
                "❌ Could not find any valid members to invite.",
                ephemeral=True
            )
            return
        
        # If user is part of multiple teams, let them choose which team to invite to
        if len(user_teams) > 1:
            # Show team selection dropdown
            view = TeamInviteSelectView(
                inviter_id=interaction.user.id,
                invited_players=mentioned_members,
                teams=user_teams
            )
            
            await interaction.followup.send(
                f"Select which team you want to invite {len(mentioned_members)} player(s) to:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, send invites directly
            team = user_teams[0]
            await self.send_team_invites(interaction, mentioned_members, team)
    
    async def send_team_invites(self, interaction: discord.Interaction, players: list, team: dict):
        """Send team invites to multiple players"""
        successful_invites = []
        failed_invites = []
        
        for player in players:
            # Check if the invited player is registered
            invited_player = await db.get_player_by_discord_id(player.id)
            if not invited_player:
                failed_invites.append(f"{player.mention} - Not registered")
                continue
            
            # Check if player is the same as the inviter
            if player.id == interaction.user.id:
                failed_invites.append(f"{player.mention} - Cannot invite yourself")
                continue
            
            # Check if player is already a member of this team
            team_members = await db.get_team_members(team['id'])
            if any(m['discord_id'] == player.id for m in team_members):
                failed_invites.append(f"{player.mention} - Already in team")
                continue
            
            # Send the invite
            try:
                await self.send_single_invite(player, team, interaction, team_members)
                successful_invites.append(player.mention)
            except discord.Forbidden:
                failed_invites.append(f"{player.mention} - DMs disabled")
            except Exception as e:
                failed_invites.append(f"{player.mention} - Error: {str(e)[:50]}")
        
        # Build response message
        response_parts = []
        
        if successful_invites:
            response_parts.append(f"✅ **Invites sent to {len(successful_invites)} player(s):**\n" + "\n".join(successful_invites))
        
        if failed_invites:
            response_parts.append(f"\n❌ **Failed to invite {len(failed_invites)} player(s):**\n" + "\n".join(failed_invites))
        
        if not successful_invites and not failed_invites:
            response_parts.append("❌ No valid players to invite.")
        
        await interaction.followup.send("\n".join(response_parts), ephemeral=True)
    
    async def send_single_invite(self, player: discord.Member, team: dict, interaction: discord.Interaction, team_members: list):
        """Send a single team invite to a player"""
        # Check if team has a captain
        team_info = await db.get_team_by_id(team['id'])
        has_captain = team_info.get('captain_discord_id') is not None
        is_first_player = len(team_members) == 0
        
        # Build invite description
        invite_description = (
            f"**{interaction.user.name}** has invited you to join their team!\n\n"
            f"**Team:** {team['team_name']} [{team['team_tag']}]\n"
            f"**Region:** {team['region']}\n"
            f"**Invited by:** {interaction.user.mention}\n\n"
        )
        
        # Add captain notice if this player will become captain
        if is_first_player and not has_captain:
            invite_description += "🎖️ **You will become the team captain!**\n\n"
        
        invite_description += "Would you like to join this team?"
        
        # Create invite embed for DM
        invite_embed = discord.Embed(
            title="Team Invite",
            description=invite_description,
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
        
        # Send DM
        dm_channel = await player.create_dm()
        await dm_channel.send(embed=invite_embed, view=invite_view)
        print(f"✓ Sent team invite to {player.name} for team {team['team_name']}")
    
    async def send_team_invite(self, interaction: discord.Interaction, player: discord.Member, team: dict):
        """Send the actual team invite DM to the player (legacy single invite)"""
        # Check if player is already a member of this team
        team_members = await db.get_team_members(team['id'])
        if any(m['discord_id'] == player.id for m in team_members):
            await interaction.followup.send(
                f"❌ {player.mention} is already a member of **{team['team_name']}**!",
                ephemeral=True
            )
            return
        
        # Check if team has a captain
        team_info = await db.get_team_by_id(team['id'])
        has_captain = team_info.get('captain_discord_id') is not None
        is_first_player = len(team_members) == 0
        
        # Build invite description
        invite_description = (
            f"**{interaction.user.name}** has invited you to join their team!\n\n"
            f"**Team:** {team['team_name']} [{team['team_tag']}]\n"
            f"**Region:** {team['region']}\n"
            f"**Invited by:** {interaction.user.mention}\n\n"
        )
        
        # Add captain notice if this player will become captain
        if is_first_player and not has_captain:
            invite_description += "🎖️ **You will become the team captain!**\n\n"
        
        invite_description += "Would you like to join this team?"
        
        # Create invite embed for DM
        invite_embed = discord.Embed(
            title="Team Invite",
            description=invite_description,
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
    async def kick_player(self, interaction: discord.Interaction, player: discord.Member):
        """Kick a player from your team"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has Captain or Manager role
        captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
        manager_role_id = os.getenv('MANAGER_ROLE_ID')
        
        user_role_ids = [role.id for role in interaction.user.roles]
        has_permission = False
        
        if captain_role_id and int(captain_role_id) in user_role_ids:
            has_permission = True
        if manager_role_id and int(manager_role_id) in user_role_ids:
            has_permission = True
        
        if not has_permission:
            await interaction.followup.send(
                "❌ You need the Captain or Manager role to use this command.",
                ephemeral=True
            )
            return
        
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
            # Get player's role in team before removing
            team_members = await db.get_team_members(team['id'])
            player_role = None
            for member in team_members:
                if member['discord_id'] == player.id:
                    player_role = member['role']
                    break
            
            # Remove player from team
            await db.remove_team_member(team['id'], player.id)
            
            # Remove team role from player
            if team.get('role_id'):
                try:
                    role = interaction.guild.get_role(team['role_id'])
                    if role and role in player.roles:
                        await player.remove_roles(role)
                        print(f"✓ Removed team role {role.name} from {player.name}")
                except Exception as e:
                    print(f"✗ Failed to remove team role: {e}")
            
            # Remove captain or manager role if applicable
            if player_role in ['captain', 'manager']:
                try:
                    # Check if player has this role in any other team
                    other_teams = await db.get_user_teams_by_role(player.id, player_role)
                    
                    # Only remove the role if they don't have it in another team
                    if not other_teams:
                        role_env_key = 'CAPTAIN_ROLE_ID' if player_role == 'captain' else 'MANAGER_ROLE_ID'
                        position_role_id = os.getenv(role_env_key)
                        if position_role_id:
                            position_role = interaction.guild.get_role(int(position_role_id))
                            if position_role and position_role in player.roles:
                                await player.remove_roles(position_role)
                                print(f"✓ Removed {player_role} role from {player.name}")
                except Exception as e:
                    print(f"✗ Failed to remove position role: {e}")
            
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
    async def disband_team(self, interaction: discord.Interaction):
        """Disband a team (captain or manager only)"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has Captain or Manager role
        captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
        manager_role_id = os.getenv('MANAGER_ROLE_ID')
        
        user_role_ids = [role.id for role in interaction.user.roles]
        has_permission = False
        
        if captain_role_id and int(captain_role_id) in user_role_ids:
            has_permission = True
        if manager_role_id and int(manager_role_id) in user_role_ids:
            has_permission = True
        
        if not has_permission:
            await interaction.followup.send(
                "❌ You need the Captain or Manager role to use this command.",
                ephemeral=True
            )
            return
        
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
    
    @app_commands.command(name="transfer-captainship", description="Transfer team captainship to another member (/transfer-captainship)")
    async def transfer_captainship(self, interaction: discord.Interaction):
        """Transfer captainship to another team member"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has Captain role
        captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
        
        user_role_ids = [role.id for role in interaction.user.roles]
        has_captain_role = captain_role_id and int(captain_role_id) in user_role_ids
        
        if not has_captain_role:
            await interaction.followup.send(
                "❌ You need the Captain role to use this command.",
                ephemeral=True
            )
            return
        
        # Check if user is a captain
        captain_teams = await db.get_user_teams_by_role(interaction.user.id, 'captain')
        
        if not captain_teams:
            await interaction.followup.send(
                "❌ You must be a team captain to transfer captainship!",
                ephemeral=True
            )
            return
        
        # If multiple teams, let them choose which team
        if len(captain_teams) > 1:
            view = TransferCaptainshipTeamSelectView(
                captain_id=interaction.user.id,
                teams=captain_teams,
                guild=interaction.guild
            )
            await interaction.followup.send(
                "Select which team's captainship you want to transfer:",
                view=view,
                ephemeral=True
            )
        else:
            # Only one team, show member selection directly
            team = captain_teams[0]
            await self.show_transfer_member_selection(interaction, team)
    
    async def show_transfer_member_selection(self, interaction: discord.Interaction, team: dict):
        """Show member selection for captainship transfer"""
        # Get all team members
        team_members = await db.get_team_members(team['id'])
        
        # Filter out the current captain and only include players/managers
        eligible_members = [
            m for m in team_members 
            if m['discord_id'] != interaction.user.id 
            and m['role'] in ['player', 'manager']
        ]
        
        if not eligible_members:
            await interaction.followup.send(
                "❌ No eligible members to transfer captainship to!\n"
                "Only players and managers can become captain.",
                ephemeral=True
            )
            return
        
        # Send DM with member selection
        try:
            transfer_embed = discord.Embed(
                title="Transfer Captainship",
                description=(
                    f"**Team:** {team['team_name']} [{team['team_tag']}]\n"
                    f"**Region:** {team['region']}\n\n"
                    f"Select the member you want to transfer captainship to.\n"
                    f"They will become the new team captain."
                ),
                color=discord.Color.blue()
            )
            
            view = TransferCaptainshipMemberSelectView(
                team_id=team['id'],
                team_name=team['team_name'],
                current_captain_id=interaction.user.id,
                members=eligible_members,
                guild=interaction.guild
            )
            
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send(embed=transfer_embed, view=view)
            
            await interaction.followup.send(
                "✅ Member selection sent to your DMs!",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Could not send DM. Please enable DMs from server members.",
                ephemeral=True
            )


class TeamInviteSelectView(discord.ui.View):
    """View for selecting which team to invite player(s) to"""
    
    def __init__(self, inviter_id: int, invited_players: list, teams: list):
        super().__init__(timeout=300)
        self.inviter_id = inviter_id
        self.invited_players = invited_players  # Now a list of members
        self.teams = teams
        
        # Add team selection dropdown
        self.add_item(TeamInviteSelect(inviter_id, invited_players, teams))


class TeamInviteSelect(discord.ui.Select):
    """Dropdown for team selection when inviting"""
    
    def __init__(self, inviter_id: int, invited_players: list, teams: list):
        self.inviter_id = inviter_id
        self.invited_players = invited_players  # Now a list of members
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
                # Send invites to all players
                await cog.send_team_invites(interaction, self.invited_players, selected_team)


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
            
            # Check if this team has a captain yet (check both database and actual player members)
            team = await db.get_team_by_id(self.team_id)
            has_captain = team.get('captain_discord_id') is not None
            
            # Check if there are any players/captains already (exclude managers and coaches)
            player_members = [m for m in team_members if m['role'] in ['player', 'captain']]
            is_first_player = len(player_members) == 0
            
            # Determine role: first invited player becomes captain, others are regular players
            player_role = 'captain' if (is_first_player and not has_captain) else 'player'
            
            # Add player to team
            await db.add_team_member(
                team_id=self.team_id,
                discord_id=interaction.user.id,
                role=player_role
            )
            
            # If this player is becoming captain, update the teams table
            if player_role == 'captain':
                await db.update_team(self.team_id, captain_discord_id=interaction.user.id)
            
            # Assign team role to player
            if team and team.get('role_id'):
                try:
                    role = self.guild.get_role(team['role_id'])
                    if role:
                        member = self.guild.get_member(interaction.user.id)
                        if member:
                            await member.add_roles(role)
                            print(f"✓ Assigned role {role.name} to {member.name}")
                except Exception as e:
                    print(f"✗ Failed to assign role: {e}")
            
            # Assign captain role if they became captain
            if player_role == 'captain':
                try:
                    captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
                    if captain_role_id:
                        captain_role = self.guild.get_role(int(captain_role_id))
                        if captain_role:
                            member = self.guild.get_member(interaction.user.id)
                            if member:
                                await member.add_roles(captain_role)
                                print(f"✓ Assigned Captain role to {member.name}")
                except Exception as e:
                    print(f"✗ Failed to assign Captain role: {e}")
            
            # Success message
            success_message = (
                f"You have successfully joined **{self.team_name}**!\n\n"
            )
            
            if player_role == 'captain':
                success_message += "🎖️ **You are now the team captain!**\n\n"
            
            success_message += "Welcome to the team!"
            
            success_embed = discord.Embed(
                title="✅ Team Invite Accepted!",
                description=success_message,
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed)
            
            # Notify the inviter
            try:
                inviter = self.guild.get_member(self.inviter_id)
                if inviter:
                    notify_message = f"{interaction.user.mention} has accepted your invite!\n"
                    
                    if player_role == 'captain':
                        notify_message += f"🎖️ They are now the **captain** of **{self.team_name}**!"
                    else:
                        notify_message += f"They are now a member of **{self.team_name}**."
                    
                    notify_embed = discord.Embed(
                        title="Team Invite Accepted",
                        description=notify_message,
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
            
            # Remove team role from user
            if team and team.get('role_id'):
                try:
                    role = interaction.guild.get_role(team['role_id'])
                    member = interaction.guild.get_member(interaction.user.id)
                    if role and member and role in member.roles:
                        await member.remove_roles(role)
                        print(f"✓ Removed team role {role.name} from {member.name}")
                except Exception as e:
                    print(f"✗ Failed to remove team role: {e}")
            
            # Remove captain or manager role if applicable
            if self.user_role in ['captain', 'manager']:
                try:
                    member = interaction.guild.get_member(interaction.user.id)
                    if member:
                        # Check if user has this role in any other team
                        other_teams = await db.get_user_teams_by_role(interaction.user.id, self.user_role)
                        
                        # Only remove the role if they don't have it in another team
                        if not other_teams:
                            role_env_key = 'CAPTAIN_ROLE_ID' if self.user_role == 'captain' else 'MANAGER_ROLE_ID'
                            position_role_id = os.getenv(role_env_key)
                            if position_role_id:
                                position_role = interaction.guild.get_role(int(position_role_id))
                                if position_role and position_role in member.roles:
                                    await member.remove_roles(position_role)
                                    print(f"✓ Removed {self.user_role} role from {member.name}")
                except Exception as e:
                    print(f"✗ Failed to remove position role: {e}")
            
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
            
            # Disable buttons first
            for item in self.children:
                item.disabled = True
            
            # Edit the original message with disabled buttons
            await interaction.edit_original_response(embed=success_embed, view=self)
            
            # Log to bot logs
            await self.log_disband(interaction, team, len(team_members))
            
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
        
        # Disable buttons first
        for item in self.children:
            item.disabled = True
        
        # Edit the original message with disabled buttons
        await interaction.edit_original_response(embed=cancel_embed, view=self)
    
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


class TransferCaptainshipTeamSelectView(discord.ui.View):
    """View for selecting which team to transfer captainship for"""
    
    def __init__(self, captain_id: int, teams: list, guild: discord.Guild):
        super().__init__(timeout=300)
        self.captain_id = captain_id
        self.teams = teams
        self.guild = guild
        self.add_item(TransferCaptainshipTeamSelect(captain_id, teams, guild))


class TransferCaptainshipTeamSelect(discord.ui.Select):
    """Dropdown for team selection when transferring captainship"""
    
    def __init__(self, captain_id: int, teams: list, guild: discord.Guild):
        self.captain_id = captain_id
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
            placeholder="Select team to transfer captainship...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.captain_id:
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
                await cog.show_transfer_member_selection(interaction, selected_team)


class TransferCaptainshipMemberSelectView(discord.ui.View):
    """View for selecting member to transfer captainship to"""
    
    def __init__(self, team_id: int, team_name: str, current_captain_id: int, members: list, guild: discord.Guild):
        super().__init__(timeout=None)
        self.team_id = team_id
        self.team_name = team_name
        self.current_captain_id = current_captain_id
        self.members = members
        self.guild = guild
        self.add_item(TransferCaptainshipMemberSelect(team_id, team_name, current_captain_id, members, guild))


class TransferCaptainshipMemberSelect(discord.ui.Select):
    """Dropdown for member selection"""
    
    def __init__(self, team_id: int, team_name: str, current_captain_id: int, members: list, guild: discord.Guild):
        self.team_id = team_id
        self.team_name = team_name
        self.current_captain_id = current_captain_id
        self.members = members
        self.guild = guild
        
        options = []
        for member in members:
            # Get member object from guild
            guild_member = guild.get_member(member['discord_id'])
            if guild_member:
                options.append(
                    discord.SelectOption(
                        label=guild_member.name,
                        value=str(member['discord_id']),
                        description=f"Role: {member['role'].title()}"
                    )
                )
        
        super().__init__(
            placeholder="Select new captain...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.current_captain_id:
            await interaction.response.send_message("This is not your transfer.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        new_captain_id = int(self.values[0])
        new_captain = self.guild.get_member(new_captain_id)
        
        if not new_captain:
            await interaction.followup.send("❌ Selected member not found!", ephemeral=True)
            return
        
        try:
            # Get team details
            team = await db.get_team_by_id(self.team_id)
            if not team:
                await interaction.followup.send("❌ Team not found!", ephemeral=True)
                return
            
            # Update team captain in database
            await db.update_team(self.team_id, captain_discord_id=new_captain_id)
            
            # Update team_members - change old captain role to manager
            await db.remove_team_member(self.team_id, self.current_captain_id)
            await db.add_team_member(self.team_id, self.current_captain_id, 'manager')
            
            # Update new captain role in team_members
            await db.remove_team_member(self.team_id, new_captain_id)
            await db.add_team_member(self.team_id, new_captain_id, 'captain')
            
            # Update Discord roles - transfer captain role
            try:
                old_captain_member = self.guild.get_member(self.current_captain_id)
                captain_role_id = os.getenv('CAPTAIN_ROLE_ID')
                manager_role_id = os.getenv('MANAGER_ROLE_ID')
                
                if captain_role_id:
                    captain_role = self.guild.get_role(int(captain_role_id))
                    
                    # Remove captain role from old captain
                    if captain_role and old_captain_member and captain_role in old_captain_member.roles:
                        await old_captain_member.remove_roles(captain_role)
                        print(f"✓ Removed Captain role from {old_captain_member.name}")
                    
                    # Add captain role to new captain
                    if captain_role and new_captain:
                        await new_captain.add_roles(captain_role)
                        print(f"✓ Assigned Captain role to {new_captain.name}")
                
                # Assign manager role to old captain
                if manager_role_id and old_captain_member:
                    manager_role = self.guild.get_role(int(manager_role_id))
                    if manager_role:
                        await old_captain_member.add_roles(manager_role)
                        print(f"✓ Assigned Manager role to {old_captain_member.name}")
                
                # Remove manager role from new captain (if they had it)
                if manager_role_id and new_captain:
                    manager_role = self.guild.get_role(int(manager_role_id))
                    if manager_role and manager_role in new_captain.roles:
                        await new_captain.remove_roles(manager_role)
                        print(f"✓ Removed Manager role from {new_captain.name}")
                        
            except Exception as e:
                print(f"✗ Failed to update captain/manager roles: {e}")
            
            # Success message to old captain
            success_embed = discord.Embed(
                title="✅ Captainship Transferred",
                description=(
                    f"You have successfully transferred captainship of **{self.team_name}**.\n\n"
                    f"**New Captain:** {new_captain.mention}\n"
                    f"**Your New Role:** Manager"
                ),
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed)
            
            # Notify new captain
            try:
                new_captain_embed = discord.Embed(
                    title="🎉 You Are Now Team Captain!",
                    description=(
                        f"You have been promoted to captain of **{self.team_name}** [{team['team_tag']}]!\n\n"
                        f"**Previous Captain:** <@{self.current_captain_id}>\n\n"
                        f"As captain, you now have full control over the team including:\n"
                        f"• Inviting and kicking players\n"
                        f"• Approving managers and coaches\n"
                        f"• Transferring or disbanding the team"
                    ),
                    color=discord.Color.gold()
                )
                await new_captain.send(embed=new_captain_embed)
            except:
                pass  # Silently fail if can't DM
            
            # Log to bot logs
            await self.log_transfer(interaction, team, new_captain)
            
            # Disable dropdown
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(view=self.view)
            
            print(f"✓ Captainship transferred from {interaction.user.name} to {new_captain.name} for team {self.team_name}")
            
        except Exception as e:
            print(f"Error transferring captainship: {e}")
            await interaction.followup.send(f"❌ Failed to transfer captainship: {e}", ephemeral=True)
    
    async def log_transfer(self, interaction: discord.Interaction, team: dict, new_captain: discord.Member):
        """Log captainship transfer to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="Captainship Transferred",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Previous Captain**\n{interaction.user.mention} ({interaction.user.name})\n"
                    f"→ New Role: Manager\n\n"
                    f"**New Captain**\n{new_captain.mention} ({new_captain.name})\n\n"
                    f"**Team ID:** {team['id']} | "
                    f"**New Captain ID:** {new_captain.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=discord.Color.gold(),
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Captainship transfer logged to bot logs")
            
        except Exception as e:
            print(f"Error logging transfer: {e}")


async def setup(bot):
    """Setup function for cog"""
    await bot.add_cog(TeamManagementCog(bot))
    print("✓ Team management cog loaded")
