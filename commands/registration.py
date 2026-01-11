import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from database.db import db


class RegistrationModal(discord.ui.Modal, title="🎮 Player Registration"):
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
    
    region = discord.ui.TextInput(
        label="Region",
        placeholder="Enter your region (e.g., Asia, EU, NA)",
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        await interaction.response.defer()
        
        # Create consent embed
        embed = discord.Embed(
            title="📢 Tournament Notifications",
            description=(
                "**Valorant Mobile India Community Tournaments**\n\n"
                "We organize regular competitive Valorant Mobile tournaments for the Indian community.\n\n"
                "Any tournament hosted by the Valorant Mobile India Community will be automatically "
                "notified to you and your team through this bot.\n\n"
                "You'll receive instant alerts with complete details, including registration links, "
                "match schedules, formats, and important updates.\n\n"
                "**Stay informed. Stay ready. Don't miss a tournament.**"
            ),
            color=discord.Color.gold()
        )
        
        embed.set_footer(text="Please provide your consent to continue")
        
        # Show consent buttons
        consent_view = ConsentView(
            user_id=interaction.user.id,
            ign=self.ign.value,
            player_id=self.player_id.value,
            region=self.region.value
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
    
    @discord.ui.button(label="I Consent", style=discord.ButtonStyle.success, emoji="✅")
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
                    "❌ You are already registered! You can only register once.",
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
                    f"❌ The IGN `{self.ign}` is already registered by another player. Please use a different IGN.",
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
            
            print(f"✅ Player registered: {self.ign} (Discord ID: {interaction.user.id})")
            
        except Exception as e:
            print(f"❌ Database error during registration: {e}")
            await interaction.followup.send(
                "❌ An error occurred while saving your registration. Please try again later.",
                ephemeral=False
            )
            return
        
        success_embed = discord.Embed(
            title="✅ Registration Successful!",
            description=f"Welcome to the tournament, **{self.ign}**!",
            color=discord.Color.green()
        )
        
        success_embed.add_field(name="IGN", value=self.ign, inline=True)
        success_embed.add_field(name="Player ID", value=self.player_id, inline=True)
        success_embed.add_field(name="Region", value=self.region, inline=True)
        
        success_embed.set_footer(text="You will receive tournament notifications • Good luck!")
        
        await interaction.followup.send(embed=success_embed)
        
        # Close thread after 5 seconds
        await asyncio.sleep(5)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete()
    
    @discord.ui.button(label="I Don't Consent", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle decline"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Registration cancelled. You can start over anytime by clicking the Register button again.",
            ephemeral=False
        )
        
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
        custom_id="register",
        emoji="📝"
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration button click"""
        # Create private thread
        try:
            thread = await interaction.channel.create_thread(
                name=f"Registration - {interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60
            )
            
            # Add user to thread
            await thread.add_user(interaction.user)
            
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
                title="🎮 Welcome to Registration!",
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
                style=discord.ButtonStyle.primary,
                emoji="📋"
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
            
            # Respond to button click
            await interaction.response.send_message(
                f"Registration thread created: {thread.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error creating registration thread: {e}")
            await interaction.response.send_message(
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
            title="🎮 VALORANT Tournament Registration",
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
    await bot.add_cog(RegistrationCog(bot))
