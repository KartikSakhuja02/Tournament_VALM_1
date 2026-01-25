import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
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
                label="In-Game Name (IGN)",
                value="ign",
                description=f"Current: {player_data['ign']}",
                emoji="🎮"
            ),
            discord.SelectOption(
                label="Player ID",
                value="player_id",
                description=f"Current: {player_data['player_id']}",
                emoji="🔢"
            ),
            discord.SelectOption(
                label="Region",
                value="region",
                description=f"Current: {player_data['region']}",
                emoji="🌍"
            ),
            discord.SelectOption(
                label="Agent",
                value="agent",
                description=f"Current: {player_data['agent'] or 'Not set'}",
                emoji="🎯"
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
            "ign": "In-Game Name (IGN)",
            "player_id": "Player ID",
            "region": "Region",
            "agent": "Agent"
        }
        
        super().__init__(title=f"Edit {field_labels[field]}")
        
        # Add text input with current value as placeholder
        self.new_value_input = discord.ui.TextInput(
            label=f"New {field_labels[field]}",
            placeholder=current_value,
            default=current_value,
            required=True,
            max_length=100
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
            valid_fields = ["ign", "player_id", "region", "agent"]
            if self.field not in valid_fields:
                raise ValueError(f"Invalid field: {self.field}")
            
            # Update the player's field in database
            query = f"UPDATE players SET {self.field} = $1 WHERE discord_id = $2"
            await db.pool.execute(query, new_value, self.target_user.id)
            print(f"✓ Database updated successfully")
            
            # Field labels for logging
            field_labels = {
                "ign": "In-Game Name (IGN)",
                "player_id": "Player ID",
                "region": "Region",
                "agent": "Agent"
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
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can edit player registrations.",
                ephemeral=True
            )
            return
        
        # Defer response since we're doing database operations
        await interaction.response.defer(ephemeral=True)
        print(f"🔍 Admin checking player: {player.id}")
        
        # Check if the target player is registered
        player_data = await db.pool.fetchrow(
            "SELECT * FROM players WHERE discord_id = $1",
            player.id
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
            name="🎮 In-Game Name (IGN)",
            value=player_dict['ign'],
            inline=True
        )
        info_embed.add_field(
            name="🔢 Player ID",
            value=player_dict['player_id'],
            inline=True
        )
        info_embed.add_field(
            name="🌍 Region",
            value=player_dict['region'],
            inline=True
        )
        info_embed.add_field(
            name="🎯 Agent",
            value=player_dict['agent'] or 'Not set',
            inline=True
        )
        info_embed.add_field(
            name="📅 Registration Date",
            value=player_dict['registered_at'].strftime("%Y-%m-%d %H:%M UTC"),
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
    
    @app_commands.command(
        name="admin-ban-player",
        description="[ADMIN] Ban a player from registering for the tournament"
    )
    @app_commands.describe(
        player="The player to ban",
        reason="Reason for the ban (optional)"
    )
    async def admin_ban_player(
        self,
        interaction: discord.Interaction,
        player: discord.User,
        reason: Optional[str] = None
    ):
        """Ban a player from tournament registration."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can ban players.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"🚫 Admin banning player: {player.id}")
        
        # Check if player is already banned
        ban_info = await db.is_player_banned(player.id)
        if ban_info:
            embed = discord.Embed(
                title="⚠️ Player Already Banned",
                description=f"{player.mention} is already banned from the tournament.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Previously Banned By",
                value=f"<@{ban_info['banned_by']}>",
                inline=True
            )
            embed.add_field(
                name="Previous Ban Date",
                value=ban_info['banned_at'].strftime("%Y-%m-%d %H:%M UTC"),
                inline=True
            )
            if ban_info['reason']:
                embed.add_field(
                    name="Previous Reason",
                    value=ban_info['reason'],
                    inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Ban the player
        success = await db.ban_player(player.id, interaction.user.id, reason)
        
        if success:
            # Send confirmation to admin
            embed = discord.Embed(
                title="🚫 Player Banned",
                description=f"Successfully banned {player.mention} from tournament registration.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Banned User",
                value=f"{player.mention} (`{player.id}`)",
                inline=True
            )
            embed.add_field(
                name="Banned By",
                value=interaction.user.mention,
                inline=True
            )
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
            embed.set_footer(text="This player cannot register as player or team")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Player {player.id} banned successfully")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="🚫 Admin: Player Banned",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Banned Player",
                        value=f"{player.mention} (`{player.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Banned By",
                        value=f"{interaction.user.mention} (`{interaction.user.id}`)",
                        inline=False
                    )
                    if reason:
                        log_embed.add_field(
                            name="Reason",
                            value=reason,
                            inline=False
                        )
                    
                    await logs_channel.send(embed=log_embed)
            
            # Try to DM the player
            try:
                dm_embed = discord.Embed(
                    title="🚫 Tournament Ban",
                    description="You have been banned from participating in the VALORANT Mobile India Tournament.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                if reason:
                    dm_embed.add_field(
                        name="Reason",
                        value=reason,
                        inline=False
                    )
                dm_embed.set_footer(text="If you believe this is an error, please contact the tournament administrators.")
                
                await player.send(embed=dm_embed)
            except discord.Forbidden:
                # Player has DMs disabled
                pass
        else:
            # Error occurred
            error_embed = discord.Embed(
                title="❌ Error Banning Player",
                description="Failed to ban the player. Please try again.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"❌ Failed to ban player {player.id}")
    
    @app_commands.command(
        name="admin-unban-player",
        description="[ADMIN] Unban a player and allow them to register again"
    )
    @app_commands.describe(
        player="The player to unban"
    )
    async def admin_unban_player(
        self,
        interaction: discord.Interaction,
        player: discord.User
    ):
        """Unban a player and restore their registration privileges."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can unban players.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"✅ Admin unbanning player: {player.id}")
        
        # Check if player is actually banned
        ban_info = await db.is_player_banned(player.id)
        if not ban_info:
            embed = discord.Embed(
                title="⚠️ Player Not Banned",
                description=f"{player.mention} is not currently banned.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Unban the player
        success = await db.unban_player(player.id)
        
        if success:
            # Send confirmation to admin
            embed = discord.Embed(
                title="✅ Player Unbanned",
                description=f"Successfully unbanned {player.mention}. They can now register for the tournament.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Unbanned User",
                value=f"{player.mention} (`{player.id}`)",
                inline=True
            )
            embed.add_field(
                name="Unbanned By",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="Originally Banned By",
                value=f"<@{ban_info['banned_by']}>",
                inline=True
            )
            if ban_info['reason']:
                embed.add_field(
                    name="Original Ban Reason",
                    value=ban_info['reason'],
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Player {player.id} unbanned successfully")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="✅ Admin: Player Unbanned",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Unbanned Player",
                        value=f"{player.mention} (`{player.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Unbanned By",
                        value=f"{interaction.user.mention} (`{interaction.user.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Originally Banned By",
                        value=f"<@{ban_info['banned_by']}>",
                        inline=False
                    )
                    if ban_info['reason']:
                        log_embed.add_field(
                            name="Original Ban Reason",
                            value=ban_info['reason'],
                            inline=False
                        )
                    
                    await logs_channel.send(embed=log_embed)
            
            # Try to DM the player
            try:
                dm_embed = discord.Embed(
                    title="✅ Tournament Ban Removed",
                    description="Your ban from the VALORANT Mobile India Tournament has been lifted. You can now register for the tournament.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.set_footer(text="Welcome back!")
                
                await player.send(embed=dm_embed)
            except discord.Forbidden:
                # Player has DMs disabled
                pass
        else:
            # Error occurred
            error_embed = discord.Embed(
                title="❌ Error Unbanning Player",
                description="Failed to unban the player. Please try again.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"❌ Failed to unban player {player.id}")
    
    @app_commands.command(
        name="admin-delete-team",
        description="[ADMIN] Permanently delete a team from the tournament"
    )
    async def admin_delete_team(
        self,
        interaction: discord.Interaction
    ):
        """Delete a team from the tournament."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can delete teams.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"🗑️ Admin deleting team")
        
        # Get all teams
        all_teams = await db.get_all_teams()
        
        if not all_teams:
            embed = discord.Embed(
                title="⚠️ No Teams Found",
                description="There are no teams registered in the tournament.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Show team selection dropdown
        embed = discord.Embed(
            title="🗑️ Delete Team",
            description="Select a team to permanently delete from the tournament.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="⚠️ This action cannot be undone!")
        
        view = DeleteTeamView(all_teams, interaction.user)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="admin-delete-player",
        description="[ADMIN] Permanently delete a player's registration"
    )
    @app_commands.describe(
        player="The player to delete"
    )
    async def admin_delete_player(
        self,
        interaction: discord.Interaction,
        player: discord.User
    ):
        """Delete a player's registration from the tournament."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can delete players.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"🗑️ Admin deleting player: {player.id}")
        
        # Check if the player is registered
        player_data = await db.pool.fetchrow(
            "SELECT * FROM players WHERE discord_id = $1",
            player.id
        )
        
        if not player_data:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"{player.mention} is not registered for the tournament.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Convert to dict
        player_dict = dict(player_data)
        
        # Show confirmation view
        confirm_view = DeletePlayerConfirmView(player, player_dict, interaction.user)
        
        embed = discord.Embed(
            title="⚠️ Confirm Player Deletion",
            description=f"Are you sure you want to permanently delete {player.mention}'s registration?",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="🎮 In-Game Name (IGN)",
            value=player_dict['ign'],
            inline=True
        )
        embed.add_field(
            name="🔢 Player ID",
            value=player_dict['player_id'],
            inline=True
        )
        embed.add_field(
            name="🌍 Region",
            value=player_dict['region'],
            inline=True
        )
        embed.add_field(
            name="🎯 Agent",
            value=player_dict['agent'] or 'Not set',
            inline=True
        )
        embed.add_field(
            name="📅 Registration Date",
            value=player_dict['registered_at'].strftime("%Y-%m-%d %H:%M UTC"),
            inline=True
        )
        embed.add_field(
            name="Discord ID",
            value=str(player.id),
            inline=True
        )
        embed.set_footer(text="⚠️ This action cannot be undone!")
        
        await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)
    
    @app_commands.command(
        name="admin-edit-team",
        description="[ADMIN] Edit a team's details"
    )
    async def admin_edit_team(
        self,
        interaction: discord.Interaction
    ):
        """Edit a registered team's details."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can edit teams.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"🔧 Admin editing team")
        
        # Get all teams
        all_teams = await db.get_all_teams()
        
        if not all_teams:
            embed = discord.Embed(
                title="⚠️ No Teams Found",
                description="There are no teams registered in the tournament.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Show team selection dropdown
        embed = discord.Embed(
            title="📝 Edit Team",
            description="Select a team to edit from the dropdown menu.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        view = EditTeamSelectView(all_teams)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="admin-transfer-captain",
        description="[ADMIN] Transfer team captainship to another team member"
    )
    async def admin_transfer_captain(
        self,
        interaction: discord.Interaction
    ):
        """Transfer captainship of a team to another member."""
        
        # Check if user has administrator role or bots role
        admin_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
        bots_role_id = os.getenv("BOTS_ROLE_ID")
        
        has_permission = False
        
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission and bots_role_id:
            bots_role = interaction.guild.get_role(int(bots_role_id))
            if bots_role and bots_role in interaction.user.roles:
                has_permission = True
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Only administrators and bot managers can transfer captainship.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        print(f"👑 Admin transferring captainship")
        
        # Get all teams
        all_teams = await db.get_all_teams()
        
        if not all_teams:
            embed = discord.Embed(
                title="⚠️ No Teams Found",
                description="There are no teams registered in the tournament.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Show team selection dropdown
        embed = discord.Embed(
            title="👑 Transfer Team Captainship",
            description="Select a team to transfer captainship.",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        view = AdminTransferCaptainTeamView(all_teams, interaction.user)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class EditTeamSelectView(discord.ui.View):
    """View with team selection dropdown for editing."""
    
    def __init__(self, teams: list):
        super().__init__(timeout=300)
        self.teams = teams
        self.add_item(EditTeamSelect(teams))


class EditTeamSelect(discord.ui.Select):
    """Dropdown for selecting team to edit."""
    
    def __init__(self, teams: list):
        self.teams = teams
        
        # Create options from teams
        options = []
        for team in teams[:25]:  # Discord limit of 25 options
            options.append(
                discord.SelectOption(
                    label=team['team_name'],
                    value=str(team['id']),
                    description=f"Tag: {team['team_tag']} | Region: {team['region']}",
                    emoji="👥"
                )
            )
        
        super().__init__(
            placeholder="Select a team to edit...",
            options=options,
            custom_id="edit_team_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        team_id = int(self.values[0])
        
        # Find the selected team
        selected_team = next((t for t in self.teams if t['id'] == team_id), None)
        
        if not selected_team:
            await interaction.response.send_message(
                "❌ Team not found.",
                ephemeral=True
            )
            return
        
        # Convert to dict
        team_dict = dict(selected_team)
        
        # Show current team info and field selection
        info_embed = discord.Embed(
            title="📋 Current Team Details",
            description=f"Editing team: **{team_dict['team_name']}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        info_embed.add_field(
            name="👥 Team Name",
            value=team_dict['team_name'],
            inline=True
        )
        info_embed.add_field(
            name="🏷️ Team Tag",
            value=team_dict['team_tag'],
            inline=True
        )
        info_embed.add_field(
            name="🌍 Region",
            value=team_dict['region'],
            inline=True
        )
        info_embed.add_field(
            name="👑 Captain",
            value=f"<@{team_dict['captain_discord_id']}>",
            inline=True
        )
        info_embed.add_field(
            name="🎨 Logo URL",
            value=team_dict['logo_url'] or 'Not set',
            inline=False
        )
        info_embed.add_field(
            name="📅 Created At",
            value=team_dict['created_at'].strftime("%Y-%m-%d %H:%M UTC"),
            inline=True
        )
        info_embed.add_field(
            name="Team ID",
            value=str(team_dict['id']),
            inline=True
        )
        info_embed.set_footer(text="Select a field below to edit")
        
        # If logo_url exists, set as thumbnail
        if team_dict['logo_url']:
            info_embed.set_thumbnail(url=team_dict['logo_url'])
        
        # Create view with field selection dropdown
        view = EditTeamFieldView(team_dict)
        
        await interaction.response.edit_message(embed=info_embed, view=view)


class EditTeamFieldView(discord.ui.View):
    """View containing the team field selection dropdown."""
    
    def __init__(self, team_data: dict):
        super().__init__(timeout=300)
        self.add_item(EditTeamFieldSelect(team_data))
    
    async def on_timeout(self):
        # Disable all items when view times out
        for item in self.children:
            item.disabled = True


class EditTeamFieldSelect(discord.ui.Select):
    """Dropdown for selecting which team field to edit."""
    
    def __init__(self, team_data: dict):
        self.team_data = team_data
        
        # Create options for each editable field
        options = [
            discord.SelectOption(
                label="Team Name",
                value="team_name",
                description=f"Current: {team_data['team_name']}",
                emoji="👥"
            ),
            discord.SelectOption(
                label="Team Tag",
                value="team_tag",
                description=f"Current: {team_data['team_tag']}",
                emoji="🏷️"
            ),
            discord.SelectOption(
                label="Region",
                value="region",
                description=f"Current: {team_data['region']}",
                emoji="🌍"
            ),
            discord.SelectOption(
                label="Logo URL",
                value="logo_url",
                description=f"Current: {team_data['logo_url'][:30] if team_data['logo_url'] else 'Not set'}...",
                emoji="🎨"
            )
        ]
        
        super().__init__(
            placeholder="Select a field to edit...",
            options=options,
            custom_id="edit_team_field_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        field = self.values[0]
        print(f"🔧 Admin editing team field: {field} for team {self.team_data['id']}")
        
        # Special handling for logo_url - ask for image upload
        if field == "logo_url":
            await interaction.response.defer(ephemeral=True)
            
            embed = discord.Embed(
                title="📸 Upload Team Logo",
                description=(
                    f"Editing logo for: **{self.team_data['team_name']}**\n\n"
                    "Please upload the team logo image in this channel.\n\n"
                    "**Requirements:**\n"
                    "• Must be an image file (PNG, JPG, JPEG, GIF)\n"
                    "• Recommended size: 512x512 pixels\n"
                    "• Maximum file size: 8MB\n\n"
                    "The image will be saved and your message will be deleted.\n"
                    "⏱️ You have 60 seconds to upload."
                ),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Wait for image upload
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and len(m.attachments) > 0
            
            try:
                import aiohttp
                from pathlib import Path
                
                bot = interaction.client
                message = await bot.wait_for('message', timeout=60.0, check=check)
                
                # Get the first attachment
                attachment = message.attachments[0]
                
                # Validate it's an image
                valid_extensions = ['.png', '.jpg', '.jpeg', '.gif']
                file_ext = Path(attachment.filename).suffix.lower()
                
                if file_ext not in valid_extensions:
                    await interaction.followup.send(
                        "❌ Please upload a valid image file (PNG, JPG, JPEG, or GIF).",
                        ephemeral=True
                    )
                    await message.delete()
                    return
                
                # Create team_logos directory if it doesn't exist
                logos_dir = Path("team_logos")
                logos_dir.mkdir(exist_ok=True)
                
                # Generate filename: teamid_timestamp.ext
                import time
                timestamp = int(time.time())
                filename = f"team_{self.team_data['id']}_{timestamp}{file_ext}"
                filepath = logos_dir / filename
                
                # Download and save the image
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            with open(filepath, 'wb') as f:
                                f.write(await resp.read())
                
                # Update database with local file path
                logo_path = str(filepath)
                query = "UPDATE teams SET logo_url = $1, updated_at = NOW() WHERE id = $2"
                await db.pool.execute(query, logo_path, self.team_data['id'])
                
                # Delete the user's message with the image
                await message.delete()
                
                print(f"✓ Team logo saved to {logo_path}")
                
                # Send confirmation
                confirm_embed = discord.Embed(
                    title="✅ Team Logo Updated Successfully",
                    description=f"Updated logo for **{self.team_data['team_name']}**",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                confirm_embed.add_field(
                    name="Field",
                    value="Team Logo",
                    inline=True
                )
                confirm_embed.add_field(
                    name="Old Logo",
                    value=self.team_data['logo_url'] or 'Not set',
                    inline=False
                )
                confirm_embed.add_field(
                    name="New Logo Path",
                    value=logo_path,
                    inline=False
                )
                confirm_embed.set_footer(text=f"Edited by {interaction.user.display_name}")
                confirm_embed.set_thumbnail(url=f"attachment://{filename}")
                
                # Send with the image as attachment
                await interaction.followup.send(
                    embed=confirm_embed,
                    file=discord.File(filepath, filename=filename),
                    ephemeral=True
                )
                
                # Log to bot logs channel
                logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
                if logs_channel_id:
                    logs_channel = interaction.client.get_channel(int(logs_channel_id))
                    if logs_channel:
                        log_embed = discord.Embed(
                            title="🛠️ Admin: Team Logo Updated",
                            color=discord.Color.orange(),
                            timestamp=datetime.utcnow()
                        )
                        log_embed.add_field(
                            name="Team",
                            value=f"**{self.team_data['team_name']}** (ID: {self.team_data['id']})",
                            inline=False
                        )
                        log_embed.add_field(
                            name="Old Logo",
                            value=self.team_data['logo_url'] or 'Not set',
                            inline=False
                        )
                        log_embed.add_field(
                            name="New Logo Path",
                            value=logo_path,
                            inline=False
                        )
                        log_embed.set_footer(text=f"Admin: {interaction.user.display_name} ({interaction.user.id})")
                        log_embed.set_thumbnail(url=f"attachment://{filename}")
                        
                        await logs_channel.send(
                            embed=log_embed,
                            file=discord.File(filepath, filename=filename)
                        )
                
                # Notify team members
                members = await db.get_team_members(self.team_data['id'])
                for member in members:
                    try:
                        user = await interaction.client.fetch_user(member['discord_id'])
                        dm_embed = discord.Embed(
                            title="📝 Team Logo Updated",
                            description=f"Your team **{self.team_data['team_name']}** logo has been updated by an administrator.",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        dm_embed.set_thumbnail(url=f"attachment://{filename}")
                        dm_embed.set_footer(text="If you believe this was done in error, please contact an administrator.")
                        
                        await user.send(embed=dm_embed, file=discord.File(filepath, filename=filename))
                    except (discord.Forbidden, discord.NotFound):
                        pass
                
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    "❌ Timeout: No image uploaded within 60 seconds.",
                    ephemeral=True
                )
            except Exception as e:
                import traceback
                error_embed = discord.Embed(
                    title="❌ Error Uploading Logo",
                    description=f"Failed to upload team logo: {str(e)}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                print(f"❌ Error uploading team logo:")
                print(traceback.format_exc())
            
            return
        
        # For other fields, show modal as usual
        modal = EditTeamValueModal(
            field=field,
            current_value=self.team_data[field] or "",
            team_data=self.team_data
        )
        await interaction.response.send_modal(modal)
        print(f"✓ Modal sent for team field: {field}")


class EditTeamValueModal(discord.ui.Modal):
    """Modal for entering the new value for a team field."""
    
    def __init__(self, field: str, current_value: str, team_data: dict):
        self.field = field
        self.team_data = team_data
        
        # Map field names to user-friendly labels
        field_labels = {
            "team_name": "Team Name",
            "team_tag": "Team Tag",
            "region": "Region",
            "logo_url": "Logo URL"
        }
        
        super().__init__(title=f"Edit {field_labels[field]}")
        
        # Add text input with current value as placeholder
        self.new_value_input = discord.ui.TextInput(
            label=f"New {field_labels[field]}",
            placeholder=current_value or "Enter new value",
            default=current_value,
            required=True if field != "logo_url" else False,
            max_length=500 if field == "logo_url" else 50,
            style=discord.TextStyle.short if field != "logo_url" else discord.TextStyle.paragraph
        )
        self.add_item(self.new_value_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.new_value_input.value.strip()
        print(f"📝 Team modal submitted - Field: {self.field}, New value: {new_value}")
        
        # Defer the response since database operation might take time
        await interaction.response.defer(ephemeral=True)
        print(f"✓ Team modal response deferred")
        
        try:
            # Whitelist valid field names to prevent SQL injection
            valid_fields = ["team_name", "team_tag", "region", "logo_url"]
            if self.field not in valid_fields:
                raise ValueError(f"Invalid field: {self.field}")
            
            # Update the team's field in database
            query = f"UPDATE teams SET {self.field} = $1, updated_at = NOW() WHERE id = $2"
            await db.pool.execute(query, new_value if new_value else None, self.team_data['id'])
            print(f"✓ Team database updated successfully")
            
            # Field labels for logging
            field_labels = {
                "team_name": "Team Name",
                "team_tag": "Team Tag",
                "region": "Region",
                "logo_url": "Logo URL"
            }
            
            # Send confirmation to admin
            embed = discord.Embed(
                title="✅ Team Updated Successfully",
                description=f"Updated **{self.team_data['team_name']}**",
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
                value=self.team_data[self.field] or 'Not set',
                inline=True
            )
            embed.add_field(
                name="New Value",
                value=new_value or 'Not set',
                inline=True
            )
            embed.add_field(
                name="Team ID",
                value=str(self.team_data['id']),
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
                        title="🛠️ Admin: Team Details Edited",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Team",
                        value=f"**{self.team_data['team_name']}** (ID: {self.team_data['id']})",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Field Edited",
                        value=field_labels[self.field],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Old Value",
                        value=self.team_data[self.field] or 'Not set',
                        inline=False
                    )
                    log_embed.add_field(
                        name="New Value",
                        value=new_value or 'Not set',
                        inline=False
                    )
                    log_embed.set_footer(text=f"Admin: {interaction.user.display_name} ({interaction.user.id})")
                    
                    await logs_channel.send(embed=log_embed)
            
            # Notify team members about the change
            members = await db.get_team_members(self.team_data['id'])
            for member in members:
                try:
                    user = await interaction.client.fetch_user(member['discord_id'])
                    dm_embed = discord.Embed(
                        title="📝 Team Updated",
                        description=f"Your team **{self.team_data['team_name']}** has been updated by an administrator.",
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
                        value=self.team_data[self.field] or 'Not set',
                        inline=False
                    )
                    dm_embed.add_field(
                        name="New Value",
                        value=new_value or 'Not set',
                        inline=False
                    )
                    dm_embed.set_footer(text="If you believe this was done in error, please contact an administrator.")
                    
                    await user.send(embed=dm_embed)
                except (discord.Forbidden, discord.NotFound):
                    # User has DMs disabled or not found
                    pass
        
        except Exception as e:
            # Send error message to admin
            error_embed = discord.Embed(
                title="❌ Error Updating Team",
                description=f"Failed to update team: {str(e)}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            # Log error with full traceback
            import traceback
            print(f"❌ Error updating team {self.team_data['id']}:")
            print(traceback.format_exc())


class AdminTransferCaptainTeamView(discord.ui.View):
    """View with team selection dropdown for captain transfer."""
    
    def __init__(self, teams: list, admin_user: discord.User):
        super().__init__(timeout=300)
        self.teams = teams
        self.admin_user = admin_user
        self.add_item(AdminTransferCaptainTeamSelect(teams, admin_user))


class AdminTransferCaptainTeamSelect(discord.ui.Select):
    """Dropdown for selecting team for captain transfer."""
    
    def __init__(self, teams: list, admin_user: discord.User):
        self.teams = teams
        self.admin_user = admin_user
        
        # Create options from teams
        options = []
        for team in teams[:25]:  # Discord limit of 25 options
            options.append(
                discord.SelectOption(
                    label=team['team_name'],
                    value=str(team['id']),
                    description=f"Tag: {team['team_tag']} | Captain: ID {team['captain_discord_id']}",
                    emoji="👥"
                )
            )
        
        super().__init__(
            placeholder="Select a team...",
            options=options,
            custom_id="admin_transfer_captain_team_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        team_id = int(self.values[0])
        
        # Find the selected team
        selected_team = next((t for t in self.teams if t['id'] == team_id), None)
        
        if not selected_team:
            await interaction.response.send_message(
                "❌ Team not found.",
                ephemeral=True
            )
            return
        
        # Get team members
        members = await db.get_team_members(team_id)
        
        if not members:
            await interaction.response.send_message(
                "❌ This team has no members.",
                ephemeral=True
            )
            return
        
        # Show member selection dropdown
        embed = discord.Embed(
            title="👑 Select New Captain",
            description=f"Select a member from **{selected_team['team_name']}** to become the new captain.",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Current Captain",
            value=f"<@{selected_team['captain_discord_id']}>",
            inline=True
        )
        embed.add_field(
            name="Total Members",
            value=str(len(members)),
            inline=True
        )
        
        view = AdminTransferCaptainMemberView(selected_team, members, self.admin_user)
        
        # Populate the dropdown with member names
        select_item = view.children[0]
        await select_item.populate_options(interaction.client)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AdminTransferCaptainMemberView(discord.ui.View):
    """View with member selection dropdown for captain transfer."""
    
    def __init__(self, team: dict, members: list, admin_user: discord.User):
        super().__init__(timeout=300)
        self.team = team
        self.members = members
        self.admin_user = admin_user
        self.add_item(AdminTransferCaptainMemberSelect(team, members, admin_user))


class AdminTransferCaptainMemberSelect(discord.ui.Select):
    """Dropdown for selecting new captain from team members."""
    
    def __init__(self, team: dict, members: list, admin_user: discord.User):
        self.team = team
        self.members = members
        self.admin_user = admin_user
        
        # Create options from members - will be populated in callback after fetching names
        options = [
            discord.SelectOption(
                label="Loading members...",
                value="0",
                emoji="⏳"
            )
        ]
        
        super().__init__(
            placeholder="Select new captain...",
            options=options,
            custom_id="admin_transfer_captain_member_select"
        )
    
    async def populate_options(self, bot):
        """Populate dropdown options with member names."""
        options = []
        
        for member in self.members[:25]:  # Discord limit of 25 options
            # Try to get player name from database
            player_data = await db.pool.fetchrow(
                "SELECT ign FROM players WHERE discord_id = $1",
                member['discord_id']
            )
            
            # Show role and mark current captain
            role_display = member['role'].title()
            
            if player_data and player_data['ign']:
                member_name = player_data['ign']
            else:
                # Fallback to Discord username if not in database
                try:
                    user = await bot.fetch_user(member['discord_id'])
                    member_name = user.name
                except:
                    member_name = str(member['discord_id'])
            
            if member['discord_id'] == self.team['captain_discord_id']:
                label = f"👑 {member_name} (Current Captain)"
            else:
                label = f"{member_name}"
            
            options.append(
                discord.SelectOption(
                    label=label[:100],  # Discord label limit
                    value=str(member['discord_id']),
                    description=f"Role: {role_display}",
                    emoji="👤"
                )
            )
        
        self.options = options
    
    async def callback(self, interaction: discord.Interaction):
        new_captain_id = int(self.values[0])
        old_captain_id = self.team['captain_discord_id']
        
        # Check if trying to transfer to current captain
        if new_captain_id == old_captain_id:
            await interaction.response.send_message(
                "❌ This user is already the team captain.",
                ephemeral=True
            )
            return
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get member info
            new_captain_member = next((m for m in self.members if m['discord_id'] == new_captain_id), None)
            
            if not new_captain_member:
                await interaction.followup.send(
                    "❌ Selected member not found in team.",
                    ephemeral=True
                )
                return
            
            # Update team captain in database
            await db.pool.execute(
                "UPDATE teams SET captain_discord_id = $1, updated_at = NOW() WHERE id = $2",
                new_captain_id,
                self.team['id']
            )
            
            # Update old captain's role to their previous role or manager
            old_captain_member = next((m for m in self.members if m['discord_id'] == old_captain_id), None)
            if old_captain_member:
                # If old captain was also a player, keep them as player, otherwise make them manager
                new_role = 'player' if old_captain_member['role'] == 'captain' else old_captain_member['role']
                if new_role == 'captain':  # Safety check
                    new_role = 'manager'
                
                await db.pool.execute(
                    "UPDATE team_members SET role = $1 WHERE team_id = $2 AND discord_id = $3",
                    new_role,
                    self.team['id'],
                    old_captain_id
                )
            
            # Update new captain's role to captain
            await db.pool.execute(
                "UPDATE team_members SET role = $1 WHERE team_id = $2 AND discord_id = $3",
                'captain',
                self.team['id'],
                new_captain_id
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Captainship Transferred",
                description=f"Successfully transferred captainship of **{self.team['team_name']}**",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Previous Captain",
                value=f"<@{old_captain_id}>",
                inline=True
            )
            embed.add_field(
                name="New Captain",
                value=f"<@{new_captain_id}>",
                inline=True
            )
            embed.add_field(
                name="Transferred By",
                value=self.admin_user.mention,
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Captainship transferred for team {self.team['id']}: {old_captain_id} → {new_captain_id}")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="👑 Admin: Captainship Transferred",
                        color=discord.Color.gold(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Team",
                        value=f"**{self.team['team_name']}** (ID: {self.team['id']})",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Previous Captain",
                        value=f"<@{old_captain_id}> (`{old_captain_id}`)",
                        inline=True
                    )
                    log_embed.add_field(
                        name="New Captain",
                        value=f"<@{new_captain_id}> (`{new_captain_id}`)",
                        inline=True
                    )
                    log_embed.add_field(
                        name="Transferred By",
                        value=f"{self.admin_user.mention} (`{self.admin_user.id}`)",
                        inline=False
                    )
                    
                    await logs_channel.send(embed=log_embed)
            
            # Notify old captain
            try:
                old_captain = await interaction.client.fetch_user(old_captain_id)
                old_captain_embed = discord.Embed(
                    title="👑 Captainship Transferred",
                    description=f"Your captainship of **{self.team['team_name']}** has been transferred to another member by tournament administrators.",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                old_captain_embed.add_field(
                    name="New Captain",
                    value=f"<@{new_captain_id}>",
                    inline=True
                )
                old_captain_embed.add_field(
                    name="Your New Role",
                    value=new_role.title() if old_captain_member else "Unknown",
                    inline=True
                )
                old_captain_embed.set_footer(text="You remain a member of the team.")
                
                await old_captain.send(embed=old_captain_embed)
            except (discord.Forbidden, discord.NotFound):
                pass
            
            # Notify new captain
            try:
                new_captain = await interaction.client.fetch_user(new_captain_id)
                new_captain_embed = discord.Embed(
                    title="👑 You Are Now Team Captain!",
                    description=f"You have been made the captain of **{self.team['team_name']}** by tournament administrators.",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )
                new_captain_embed.add_field(
                    name="Team",
                    value=self.team['team_name'],
                    inline=True
                )
                new_captain_embed.add_field(
                    name="Previous Captain",
                    value=f"<@{old_captain_id}>",
                    inline=True
                )
                new_captain_embed.set_footer(text="You can now manage team members and settings.")
                
                await new_captain.send(embed=new_captain_embed)
            except (discord.Forbidden, discord.NotFound):
                pass
            
            # Notify other team members
            for member in self.members:
                if member['discord_id'] not in [old_captain_id, new_captain_id]:
                    try:
                        user = await interaction.client.fetch_user(member['discord_id'])
                        member_embed = discord.Embed(
                            title="👑 Team Captain Changed",
                            description=f"The captain of **{self.team['team_name']}** has been changed by tournament administrators.",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        member_embed.add_field(
                            name="Previous Captain",
                            value=f"<@{old_captain_id}>",
                            inline=True
                        )
                        member_embed.add_field(
                            name="New Captain",
                            value=f"<@{new_captain_id}>",
                            inline=True
                        )
                        
                        await user.send(embed=member_embed)
                    except (discord.Forbidden, discord.NotFound):
                        pass
        
        except Exception as e:
            import traceback
            error_embed = discord.Embed(
                title="❌ Error Transferring Captainship",
                description=f"Failed to transfer captainship: {str(e)}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"❌ Error transferring captainship:")
            print(traceback.format_exc())


class DeletePlayerConfirmView(discord.ui.View):
    """Confirmation view for player deletion."""
    
    def __init__(self, player: discord.User, player_data: dict, admin_user: discord.User):
        super().__init__(timeout=60)
        self.player = player
        self.player_data = player_data
        self.admin_user = admin_user
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Delete the player
        success = await db.delete_player(self.player.id)
        
        if success:
            # Send confirmation
            embed = discord.Embed(
                title="✅ Player Deleted",
                description=f"Successfully deleted {self.player.mention}'s registration.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Player",
                value=f"{self.player.mention} (`{self.player.id}`)",
                inline=True
            )
            embed.add_field(
                name="Deleted By",
                value=self.admin_user.mention,
                inline=True
            )
            embed.add_field(
                name="IGN",
                value=self.player_data['ign'],
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Player {self.player.id} deleted by admin {self.admin_user.id}")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="🗑️ Admin: Player Registration Deleted",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Player",
                        value=f"{self.player.mention} (`{self.player.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="IGN",
                        value=self.player_data['ign'],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Player ID",
                        value=self.player_data['player_id'],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Region",
                        value=self.player_data['region'],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Deleted By",
                        value=f"{self.admin_user.mention} (`{self.admin_user.id}`)",
                        inline=False
                    )
                    
                    await logs_channel.send(embed=log_embed)
            
            # Try to DM the player
            try:
                dm_embed = discord.Embed(
                    title="🗑️ Registration Deleted",
                    description="Your tournament registration has been deleted by tournament administrators.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(
                    name="Your IGN",
                    value=self.player_data['ign'],
                    inline=True
                )
                dm_embed.add_field(
                    name="Region",
                    value=self.player_data['region'],
                    inline=True
                )
                dm_embed.set_footer(text="Contact tournament administrators if you have questions.")
                
                await self.player.send(embed=dm_embed)
            except discord.Forbidden:
                # Player has DMs disabled
                pass
        else:
            error_embed = discord.Embed(
                title="❌ Error Deleting Player",
                description="Failed to delete the player registration. Please try again.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"❌ Failed to delete player {self.player.id}")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✖️ Deletion Cancelled",
            description="Player deletion has been cancelled.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class DeleteTeamView(discord.ui.View):
    """View with team selection dropdown for deletion."""
    
    def __init__(self, teams: list, admin_user: discord.User):
        super().__init__(timeout=300)
        self.teams = teams
        self.admin_user = admin_user
        self.add_item(DeleteTeamSelect(teams, admin_user))


class DeleteTeamSelect(discord.ui.Select):
    """Dropdown for selecting team to delete."""
    
    def __init__(self, teams: list, admin_user: discord.User):
        self.teams = teams
        self.admin_user = admin_user
        
        # Create options from teams
        options = []
        for team in teams[:25]:  # Discord limit of 25 options
            options.append(
                discord.SelectOption(
                    label=team['team_name'],
                    value=str(team['id']),
                    description=f"Tag: {team['team_tag']} | ID: {team['id']}",
                    emoji="👥"
                )
            )
        
        super().__init__(
            placeholder="Select a team to delete...",
            options=options,
            custom_id="delete_team_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        team_id = int(self.values[0])
        
        # Find the selected team
        selected_team = next((t for t in self.teams if t['id'] == team_id), None)
        
        if not selected_team:
            await interaction.response.send_message(
                "❌ Team not found.",
                ephemeral=True
            )
            return
        
        # Show confirmation view
        confirm_view = DeleteTeamConfirmView(selected_team, self.admin_user)
        
        # Get team members
        members = await db.get_team_members(team_id)
        member_list = "\n".join([f"• <@{m['discord_id']}> ({m['role']})" for m in members[:10]])
        if len(members) > 10:
            member_list += f"\n...and {len(members) - 10} more"
        
        embed = discord.Embed(
            title="⚠️ Confirm Team Deletion",
            description=f"Are you sure you want to permanently delete **{selected_team['team_name']}**?",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Team Tag",
            value=selected_team['team_tag'],
            inline=True
        )
        embed.add_field(
            name="Team ID",
            value=str(team_id),
            inline=True
        )
        embed.add_field(
            name="Member Count",
            value=str(len(members)),
            inline=True
        )
        if members:
            embed.add_field(
                name="Team Members",
                value=member_list,
                inline=False
            )
        embed.set_footer(text="⚠️ This action cannot be undone! All team members will be notified.")
        
        await interaction.response.edit_message(embed=embed, view=confirm_view)


class DeleteTeamConfirmView(discord.ui.View):
    """Confirmation view for team deletion."""
    
    def __init__(self, team: dict, admin_user: discord.User):
        super().__init__(timeout=60)
        self.team = team
        self.admin_user = admin_user
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        team_id = self.team['id']
        team_name = self.team['team_name']
        
        # Get team members before deletion
        members = await db.get_team_members(team_id)
        
        # Delete team role if it exists
        if self.team.get('role_id'):
            try:
                role = interaction.guild.get_role(self.team['role_id'])
                if role:
                    await role.delete(reason=f"Team {team_name} deleted by admin")
                    print(f"✓ Deleted role {role.name}")
            except Exception as e:
                print(f"✗ Failed to delete role: {e}")
        
        # Delete the team (cascade deletes team_members)
        success = await db.delete_team(team_id)
        
        if success:
            # Send confirmation
            embed = discord.Embed(
                title="✅ Team Deleted",
                description=f"Successfully deleted **{team_name}**.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Deleted By",
                value=self.admin_user.mention,
                inline=True
            )
            embed.add_field(
                name="Members Removed",
                value=str(len(members)),
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✓ Team {team_id} ({team_name}) deleted by admin {self.admin_user.id}")
            
            # Log to bot logs channel
            logs_channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
            if logs_channel_id:
                logs_channel = interaction.client.get_channel(int(logs_channel_id))
                if logs_channel:
                    log_embed = discord.Embed(
                        title="🗑️ Admin: Team Deleted",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(
                        name="Team Name",
                        value=team_name,
                        inline=True
                    )
                    log_embed.add_field(
                        name="Team Tag",
                        value=self.team['team_tag'],
                        inline=True
                    )
                    log_embed.add_field(
                        name="Team ID",
                        value=str(team_id),
                        inline=True
                    )
                    log_embed.add_field(
                        name="Deleted By",
                        value=f"{self.admin_user.mention} (`{self.admin_user.id}`)",
                        inline=False
                    )
                    log_embed.add_field(
                        name="Members Affected",
                        value=str(len(members)),
                        inline=True
                    )
                    
                    await logs_channel.send(embed=log_embed)
            
            # Notify all team members via DM
            for member in members:
                try:
                    user = await interaction.client.fetch_user(member['discord_id'])
                    dm_embed = discord.Embed(
                        title="👥 Team Deleted",
                        description=f"Your team **{team_name}** has been deleted by tournament administrators.",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    dm_embed.add_field(
                        name="Your Role",
                        value=member['role'].title(),
                        inline=True
                    )
                    dm_embed.set_footer(text="Contact tournament administrators if you have questions.")
                    
                    await user.send(embed=dm_embed)
                except (discord.Forbidden, discord.NotFound):
                    # User has DMs disabled or not found
                    pass
        else:
            error_embed = discord.Embed(
                title="❌ Error Deleting Team",
                description="Failed to delete the team. Please try again.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"❌ Failed to delete team {team_id}")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✖️ Deletion Cancelled",
            description="Team deletion has been cancelled.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot):
    """Load the Admin cog."""
    await bot.add_cog(Admin(bot))
    print("✓ Admin cog loaded")
