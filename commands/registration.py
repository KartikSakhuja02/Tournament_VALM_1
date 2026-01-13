import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from database.db import db


class RegistrationModal(discord.ui.Modal, title="Player Registration"):
    """Modal form for player registration"""
    
    ign = discord.ui.TextInput(
        label="In-Game Name (IGN)",
        placeholder="Enter your VALORANT Mobile IGN",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )
    
    player_id = discord.ui.TextInput(
        label="Player ID",
        placeholder="Enter your Player ID (numbers only)",
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission - show region selector"""
        await interaction.response.defer()
        
        # Create region selection view
        region_view = RegionSelectView(
            user_id=interaction.user.id,
            ign=self.ign.value,
            player_id=self.player_id.value
        )
        
        embed = discord.Embed(
            title="Select Your Region",
            description=(
                f"**IGN:** `{self.ign.value}`\n"
                f"**Player ID:** `{self.player_id.value}`\n\n"
                "Please select your region from the dropdown menu below."
            ),
            color=0xFF4654
        )
        
        await interaction.followup.send(embed=embed, view=region_view)


class RegionSelectView(discord.ui.View):
    """View with region dropdown"""
    
    def __init__(self, user_id: int, ign: str, player_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        
        # Add region select menu
        self.add_item(RegionSelect(user_id, ign, player_id))


class RegionSelect(discord.ui.Select):
    """Dropdown for region selection"""
    
    def __init__(self, user_id: int, ign: str, player_id: str):
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        
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
            placeholder="Choose your region...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle region selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        selected_region = self.values[0]
        
        # Create consent embed
        embed = discord.Embed(
            title="Tournament Notifications & Terms",
            description=(
                "╔═══════════════════════════════════╗\n"
                "║  **VALORANT Mobile India Community**  ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "We organize **regular competitive tournaments** for the Indian VALORANT Mobile community.\n\n"
                "**What You'll Receive:**\n"
                "• Instant tournament announcements\n"
                "• Registration links & deadlines\n"
                "• Match schedules & brackets\n"
                "• Format details & prize information\n"
                "• Live updates during tournaments\n\n"
                "**By consenting, you agree to receive these notifications.**\n\n"
                "*Stay informed. Stay ready. Don't miss a tournament.*"
            ),
            color=0xFF4654  # VALORANT red
        )
        
        embed.set_footer(text="Please review and provide your consent below", icon_url="https://i.imgur.com/7lGjguC.png")
        
        # Show consent buttons
        consent_view = ConsentView(
            user_id=self.user_id,
            ign=self.ign,
            player_id=self.player_id,
            region=selected_region
        )
        
        await interaction.followup.send(embed=embed, view=consent_view)


class ConsentView(discord.ui.View):
    """View with consent buttons"""
    
    def __init__(self, user_id: int, ign: str, player_id: str, region: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        self.region = region
    
    @discord.ui.button(label="I Consent", style=discord.ButtonStyle.success)
    async def consent_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Save to database
        try:
            # Check if player already exists
            existing_player = await db.get_player_by_discord_id(interaction.user.id)
            
            if existing_player:
                await interaction.followup.send(
                    "You are already registered! You can only register once.",
                    ephemeral=False
                )
                await asyncio.sleep(3)
                if isinstance(interaction.channel, discord.Thread):
                    await interaction.channel.delete()
                return
            
            # Check if IGN is already taken
            existing_ign = await db.get_player_by_ign(self.ign)
            if existing_ign:
                await interaction.followup.send(
                    f"The IGN `{self.ign}` is already registered by another player. Please use a different IGN.",
                    ephemeral=False
                )
                return
            
            # Create player in database
            await db.create_player(
                discord_id=interaction.user.id,
                ign=self.ign,
                player_id=self.player_id,
                region=self.region,
                tournament_notifications=True
            )
            
            # Create player stats entry
            await db.create_player_stats(interaction.user.id)
            
            # Assign region role(s)
            roles_to_assign = []
            
            # Define role mappings
            role_mapping = {
                'NA': 'AMERICAS_ROLE_ID',
                'BR': 'AMERICAS_ROLE_ID',
                'LATAM': 'AMERICAS_ROLE_ID',
                'EU': 'EMEA_ROLE_ID',
                'India': 'INDIA_ROLE_ID',
                'AP': 'APAC_ROLE_ID',
                'KR': 'APAC_ROLE_ID',
                'CN': 'CN_ROLE_ID'
            }
            
            # Get the role ID for the selected region
            role_env_key = role_mapping.get(self.region)
            if role_env_key:
                role_id = os.getenv(role_env_key)
                if role_id:
                    roles_to_assign.append(int(role_id))
            
            # Special case: India also gets APAC role
            if self.region == 'India':
                apac_role_id = os.getenv('APAC_ROLE_ID')
                if apac_role_id:
                    roles_to_assign.append(int(apac_role_id))
            
            # Assign roles to the user
            assigned_roles = []
            if roles_to_assign:
                try:
                    member = interaction.guild.get_member(interaction.user.id)
                    if member:
                        for role_id in roles_to_assign:
                            role = interaction.guild.get_role(role_id)
                            if role:
                                await member.add_roles(role)
                                assigned_roles.append(role.name)
                                print(f"✓ Assigned role: {role.name} to {self.ign}")
                            else:
                                print(f"✗ Role with ID {role_id} not found")
                    else:
                        print(f"✗ Member not found: {interaction.user.id}")
                except Exception as e:
                    print(f"✗ Error assigning roles: {e}")
            
            print(f"✅ Player registered: {self.ign} (Discord ID: {interaction.user.id})")
            
            # Send log to bot-logs channel
            bot_logs_channel_id = os.getenv('BOT_LOGS_CHANNEL_ID')
            if bot_logs_channel_id:
                try:
                    logs_channel = interaction.guild.get_channel(int(bot_logs_channel_id))
                    if logs_channel:
                        # Format timestamp
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                        
                        log_embed = discord.Embed(
                            title="New Player Registration (Thread - Manual)",
                            description=(
                                f"**Player**\n"
                                f"{interaction.user.mention} ({interaction.user.name})\n\n"
                                f"**IGN                    Player ID                    Region**\n"
                                f"{self.ign}                    {self.player_id}                    {self.region}\n\n"
                                f"**User ID:** {interaction.user.id} • **Method:** Thread Manual • {timestamp}"
                            ),
                            color=0x5865F2
                        )
                        
                        log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                        
                        await logs_channel.send(embed=log_embed)
                        print(f"✓ Sent registration log to bot-logs channel")
                except Exception as e:
                    print(f"✗ Failed to send log to bot-logs channel: {e}")
            
        except Exception as e:
            print(f"❌ Database error during registration: {e}")
            await interaction.followup.send(
                "An error occurred while saving your registration. Please try again later.",
                ephemeral=False
            )
            return
        
        success_embed = discord.Embed(
            title="Registration Complete!",
            description=(
                f"**Welcome to the VALORANT Mobile India Community, {self.ign}!**\n\n"
                "Your registration has been successfully processed.\n"
                "You're all set for upcoming tournaments!\n\n"
                "══════════════════════════"
            ),
            color=0x00FF7F  # Spring green
        )
        
        success_embed.add_field(name="IGN", value=f"```{self.ign}```", inline=True)
        success_embed.add_field(name="Player ID", value=f"```{self.player_id}```", inline=True)
        success_embed.add_field(name="Region", value=f"```{self.region}```", inline=True)
        
        success_embed.add_field(
            name="What's Next?",
            value="You'll receive notifications for all upcoming tournaments. Good luck and have fun!",
            inline=False
        )
        
        success_embed.set_footer(text="Tournament notifications enabled | This thread will close in 5 seconds")
        
        await interaction.followup.send(embed=success_embed)
        
        # Close thread after 5 seconds
        await asyncio.sleep(5)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()
    
    @discord.ui.button(label="I Don't Consent", style=discord.ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle decline"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        decline_embed = discord.Embed(
            title="Registration Cancelled",
            description=(
                "You have declined to receive tournament notifications.\n\n"
                "No data has been saved.\n\n"
                "You can start over anytime by clicking the **Register** button in the registration channel."
            ),
            color=0x808080  # Grey
        )
        decline_embed.set_footer(text="This thread will close in 3 seconds")
        
        await interaction.response.send_message(embed=decline_embed, ephemeral=False)
        
        # Close thread after 3 seconds
        await asyncio.sleep(3)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()


class RegistrationButtons(discord.ui.View):
    """Persistent view with registration buttons"""
    
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.primary,
        custom_id="register"
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration button click"""
        # Respond immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is already registered
        existing_player = await db.get_player_by_discord_id(interaction.user.id)
        if existing_player:
            await interaction.followup.send(
                f"❌ You are already registered!\n"
                f"**IGN:** `{existing_player['ign']}`\n"
                f"**Region:** `{existing_player['region']}`\n\n"
                "If you need to update your information, please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Registration - {interaction.user.name}",
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
                    else:
                        print(f"Administrator role not found with ID: {administrator_role_id}")
                except Exception as e:
                    print(f"Error processing administrators: {e}")
            else:
                print("ADMINISTRATOR_ROLE_ID not set in .env")
            
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
                    else:
                        print(f"Head Mod role not found with ID: {headmod_role_id}")
                except Exception as e:
                    print(f"Error processing head mods: {e}")
            else:
                print("HEADMOD_ROLE_ID not set in .env")
            
            # Add staff members (if configured)
            staff_role_id = os.getenv("STAFF_ROLE_ID")
            if staff_role_id:
                try:
                    staff_role = interaction.guild.get_role(int(staff_role_id))
                    if staff_role:
                        for member in staff_role.members:
                            try:
                                await thread.add_user(member)
                                await asyncio.sleep(0.5)
                            except:
                                pass
                except:
                    pass
            
            # Send welcome message in thread
            welcome_embed = discord.Embed(
                title="Welcome to Registration!",
                description=(
                    f"Hey {interaction.user.mention}!\n\n"
                    "Thank you for your interest in joining the tournament.\n\n"
                    "Please click the button below to fill out the registration form."
                ),
                color=discord.Color.red()
            )
            welcome_embed.set_footer(text="Click 'Fill Form' to continue")
            
            # Create view with form button
            form_view = discord.ui.View(timeout=300)
            form_button = discord.ui.Button(
                label="Fill Form",
                style=discord.ButtonStyle.primary
            )
            
            async def form_callback(form_interaction: discord.Interaction):
                if form_interaction.user.id != interaction.user.id:
                    await form_interaction.response.send_message(
                        "This is not your registration.",
                        ephemeral=True
                    )
                    return
                
                # Show modal
                modal = RegistrationModal()
                await form_interaction.response.send_modal(modal)
            
            form_button.callback = form_callback
            form_view.add_item(form_button)
            
            await thread.send(embed=welcome_embed, view=form_view)
            
            # Respond to button click with followup (since we deferred)
            await interaction.followup.send(
                f"Registration thread created: {thread.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error creating registration thread: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    "An error occurred. Please try again later.",
                    ephemeral=True
                )
            except:
                # If followup also fails, the interaction already expired
                pass
    
    @discord.ui.button(
        label="Check Notification Status",
        style=discord.ButtonStyle.secondary,
        custom_id="check_status"
    )
    async def check_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Check user's notification status"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is registered
            player = await db.get_player_by_discord_id(interaction.user.id)
            
            if not player:
                # User not registered
                embed = discord.Embed(
                    title="Not Registered",
                    description=(
                        "You are not registered for tournaments yet.\n\n"
                        "Click the **Register** button to sign up and receive tournament notifications."
                    ),
                    color=0xFFA500  # Orange
                )
                embed.set_footer(text="Register now to stay updated!")
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            else:
                # User is registered - show status with toggle buttons
                is_enabled = player.get('tournament_notifications', False)
                
                if is_enabled:
                    embed = discord.Embed(
                        title="Notification Status: ACTIVE",
                        description=(
                            f"**IGN:** `{player['ign']}`\n"
                            f"**Player ID:** `{player['player_id']}`\n"
                            f"**Region:** `{player['region']}`\n\n"
                            "You will receive notifications for all upcoming tournaments.\n\n"
                            "Status: **ENABLED**"
                        ),
                        color=0x00FF7F  # Green
                    )
                    embed.set_footer(text=f"Registered on: {player['registered_at'].strftime('%B %d, %Y')}")
                else:
                    embed = discord.Embed(
                        title="Notification Status: INACTIVE",
                        description=(
                            f"**IGN:** `{player['ign']}`\n"
                            f"**Player ID:** `{player['player_id']}`\n"
                            f"**Region:** `{player['region']}`\n\n"
                            "You are registered but notifications are currently disabled.\n\n"
                            "Status: **DISABLED**"
                        ),
                        color=0xFF4654  # Red
                    )
                    embed.set_footer(text=f"Registered on: {player['registered_at'].strftime('%B %d, %Y')}")
                
                # Create toggle view
                toggle_view = NotificationToggleView(interaction.user.id, is_enabled)
                await interaction.followup.send(embed=embed, view=toggle_view, ephemeral=True)
            
        except Exception as e:
            print(f"Error checking notification status: {e}")
            await interaction.followup.send(
                "An error occurred while checking your status. Please try again later.",
                ephemeral=True
            )


class NotificationToggleView(discord.ui.View):
    """View with notification toggle buttons"""
    
    def __init__(self, user_id: int, current_status: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.current_status = current_status
    
    @discord.ui.button(label="Enable Notifications", style=discord.ButtonStyle.success)
    async def enable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable tournament notifications"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your status panel.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Update database
            await db.update_player(
                discord_id=interaction.user.id,
                tournament_notifications=True
            )
            
            success_embed = discord.Embed(
                title="Notifications Enabled",
                description=(
                    "Tournament notifications have been enabled successfully!\n\n"
                    "You will now receive updates about all upcoming tournaments."
                ),
                color=0x00FF7F  # Green
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            print(f"✓ Notifications enabled for user {interaction.user.id}")
            
        except Exception as e:
            print(f"Error enabling notifications: {e}")
            await interaction.followup.send(
                "An error occurred. Please try again later.",
                ephemeral=True
            )
    
    @discord.ui.button(label="Disable Notifications", style=discord.ButtonStyle.danger)
    async def disable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Disable tournament notifications"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your status panel.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Update database
            await db.update_player(
                discord_id=interaction.user.id,
                tournament_notifications=False
            )
            
            warning_embed = discord.Embed(
                title="Notifications Disabled",
                description=(
                    "Tournament notifications have been disabled.\n\n"
                    "You will no longer receive updates about upcoming tournaments.\n\n"
                    "You can re-enable them anytime by using the **Check Notification Status** button."
                ),
                color=0xFF4654  # Red
            )
            
            await interaction.followup.send(embed=warning_embed, ephemeral=True)
            print(f"✓ Notifications disabled for user {interaction.user.id}")
            
        except Exception as e:
            print(f"Error disabling notifications: {e}")
            await interaction.followup.send(
                "An error occurred. Please try again later.",
                ephemeral=True
            )

class RegistrationCog(commands.Cog):
    """Player registration system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def create_registration_embed(self):
        """Create the registration embed message"""
        embed = discord.Embed(
            title="VALORANT Tournament Registration",
            description="Welcome to the Bot! Click the button below to register for the tournament.",
            color=discord.Color.red()  # VALORANT red theme
        )
        
        embed.add_field(
            name="Registration Requirements",
            value="• IGN (In-Game Name)\n• Player ID\n• Region",
            inline=False
        )
        
        embed.set_footer(text="Click the button below to start registration")
        
        return embed
    
    async def send_registration_message(self, channel_id: int):
        """Send the registration embed to the specified channel"""
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
            
            view = RegistrationButtons(self)
            
            # Load and attach logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "LOGO.jpeg")
            
            if os.path.exists(logo_path):
                file = discord.File(logo_path, filename="LOGO.jpeg")
                embed.set_thumbnail(url="attachment://LOGO.jpeg")
                # Send the message with embed, logo, and buttons
                await channel.send(file=file, embed=embed, view=view)
                print(f"✅ Registration message sent to channel: {channel.name}")
            else:
                print(f"⚠️  Logo not found at {logo_path}, sending without logo")
                await channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"❌ Error sending registration message: {e}")

async def setup(bot):
    """Setup function for cog - registers persistent views"""
    cog = RegistrationCog(bot)
    await bot.add_cog(cog)
    
    # Register persistent view so buttons work after bot restart
    bot.add_view(RegistrationButtons(cog))
    print("✓ Registration persistent view registered")
