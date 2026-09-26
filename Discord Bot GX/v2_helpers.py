# ============================================================================
# DISCORD COMPONENTS V2 HELPER UTILITIES
# Flags: 32768 (IS_COMPONENTS_V2)
# Container: Type 17 | TextDisplay: Type 10 | Separator: Type 14 | ActionRow: Type 1 | Button: Type 2
# ============================================================================
import discord
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("discord_bot.v2_helpers")

IS_COMPONENTS_V2 = 32768
DEFAULT_ACCENT_COLOR = 0x581C87   # 5774471 (Dark Purple)
NEON_PURPLE_COLOR = 0xC12AFF      # GX Neon Purple
GREEN_COLOR = 0x00FF88            # Success Green
ORANGE_COLOR = 0xFFB800           # Warning Gold / Orange
RED_COLOR = 0xFF2A55              # Danger Red
BLUE_COLOR = 0x3498DB             # Info Blue

def make_v2_container(
    text_content: str,
    action_rows: Optional[List[Dict[str, Any]]] = None,
    footer_text: Optional[str] = None,
    accent_color: int = DEFAULT_ACCENT_COLOR
) -> Dict[str, Any]:
    """Build a Components V2 Container dictionary (Type 17) with TextDisplay, Separators, and Action Rows."""
    components = [
        {
            "type": 10,  # TextDisplay
            "content": text_content
        }
    ]

    if action_rows:
        components.append({
            "type": 14,  # Separator
            "divider": True,
            "spacing": 1
        })
        components.extend(action_rows)

    if footer_text:
        components.append({
            "type": 14,  # Separator
            "divider": True,
            "spacing": 1
        })
        components.append({
            "type": 10,  # TextDisplay
            "content": f"-# {footer_text}"
        })

    return {
        "type": 17,  # Container
        "accent_color": accent_color,
        "components": components
    }

def _inject_v2_content(components: List[Dict[str, Any]], content: str):
    """Safely inject text content into Components V2 components.
    Discord API rejects root 'content' field with error 50035 when IS_COMPONENTS_V2 flag (32768) is used.
    Mentions and text are prepended to the first TextDisplay component inside the container.
    """
    if not content or not components:
        return
    for c in components:
        if isinstance(c, dict) and c.get("type") == 17 and "components" in c:
            for sub in c["components"]:
                if isinstance(sub, dict) and sub.get("type") == 10 and "content" in sub:
                    sub["content"] = f"{content}\n\n{sub['content']}"
                    return
            c["components"].insert(0, {"type": 10, "content": content})
            return
    components.insert(0, {"type": 10, "content": content})

async def send_v2_channel_message(
    channel: discord.abc.Messageable,
    components: List[Dict[str, Any]],
    content: Optional[str] = None,
    file: Optional[discord.File] = None,
    files: Optional[List[discord.File]] = None
):
    """Send a Components V2 message directly to any text-based channel, supporting attachments."""
    if content:
        _inject_v2_content(components, content)

    if file:
        files = [file]

    payload = {
        "flags": IS_COMPONENTS_V2,
        "embeds": [],
        "components": components
    }

    route = discord.http.Route('POST', f'/channels/{channel.id}/messages')

    if files:
        import json
        params = discord.http.handle_message_parameters(
            flags=discord.MessageFlags(components_v2=True),
            files=files
        )
        payload_dict = json.loads(params.multipart[0]['value'])
        payload_dict['components'] = components
        payload_dict['embeds'] = []
        payload_dict['flags'] = IS_COMPONENTS_V2
        params.multipart[0]['value'] = json.dumps(payload_dict)
        return await channel._state.http.request(route, files=params.files, form=params.multipart)
    else:
        return await channel._state.http.request(route, json=payload)

async def edit_v2_channel_message(channel: discord.abc.Messageable, message_id: int, components: List[Dict[str, Any]], content: Optional[str] = None):
    """Edit an existing channel message with a new Components V2 payload."""
    if content is not None:
        _inject_v2_content(components, content)

    payload = {
        "flags": IS_COMPONENTS_V2,
        "embeds": [],
        "components": components
    }

    route = discord.http.Route('PATCH', f'/channels/{channel.id}/messages/{message_id}')
    return await channel._state.http.request(route, json=payload)

async def send_v2_interaction_response(interaction: discord.Interaction, components: List[Dict[str, Any]], content: Optional[str] = None, ephemeral: bool = True):
    """Respond to an interaction using Components V2 payload."""
    flags = IS_COMPONENTS_V2
    if ephemeral:
        flags |= 64  # EPHEMERAL

    # If the interaction was already deferred or responded to, use followup
    if interaction.response.is_done():
        return await send_v2_followup(interaction, components, content=content, ephemeral=ephemeral)

    if content:
        _inject_v2_content(components, content)

    data = {
        "flags": flags,
        "embeds": [],
        "components": components
    }

    payload = {
        "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
        "data": data
    }

    route = discord.http.Route(
        'POST',
        '/interactions/{interaction_id}/{interaction_token}/callback',
        interaction_id=interaction.id,
        interaction_token=interaction.token
    )
    return await interaction.client.http.request(route, json=payload)

async def send_v2_followup(interaction: discord.Interaction, components: List[Dict[str, Any]], content: Optional[str] = None, ephemeral: bool = True):
    """Send a webhook followup response after deferring an interaction."""
    flags = IS_COMPONENTS_V2
    if ephemeral:
        flags |= 64  # EPHEMERAL

    if content:
        _inject_v2_content(components, content)

    payload = {
        "flags": flags,
        "embeds": [],
        "components": components
    }

    route = discord.http.Route(
        'POST',
        '/webhooks/{application_id}/{interaction_token}',
        application_id=interaction.application_id,
        interaction_token=interaction.token
    )
    return await interaction.client.http.request(route, json=payload)

async def update_v2_interaction_response(interaction: discord.Interaction, components: List[Dict[str, Any]], content: Optional[str] = None):
    """Update the message that triggered a component interaction (type 7 UPDATE_MESSAGE)."""
    data = {
        "flags": IS_COMPONENTS_V2,
        "embeds": [],
        "components": components
    }
    if content is not None:
        data["content"] = content

    payload = {
        "type": 7,  # UPDATE_MESSAGE
        "data": data
    }

    route = discord.http.Route(
        'POST',
        '/interactions/{interaction_id}/{interaction_token}/callback',
        interaction_id=interaction.id,
        interaction_token=interaction.token
    )
    return await interaction.client.http.request(route, json=payload)

async def send_v2_modal_response(interaction: discord.Interaction, title: str, custom_id: str, components: List[Dict[str, Any]]):
    """Send a Modal interaction response."""
    payload = {
        "type": 9,  # MODAL
        "data": {
            "title": title,
            "custom_id": custom_id,
            "components": components
        }
    }
    route = discord.http.Route(
        'POST',
        '/interactions/{interaction_id}/{interaction_token}/callback',
        interaction_id=interaction.id,
        interaction_token=interaction.token
    )
    res = await interaction.client.http.request(route, json=payload)
    try:
        interaction.response._response_type = discord.InteractionResponseType.modal
    except Exception:
        pass
    return res
