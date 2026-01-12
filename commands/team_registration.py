"""
Team Registration Command
Handles team registration with team details and logo upload
"""

import discord
from discord import app_commands
from discord.ext import commands
from database.db import db
from utils import has_test_role
import os
from datetime import datetime
import aiohttp
import asyncio


# Environment variables
TEAM_REGISTRATION_CHANNEL_ID = int(os.getenv("TEAM_REGISTRATION_CHANNEL_ID"))
BOT_LOGS_CHANNEL_ID = int(os.getenv("BOT_LOGS_CHANNEL_ID"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))
HEADMOD_ROLE_ID = int(os.getenv("HEADMOD_ROLE_ID"))
ADMINISTRATOR_ROLE_ID = int(os.getenv("ADMINISTRATOR_ROLE_ID"))


class TeamDetailsModal(discord.ui.Modal, title="Team Registration"):
    """Modal for entering team details"""
    
    team_name = discord.ui.TextInput(
        label="Team Name",
        placeholder="Enter your team name (e.g., Phoenix Strikers)",
        max_length=50,
        required=True
    )
    
    team_tag = discord.ui.TextInput(
        label="Team Tag",
        placeholder="Enter your team tag (e.g., PHX)",
        max_length=10,
        required=True
    )
    
    def __init__(self, user: discord.Member):
        super().__init__()
        self.user = user
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        await interaction.response.defer()
        
        team_name = self.team_name.value.strip()
        team_tag = self.team_tag.value.strip()
        
        # Check if team name already exists
        existing_team = await db.get_team_by_name(team_name)
        if existing_team:
            await interaction.followup.send(
                f"❌ **Team Name Already Taken**\n\n"
                f"A team with the name **{team_name}** already exists.\n"
                f"Please choose a different name.",
                ephemeral=True
            )
            return
        
        # Show region selection
        await interaction.followup.send(
            f"✓ Team details saved!\n\n"
            f"**Team Name:** {team_name}\n"
            f"**Team Tag:** {team_tag}\n\n"
            f"Now select your team's region:",
            view=TeamRegionSelectView(team_name, team_tag, self.user),
            ephemeral=False
        )


class TeamRegionSelectView(discord.ui.View):
    """View with region selection dropdown"""
    
    def __init__(self, team_name: str, team_tag: str, user: discord.Member):
        super().__init__(timeout=300)
        self.team_name = team_name
        self.team_tag = team_tag
        self.user = user
        self.add_item(TeamRegionSelect(team_name, team_tag, user))


class TeamRegionSelect(discord.ui.Select):
    """Dropdown for selecting team region"""
    
    def __init__(self, team_name: str, team_tag: str, user: discord.Member):
        self.team_name = team_name
        self.team_tag = team_tag
        self.user = user
        
        options = [
            discord.SelectOption(label="North America", value="NA", emoji="🇺🇸"),
            discord.SelectOption(label="Europe", value="EU", emoji="🇪🇺"),
            discord.SelectOption(label="Asia Pacific", value="AP", emoji="🌏"),
            discord.SelectOption(label="India", value="India", emoji="🇮🇳"),
            discord.SelectOption(label="Brazil", value="BR", emoji="🇧🇷"),
            discord.SelectOption(label="Latin America", value="LATAM", emoji="🌎"),
            discord.SelectOption(label="Korea", value="KR", emoji="🇰🇷"),
            discord.SelectOption(label="China", value="CN", emoji="🇨🇳"),
        ]
        
        super().__init__(
            placeholder="Select your team's region...",
            options=options,
            custom_id="team_region_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle region selection"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This selection is not for you!",
                ephemeral=True
            )
            return
        
        region = self.values[0]
        
        # Disable dropdown
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        
        # Ask for team logo
        await interaction.followup.send(
            f"✓ Region selected: **{region}**\n\n"
            f"**Final Step: Upload Team Logo**\n\n"
            f"Please upload your team logo as an image (PNG, JPG, JPEG).\n"
            f"The image will be saved as `{self.team_name}.png` on our server.\n\n"
            f"**Upload your logo in this thread now.**",
            ephemeral=False
        )
        
        # Wait for image upload
        await self.wait_for_logo_upload(interaction, region)
    
    async def wait_for_logo_upload(self, interaction: discord.Interaction, region: str):
        """Wait for user to upload team logo"""
        def check(message: discord.Message):
            return (
                message.author.id == self.user.id and
                message.channel.id == interaction.channel.id and
                len(message.attachments) > 0
            )
        
        try:
            # Wait for message with attachment (5 minutes timeout)
            msg = await interaction.client.wait_for('message', check=check, timeout=300.0)
            
            # Get first attachment
            attachment = msg.attachments[0]
            
            # Check if it's an image
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                await interaction.followup.send(
                    "❌ Please upload a valid image file (PNG, JPG, JPEG).",
                    ephemeral=True
                )
                return
            
            # Download and save the logo
            logo_saved = await self.download_logo(attachment, self.team_name)
            
            if not logo_saved:
                await interaction.followup.send(
                    "❌ Failed to save team logo. Please try again.",
                    ephemeral=True
                )
                return
            
            # Create team in database
            await self.create_team(interaction, region)
            
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ **Timeout**\n\n"
                "You didn't upload a logo within 5 minutes.\n"
                "Please start the registration process again.",
                ephemeral=True
            )
    
    async def download_logo(self, attachment: discord.Attachment, team_name: str) -> bool:
        """Download and save team logo"""
        try:
            # Create team logos directory if it doesn't exist
            logo_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GFX", "team_logos")
            os.makedirs(logo_dir, exist_ok=True)
            
            # Clean team name for filename (remove special characters)
            clean_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_name = clean_name.replace(' ', '_')
            
            # Save path
            file_path = os.path.join(logo_dir, f"{clean_name}.png")
            
            # Download and save
            await attachment.save(file_path)
            
            print(f"✅ Team logo saved: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving team logo: {e}")
            return False
    
    async def create_team(self, interaction: discord.Interaction, region: str):
        """Create team in database"""
        try:
            # Check if user is registered as a player
            player = await db.get_player_by_discord_id(self.user.id)
            if not player:
                await interaction.followup.send(
                    "❌ **Cannot Create Team**\n\n"
                    "You must be registered as a player to create a team.\n"
                    "Please register as a player first using the player registration.",
                    ephemeral=True
                )
                return
            
            # Create team with user as captain
            team = await db.create_team(
                team_name=self.team_name,
                captain_discord_id=self.user.id,
                region=region
            )
            
            # Add captain as player to team
            await db.add_team_member(
                team_id=team['id'],
                discord_id=self.user.id,
                role='player'
            )
            
            # Send success message
            await interaction.followup.send(
                f"🎉 **Team Created Successfully!**\n\n"
                f"**Team Name:** {self.team_name}\n"
                f"**Team Tag:** {self.team_tag}\n"
                f"**Region:** {region}\n"
                f"**Captain:** {self.user.mention}\n\n"
                f"**Team Composition:**\n"
                f"✓ 1/6 Players (You as captain)\n"
                f"• 0/2 Managers\n"
                f"• 0/1 Coach\n\n"
                f"You can now recruit players, managers, and a coach for your team!",
                ephemeral=False
            )
            
            # Log to bot-logs channel
            await self.log_team_creation(interaction.guild, team)
            
            # Close thread after 10 seconds
            await asyncio.sleep(10)
            try:
                await interaction.channel.send("Thread will close in 5 seconds...")
                await asyncio.sleep(5)
                await interaction.channel.delete()
            except:
                pass
            
        except Exception as e:
            print(f"❌ Error creating team: {e}")
            await interaction.followup.send(
                f"❌ Failed to create team: {e}",
                ephemeral=True
            )
    
    async def log_team_creation(self, guild: discord.Guild, team: dict):
        """Log team creation to bot-logs channel"""
        try:
            logs_channel = guild.get_channel(BOT_LOGS_CHANNEL_ID)
            if not logs_channel:
                return
            
            # Create embed
            embed = discord.Embed(
                title="New Team Registration (Thread - Manual)",
                description=(
                    f"**Team Name:** {self.team_name}\n"
                    f"**Team Tag:** {self.team_tag}\n"
                    f"**Region:** {team['region']}\n"
                    f"**Captain:** <@{self.user.id}>\n\n"
                    f"**Team ID:** {team['id']}\n"
                    f"**Method:** Manual\n"
                    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
                color=discord.Color.gold()
            )
            
            await logs_channel.send(embed=embed)
        except Exception as e:
            print(f"✗ Failed to log team creation: {e}")


class TeamRegistrationButtons(discord.ui.View):
    """Persistent view with team registration button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register Your Team",
        style=discord.ButtonStyle.primary,
        custom_id="register_team_button"
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle team registration button click"""
        # Defer the response immediately
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is registered as a player
        player = await db.get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.followup.send(
                "❌ **Cannot Register Team**\n\n"
                "You must be registered as a player to create a team.\n"
                "Please register as a player first using the player registration.",
                ephemeral=True
            )
            return
        
        # Check if user is already a captain
        existing_teams = await db.get_all_teams()
        for team in existing_teams:
            if team['captain_discord_id'] == interaction.user.id:
                await interaction.followup.send(
                    f"❌ **Already a Team Captain**\n\n"
                    f"You are already the captain of **{team['team_name']}**.\n"
                    f"Each player can only be a captain of one team.",
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
        
        # Send team composition info and button
        embed = discord.Embed(
            title="Team Registration",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                f"You are about to register a new team. You will become the **Team Captain**.\n\n"
                f"**Team Composition Requirements:**\n"
                f"✓ **6 Players** (including captain)\n"
                f"✓ **1-2 Managers** (optional)\n"
                f"✓ **1 Coach** (optional)\n\n"
                f"Click the button below to start the registration process."
            ),
            color=discord.Color.gold()
        )
        
        # Create a view with the register button
        view = discord.ui.View(timeout=300)
        
        async def modal_callback(modal_interaction: discord.Interaction):
            modal = TeamDetailsModal(interaction.user)
            await modal_interaction.response.send_modal(modal)
        
        register_btn = discord.ui.Button(
            label="Register Your Team",
            style=discord.ButtonStyle.success,
            emoji="🎮"
        )
        register_btn.callback = modal_callback
        view.add_item(register_btn)
        
        await thread.send(embed=embed, view=view)
        
        # Send confirmation
        await interaction.followup.send(
            f"✓ Registration thread created: {thread.mention}",
            ephemeral=True
        )


class TeamRegistrationCog(commands.Cog):
    """Team registration commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def create_team_registration_embed(self):
        """Create the team registration embed message"""
        embed = discord.Embed(
            title="Team Registration",
            description=(
                "Ready to create your VALORANT Mobile team? Click the button below to get started.\n\n"
                "**Requirements:**\n"
                "• Must be registered as a player\n"
                "• Team name must be unique\n"
                "• Team logo required (image file)\n\n"
                "**Team Composition:**\n"
                "• 6 Players (including captain)\n"
                "• 1-2 Managers (optional)\n"
                "• 1 Coach (optional)\n\n"
                "**You will become the team captain!**"
            ),
            color=discord.Color.gold()
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
                # Send the message with embed, logo, and buttons
                await channel.send(file=file, embed=embed, view=view)
                print(f"✅ Team registration message sent to channel: {channel.name}")
            else:
                print(f"⚠️  Logo not found at {logo_path}, sending without logo")
                await channel.send(embed=embed, view=view)
                print(f"✅ Team registration message sent to channel: {channel.name}")
            
        except Exception as e:
            print(f"❌ Error sending team registration message: {e}")
    
    @app_commands.command(name="setup_team_registration")
    @app_commands.describe(channel="The channel where the team registration UI will be posted")
    @has_test_role()
    async def setup_team_registration(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Setup the team registration UI in a channel (optional - auto-sent on startup)"""
        await interaction.response.defer(ephemeral=True)
        
        target_channel = channel or interaction.channel
        await self.send_team_registration_message(target_channel.id)
        
        await interaction.followup.send(
            f"✓ Team registration UI posted in {target_channel.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamRegistrationCog(bot))
