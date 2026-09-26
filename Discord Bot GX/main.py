import asyncio
import json
import logging
import os
import sys
import discord
from discord.ext import commands

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import config
from database import Database
from cogs.tickets import TicketPanelView, SupportPanelView, TicketCloseView, TicketRatingView

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("discord_bot.main")

class DiscordManagerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=config.DEFAULT_PREFIX,
            intents=intents,
            help_command=None
        )
        self.db = Database()

    async def setup_hook(self):
        logger.info("Initializing Database...")
        await self.db.init_db()

        # Register persistent UI views for interactive buttons
        self.add_view(TicketPanelView())
        self.add_view(SupportPanelView())
        self.add_view(TicketCloseView())
        self.add_view(TicketRatingView())
        logger.info("Registered persistent ticket UI views.")

        # Load extension cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        if os.path.exists(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = f"cogs.{filename[:-3]}"
                    try:
                        await self.load_extension(cog_name)
                        logger.info(f"Loaded extension: {cog_name}")
                    except Exception as e:
                        logger.error(f"Failed to load extension {cog_name}: {e}")

        # Async background sync for slash commands so login is instantaneous
        asyncio.create_task(self.sync_commands_background())

    async def sync_commands_background(self):
        logger.info("Syncing slash commands in background...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} slash command(s).")
        except Exception as e:
            logger.error(f"Background slash command sync error: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} server(s).")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="More than a menu"
        )
        await self.change_presence(activity=activity)

        # Clear duplicate guild-specific commands so only global commands show (fixing 2x duplicate slash commands)
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Successfully purged duplicate guild-level commands from: {guild.name} ({guild.id})")
            except Exception as e:
                logger.error(f"Failed to clear guild commands for {guild.id}: {e}")

        # Automatically export live guild members cache for Web Admin Dashboard
        await self.sync_guild_members_cache()

    async def sync_guild_members_cache(self):
        try:
            target_guild = None
            if hasattr(config, 'GUILD_ID') and config.GUILD_ID:
                try:
                    target_guild = self.get_guild(int(config.GUILD_ID))
                except Exception:
                    pass
            if not target_guild and self.guilds:
                target_guild = self.guilds[0]

            if not target_guild:
                logger.warning("No guild found to sync members cache.")
                return

            members_list = []
            for m in target_guild.members:
                avatar_url = m.display_avatar.url if m.display_avatar else f"https://cdn.discordapp.com/embed/avatars/{int(m.id) % 5}.png"
                members_list.append({
                    "id": str(m.id),
                    "username": m.name,
                    "global_name": m.global_name,
                    "displayName": m.display_name or m.name,
                    "avatar": avatar_url,
                    "isBot": m.bot,
                    "roles": [str(r.id) for r in m.roles if not r.is_default()]
                })

            members_list.sort(key=lambda x: (x["isBot"], x["displayName"].lower()))

            cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "guild_members.json"))
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(members_list, f, ensure_ascii=False, indent=2)

            logger.info(f"Successfully cached {len(members_list)} guild member(s) to data/guild_members.json")
        except Exception as e:
            logger.warning(f"Failed to sync guild members cache: {e}")

    async def on_member_join(self, member):
        await self.sync_guild_members_cache()

    async def on_member_remove(self, member):
        await self.sync_guild_members_cache()

async def main():
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_bot_token_here":
        logger.warning(
            "DISCORD_TOKEN is missing or set to placeholder in .env file!\n"
            "Please update your .env file with a valid bot token from https://discord.com/developers/applications"
        )
        sys.exit(1)

    bot = DiscordManagerBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
