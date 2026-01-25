import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from pathlib import Path
from database.db import db
from utils.thread_manager import add_staff_to_thread
from commands.registration import inactivity_warning_task, cancel_inactivity_warning, _active_threads


class TeamRoleSelectView(discord.ui.View):
    """View to select role (Manager or Captain)"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    @discord.ui.button(label="I'm a Captain (Player)", style=discord.ButtonStyle.primary)
    async def captain_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """User selects captain role"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        # Cancel inactivity warning since user is now interacting
        if isinstance(interaction.channel, discord.Thread):
            cancel_inactivity_warning(interaction.channel.id)
        
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
        
        # Check if user is registered as a player
        player = await db.get_player_by_discord_id(interaction.user.id)
        if not player:
            # Get registration channel ID from env
            registration_channel_id = os.getenv('REGISTRATION_CHANNEL_ID')
            registration_mention = f"<#{registration_channel_id}>" if registration_channel_id else "the player registration channel"
            
            embed = discord.Embed(
                title="❌ Player Registration Required",
                description=(
                    "To create a team as a **Captain**, you must be registered as a player first.\n\n"
                    f"Please go to {registration_mention} and register yourself as a player, then come back to create your team.\n\n"
                    "**Note:** If you want to create a team without being a player, select **I'm a Manager** instead."
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text="This thread will be deleted in 5 seconds")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
            # Delete thread after 5 seconds
            await asyncio.sleep(5)
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            return
        
        # Show team name modal with captain role
        modal = TeamNameModal(user_role='captain')
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="I'm a Manager", style=discord.ButtonStyle.secondary)
    async def manager_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """User selects manager role"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        # Cancel inactivity warning since user is now interacting
        if isinstance(interaction.channel, discord.Thread):
            cancel_inactivity_warning(interaction.channel.id)
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
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
        
        # Show team name modal with manager role
        modal = TeamNameModal(user_role='manager')
        await interaction.response.send_modal(modal)


class TeamNameModal(discord.ui.Modal, title="Team Registration - Step 1"):
    """Modal for team name and tag input"""
    
    team_name = discord.ui.TextInput(
        label="Team Name",
        placeholder="Enter your team name (must be unique)",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )
    
    team_tag = discord.ui.TextInput(
        label="Team Tag",
        placeholder="Enter your team tag (2-5 characters)",
        required=True,
        min_length=2,
        max_length=5,
        style=discord.TextStyle.short
    )
    
    def __init__(self, user_role: str):
        super().__init__()
        self.user_role = user_role  # 'captain' or 'manager'
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission - show region selector"""
        await interaction.response.defer()
        
        # Validate team name doesn't exist
        existing_team = await db.get_team_by_name(self.team_name.value)
        if existing_team:
            await interaction.followup.send(
                f"❌ Team name `{self.team_name.value}` is already taken. Please choose a different name.",
                ephemeral=False
            )
            return
        
        # Validate team tag doesn't exist
        existing_tag = await db.get_team_by_tag(self.team_tag.value)
        if existing_tag:
            await interaction.followup.send(
                f"❌ Team tag `{self.team_tag.value}` is already taken. Please choose a different tag.",
                ephemeral=False
            )
            return
        
        # Create region selection view
        region_view = TeamRegionSelectView(
            user_id=interaction.user.id,
            team_name=self.team_name.value,
            team_tag=self.team_tag.value,
            user_role=self.user_role
        )
        
        embed = discord.Embed(
            title="Select Team Region",
            description=(
                f"**Team Name:** `{self.team_name.value}`\n"
                f"**Team Tag:** `{self.team_tag.value}`\n\n"
                "Please select your team's region from the dropdown menu below."
            ),
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=region_view)


class TeamRegionSelectView(discord.ui.View):
    """View with team region dropdown"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, user_role: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.user_role = user_role
        
        # Add region select menu
        self.add_item(TeamRegionSelect(user_id, team_name, team_tag, user_role))


class TeamRegionSelect(discord.ui.Select):
    """Dropdown for team region selection"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, user_role: str):
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.user_role = user_role
        
        options = [
            discord.SelectOption(label="North America (NA)", value="NA"),
            discord.SelectOption(label="Europe (EU)", value="EU"),
            discord.SelectOption(label="Asia-Pacific (AP)", value="AP"),
            discord.SelectOption(label="India", value="India"),
            discord.SelectOption(label="Brazil (BR)", value="BR"),
            discord.SelectOption(label="Latin America (LATAM)", value="LATAM"),
            discord.SelectOption(label="Korea (KR)", value="KR"),
            discord.SelectOption(label="China (CN)", value="CN")
        ]
        
        super().__init__(
            placeholder="Choose your team's region...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle team region selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        selected_region = self.values[0]
        
        # If user is captain, check player region match
        if self.user_role == 'captain':
            # Get player's region
            player = await db.get_player_by_discord_id(interaction.user.id)
            if not player:
                await interaction.followup.send(
                    "❌ You must be registered as a player before creating a team as captain.\n"
                    "Please use the player registration first.",
                    ephemeral=False
                )
                return
            
            player_region = player['region']
            
            # Check if regions match (India and AP are considered the same)
            regions_match = (player_region == selected_region) or \
                           (player_region == 'India' and selected_region == 'AP') or \
                           (player_region == 'AP' and selected_region == 'India')
            
            if not regions_match:
                # Show region mismatch confirmation
                mismatch_view = RegionMismatchView(
                    user_id=self.user_id,
                    team_name=self.team_name,
                    team_tag=self.team_tag,
                    team_region=selected_region,
                    player_region=player_region,
                    user_role=self.user_role
                )
                
                embed = discord.Embed(
                    title="⚠️ Region Mismatch Detected",
                    description=(
                        f"**Your Player Region:** `{player_region}`\n"
                        f"**Team Region Selected:** `{selected_region}`\n\n"
                        "You chose a different region for your team than your player registration. "
                        "This means you will be playing for a team from a different region.\n\n"
                        "**Do you want to proceed?**"
                    ),
                    color=discord.Color.orange()
                )
                
                await interaction.followup.send(embed=embed, view=mismatch_view)
                return
        
        # Proceed to logo upload (for managers or captains with matching regions)
        await self.show_logo_upload(interaction, selected_region)
    
    async def show_logo_upload(self, interaction: discord.Interaction, region: str):
        """Show logo upload instructions"""
        logo_view = TeamLogoUploadView(
            user_id=self.user_id,
            team_name=self.team_name,
            team_tag=self.team_tag,
            region=region,
            user_role=self.user_role
        )
        
        embed = discord.Embed(
            title="Upload Team Logo",
            description=(
                f"**Team Name:** `{self.team_name}`\n"
                f"**Team Tag:** `{self.team_tag}`\n"
                f"**Region:** `{region}`\n\n"
                "Please upload your team logo by clicking the button below and attaching an image.\n\n"
                "**Requirements:**\n"
                "• Must be an image file (PNG, JPG, JPEG, GIF)\n"
                "• Recommended size: 512x512 pixels\n"
                "• Maximum file size: 8MB"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=logo_view)


class RegionMismatchView(discord.ui.View):
    """View with accept/decline buttons for region mismatch"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, team_region: str, player_region: str, user_role: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.team_region = team_region
        self.player_region = player_region
        self.user_role = user_role
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept playing for a team from different region"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Proceed to logo upload
        logo_view = TeamLogoUploadView(
            user_id=self.user_id,
            team_name=self.team_name,
            team_tag=self.team_tag,
            region=self.team_region,
            user_role=self.user_role
        )
        
        embed = discord.Embed(
            title="Upload Team Logo",
            description=(
                f"**Team Name:** `{self.team_name}`\n"
                f"**Team Tag:** `{self.team_tag}`\n"
                f"**Region:** `{self.team_region}`\n\n"
                "Please upload your team logo by clicking the button below and attaching an image.\n\n"
                "**Requirements:**\n"
                "• Must be an image file (PNG, JPG, JPEG, GIF)\n"
                "• Recommended size: 512x512 pixels\n"
                "• Maximum file size: 8MB"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=logo_view)
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline and cancel registration"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Team registration cancelled. You can start over by clicking the **Register Your Team** button again.",
            ephemeral=False
        )
        
        # Delete thread after 3 seconds
        await asyncio.sleep(3)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()


class TeamLogoUploadView(discord.ui.View):
    """View for team logo upload"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, region: str, user_role: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.region = region
        self.user_role = user_role
    
    @discord.ui.button(label="Upload Logo", style=discord.ButtonStyle.primary)
    async def upload_logo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show logo upload modal"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        # Show modal to collect logo message
        modal = TeamLogoModal(
            team_name=self.team_name,
            team_tag=self.team_tag,
            region=self.region,
            user_role=self.user_role
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Skip Logo", style=discord.ButtonStyle.secondary)
    async def skip_logo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip logo upload and complete registration"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your team registration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create Discord role for the team
        try:
            team_role = await interaction.guild.create_role(
                name=self.team_name,
                color=discord.Color.blue(),
                mentionable=True,
                reason=f"Team role created for {self.team_name}"
            )
            print(f"✓ Created role {team_role.name} (ID: {team_role.id})")
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to create team role: {e}",
                ephemeral=False
            )
            return
        
        # Create team in database without logo
        team = await db.create_team(
            team_name=self.team_name,
            team_tag=self.team_tag,
            region=self.region,
            captain_discord_id=interaction.user.id,
            logo_url=None,  # No logo
            role_id=team_role.id  # Store the role ID
        )
        
        # Add user as team member with their selected role
        await db.add_team_member(
            team_id=team['id'],
            discord_id=interaction.user.id,
            role=self.user_role  # 'captain' or 'manager'
        )
        
        # Assign the team role and captain/manager role to the user
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                # Assign team role
                await member.add_roles(team_role)
                print(f"✓ Assigned team role {team_role.name} to {member.name}")
                
                # Assign captain or manager role
                role_env_key = 'CAPTAIN_ROLE_ID' if self.user_role == 'captain' else 'MANAGER_ROLE_ID'
                position_role_id = os.getenv(role_env_key)
                if position_role_id:
                    position_role = interaction.guild.get_role(int(position_role_id))
                    if position_role:
                        await member.add_roles(position_role)
                        print(f"✓ Assigned {self.user_role} role to {member.name}")
        except Exception as e:
            print(f"✗ Failed to assign role: {e}")
        
        # Determine role display text
        role_text = "team captain" if self.user_role == "captain" else "team manager"
        
        # Success message without logo
        success_embed = discord.Embed(
            title="✅ Team Registered Successfully!",
            description=(
                f"**Team Name:** `{self.team_name}`\n"
                f"**Team Tag:** `{self.team_tag}`\n"
                f"**Region:** `{self.region}`\n"
                f"**Your Role:** {role_text.title()}\n\n"
                f"Your team has been created! You are now the {role_text}.\n"
                "You can add players, managers, and coaches to your team.\n\n"
                "You can add a logo later by contacting an administrator."
            ),
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=success_embed, ephemeral=False)
        
        # Log to bot logs channel (without logo)
        await self.log_team_registration_no_logo(interaction, team, role_text)
        
        # Close thread after 5 seconds
        await asyncio.sleep(5)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()
    
    async def log_team_registration_no_logo(self, interaction: discord.Interaction, team: dict, role_text: str):
        """Log team registration to bot logs channel without logo"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="New Team Registered (Thread)",
                description=(
                    f"**Team Name**\n{team['team_name']}\n\n"
                    f"**Tag**\n[{team['team_tag']}]\n\n"
                    f"**Region**\n{team['region']}\n\n"
                    f"**{role_text.title()}**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Logo**\nNot uploaded\n\n"
                    f"**Team ID:** {team['id']} | **Captain ID:** {interaction.user.id} • **Method:** Thread • "
                    f"<t:{int(team['created_at'].timestamp())}:f>"
                ),
                color=0x5865F2,  # Discord blurple
                timestamp=team['created_at']
            )
            
            await channel.send(embed=log_embed)
            print(f"✓ Team registration logged (no logo)")
            
        except Exception as e:
            print(f"Error logging team registration: {e}")


class TeamLogoModal(discord.ui.Modal, title="Upload Team Logo"):
    """Modal for logo upload instructions"""
    
    logo_instruction = discord.ui.TextInput(
        label="Reply with your team logo",
        placeholder="After clicking Submit, send your logo image in the next message",
        required=True,
        style=discord.TextStyle.paragraph,
        default="I will upload the logo in the next message"
    )
    
    def __init__(self, team_name: str, team_tag: str, region: str, user_role: str):
        super().__init__()
        self.team_name = team_name
        self.team_tag = team_tag
        self.region = region
        self.user_role = user_role  # 'captain' or 'manager'
    
    async def on_submit(self, interaction: discord.Interaction):
        """Wait for logo upload"""
        await interaction.response.send_message(
            "✅ Please send your team logo as an image attachment in this thread now.\n"
            "**You have 60 seconds to upload the logo.**",
            ephemeral=False
        )
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and
                   len(m.attachments) > 0)
        
        try:
            msg = await interaction.client.wait_for('message', timeout=60.0, check=check)
            
            # Get the first attachment
            attachment = msg.attachments[0]
            
            # Check if it's an image
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                await interaction.followup.send(
                    "❌ Please upload a valid image file (PNG, JPG, JPEG, GIF).",
                    ephemeral=False
                )
                return
            
            # Download and save logo locally
            logo_dir = Path(__file__).parent.parent / "team_logos"
            logo_dir.mkdir(exist_ok=True)
            
            # Sanitize team name for filename (remove special characters)
            safe_team_name = "".join(c for c in self.team_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_team_name = safe_team_name.replace(' ', '_')
            logo_filename = f"{safe_team_name}.png"
            logo_path = logo_dir / logo_filename
            
            # Download the image
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            with open(logo_path, 'wb') as f:
                                f.write(await resp.read())
                            print(f"✓ Downloaded team logo: {logo_path}")
                        else:
                            raise Exception(f"Failed to download image: HTTP {resp.status}")
            except Exception as e:
                print(f"Error downloading logo: {e}")
                await interaction.followup.send(
                    f"❌ Failed to download logo: {e}\nPlease try again.",
                    ephemeral=False
                )
                return
            
            logo_url = attachment.url
            local_logo_path = str(logo_path)
            
            # Create Discord role for the team
            try:
                team_role = await interaction.guild.create_role(
                    name=self.team_name,
                    color=discord.Color.blue(),
                    mentionable=True,
                    reason=f"Team role created for {self.team_name}"
                )
                print(f"✓ Created role {team_role.name} (ID: {team_role.id})")
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Failed to create team role: {e}",
                    ephemeral=False
                )
                return
            
            # Create team in database
            team = await db.create_team(
                team_name=self.team_name,
                team_tag=self.team_tag,
                region=self.region,
                captain_discord_id=interaction.user.id,
                logo_url=local_logo_path,  # Store local path instead of Discord URL
                role_id=team_role.id  # Store the role ID
            )
            
            # Add user as team member with their selected role
            await db.add_team_member(
                team_id=team['id'],
                discord_id=interaction.user.id,
                role=self.user_role  # 'captain' or 'manager'
            )
            
            # Assign the team role and captain/manager role to the user
            try:
                member = interaction.guild.get_member(interaction.user.id)
                if member:
                    # Assign team role
                    await member.add_roles(team_role)
                    print(f"✓ Assigned team role {team_role.name} to {member.name}")
                    
                    # Assign captain or manager role
                    role_env_key = 'CAPTAIN_ROLE_ID' if self.user_role == 'captain' else 'MANAGER_ROLE_ID'
                    position_role_id = os.getenv(role_env_key)
                    if position_role_id:
                        position_role = interaction.guild.get_role(int(position_role_id))
                        if position_role:
                            await member.add_roles(position_role)
                            print(f"✓ Assigned {self.user_role} role to {member.name}")
            except Exception as e:
                print(f"✗ Failed to assign role: {e}")
            
            # Determine role display text
            role_text = "team captain" if self.user_role == "captain" else "team manager"
            
            # Success message with local logo file
            success_embed = discord.Embed(
                title="✅ Team Registered Successfully!",
                description=(
                    f"**Team Name:** `{self.team_name}`\n"
                    f"**Team Tag:** `{self.team_tag}`\n"
                    f"**Region:** `{self.region}`\n"
                    f"**Your Role:** {role_text.title()}\n\n"
                    f"Your team has been created! You are now the {role_text}.\n"
                    "You can add players, managers, and coaches to your team."
                ),
                color=discord.Color.green()
            )
            
            # Attach the downloaded logo file
            logo_file = discord.File(logo_path, filename=logo_filename)
            success_embed.set_thumbnail(url=f"attachment://{logo_filename}")
            
            await interaction.followup.send(embed=success_embed, file=logo_file, ephemeral=False)
            
            # Log to bot logs channel
            await self.log_team_registration(
                interaction=interaction,
                team=team,
                logo_path=logo_path
            )
            
            # Close thread after 5 seconds
            await asyncio.sleep(5)
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ Time's up! You didn't upload a logo within 60 seconds.\n"
                "Please start the registration process again.",
                ephemeral=False
            )
    
    async def log_team_registration(self, interaction: discord.Interaction, team: dict, logo_path: Path):
        """Log team registration to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            # Check if logo file exists
            if not logo_path.exists():
                print(f"⚠️ Logo file not found: {logo_path}")
                return
            
            log_embed = discord.Embed(
                title="New Team Registered (Thread)",
                description=(
                    f"**Team Name**\n{team['team_name']}\n\n"
                    f"**Tag**\n[{team['team_tag']}]\n\n"
                    f"**Region**\n{team['region']}\n\n"
                    f"**Captain**\n{interaction.user.mention} ({interaction.user.name})\n\n"
                    f"**Logo**\n[View Logo](attachment://{logo_path.name})\n\n"
                    f"**Team ID:** {team['id']} | **Captain ID:** {interaction.user.id} • **Method:** Thread • "
                    f"<t:{int(team['created_at'].timestamp())}:f>"
                ),
                color=0x5865F2,  # Discord blurple
                timestamp=team['created_at']
            )
            
            # Attach the local logo file
            logo_file = discord.File(logo_path, filename=logo_path.name)
            log_embed.set_thumbnail(url=f"attachment://{logo_path.name}")
            
            await channel.send(embed=log_embed, file=logo_file)
            print(f"✓ Team registration logged with logo: {logo_path.name}")
            
        except Exception as e:
            print(f"Error logging team registration: {e}")


class TeamRegistrationButtons(discord.ui.View):
    """Persistent view with team registration button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register Your Team",
        style=discord.ButtonStyle.primary,
        custom_id="register_team"
    )
    async def register_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle team registration button click"""
        # Respond immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Team Registration - {interaction.user.name}",
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
            
            # Send welcome message in thread
            welcome_embed = discord.Embed(
                title="Welcome to Team Registration!",
                description=(
                    f"Hello {interaction.user.mention}!\n\n"
                    "Let's create your VALORANT Mobile team. "
                    "I'll guide you through the process.\n\n"
                    "**First, select your role in the team:**"
                ),
                color=discord.Color.blue()
            )
            
            role_view = TeamRoleSelectView(interaction.user.id)
            
            await thread.send(embed=welcome_embed, view=role_view)
            
            # Start inactivity warning task
            task = asyncio.create_task(inactivity_warning_task(thread, interaction.user.id))
            _active_threads[thread.id] = {
                'task': task,
                'target_user_id': interaction.user.id
            }
            print(f"✓ Started inactivity monitoring for team thread {thread.id}")
            
        except Exception as e:
            print(f"Error creating team registration thread: {e}")
            await interaction.followup.send(
                f"❌ Failed to create registration thread: {e}",
                ephemeral=True
            )


class TeamRegistrationCog(commands.Cog):
    """Team registration system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def create_team_registration_embed(self):
        """Create the team registration embed message"""
        embed = discord.Embed(
            title="Team Registration",
            description="Ready to create your VALORANT Mobile team? Click the button below to get started.",
            color=discord.Color.blue()
        )
        
        # Requirements section
        embed.add_field(
            name="Requirements:",
            value=(
                "• Must be registered as a player\n"
                "• Team name must be unique\n"
                "• Team logo required (image file)"
            ),
            inline=False
        )
        
        # Team Composition section
        embed.add_field(
            name="Team Composition:",
            value=(
                "• 6 Players (including captain)\n"
                "• 1-2 Managers (optional)\n"
                "• 1 Coach (optional)"
            ),
            inline=False
        )
        
        # Team Management section
        embed.add_field(
            name="Team Management Features:",
            value=(
                "**As Captain, you can:**\n"
                "• Invite players to your team (`/invite-player`)\n"
                "• Kick players from your team (`/kick-player`)\n"
                "• Transfer captainship (`/transfer-captain`)\n"
                "• Approve/Reject manager and coach applications\n"
                "• Disband the team (`/disband-team`)\n\n"
                "**As Manager, you can:**\n"
                "• Invite players to the team (`/invite-player`)\n"
                "• Register players for the team (`/register-player`)\n"
                "• Leave the team (`/leave-team`)\n\n"
                "**All team members can:**\n"
                "• View team profile (`/team-profile`)\n"
                "• Leave the team anytime (`/leave-team`)\n"
                "• Receive a unique team role automatically"
            ),
            inline=False
        )
        
        # Captain note
        embed.add_field(
            name="",
            value="**You will become the team captain or manager upon creation!**",
            inline=False
        )
        
        return embed
    
    async def send_team_registration_message(self, channel_id: int):
        """Send the team registration embed to the specified channel"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Channel with ID {channel_id} not found!")
                return
            
            # Purge old bot messages from the channel
            print(f"🧹 Purging old bot messages from {channel.name}...")
            deleted = await channel.purge(limit=100, check=lambda m: m.author == self.bot.user)
            print(f"✅ Deleted {len(deleted)} old bot message(s)")
            
            embed = self.create_team_registration_embed()
            view = TeamRegistrationButtons()
            
            # Load and attach logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "LOGO.jpeg")
            
            if os.path.exists(logo_path):
                file = discord.File(logo_path, filename="LOGO.jpeg")
                embed.set_thumbnail(url="attachment://LOGO.jpeg")
                await channel.send(file=file, embed=embed, view=view)
                print(f"✅ Team registration message sent to channel: {channel.name}")
            else:
                print(f"⚠️  Logo not found at {logo_path}, sending without logo")
                await channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"❌ Error sending team registration message: {e}")


async def setup(bot):
    """Setup function for cog - registers persistent views"""
    cog = TeamRegistrationCog(bot)
    await bot.add_cog(cog)
    
    # Register persistent view so buttons work after bot restart
    bot.add_view(TeamRegistrationButtons())
    print("✓ Team registration persistent view registered")
