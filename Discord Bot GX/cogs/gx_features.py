import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from v2_helpers import (
    make_v2_container,
    send_v2_channel_message,
    send_v2_interaction_response,
    send_v2_followup,
    NEON_PURPLE_COLOR,
    ORANGE_COLOR,
    GREEN_COLOR,
    RED_COLOR,
    DEFAULT_ACCENT_COLOR
)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

class GXFeaturesCog(commands.Cog, name="GX App Features"):
    """Customer vouches, live app status monitoring, and HWID reset management (Components V2)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="vouch", description="Leave a review and star rating for GX App.")
    @app_commands.describe(
        rating="Rating from 1 to 5 stars",
        review="Your review feedback"
    )
    @app_commands.choices(rating=[
        app_commands.Choice(name="⭐⭐⭐⭐⭐ 5 Stars (Excellent)", value=5),
        app_commands.Choice(name="⭐⭐⭐⭐ 4 Stars (Good)", value=4),
        app_commands.Choice(name="⭐⭐⭐ 3 Stars (Average)", value=3),
        app_commands.Choice(name="⭐⭐ 2 Stars (Poor)", value=2),
        app_commands.Choice(name="⭐ 1 Star (Terrible)", value=1),
    ])
    async def vouch(self, interaction: discord.Interaction, rating: int, review: str):
        vouch_channel = discord.utils.get(interaction.guild.text_channels, name="💬-vouches") or discord.utils.get(interaction.guild.text_channels, name="vouches")
        if not vouch_channel:
            err_c = make_v2_container("❌ Could not find `#💬-vouches` channel.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        stars = "⭐" * rating
        text_content = (
            f"### 💬 Customer Review {stars}\n\n"
            f"> *\"{review}\"*\n\n"
            f"• **Rating:** `{rating} / 5` Stars\n"
            f"• **Verified Buyer:** {interaction.user.mention} (`{interaction.user.display_name}`)"
        )
        vouch_container = make_v2_container(
            text_content=text_content,
            footer_text="Verified Customer Review • Thank you for supporting GX App!",
            accent_color=0xFFD700  # Gold
        )

        await send_v2_channel_message(vouch_channel, [vouch_container])

        confirm_container = make_v2_container(
            text_content="✅ Thank you! Your review has been posted in `#💬-vouches`.",
            accent_color=GREEN_COLOR
        )
        await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)

    @app_commands.command(name="set-status", description="Update the live software status in #🟢-status.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        status="Current software status",
        build="Software build version (default: 1.11)",
        note="Optional status details or update notes"
    )
    @app_commands.choices(status=[
        app_commands.Choice(name="🟢 WORKING / UNDETECTED", value="working"),
        app_commands.Choice(name="🟡 MAINTENANCE / TESTING", value="maintenance"),
        app_commands.Choice(name="🔴 UPDATING (TEMPORARY OFF)", value="updating"),
    ])
    async def set_status(self, interaction: discord.Interaction, status: str, build: Optional[str] = "1.11", note: Optional[str] = "All key licenses and software functions operational."):
        status_channel = discord.utils.get(interaction.guild.text_channels, name="🟢-status") or discord.utils.get(interaction.guild.text_channels, name="status")
        if not status_channel:
            err_c = make_v2_container("❌ Could not find `#🟢-status` channel.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        status_display = {
            "working": ("ONLINE & UNDETECTED 🟢", NEON_PURPLE_COLOR, "Software is fully operational, updated, and undetected."),
            "maintenance": ("UNDER MAINTENANCE 🟡", ORANGE_COLOR, "Software is undergoing maintenance or testing."),
            "updating": ("UPDATING 🔴", RED_COLOR, "Software is currently updating. Please wait until status turns green.")
        }

        title, accent_color, default_desc = status_display.get(status, ("STATUS UPDATE", DEFAULT_ACCENT_COLOR, ""))

        text_content = (
            f"### 🟢 GX Software Status: {title}\n\n"
            f"• **Software Core**: `{title}`\n"
            f"• **License Server**: 🟢 **OPERATIONAL (0ms Latency)**\n"
            f"• **Supported OS**: Windows 10 & 11 (64-bit)\n"
            f"• **Software Build**: `v{build} (Latest Undetected)`\n"
            f"• **Key Verification**: 24/7 Automated Activation\n\n"
            f"> 🛡️ **Overview**: *{default_desc}*\n"
            f"> 📝 **Latest Note**: *{note}*"
        )
        status_container = make_v2_container(
            text_content=text_content,
            footer_text=f"GX Status • Fast • Secure • Global • Updated by {interaction.user.display_name}",
            accent_color=accent_color
        )

        try:
            await status_channel.purge(limit=10)
        except Exception:
            pass

        await send_v2_channel_message(status_channel, [status_container])

        confirm_container = make_v2_container(
            text_content=f"✅ Software status updated to `{title}` (Build `v{build}`) in {status_channel.mention}!",
            accent_color=GREEN_COLOR
        )
        await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)

    @app_commands.command(name="hwid-reset", description="Request a Hardware ID (HWID) reset for your GX App key.")
    @app_commands.describe(reason="Reason for HWID reset (e.g. upgraded motherboard, formatted PC)")
    async def hwid_reset(self, interaction: discord.Interaction, reason: str):
        key_role = discord.utils.get(interaction.guild.roles, name="⭐ Key Holder")
        if key_role and key_role not in interaction.user.roles:
            err_c = make_v2_container("❌ Only verified **⭐ Key Holder** members can request an HWID reset.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        key_log_ch = discord.utils.get(interaction.guild.text_channels, name="📋-key-logs") or discord.utils.get(interaction.guild.text_channels, name="📑-mod-logs")
        if key_log_ch:
            log_text = (
                "### 🔄 HWID Reset Request\n\n"
                f"> **User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"> **Reason:** `{reason}`\n\n"
                "Staff: Use `/approve-hwid user:<User>` to confirm reset."
            )
            req_container = make_v2_container(
                text_content=log_text,
                footer_text="GX HWID Queue",
                accent_color=ORANGE_COLOR
            )
            await send_v2_channel_message(key_log_ch, [req_container])

        confirm_c = make_v2_container(
            text_content="✅ Your HWID reset request has been submitted to staff! Our team will process it shortly.",
            accent_color=GREEN_COLOR
        )
        await send_v2_interaction_response(interaction, [confirm_c], ephemeral=True)

    @app_commands.command(name="approve-hwid", description="Approve an HWID reset for a user.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="The member whose HWID reset is approved")
    async def approve_hwid(self, interaction: discord.Interaction, user: discord.Member):
        dm_text = (
            "### ✅ HWID Reset Approved\n\n"
            f"Hello {user.mention}, your HWID reset request has been **Approved**!\n"
            "You can now launch and re-bind your GX App key on your new hardware."
        )
        dm_container = make_v2_container(
            text_content=dm_text,
            footer_text="GX Hardware Security",
            accent_color=GREEN_COLOR
        )
        try:
            dm_channel = user.dm_channel or await user.create_dm()
            await send_v2_channel_message(dm_channel, [dm_container])
        except discord.Forbidden:
            pass

        confirm_c = make_v2_container(
            text_content=f"✅ Approved HWID reset for {user.mention}. Notification dispatched!",
            accent_color=GREEN_COLOR
        )
        await send_v2_interaction_response(interaction, [confirm_c], ephemeral=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            err_c = make_v2_container("❌ Moderator or Administrator permissions required.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GXFeaturesCog(bot))
