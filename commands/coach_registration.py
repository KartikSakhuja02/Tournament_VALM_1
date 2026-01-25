import discord
from discord.ext import commands
import os
import asyncio
from database.db import db
from utils.thread_manager import add_staff_to_thread
from commands.registration import inactivity_warning_task, cancel_inactivity_warning, _active_threads


class CoachRegistrationButtons(discord.ui.View):
    """Persistent view with coach registration button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register as Coach",
        style=discord.ButtonStyle.primary,
        custom_id="register_coach"
    )
    async def register_coach(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle coach registration button click"""
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
        
        # Check if user already has an active coach registration thread
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
                name=f"Coach Registration - {interaction.user.name}",
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
            
            # Get teams with available coach slots (excluding teams user is already in)
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
                
                coach_count = sum(1 for m in members if m['role'] == 'coach')
                print(f"[DEBUG] Team '{team['team_name']}' has {coach_count} coaches")
                
                if coach_count < 1:  # Max 1 coach per team
                    teams_with_slots.append({
                        'team': team,
                        'available_slots': 1 - coach_count
                    })
                    print(f"[DEBUG] Team '{team['team_name']}' added with coach slot")
            
            print(f"[DEBUG] Teams with available coach slots: {len(teams_with_slots)}")
            
            # Send team selection UI
            welcome_embed = discord.Embed(
                title="Select Team to Coach",
                description=(
                    f"Hello {interaction.user.mention}!\n\n"
                    "Please select which team you want to coach from the dropdown below.\n\n"
                    "**Note:** The team captain and managers will need to approve your request."
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
            print(f"✓ Started inactivity monitoring for coach thread {thread.id}")
            
        except Exception as e:
            print(f"Error creating coach registration thread: {e}")
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
        
        # Always add 'My Team is Not Listed' option first
        options.append(
            discord.SelectOption(
                label="My Team is Not Listed",
                value="no_teams",
                description="Click here if your team is not available"
            )
        )
        
        if teams_with_slots:
            # Add teams with available coach slots
            for item in teams_with_slots:
                team = item['team']
                options.append(
                    discord.SelectOption(
                        label=f"{team['team_name']} [{team['team_tag']}]",
                        value=str(team['id']),
                        description="1 coach slot available"
                    )
                )
        
        super().__init__(
            placeholder="Choose a team to coach...",
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
                "• The coach slot is already filled\n"
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
            print(f"✓ Added captain {captain.name} to coach registration thread")
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
            title="Coach Approval Request",
            description=(
                f"{mentions_text}, {interaction.user.mention} wants to become a coach for your team!\n\n"
                f"**Team:** {selected_team['team_name']} [{selected_team['team_tag']}]\n"
                f"**Applicant:** {interaction.user.mention} ({interaction.user.name})\n\n"
                "Any captain or manager can approve/decline this request."
            ),
            color=discord.Color.orange()
        )
        
        approval_view = CoachApprovalView(
            approver_ids=approver_ids,
            applicant_id=interaction.user.id,
            team_id=team_id,
            team_name=selected_team['team_name']
        )
        
        await interaction.followup.send(embed=approval_embed, view=approval_view)


class CoachApprovalView(discord.ui.View):
    """View with accept/decline buttons for captain and managers"""
    
    def __init__(self, approver_ids: list, applicant_id: int, team_id: int, team_name: str):
        super().__init__(timeout=300)
        self.approver_ids = approver_ids
        self.applicant_id = applicant_id
        self.team_id = team_id
        self.team_name = team_name
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept coach request"""
        if interaction.user.id not in self.approver_ids:
            await interaction.response.send_message(
                "❌ Only the team captain or managers can approve this request.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Add user as coach to team
            await db.add_team_member(
                team_id=self.team_id,
                discord_id=self.applicant_id,
                role='coach'
            )
            
            # Get team details for logging
            team = await db.get_team_by_id(self.team_id)
            
            # Assign team role to coach
            if team and team.get('role_id'):
                try:
                    role = interaction.guild.get_role(team['role_id'])
                    applicant = interaction.guild.get_member(self.applicant_id)
                    if role and applicant:
                        await applicant.add_roles(role)
                        print(f"✓ Assigned role {role.name} to coach {applicant.name}")
                except Exception as e:
                    print(f"✗ Failed to assign role: {e}")
            
            # Success message
            applicant = interaction.guild.get_member(self.applicant_id)
            success_embed = discord.Embed(
                title="✅ Coach Approved!",
                description=(
                    f"{applicant.mention} has been added as a coach for **{self.team_name}**!\n\n"
                    "The coach can now guide and train the team to victory!"
                ),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=False)
            
            # Log to bot logs channel
            await self.log_coach_addition(interaction, applicant, team)
            
            # Delete thread after 3 seconds
            await asyncio.sleep(3)
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            
        except Exception as e:
            print(f"Error adding coach: {e}")
            await interaction.followup.send(
                f"❌ Failed to add coach: {e}",
                ephemeral=False
            )
    
    async def log_coach_addition(self, interaction: discord.Interaction, applicant: discord.Member, team: dict):
        """Log coach addition to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="New Coach Added",
                description=(
                    f"**Team**\n{team['team_name']} [{team['team_tag']}]\n\n"
                    f"**Coach**\n{applicant.mention} ({applicant.name})\n\n"
                    f"**Approved By**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Team ID:** {team['id']} | **Coach ID:** {applicant.id} • "
                    f"<t:{int(interaction.created_at.timestamp())}:f>"
                ),
                color=0x5865F2,  # Discord blurple
                timestamp=interaction.created_at
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Coach addition logged: {applicant.name} to {team['team_name']}")
            
        except Exception as e:
            print(f"Error logging coach addition: {e}")
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline coach request"""
        if interaction.user.id not in self.approver_ids:
            await interaction.response.send_message(
                "❌ Only the team captain or managers can decline this request.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Decline message
        applicant = interaction.guild.get_member(self.applicant_id)
        decline_embed = discord.Embed(
            title="❌ Coach Request Declined",
            description=(
                f"Unfortunately, your request to coach **{self.team_name}** has been declined.\n\n"
                f"{applicant.mention}, you may apply to other teams."
            ),
            color=discord.Color.red()
        )
        decline_embed.set_footer(text="This thread will close in 3 seconds")
        
        await interaction.followup.send(embed=decline_embed, ephemeral=False)
        
        # Close thread after 3 seconds
        await asyncio.sleep(3)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()


class CoachRegistrationCog(commands.Cog):
    """Coach registration system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def create_registration_embed(self):
        """Create the coach registration embed message"""
        embed = discord.Embed(
            title="Coach Registration",
            description="Want to become a coach for a team? Click the button below to get started.",
            color=0x5865F2  # Discord blurple
        )
        
        embed.add_field(
            name="Requirements:",
            value=(
                "• The team must not have a coach yet (max 1 per team)\n"
                "• Team captain or existing manager must approve your request"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Process:",
            value=(
                "1. Click the Register button\n"
                "2. Select the team you want to coach\n"
                "3. Wait for captain/manager approval\n"
                "4. Get notified once approved"
            ),
            inline=False
        )
        
        embed.add_field(
            name="",
            value="**Coaches guide and train their teams to victory!**",
            inline=False
        )
        
        # Add logo if exists
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "LOGO.jpeg")
        if os.path.exists(logo_path):
            embed.set_thumbnail(url="attachment://LOGO.jpeg")
        
        return embed
    
    async def send_registration_message(self, channel_id: int):
        """Send the coach registration embed to the specified channel"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Channel with ID {channel_id} not found!")
                return
            
            # Purge old bot messages from the channel
            print(f"🧹 Purging old bot messages from {channel.name}...")
            deleted = await channel.purge(limit=100, check=lambda m: m.author == self.bot.user)
            print(f"✅ Deleted {len(deleted)} old bot message(s)")
            
            embed = self.create_registration_embed()
            view = CoachRegistrationButtons()
            
            # Load and attach logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "LOGO.jpeg")
            
            if os.path.exists(logo_path):
                file = discord.File(logo_path, filename="LOGO.jpeg")
                await channel.send(file=file, embed=embed, view=view)
                print(f"✅ Coach registration message sent to channel: {channel.name}")
            else:
                print(f"⚠️  Logo not found at {logo_path}, sending without logo")
                await channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"❌ Error sending coach registration message: {e}")


async def setup(bot):
    """Setup function for cog - registers persistent views"""
    cog = CoachRegistrationCog(bot)
    await bot.add_cog(cog)
    
    # Register persistent view so buttons work after bot restart
    bot.add_view(CoachRegistrationButtons())
    print("✓ Coach registration persistent view registered")
