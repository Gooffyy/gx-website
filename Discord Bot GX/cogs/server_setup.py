import os
import discord
from discord import app_commands
from discord.ext import commands
import secrets
import string
import logging
from typing import Optional
from cogs.tickets import TicketPanelView, deploy_v2_ticket_panel, deploy_v2_purchase_panel, deploy_v2_support_panel
from v2_helpers import (
    make_v2_container,
    send_v2_interaction_response,
    send_v2_followup,
    send_v2_channel_message,
    GREEN_COLOR,
    RED_COLOR,
    ORANGE_COLOR,
    BLUE_COLOR,
    NEON_PURPLE_COLOR,
    DEFAULT_ACCENT_COLOR
)

logger = logging.getLogger("discord_bot.server_setup")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

async def clear_and_send(channel: discord.TextChannel, bot: commands.Bot, embed: discord.Embed, files: list = None):
    """Deletes previous bot messages in channel and sends the new embed with optional file attachments."""
    async for msg in channel.history(limit=10):
        if msg.author == bot.user:
            try:
                await msg.delete()
            except Exception:
                pass
    if files:
        await channel.send(files=files, embed=embed)
    else:
        await channel.send(embed=embed)

class ServerSetupCog(commands.Cog, name="GX Server Setup"):
    """Automated server template builder and license key management for GX App."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._auto_setup_done = set()

    def generate_random_key(self, prefix: str = "GX") -> str:
        chars = string.ascii_uppercase + string.digits
        part1 = "".join(secrets.choice(chars) for _ in range(4))
        part2 = "".join(secrets.choice(chars) for _ in range(4))
        part3 = "".join(secrets.choice(chars) for _ in range(4))
        part4 = "".join(secrets.choice(chars) for _ in range(4))
        return f"{prefix}-{part1}-{part2}-{part3}-{part4}"

    async def build_full_gx_server(self, guild: discord.Guild):
        """Construct the entire GX application server structure automatically."""
        logger.info(f"Starting automatic full server setup for guild: {guild.name} ({guild.id})")

        # Delete any legacy #🔑-redeem-key channel if it exists
        old_redeem = discord.utils.get(guild.text_channels, name="🔑-redeem-key") or discord.utils.get(guild.text_channels, name="redeem-key")
        if old_redeem:
            try:
                await old_redeem.delete(reason="Removed redeem key channel per instruction: purchases handled via tickets.")
                logger.info(f"Deleted old key channel: {old_redeem.name}")
            except Exception as e:
                logger.error(f"Failed to delete old key channel: {e}")

        # 1. Create & Update Roles
        role_configs = [
            ("👑 Owner", discord.Color.from_rgb(122, 0, 255), True),       # Electric Imperial Purple (#7A00FF)
            ("👑 Admin", discord.Color.from_rgb(161, 0, 255), True),      # Bright Royal Violet (#A100FF)
            ("🛡️ Moderator", discord.Color.from_rgb(192, 66, 255), True),  # Neon Lavender Purple (#C042FF)
            ("🤝 Friends", discord.Color.from_rgb(224, 112, 255), True),   # Soft Orchid Purple (#E070FF)
            ("⭐ Key Holder", discord.Color.from_rgb(72, 0, 133), True),   # Deep Midnight Violet (#480085)
            ("👤 Member", discord.Color.from_rgb(45, 0, 89), True)         # Slate Dark Plum (#2D0059)
        ]

        created_roles = {}
        for role_name, color, hoist in role_configs:
            existing = discord.utils.get(guild.roles, name=role_name)
            if not existing:
                try:
                    role = await guild.create_role(name=role_name, color=color, hoist=hoist)
                    created_roles[role_name] = role
                except Exception as e:
                    logger.error(f"Could not create role {role_name}: {e}")
            else:
                try:
                    await existing.edit(color=color, hoist=True)
                except Exception as e:
                    logger.error(f"Could not update role {role_name}: {e}")
                created_roles[role_name] = existing

        everyone = guild.default_role
        owner_role = created_roles.get("👑 Owner")
        admin_role = created_roles.get("👑 Admin")
        mod_role = created_roles.get("🛡️ Moderator")
        key_holder_role = created_roles.get("⭐ Key Holder")
        member_role = created_roles.get("👤 Member")

        # Assign 👑 Owner role to Server Owner
        if owner_role and guild.owner:
            if owner_role not in guild.owner.roles:
                try:
                    await guild.owner.add_roles(owner_role, reason="Assigning Owner role to Server Owner")
                except Exception as e:
                    logger.warning(f"Could not assign Owner role to {guild.owner}: {e}")

        # Auto-update Server Icon & Bot Avatar with circular neon logo
        logo_path = os.path.join(ASSETS_DIR, "logo_avatar.jpg")
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    await guild.edit(icon=f.read())
                    logger.info(f"Successfully updated server icon for {guild.name}")
            except Exception as e:
                logger.warning(f"Could not auto-update server icon: {e}")

            if not getattr(self.bot, "_avatar_updated", False):
                try:
                    with open(logo_path, "rb") as f:
                        await self.bot.user.edit(avatar=f.read())
                        self.bot._avatar_updated = True
                        logger.info("Successfully updated bot avatar to GX neon logo.")
                except Exception as e:
                    logger.warning(f"Could not auto-update bot avatar: {e}")

        read_only_overwrite = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if owner_role:
            read_only_overwrite[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        staff_only_overwrite = {
            everyone: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if owner_role:
            staff_only_overwrite[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        customer_only_overwrite = {
            everyone: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if owner_role:
            customer_only_overwrite[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if key_holder_role:
            customer_only_overwrite[key_holder_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        # 2. Category 1: INFORMATION
        cat_info = (
            discord.utils.get(guild.categories, name="📌┃INFORMATION")
            or discord.utils.get(guild.categories, name="📌 INFORMATION")
            or await guild.create_category("📌┃INFORMATION")
        )
        ch_rules = (
            discord.utils.get(cat_info.text_channels, name="📜┃rules")
            or discord.utils.get(cat_info.text_channels, name="📜-rules")
            or await cat_info.create_text_channel("📜┃rules", overwrites=read_only_overwrite)
        )
        ch_announcements = (
            discord.utils.get(cat_info.text_channels, name="📢┃announcements")
            or discord.utils.get(cat_info.text_channels, name="📢-announcements")
            or await cat_info.create_text_channel("📢┃announcements", overwrites=read_only_overwrite)
        )
        ch_updates = (
            discord.utils.get(cat_info.text_channels, name="🚀┃updates")
            or discord.utils.get(cat_info.text_channels, name="🚀-updates")
            or await cat_info.create_text_channel("🚀┃updates", overwrites=read_only_overwrite)
        )
        ch_status = (
            discord.utils.get(cat_info.text_channels, name="🟢┃status")
            or discord.utils.get(cat_info.text_channels, name="🟢-status")
            or await cat_info.create_text_channel("🟢┃status", overwrites=read_only_overwrite)
        )
        ch_faq = (
            discord.utils.get(cat_info.text_channels, name="❓┃faq")
            or discord.utils.get(cat_info.text_channels, name="❓-faq")
            or await cat_info.create_text_channel("❓┃faq", overwrites=read_only_overwrite)
        )

        # 3. Category 2: GX APP & STORE
        cat_keys = (
            discord.utils.get(guild.categories, name="🛒┃GX APP & KEYS")
            or discord.utils.get(guild.categories, name="🛒┃GX STORE")
            or discord.utils.get(guild.categories, name="🛒 GX APP & KEYS")
            or discord.utils.get(guild.categories, name="🛒 GX STORE")
            or await guild.create_category("🛒┃GX STORE")
        )
        ch_buy = (
            discord.utils.get(cat_keys.text_channels, name="💳┃how-to-buy")
            or discord.utils.get(cat_keys.text_channels, name="💳-how-to-buy")
            or await cat_keys.create_text_channel("💳┃how-to-buy", overwrites=read_only_overwrite)
        )
        ch_pricing = (
            discord.utils.get(cat_keys.text_channels, name="💲┃pricing")
            or discord.utils.get(cat_keys.text_channels, name="💲-pricing")
            or await cat_keys.create_text_channel("💲┃pricing", overwrites=read_only_overwrite)
        )
        ch_vouches = (
            discord.utils.get(cat_keys.text_channels, name="💬┃vouches")
            or discord.utils.get(cat_keys.text_channels, name="💬-vouches")
            or await cat_keys.create_text_channel("💬┃vouches")
        )
        
        # Customer Private Download Channel
        ch_downloads = (
            discord.utils.get(cat_keys.text_channels, name="📥┃downloads")
            or discord.utils.get(cat_keys.text_channels, name="📥-downloads")
            or await cat_keys.create_text_channel("📥┃downloads", overwrites=customer_only_overwrite)
        )

        # Purchase Channel
        ch_purchase = (
            discord.utils.get(cat_keys.text_channels, name="🛒┃purchase")
            or discord.utils.get(cat_keys.text_channels, name="🛒-purchase")
            or discord.utils.get(cat_keys.text_channels, name="purchase")
            or discord.utils.get(guild.text_channels, name="🛒┃purchase")
            or discord.utils.get(guild.text_channels, name="🛒-purchase")
            or discord.utils.get(guild.text_channels, name="purchase")
        )
        if not ch_purchase:
            ch_purchase = await cat_keys.create_text_channel("🛒┃purchase", overwrites=read_only_overwrite)

        # 4. Category 3: COMMUNITY
        cat_comm = (
            discord.utils.get(guild.categories, name="💬┃COMMUNITY")
            or discord.utils.get(guild.categories, name="💬 COMMUNITY")
            or await guild.create_category("💬┃COMMUNITY")
        )
        ch_general = (
            discord.utils.get(cat_comm.text_channels, name="💬┃general")
            or discord.utils.get(cat_comm.text_channels, name="💬-general")
        )
        if not ch_general:
            await cat_comm.create_text_channel("💬┃general")

        ch_bot = (
            discord.utils.get(cat_comm.text_channels, name="🤖┃bot-commands")
            or discord.utils.get(cat_comm.text_channels, name="🤖-bot-commands")
        )
        if not ch_bot:
            await cat_comm.create_text_channel("🤖┃bot-commands")

        ch_support_tickets = (
            discord.utils.get(cat_comm.text_channels, name="🛠️┃support-tickets")
            or discord.utils.get(cat_comm.text_channels, name="🛠️-support-tickets")
            or discord.utils.get(guild.text_channels, name="support-tickets")
        )
        if not ch_support_tickets:
            ch_support_tickets = await cat_comm.create_text_channel("🛠️┃support-tickets")

        ch_voice = (
            discord.utils.get(cat_comm.voice_channels, name="🔊┃General Voice")
            or discord.utils.get(cat_comm.voice_channels, name="🔊-General Voice")
        )
        if not ch_voice:
            await cat_comm.create_voice_channel("🔊┃General Voice")

        # 5. Category 4: STAFF ONLY
        cat_staff = (
            discord.utils.get(guild.categories, name="🔒┃STAFF ONLY")
            or discord.utils.get(guild.categories, name="🔒 STAFF ONLY")
            or await guild.create_category("🔒┃STAFF ONLY", overwrites=staff_only_overwrite)
        )
        ch_staff_chat = (
            discord.utils.get(cat_staff.text_channels, name="💬┃staff-chat")
            or discord.utils.get(cat_staff.text_channels, name="💬-staff-chat")
        )
        if not ch_staff_chat:
            await cat_staff.create_text_channel("💬┃staff-chat")

        ch_key_logs = (
            discord.utils.get(cat_staff.text_channels, name="📋┃key-logs")
            or discord.utils.get(cat_staff.text_channels, name="📋-key-logs")
        )
        if not ch_key_logs:
            await cat_staff.create_text_channel("📋┃key-logs")

        mod_logs_ch = (
            discord.utils.get(cat_staff.text_channels, name="📑┃mod-logs")
            or discord.utils.get(cat_staff.text_channels, name="📑-mod-logs")
            or await cat_staff.create_text_channel("📑┃mod-logs")
        )

        # 6. Category 5: FRIENDS LOUNGE
        friends_role = created_roles.get("🤝 Friends")
        friends_only_overwrite = {
            everyone: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)
        }
        if owner_role:
            friends_only_overwrite[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)
        if friends_role:
            friends_only_overwrite[friends_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)

        cat_friends = (
            discord.utils.get(guild.categories, name="🔒┃FRIENDS LOUNGE")
            or discord.utils.get(guild.categories, name="🔒 FRIENDS LOUNGE")
            or discord.utils.get(guild.categories, name="🔒 FRIENDS ONLY")
        )
        if not cat_friends:
            cat_friends = await guild.create_category("🔒┃FRIENDS LOUNGE", overwrites=friends_only_overwrite)
        else:
            try:
                await cat_friends.edit(overwrites=friends_only_overwrite)
            except Exception:
                pass

        if not discord.utils.get(cat_friends.text_channels, name="💬┃friends-chat") and not discord.utils.get(cat_friends.text_channels, name="💬-friends-chat"):
            await cat_friends.create_text_channel("💬┃friends-chat", overwrites=friends_only_overwrite)
        if not discord.utils.get(cat_friends.voice_channels, name="🔊┃Friends Voice") and not discord.utils.get(cat_friends.voice_channels, name="🔊-friends-vc") and not discord.utils.get(cat_friends.voice_channels, name="🔊-Friends Voice"):
            await cat_friends.create_voice_channel("🔊┃Friends Voice", overwrites=friends_only_overwrite)

        # Save settings to DB
        await self.bot.db.update_guild_setting(guild.id, "welcome_channel_id", ch_announcements.id)
        if mod_logs_ch:
            await self.bot.db.update_guild_setting(guild.id, "log_channel_id", mod_logs_ch.id)
            
        if member_role:
            await self.bot.db.update_guild_setting(guild.id, "autorole_id", member_role.id)
            for m in guild.members:
                if not m.bot and member_role not in m.roles:
                    try:
                        await m.add_roles(member_role, reason="Auto-assigning Member role to server members")
                    except Exception as e:
                        logger.warning(f"Could not assign member role to {m.name}: {e}")

        logo_path = os.path.join(ASSETS_DIR, "logo_avatar.jpg")
        hero_path = os.path.join(ASSETS_DIR, "hero_banner.jpg")
        pricing_path = os.path.join(ASSETS_DIR, "pricing_banner.png")
        payment_path = os.path.join(ASSETS_DIR, "payment_methods_banner.jpg")
        status_path = os.path.join(ASSETS_DIR, "status_banner.jpg")

        # 1. Rules Embed with Hero Banner & Logo Avatar
        rules_embed = discord.Embed(
            title="📜 Server Rules & Community Guidelines",
            description=(
                "Welcome to **GX App** — *Control Beyond Limits.*\n"
                "Please adhere to our official community rules and software guidelines:\n\n"
                "1. **Be Respectful**: Zero tolerance for toxicity, harassment, racism, or hate speech.\n"
                "2. **No Spamming**: Keep discussions organized within their designated channels.\n"
                "3. **License Security**: Do **not** share, leak, crack, or resell license keys. Keys are hardware-locked.\n"
                "4. **Orders & Support Protocol**:\n"
                "   • **To purchase keys**: Head over to **`#🛒-purchase`** and click **`🛒 Purchase Key`**.\n"
                "   • **For technical support or HWID resets**: Head to **`#🛠️-support-tickets`** and click **`🔧 Request Support`**.\n"
                "5. **Terms of Service**: Strictly adhere to Discord TOS and GX community policies at all times."
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        rules_embed.set_footer(text="GX Community Guidelines • Est. 2026 • Control Beyond Limits")
        rules_files = []
        if os.path.exists(hero_path):
            rules_files.append(discord.File(hero_path, filename="hero_banner.jpg"))
            rules_embed.set_image(url="attachment://hero_banner.jpg")
        if os.path.exists(logo_path):
            rules_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            rules_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_rules, self.bot, rules_embed, rules_files)

        # 2. Live Status Embed with Status Banner & Logo Avatar
        status_embed = discord.Embed(
            title="🟢 GX Software Status: ONLINE & UNDETECTED",
            description=(
                "### ⚡ Current System Health & Operational Status\n\n"
                "• **Software Core**: 🟢 **ONLINE & UNDETECTED**\n"
                "• **License Server**: 🟢 **OPERATIONAL (0ms Latency)**\n"
                "• **Supported OS**: Windows 10 & 11 (64-bit)\n"
                "• **Software Build**: `v1.11 (Latest Undetected)`\n"
                "• **Key Verification**: 24/7 Automated Activation\n\n"
                "> 🛡️ *All subscriptions and software features are running with optimal performance.*"
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        status_embed.set_footer(text="GX Status • Fast • Secure • Global • Use /set-status to update")
        status_files = []
        if os.path.exists(status_path):
            status_files.append(discord.File(status_path, filename="status_banner.jpg"))
            status_embed.set_image(url="attachment://status_banner.jpg")
        if os.path.exists(logo_path):
            status_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            status_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_status, self.bot, status_embed, status_files)

        # 3. Downloads Panel Embed with Logo Avatar
        download_embed = discord.Embed(
            title="📥 GX App Customer Downloads & Setup Guide",
            description=(
                "Welcome **⭐ Key Holder**! Here are your software downloads and setup requirements:\n\n"
                "**1. Software Package**: Your download link will be provided directly in your private purchase ticket.\n\n"
                "**2. System Requirements**:\n"
                "• Windows 10 / 11 (64-bit)\n"
                "• Visual C++ Redistributable (Latest x64)\n"
                "• DirectX 11 / 12 Runtimes\n\n"
                "**3. HWID Binding**:\n"
                "Your key binds to your computer upon first login. If you change hardware, request an HWID reset in **`#🛠️-support-tickets`**."
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        download_embed.set_footer(text="GX Customer Downloads • Strictly Private")
        download_files = []
        if os.path.exists(logo_path):
            download_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            download_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_downloads, self.bot, download_embed, download_files)

        # 4. Pricing Channel Embed with Pricing Graphic & Logo Avatar
        pricing_embed = discord.Embed(
            title="💲 GX App — Subscription Plans",
            description=(
                "Review our official subscription plans and features above.\n\n"
                "🛒 **Ready to purchase?** Head over to **`#🛒-purchase`** and click **`🛒 Purchase Key`** to open your private order ticket!"
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        pricing_embed.set_footer(text="GX Subscription Plans • Est. 2026 • Speed • Control • Precision • Freedom")
        pricing_files = []
        if os.path.exists(pricing_path):
            pricing_files.append(discord.File(pricing_path, filename="pricing_banner.png"))
            pricing_embed.set_image(url="attachment://pricing_banner.png")
        if os.path.exists(logo_path):
            pricing_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            pricing_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_pricing, self.bot, pricing_embed, pricing_files)

        # 5. How-To-Buy Channel Embed with Payment Methods Graphic & Logo Avatar
        buy_embed = discord.Embed(
            title="💳 How to Purchase GX Software",
            description=(
                "### 📋 How to Order:\n"
                "1. Choose your plan from our available options in **`#💲┃pricing`**.\n"
                "2. Head over to **`#🛒┃purchase`** and click **`🛒 Purchase Key`**.\n"
                "3. Select your desired plan and payment method in the order form.\n"
                "4. A private ticket and voice channel will open immediately for staff to process your key!"
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        buy_embed.set_footer(text="GX Menu • Fast • Secure • Global • Choose your preferred payment method")
        buy_files = []
        if os.path.exists(payment_path):
            buy_files.append(discord.File(payment_path, filename="payment_methods_banner.jpg"))
            buy_embed.set_image(url="attachment://payment_methods_banner.jpg")
        if os.path.exists(logo_path):
            buy_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            buy_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_buy, self.bot, buy_embed, buy_files)

        # 6. FAQ Channel Embed with Logo Avatar
        faq_embed = discord.Embed(
            title="❓ Frequently Asked Questions (FAQ)",
            description=(
                "**Q: How do I purchase a license key?**\n"
                "A: Head over to **`#🛒┃purchase`** and click **`🛒 Purchase Key`**.\n\n"
                "**Q: What payment methods do you accept?**\n"
                "A: We accept **PayPal, Binance Pay, InstaPay, Vodafone Cash, Etisalat Cash, Orange Cash, Telda, and TapTap Send**!\n\n"
                "**Q: What are the prices in EGP?**\n"
                "A: Monthly is **350 EGP** (`$6.99 USD`) and Lifetime is **750 EGP** (`$14.99 USD`).\n\n"
                "**Q: Where do I download the application?**\n"
                "A: Once your key purchase is confirmed, the **`#📥┃downloads`** channel will be unlocked for you!\n\n"
                "**Q: Can I use my key on another PC?**\n"
                "A: Keys are HWID-locked to 1 machine. If you switch hardware, open a ticket in **`#🛠️┃support-tickets`** to request an HWID reset."
            ),
            color=discord.Color.from_rgb(88, 28, 135)
        )
        faq_embed.set_footer(text="GX FAQ • Fast • Secure • Global")
        faq_files = []
        if os.path.exists(logo_path):
            faq_files.append(discord.File(logo_path, filename="logo_avatar.jpg"))
            faq_embed.set_thumbnail(url="attachment://logo_avatar.jpg")
        await clear_and_send(ch_faq, self.bot, faq_embed, faq_files)

        ch_support_tickets = (
            discord.utils.get(cat_comm.text_channels, name="🛠️┃support-tickets")
            or discord.utils.get(cat_comm.text_channels, name="🛠️-support-tickets")
            or discord.utils.get(guild.text_channels, name="support-tickets")
        )
        if not ch_support_tickets:
            ch_support_tickets = await cat_comm.create_text_channel("🛠️┃support-tickets", overwrites=read_only_overwrite)

        # Deploy Purchase Panel in #🛒┃purchase & Support Panel in #🛠️┃support-tickets
        await deploy_v2_purchase_panel(self.bot, ch_purchase)
        await deploy_v2_support_panel(self.bot, ch_support_tickets)

        logger.info(f"Full GX server setup completed for guild: {guild.name}")

    @app_commands.command(name="setup-gx-server", description="Manually trigger building/updating the complete GX App server layout.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_gx_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await self.build_full_gx_server(interaction.guild)
        summary_container = make_v2_container(
            text_content=(
                "### 🎉 GX Server Structure Successfully Built!\n\n"
                "The entire GX App server layout (categories, channels, roles, rules, pricing, graphics, and ticket button panel) has been updated!"
            ),
            footer_text="GX Server Deployment",
            accent_color=NEON_PURPLE_COLOR
        )
        await send_v2_followup(interaction, [summary_container], ephemeral=False)

    @app_commands.command(name="update-server-icon", description="Apply the neon GX circular logo to the server icon.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_server_icon(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        logo_path = os.path.join(ASSETS_DIR, "logo_avatar.jpg")
        if not os.path.exists(logo_path):
            err_c = make_v2_container("❌ Logo file not found in assets directory.", accent_color=RED_COLOR)
            return await send_v2_followup(interaction, [err_c], ephemeral=True)

        try:
            with open(logo_path, "rb") as f:
                await interaction.guild.edit(icon=f.read())
            c = make_v2_container("✅ Server icon updated with neon GX logo!", accent_color=GREEN_COLOR)
            await send_v2_followup(interaction, [c], ephemeral=True)
        except Exception as e:
            err_c = make_v2_container(f"❌ Failed to update server icon: {e}", accent_color=RED_COLOR)
            await send_v2_followup(interaction, [err_c], ephemeral=True)

    @app_commands.command(name="setup-friends", description="Create or reset the private Friends role, text channel, and voice channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_friends(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=False)

        friends_role = discord.utils.get(guild.roles, name="🤝 Friends") or discord.utils.get(guild.roles, name="Friends")
        if not friends_role:
            friends_role = await guild.create_role(name="🤝 Friends", color=discord.Color.from_rgb(147, 51, 234), hoist=True)

        owner_role = discord.utils.get(guild.roles, name="👑 Owner")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False),
            friends_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True, manage_channels=True)
        }
        if owner_role:
            overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, view_channel=True)

        cat = (
            discord.utils.get(guild.categories, name="🔒┃FRIENDS LOUNGE")
            or discord.utils.get(guild.categories, name="🔒 FRIENDS LOUNGE")
            or discord.utils.get(guild.categories, name="🔒 FRIENDS ONLY")
        )
        if not cat:
            cat = await guild.create_category("🔒┃FRIENDS LOUNGE", overwrites=overwrites)
        else:
            await cat.edit(overwrites=overwrites)

        txt = (
            discord.utils.get(cat.text_channels, name="💬┃friends-chat")
            or discord.utils.get(cat.text_channels, name="💬-friends-chat")
            or await cat.create_text_channel("💬┃friends-chat", overwrites=overwrites)
        )
        vc = (
            discord.utils.get(cat.voice_channels, name="🔊┃Friends Voice")
            or discord.utils.get(cat.voice_channels, name="🔊-Friends Voice")
            or discord.utils.get(cat.voice_channels, name="🔊-friends-vc")
            or await cat.create_voice_channel("🔊┃Friends Voice", overwrites=overwrites)
        )

        text_content = (
            "### 🤝 Friends Lounge Ready!\n\n"
            f"> **Role:** {friends_role.mention}\n"
            f"> **Private Text Channel:** {txt.mention}\n"
            f"> **Private Voice Channel:** {vc.mention}\n\n"
            "Only **👑 Owner** and members with the **🤝 Friends** role have access!"
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Community", accent_color=DEFAULT_ACCENT_COLOR)
        await send_v2_followup(interaction, [container], ephemeral=False)

    @app_commands.command(name="add-friend", description="Assign the Friends role to a member.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="The user to add to Friends")
    async def add_friend(self, interaction: discord.Interaction, member: discord.Member):
        guild = interaction.guild
        friends_role = discord.utils.get(guild.roles, name="🤝 Friends") or discord.utils.get(guild.roles, name="Friends")
        if not friends_role:
            friends_role = await guild.create_role(name="🤝 Friends", color=discord.Color.from_rgb(155, 89, 182), hoist=True)

        await member.add_roles(friends_role, reason=f"Added to Friends by {interaction.user}")
        c = make_v2_container(f"✅ Added {member.mention} to {friends_role.mention}!", accent_color=GREEN_COLOR)
        await send_v2_interaction_response(interaction, [c], ephemeral=False)

    @app_commands.command(name="generatekey", description="Generate a new license key for GX App.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(duration_days="Duration of the key in days (e.g. 30)")
    async def generate_key(self, interaction: discord.Interaction, duration_days: int = 30):
        key = self.generate_random_key()
        await self.bot.db.add_license_key(
            guild_id=interaction.guild_id,
            key=key,
            duration_days=duration_days,
            created_by=interaction.user.id
        )

        text_content = (
            f"### 🔑 License Key Generated ({duration_days} Days)\n\n"
            f"> **Key Code:** `{key}`\n"
            f"> **Duration:** `{duration_days} Days`\n"
            f"> **Created By:** {interaction.user.mention}"
        )
        container = make_v2_container(
            text_content=text_content,
            footer_text="Share this key with customer to redeem with /redeem",
            accent_color=0xFFD700
        )
        await send_v2_interaction_response(interaction, [container], ephemeral=True)

    @app_commands.command(name="redeem", description="Redeem your GX App license key to gain Key Holder role & access.")
    @app_commands.describe(key="Your license key (e.g. GX-XXXX-XXXX-XXXX-XXXX)")
    async def redeem_key(self, interaction: discord.Interaction, key: str):
        key_clean = key.strip().upper()
        result = await self.bot.db.redeem_license_key(interaction.guild_id, key_clean, interaction.user.id)

        if not result:
            err_c = make_v2_container("❌ **Invalid or Already Used Key.** Please check your key or contact support.", accent_color=RED_COLOR)
            return await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

        key_role = discord.utils.get(interaction.guild.roles, name="⭐ Key Holder")
        if key_role and isinstance(interaction.user, discord.Member):
            try:
                await interaction.user.add_roles(key_role, reason=f"Redeemed key {key_clean}")
            except discord.Forbidden:
                pass

        text_content = (
            f"### 🎉 License Key Redeemed!\n\n"
            f"Congratulations {interaction.user.mention}! Your key has been successfully activated.\n\n"
            f"> **Key Plan:** `{result['duration_days']} Days Access`\n"
            f"> **Granted Role:** {key_role.mention if key_role else 'Key Holder'}"
        )
        container = make_v2_container(text_content=text_content, footer_text="GX Key Activation", accent_color=GREEN_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=True)

        key_log_ch = discord.utils.get(interaction.guild.text_channels, name="📋-key-logs")
        if key_log_ch:
            log_text = (
                "### 🔑 Key Redeemed Notice\n\n"
                f"> **User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"> **Key Code:** `{key_clean}`\n"
                f"> **Duration:** `{result['duration_days']} Days`"
            )
            log_c = make_v2_container(text_content=log_text, footer_text="GX Security", accent_color=BLUE_COLOR)
            await send_v2_channel_message(key_log_ch, [log_c])

    @app_commands.command(name="listkeys", description="List generated license keys for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_keys(self, interaction: discord.Interaction):
        keys = await self.bot.db.get_license_keys(interaction.guild_id)
        if not keys:
            c = make_v2_container("ℹ️ No license keys have been generated yet.", accent_color=DEFAULT_ACCENT_COLOR)
            return await send_v2_interaction_response(interaction, [c], ephemeral=True)

        lines = [f"### 🔑 License Keys Summary ({len(keys)})\n"]
        for k in keys[:15]:
            status = f"✅ Used by <@{k['used_by']}>" if k['used_by'] else "🟢 Available"
            lines.append(f"> • `{k['key']}` ({k['duration_days']}d): {status}")

        container = make_v2_container(text_content="\n".join(lines), footer_text="GX License Database", accent_color=BLUE_COLOR)
        await send_v2_interaction_response(interaction, [container], ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            err_c = make_v2_container("❌ You must be an Administrator to run this setup command.", accent_color=RED_COLOR)
            await send_v2_interaction_response(interaction, [err_c], ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerSetupCog(bot))
