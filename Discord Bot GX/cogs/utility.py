import discord
from discord import app_commands
from discord.ext import commands
import time
from v2_helpers import (
    make_v2_container,
    send_v2_interaction_response,
    send_v2_followup,
    NEON_PURPLE_COLOR,
    DEFAULT_ACCENT_COLOR
)

class UtilityCog(commands.Cog, name="Utility"):
    """Utility commands for server members and administrators (Components V2)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's response time and API latency.")
    async def ping(self, interaction: discord.Interaction):
        start = time.perf_counter()
        await interaction.response.defer(ephemeral=True)
        end = time.perf_counter()
        latency = round((end - start) * 1000)
        api_latency = round(self.bot.latency * 1000)

        text_content = (
            "### 🏓 Pong! Bot Latency & Status\n\n"
            f"> **Bot Processing Latency:** `{latency} ms`\n"
            f"> **Discord Gateway Latency:** `{api_latency} ms`\n"
            "> **Components Engine:** `Discord Components V2 (Active)`"
        )
        container = make_v2_container(
            text_content=text_content,
            footer_text="GX System Diagnostics",
            accent_color=NEON_PURPLE_COLOR
        )
        await send_v2_followup(interaction, [container], ephemeral=True)

    @app_commands.command(name="serverinfo", description="Display information about the current Discord server.")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            err_c = make_v2_container("❌ This command can only be used in a server.")
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        owner = guild.owner.mention if guild.owner else "Unknown"
        created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        text_content = (
            f"### 📊 Server Information — {guild.name}\n\n"
            f"> **Server ID:** `{guild.id}`\n"
            f"> **Server Owner:** {owner}\n"
            f"> **Created At:** `{created_at}`\n"
            f"> **Total Members:** `{guild.member_count}`\n"
            f"> **Text Channels:** `{len(guild.text_channels)}`\n"
            f"> **Voice Channels:** `{len(guild.voice_channels)}`\n"
            f"> **Roles Total:** `{len(guild.roles)}`\n"
            f"> **Nitro Boost Tier:** `Level {guild.premium_tier}` ({guild.premium_subscription_count} boosts)"
        )
        container = make_v2_container(
            text_content=text_content,
            footer_text="GX Community Overview",
            accent_color=DEFAULT_ACCENT_COLOR
        )
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="userinfo", description="Display details about a server member.")
    @app_commands.describe(user="The member to view details for (defaults to yourself).")
    async def user_info(self, interaction: discord.Interaction, user: discord.Member = None):
        member = user or interaction.user
        if not isinstance(member, discord.Member):
            err_c = make_v2_container("❌ Could not find member details.")
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC") if member.joined_at else "N/A"
        created_at = member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        text_content = (
            f"### 👤 User Information — {member.display_name}\n\n"
            f"> **Full Username:** `{member}`\n"
            f"> **Discord User ID:** `{member.id}`\n"
            f"> **Account Created:** `{created_at}`\n"
            f"> **Joined Server:** `{joined_at}`\n"
            f"> **Roles ({len(roles)}):** " + (", ".join(roles[:8]) if roles else "None")
        )
        container = make_v2_container(
            text_content=text_content,
            footer_text="GX Member Profile",
            accent_color=DEFAULT_ACCENT_COLOR
        )
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
