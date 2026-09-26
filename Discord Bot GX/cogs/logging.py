import discord
from discord.ext import commands
import logging
from v2_helpers import (
    make_v2_container,
    send_v2_channel_message,
    GREEN_COLOR,
    RED_COLOR,
    ORANGE_COLOR,
    BLUE_COLOR,
    DEFAULT_ACCENT_COLOR
)

logger = logging.getLogger("discord_bot.logging_cog")

class LoggingCog(commands.Cog, name="Event Logging"):
    """Listens for server events and dispatches audit logs and welcome events (Components V2)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        settings = await self.bot.db.get_guild_settings(guild.id)
        channel_id = settings.get("log_channel_id")
        if channel_id:
            return guild.get_channel(channel_id)
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        settings = await self.bot.db.get_guild_settings(guild.id)

        # 1. Retrieve Auto-Role
        role = None
        autorole_id = settings.get("autorole_id")
        if autorole_id:
            role = guild.get_role(autorole_id)

        if not role:
            role = discord.utils.get(guild.roles, name="👤 Member") or discord.utils.get(guild.roles, name="Member")

        if role:
            try:
                await member.add_roles(role, reason="Automatic member role assignment on join")
                logger.info(f"Assigned auto-role {role.name} to new member {member.name} ({member.id}) in guild {guild.name}")
            except discord.Forbidden:
                logger.warning(f"Failed to assign role {role.name} to {member.name}: Bot role is lower than target role in Discord Role Hierarchy.")
            except Exception as e:
                logger.error(f"Error assigning auto-role to {member.name}: {e}")

        # 2. Handle Welcome Message
        welcome_channel_id = settings.get("welcome_channel_id")
        welcome_message = settings.get("welcome_message") or "Welcome {user} to {server}!"
        if welcome_channel_id:
            channel = guild.get_channel(welcome_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    formatted_msg = welcome_message.format(user=member.mention, server=guild.name)
                    welcome_container = make_v2_container(
                        text_content=f"### 👋 Welcome to {guild.name}!\n\n{formatted_msg}",
                        footer_text=f"Member #{guild.member_count}",
                        accent_color=GREEN_COLOR
                    )
                    await send_v2_channel_message(channel, [welcome_container])
                except Exception as e:
                    logger.error(f"Error sending welcome message in guild {guild.id}: {e}")

        # 3. Audit Log Member Join
        log_channel = await self.get_log_channel(guild)
        if log_channel:
            text_content = (
                "### 📥 Member Joined Server\n\n"
                f"> **Member:** {member.mention} (`{member.id}`)\n"
                f"> **Account Created:** {member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Audit Logs", accent_color=GREEN_COLOR)
            await send_v2_channel_message(log_channel, [container])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log_channel = await self.get_log_channel(member.guild)
        if log_channel:
            text_content = (
                "### 📤 Member Left Server\n\n"
                f"> **Member:** **{member.name}** (`{member.id}`)"
            )
            container = make_v2_container(text_content=text_content, footer_text="GX Audit Logs", accent_color=RED_COLOR)
            await send_v2_channel_message(log_channel, [container])

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        log_channel = await self.get_log_channel(message.guild)
        if log_channel and log_channel.id != message.channel.id:
            text_content = (
                "### 🗑️ Message Deleted\n\n"
                f"> **Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"> **Channel:** {message.channel.mention}\n"
                f"> **Content:** {message.content or '*No text content*'}"
            )
            container = make_v2_container(text_content=text_content, footer_text=f"User ID: {message.author.id} | Message ID: {message.id}", accent_color=RED_COLOR)
            await send_v2_channel_message(log_channel, [container])

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return

        log_channel = await self.get_log_channel(before.guild)
        if log_channel and log_channel.id != before.channel.id:
            text_content = (
                "### ✏️ Message Edited\n\n"
                f"> **Author:** {before.author.mention} (`{before.author.id}`)\n"
                f"> **Channel:** {before.channel.mention}\n"
                f"> **Before:** {before.content or '*Empty*'}\n"
                f"> **After:** {after.content or '*Empty*'}"
            )
            container = make_v2_container(text_content=text_content, footer_text=f"User ID: {before.author.id} | Message ID: {before.id}", accent_color=ORANGE_COLOR)
            await send_v2_channel_message(log_channel, [container])

async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
