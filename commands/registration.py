import discord
from discord.ext import commands
from discord import app_commands

class RegistrationButtons(discord.ui.View):
    """Persistent view with registration buttons"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent buttons (no timeout)
    
    @discord.ui.button(
        label="📸 Screenshot Register",
        style=discord.ButtonStyle.primary,
        custom_id="screenshot_register"
    )
    async def screenshot_register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle screenshot registration button click"""
        await interaction.response.send_message(
            "📸 Screenshot registration selected! (Functionality coming soon)",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="✍️ Manual Register",
        style=discord.ButtonStyle.secondary,
        custom_id="manual_register"
    )
    async def manual_register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle manual registration button click"""
        await interaction.response.send_message(
            "✍️ Manual registration selected! (Functionality coming soon)",
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
            description="Welcome to the Regional Scrim Tournament! Register your team using one of the options below:",
            color=discord.Color.red()  # VALORANT red theme
        )
        
        embed.add_field(
            name="📸 Screenshot Register",
            value="Upload a screenshot of your team details for quick registration",
            inline=False
        )
        
        embed.add_field(
            name="✍️ Manual Register",
            value="Manually enter your team information step by step",
            inline=False
        )
        
        embed.add_field(
            name="📋 Requirements",
            value="• Team Name\n• 5 Players + 1 Substitute\n• Valid IGNs\n• Discord Tags",
            inline=False
        )
        
        embed.set_footer(text="Click a button below to start registration")
        embed.set_thumbnail(url="https://i.imgur.com/YZ4w2ey.png")  # VALORANT logo (example)
        
        return embed
    
    async def send_registration_message(self, channel_id: int):
        """Send the registration embed to the specified channel"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Channel with ID {channel_id} not found!")
                return
            
            embed = self.create_registration_embed()
            view = RegistrationButtons()
            
            # Send the message with embed and buttons
            await channel.send(embed=embed, view=view)
            print(f"✅ Registration message sent to channel: {channel.name}")
            
        except Exception as e:
            print(f"❌ Error sending registration message: {e}")

async def setup(bot):
    await bot.add_cog(RegistrationCog(bot))
