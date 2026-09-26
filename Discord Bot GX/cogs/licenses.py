# ============================================================================
# GX MENU — LICENSE MANAGEMENT COG (DISCORD COMPONENTS V2 — 100% ENGLISH)
# Syncs directly with E:\gx website\data\licenses.json & Client Web Portal
# Target Client Role ID: 1547640724604850186
# Staff Role ID:         1547640722013036637
# Log Channel ID:        1547753183424806983
# ============================================================================
import os
import json
import time
import datetime
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, Dict, Any

import config
from v2_helpers import (
    IS_COMPONENTS_V2,
    NEON_PURPLE_COLOR,
    ORANGE_COLOR,
    RED_COLOR,
    GREEN_COLOR,
    make_v2_container,
    send_v2_channel_message,
    edit_v2_channel_message,
    send_v2_interaction_response,
    send_v2_followup,
    update_v2_interaction_response,
    send_v2_modal_response
)

logger = logging.getLogger("discord_bot.licenses")

import urllib.request
import urllib.parse
import secrets
import string

CF_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL", "https://tight-base-cfefgx-auth.mahmoudgam3r369.workers.dev")
CF_ADMIN_SECRET = os.getenv("CLOUDFLARE_ADMIN_SECRET", "gxdev123")

def generate_random_key(plan: str = "Lifetime") -> str:
    chars = string.ascii_uppercase + string.digits
    prefix = "GX-MNTH" if plan == "Monthly" else "GX-LIFE"
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    part3 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"{prefix}-{part1}-{part2}-{part3}"

def sync_key_with_cloudflare(key: str, days: int = 0, action: str = "add") -> bool:
    if not CF_WORKER_URL or not key:
        return False
    try:
        query = urllib.parse.urlencode({
            "action": action,
            "admin": CF_ADMIN_SECRET,
            "key": key,
            "days": days
        })
        url = f"{CF_WORKER_URL}/?{query}"
        req = urllib.request.Request(url, headers={"User-Agent": "GX-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("success", False)
    except Exception as e:
        logger.warning(f"Cloudflare Worker sync error: {e}")
        return False

def read_licenses() -> Dict[str, Any]:
    """Load licenses from the shared JSON file."""
    try:
        if not os.path.exists(config.LICENSES_FILE_PATH):
            return {}
        with open(config.LICENSES_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading licenses file: {e}")
        return {}

def write_licenses(data: Dict[str, Any]) -> bool:
    """Save licenses to the shared JSON file."""
    try:
        os.makedirs(os.path.dirname(config.LICENSES_FILE_PATH), exist_ok=True)
        with open(config.LICENSES_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing licenses file: {e}")
        return False

def is_authorized_staff(interaction: discord.Interaction) -> bool:
    """Check if the user is Server Owner or possesses the Staff Role."""
    if interaction.guild and interaction.guild.owner_id == interaction.user.id:
        return True
    if isinstance(interaction.user, discord.Member):
        for r in interaction.user.roles:
            if r.id == config.STAFF_ROLE_ID:
                return True
    return False

def build_v2_license_container(target_user_id: int, license_data: dict) -> dict:
    """Build the official Components V2 license container with interactive buttons inside."""
    status = license_data.get("status", "active")
    is_held = status == "onhold"
    is_revoked = status == "revoked"
    plan = license_data.get("plan", "Monthly")
    is_monthly = plan == "Monthly"

    accent_color = NEON_PURPLE_COLOR
    if is_held:
        accent_color = ORANGE_COLOR
    elif is_revoked:
        accent_color = RED_COLOR

    assigned_at = license_data.get("assignedAt")
    if assigned_at:
        try:
            assigned_dt = datetime.datetime.fromisoformat(assigned_at.replace("Z", "+00:00"))
            assigned_unix = int(assigned_dt.timestamp())
        except Exception:
            assigned_unix = int(time.time())
    else:
        assigned_unix = int(time.time())

    expires_at = license_data.get("expiresAt")
    expires_unix = None
    if expires_at:
        try:
            expires_dt = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            expires_unix = int(expires_dt.timestamp())
        except Exception:
            pass

    plan_title = (
        "Monthly License (30 Days) — $6.99 / 350 EGP"
        if is_monthly
        else "Lifetime License (VIP) — $14.99 / 750 EGP"
    )
    status_str = (
        "⏸️ ON-HOLD / FROZEN"
        if is_held
        else ("🔴 DELETED / REVOKED" if is_revoked else "🟢 ACTIVE")
    )
    raw_key = license_data.get("key", "N/A")

    text_lines = [
        "### ⚡ GX MENU — LICENSE MANAGEMENT CARD\n",
        f"> **DISCORD USER MENTION :** <@{target_user_id}>",
        f"> **PLAN :** `{plan_title}`",
        f"> **STATUS :** {status_str}",
        f"> **KEY :** ||{raw_key}||",
        f"> **ACTIVATION TIME :** <t:{assigned_unix}:f> (<t:{assigned_unix}:R>)",
        f"> **EXPIRATION :** " + (f"<t:{expires_unix}:f> (<t:{expires_unix}:R>)" if expires_unix else "♾️ NEVER (UNLIMITED LIFETIME VIP)")
    ]

    if is_held and license_data.get("holdReason"):
        text_lines.append(f"> **HOLD REASON :** `{license_data['holdReason']}`")

    assigned_by = license_data.get("assignedById")
    assigned_by_text = f"<@{assigned_by}>" if assigned_by else license_data.get("assignedBy", "Staff")
    text_lines.append(f"> **ASSIGNED BY :** {assigned_by_text}")

    components_inside = [
        {
            "type": 10,  # TextDisplay
            "content": "\n".join(text_lines)
        },
        {
            "type": 14,  # Separator
            "divider": True,
            "spacing": 1
        }
    ]

    if is_revoked:
        components_inside.append({
            "type": 1,  # ActionRow
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "label": "HOLD / FREEZE KEY",
                    "custom_id": f"dis_hold_{target_user_id}",
                    "disabled": True,
                    "emoji": {"name": "⏸️"}
                },
                {
                    "type": 2,
                    "style": 4,
                    "label": "DELETED",
                    "custom_id": f"dis_del_{target_user_id}",
                    "disabled": True,
                    "emoji": {"name": "🗑️"}
                }
            ]
        })
    else:
        components_inside.append({
            "type": 1,  # ActionRow inside container
            "components": [
                {
                    "type": 2,
                    "style": 3 if is_held else 2,  # Green (3) when held, Gray (2) when active
                    "label": "UNFREEZE / REACTIVATE" if is_held else "HOLD / FREEZE KEY",
                    "custom_id": f"license_hold_{target_user_id}",
                    "emoji": {"name": "▶️" if is_held else "⏸️"}
                },
                {
                    "type": 2,
                    "style": 4,  # Danger Red
                    "label": "DELETE KEY",
                    "custom_id": f"license_delete_{target_user_id}",
                    "emoji": {"name": "🗑️"}
                }
            ]
        })

    return {
        "type": 17,  # Container
        "accent_color": accent_color,
        "components": components_inside
    }


class LicensesCog(commands.Cog, name="License Management"):
    """License assignment, interactive components v2 controls, and KeyAuth portal synchronization."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check_subscription_expiries.start()

    async def cog_unload(self):
        self.check_subscription_expiries.cancel()

    @tasks.loop(minutes=30)
    async def check_subscription_expiries(self):
        """Background monitor that alerts customers before subscription expiry and auto-revokes upon expiry."""
        try:
            licenses = read_licenses()
            if not licenses:
                return

            now = datetime.datetime.now(datetime.timezone.utc)
            now_ts = int(now.timestamp())
            modified = False

            guild = self.bot.get_guild(config.GUILD_ID) if hasattr(config, "GUILD_ID") else None
            if not guild and self.bot.guilds:
                guild = self.bot.guilds[0]

            for key_id, lic in list(licenses.items()):
                # Only check monthly active licenses with expiresAt
                status = lic.get("status", "active")
                plan = lic.get("plan", "Monthly")
                expires_at = lic.get("expiresAt")

                if status not in ("active", "onhold") or plan != "Monthly" or not expires_at:
                    continue

                try:
                    exp_dt = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    exp_ts = int(exp_dt.timestamp())
                except Exception:
                    continue

                diff_seconds = exp_ts - now_ts
                target_user_id = lic.get("userId") or lic.get("owner_discord_id") or lic.get("discord_user_id") or (key_id if key_id.isdigit() else None)
                if not target_user_id:
                    continue

                # 1. EXPIRATION PASSED (diff <= 0)
                if diff_seconds <= 0 and status == "active":
                    lic["status"] = "expired"
                    lic["active"] = False
                    lic["expiredAt"] = now.isoformat()
                    modified = True
                    logger.info(f"License {key_id} for user {target_user_id} expired. Processing auto-revocation.")

                    # Remove client role from guild
                    if guild:
                        try:
                            member = guild.get_member(int(target_user_id)) or await guild.fetch_member(int(target_user_id))
                            if member:
                                client_role = guild.get_role(config.CLIENT_ROLE_ID)
                                if client_role and client_role in member.roles:
                                    await member.remove_roles(client_role, reason="GX Subscription Expired (30 Days Ended)")
                        except Exception as e:
                            logger.warning(f"Could not remove client role from expired user {target_user_id}: {e}")

                    # Dispatch DM to Customer
                    try:
                        u = await self.bot.fetch_user(int(target_user_id))
                        if u:
                            dm = u.dm_channel or await u.create_dm()
                            exp_container = make_v2_container(
                                text_content=(
                                    f"### ⏰ GX App — Subscription Expired\n\n"
                                    f"Hello **{u.name}**, your **Monthly License** subscription has ended.\n\n"
                                    "> ⚠️ *Your access to GX App and VIP Client channels has been paused.*\n\n"
                                    "**Want to continue enjoying GX App?**\n"
                                    "• Renew your **Monthly License ($6.99 / 350 EGP)**\n"
                                    "• Or upgrade to **👑 Lifetime License ($24.99 / 1250 EGP)** for permanent access with zero monthly renewals!\n\n"
                                    "Head over to `#🛒┃purchase` in our server to renew instantly."
                                ),
                                footer_text="GX License Management • Renewal Notification",
                                accent_color=RED_COLOR
                            )
                            await send_v2_channel_message(dm, [exp_container])
                    except Exception as dm_err:
                        logger.warning(f"Could not send expiry DM to user {target_user_id}: {dm_err}")

                    # Post mod log
                    if guild:
                        mod_logs = discord.utils.get(guild.text_channels, name="📑┃mod-logs") or discord.utils.get(guild.text_channels, name="mod-logs")
                        if mod_logs:
                            log_container = make_v2_container(
                                text_content=(
                                    f"### ⏰ Subscription Expired — Role Revoked\n\n"
                                    f"• **Customer**: <@{target_user_id}> (`{target_user_id}`)\n"
                                    f"• **Plan**: Monthly (30 Days)\n"
                                    f"• **Key**: `{lic.get('key', key_id)}`\n"
                                    f"• **Expired At**: <t:{now_ts}:F>"
                                ),
                                footer_text="GX Automated Subscription System",
                                accent_color=RED_COLOR
                            )
                            await send_v2_channel_message(mod_logs, [log_container])

                # 2. 24-HOUR URGENT ALERT (0 < diff <= 86400)
                elif 0 < diff_seconds <= 86400 and not lic.get("notified_1d"):
                    lic["notified_1d"] = True
                    modified = True
                    try:
                        u = await self.bot.fetch_user(int(target_user_id))
                        if u:
                            dm = u.dm_channel or await u.create_dm()
                            hours_left = max(1, int(diff_seconds // 3600))
                            alert_container = make_v2_container(
                                text_content=(
                                    f"### ⚠️ GX App Subscription Expires in ~{hours_left} Hours!\n\n"
                                    f"Hey **{u.name}**, this is an urgent reminder that your **GX App Monthly License** expires <t:{exp_ts}:R>!\n\n"
                                    "To prevent any disruption to your application access and loader credentials, renew now or upgrade to Lifetime:\n\n"
                                    "👉 Head to `#🛒┃purchase` in the GX server to renew your license."
                                ),
                                footer_text="GX Renewal System • 24h Expiry Warning",
                                accent_color=ORANGE_COLOR
                            )
                            await send_v2_channel_message(dm, [alert_container])
                            logger.info(f"Dispatched 24h expiry reminder to user {target_user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to dispatch 24h alert DM to {target_user_id}: {e}")

                # 3. 3-DAY ADVANCE ALERT (86400 < diff <= 3 * 86400)
                elif 86400 < diff_seconds <= 3 * 86400 and not lic.get("notified_3d"):
                    lic["notified_3d"] = True
                    modified = True
                    try:
                        u = await self.bot.fetch_user(int(target_user_id))
                        if u:
                            dm = u.dm_channel or await u.create_dm()
                            days_left = max(1, int(diff_seconds // 86400))
                            alert_container = make_v2_container(
                                text_content=(
                                    f"### ⏰ GX App Subscription Expiry Reminder (~{days_left} Days Left)\n\n"
                                    f"Hello **{u.name}**, your **GX App Monthly License** is scheduled to expire <t:{exp_ts}:R> (<t:{exp_ts}:F>).\n\n"
                                    "We hope you are enjoying GX App! When your subscription ends, you can easily renew your plan or upgrade to permanent Lifetime access.\n\n"
                                    "Visit `#🛒┃purchase` whenever you are ready."
                                ),
                                footer_text="GX Subscription Service • Friendly Reminder",
                                accent_color=NEON_PURPLE_COLOR
                            )
                            await send_v2_channel_message(dm, [alert_container])
                            logger.info(f"Dispatched 3-day expiry reminder to user {target_user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to dispatch 3d alert DM to {target_user_id}: {e}")

            if modified:
                write_licenses(licenses)

        except Exception as err:
            logger.error(f"Error in check_subscription_expiries task: {err}", exc_info=True)

    @check_subscription_expiries.before_loop
    async def before_check_subscription_expiries(self):
        await self.bot.wait_until_ready()

    assign_group = app_commands.Group(name="assign", description="GX MENU Client & License Manager")
    key_group = app_commands.Group(name="key", description="GX License Key Inspection & Management Operations")

    @assign_group.command(name="key", description="Assign a license key to a customer (auto-generates if empty), grant Client role, and post V2 card.")
    @app_commands.describe(
        user="Target customer",
        key="License key (Leave empty to auto-generate a fresh Cloudflare key)",
        plan="Subscription plan matching website pricing"
    )
    @app_commands.choices(plan=[
        app_commands.Choice(name="Monthly License (30 Days) — $6.99 / 350 EGP", value="Monthly"),
        app_commands.Choice(name="Lifetime License (VIP) — $14.99 / 750 EGP", value="Lifetime"),
    ])
    async def assign_key(self, interaction: discord.Interaction, user: discord.Member, key: Optional[str] = None, plan: Optional[str] = "Monthly"):
        await interaction.response.defer(ephemeral=True)

        # Check Staff Permission
        if not is_authorized_staff(interaction):
            denied_container = make_v2_container(
                text_content=(
                    "### ⛔ Access Denied!\n"
                    "You are not authorized to use this command.\n"
                    f"This command is strictly reserved for Staff Members with role: <@&{config.STAFF_ROLE_ID}>"
                ),
                footer_text="GX Security Clearance",
                accent_color=RED_COLOR
            )
            return await send_v2_followup(interaction, [denied_container], ephemeral=True)

        raw_key = key.strip() if key else generate_random_key(plan)
        sync_key_with_cloudflare(raw_key, 30 if plan == "Monthly" else 0, "add")

        now = datetime.datetime.now(datetime.timezone.utc)
        assigned_at = now.isoformat()
        expires_at = None

        if plan == "Monthly":
            expires_at = (now + datetime.timedelta(days=30)).isoformat()

        licenses = read_licenses()
        new_license = {
            "userId": str(user.id),
            "username": str(user),
            "key": raw_key,
            "plan": plan,
            "status": "active",
            "holdReason": None,
            "assignedAt": assigned_at,
            "expiresAt": expires_at,
            "assignedBy": str(interaction.user),
            "assignedById": str(interaction.user.id)
        }

        # 1. Grant Client Role
        role_granted = False
        client_role = interaction.guild.get_role(config.CLIENT_ROLE_ID) if interaction.guild else None
        if client_role:
            try:
                await user.add_roles(client_role, reason=f"Assigned {plan} license by {interaction.user}")
                role_granted = True
            except Exception as e:
                logger.warning(f"Could not grant Client role: {e}")

        # 2. Direct Message Customer in English
        dm_sent = False
        assigned_unix = int(now.timestamp())
        expires_unix = int(datetime.datetime.fromisoformat(expires_at).timestamp()) if expires_at else None
        is_monthly = plan == "Monthly"

        try:
            dm_text = (
                f"### ⚡ GX MENU — Your License Key Has Been Assigned!\n\n"
                f"Welcome **{user.name}**! Your subscription has been activated in the system. "
                "You now have immediate access to the Client Portal.\n\n"
                f"> **Your License Key:** `{raw_key}`\n"
                f"> **Subscription Plan:** `{'Monthly License (30 Days) — $6.99 / 350 EGP' if is_monthly else 'Lifetime License (VIP) — $14.99 / 750 EGP'}`\n"
                f"> **Status:** 🟢 `ACTIVE`\n"
                f"> **Activated At:** <t:{assigned_unix}:f>\n"
                f"> **Expires At:** " + (f"<t:{expires_unix}:f> (<t:{expires_unix}:R>)" if expires_unix else "♾️ `NEVER (LIFETIME ACCESS)`") + "\n\n"
                f"🔗 **[Click Here to Open Client Portal]({config.PORTAL_URL})**\n\n"
                "-# Key is encrypted and automatically HWID-locked upon first loader injection."
            )
            dm_container = make_v2_container(
                text_content=dm_text,
                footer_text="GX Menu • Automated License Delivery",
                accent_color=NEON_PURPLE_COLOR
            )
            # Send DM using client HTTP route or channel message
            dm_channel = user.dm_channel or await user.create_dm()
            await send_v2_channel_message(dm_channel, [dm_container])
            dm_sent = True
        except Exception as dm_err:
            logger.warning(f"Failed to deliver DM to {user}: {dm_err}")

        # 3. Dispatch Components V2 Container to Log Channel 1547753183424806983
        channel_sent = False
        log_channel = self.bot.get_channel(config.ASSIGN_LOG_CHANNEL_ID)
        if not log_channel:
            try:
                log_channel = await self.bot.fetch_channel(config.ASSIGN_LOG_CHANNEL_ID)
            except Exception:
                pass

        if log_channel:
            try:
                v2_container = build_v2_license_container(user.id, new_license)
                sent_msg = await send_v2_channel_message(log_channel, [v2_container])
                channel_sent = True
                new_license["logMessageId"] = str(sent_msg["id"])
                new_license["logChannelId"] = str(log_channel.id)
            except Exception as log_err:
                logger.warning(f"Failed to post to log channel: {log_err}")

        # 4. Save to shared licenses.json
        licenses[str(user.id)] = new_license
        write_licenses(licenses)

        # 5. Reply to Staff Ephemerally in Components V2 Container
        reply_text = (
            "### ✅ License Assigned & Components V2 Card Dispatched\n\n"
            f"> **Customer:** {user.mention} (`{user}`)\n"
            f"> **Plan:** `{'Monthly (30 Days)' if is_monthly else 'Lifetime (VIP)'}`\n"
            f"> **Key:** ||`{raw_key}`||\n"
            f"> **Expires:** " + (f"<t:{expires_unix}:f> (<t:{expires_unix}:R>)" if expires_unix else "♾️ `Lifetime (Never)`") + "\n\n"
            f"• **Client Role:** `{'✅ GRANTED' if role_granted else '⚠️ CHECK PERMISSIONS'}`\n"
            f"• **Customer DM:** `{'✅ DELIVERED' if dm_sent else '⚠️ CLOSED DMS'}`\n"
            f"• **Channel Card:** `{'✅ Dispatched to <#' + str(config.ASSIGN_LOG_CHANNEL_ID) + '>' if channel_sent else '⚠️ CHECK LOG CHANNEL'}`"
        )
        staff_container = make_v2_container(
            text_content=reply_text,
            footer_text="GX License Management Engine",
            accent_color=GREEN_COLOR
        )
        return await send_v2_followup(interaction, [staff_container], ephemeral=True)

    @assign_group.command(name="hold", description="Place a license ON-HOLD / Suspended with reason.")
    @app_commands.describe(user="Target customer", reason="Reason for hold (e.g. Subscription Expired)")
    async def assign_hold(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_staff(interaction):
            denied_container = make_v2_container(
                text_content=f"⛔ **Access Denied!** Requires Staff Role <@&{config.STAFF_ROLE_ID}>.",
                accent_color=RED_COLOR
            )
            return await send_v2_followup(interaction, [denied_container], ephemeral=True)

        licenses = read_licenses()
        uid_str = str(user.id)
        if uid_str not in licenses:
            err_container = make_v2_container(
                text_content=f"⚠️ No active license record found for {user.mention}.",
                accent_color=ORANGE_COLOR
            )
            return await send_v2_followup(interaction, [err_container], ephemeral=True)

        rec = licenses[uid_str]
        rec["status"] = "onhold"
        rec["holdReason"] = reason
        rec["heldAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rec["heldBy"] = str(interaction.user)
        write_licenses(licenses)

        # DM customer
        try:
            dm_channel = user.dm_channel or await user.create_dm()
            hold_dm = make_v2_container(
                text_content=(
                    f"### GX MENU — License Status Notice (ON-HOLD)\n\n"
                    f"Dear **{user.name}**, your license has been temporarily suspended in the Client Portal.\n\n"
                    f"> **Hold Reason:** `{reason}`\n\n"
                    "Please contact staff or open a support ticket in our official Discord server if you have any questions."
                ),
                footer_text="GX Security & Enforcement",
                accent_color=ORANGE_COLOR
            )
            await send_v2_channel_message(dm_channel, [hold_dm])
        except Exception:
            pass

        # Update channel log message
        log_msg_id = rec.get("logMessageId")
        log_ch_id = rec.get("logChannelId")
        if log_msg_id and log_ch_id:
            try:
                ch = self.bot.get_channel(int(log_ch_id)) or await self.bot.fetch_channel(int(log_ch_id))
                if ch:
                    updated_container = build_v2_license_container(user.id, rec)
                    await edit_v2_channel_message(ch, int(log_msg_id), [updated_container])
            except Exception as e:
                logger.warning(f"Could not update channel log: {e}")

        confirm_container = make_v2_container(
            text_content=f"⏸️ Subscription for {user.mention} is now **ON-HOLD**.\n> Reason: `{reason}`",
            footer_text="GX License Manager",
            accent_color=ORANGE_COLOR
        )
        return await send_v2_followup(interaction, [confirm_container], ephemeral=True)

    @assign_group.command(name="unhold", description="Reactivate an on-hold license to Active.")
    @app_commands.describe(user="Target customer")
    async def assign_unhold(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_staff(interaction):
            denied_container = make_v2_container(
                text_content=f"⛔ **Access Denied!** Requires Staff Role <@&{config.STAFF_ROLE_ID}>.",
                accent_color=RED_COLOR
            )
            return await send_v2_followup(interaction, [denied_container], ephemeral=True)

        licenses = read_licenses()
        uid_str = str(user.id)
        if uid_str not in licenses:
            err_container = make_v2_container(
                text_content=f"⚠️ No license record found for {user.mention}.",
                accent_color=ORANGE_COLOR
            )
            return await send_v2_followup(interaction, [err_container], ephemeral=True)

        rec = licenses[uid_str]
        rec["status"] = "active"
        rec["holdReason"] = None
        rec.pop("heldAt", None)
        rec.pop("heldBy", None)
        write_licenses(licenses)

        # DM customer
        try:
            dm_channel = user.dm_channel or await user.create_dm()
            unhold_dm = make_v2_container(
                text_content=(
                    f"### GX MENU — Your Subscription Has Been Reactivated!\n\n"
                    f"Dear **{user.name}**, the hold status has been lifted from your account. "
                    "You may now access the Client Portal and use your license key.\n\n"
                    f"🔗 **[Click Here to Access Client Portal]({config.PORTAL_URL})**"
                ),
                footer_text="GX Client Access",
                accent_color=GREEN_COLOR
            )
            await send_v2_channel_message(dm_channel, [unhold_dm])
        except Exception:
            pass

        # Update channel log message
        log_msg_id = rec.get("logMessageId")
        log_ch_id = rec.get("logChannelId")
        if log_msg_id and log_ch_id:
            try:
                ch = self.bot.get_channel(int(log_ch_id)) or await self.bot.fetch_channel(int(log_ch_id))
                if ch:
                    updated_container = build_v2_license_container(user.id, rec)
                    await edit_v2_channel_message(ch, int(log_msg_id), [updated_container])
            except Exception as e:
                logger.warning(f"Could not update channel log: {e}")

        confirm_container = make_v2_container(
            text_content=f"✅ Subscription for {user.mention} has been reactivated to **ACTIVE**.",
            footer_text="GX License Manager",
            accent_color=GREEN_COLOR
        )
        return await send_v2_followup(interaction, [confirm_container], ephemeral=True)

    @assign_group.command(name="revoke", description="Revoke key and remove client role.")
    @app_commands.describe(user="Target customer")
    async def assign_revoke(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_staff(interaction):
            denied_container = make_v2_container(
                text_content=f"⛔ **Access Denied!** Requires Staff Role <@&{config.STAFF_ROLE_ID}>.",
                accent_color=RED_COLOR
            )
            return await send_v2_followup(interaction, [denied_container], ephemeral=True)

        licenses = read_licenses()
        uid_str = str(user.id)
        if uid_str not in licenses:
            err_container = make_v2_container(
                text_content=f"⚠️ No license record found for {user.mention}.",
                accent_color=ORANGE_COLOR
            )
            return await send_v2_followup(interaction, [err_container], ephemeral=True)

        rec = licenses[uid_str]
        log_msg_id = rec.get("logMessageId")
        log_ch_id = rec.get("logChannelId")

        rec["status"] = "revoked"
        revoked_rec = dict(rec)
        licenses.pop(uid_str, None)
        write_licenses(licenses)

        # Remove Client Role
        client_role = interaction.guild.get_role(config.CLIENT_ROLE_ID) if interaction.guild else None
        if client_role and client_role in user.roles:
            try:
                await user.remove_roles(client_role, reason=f"License revoked by {interaction.user}")
            except Exception:
                pass

        # DM customer
        try:
            dm_channel = user.dm_channel or await user.create_dm()
            revoke_dm = make_v2_container(
                text_content=(
                    f"### GX MENU — License Key Revoked\n\n"
                    f"Dear **{user.name}**, your license key and Client role have been revoked by administration."
                ),
                footer_text="GX License Management",
                accent_color=RED_COLOR
            )
            await send_v2_channel_message(dm_channel, [revoke_dm])
        except Exception:
            pass

        # Update channel log message with disabled buttons
        if log_msg_id and log_ch_id:
            try:
                ch = self.bot.get_channel(int(log_ch_id)) or await self.bot.fetch_channel(int(log_ch_id))
                if ch:
                    disabled_container = build_v2_license_container(user.id, revoked_rec)
                    await edit_v2_channel_message(ch, int(log_msg_id), [disabled_container])
            except Exception:
                pass

        confirm_container = make_v2_container(
            text_content=f"🚫 License for {user.mention} has been completely revoked and Client role removed.",
            footer_text="GX License Manager",
            accent_color=RED_COLOR
        )
        return await send_v2_followup(interaction, [confirm_container], ephemeral=True)

    @assign_group.command(name="check", description="Inspect assigned license record & expiration.")
    @app_commands.describe(user="Target customer")
    async def assign_check(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        licenses = read_licenses()
        uid_str = str(user.id)
        if uid_str not in licenses:
            err_container = make_v2_container(
                text_content=f"ℹ️ No license found for {user.mention} in the system.",
                accent_color=NEON_PURPLE_COLOR
            )
            return await send_v2_followup(interaction, [err_container], ephemeral=True)

        rec = licenses[uid_str]
        status = rec.get("status", "active")
        is_held = status == "onhold"
        is_monthly = rec.get("plan") == "Monthly"

        assigned_at = rec.get("assignedAt")
        assigned_unix = int(time.time())
        if assigned_at:
            try:
                assigned_unix = int(datetime.datetime.fromisoformat(assigned_at.replace("Z", "+00:00")).timestamp())
            except Exception:
                pass

        expires_at = rec.get("expiresAt")
        expires_unix = None
        if expires_at:
            try:
                expires_unix = int(datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp())
            except Exception:
                pass

        text_content = (
            f"### 📋 License Record for {user.mention} ({user})\n\n"
            f"> **Assigned Key:** ||`{rec.get('key', 'N/A')}`||\n"
            f"> **Plan:** `{'Monthly License (30 Days) — $6.99 / 350 EGP' if is_monthly else 'Lifetime License (VIP) — $14.99 / 750 EGP'}`\n"
            f"> **Status:** `{'⏸️ ON-HOLD' if is_held else '🟢 ACTIVE'}`\n"
            f"> **Activation Time:** <t:{assigned_unix}:f> (<t:{assigned_unix}:R>)\n"
            f"> **Expiration Time:** " + (f"<t:{expires_unix}:f> (<t:{expires_unix}:R>)" if expires_unix else "♾️ `NEVER (UNLIMITED LIFETIME ACCESS)`") + "\n"
            f"> **Hold Reason:** `{rec.get('holdReason') or 'None'}`"
        )
        check_container = make_v2_container(
            text_content=text_content,
            footer_text="GX License Inspection",
            accent_color=ORANGE_COLOR if is_held else GREEN_COLOR
        )
        return await send_v2_followup(interaction, [check_container], ephemeral=True)

    @key_group.command(name="check", description="Lookup key details, ownership, status, and expiration.")
    @app_commands.describe(keycode="License key string to check (e.g. GX-XXXX-XXXX-XXXX)")
    async def key_check(self, interaction: discord.Interaction, keycode: str):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_staff(interaction):
            denied_container = make_v2_container(
                text_content=(
                    "### ⛔ Access Denied!\n"
                    "You are not authorized to use this command.\n"
                    f"This command is strictly reserved for Staff Members with role: <@&{config.STAFF_ROLE_ID}>"
                ),
                footer_text="GX Security Clearance",
                accent_color=RED_COLOR
            )
            return await send_v2_followup(interaction, [denied_container], ephemeral=True)

        clean_key = keycode.strip()
        licenses = read_licenses()
        found_uid = None
        found_rec = None

        for uid, rec in licenses.items():
            if rec.get("key", "").strip().lower() == clean_key.lower():
                found_uid = uid
                found_rec = rec
                break

        if found_rec:
            status = found_rec.get("status", "active")
            is_held = status == "onhold"
            is_revoked = status == "revoked"
            plan = found_rec.get("plan", "Monthly")
            is_monthly = plan == "Monthly"

            assigned_at = found_rec.get("assignedAt")
            assigned_unix = None
            if assigned_at:
                try:
                    assigned_unix = int(datetime.datetime.fromisoformat(assigned_at.replace("Z", "+00:00")).timestamp())
                except Exception:
                    pass

            expires_at = found_rec.get("expiresAt")
            expires_unix = None
            if expires_at:
                try:
                    expires_unix = int(datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp())
                except Exception:
                    pass

            accent_color = NEON_PURPLE_COLOR
            status_text = "🟢 ACTIVE"
            if is_held:
                accent_color = ORANGE_COLOR
                hold_reason = found_rec.get("holdReason") or "Unspecified"
                status_text = f"⏸️ ON-HOLD / FROZEN (`{hold_reason}`)"
            elif is_revoked:
                accent_color = RED_COLOR
                status_text = "🔴 DELETED / REVOKED"
            elif expires_unix and time.time() > expires_unix:
                accent_color = ORANGE_COLOR
                status_text = "⏳ EXPIRED"

            assigned_by = found_rec.get("assignedBy", "Staff")
            assigned_by_id = found_rec.get("assignedById")
            assigner_str = f"<@{assigned_by_id}>" if assigned_by_id else f"`{assigned_by}`"

            plan_str = "Monthly License (30 Days) — $6.99 / 350 EGP" if is_monthly else "Lifetime License (VIP) — $14.99 / 750 EGP"

            lines = [
                "### 🔍 GX Key Information & Ownership Card\n",
                f"> **KEY CODE :** `{clean_key}`",
                f"> **DISCORD USER MENTION :** <@{found_uid}> (`{found_rec.get('username', found_uid)}`)",
                f"> **PLAN :** `{plan_str}`",
                f"> **STATUS :** {status_text}",
                f"> **ACTIVATION TIME :** " + (f"<t:{assigned_unix}:f> (<t:{assigned_unix}:R>)" if assigned_unix else "`Unknown`"),
                f"> **EXPIRATION :** " + (f"<t:{expires_unix}:f> (<t:{expires_unix}:R>)" if expires_unix else "♾️ `NEVER (UNLIMITED LIFETIME VIP)`"),
                f"> **ASSIGNED BY :** {assigner_str}"
            ]
            if is_held and found_rec.get("holdReason"):
                lines.append(f"> **HOLD REASON :** `{found_rec['holdReason']}`")

            if interaction.guild and found_uid.isdigit():
                member = interaction.guild.get_member(int(found_uid))
                if member:
                    client_role = interaction.guild.get_role(config.CLIENT_ROLE_ID)
                    has_role = client_role in member.roles if client_role else False
                    lines.append(f"> **CLIENT ROLE IN SERVER :** `{'✅ ASSIGNED' if has_role else '❌ MISSING'}`")

            res_container = make_v2_container(
                text_content="\n".join(lines),
                footer_text="GX License Management Engine • Components V2",
                accent_color=accent_color
            )
            return await send_v2_followup(interaction, [res_container], ephemeral=True)

        # Check SQLite DB license_keys table
        db_key_data = await self.bot.db.get_key_info(clean_key)
        if db_key_data:
            used_by = db_key_data.get("used_by")
            used_status = f"✅ Redeemed by <@{used_by}>" if used_by else "🟢 Available (Unredeemed)"
            created_by = db_key_data.get("created_by")
            creator_str = f"<@{created_by}>" if created_by else "`System`"

            lines = [
                "### 🔍 GX Key Information (Database Record)\n",
                f"> **KEY CODE :** `{clean_key}`",
                f"> **DURATION :** `{db_key_data.get('duration_days', 30)} Days`",
                f"> **STATUS :** {used_status}",
                f"> **CREATED BY :** {creator_str}",
                f"> **CREATED AT :** `{db_key_data.get('created_at', 'N/A')}`",
                f"> **REDEEMED AT :** `{db_key_data.get('used_at') or 'Not yet redeemed'}`"
            ]
            res_container = make_v2_container(
                text_content="\n".join(lines),
                footer_text="GX License Database Record",
                accent_color=BLUE_COLOR if not used_by else NEON_PURPLE_COLOR
            )
            return await send_v2_followup(interaction, [res_container], ephemeral=True)

        not_found_container = make_v2_container(
            text_content=(
                f"### ❌ Key Not Found\n\n"
                f"No license record or database key was found matching: `{clean_key}`\n\n"
                "Please verify the key code or assign a new key using `/assign key`."
            ),
            footer_text="GX License Management",
            accent_color=RED_COLOR
        )
        return await send_v2_followup(interaction, [not_found_container], ephemeral=True)

    # ------------------------------------------------------------------------
    # INTERACTION LISTENER (BUTTONS & MODALS)
    # ------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # 1. BUTTON INTERACTIONS
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")

            # A. HOLD / FREEZE BUTTON CLICK
            if custom_id.startswith("license_hold_"):
                if not is_authorized_staff(interaction):
                    denied_container = make_v2_container(
                        text_content=f"⛔ **Access Denied!** You must have Staff Role <@&{config.STAFF_ROLE_ID}> to manage licenses.",
                        accent_color=RED_COLOR
                    )
                    return await send_v2_interaction_response(interaction, [denied_container], ephemeral=True)

                target_user_id = custom_id.replace("license_hold_", "")
                licenses = read_licenses()
                rec = licenses.get(target_user_id)
                if not rec:
                    err_container = make_v2_container(
                        text_content="⚠️ No license record found for this user in the database.",
                        accent_color=ORANGE_COLOR
                    )
                    return await send_v2_interaction_response(interaction, [err_container], ephemeral=True)

                # If currently on hold -> clicking unfreezes directly
                if rec.get("status") == "onhold":
                    rec["status"] = "active"
                    rec["holdReason"] = None
                    rec.pop("heldAt", None)
                    rec.pop("heldBy", None)
                    write_licenses(licenses)

                    # DM customer
                    try:
                        target_user = await self.bot.fetch_user(int(target_user_id))
                        if target_user:
                            dm_channel = target_user.dm_channel or await target_user.create_dm()
                            unhold_dm = make_v2_container(
                                text_content=(
                                    f"### GX MENU — License Reactivated!\n\n"
                                    "Your subscription has been successfully reactivated. "
                                    "You may now access the Client Portal and use your license key.\n\n"
                                    f"🔗 **[Click Here to Access Client Portal]({config.PORTAL_URL})**"
                                ),
                                footer_text="GX Client Access",
                                accent_color=GREEN_COLOR
                            )
                            await send_v2_channel_message(dm_channel, [unhold_dm])
                    except Exception:
                        pass

                    updated_container = build_v2_license_container(int(target_user_id), rec)
                    return await update_v2_interaction_response(interaction, [updated_container])

                # If active -> Open Modal to ask for reason
                modal_components = [
                    {
                        "type": 1,  # ActionRow
                        "components": [
                            {
                                "type": 4,  # TextInput
                                "custom_id": "hold_reason_input",
                                "style": 2,  # Paragraph
                                "label": "Reason for Hold / Freeze",
                                "placeholder": "e.g. Subscription Expired / Policy Violation",
                                "value": "Subscription Expired",
                                "required": True
                            }
                        ]
                    }
                ]
                return await send_v2_modal_response(
                    interaction,
                    title="HOLD / FREEZE LICENSE KEY",
                    custom_id=f"modal_hold_{target_user_id}",
                    components=modal_components
                )

            # B. DELETE KEY BUTTON CLICK (Confirmation Dialog)
            elif custom_id.startswith("license_delete_"):
                if not is_authorized_staff(interaction):
                    denied_container = make_v2_container(
                        text_content=f"⛔ **Access Denied!** Requires Staff Role <@&{config.STAFF_ROLE_ID}>.",
                        accent_color=RED_COLOR
                    )
                    return await send_v2_interaction_response(interaction, [denied_container], ephemeral=True)

                target_user_id = custom_id.replace("license_delete_", "")
                message_id = interaction.message.id if interaction.message else 0

                confirm_container = make_v2_container(
                    text_content=(
                        "### ⚠️ Permanent License Deletion Confirmation\n\n"
                        f"Are you sure you want to permanently delete the license key for <@{target_user_id}>?\n"
                        f"This will immediately revoke portal access and remove the Client role <@&{config.CLIENT_ROLE_ID}>."
                    ),
                    action_rows=[
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 4,  # Danger Red
                                    "label": "Confirm Delete",
                                    "custom_id": f"confirm_del_{target_user_id}_{message_id}",
                                    "emoji": {"name": "⚠️"}
                                },
                                {
                                    "type": 2,
                                    "style": 2,  # Secondary Gray
                                    "label": "Cancel",
                                    "custom_id": f"cancel_del_{target_user_id}",
                                    "emoji": {"name": "✖️"}
                                }
                            ]
                        }
                    ],
                    footer_text="GX License Deletion Safety Guard",
                    accent_color=RED_COLOR
                )
                return await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)

            # C. CONFIRMED DELETE
            elif custom_id.startswith("confirm_del_"):
                parts = custom_id.replace("confirm_del_", "").split("_")
                target_user_id = parts[0]
                message_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

                licenses = read_licenses()
                user_rec = licenses.get(target_user_id, {"status": "revoked"})
                user_rec["status"] = "revoked"

                licenses.pop(target_user_id, None)
                write_licenses(licenses)

                # Remove Client Role
                if interaction.guild:
                    try:
                        member = interaction.guild.get_member(int(target_user_id)) or await interaction.guild.fetch_member(int(target_user_id))
                        client_role = interaction.guild.get_role(config.CLIENT_ROLE_ID)
                        if member and client_role and client_role in member.roles:
                            await member.remove_roles(client_role, reason=f"License deleted by {interaction.user}")
                    except Exception:
                        pass

                # DM Customer
                try:
                    target_user = await self.bot.fetch_user(int(target_user_id))
                    if target_user:
                        dm_channel = target_user.dm_channel or await target_user.create_dm()
                        del_dm = make_v2_container(
                            text_content=(
                                f"### GX MENU — License Key Revoked\n\n"
                                "Your license key and Client role have been permanently deleted by administration."
                            ),
                            footer_text="GX Security",
                            accent_color=RED_COLOR
                        )
                        await send_v2_channel_message(dm_channel, [del_dm])
                except Exception:
                    pass

                # Update channel log message with disabled buttons
                if message_id and interaction.channel:
                    try:
                        disabled_container = build_v2_license_container(int(target_user_id), user_rec)
                        await edit_v2_channel_message(interaction.channel, message_id, [disabled_container])
                    except Exception as e:
                        logger.warning(f"Could not update channel message: {e}")

                done_container = make_v2_container(
                    text_content=f"✅ **License successfully deleted.**\nKey removed and Client role stripped from <@{target_user_id}>.",
                    footer_text="GX License Deletion",
                    accent_color=GREEN_COLOR
                )
                return await update_v2_interaction_response(interaction, [done_container])

            # D. CANCEL DELETE
            elif custom_id.startswith("cancel_del_"):
                cancel_container = make_v2_container(
                    text_content="✖️ **Deletion cancelled.** The license remains active and untouched.",
                    footer_text="GX License Deletion",
                    accent_color=NEON_PURPLE_COLOR
                )
                return await update_v2_interaction_response(interaction, [cancel_container])

        # 2. MODAL SUBMISSIONS
        elif interaction.type == discord.InteractionType.modal_submit:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("modal_hold_"):
                target_user_id = custom_id.replace("modal_hold_", "")
                components_list = interaction.data.get("components", [])
                reason = "Subscription Expired"

                for row in components_list:
                    for comp in row.get("components", [row]):
                        if comp.get("custom_id") == "hold_reason_input":
                            reason = comp.get("value", "Subscription Expired")

                licenses = read_licenses()
                rec = licenses.get(target_user_id)
                if not rec:
                    err_container = make_v2_container(
                        text_content="⚠️ No license record found for this user in the database.",
                        accent_color=ORANGE_COLOR
                    )
                    return await send_v2_interaction_response(interaction, [err_container], ephemeral=True)

                rec["status"] = "onhold"
                rec["holdReason"] = reason
                rec["heldAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                rec["heldBy"] = str(interaction.user)
                write_licenses(licenses)

                # DM Customer
                try:
                    target_user = await self.bot.fetch_user(int(target_user_id))
                    if target_user:
                        dm_channel = target_user.dm_channel or await target_user.create_dm()
                        hold_dm = make_v2_container(
                            text_content=(
                                f"### GX MENU — License Placed ON-HOLD\n\n"
                                f"Dear **{target_user.name}**, your license has been placed on hold (Frozen).\n\n"
                                f"> **Hold Reason:** `{reason}`\n\n"
                                "Please open a support ticket in our official Discord server if you have any questions."
                            ),
                            footer_text="GX Security & Enforcement",
                            accent_color=ORANGE_COLOR
                        )
                        await send_v2_channel_message(dm_channel, [hold_dm])
                except Exception:
                    pass

                # Update channel log message
                log_msg_id = rec.get("logMessageId")
                log_ch_id = rec.get("logChannelId")
                if log_msg_id and log_ch_id:
                    try:
                        ch = self.bot.get_channel(int(log_ch_id)) or await self.bot.fetch_channel(int(log_ch_id))
                        if ch:
                            updated_container = build_v2_license_container(int(target_user_id), rec)
                            await edit_v2_channel_message(ch, int(log_msg_id), [updated_container])
                    except Exception:
                        pass

                confirm_container = make_v2_container(
                    text_content=f"⏸️ Subscription for <@{target_user_id}> is now **ON-HOLD** with reason: `{reason}`",
                    footer_text="GX License Manager",
                    accent_color=ORANGE_COLOR
                )
                return await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LicensesCog(bot))
