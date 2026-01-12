"""
Manager Registration Command
Handles manager registration with team selection and captain approval
"""

import discord
from discord import app_commands
from discord.ext import commands
from database.db import db
from utils import has_test_role
import os
from datetime import datetime


# Environment variables
REGISTRATION_CHANNEL_ID = int(os.getenv("REGISTRATION_CHANNEL_ID"))
BOT_LOGS_CHANNEL_ID = int(os.getenv("BOT_LOGS_CHANNEL_ID"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))
HEADMOD_ROLE_ID = int(os.getenv("HEADMOD_ROLE_ID"))
ADMINISTRATOR_ROLE_ID = int(os.getenv("ADMINISTRATOR_ROLE_ID"))


class TeamSelectView(discord.ui.View):
    """View with team selection dropdown"""
    
    def __init__(self, teams: list, user: discord.Member):
        super().__init__(timeout=300)
        self.user = user
        self.add_item(TeamSelect(teams, user))


class TeamSelect(discord.ui.Select):
    """Dropdown for selecting a team to manage"""
    
    def __init__(self, teams: list, user: discord.Member):
        self.user = user
        
        # Create options from teams
        options = []
        
        if not teams:
            # No teams available
            options.append(
                discord.SelectOption(
                    label="No teams found",
                    value="no_teams",
                    description="Register your team first (must be captain)",
                    emoji="❌"
                )
            )
        else:
            for team in teams:
                manager_count = team.get('manager_count', 0)
                available_slots = 2 - manager_count
                options.append(
                    discord.SelectOption(
                        label=team['team_name'],
                        value=str(team['id']),
                        description=f"Region: {team['region']} | {available_slots} manager slot(s) available",
                        emoji="🎮"
                    )
                )
        
        super().__init__(
            placeholder="Select a team to manage...",
            options=options,
            custom_id="team_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle team selection"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This selection is not for you!",
                ephemeral=True
            )
            return
        
        selected_value = self.values[0]
        
        if selected_value == "no_teams":
            # No teams available
            await interaction.response.edit_message(
                content="❌ **No Teams Available**\n\n"
                        "There are currently no teams registered with available manager slots.\n"
                        "To register your own team, you must:\n"
                        "• Be registered as a player\n"
                        "• Register as team captain\n"
                        "• Create your team using the team registration command",
                view=None
            )
            return
        
        # Get selected team
        team_id = int(selected_value)
        team = await db.get_team_by_id(team_id)
        
        if not team:
            await interaction.response.edit_message(
                content="❌ Team not found. Please try again.",
                view=None
            )
            return
        
        # Check if team still has manager slots
        manager_count = await db.get_team_role_count(team_id, 'manager')
        if manager_count >= 2:
            await interaction.response.edit_message(
                content=f"❌ **{team['team_name']}** already has the maximum number of managers (2).\nPlease select a different team.",
                view=None
            )
            return
        
        # Disable the select menu
        await interaction.response.edit_message(
            content=f"✓ Team selected: **{team['team_name']}**\n\nWaiting for captain approval...",
            view=None
        )
        
        # Get captain
        captain = await interaction.guild.fetch_member(team['captain_discord_id'])
        
        # Get existing managers
        managers = await db.get_team_members(team_id, 'manager')
        
        # Add captain and managers to thread
        thread = interaction.channel
        try:
            await thread.add_user(captain)
            for manager in managers:
                try:
                    manager_member = await interaction.guild.fetch_member(manager['discord_id'])
                    await thread.add_user(manager_member)
                except:
                    pass
        except:
            pass
        
        # Send approval request
        approval_view = ManagerApprovalView(team, self.user, captain, managers)
        await thread.send(
            f"{captain.mention} | {' '.join([f'<@{m['discord_id']}>' for m in managers])}\n\n"
            f"**Manager Registration Request**\n\n"
            f"👤 **User:** {self.user.mention} ({self.user.name})\n"
            f"🎮 **Team:** {team['team_name']}\n"
            f"📍 **Region:** {team['region']}\n\n"
            f"The above user wants to register as a manager for your team.\n"
            f"**Only the team captain or existing managers can approve/reject this request.**",
            view=approval_view
        )


class ManagerApprovalView(discord.ui.View):
    """View with approve/reject buttons for manager requests"""
    
    def __init__(self, team: dict, requesting_user: discord.Member, captain: discord.Member, managers: list):
        super().__init__(timeout=None)
        self.team = team
        self.requesting_user = requesting_user
        self.captain = captain
        self.managers = managers
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user can approve/reject (captain or manager)"""
        if user_id == self.captain.id:
            return True
        return any(m['discord_id'] == user_id for m in self.managers)
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✓")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve manager request"""
        if not self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                "❌ Only the team captain or existing managers can approve this request.",
                ephemeral=True
            )
            return
        
        # Add manager to team
        try:
            await db.add_team_member(
                self.team['id'],
                self.requesting_user.id,
                'manager'
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to add manager: {e}",
                ephemeral=True
            )
            return
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(
            content=f"✅ **Approved by {interaction.user.mention}**\n\n"
                    f"{self.requesting_user.mention} has been added as a manager for **{self.team['team_name']}**!",
            view=self
        )
        
        # Send success message to user
        await interaction.channel.send(
            f"🎉 Congratulations {self.requesting_user.mention}!\n\n"
            f"You are now a manager for **{self.team['team_name']}**.\n"
            f"You can now help manage the team and approve/reject future manager requests."
        )
        
        # Log to bot-logs channel
        await self.log_registration(interaction.guild, interaction.user)
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.secondary, emoji="✗")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reject manager request"""
        if not self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                "❌ Only the team captain or existing managers can reject this request.",
                ephemeral=True
            )
            return
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(
            content=f"❌ **Rejected by {interaction.user.mention}**\n\n"
                    f"Manager request for {self.requesting_user.mention} has been rejected.",
            view=self
        )
        
        # Send rejection message
        await interaction.channel.send(
            f"Sorry {self.requesting_user.mention}, your manager request for **{self.team['team_name']}** was rejected.\n"
            f"You can try registering for a different team."
        )
    
    async def log_registration(self, guild: discord.Guild, approver: discord.Member):
        """Log manager registration to bot-logs channel"""
        try:
            logs_channel = guild.get_channel(BOT_LOGS_CHANNEL_ID)
            if not logs_channel:
                return
            
            # Create embed
            embed = discord.Embed(
                title="New Manager Registration (Thread - Manual)",
                description=(
                    f"**User:** {self.requesting_user.mention}\n"
                    f"**Team:** {self.team['team_name']}\n"
                    f"**Region:** {self.team['region']}\n"
                    f"**Approved By:** {approver.mention}\n\n"
                    f"**User ID:** {self.requesting_user.id}\n"
                    f"**Method:** Manual\n"
                    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
                color=discord.Color.green()
            )
            
            await logs_channel.send(embed=embed)
        except Exception as e:
            print(f"✗ Failed to log manager registration: {e}")


class ManagerRegistrationButtons(discord.ui.View):
    """Persistent view with manager registration button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register as Manager",
        style=discord.ButtonStyle.primary,
        emoji="👔",
        custom_id="register_manager_button"
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle manager registration button click"""
        # Defer the response immediately
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is already registered as a player
        player = await db.get_player_by_discord_id(interaction.user.id)
        if player:
            await interaction.followup.send(
                "❌ **Cannot Register as Manager**\n\n"
                "You are already registered as a player. Players cannot register as managers.\n"
                "If you want to manage a team, you need to use a different Discord account.",
                ephemeral=True
            )
            return
        
        # Check if user is already a manager
        teams = await db.get_member_teams(interaction.user.id)
        manager_teams = [t for t in teams if t['role'] == 'manager']
        if manager_teams:
            team_list = "\n".join([f"• {t['team_name']}" for t in manager_teams])
            await interaction.followup.send(
                f"❌ **Already Registered as Manager**\n\n"
                f"You are already a manager for the following team(s):\n{team_list}\n\n"
                f"Each user can only be a manager for one team at a time.",
                ephemeral=True
            )
            return
        
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Manager Registration - {interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to create registration thread: {e}",
                ephemeral=True
            )
            return
        
        # Add user to thread
        await thread.add_user(interaction.user)
        
        # Add staff, head mods, and administrators to thread
        guild = interaction.guild
        staff_role = guild.get_role(STAFF_ROLE_ID)
        headmod_role = guild.get_role(HEADMOD_ROLE_ID)
        admin_role = guild.get_role(ADMINISTRATOR_ROLE_ID)
        
        # Add staff members
        if staff_role:
            for member in staff_role.members:
                try:
                    await thread.add_user(member)
                except:
                    pass
        
        # Add head mods
        if headmod_role:
            for member in headmod_role.members:
                try:
                    await thread.add_user(member)
                except:
                    pass
        
        # Add administrators
        if admin_role:
            for member in admin_role.members:
                try:
                    await thread.add_user(member)
                except:
                    pass
        
        # Get teams with available manager slots
        teams_with_slots = await db.get_teams_with_manager_slots()
        
        # Send team selection
        await thread.send(
            f"Welcome {interaction.user.mention}!\n\n"
            f"**Manager Registration**\n\n"
            f"You are registering as a manager for an existing team.\n"
            f"Please select the team you want to manage from the dropdown below.\n\n"
            f"**Note:** The team captain and existing managers will need to approve your request.",
            view=TeamSelectView(teams_with_slots, interaction.user)
        )
        
        # Send confirmation
        await interaction.followup.send(
            f"✓ Registration thread created: {thread.mention}",
            ephemeral=True
        )


class ManagerRegistrationCog(commands.Cog):
    """Manager registration commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="setup_manager_registration")
    @app_commands.describe(channel="The channel where the manager registration UI will be posted")
    @has_test_role()
    async def setup_manager_registration(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Setup the manager registration UI in a channel"""
        await interaction.response.defer(ephemeral=True)
        
        target_channel = channel or interaction.channel
        
        # Create embed
        embed = discord.Embed(
            title="🎮 VALORANT Mobile Tournament - Manager Registration",
            description=(
                "**Welcome to Manager Registration!**\n\n"
                "Register as a **Manager** to help run an existing team.\n\n"
                "**Requirements:**\n"
                "✓ Must NOT be registered as a player\n"
                "✓ Must be approved by team captain or existing managers\n"
                "✓ Maximum 2 managers per team\n\n"
                "**Manager Responsibilities:**\n"
                "• Help captain manage team operations\n"
                "• Approve/reject new manager requests\n"
                "• Coordinate team schedules and practices\n\n"
                "Click **Register as Manager** below to begin!"
            ),
            color=discord.Color.blue()
        )
        
        # Send message with button
        await target_channel.send(
            embed=embed,
            view=ManagerRegistrationButtons()
        )
        
        await interaction.followup.send(
            f"✓ Manager registration UI posted in {target_channel.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ManagerRegistrationCog(bot))
