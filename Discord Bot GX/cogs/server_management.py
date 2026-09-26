import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from v2_helpers import (
    make_v2_container,
    send_v2_interaction_response,
    GREEN_COLOR,
    RED_COLOR,
    BLUE_COLOR,
    DEFAULT_ACCENT_COLOR
)

class ServerManagementCog(commands.Cog, name="Server Management"):
    """Server configuration and channel/role automation commands (Components V2)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setwelcome", description="Configure welcome message channel and text.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Channel to post welcome messages in",
        message="Welcome message template. Use {user} for user mention, {server} for server name."
    )
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: Optional[str] = "Welcome {user} to {server}!"):
        await self.bot.db.update_guild_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        await self.bot.db.update_guild_setting(interaction.guild_id, "welcome_message", message)

        preview = message.format(user=interaction.user.mention, server=interaction.guild.name)
        text_content = (
            "### ⚙️ Welcome Channel Configured\n\n"
            f"> **Target Channel:** {channel.mention}\n"
            f"> **Template Preview:** {preview}"
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Server Automation", accent_color=GREEN_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="setlogchannel", description="Configure channel for server audit and moderation logs.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Text channel to route audit logs to")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.update_guild_setting(interaction.guild_id, "log_channel_id", channel.id)
        text_content = (
            "### ⚙️ Audit Log Channel Configured\n\n"
            f"Server audit and security logs will now be routed to {channel.mention}."
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Server Automation", accent_color=GREEN_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="setautorole", description="Configure a role automatically assigned to new members upon joining.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to automatically assign to new members")
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.update_guild_setting(interaction.guild_id, "autorole_id", role.id)
        text_content = (
            "### ⚙️ Auto-Role Configured\n\n"
            f"New server members will automatically receive {role.mention} upon joining."
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Server Automation", accent_color=GREEN_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="createchannel", description="Quickly create a text or voice channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(name="Channel name", channel_type="Channel type (text or voice)", category="Optional category to put channel under")
    @app_commands.choices(channel_type=[
        app_commands.Choice(name="Text Channel", value="text"),
        app_commands.Choice(name="Voice Channel", value="voice"),
    ])
    async def create_channel(self, interaction: discord.Interaction, name: str, channel_type: str, category: Optional[discord.CategoryChannel] = None):
        guild = interaction.guild
        try:
            if channel_type == "text":
                ch = await guild.create_text_channel(name=name, category=category)
            else:
                ch = await guild.create_voice_channel(name=name, category=category)

            text_content = (
                f"### 📁 Channel Created\n\n"
                f"> **Created {channel_type.title()} Channel:** {ch.mention}\n"
                f"> **Category:** {category.name if category else 'None'}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Server Management", accent_color=BLUE_COLOR)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I lack permission to create channels.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="createrole", description="Quickly create a role with a custom name and color.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(name="Role name", hex_color="Hex color code (e.g. #FF5733)")
    async def create_role(self, interaction: discord.Interaction, name: str, hex_color: Optional[str] = "#99AAB5"):
        guild = interaction.guild
        try:
            color_int = int(hex_color.replace("#", ""), 16)
            color = discord.Color(color_int)
        except ValueError:
            err_c = make_v2_container("❌ Invalid hex color code. Example: `#3498DB`", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        try:
            role = await guild.create_role(name=name, color=color, reason=f"Created by {interaction.user}")
            text_content = (
                "### ✨ Role Created\n\n"
                f"> **Role:** {role.mention}\n"
                f"> **Color Hex:** `{hex_color}`"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Server Management", accent_color=color_int)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I lack permission to create roles.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            err_c = make_v2_container("❌ Administrator or Manage permissions required.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerManagementCog(bot))
