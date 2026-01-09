import discord
from discord.ext import commands
from discord import app_commands
from utils import has_test_role

class PingCommand(commands.Cog):
    """Ping command to check bot latency"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Check bot latency and response time")
    @has_test_role()
    async def ping(self, interaction: discord.Interaction):
        """Shows the bot's latency in milliseconds"""
        # Get WebSocket latency
        latency_ms = round(self.bot.latency * 1000, 2)
        
        # Create embed for better formatting
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green(),
            description=f"Bot is responsive"
        )
        embed.add_field(name="WebSocket Latency", value=f"`{latency_ms}ms`", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PingCommand(bot))
