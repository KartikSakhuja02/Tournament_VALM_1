import discord
from discord import app_commands
from discord.ext import commands
import os
from datetime import datetime
from typing import Optional
from database.db import db


class EditFieldSelect(discord.ui.Select):
    """Dropdown for selecting which field to edit."""
    
    def __init__(self, player_data: dict, target_user: discord.User):
        self.player_data = player_data
        self.target_user = target_user
        
        # Create options for each editable field
        options = [
            discord.SelectOption(
                label="In-Game Name",
                value="in_game_name",
                description=f"Current: {player_data['in_game_name']}",
                emoji="🎮"
            ),
            discord.SelectOption(
                label="Team Name",
                value="team_name",
                description=f"Current: {player_data['team_name']}",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Tracker.gg Link",
                value="trackergg_link",
                description=f"Current: {player_data['trackergg_link'][:50]}..." if len(player_data['trackergg_link']) > 50 else f"Current: {player_data['trackergg_link']}",
                emoji="🔗"
            ),
            discord.SelectOption(
                label="Valorant Rank",
                value="valorant_rank",
                description=f"Current: {player_data['valorant_rank']}",
                emoji="⭐"
            )
        ]
        
        super().__init__(
            placeholder="Select a field to edit...",
            options=options,
            custom_id="edit_field_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        field = self.values[0]
        print(f"🔧 Admin editing field: {field} for user {self.target_user.id}")
        
        # Show modal for new value
        modal = EditValueModal(
            field=field,
            current_value=self.player_data[field],
            player_data=self.player_data,
            target_user=self.target_user
        )
        await interaction.response.send_modal(modal)
        print(f"✓ Modal sent for field: {field}")


class EditFieldView(discord.ui.View):
    """View containing the field selection dropdown."""
    
    def __init__(self, player_data: dict, target_user: discord.User):
        super().__init__(timeout=300)
        self.add_item(EditFieldSelect(player_data, target_user))
    
    async def on_timeout(self):
        # Disable all items when view times out
        for item in self.children:
            item.disabled = True


class EditValueModal(discord.ui.Modal):
    """Modal for entering the new value for a field."""
    
    def __init__(self, field: str, current_value: str, player_data: dict, target_user: discord.User):
        self.field = field
        self.player_data = player_data
        self.target_user = target_user
        
        # Map field names to user-friendly labels
        field_labels = {
            "in_game_name": "In-Game Name",
            "team_name": "Team Name",
            "trackergg_link": "Tracker.gg Link",
            "valorant_rank": "Valorant Rank"
        }
        
        super().__init__(title=f"Edit {field_labels[field]}")
        
        # Add text input with current value as placeholder
        self.new_value_input = discord.ui.TextInput(
            label=f"New {field_labels[field]}",
            placeholder=current_value,
            default=current_value,
            required=True,
            max_length=500 if field == "trackergg_link" else 100
        )
        self.add_item(self.new_value_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.new_value_input.value.strip()
        print(f"📝 Modal submitted - Field: {self.field}, New value: {new_value}")
        
        # Defer the response since database operation might take time
        await interaction.response.defer(ephemeral=True)
        print(f"✓ Modal response deferred")
        
        print(f"✓ Database connection obtained")
        
        try:
            # Whitelist valid field names to prevent SQL injection
            valid_fields = ["in_game_name", "team_name", "trackergg_link", "valorant_rank"]
            if self.field not in valid_fields:
                raise ValueError(f"Invalid field: {self.field}")
            
            # Update the player's field in database
            query = f"UPDATE players SET {self.field} = $1 WHERE discord_id = $2"
            await db.pool.execute(query, new_value, str(self.target_user.id))
            print(f"✓ Database updated successfully")
            
            # Field labels for logging
            field_labels = {
                "in_game_name": "In-Game Name",
                "team_name": "Team Name",
                "trackergg_link": "Tracker.gg Link",
                "valorant_rank": "Valorant Rank"
            }
            
            # Send confirmation to admin
            embed = discord.Embed(
                title="✅ Player Updated Successfully",
                description=f"Updated {self.target_user.mention}'s registration",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Field",
                value=field_labels[self.field],
                inline=True
            )
            embed.add_field(
                name="Old Value",
                value=self.player_data[self.field],
                inline=True
            )
            embed.add_field(
                name="New Value",
                value=new_value,
                inline=True
            )
            embed.set_footer(text=f"Edited by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Confirmation sent to admin")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="🛠️ Admin: Player Registration Edited",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Player",
                        value=f"{self.target_user.mention} (`{self.target_user.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Field Edited",
                        value=field_labels[self.field],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Old Value",
                        value=self.player_data[self.field],
                        inline=False
                    )
                    log_embed.add_field(
                        name="New Value",
                        value=new_value,
                        inline=False
                    )
                    log_embed.set_footer(text=f"Admin: {interaction.user.display_name} ({interaction.user.id})")
                    
                    await logs_channel.send(embed=log_embed)
            
            # Send DM to player about the change
            try:
                dm_embed = discord.Embed(
                    title="📝 Registration Updated",
                    description="An administrator has updated your tournament registration.",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(
                    name="Field Updated",
                    value=field_labels[self.field],
                    inline=True
                )
                dm_embed.add_field(
                    name="Previous Value",
                    value=self.player_data[self.field],
                    inline=False
                )
                dm_embed.add_field(
                    name="New Value",
                    value=new_value,
                    inline=False
                )
                dm_embed.set_footer(text="If you believe this was done in error, please contact an administrator.")
                
                await self.target_user.send(embed=dm_embed)
            except discord.Forbidden:
                # Player has DMs disabled, that's okay
                pass
        
        except Exception as e:
            # Send error message to admin
            error_embed = discord.Embed(
                title="❌ Error Updating Player",
                description=f"Failed to update player registration: {str(e)}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            # Log error with full traceback
            import traceback
            print(f"❌ Error updating player {self.target_user.id}:")
            print(traceback.format_exc())


class Admin(commands.Cog):
    """Admin commands for managing the tournament."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(
        name="admin-edit-player",
        description="[ADMIN] Edit a player's registration details"
    )
    @app_commands.describe(
        player="The player whose registration you want to edit"
    )
    async def admin_edit_player(
        self,
        interaction: discord.Interaction,
        player: discord.User
    ):
        """Edit a registered player's details."""
        
        # Check if user has administrator role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        if not admin_role_id:
            await interaction.response.send_message(
                "❌ Administrator role is not configured.",
                ephemeral=True
            )
            return
        
        admin_role = interaction.guild.get_role(int(admin_role_id))
        if not admin_role or admin_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators can edit player registrations.",
                ephemeral=True
            )
            return
        
        # Defer response since we're doing database operations
        await interaction.response.defer(ephemeral=True)
        print(f"🔍 Admin checking player: {player.id}")
        
        # Check if the target player is registered
        player_data = await db.pool.fetchrow(
            "SELECT * FROM players WHERE discord_id = $1",
            str(player.id)
        )
        
        if not player_data:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"{player.mention} is not registered for the tournament.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Convert row to dict for easier access
        player_dict = dict(player_data)
        
        # Show current player info and field selection
        info_embed = discord.Embed(
            title="📋 Current Player Registration",
            description=f"Editing registration for {player.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        info_embed.add_field(
            name="🎮 In-Game Name",
            value=player_dict['in_game_name'],
            inline=True
        )
        info_embed.add_field(
            name="👥 Team Name",
            value=player_dict['team_name'],
            inline=True
        )
        info_embed.add_field(
            name="⭐ Rank",
            value=player_dict['valorant_rank'],
            inline=True
        )
        info_embed.add_field(
            name="🔗 Tracker.gg Link",
            value=player_dict['trackergg_link'],
            inline=False
        )
        info_embed.add_field(
            name="📅 Registration Date",
            value=player_dict['registration_date'].strftime("%Y-%m-%d %H:%M UTC"),
            inline=True
        )
        info_embed.set_footer(text="Select a field below to edit")
        
        # Create view with field selection dropdown
        view = EditFieldView(player_dict, player)
        
        await interaction.followup.send(
            embed=info_embed,
            view=view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Load the Admin cog."""
    await bot.add_cog(Admin(bot))
    print("✓ Admin cog loaded")
