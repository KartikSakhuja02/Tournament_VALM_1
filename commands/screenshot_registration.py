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
from database.db import db


class RetryErrorView(discord.ui.View):
    """View with Restart and Cancel buttons for errors"""
    
    def __init__(self, user_id: int, cog):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.cog = cog
    
    @discord.ui.button(label="Restart", style=discord.ButtonStyle.primary)
    async def restart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Restart the registration process"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="Please send a clear screenshot of your profile showing your IGN and Player ID.",
            view=None
        )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the registration"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="Registration cancelled. You can start again by clicking the registration button in the registration channel.",
            view=None
        )
        
        # Delete thread after 5 seconds
        if isinstance(interaction.channel, discord.Thread):
            await asyncio.sleep(5)
            await interaction.channel.delete()


class OCRApprovalView(discord.ui.View):
    """View with Approve/Decline buttons after OCR scan"""
    
    def __init__(self, user_id: int, ign: str, player_id: str, cog):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        self.cog = cog
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the OCR results and proceed to region selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        # Show region selection
        region_view = RegionSelectionView(self.user_id, self.ign, self.player_id, self.cog, interaction.channel)
        await interaction.response.edit_message(
            content=f"Information Confirmed.\n\nIGN: `{self.ign}`\nID: `{self.player_id}`\n\nSelect your region:",
            view=region_view
        )
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline and ask to send screenshot again"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="OCR reading was incorrect.\n\nPlease send your profile screenshot again with:\n"
                    "- IGN (In-Game Name) clearly visible\n- Player ID visible\n- Good image quality\n\n"
                    "Send the screenshot now:",
            view=None
        )


class RegionSelectionView(discord.ui.View):
    """View with region dropdown"""
    
    def __init__(self, user_id: int, ign: str, player_id: str, cog, channel):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        self.cog = cog
        self.channel = channel
        
        # Add dropdown
        self.add_item(RegionDropdown(user_id, ign, player_id, cog, channel))


class RegionDropdown(discord.ui.Select):
    """Dropdown for region selection"""
    
    def __init__(self, user_id: int, ign: str, player_id: str, cog, channel):
        self.user_id = user_id
        self.ign = ign
        self.player_id = player_id
        self.cog = cog
        self.channel = channel
        
        options = [
            discord.SelectOption(label="North America (NA)", value="na"),
            discord.SelectOption(label="Europe (EU)", value="eu"),
            discord.SelectOption(label="Asia-Pacific (AP)", value="ap"),
            discord.SelectOption(label="Korea (KR)", value="kr"),
            discord.SelectOption(label="Brazil (BR)", value="br"),
            discord.SelectOption(label="Latin America (LATAM)", value="latam"),
            discord.SelectOption(label="Japan (JP)", value="jp"),
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
        
        region = self.values[0]
        
        await interaction.response.defer()
        
        # Register player in database
        try:
            # Check if already registered
            existing = await db.get_player_by_discord_id(self.user_id)
            if existing:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content=f"You are already registered.\n\nIGN: `{existing['ign']}`\nRegion: `{existing['region'].upper()}`",
                    view=None
                )
                await asyncio.sleep(5)
                if isinstance(self.channel, discord.Thread):
                    await self.channel.delete()
                return
            
            # Check if IGN is taken
            existing_ign = await db.get_player_by_ign(self.ign)
            if existing_ign:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content=f"IGN `{self.ign}` is already taken by another player.",
                    view=None
                )
                await asyncio.sleep(5)
                if isinstance(self.channel, discord.Thread):
                    await self.channel.delete()
                return
            
            # Create player
            player = await db.create_player(
                discord_id=self.user_id,
                ign=self.ign,
                player_id=self.player_id,
                region=region
            )
            
            # Create initial stats
            await db.create_player_stats(self.user_id)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=f"Registration Complete!\n\nIGN: `{self.ign}`\nID: `{self.player_id}`\nRegion: `{region.upper()}`\n\n"
                        f"You are now registered. Your stats will be tracked automatically.",
                view=None
            )
            
        except Exception as e:
            print(f"Database error during registration: {e}")
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=f"An error occurred during registration: {str(e)}",
                view=None
            )
        
        # Delete thread after 10 seconds
        await asyncio.sleep(10)
        if isinstance(self.channel, discord.Thread):
            await self.channel.delete()


class OCRFailureView(discord.ui.View):
    """View shown when OCR fails"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    @discord.ui.button(label="Try Manual Method", style=discord.ButtonStyle.primary)
    async def manual_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Switch to manual registration"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your registration.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="Please use the Manual Register button in the registration channel to continue.",
            view=None
        )
        
        # Delete thread after 5 seconds
        if isinstance(interaction.channel, discord.Thread):
            await asyncio.sleep(5)
            await interaction.channel.delete()


class ScreenshotRegistrationCog(commands.Cog):
    """Screenshot registration with OCR"""
    
    def __init__(self, bot):
        self.bot = bot
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.staff_role_id = int(os.getenv("STAFF_ROLE_ID", 0))
        self.pending_threads = {}  # {thread_id: {"user_id": int, "created_at": timestamp}}
    
    async def handle_screenshot_registration(self, interaction: discord.Interaction):
        """Create private thread for screenshot registration"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create private thread
            thread = await interaction.channel.create_thread(
                name=f"Registration - {interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60
            )
            
            # Add user to thread
            await thread.add_user(interaction.user)
            
            # Add staff members with delay to avoid rate limiting
            if self.staff_role_id:
                guild = interaction.guild
                staff_role = guild.get_role(self.staff_role_id)
                if staff_role:
                    for member in staff_role.members:
                        try:
                            await thread.add_user(member)
                            await asyncio.sleep(0.5)  # Small delay to avoid rate limits
                        except:
                            pass
            
            # Send instructions
            await thread.send(
                f"{interaction.user.mention}\n\n"
                f"Welcome to the registration process.\n\n"
                f"Please send a clear screenshot of your VALORANT profile showing:\n"
                f"- Your IGN (In-Game Name)\n"
                f"- Your Player ID\n"
                f"- Your Region\n\n"
                f"The bot will automatically read the information from your screenshot."
            )
            
            # Track thread for timeout
            self.pending_threads[thread.id] = {
                "user_id": interaction.user.id,
                "created_at": asyncio.get_event_loop().time(),
                "pinged_5min": False,
                "pinged_10min": False
            }
            
            # Start timeout task
            self.bot.loop.create_task(self.handle_thread_timeout(thread.id))
            
            await interaction.followup.send(
                f"Registration thread created: {thread.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error creating registration thread: {e}")
            await interaction.followup.send(
                "An error occurred while creating your registration thread. Please try again.",
                ephemeral=True
            )
    
    async def handle_thread_timeout(self, thread_id: int):
        """Handle thread timeout with pings"""
        await asyncio.sleep(300)  # 5 minutes
        
        if thread_id not in self.pending_threads:
            return
        
        thread = self.bot.get_channel(thread_id)
        if not thread:
            del self.pending_threads[thread_id]
            return
        
        # Check if user has sent any messages
        messages = [msg async for msg in thread.history(limit=10)]
        user_messages = [msg for msg in messages if msg.author.id == self.pending_threads[thread_id]["user_id"]]
        
        if len(user_messages) <= 0:
            # First ping at 5 minutes
            user = self.bot.get_user(self.pending_threads[thread_id]["user_id"])
            if user:
                await thread.send(f"{user.mention} Please send your profile screenshot to continue registration.")
                self.pending_threads[thread_id]["pinged_5min"] = True
            
            # Wait another 5 minutes
            await asyncio.sleep(300)
            
            if thread_id not in self.pending_threads:
                return
            
            # Check again
            messages = [msg async for msg in thread.history(limit=10)]
            user_messages = [msg for msg in messages if msg.author.id == self.pending_threads[thread_id]["user_id"]]
            
            if len(user_messages) <= 0:
                # Second ping at 10 minutes
                if user:
                    await thread.send(f"{user.mention} Last reminder: Please send your screenshot or the thread will be deleted.")
                    self.pending_threads[thread_id]["pinged_10min"] = True
                
                # Wait final 5 minutes
                await asyncio.sleep(300)
                
                if thread_id not in self.pending_threads:
                    return
                
                # Final check
                messages = [msg async for msg in thread.history(limit=10)]
                user_messages = [msg for msg in messages if msg.author.id == self.pending_threads[thread_id]["user_id"]]
                
                if len(user_messages) <= 0:
                    # Delete thread after 15 minutes
                    await thread.send("Registration cancelled due to inactivity. Thread will be deleted in 5 seconds.")
                    await asyncio.sleep(5)
                    await thread.delete()
                    del self.pending_threads[thread_id]
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages in registration threads"""
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only process messages in tracked threads
        if not isinstance(message.channel, discord.Thread):
            return
        
        if message.channel.id not in self.pending_threads:
            return
        
        # Check if message is from the user being registered
        if message.author.id != self.pending_threads[message.channel.id]["user_id"]:
            return
        
        # Check if message has attachments
        if not message.attachments:
            # User sent text instead of screenshot
            error_view = RetryErrorView(message.author.id, self)
            await message.channel.send(
                "Please send a screenshot image, not text.\n\nAttach your VALORANT profile screenshot.",
                view=error_view
            )
            return
        
        # Get the first attachment
        attachment = message.attachments[0]
        
        # Check if it's an image
        if not attachment.content_type or not attachment.content_type.startswith('image/'):
            error_view = RetryErrorView(message.author.id, self)
            await message.channel.send(
                "Please send an image file.\n\nSupported formats: PNG, JPG, JPEG",
                view=error_view
            )
            return
        
        # Process screenshot with OCR
        processing_msg = await message.channel.send("Reading your profile screenshot...")
        
        try:
            # Download image
            image_bytes = await attachment.read()
            
            # Run OCR
            ign, player_id = await self.extract_profile_info(image_bytes)
            
            if not ign or not player_id:
                # OCR failed
                await processing_msg.delete()
                ocr_fail_view = OCRFailureView(message.author.id)
                await message.channel.send(
                    "There is a problem with the OCR. Could not read your profile information.\n\n"
                    "Please try using the manual registration method instead.",
                    view=ocr_fail_view
                )
                return
            
            # Show OCR results with approve/decline
            await processing_msg.delete()
            approve_view = OCRApprovalView(message.author.id, ign, player_id, self)
            await message.channel.send(
                f"Successfully read your profile.\n\n"
                f"IGN: `{ign}`\n"
                f"Player ID: `{player_id}`\n\n"
                f"Is this information correct?",
                view=approve_view
            )
            
            # Remove from pending threads
            if message.channel.id in self.pending_threads:
                del self.pending_threads[message.channel.id]
            
        except Exception as e:
            print(f"OCR error: {e}")
            await processing_msg.delete()
            error_view = RetryErrorView(message.author.id, self)
            await message.channel.send(
                f"Error processing screenshot: {str(e)}\n\n"
                f"Please try again with a clearer screenshot.",
                view=error_view
            )
    
    async def extract_profile_info(self, image_bytes: bytes) -> tuple[str, str]:
        """Extract IGN and Player ID from screenshot using Gemini OCR"""
        
        if not self.gemini_api_key:
            return None, None
        
        try:
            # Convert image to base64
            img = Image.open(BytesIO(image_bytes))
            
            # Resize if too large
            max_size = 1600
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Gemini prompt
            prompt = """
You are reading a VALORANT Mobile player profile screenshot.

Extract the following information:
1. IGN (In-Game Name) - the player's username
2. Player ID - the numeric ID (format: 1234 or #1234)

Return RAW JSON ONLY (no markdown):
{
  "ign": "PlayerName",
  "id": "1234567"
}

Rules:
- Find the player's IGN (usually displayed prominently)
- Find the Player ID (numbers, may have # prefix)
- Remove # from ID if present
- If IGN not found, set to null
- If ID not found, set to null
"""
            
            # Try Gemini models
            models = [
                ("v1beta", "gemini-2.0-flash-exp"),
                ("v1beta", "gemini-exp-1206"),
                ("v1beta", "gemini-1.5-pro"),
            ]
            
            for version, model in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"
                    
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/png",
                                        "data": img_b64
                                    }
                                }
                            ]
                        }]
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            params={"key": self.gemini_api_key},
                            json=payload,
                            headers={"Content-Type": "application/json"}
                        ) as resp:
                            if resp.status != 200:
                                continue
                            
                            data = await resp.json()
                            text_response = data['candidates'][0]['content']['parts'][0]['text']
                            
                            # Parse JSON
                            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                            if json_match:
                                result = json.loads(json_match.group())
                                ign = result.get('ign')
                                player_id = result.get('id')
                                
                                # Clean up ID
                                if player_id:
                                    player_id = str(player_id).replace('#', '').strip()
                                
                                return ign, player_id
                
                except Exception as e:
                    print(f"OCR error with {model}: {e}")
                    continue
            
            return None, None
            
        except Exception as e:
            print(f"Image processing error: {e}")
            return None, None


async def setup(bot):
    await bot.add_cog(ScreenshotRegistrationCog(bot))
