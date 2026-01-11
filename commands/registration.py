import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import aiohttp
import base64
from io import BytesIO
from PIL import Image
import re
import json

class RegistrationButtons(discord.ui.View):
    """Persistent view with registration buttons"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.primary,
        custom_id="register"
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration button click"""
        await interaction.response.send_message(
            "Registration selected! (Functionality coming soon)",
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
            
            view = RegistrationButtons()
            
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
