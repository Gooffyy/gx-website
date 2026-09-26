import discord
from discord import app_commands
from discord.ext import commands
import datetime
from typing import Optional

from v2_helpers import (
    make_v2_container,
    send_v2_interaction_response,
    send_v2_followup,
    RED_COLOR,
    ORANGE_COLOR,
    GREEN_COLOR,
    DEFAULT_ACCENT_COLOR
)

class ModerationCog(commands.Cog, name="Moderation"):
    """Moderation slash commands for managing server members (Components V2)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            err_c = make_v2_container("❌ You cannot kick a member with a role equal to or higher than yours.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        try:
            await member.kick(reason=f"By {interaction.user}: {reason}")
            text_content = (
                "### 👢 Member Kicked\n\n"
                f"> **Target:** {member.mention} (`{member}`)\n"
                f"> **Reason:** `{reason}`\n"
                f"> **Moderator:** {interaction.user.mention}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Moderation", accent_color=ORANGE_COLOR)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I do not have permission to kick this user.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="Reason for banning", delete_message_days="Days of messages to delete (0-7)")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided", delete_message_days: Optional[int] = 0):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            err_c = make_v2_container("❌ You cannot ban a member with a role equal to or higher than yours.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        try:
            await member.ban(reason=f"By {interaction.user}: {reason}", delete_message_days=min(max(delete_message_days, 0), 7))
            text_content = (
                "### 🔨 Member Banned\n\n"
                f"> **Target:** {member.mention} (`{member}`)\n"
                f"> **Reason:** `{reason}`\n"
                f"> **Moderator:** {interaction.user.mention}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Moderation", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I do not have permission to ban this user.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user_id="The Discord User ID to unban", reason="Reason for unbanning")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: Optional[str] = "No reason provided"):
        try:
            uid = int(user_id)
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f"By {interaction.user}: {reason}")
            text_content = (
                "### ✅ User Unbanned\n\n"
                f"> **Target:** `{user.name}` (`{user.id}`)\n"
                f"> **Reason:** `{reason}`\n"
                f"> **Moderator:** {interaction.user.mention}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Moderation", accent_color=GREEN_COLOR)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except ValueError:
            err_c = make_v2_container("❌ Please enter a valid numerical User ID.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
        except discord.NotFound:
            err_c = make_v2_container("❌ User not found in ban list.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I do not have permission to unban users.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="timeout", description="Temporarily timeout/mute a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason for timeout")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = "No reason provided"):
        if minutes <= 0 or minutes > 40320:
            err_c = make_v2_container("❌ Duration must be between 1 minute and 40320 minutes (28 days).", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        duration = datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(duration, reason=f"By {interaction.user}: {reason}")
            text_content = (
                "### ⏳ Member Timed Out\n\n"
                f"> **Target:** {member.mention} (`{member}`)\n"
                f"> **Duration:** `{minutes}` Minutes\n"
                f"> **Reason:** `{reason}`\n"
                f"> **Moderator:** {interaction.user.mention}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Moderation", accent_color=ORANGE_COLOR)
            await send_v2_interaction_response(interaction, [container], ephemeral=False)
        except discord.Forbidden:
            err_c = make_v2_container("❌ I do not have permission to timeout this user.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="purge", description="Delete a specified number of messages from this channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            err_c = make_v2_container("❌ Amount must be between 1 and 100.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        container = make_v2_container(
            text_content=f"🧹 **Channel Cleaned:** Successfully purged `{len(deleted)}` messages.",
            accent_color=GREEN_COLOR
        )
        await send_v2_followup(interaction, [container], ephemeral=True)

    @app_commands.command(name="warn", description="Issue a warning to a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to warn", reason="Reason for warning")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        warn_id = await self.bot.db.add_warning(
            guild_id=interaction.guild_id,
            user_id=member.id,
            moderator_id=interaction.user.id,
            reason=reason
        )
        warnings = await self.bot.db.get_warnings(interaction.guild_id, member.id)

        text_content = (
            f"### ⚠️ Member Warned (Warn ID: `#{warn_id}`)\n\n"
            f"> **Member:** {member.mention} (`{member}`)\n"
            f"> **Reason:** `{reason}`\n"
            f"> **Total Warnings:** `{len(warnings)}`\n"
            f"> **Moderator:** {interaction.user.mention}"
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Moderation Logs", accent_color=ORANGE_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="warnings", description="View warnings for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member whose warnings to inspect")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warn_list = await self.bot.db.get_warnings(interaction.guild_id, member.id)
        if not warn_list:
            c = make_v2_container(f"ℹ️ **{member.display_name}** has no recorded warnings.", accent_color=DEFAULT_ACCENT_COLOR)
            return await send_v2_interaction_response(interaction, [c], ephemeral=True)

        lines = [f"### ⚠️ Warnings for {member.display_name} ({len(warn_list)})\n"]
        for w in warn_list[:10]:
            lines.append(f"> • **Warn `#{w['id']}`** ({w['timestamp']}): `{w['reason']}` (Mod: <@{w['moderator_id']}>)")

        container = make_v2_container(
            text_content="\n".join(lines),
            footer_text="GX Moderation Database",
            accent_color=ORANGE_COLOR
        )
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member whose warnings to clear")
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        count = await self.bot.db.clear_warnings(interaction.guild_id, member.id)
        container = make_v2_container(
            text_content=f"✅ Cleared `{count}` warning(s) for **{member.display_name}**.",
            accent_color=GREEN_COLOR
        )
        await send_v2_interaction_response(interaction, [container], ephemeral=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            err_c = make_v2_container("❌ You lack the required permissions to execute this command.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
