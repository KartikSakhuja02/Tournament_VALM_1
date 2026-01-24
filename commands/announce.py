import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class AnnouncementTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Registration Open",
                value="registration_open",
                description="Announce that player/team registration is now open",
                emoji="📝"
            ),
            discord.SelectOption(
                label="Tournament Start",
                value="tournament_start",
                description="Announce the tournament is starting soon",
                emoji="🏆"
            ),
            discord.SelectOption(
                label="Match Scheduled",
                value="match_scheduled",
                description="Announce upcoming match schedules",
                emoji="⏰"
            ),
            discord.SelectOption(
                label="Results Announcement",
                value="results",
                description="Announce match results or winners",
                emoji="🎯"
            ),
            discord.SelectOption(
                label="General Announcement",
                value="general",
                description="Custom announcement for any purpose",
                emoji="📢"
            )
        ]
        super().__init__(
            placeholder="Select announcement type...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        announcement_type = self.values[0]
        
        # Get pre-filled template based on type
        templates = {
            "registration_open": (
                "🎮 **REGISTRATION NOW OPEN!** 🎮\n\n"
                "The registration for our VALORANT tournament is officially open!\n\n"
                "📝 **How to Register:**\n"
                "• Use `/register` to register as a player\n"
                "• Use `/team-register` to register your team\n\n"
                "⏰ **Registration Deadline:** [Add date here]\n\n"
                "Don't miss your chance to compete! Register now! 🔥"
            ),
            "tournament_start": (
                "🏆 **TOURNAMENT BEGINS!** 🏆\n\n"
                "The tournament is officially starting!\n\n"
                "📅 **Start Date:** [Add date and time]\n"
                "🎯 **Format:** [Add format details]\n"
                "📺 **Stream:** [Add stream link if any]\n\n"
                "Good luck to all participating teams! May the best team win! 💪"
            ),
            "match_scheduled": (
                "⏰ **MATCH SCHEDULE ANNOUNCEMENT** ⏰\n\n"
                "📋 **Match Details:**\n"
                "• **Teams:** [Team 1] vs [Team 2]\n"
                "• **Date:** [Add date]\n"
                "• **Time:** [Add time]\n"
                "• **Map:** [Add map if known]\n\n"
                "Make sure both teams are ready! ⚔️"
            ),
            "results": (
                "🎯 **MATCH RESULTS** 🎯\n\n"
                "📊 **Final Score:**\n"
                "• **Winner:** [Team Name] 🏆\n"
                "• **Score:** [Score]\n\n"
                "🌟 **MVP:** [Player Name]\n\n"
                "Congratulations to the winning team! GG! 🎉"
            ),
            "general": (
                "📢 **ANNOUNCEMENT** 📢\n\n"
                "[Write your announcement here]\n\n"
                "Thank you for your attention!"
            )
        }
        
        template = templates.get(announcement_type, templates["general"])
        
        # Show modal with the template
        modal = AnnouncementModal(template, self.view.target_channel)
        await interaction.response.send_modal(modal)


class AnnouncementTypeView(discord.ui.View):
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.target_channel = target_channel
        self.add_item(AnnouncementTypeSelect())


class AnnouncementModal(discord.ui.Modal, title="Create Announcement"):
    def __init__(self, template: str, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel
        
        self.message_input = discord.ui.TextInput(
            label="Announcement Message",
            style=discord.TextStyle.paragraph,
            placeholder="Edit the template below or write your own...",
            default=template,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        message_content = self.message_input.value
        
        # Show role selection view
        view = RoleSelectionView(message_content, self.target_channel)
        
        embed = discord.Embed(
            title="Select Roles to Ping",
            description="Choose which roles should be mentioned in this announcement.\nSelect 'None' if you don't want to ping anyone.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RoleSelectionView(discord.ui.View):
    def __init__(self, message_content: str, target_channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.target_channel = target_channel
        self.add_item(RoleSelectDropdown())
    
    @discord.ui.button(label="Continue to Preview", style=discord.ButtonStyle.primary, row=1)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get selected roles from dropdown
        role_select = None
        for item in self.children:
            if isinstance(item, RoleSelectDropdown):
                role_select = item
                break
        
        selected_role_ids = role_select.values if role_select and role_select.values else []
        
        # Build role mentions
        role_mentions = ""
        if selected_role_ids and selected_role_ids[0] != "none":
            roles = [interaction.guild.get_role(int(role_id)) for role_id in selected_role_ids]
            role_mentions = " ".join([role.mention for role in roles if role]) + "\n\n"
        
        full_message = role_mentions + self.message_content
        
        # Show preview
        preview_view = PreviewView(full_message, self.target_channel)
        
        preview_embed = discord.Embed(
            title="📋 Announcement Preview",
            description=f"**Channel:** {self.target_channel.mention}\n\n**Message:**\n{full_message}",
            color=discord.Color.gold()
        )
        preview_embed.set_footer(text="Review your announcement before sending")
        
        await interaction.response.edit_message(embed=preview_embed, view=preview_view)


class RoleSelectDropdown(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select roles to ping...",
            min_values=1,
            max_values=5,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Just acknowledge the selection
        await interaction.response.defer()


class PreviewView(discord.ui.View):
    def __init__(self, message_content: str, target_channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.target_channel = target_channel
    
    @discord.ui.button(label="✅ Send Announcement", style=discord.ButtonStyle.success)
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Send the announcement to target channel
            await self.target_channel.send(self.message_content)
            
            success_embed = discord.Embed(
                title="✅ Announcement Sent!",
                description=f"Your announcement has been posted in {self.target_channel.mention}",
                color=discord.Color.green()
            )
            
            await interaction.response.edit_message(embed=success_embed, view=None)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to send announcement: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=error_embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="Announcement Cancelled",
            description="The announcement was not sent.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=cancel_embed, view=None)


class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="announce", description="Create and send an announcement")
    @app_commands.describe(channel="Channel to send announcement (defaults to current channel)")
    async def announce(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        # Check if user has Administrator permission or Bots role
        if not interaction.user.guild_permissions.administrator:
            bots_role = discord.utils.get(interaction.guild.roles, name="Bots")
            if not bots_role or bots_role not in interaction.user.roles:
                await interaction.response.send_message(
                    "❌ You need Administrator permission or the Bots role to use this command.",
                    ephemeral=True
                )
                return
        
        target_channel = channel or interaction.channel
        
        # Check if bot has permissions in target channel
        permissions = target_channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {target_channel.mention}",
                ephemeral=True
            )
            return
        
        view = AnnouncementTypeView(target_channel)
        
        embed = discord.Embed(
            title="📢 Create Announcement",
            description=f"Select the type of announcement you want to create.\n\n**Target Channel:** {target_channel.mention}",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    # Monkey patch to populate roles dynamically when view is created
    original_init = RoleSelectionView.__init__
    
    def new_init(self, message_content: str, target_channel: discord.TextChannel):
        original_init(self, message_content, target_channel)
        
        # Populate roles from guild
        guild = target_channel.guild
        options = [discord.SelectOption(label="None (No ping)", value="none", emoji="🚫")]
        
        for role in guild.roles:
            if role.name != "@everyone" and not role.managed and len(options) < 25:
                options.append(
                    discord.SelectOption(
                        label=role.name,
                        value=str(role.id),
                        emoji="📌"
                    )
                )
        
        # Update dropdown options
        for item in self.children:
            if isinstance(item, RoleSelectDropdown):
                item.options = options
                break
    
    RoleSelectionView.__init__ = new_init
    
    await bot.add_cog(Announce(bot))
