import discord
from discord.ext import commands
import os


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
        await interaction.response.send_message(
            "Team registration functionality coming soon!",
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
    await bot.add_cog(TeamRegistrationCog(bot))
