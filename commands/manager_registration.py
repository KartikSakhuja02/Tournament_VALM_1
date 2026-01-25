import discord
from discord.ext import commands
import os
import asyncio
from database.db import db
from utils.thread_manager import add_staff_to_thread
from commands.registration import inactivity_warning_task, cancel_inactivity_warning, _active_threads


class ManagerRegistrationButtons(discord.ui.View):
    """Persistent view with manager registration button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register as Manager",
        style=discord.ButtonStyle.primary,
        custom_id="register_manager"
    )
    async def register_manager(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle manager registration button click"""
        # Check if user is banned
        ban_info = await db.is_player_banned(interaction.user.id)
        if ban_info:
            embed = discord.Embed(
                title="🚫 Registration Blocked",
                description="You are banned from participating in this tournament.",
                color=discord.Color.red()
            )
            if ban_info['reason']:
                embed.add_field(
                    name="Reason",
                    value=ban_info['reason'],
                    inline=False
                )
            embed.set_footer(text="Contact tournament administrators if you believe this is an error.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Respond immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is already a member of any team (any role)
        all_user_teams = []
        all_teams = await db.get_all_teams()
        for team in all_teams:
            members = await db.get_team_members(team['id'])
            if any(m['discord_id'] == interaction.user.id for m in members):
                all_user_teams.append(team)
        
        if all_user_teams:
            team_names = ", ".join([f"**{team['team_name']}**" for team in all_user_teams])
            await interaction.followup.send(
                f"❌ You are already part of: {team_names}\n"
                "Each person can only be a member of the teams they're already in.",
                ephemeral=True
            )
            return
        
        # Check if user already has an active manager registration thread
        for thread_id, thread_data in _active_threads.items():
            if thread_data['target_user_id'] == interaction.user.id:
                try:
                    thread = interaction.guild.get_thread(thread_id)
                    if thread and not thread.archived:
                        await interaction.followup.send(
                            f"❌ You already have an active registration thread: {thread.mention}\n"
                            "Please complete your registration there first.",
                            ephemeral=True
                        )
                        return
                except:
                    pass
        
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Manager Registration - {interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60
            )
            
            # Add user to thread
            await thread.add_user(interaction.user)
            
            # Add staff members (admins always, headmods only if online)
            await add_staff_to_thread(thread, interaction.guild)
            
            # Send confirmation
            await interaction.followup.send(
                f"✅ Private thread created: {thread.mention}",
                ephemeral=True
            )
            
            # Get teams with available manager slots (excluding teams user is already in)
            teams = await db.get_all_teams()
            print(f"[DEBUG] Total teams found: {len(teams)}")
            
            teams_with_slots = []
            
            for team in teams:
                members = await db.get_team_members(team['id'])
                print(f"[DEBUG] Team '{team['team_name']}' has {len(members)} members")
                
                # Skip if user is already a member of this team
                if any(m['discord_id'] == interaction.user.id for m in members):
                    print(f"[DEBUG] Skipping team '{team['team_name']}' - user already a member")
                    continue
                
                manager_count = sum(1 for m in members if m['role'] == 'manager')
                print(f"[DEBUG] Team '{team['team_name']}' has {manager_count} managers")
                
                if manager_count < 2:  # Max 2 managers per team
                    available_slots = 2 - manager_count
                    teams_with_slots.append({
                        'team': team,
                        'available_slots': available_slots
                    })
                    print(f"[DEBUG] Team '{team['team_name']}' added with {available_slots} slots")
            
            print(f"[DEBUG] Teams with available slots: {len(teams_with_slots)}")
            
            # Send team selection UI
            welcome_embed = discord.Embed(
                title="Select Team to Manage",
                description=(
                    f"Hello {interaction.user.mention}!\n\n"
                    "Please select which team you want to manage from the dropdown below.\n\n"
                    "**Note:** The team captain will need to approve your request."
                ),
                color=discord.Color.blue()
            )
            
            team_select_view = TeamSelectView(
                user_id=interaction.user.id,
                teams_with_slots=teams_with_slots
            )
            
            await thread.send(embed=welcome_embed, view=team_select_view)
            
            # Start inactivity warning task
            task = asyncio.create_task(inactivity_warning_task(thread, interaction.user.id))
            _active_threads[thread.id] = {
                'task': task,
                'target_user_id': interaction.user.id
            }
            print(f"✓ Started inactivity monitoring for manager thread {thread.id}")
            
        except Exception as e:
            print(f"Error creating manager registration thread: {e}")
            await interaction.followup.send(
                f"❌ Failed to create registration thread: {e}",
                ephemeral=True
            )


class TeamSelectView(discord.ui.View):
    """View with team dropdown"""
    
    def __init__(self, user_id: int, teams_with_slots: list):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.teams_with_slots = teams_with_slots
        
        # Add team select dropdown
        self.add_item(TeamSelect(user_id, teams_with_slots))


class TeamSelect(discord.ui.Select):
    """Dropdown for team selection"""
    
    def __init__(self, user_id: int, teams_with_slots: list):
        self.user_id = user_id
        self.teams_with_slots = teams_with_slots
        
        options = []
        
        # Always add 'No Teams Found' / 'My Team Not Listed' option first
        options.append(
            discord.SelectOption(
                label="My Team is Not Listed",
                value="no_teams",
                description="Click here if your team is not available"
            )
        )
        
        if teams_with_slots:
            # Add teams with available slots
            for item in teams_with_slots:
                team = item['team']
                slots = item['available_slots']
                options.append(
                    discord.SelectOption(
                        label=f"{team['team_name']} [{team['team_tag']}]",
                        value=str(team['id']),
                        description=f"{slots} manager slot{'s' if slots > 1 else ''} available"
                    )
                )
        
        super().__init__(
            placeholder="Choose a team to manage...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle team selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        # Cancel inactivity warning since user is now interacting
        if isinstance(interaction.channel, discord.Thread):
            cancel_inactivity_warning(interaction.channel.id)
        
        await interaction.response.defer()
        
        selected_value = self.values[0]
        
        # Check if "My Team is Not Listed" was selected
        if selected_value == "no_teams":
            await interaction.followup.send(
                "❌ Your team is not listed.\n\n"
                "**Possible reasons:**\n"
                "• Your team hasn't been registered yet\n"
                "• All manager slots are filled\n"
                "• You're already a member of the team\n\n"
                "Please register your team first from the team registration channel, or contact an administrator.",
                ephemeral=False
            )
            
            # Delete thread after 3 seconds
            await asyncio.sleep(3)
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            return
        
        # Get selected team
        team_id = int(selected_value)
        selected_team = None
        for item in self.teams_with_slots:
            if item['team']['id'] == team_id:
                selected_team = item['team']
                break
        
        if not selected_team:
            await interaction.followup.send(
                "❌ Team not found. Please try again.",
                ephemeral=False
            )
            return
        
        # Get captain
        captain_id = selected_team['captain_discord_id']
        captain = interaction.guild.get_member(captain_id)
        
        if not captain:
            await interaction.followup.send(
                "❌ Team captain not found in this server.",
                ephemeral=False
            )
            return
        
        # Get existing managers
        team_members = await db.get_team_members(team_id)
        existing_managers = [m for m in team_members if m['role'] in ['captain', 'manager']]
        approver_ids = [captain_id] + [m['discord_id'] for m in existing_managers if m['discord_id'] != captain_id]
        
        # Add captain to thread
        try:
            await interaction.channel.add_user(captain)
            print(f"✓ Added captain {captain.name} to manager registration thread")
        except Exception as e:
            print(f"Error adding captain to thread: {e}")
        
        # Add existing managers to thread
        for manager_data in existing_managers:
            if manager_data['discord_id'] != captain_id:
                try:
                    manager = interaction.guild.get_member(manager_data['discord_id'])
                    if manager:
                        await interaction.channel.add_user(manager)
                        print(f"✓ Added manager {manager.name} to thread")
                        await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"Error adding manager to thread: {e}")
        
        # Build mention string for approvers
        approver_mentions = []
        if captain:
            approver_mentions.append(captain.mention)
        for manager_data in existing_managers:
            if manager_data['discord_id'] != captain_id:
                manager = interaction.guild.get_member(manager_data['discord_id'])
                if manager:
                    approver_mentions.append(manager.mention)
        
        mentions_text = ", ".join(approver_mentions) if approver_mentions else "Team leadership"
        
        # Send approval request
        approval_embed = discord.Embed(
            title="Manager Approval Request",
            description=(
                f"{mentions_text}, {interaction.user.mention} wants to become a manager for your team!\n\n"
                f"**Team:** {selected_team['team_name']} [{selected_team['team_tag']}]\n"
                f"**Applicant:** {interaction.user.mention} ({interaction.user.name})\n\n"
                "Any captain or existing manager can approve/decline this request."
            ),
            color=discord.Color.orange()
        )
        
        approval_view = ManagerApprovalView(
            approver_ids=approver_ids,
            applicant_id=interaction.user.id,
            team_id=team_id,
            team_name=selected_team['team_name']
        )
        
        await interaction.followup.send(embed=approval_embed, view=approval_view)


class ManagerApprovalView(discord.ui.View):
    """View with accept/decline buttons for captain and managers"""
    
    def __init__(self, approver_ids: list, applicant_id: int, team_id: int, team_name: str):
        super().__init__(timeout=300)
        self.approver_ids = approver_ids
        self.applicant_id = applicant_id
        self.team_id = team_id
        self.team_name = team_name
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept manager request"""
        if interaction.user.id not in self.approver_ids:
            await interaction.response.send_message(
                "❌ Only the team captain or existing managers can approve this request.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Add user as manager to team
            await db.add_team_member(
                team_id=self.team_id,
                discord_id=self.applicant_id,
                role='manager'
            )
            
            # Get team details for logging
            team = await db.get_team_by_id(self.team_id)
            
            # Assign team role and manager role to manager
            if team and team.get('role_id'):
                try:
                    applicant = interaction.guild.get_member(self.applicant_id)
                    if applicant:
                        # Assign team role
                        team_role = interaction.guild.get_role(team['role_id'])
                        if team_role:
                            await applicant.add_roles(team_role)
                            print(f"✓ Assigned team role {team_role.name} to manager {applicant.name}")
                        
                        # Assign manager role
                        manager_role_id = os.getenv('MANAGER_ROLE_ID')
                        if manager_role_id:
                            manager_role = interaction.guild.get_role(int(manager_role_id))
                            if manager_role:
                                await applicant.add_roles(manager_role)
                                print(f"✓ Assigned Manager role to {applicant.name}")
                except Exception as e:
                    print(f"✗ Failed to assign role: {e}")
            
            # Success message
            applicant = interaction.guild.get_member(self.applicant_id)
            success_embed = discord.Embed(
                title="✅ Manager Approved!",
                description=(
                    f"{applicant.mention} has been added as a manager for **{self.team_name}**!\n\n"
                    "The manager can now help organize and lead the team."
                ),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=False)
            
            # Log to bot logs channel
            await self.log_manager_addition(interaction, applicant, team)
            
            # Delete thread after 3 seconds
            await asyncio.sleep(3)
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            
        except Exception as e:
            print(f"Error adding manager: {e}")
            await interaction.followup.send(
                f"❌ Failed to add manager: {e}",
                ephemeral=False
            )
    
    async def log_manager_addition(self, interaction: discord.Interaction, applicant: discord.Member, team: dict):
        """Log manager addition to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="New Manager Added",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Manager**\n{applicant.mention} ({applicant.name})\n\n"
                    f"**Approved By**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Team ID:** {team['id']} | **Manager ID:** {applicant.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=0x5865F2,  # Discord blurple
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Manager addition logged: {applicant.name} to {team['team_name']}")
            
        except Exception as e:
            print(f"Error logging manager addition: {e}")
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline manager request"""
        if interaction.user.id not in self.approver_ids:
            await interaction.response.send_message(
                "❌ Only the team captain or existing managers can decline this request.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "❌ Manager request declined.",
            ephemeral=False
        )
        
        # Delete thread after 3 seconds
        await asyncio.sleep(3)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()


class ManagerRegistrationCog(commands.Cog):
    """Manager registration system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def create_manager_registration_embed(self):
        """Create the manager registration embed message"""
        embed = discord.Embed(
            title="Manager Registration",
            description="Want to become a manager for a team? Click the button below to get started.",
            color=discord.Color.blue()
        )
        
        # Requirements section
        embed.add_field(
            name="Requirements:",
            value=(
                "• The team must have less than 2 managers\n"
                "• Team captain or existing manager must approve your request"
            ),
            inline=False
        )
        
        # Process section
        embed.add_field(
            name="Process:",
            value=(
                "1. Click the Register button\n"
                "2. Select the team you want to manage\n"
                "3. Wait for captain/manager approval\n"
                "4. Get notified once approved"
            ),
            inline=False
        )
        
        embed.add_field(
            name="",
            value="**Managers help organize and lead their teams!**",
            inline=False
        )
        
        return embed
    
    async def send_manager_registration_message(self, channel_id: int):
        """Send the manager registration embed to the specified channel"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Channel with ID {channel_id} not found!")
                return
            
            # Purge old bot messages from the channel
            print(f"🧹 Purging old bot messages from {channel.name}...")
            deleted = await channel.purge(limit=100, check=lambda m: m.author == self.bot.user)
            print(f"✅ Deleted {len(deleted)} old bot message(s)")
            
            embed = self.create_manager_registration_embed()
            view = ManagerRegistrationButtons()
            
            # Load and attach logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "LOGO.jpeg")
            
            if os.path.exists(logo_path):
                file = discord.File(logo_path, filename="LOGO.jpeg")
                embed.set_thumbnail(url="attachment://LOGO.jpeg")
                await channel.send(file=file, embed=embed, view=view)
                print(f"✅ Manager registration message sent to channel: {channel.name}")
            else:
                print(f"⚠️  Logo not found at {logo_path}, sending without logo")
                await channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"❌ Error sending manager registration message: {e}")


async def setup(bot):
    """Setup function for cog - registers persistent views"""
    cog = ManagerRegistrationCog(bot)
    await bot.add_cog(cog)
    
    # Register persistent view so buttons work after bot restart
    bot.add_view(ManagerRegistrationButtons())
    print("✓ Manager registration persistent view registered")
