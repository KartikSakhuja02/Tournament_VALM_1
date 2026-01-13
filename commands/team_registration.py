import discord
from discord.ext import commands
import os
import asyncio
from database.db import db


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
        placeholder="Enter your team tag (3-5 characters)",
        required=True,
        min_length=3,
        max_length=5,
        style=discord.TextStyle.short
    )
    
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
            team_tag=self.team_tag.value
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
    
    def __init__(self, user_id: int, team_name: str, team_tag: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        
        # Add region select menu
        self.add_item(TeamRegionSelect(user_id, team_name, team_tag))


class TeamRegionSelect(discord.ui.Select):
    """Dropdown for team region selection"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str):
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        
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
        
        # Get player's region
        player = await db.get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.followup.send(
                "❌ You must be registered as a player before creating a team.\n"
                "Please use the player registration first.",
                ephemeral=False
            )
            return
        
        player_region = player['region']
        
        # Check if regions match
        if player_region != selected_region:
            # Show region mismatch confirmation
            mismatch_view = RegionMismatchView(
                user_id=self.user_id,
                team_name=self.team_name,
                team_tag=self.team_tag,
                team_region=selected_region,
                player_region=player_region
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
        else:
            # Regions match, proceed to logo upload
            await self.show_logo_upload(interaction, selected_region)
    
    async def show_logo_upload(self, interaction: discord.Interaction, region: str):
        """Show logo upload instructions"""
        logo_view = TeamLogoUploadView(
            user_id=self.user_id,
            team_name=self.team_name,
            team_tag=self.team_tag,
            region=region
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
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, team_region: str, player_region: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.team_region = team_region
        self.player_region = player_region
    
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
            region=self.team_region
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


class TeamLogoUploadView(discord.ui.View):
    """View for team logo upload"""
    
    def __init__(self, user_id: int, team_name: str, team_tag: str, region: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.team_name = team_name
        self.team_tag = team_tag
        self.region = region
    
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
            region=self.region
        )
        await interaction.response.send_modal(modal)


class TeamLogoModal(discord.ui.Modal, title="Upload Team Logo"):
    """Modal for logo upload instructions"""
    
    logo_instruction = discord.ui.TextInput(
        label="Reply with your team logo",
        placeholder="After clicking Submit, send your logo image in the next message",
        required=True,
        style=discord.TextStyle.paragraph,
        default="I will upload the logo in the next message"
    )
    
    def __init__(self, team_name: str, team_tag: str, region: str):
        super().__init__()
        self.team_name = team_name
        self.team_tag = team_tag
        self.region = region
    
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
            
            logo_url = attachment.url
            
            # Create team in database
            team = await db.create_team(
                team_name=self.team_name,
                team_tag=self.team_tag,
                region=self.region,
                captain_discord_id=interaction.user.id,
                logo_url=logo_url
            )
            
            # Add captain as team member
            await db.add_team_member(
                team_id=team['id'],
                discord_id=interaction.user.id,
                role='captain'
            )
            
            # Success message
            success_embed = discord.Embed(
                title="✅ Team Registered Successfully!",
                description=(
                    f"**Team Name:** `{self.team_name}`\n"
                    f"**Team Tag:** `{self.team_tag}`\n"
                    f"**Region:** `{self.region}`\n"
                    f"**Captain:** {interaction.user.mention}\n\n"
                    "Your team has been created! You are now the team captain.\n"
                    "You can add players, managers, and coaches to your team."
                ),
                color=discord.Color.green()
            )
            success_embed.set_thumbnail(url=logo_url)
            
            await interaction.followup.send(embed=success_embed, ephemeral=False)
            
            # Log to bot logs channel
            await self.log_team_registration(
                interaction=interaction,
                team=team,
                logo_url=logo_url
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
    
    async def log_team_registration(self, interaction: discord.Interaction, team: dict, logo_url: str):
        """Log team registration to bot logs channel"""
        bot_logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
        if not bot_logs_channel_id:
            return
        
        try:
            channel = interaction.client.get_channel(int(bot_logs_channel_id))
            if not channel:
                return
            
            log_embed = discord.Embed(
                title="New Team Registration",
                description=(
                    f"**Team Name:** {team['team_name']}\n"
                    f"**Team Tag:** {team['team_tag']}\n"
                    f"**Region:** {team['region']}\n"
                    f"**Captain:** {interaction.user.mention} ({interaction.user.name})\n"
                    f"**Team ID:** {team['id']}\n"
                    f"**Registered:** <t:{int(team['created_at'].timestamp())}:F>"
                ),
                color=discord.Color.blue(),
                timestamp=team['created_at']
            )
            log_embed.set_thumbnail(url=logo_url)
            log_embed.set_footer(text=f"Captain ID: {interaction.user.id}")
            
            await channel.send(embed=log_embed)
            
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
        
        # Check if player is registered
        player = await db.get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.followup.send(
                "❌ You must be registered as a player before creating a team.\n"
                "Please use the player registration first.",
                ephemeral=True
            )
            return
        
        # Check if player already has a team
        existing_team = await db.get_team_by_captain(interaction.user.id)
        if existing_team:
            await interaction.followup.send(
                f"❌ You already have a team: **{existing_team['team_name']}** (`{existing_team['team_tag']}`)\n"
                "Each player can only captain one team.",
                ephemeral=True
            )
            return
        
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Team Registration - {interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60
            )
            
            # Add user to thread
            await thread.add_user(interaction.user)
            
            # Add administrators
            administrator_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
            if administrator_role_id:
                try:
                    admin_role = interaction.guild.get_role(int(administrator_role_id))
                    if admin_role:
                        print(f"Found {len(admin_role.members)} members with Administrator role")
                        for member in admin_role.members:
                            try:
                                await thread.add_user(member)
                                print(f"✓ Added Administrator: {member.name} to thread")
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"✗ Failed to add {member.name}: {e}")
                except Exception as e:
                    print(f"Error processing administrators: {e}")
            
            # Add head mods
            headmod_role_id = os.getenv("HEADMOD_ROLE_ID")
            if headmod_role_id:
                try:
                    headmod_role = interaction.guild.get_role(int(headmod_role_id))
                    if headmod_role:
                        print(f"Found {len(headmod_role.members)} members with Head Mod role")
                        for member in headmod_role.members:
                            try:
                                await thread.add_user(member)
                                print(f"✓ Added Head Mod: {member.name} to thread")
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"✗ Failed to add {member.name}: {e}")
                except Exception as e:
                    print(f"Error processing head mods: {e}")
            
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
                    "**Steps:**\n"
                    "1️⃣ Team Name & Tag\n"
                    "2️⃣ Select Region\n"
                    "3️⃣ Upload Team Logo\n\n"
                    "Click the button below to start!"
                ),
                color=discord.Color.blue()
            )
            
            start_view = discord.ui.View()
            start_button = discord.ui.Button(
                label="Start Registration",
                style=discord.ButtonStyle.primary
            )
            
            async def start_callback(button_interaction: discord.Interaction):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message(
                        "This is not your team registration.",
                        ephemeral=True
                    )
                    return
                
                # Show team name modal
                modal = TeamNameModal()
                await button_interaction.response.send_modal(modal)
            
            start_button.callback = start_callback
            start_view.add_item(start_button)
            
            await thread.send(embed=welcome_embed, view=start_view)
            
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
        
        # Captain note
        embed.add_field(
            name="",
            value="**You will become the team captain!**",
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
