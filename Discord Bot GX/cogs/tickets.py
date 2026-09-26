import asyncio
import logging
import os
import json
import time
import datetime
import re
import discord
from discord import app_commands, ui
from discord.ext import commands

import config
import transcript_manager
from v2_helpers import (
    make_v2_container,
    send_v2_channel_message,
    send_v2_interaction_response,
    send_v2_followup,
    send_v2_modal_response,
    NEON_PURPLE_COLOR,
    GREEN_COLOR,
    RED_COLOR,
    ORANGE_COLOR
)

logger = logging.getLogger("discord_bot.tickets")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
DARK_PURPLE_COLOR = 5774471  # 0x581C87 Dark Purple Accent Color
PRE_IMAGE_PATH = r"E:\gx website\images\PRE.png"
PRE_IN_IMAGE_PATH = r"E:\gx website\images\PRE IN.png"

def is_authorized_staff(interaction: discord.Interaction) -> bool:
    """Check if the user is Server Owner or possesses the Staff Role."""
    if interaction.guild and interaction.guild.owner_id == interaction.user.id:
        return True
    if isinstance(interaction.user, discord.Member):
        for r in interaction.user.roles:
            if r.id == config.STAFF_ROLE_ID:
                return True
    return False

def read_vouches() -> list:
    """Load reviews/vouches from data/vouches.json."""
    try:
        if not os.path.exists(config.VOUCHES_FILE_PATH):
            return []
        with open(config.VOUCHES_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading vouches file: {e}")
        return []

def write_vouches(data: list) -> bool:
    """Save reviews/vouches to data/vouches.json."""
    try:
        os.makedirs(os.path.dirname(config.VOUCHES_FILE_PATH), exist_ok=True)
        with open(config.VOUCHES_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing vouches file: {e}")
        return False

def read_licenses() -> dict:
    """Load licenses from data/licenses.json."""
    try:
        if not os.path.exists(config.LICENSES_FILE_PATH):
            return {}
        with open(config.LICENSES_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading licenses file: {e}")
        return {}

def write_licenses(data: dict) -> bool:
    """Save licenses to data/licenses.json."""
    try:
        os.makedirs(os.path.dirname(config.LICENSES_FILE_PATH), exist_ok=True)
        with open(config.LICENSES_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing licenses file: {e}")
        return False

def make_dark_purple_container(
    text_content: str,
    action_rows: list = None,
    footer_text: str = None,
    accent_color: int = DARK_PURPLE_COLOR,
    image_url: str = None
) -> dict:
    """Build a Components V2 Container payload dictionary with dark purple accent color."""
    container_components = []

    container_components.append({
        "type": 10,  # Text Display (Text above the image)
        "content": text_content
    })

    if image_url:
        container_components.append({"type": 14})  # Separator Line inside container
        container_components.append({
            "type": 12,  # Media Gallery (Image below the text)
            "items": [
                {"media": {"url": image_url}}
            ]
        })

    if action_rows:
        container_components.append({"type": 14})  # Separator Line inside container
        container_components.extend(action_rows)
    if footer_text:
        container_components.append({"type": 14})  # Separator Line inside container
        container_components.append({
            "type": 10,  # Text Display
            "content": f"-# {footer_text}"
        })

    return {
        "type": 17,  # Container
        "accent_color": accent_color,
        "components": container_components
    }



class PurchaseModal(ui.Modal, title="🛒 GX App Purchase Form"):
    plan = ui.Label(
        text="Choose Your License Plan",
        component=ui.RadioGroup(
            custom_id="plan_choice_radio",
            options=[
                discord.RadioGroupOption(
                    label="⭐ Monthly License ($6.99 / 350 EGP)",
                    value="Monthly License ($6.99 / 350 EGP)",
                    description="30 Days unlimited access to GX App + updates",
                    default=True
                ),
                discord.RadioGroupOption(
                    label="👑 Lifetime License ($24.99 / 1250 EGP)",
                    value="Lifetime License ($24.99 / 1250 EGP)",
                    description="Permanent access + VIP Role + Priority Support"
                )
            ]
        )
    )
    payment = ui.Label(
        text="Preferred Payment Method",
        component=ui.RadioGroup(
            custom_id="payment_method_radio",
            options=[
                discord.RadioGroupOption(label="💳 PayPal", value="PayPal", default=True),
                discord.RadioGroupOption(label="🟡 Binance Pay / Crypto", value="Binance Pay / Crypto"),
                discord.RadioGroupOption(label="🔴 Vodafone Cash", value="Vodafone Cash"),
                discord.RadioGroupOption(label="🟢 Etisalat Cash", value="Etisalat Cash"),
                discord.RadioGroupOption(label="🟠 Orange Cash", value="Orange Cash"),
                discord.RadioGroupOption(label="⚡ InstaPay", value="InstaPay"),
                discord.RadioGroupOption(label="🟣 Telda", value="Telda"),
                discord.RadioGroupOption(label="🌍 TapTap Send", value="TapTap Send"),
            ]
        )
    )
    notes = ui.Label(
        text="Additional Order Notes",
        component=ui.TextInput(
            custom_id="additional_notes_input",
            style=discord.TextStyle.paragraph,
            placeholder="Any contact details or notes for staff (optional)...",
            required=False,
            max_length=500
        )
    )

    def __init__(self):
        super().__init__(title="🛒 GX App Purchase Form", custom_id="gx_purchase_v2_modal")


class PurchaseSelectFallbackModal(ui.Modal, title="🛒 GX App Purchase Form"):
    plan = ui.Label(
        text="Choose Your License Plan",
        component=ui.Select(
            custom_id="plan_choice_radio",
            options=[
                discord.SelectOption(label="⭐ Monthly License ($6.99 / 350 EGP)", value="Monthly License ($6.99 / 350 EGP)", default=True),
                discord.SelectOption(label="👑 Lifetime License ($24.99 / 1250 EGP)", value="Lifetime License ($24.99 / 1250 EGP)")
            ]
        )
    )
    payment = ui.Label(
        text="Preferred Payment Method",
        component=ui.Select(
            custom_id="payment_method_radio",
            options=[
                discord.SelectOption(label="💳 PayPal", value="PayPal", default=True),
                discord.SelectOption(label="🟡 Binance Pay / Crypto", value="Binance Pay / Crypto"),
                discord.SelectOption(label="🔴 Vodafone Cash", value="Vodafone Cash"),
                discord.SelectOption(label="🟢 Etisalat Cash", value="Etisalat Cash"),
                discord.SelectOption(label="🟠 Orange Cash", value="Orange Cash"),
                discord.SelectOption(label="⚡ InstaPay", value="InstaPay"),
                discord.SelectOption(label="🟣 Telda", value="Telda"),
                discord.SelectOption(label="🌍 TapTap Send", value="TapTap Send"),
            ]
        )
    )
    notes = ui.Label(
        text="Additional Order Notes",
        component=ui.TextInput(
            custom_id="additional_notes_input",
            style=discord.TextStyle.paragraph,
            placeholder="Any contact details or notes for staff (optional)...",
            required=False,
            max_length=500
        )
    )

    def __init__(self):
        super().__init__(title="🛒 GX App Purchase Form", custom_id="gx_purchase_v2_modal")


class SupportModal(ui.Modal, title="🔧 Technical Support Request"):
    category = ui.Label(
        text="Support Category",
        component=ui.RadioGroup(
            custom_id="support_category_radio",
            options=[
                discord.RadioGroupOption(
                    label="🛠️ Setup & Installation Help",
                    value="Setup Help",
                    description="Assistance with installing or setting up GX App",
                    default=True
                ),
                discord.RadioGroupOption(
                    label="🔄 HWID Reset Request",
                    value="HWID Reset",
                    description="Requesting a hardware ID reset for your license"
                ),
                discord.RadioGroupOption(
                    label="❓ General Inquiry",
                    value="General Inquiry",
                    description="General questions about features, pricing, or terms"
                ),
                discord.RadioGroupOption(
                    label="⚠️ Technical Issue / Bug Report",
                    value="Technical Issue",
                    description="Troubleshooting crashes, errors, or unexpected behavior"
                )
            ]
        )
    )
    issue = ui.Label(
        text="Describe Your Request or Issue",
        component=ui.TextInput(
            custom_id="support_issue_input",
            style=discord.TextStyle.paragraph,
            placeholder="Describe what you need assistance with or state your HWID reason...",
            min_length=5,
            max_length=1000,
            required=True
        )
    )

    def __init__(self):
        super().__init__(title="🔧 Technical Support Request", custom_id="gx_support_v2_modal")


class SupportSelectFallbackModal(ui.Modal, title="🔧 Technical Support Request"):
    category = ui.Label(
        text="Support Category",
        component=ui.Select(
            custom_id="support_category_radio",
            options=[
                discord.SelectOption(label="🛠️ Setup & Installation Help", value="Setup Help", default=True),
                discord.SelectOption(label="🔄 HWID Reset Request", value="HWID Reset"),
                discord.SelectOption(label="❓ General Inquiry", value="General Inquiry"),
                discord.SelectOption(label="⚠️ Technical Issue", value="Technical Issue")
            ]
        )
    )
    issue = ui.Label(
        text="Describe Your Request or Issue",
        component=ui.TextInput(
            custom_id="support_issue_input",
            style=discord.TextStyle.paragraph,
            placeholder="Describe what you need assistance with or state your HWID reason...",
            min_length=5,
            max_length=1000,
            required=True
        )
    )

    def __init__(self):
        super().__init__(title="🔧 Technical Support Request", custom_id="gx_support_v2_modal")


async def send_purchase_modal(interaction: discord.Interaction):
    """Display the official purchase inquiry form modal with radio options."""
    try:
        await interaction.response.send_modal(PurchaseModal())
    except Exception as e:
        logger.warning(f"RadioGroup modal send failed for PurchaseModal, attempting fallback: {e}")
        try:
            await interaction.response.send_modal(PurchaseSelectFallbackModal())
        except Exception as e2:
            logger.error(f"Fallback modal send failed for PurchaseModal: {e2}")


async def send_support_modal(interaction: discord.Interaction):
    """Display the official technical support request modal with radio options."""
    try:
        await interaction.response.send_modal(SupportModal())
    except Exception as e:
        logger.warning(f"RadioGroup modal send failed for SupportModal, attempting fallback: {e}")
        try:
            await interaction.response.send_modal(SupportSelectFallbackModal())
        except Exception as e2:
            logger.error(f"Fallback modal send failed for SupportModal: {e2}")


async def handle_purchase_modal_submit(interaction: discord.Interaction):
    """Process submitted Purchase Modal."""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except Exception as e:
        logger.warning(f"Could not defer purchase modal interaction: {e}")

    guild = interaction.guild
    user = interaction.user

    data_map = {}
    components_list = interaction.data.get("components", [])
    for item in components_list:
        if "components" in item:
            for sub in item["components"]:
                cid = sub.get("custom_id")
                val = sub.get("value")
                if val is None and sub.get("values"):
                    val = sub.get("values")[0]
                if cid:
                    data_map[cid] = val
        elif "component" in item:
            sub = item["component"]
            cid = sub.get("custom_id")
            val = sub.get("value")
            if val is None and sub.get("values"):
                val = sub.get("values")[0]
            if cid:
                data_map[cid] = val
        elif item.get("custom_id"):
            val = item.get("value")
            if val is None and item.get("values"):
                val = item.get("values")[0]
            data_map[item["custom_id"]] = val

    plan_choice = data_map.get("plan_choice_radio") or data_map.get("plan_choice_input") or data_map.get("plan_input") or "Monthly License ($6.99 / 350 EGP)"
    payment_method = data_map.get("payment_method_radio") or data_map.get("payment_method_input") or "PayPal"
    additional_notes = data_map.get("additional_notes_input") or "None provided"

    tickets_cat = (
        discord.utils.get(guild.categories, name="🎟️┃TICKETS")
        or discord.utils.get(guild.categories, name="🎟️ TICKETS")
        or discord.utils.get(guild.categories, name="🛒┃GX APP & KEYS")
        or discord.utils.get(guild.categories, name="🛒┃GX STORE")
        or discord.utils.get(guild.categories, name="🛒 GX STORE")
        or discord.utils.get(guild.categories, name="💬┃COMMUNITY")
        or discord.utils.get(guild.categories, name="💬 COMMUNITY")
    )
    if not tickets_cat:
        tickets_cat = await guild.create_category("🎟️┃TICKETS")

    clean_user_suffix = user.name.lower().replace(' ', '-')
    primary_ch_name = f"🛒┃purchase-{clean_user_suffix}"
    fallback_ch_name = f"purchase-{clean_user_suffix}"
    existing_ch = (
        discord.utils.get(tickets_cat.text_channels, name=primary_ch_name)
        or discord.utils.get(tickets_cat.text_channels, name=fallback_ch_name)
        or discord.utils.get(tickets_cat.text_channels, name=f"ticket-{clean_user_suffix}")
    )
    if existing_ch:
        error_container = make_dark_purple_container(
            text_content=f"⚠️ **Purchase Ticket Already Open**\nYou already have an active purchase ticket in {existing_ch.mention}!",
            footer_text="GX Purchase Ticket Manager"
        )
        await send_v2_interaction_response(interaction, [error_container], ephemeral=True)
        return

    owner_role = discord.utils.get(guild.roles, name="👑 Owner")
    mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    if owner_role:
        overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        ticket_ch = await tickets_cat.create_text_channel(
            name=primary_ch_name,
            overwrites=overwrites,
            topic=f"Purchase ticket for {user} ({user.id}) - Plan: {plan_choice}"
        )

        transcript_manager.save_ticket_meta(ticket_ch.id, {
            "ticket_id": f"purchase_{int(time.time())}_{user.id}",
            "channel_id": str(ticket_ch.id),
            "channel_name": ticket_ch.name,
            "ticket_type": "purchase",
            "creator_id": str(user.id),
            "creator_name": user.name,
            "creator_display_name": user.display_name,
            "creator_avatar": str(user.display_avatar.url),
            "plan": plan_choice,
            "payment_method": payment_method,
            "notes": additional_notes,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })


        staff_ping = f"{owner_role.mention if owner_role else ''} {mod_role.mention if mod_role else ''}".strip()
        ping_header = f"{user.mention} | Sales Staff Notification: {staff_ping}\n\n" if staff_ping else f"{user.mention}\n\n"

        image_file = None
        image_url = None
        if os.path.exists(PRE_IN_IMAGE_PATH):
            image_file = discord.File(PRE_IN_IMAGE_PATH, filename="PRE_IN.png")
            image_url = "attachment://PRE_IN.png"
        elif os.path.exists(PRE_IMAGE_PATH):
            image_file = discord.File(PRE_IMAGE_PATH, filename="PRE.png")
            image_url = "attachment://PRE.png"

        welcome_container = make_dark_purple_container(
            text_content=(
                f"{ping_header}"
                f"### 🛒 GX Key Purchase Ticket — {user.display_name}\n\n"
                f"Welcome {user.mention}!\n"
                "Our sales team has been notified of your purchase request. A staff member will issue your key shortly!\n\n"
                f"📋 **Selected License Plan**: `{plan_choice}`\n"
                f"💳 **Preferred Payment Method**: `{payment_method}`\n"
                f"📝 **Additional Order Notes**: `{additional_notes}`"
            ),
            action_rows=[
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 2,
                            "emoji": {"name": "🤝"},
                            "custom_id": f"gx_ticket_claim_{user.id}"
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "emoji": {"name": "🛠️"},
                            "custom_id": f"gx_ticket_mod_menu_{user.id}"
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "emoji": {"name": "🔒"},
                            "custom_id": f"gx_ticket_close_direct_{user.id}"
                        }
                    ]
                }
            ],
            footer_text="🤝 Staff Claim • 🛠️ Mod Menu • 🔒 Close Ticket",
            image_url=image_url
        )

        await send_v2_channel_message(ticket_ch, [welcome_container], file=image_file)

        confirm_container = make_dark_purple_container(
            text_content=(
                f"### ✅ Purchase Ticket Created!\n\n"
                f"Ticket created for **{plan_choice}**!\n\n"
                f"👉 Head over to {ticket_ch.mention}."
            ),
            footer_text="GX Purchase Ticket Manager"
        )
        await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)

    except discord.Forbidden:
        error_container = make_dark_purple_container(
            text_content="❌ **Permission Error**\nI lack permissions to create private ticket channels.",
            footer_text="GX Support System"
        )
        await send_v2_interaction_response(interaction, [error_container], ephemeral=True)

async def handle_support_modal_submit(interaction: discord.Interaction):
    """Process submitted Tech Support Modal with category and details."""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except Exception as e:
        logger.warning(f"Could not defer support modal interaction: {e}")

    guild = interaction.guild
    user = interaction.user

    data_map = {}
    components_list = interaction.data.get("components", [])
    for item in components_list:
        if "components" in item:
            for sub in item["components"]:
                cid = sub.get("custom_id")
                val = sub.get("value")
                if val is None and sub.get("values"):
                    val = sub.get("values")[0]
                if cid:
                    data_map[cid] = val
        elif "component" in item:
            sub = item["component"]
            cid = sub.get("custom_id")
            val = sub.get("value")
            if val is None and sub.get("values"):
                val = sub.get("values")[0]
            if cid:
                data_map[cid] = val
        elif item.get("custom_id"):
            val = item.get("value")
            if val is None and item.get("values"):
                val = item.get("values")[0]
            data_map[item["custom_id"]] = val

    category_choice = data_map.get("support_category_radio") or data_map.get("support_category_input") or "General Inquiry"
    issue_details = data_map.get("support_issue_input") or "None provided"

    tickets_cat = (
        discord.utils.get(guild.categories, name="🎟️┃TICKETS")
        or discord.utils.get(guild.categories, name="🎟️ TICKETS")
        or discord.utils.get(guild.categories, name="💬┃COMMUNITY")
        or discord.utils.get(guild.categories, name="💬 COMMUNITY")
    )
    if not tickets_cat:
        tickets_cat = await guild.create_category("🎟️┃TICKETS")

    clean_user_suffix = user.name.lower().replace(' ', '-')
    primary_ch_name = f"🛠️┃support-{clean_user_suffix}"
    fallback_ch_name = f"support-{clean_user_suffix}"
    existing_ch = (
        discord.utils.get(tickets_cat.text_channels, name=primary_ch_name)
        or discord.utils.get(tickets_cat.text_channels, name=fallback_ch_name)
        or discord.utils.get(tickets_cat.text_channels, name=f"ticket-{clean_user_suffix}")
    )
    if existing_ch:
        error_container = make_dark_purple_container(
            text_content=f"⚠️ **Support Ticket Already Open**\nYou already have an active support ticket in {existing_ch.mention}!",
            footer_text="GX Support Ticket Manager"
        )
        await send_v2_interaction_response(interaction, [error_container], ephemeral=True)
        return

    owner_role = discord.utils.get(guild.roles, name="👑 Owner")
    mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    if owner_role:
        overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        support_ch = await tickets_cat.create_text_channel(
            name=primary_ch_name,
            overwrites=overwrites,
            topic=f"Tech support ticket for {user} ({user.id}) - Category: {category_choice}"
        )

        transcript_manager.save_ticket_meta(support_ch.id, {
            "ticket_id": f"support_{int(time.time())}_{user.id}",
            "channel_id": str(support_ch.id),
            "channel_name": support_ch.name,
            "ticket_type": "support",
            "creator_id": str(user.id),
            "creator_name": user.name,
            "creator_display_name": user.display_name,
            "creator_avatar": str(user.display_avatar.url),
            "category": category_choice,
            "notes": issue_details,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })


        staff_ping = f"{owner_role.mention if owner_role else ''} {mod_role.mention if mod_role else ''}".strip()
        ping_header = f"{user.mention} | Tech Support Notification: {staff_ping}\n\n" if staff_ping else f"{user.mention}\n\n"

        welcome_container = make_dark_purple_container(
            text_content=(
                f"{ping_header}"
                f"### 🔧 GX Technical Support — {user.display_name}\n\n"
                f"Welcome {user.mention}!\n"
                "Our technical support staff has been notified. A team member will assist you shortly!\n\n"
                f"📌 **Support Category**: `{category_choice}`\n"
                f"📝 **Issue Details**: `{issue_details}`"
            ),
            action_rows=[
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "gx_close_ticket_btn",
                            "label": "🔒 Close Ticket",
                            "style": 4
                        }
                    ]
                }
            ],
            footer_text="Click 🔒 Close Ticket below when your issue is resolved."
        )

        await send_v2_channel_message(support_ch, [welcome_container])

        confirm_container = make_dark_purple_container(
            text_content=(
                f"### ✅ Support Ticket Created!\n\n"
                f"Support ticket created for **{category_choice}**!\n\n"
                f"👉 Head over to {support_ch.mention}."
            ),
            footer_text="GX Support Ticket Manager"
        )
        await send_v2_interaction_response(interaction, [confirm_container], ephemeral=True)

    except discord.Forbidden:
        error_container = make_dark_purple_container(
            text_content="❌ **Permission Error**\nI lack permissions to create private ticket channels.",
            footer_text="GX Support System"
        )
        await send_v2_interaction_response(interaction, [error_container], ephemeral=True)

class TicketRatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def log_rating(self, interaction: discord.Interaction, rating: int):
        guild = interaction.guild
        stars = "⭐" * rating

        mod_logs = (
            discord.utils.get(guild.text_channels, name="📑┃mod-logs")
            or discord.utils.get(guild.text_channels, name="📑-mod-logs")
            or discord.utils.get(guild.text_channels, name="mod-logs")
        )
        if mod_logs:
            log_container = make_dark_purple_container(
                text_content=(
                    "### 📊 Support Ticket Staff Rating\n\n"
                    f"• **Customer**: {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"• **Rating**: {stars} (`{rating}/5`)\n"
                    f"• **Ticket Channel**: `{interaction.channel.name}`"
                ),
                footer_text="📑 GX Automated Mod Logs"
            )
            try:
                await send_v2_channel_message(mod_logs, [log_container])
            except Exception as e:
                logger.error(f"Failed to send rating log: {e}")

        response_container = make_dark_purple_container(
            text_content=f"### 🙏 Thank You!\nThank you for rating your support experience {stars}! Closing channels now...",
            footer_text="GX Ticket System"
        )
        try:
            await send_v2_interaction_response(interaction, [response_container], ephemeral=False)
        except Exception:
            try:
                await interaction.response.send_message(f"Thank you for rating {stars}! Closing channels now...", ephemeral=False)
            except Exception:
                pass

        await asyncio.sleep(2)

        clean_ch_name = interaction.channel.name.replace("🛒┃", "").replace("🛠️┃", "").replace("🛒-", "").replace("🛠️-", "")
        ticket_vc = (
            discord.utils.get(guild.voice_channels, name=f"🔊┃{clean_ch_name}")
            or discord.utils.get(guild.voice_channels, name=f"🔊┃{interaction.channel.name}")
            or discord.utils.get(guild.voice_channels, name=f"🔊-{interaction.channel.name}")
            or discord.utils.get(guild.voice_channels, name=f"🔊-{clean_ch_name}")
            or discord.utils.get(guild.voice_channels, name=interaction.channel.name)
        )
        if ticket_vc:
            try:
                await ticket_vc.delete(reason=f"Ticket closed with rating {rating}/5")
            except Exception as e:
                logger.error(f"Failed to delete ticket voice channel: {e}")

        try:
            await interaction.channel.delete(reason=f"Ticket closed with rating {rating}/5")
        except Exception as e:
            logger.error(f"Failed to delete channel after rating: {e}")

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="⭐ 2", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="⭐ 3", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="⭐ 4", style=discord.ButtonStyle.primary, custom_id="rate_4")
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="gx_close_ticket_btn"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

class TicketPanelView(discord.ui.View):
    """Purchase Panel View with Open Purchase Ticket Button."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛒 Purchase Key",
        style=discord.ButtonStyle.primary,
        custom_id="gx_open_purchase_btn"
    )
    async def open_purchase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

class SupportPanelView(discord.ui.View):
    """Technical Support Panel View with Open Support Ticket Button."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔧 Request Support",
        style=discord.ButtonStyle.primary,
        custom_id="gx_open_support_btn"
    )
    async def open_support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

async def deploy_v2_purchase_panel(bot: commands.Bot, channel: discord.TextChannel):
    """Deploy or update the Purchase Panel card in #🛒-purchase using Components V2 container."""
    async for msg in channel.history(limit=10):
        if msg.author == bot.user:
            try:
                await msg.delete()
            except Exception as e:
                logger.warning(f"Could not delete previous purchase panel message: {e}")

    image_file = None
    image_url = None
    if os.path.exists(PRE_IMAGE_PATH):
        image_file = discord.File(PRE_IMAGE_PATH, filename="PRE.png")
        image_url = "attachment://PRE.png"

    container = make_dark_purple_container(
        text_content=(
            "### 🛒 GX App License Purchase Portal\n\n"
            "Click **`🛒 Purchase Key`** below to select your license plan and preferred payment method!\n\n"
            "> 🔒 *A private ticket channel will be created for your order.*"
        ),
        action_rows=[
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "custom_id": "gx_open_purchase_btn",
                        "label": "🛒 Purchase Key",
                        "style": 1
                    }
                ]
            }
        ],
        footer_text="🛡️ GX Support Team • Private Purchase Channels",
        image_url=image_url
    )
    await send_v2_channel_message(channel, [container], file=image_file)

async def deploy_v2_support_panel(bot: commands.Bot, channel: discord.TextChannel):
    """Deploy or update the Technical Support Panel card in #🛠️-support-tickets using Components V2 container."""
    async for msg in channel.history(limit=10):
        if msg.author == bot.user:
            try:
                await msg.delete()
            except Exception as e:
                logger.warning(f"Could not delete previous support panel message: {e}")

    container = make_dark_purple_container(
        text_content=(
            "### 🔧 GX Technical Support & HWID Portal\n\n"
            "Need technical assistance, setup guidance, or an HWID reset?\n"
            "Click **`🔧 Request Support`** below to submit your request form!\n\n"
            "> 🛡️ *A private ticket channel will be created for your inquiry.*"
        ),
        action_rows=[
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "custom_id": "gx_open_support_btn",
                        "label": "🔧 Request Support",
                        "style": 1
                    }
                ]
            }
        ],
        footer_text="🛡️ GX Support Team • Private Support Channels"
    )
    await send_v2_channel_message(channel, [container])

# Backward compatibility alias
async def deploy_v2_ticket_panel(bot: commands.Bot, channel: discord.TextChannel):
    await deploy_v2_purchase_panel(bot, channel)

async def close_ticket_channels(
    channel: discord.TextChannel,
    guild: discord.Guild,
    reason: str = "Ticket closed",
    closer: discord.Member | discord.User = None,
    bot: commands.Bot = None
):
    """Extract full chat transcript, save JSON/HTML, dispatch audit embed to channel 1548141255710736386, and delete channels."""
    try:
        await transcript_manager.log_and_export_ticket(
            channel=channel,
            guild=guild,
            closer=closer or guild.me,
            reason=reason,
            bot=bot
        )
    except Exception as e:
        logger.error(f"Failed to export/log transcript for {channel.name}: {e}", exc_info=True)

    clean_ch_name = (
        channel.name
        .replace("🛒┃", "")
        .replace("🛠️┃", "")
        .replace("🛒-", "")
        .replace("🛠️-", "")
    )
    ticket_vc = (
        discord.utils.get(guild.voice_channels, name=f"🔊┃{clean_ch_name}")
        or discord.utils.get(guild.voice_channels, name=f"🔊┃{channel.name}")
        or discord.utils.get(guild.voice_channels, name=f"🔊-{channel.name}")
        or discord.utils.get(guild.voice_channels, name=f"🔊-{clean_ch_name}")
        or discord.utils.get(guild.voice_channels, name=channel.name)
    )
    if ticket_vc:
        try:
            await ticket_vc.delete(reason=reason)
        except Exception as e:
            logger.warning(f"Could not delete ticket voice channel: {e}")
    try:
        await channel.delete(reason=reason)
    except Exception as e:
        logger.warning(f"Could not delete ticket text channel: {e}")


class RatingServiceModal(ui.Modal, title="⭐ Rate Service"):
    rating = ui.Label(
        text="Rating",
        component=ui.RadioGroup(
            custom_id="rating_score_radio",
            options=[
                discord.RadioGroupOption(label="⭐", value="1"),
                discord.RadioGroupOption(label="⭐⭐", value="2"),
                discord.RadioGroupOption(label="⭐⭐⭐", value="3"),
                discord.RadioGroupOption(label="⭐⭐⭐⭐", value="4"),
                discord.RadioGroupOption(label="⭐⭐⭐⭐⭐", value="5", default=True),
            ]
        )
    )
    feedback = ui.Label(
        text="Review & Feedback",
        component=ui.TextInput(
            custom_id="rating_review_input",
            style=discord.TextStyle.paragraph,
            placeholder="Share your experience with GX App, performance, and delivery speed...",
            min_length=2,
            max_length=1000,
            required=True
        )
    )

    def __init__(self, target_user_id: str):
        super().__init__(title="⭐ Rate Service", custom_id=f"gx_rating_submit_modal_{target_user_id}")

class RatingSelectFallbackModal(ui.Modal, title="⭐ Rate Service"):
    rating = ui.Label(
        text="Rating",
        component=ui.Select(
            custom_id="rating_score_radio",
            placeholder="Select a rating (1 to 5 Stars)...",
            options=[
                discord.SelectOption(label="⭐", value="1"),
                discord.SelectOption(label="⭐⭐", value="2"),
                discord.SelectOption(label="⭐⭐⭐", value="3"),
                discord.SelectOption(label="⭐⭐⭐⭐", value="4"),
                discord.SelectOption(label="⭐⭐⭐⭐⭐", value="5", default=True),
            ]
        )
    )
    feedback = ui.Label(
        text="Review & Feedback",
        component=ui.TextInput(
            custom_id="rating_review_input",
            style=discord.TextStyle.paragraph,
            placeholder="Share your experience with GX App, performance, and delivery speed...",
            min_length=2,
            max_length=1000,
            required=True
        )
    )

    def __init__(self, target_user_id: str):
        super().__init__(title="⭐ Rate Service", custom_id=f"gx_rating_submit_modal_{target_user_id}")

async def handle_rating_modal_submit(interaction: discord.Interaction, custom_id: str):
    """Process customer service rating and review modal submission."""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except Exception as e:
        logger.warning(f"Could not defer rating modal interaction: {e}")

    target_user_id = custom_id.replace("gx_rating_submit_modal_", "")
    user = interaction.user
    guild = interaction.guild

    data_map = {}
    components_list = interaction.data.get("components", [])
    for item in components_list:
        if "components" in item:
            for sub in item["components"]:
                cid = sub.get("custom_id")
                val = sub.get("value")
                if val is None and sub.get("values"):
                    val = sub.get("values")[0]
                if cid:
                    data_map[cid] = val
        elif "component" in item:
            sub = item["component"]
            cid = sub.get("custom_id")
            val = sub.get("value")
            if val is None and sub.get("values"):
                val = sub.get("values")[0]
            if cid:
                data_map[cid] = val
        elif item.get("custom_id"):
            val = item.get("value")
            if val is None and item.get("values"):
                val = item.get("values")[0]
            data_map[item["custom_id"]] = val

    rating_raw = str(data_map.get("rating_score_radio") or data_map.get("rating_score_input") or "5").strip()
    comment = str(data_map.get("rating_review_input", "")).strip() or "Excellent service and instantaneous activation!"

    digits = re.findall(r'[1-5]', rating_raw)
    if digits:
        rating_val = int(digits[0])
    else:
        star_count = rating_raw.count("⭐") + rating_raw.count("★")
        rating_val = min(5, max(1, star_count)) if star_count > 0 else 5
    stars_display = "⭐" * rating_val

    plan_choice = "GX App License"
    if interaction.channel and getattr(interaction.channel, "topic", None):
        topic = interaction.channel.topic
        if "Plan: " in topic:
            plan_choice = topic.split("Plan: ")[-1].strip()

    # 1. Save to data/vouches.json
    vouches = read_vouches()
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    avatar_url = user.display_avatar.url if hasattr(user, "display_avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    nickname = getattr(user, "nick", None) or user.display_name or user.name

    new_vouch = {
        "id": f"vouch_{int(time.time())}_{user.id}",
        "userId": str(user.id),
        "username": user.name,
        "nickname": nickname,
        "avatar": avatar_url,
        "rating": rating_val,
        "comment": comment,
        "plan": plan_choice,
        "timestamp": now_utc
    }
    vouches.append(new_vouch)
    write_vouches(vouches)
    logger.info(f"Saved new vouch from {user} ({rating_val} stars): {comment}")

    if interaction.channel:
        transcript_manager.update_ticket_meta(
            interaction.channel.id,
            rating=rating_val,
            comment=comment,
            rating_at=now_utc
        )


    # 2. Post to Vouches Channel (1547753169864495154)
    vouches_ch = guild.get_channel(config.VOUCHES_CHANNEL_ID)
    if not vouches_ch:
        vouches_ch = (
            discord.utils.get(guild.text_channels, name="⭐┃vouches")
            or discord.utils.get(guild.text_channels, name="⭐-vouches")
            or discord.utils.get(guild.text_channels, name="vouches")
        )
    if vouches_ch:
        vouch_card = make_dark_purple_container(
            text_content=(
                "### ⭐ New Customer Vouch Received!\n\n"
                f"• **Customer**: {user.mention} (`{user.name}`)\n"
                f"• **Purchased Plan**: `{plan_choice}`\n"
                f"• **Rating**: {stars_display} (`{rating_val}/5`)\n\n"
                f"💬 **Feedback**:\n"
                f"> \"{comment}\"\n\n"
                f"📅 <t:{int(time.time())}:R>"
            ),
            footer_text="🛡️ Verified Discord Purchase • Synced to Website Vouches"
        )
        try:
            await send_v2_channel_message(vouches_ch, [vouch_card])
        except Exception as e:
            logger.error(f"Failed to post to vouches channel: {e}")

    # 3. Post summary card in Ticket Channel with Close Ticket button
    summary_card = make_dark_purple_container(
        text_content=(
            "### ⭐ Service Review Submitted!\n\n"
            f"Thank you {user.mention} for your review!\n\n"
            f"• **Rating**: {stars_display} (`{rating_val}/5`)\n"
            f"• **Feedback**: \"{comment}\"\n\n"
            "Your feedback is now visible in our vouches channel and on our official website!\n"
            "You can close this ticket whenever you are ready:"
        ),
        action_rows=[
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 2,
                        "label": "🔒 Close Ticket",
                        "custom_id": f"gx_ticket_close_direct_{user.id}"
                    }
                ]
            }
        ],
        footer_text="GX Order Management • Quality Control"
    )
    try:
        await send_v2_channel_message(interaction.channel, [summary_card])
    except Exception as e:
        logger.error(f"Failed to post review summary to ticket channel: {e}")

    # 4. Ephemeral confirmation to user
    confirm_card = make_dark_purple_container(
        text_content=f"### ✅ Review Submitted!\nThank you for rating our service {stars_display}! Your review has been saved and posted to vouches.",
        footer_text="GX Customer Reviews"
    )
    await send_v2_followup(interaction, [confirm_card], ephemeral=True)

class TicketsCog(commands.Cog, name="Tickets"):
    """Interactive Support & Purchase Ticket system with text & voice channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Global listener for Buttons and Modals in Ticket System."""
        # 1. BUTTON INTERACTIONS
        if interaction.type == discord.InteractionType.component:
            if interaction.response.is_done():
                return
            custom_id = interaction.data.get("custom_id", "")
            if custom_id in ["gx_open_purchase_btn", "gx_open_ticket_btn"]:
                if not interaction.response.is_done():
                    try:
                        await send_purchase_modal(interaction)
                    except Exception as e:
                        logger.error(f"Error launching purchase modal: {e}")
                return
            elif custom_id == "gx_open_support_btn":
                if not interaction.response.is_done():
                    try:
                        await send_support_modal(interaction)
                    except Exception as e:
                        logger.error(f"Error launching support modal: {e}")
                return

            # --- TICKET CLAIM (🤝) ---
            elif custom_id.startswith("gx_ticket_claim_"):
                if not is_authorized_staff(interaction):
                    err_c = make_dark_purple_container(
                        text_content="❌ **Permission Denied**\nOnly authorized GX staff can claim tickets.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                target_user_id = custom_id.replace("gx_ticket_claim_", "")
                claim_announcement = make_dark_purple_container(
                    text_content=(
                        f"### 🤝 Ticket Claimed by {interaction.user.display_name}\n\n"
                        f"This ticket has been officially claimed by {interaction.user.mention}!\n"
                        f"They are now handling this order and will provide your key shortly."
                    ),
                    footer_text="GX Order Management • Staff Claim"
                )
                await send_v2_channel_message(interaction.channel, [claim_announcement])

                transcript_manager.update_ticket_meta(
                    interaction.channel.id,
                    claimed_by_id=str(interaction.user.id),
                    claimed_by_name=interaction.user.display_name,
                    claimed_by_avatar=interaction.user.display_avatar.url if hasattr(interaction.user, "display_avatar") else None,
                    claimed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                )

                confirm_c = make_dark_purple_container(
                    text_content=f"✅ You have claimed ticket `{interaction.channel.name}`.",
                    footer_text="GX Ticket System"
                )
                await send_v2_interaction_response(interaction, [confirm_c], ephemeral=True)


            # --- MOD MENU (🛠️) ---
            elif custom_id.startswith("gx_ticket_mod_menu_"):
                if not is_authorized_staff(interaction):
                    err_c = make_dark_purple_container(
                        text_content="❌ **Permission Denied**\nOnly authorized GX staff can open the moderation menu.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                target_user_id = custom_id.replace("gx_ticket_mod_menu_", "")
                menu_container = make_dark_purple_container(
                    text_content=(
                        "### 🛠️ Ticket Moderation Controls\n\n"
                        f"• **Customer**: <@{target_user_id}> (`{target_user_id}`)\n"
                        f"• **Ticket Channel**: `{interaction.channel.name}`\n\n"
                        "Select an action below to manage this order:"
                    ),
                    action_rows=[
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,  # Green / Success
                                    "label": "✅ Order Done",
                                    "custom_id": f"gx_mod_done_{target_user_id}"
                                },
                                {
                                    "type": 2,
                                    "style": 4,  # Red / Danger
                                    "label": "🚫 Blacklist Customer",
                                    "custom_id": f"gx_mod_blacklist_{target_user_id}"
                                },
                                {
                                    "type": 2,
                                    "style": 2,  # Gray / Secondary
                                    "label": "🔒 Close Ticket",
                                    "custom_id": f"gx_mod_close_{target_user_id}"
                                }
                            ]
                        }
                    ],
                    footer_text="GX Staff Moderation Controls"
                )
                await send_v2_interaction_response(interaction, [menu_container], ephemeral=True)

            # --- ORDER DONE (✅) ---
            elif custom_id.startswith("gx_mod_done_"):
                if not is_authorized_staff(interaction):
                    err_c = make_dark_purple_container(
                        text_content="❌ **Permission Denied**\nOnly authorized GX staff can mark orders done.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                target_user_id = custom_id.replace("gx_mod_done_", "")
                done_announcement = make_dark_purple_container(
                    text_content=(
                        "### 🎉 Order Completed!\n\n"
                        f"Hey <@{target_user_id}>, your purchase has been completed by {interaction.user.mention}!\n\n"
                        "We hope you enjoy using **GX App**!\n"
                        "Please click the **⭐ Rate Service** button below to leave your rating and feedback.\n"
                        "Your review will be showcased on our vouches channel and official website!"
                    ),
                    action_rows=[
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 1,  # Primary / Blurple
                                    "label": "⭐ Rate Service",
                                    "custom_id": f"gx_rate_order_btn_{target_user_id}"
                                }
                            ]
                        }
                    ],
                    footer_text="GX Quality Control • Customer Feedback"
                )
                await send_v2_channel_message(
                    interaction.channel,
                    [done_announcement],
                    content=f"<@{target_user_id}>"
                )

                staff_ack = make_dark_purple_container(
                    text_content=f"✅ Order marked as completed for <@{target_user_id}>. Review prompt dispatched!",
                    footer_text="GX Ticket System"
                )
                await send_v2_interaction_response(interaction, [staff_ack], ephemeral=True)

            # --- RATE SERVICE BUTTON (⭐) ---
            elif custom_id.startswith("gx_rate_order_btn_"):
                target_user_id = custom_id.replace("gx_rate_order_btn_", "")
                if str(interaction.user.id) != str(target_user_id) and not is_authorized_staff(interaction):
                    err_c = make_dark_purple_container(
                        text_content=f"❌ Only the customer of this ticket (<@{target_user_id}>) can submit a review.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                try:
                    await interaction.response.send_modal(RatingServiceModal(target_user_id))
                except Exception as e:
                    logger.warning(f"RadioGroup modal send failed, attempting fallback: {e}")
                    try:
                        await interaction.response.send_modal(RatingSelectFallbackModal(target_user_id))
                    except Exception as e2:
                        logger.error(f"Fallback modal send failed: {e2}")

            # --- BLACKLIST CUSTOMER (🚫) ---
            elif custom_id.startswith("gx_mod_blacklist_"):
                if not is_authorized_staff(interaction):
                    err_c = make_dark_purple_container(
                        text_content="❌ **Permission Denied**\nOnly authorized GX staff can blacklist customers.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                target_user_id = custom_id.replace("gx_mod_blacklist_", "")
                
                # Revoke licenses in data/licenses.json
                licenses = read_licenses()
                revoked_keys = []
                for code, ldata in licenses.items():
                    if str(ldata.get("owner_discord_id")) == str(target_user_id) or str(ldata.get("discord_user_id")) == str(target_user_id):
                        ldata["active"] = False
                        ldata["revoked"] = True
                        ldata["status"] = "revoked"
                        revoked_keys.append(code)
                if revoked_keys:
                    write_licenses(licenses)

                # Remove client role if member is found in guild
                target_member = interaction.guild.get_member(int(target_user_id))
                if target_member:
                    client_role = interaction.guild.get_role(config.CLIENT_ROLE_ID)
                    if client_role and client_role in target_member.roles:
                        try:
                            await target_member.remove_roles(client_role, reason="Customer Blacklisted by Staff")
                        except Exception as e:
                            logger.warning(f"Could not remove client role from blacklisted user: {e}")

                staff_ack = make_dark_purple_container(
                    text_content=f"🚫 Customer <@{target_user_id}> has been blacklisted and {len(revoked_keys)} key(s) revoked.",
                    footer_text="GX Blacklist Manager"
                )
                await send_v2_interaction_response(interaction, [staff_ack], ephemeral=True)

                bl_msg = make_dark_purple_container(
                    text_content="### 🚫 Ticket Closed — Customer Blacklisted\nThis user has been blacklisted. Deleting ticket channels in 5 seconds...",
                    footer_text="GX Security"
                )
                await send_v2_channel_message(interaction.channel, [bl_msg])
                await asyncio.sleep(5)
                await close_ticket_channels(interaction.channel, interaction.guild, f"Blacklisted customer {target_user_id}", closer=interaction.user, bot=self.bot)

            # --- CLOSE TICKET DIRECT (🔒) / MOD CLOSE ---
            elif custom_id.startswith("gx_mod_close_") or custom_id.startswith("gx_ticket_close_direct_"):
                target_user_id = custom_id.replace("gx_mod_close_", "").replace("gx_ticket_close_direct_", "")
                if not is_authorized_staff(interaction) and str(interaction.user.id) != str(target_user_id):
                    err_c = make_dark_purple_container(
                        text_content="❌ You do not have permission to close this ticket.",
                        footer_text="GX Ticket System"
                    )
                    await send_v2_interaction_response(interaction, [err_c], ephemeral=True)
                    return

                close_card = make_dark_purple_container(
                    text_content="### 🔒 Ticket Closing\nThis ticket is now being closed. Channels will be deleted in 3 seconds...",
                    footer_text="GX Ticket Manager"
                )
                await send_v2_interaction_response(interaction, [close_card], ephemeral=False)
                await asyncio.sleep(3)
                await close_ticket_channels(interaction.channel, interaction.guild, f"Closed by {interaction.user}", closer=interaction.user, bot=self.bot)


            # Legacy close & rating buttons support
            elif custom_id == "gx_close_ticket_btn":
                rating_container = make_dark_purple_container(
                    text_content=(
                        "### ⭐ Rate Your Support Experience\n\n"
                        "Before this ticket closes, please rate the support you received from our team below:"
                    ),
                    action_rows=[
                        {
                            "type": 1,
                            "components": [
                                {"type": 2, "custom_id": "rate_1", "label": "⭐ 1", "style": 2},
                                {"type": 2, "custom_id": "rate_2", "label": "⭐ 2", "style": 2},
                                {"type": 2, "custom_id": "rate_3", "label": "⭐ 3", "style": 2},
                                {"type": 2, "custom_id": "rate_4", "label": "⭐ 4", "style": 1},
                                {"type": 2, "custom_id": "rate_5", "label": "⭐ 5", "style": 3},
                            ]
                        }
                    ],
                    footer_text="GX Support Team • Quality Control"
                )
                await send_v2_interaction_response(interaction, [rating_container], ephemeral=False)
            elif custom_id.startswith("rate_"):
                try:
                    rating_val = int(custom_id.replace("rate_", ""))
                    view = TicketRatingView()
                    await view.log_rating(interaction, rating_val)
                except Exception as e:
                    logger.error(f"Error rating ticket: {e}")

        # 2. MODAL SUBMISSIONS
        elif interaction.type == discord.InteractionType.modal_submit:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id in ["gx_purchase_v2_modal", "gx_ticket_v2_modal"]:
                await handle_purchase_modal_submit(interaction)
            elif custom_id == "gx_support_v2_modal":
                await handle_support_modal_submit(interaction)
            elif custom_id.startswith("gx_rating_submit_modal_"):
                await handle_rating_modal_submit(interaction, custom_id)

    @app_commands.command(name="setup-ticket-panel", description="Deploy the futuristic Components V2 purchase and support panels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_ticket_panel(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True)

        cat_keys = (
            discord.utils.get(guild.categories, name="🛒┃GX APP & KEYS")
            or discord.utils.get(guild.categories, name="🛒┃GX STORE")
            or discord.utils.get(guild.categories, name="🛒 GX STORE")
            or discord.utils.get(guild.categories, name="🛒 GX APP & KEYS")
        )
        cat_comm = (
            discord.utils.get(guild.categories, name="💬┃COMMUNITY")
            or discord.utils.get(guild.categories, name="💬 COMMUNITY")
        )

        purchase_ch = (
            discord.utils.get(guild.text_channels, name="🛒┃purchase")
            or discord.utils.get(guild.text_channels, name="🛒-purchase")
            or discord.utils.get(guild.text_channels, name="purchase")
            or discord.utils.get(guild.text_channels, name="💳-purchase")
            or discord.utils.get(guild.text_channels, name="📩-purchase")
        )
        if not purchase_ch:
            purchase_ch = await guild.create_text_channel(name="🛒┃purchase", category=cat_keys)

        support_ch = (
            discord.utils.get(guild.text_channels, name="🛠️┃support-tickets")
            or discord.utils.get(guild.text_channels, name="🛠️-support-tickets")
            or discord.utils.get(guild.text_channels, name="support-tickets")
        )
        if not support_ch:
            support_ch = await guild.create_text_channel(name="🛠️┃support-tickets", category=cat_comm)

        await deploy_v2_purchase_panel(self.bot, purchase_ch)
        await deploy_v2_support_panel(self.bot, support_ch)

        confirm_container = make_dark_purple_container(
            text_content=f"### ✅ Panels Deployed!\nPurchase Panel in {purchase_ch.mention} and Support Panel in {support_ch.mention}!",
            footer_text="GX Ticket Setup"
        )
        await send_v2_followup(interaction, [confirm_container], ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            err_container = make_dark_purple_container(
                text_content="❌ Administrator permissions required.",
                footer_text="GX Ticket System"
            )
            await send_v2_interaction_response(interaction, [err_container], ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
