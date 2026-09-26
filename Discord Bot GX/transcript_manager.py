import asyncio
import os
import json
import time
import datetime
import html
import logging
import base64
import re
import discord
from discord.ext import commands

import config

logger = logging.getLogger("discord_bot.transcript_manager")

ACTIVE_TICKETS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(config.LICENSES_FILE_PATH), "active_tickets.json")
)

def _read_active_tickets() -> dict:
    try:
        if not os.path.exists(ACTIVE_TICKETS_FILE):
            return {}
        with open(ACTIVE_TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading active tickets file: {e}")
        return {}

def _write_active_tickets(data: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(ACTIVE_TICKETS_FILE), exist_ok=True)
        with open(ACTIVE_TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing active tickets file: {e}")
        return False

def save_ticket_meta(channel_id: str | int, meta: dict):
    """Save or update ticket metadata for an active ticket channel."""
    tickets = _read_active_tickets()
    cid = str(channel_id)
    if cid not in tickets:
        tickets[cid] = {}
    tickets[cid].update(meta)
    _write_active_tickets(tickets)

def get_ticket_meta(channel_id: str | int) -> dict:
    """Retrieve metadata for an active ticket channel."""
    tickets = _read_active_tickets()
    return tickets.get(str(channel_id), {})

def update_ticket_meta(channel_id: str | int, **kwargs):
    """Update fields on active ticket channel."""
    tickets = _read_active_tickets()
    cid = str(channel_id)
    if cid not in tickets:
        tickets[cid] = {}
    tickets[cid].update(kwargs)
    _write_active_tickets(tickets)

def remove_ticket_meta(channel_id: str | int):
    """Remove active ticket channel metadata when closed."""
    tickets = _read_active_tickets()
    cid = str(channel_id)
    if cid in tickets:
        del tickets[cid]
        _write_active_tickets(tickets)

def format_role_color(color: discord.Color) -> str:
    """Convert discord Color to hex string, default to purple if black/default."""
    if not color or color.value == 0:
        return "#c12aff"
    return f"#{color.value:06x}"

def serialize_member_profile(member: discord.Member | discord.User, guild: discord.Guild = None) -> dict:
    """Extract complete profile including server roles, dates, and avatar."""
    display_name = getattr(member, "nick", None) or member.display_name or member.name
    avatar_url = member.display_avatar.url if hasattr(member, "display_avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    
    roles_list = []
    top_color = "#c12aff"
    joined_at_iso = None
    created_at_iso = member.created_at.isoformat() if hasattr(member, "created_at") and member.created_at else None

    if isinstance(member, discord.Member):
        if member.joined_at:
            joined_at_iso = member.joined_at.isoformat()
        if member.top_role and member.top_role.color.value != 0:
            top_color = format_role_color(member.top_role.color)
        
        # Include all roles except @everyone, highest first
        for r in reversed(member.roles[1:]):
            roles_list.append({
                "id": str(r.id),
                "name": r.name,
                "color": format_role_color(r.color),
                "position": r.position
            })

    return {
        "id": str(member.id),
        "name": member.name,
        "display_name": display_name,
        "avatar": avatar_url,
        "bot": bool(member.bot),
        "top_role_color": top_color,
        "roles": roles_list,
        "joined_at": joined_at_iso,
        "created_at": created_at_iso
    }

def parse_components_to_embeds(components_list: list) -> list:
    """Parse Discord Components V2 Containers and ActionRows into rich embed representations for transcripts."""
    embeds = []
    if not components_list:
        return embeds

    for comp in components_list:
        c_dict = comp.to_dict() if hasattr(comp, "to_dict") else comp
        if not isinstance(c_dict, dict):
            continue

        ctype = c_dict.get("type")
        if ctype == 17:  # Components V2 Container
            accent = c_dict.get("accent_color")
            color_hex = f"#{accent:06x}" if accent else "#581C87"

            sub_comps = c_dict.get("components", [])
            text_lines = []
            footer_text = None
            gallery_urls = []
            buttons = []

            for sc in sub_comps:
                stype = sc.get("type")
                if stype == 10:  # TextDisplay
                    txt = sc.get("content", "")
                    if txt.startswith("-# "):
                        footer_text = txt[3:].strip()
                    else:
                        text_lines.append(txt)
                elif stype == 12:  # MediaGallery
                    for itm in sc.get("items", []):
                        m_obj = itm.get("media", {}) if isinstance(itm, dict) else {}
                        u = m_obj.get("url")
                        if u:
                            if u == "attachment://PRE_IN.png":
                                u = "/images/PRE IN.png"
                            elif u == "attachment://PRE.png":
                                u = "/images/PRE.png"
                            gallery_urls.append(u)
                elif stype == 1:  # ActionRow
                    for b in sc.get("components", []):
                        if b.get("type") == 2:
                            emoji_val = b.get("emoji", {}).get("name", "") if b.get("emoji") else ""
                            label_val = b.get("label", "")
                            buttons.append({
                                "emoji": emoji_val,
                                "label": label_val,
                                "style": b.get("style", 2),
                                "custom_id": b.get("custom_id", "")
                            })

            embed_item = {
                "title": None,
                "description": "\n\n".join(text_lines),
                "color": color_hex,
                "fields": [],
                "image": {"url": gallery_urls[0]} if gallery_urls else None,
                "images": gallery_urls,
                "footer": {"text": footer_text} if footer_text else None,
                "buttons": buttons,
                "is_v2_container": True
            }
            embeds.append(embed_item)

        elif ctype == 1:  # ActionRow
            buttons = []
            for b in c_dict.get("components", []):
                if b.get("type") == 2:
                    emoji_val = b.get("emoji", {}).get("name", "") if b.get("emoji") else ""
                    label_val = b.get("label", "")
                    buttons.append({
                        "emoji": emoji_val,
                        "label": label_val,
                        "style": b.get("style", 2),
                        "custom_id": b.get("custom_id", "")
                    })
            if buttons:
                embeds.append({
                    "title": None,
                    "description": "",
                    "color": "#4e5058",
                    "fields": [],
                    "image": None,
                    "buttons": buttons,
                    "is_v2_container": False
                })

    return embeds

async def extract_ticket_data(
    channel: discord.TextChannel,
    guild: discord.Guild,
    closer: discord.Member | discord.User,
    reason: str = "Ticket Closed",
    bot: commands.Bot = None
) -> dict:
    """Collect all messages, images, embeds, claim details, and participant profiles from channel."""
    meta = get_ticket_meta(channel.id)
    ticket_id = meta.get("ticket_id") or f"{channel.id}_{int(time.time())}"
    ticket_type = meta.get("ticket_type") or ("purchase" if "purchase" in channel.name else "support")

    # Resolve creator
    creator_id = meta.get("creator_id")
    creator_member = guild.get_member(int(creator_id)) if creator_id else None
    if not creator_member and creator_id and bot:
        try:
            creator_member = await bot.fetch_user(int(creator_id))
        except Exception:
            creator_member = None

    creator_profile = meta.get("creator") or (
        serialize_member_profile(creator_member, guild) if creator_member else {
            "id": creator_id or "0",
            "name": meta.get("creator_name", "Customer"),
            "display_name": meta.get("creator_display_name", "Customer"),
            "avatar": meta.get("creator_avatar", "https://cdn.discordapp.com/embed/avatars/0.png"),
            "bot": False,
            "top_role_color": "#c12aff",
            "roles": []
        }
    )

    # Resolve claimer
    claimed_by_id = meta.get("claimed_by_id")
    claimed_by_profile = None
    if claimed_by_id:
        claimed_member = guild.get_member(int(claimed_by_id))
        if not claimed_member and bot:
            try:
                claimed_member = await bot.fetch_user(int(claimed_by_id))
            except Exception:
                claimed_member = None
        if claimed_member:
            claimed_by_profile = serialize_member_profile(claimed_member, guild)
            claimed_by_profile["claimed_at"] = meta.get("claimed_at")
        else:
            claimed_by_profile = {
                "id": str(claimed_by_id),
                "name": meta.get("claimed_by_name", "Staff Member"),
                "display_name": meta.get("claimed_by_name", "Staff Member"),
                "avatar": meta.get("claimed_by_avatar", "https://cdn.discordapp.com/embed/avatars/0.png"),
                "bot": False,
                "top_role_color": "#00ff88",
                "roles": [],
                "claimed_at": meta.get("claimed_at")
            }

    # Closer profile
    closed_by_profile = serialize_member_profile(closer, guild)
    closed_by_profile["reason"] = reason

    # Catalog of all participants
    participants = {}
    if creator_profile and creator_profile.get("id"):
        participants[creator_profile["id"]] = creator_profile
    if claimed_by_profile and claimed_by_profile.get("id"):
        participants[claimed_by_profile["id"]] = claimed_by_profile
    if closed_by_profile and closed_by_profile.get("id"):
        participants[closed_by_profile["id"]] = closed_by_profile

    # Fetch messages
    messages_data = []
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    first_msg_time = None

    try:
        async for m in channel.history(limit=2000, oldest_first=True):
            if not first_msg_time:
                first_msg_time = m.created_at.isoformat()

            # Record participant
            if str(m.author.id) not in participants:
                participants[str(m.author.id)] = serialize_member_profile(m.author, guild)

            author_prof = participants[str(m.author.id)]

            # Attachments - Download locally before channel deletion!
            attachments_list = []
            att_dir = os.path.join(config.TRANSCRIPTS_DIR, "attachments", str(ticket_id))
            for att in m.attachments:
                is_img = bool(att.content_type and att.content_type.startswith("image")) or any(
                    att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]
                )
                local_rel_url = None
                data_uri = None
                try:
                    os.makedirs(att_dir, exist_ok=True)
                    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', att.filename)
                    disk_filename = f"{att.id}_{clean_name}"
                    disk_path = os.path.join(att_dir, disk_filename)

                    data = await att.read()
                    with open(disk_path, "wb") as f:
                        f.write(data)

                    local_rel_url = f"/data/transcripts/attachments/{ticket_id}/{disk_filename}"

                    if is_img and len(data) <= 5 * 1024 * 1024:
                        ext = att.filename.split('.')[-1].lower()
                        mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}")
                        b64 = base64.b64encode(data).decode('utf-8')
                        data_uri = f"data:{mime};base64,{b64}"
                except Exception as dl_err:
                    logger.warning(f"Could not download attachment {att.filename}: {dl_err}")

                attachments_list.append({
                    "id": str(att.id),
                    "filename": att.filename,
                    "url": local_rel_url or att.url,
                    "remote_url": att.url,
                    "data_uri": data_uri,
                    "size": att.size,
                    "is_image": is_img
                })

            # Embeds
            embeds_list = []
            for emb in m.embeds:
                emb_dict = {
                    "title": emb.title,
                    "description": emb.description,
                    "color": format_role_color(emb.color) if emb.color else "#581c87",
                    "fields": [{"name": f.name, "value": f.value, "inline": f.inline} for f in emb.fields],
                    "image": {"url": emb.image.url} if emb.image else None,
                    "thumbnail": {"url": emb.thumbnail.url} if emb.thumbnail else None,
                    "footer": {"text": emb.footer.text, "icon_url": emb.footer.icon_url} if emb.footer else None,
                    "author": {"name": emb.author.name, "icon_url": emb.author.icon_url} if emb.author else None,
                    "timestamp": emb.timestamp.isoformat() if emb.timestamp else None
                }
                embeds_list.append(emb_dict)

            # Components V2 (Containers, TextDisplays, ActionRows, Buttons)
            components_raw = []
            if hasattr(m, "components") and m.components:
                for c in m.components:
                    try:
                        components_raw.append(c.to_dict() if hasattr(c, "to_dict") else {})
                    except Exception:
                        pass

                v2_embeds = parse_components_to_embeds(m.components)
                embeds_list.extend(v2_embeds)

            messages_data.append({
                "id": str(m.id),
                "author_id": str(m.author.id),
                "author_name": author_prof["name"],
                "author_display_name": author_prof["display_name"],
                "author_avatar": author_prof["avatar"],
                "author_bot": author_prof["bot"],
                "author_role_color": author_prof.get("top_role_color", "#c12aff"),
                "timestamp": m.created_at.isoformat(),
                "content": m.content,
                "attachments": attachments_list,
                "embeds": embeds_list,
                "components": components_raw
            })
    except Exception as e:
        logger.error(f"Error fetching channel history for {channel.name}: {e}")

    created_at_val = meta.get("created_at") or first_msg_time or now_iso
    closed_at_val = now_iso

    return {
        "id": ticket_id,
        "channel_id": str(channel.id),
        "channel_name": channel.name,
        "ticket_type": ticket_type,
        "created_at": created_at_val,
        "closed_at": closed_at_val,
        "creator": creator_profile,
        "claimed_by": claimed_by_profile,
        "closed_by": closed_by_profile,
        "close_reason": reason,
        "purchase_details": {
            "plan": meta.get("plan") or "GX App License",
            "payment_method": meta.get("payment_method") or "Direct Payment",
            "notes": meta.get("notes") or ""
        },
        "support_details": {
            "category": meta.get("category") or "General Inquiry",
            "issue": meta.get("notes") or ""
        },
        "rating": {
            "score": meta.get("rating"),
            "stars": ("⭐" * int(meta["rating"])) if meta.get("rating") else None,
            "comment": meta.get("comment"),
            "submitted_at": meta.get("rating_at")
        } if meta.get("rating") else None,
        "participants": participants,
        "messages": messages_data
    }

def render_html_transcript(data: dict) -> str:
    """Generate a high-fidelity, self-contained Discord-styled HTML transcript page."""
    json_str = json.dumps(data, ensure_ascii=False)
    channel_name_safe = html.escape(data.get('channel_name', 'ticket'))
    ticket_type_safe = html.escape(str(data.get('ticket_type', 'purchase')))
    messages_count = len(data.get('messages', []))

    creator = data.get('creator', {})
    creator_display = html.escape(str(creator.get('display_name', 'Customer')))
    creator_avatar = html.escape(str(creator.get('avatar', 'https://cdn.discordapp.com/embed/avatars/0.png')))
    creator_id = html.escape(str(creator.get('id', '0')))

    claimed = data.get('claimed_by')
    if claimed:
        claimed_display = html.escape(str(claimed.get('display_name', 'Staff')))
        claimed_avatar = html.escape(str(claimed.get('avatar', 'https://cdn.discordapp.com/embed/avatars/0.png')))
        claimed_id = html.escape(str(claimed.get('id', '0')))
        claimed_html = f'''
          <span class="clickable-user" onclick="showUserProfile('{claimed_id}')">
            <img class="meta-avatar" src="{claimed_avatar}" alt="avatar" />
            <span>{claimed_display}</span>
          </span>
        '''
    else:
        claimed_html = '<span style="color: #ed4245;">❌ Unclaimed</span>'

    closed = data.get('closed_by', {})
    closed_display = html.escape(str(closed.get('display_name', 'Staff')))
    closed_avatar = html.escape(str(closed.get('avatar', 'https://cdn.discordapp.com/embed/avatars/0.png')))
    closed_id = html.escape(str(closed.get('id', '0')))

    plan_title = data.get('purchase_details', {}).get('plan', 'GX App License') if data.get('ticket_type') == 'purchase' else data.get('support_details', {}).get('category', 'Support')
    plan_title_safe = html.escape(str(plan_title))

    pay_method = data.get('purchase_details', {}).get('payment_method', 'N/A') if data.get('ticket_type') == 'purchase' else 'N/A'
    pay_method_safe = html.escape(str(pay_method))

    rating_html = ''
    if data.get('rating'):
        r_stars = html.escape(str(data['rating'].get('stars', '⭐⭐⭐⭐⭐')))
        r_comment = html.escape(str(data['rating'].get('comment', 'Great service!')))
        rating_html = f'''
        <div class="rating-banner">
          <div>
            <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--gx-gold); display: block; margin-bottom: 2px;">⭐ CUSTOMER REVIEW</span>
            <div class="rating-stars">{r_stars}</div>
          </div>
          <div class="rating-comment">
            "{r_comment}"
          </div>
        </div>
        '''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ticket Transcript — #{channel_name_safe}</title>
  <link rel="icon" type="image/png" href="https://raw.githubusercontent.com/discord/discord-api-docs/master/images/discord-logo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Michroma&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-chat: #313338;
      --bg-header: #2b2d31;
      --bg-sidebar: #1e1f22;
      --bg-card: #2b2d31;
      --bg-popover: #232428;
      --bg-hover: rgba(255, 255, 255, 0.04);
      --text-normal: #dbdee1;
      --text-muted: #949ba4;
      --text-header: #f2f3f5;
      --brand: #5865F2;
      --brand-glow: rgba(88, 101, 242, 0.3);
      --gx-purple: #C12AFF;
      --gx-dark-purple: #581C87;
      --gx-green: #00FF88;
      --gx-gold: #FFD700;
      --border-subtle: rgba(255, 255, 255, 0.08);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-chat);
      color: var(--text-normal);
      font-family: 'gg sans', 'Space Grotesk', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 15px;
      line-height: 1.45;
      overflow-x: hidden;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    a {{ color: #00a8fc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .discord-header {{
      background: var(--bg-header);
      height: 56px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .channel-icon {{
      color: #80848e;
      font-size: 20px;
      font-weight: bold;
    }}
    .channel-name {{
      font-weight: 700;
      color: var(--text-header);
      font-size: 16px;
    }}
    .header-badge {{
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .badge-closed {{ background: rgba(237, 66, 69, 0.2); color: #f23f43; border: 1px solid rgba(237, 66, 69, 0.4); }}
    .badge-purchase {{ background: rgba(193, 42, 255, 0.2); color: var(--gx-purple); border: 1px solid rgba(193, 42, 255, 0.4); }}
    .badge-support {{ background: rgba(0, 255, 136, 0.2); color: var(--gx-green); border: 1px solid rgba(0, 255, 136, 0.4); }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .action-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-subtle);
      color: var(--text-header);
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}
    .action-btn:hover {{
      background: var(--brand);
      border-color: var(--brand);
      color: #fff;
    }}

    .transcript-container {{
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 20px 60px;
      flex: 1;
    }}

    .meta-hero-card {{
      background: var(--bg-card);
      border: 1px solid rgba(193, 42, 255, 0.35);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 28px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
      position: relative;
      overflow: hidden;
    }}
    .meta-hero-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--gx-dark-purple), var(--gx-purple), var(--gx-green));
    }}
    .meta-hero-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .meta-item {{
      background: rgba(0, 0, 0, 0.25);
      padding: 10px 14px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
    }}
    .meta-label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .meta-value {{
      font-size: 13.5px;
      color: #fff;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .clickable-user {{
      cursor: pointer;
      color: #fff;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.05);
      transition: background 0.15s;
    }}
    .clickable-user:hover {{
      background: rgba(193, 42, 255, 0.25);
      color: var(--gx-purple);
    }}
    .meta-avatar {{
      width: 20px;
      height: 20px;
      border-radius: 50%;
      object-fit: cover;
    }}

    .rating-banner {{
      margin-top: 14px;
      background: rgba(255, 215, 0, 0.08);
      border: 1px solid rgba(255, 215, 0, 0.35);
      border-radius: 6px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .rating-stars {{
      color: var(--gx-gold);
      font-size: 18px;
      letter-spacing: 2px;
    }}
    .rating-comment {{
      color: #f4f4f5;
      font-size: 13.5px;
      font-style: italic;
      flex: 1;
      min-width: 220px;
    }}

    .messages-list {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .message-group {{
      display: flex;
      gap: 16px;
      padding: 8px 16px;
      border-radius: 4px;
      transition: background 0.15s;
      position: relative;
    }}
    .message-group:hover {{
      background: var(--bg-hover);
    }}
    .msg-avatar-wrap {{
      width: 40px;
      height: 40px;
      flex-shrink: 0;
      cursor: pointer;
    }}
    .msg-avatar {{
      width: 40px;
      height: 40px;
      border-radius: 50%;
      object-fit: cover;
      transition: transform 0.15s;
    }}
    .msg-avatar:hover {{
      transform: scale(1.06);
    }}
    .msg-content-wrap {{
      flex: 1;
      min-width: 0;
    }}
    .msg-header {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 4px;
    }}
    .msg-author {{
      font-weight: 600;
      font-size: 15px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .msg-author:hover {{
      text-decoration: underline;
    }}
    .bot-tag {{
      background: var(--brand);
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 3px;
      line-height: 1;
      vertical-align: middle;
    }}
    .msg-timestamp {{
      font-size: 11.5px;
      color: var(--text-muted);
      cursor: default;
    }}
    .msg-text {{
      color: var(--text-normal);
      word-wrap: break-word;
      white-space: pre-wrap;
      line-height: 1.4;
    }}
    .msg-text code {{
      background: #1e1f22;
      padding: 2px 4px;
      border-radius: 3px;
      font-family: Consolas, monospace;
      font-size: 13px;
    }}
    .msg-text pre {{
      background: #1e1f22;
      padding: 10px 14px;
      border-radius: 6px;
      margin: 6px 0;
      overflow-x: auto;
      font-family: Consolas, monospace;
      font-size: 13px;
    }}
    .msg-mention {{
      background: rgba(88, 101, 242, 0.18);
      color: #c9cdfb;
      padding: 1px 5px;
      border-radius: 3px;
      font-weight: 600;
      cursor: pointer;
    }}
    .msg-mention:hover {{
      background: var(--brand);
      color: #fff;
    }}

    .discord-embed {{
      background: var(--bg-card);
      border-left: 4px solid var(--gx-purple);
      border-radius: 4px;
      padding: 14px 16px;
      margin-top: 8px;
      max-width: 540px;
      display: grid;
      gap: 8px;
    }}
    .embed-title {{
      font-size: 14.5px;
      font-weight: 700;
      color: #fff;
    }}
    .embed-desc {{
      font-size: 13.5px;
      color: var(--text-normal);
      line-height: 1.4;
      white-space: pre-wrap;
    }}
    .embed-fields {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-top: 4px;
    }}
    .embed-field-name {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-header);
      margin-bottom: 2px;
    }}
    .embed-field-value {{
      font-size: 13px;
      color: var(--text-normal);
      white-space: pre-wrap;
    }}
    .embed-image {{
      max-width: 100%;
      border-radius: 4px;
      margin-top: 6px;
      cursor: pointer;
    }}
    .embed-footer {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    .msg-attachment {{
      margin-top: 8px;
    }}
    .attachment-img {{
      max-width: 480px;
      max-height: 380px;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--border-subtle);
    }}

    .discord-v2-container {{
      background: var(--bg-card);
      border-left: 4px solid var(--gx-purple);
      border-radius: 6px;
      padding: 14px 16px;
      margin-top: 8px;
      max-width: 580px;
    }}
    .embed-action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .embed-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 13px;
      font-weight: 600;
      user-select: none;
    }}
    .embed-btn-1 {{ background: #5865f2; color: #fff; }}
    .embed-btn-2 {{ background: #4e5058; color: #dbdee1; }}
    .embed-btn-3 {{ background: #248046; color: #fff; }}
    .embed-btn-4 {{ background: #da373c; color: #fff; }}
    .embed-btn-emoji {{ font-size: 16px; }}

    .attachment-fallback-card {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: #2b2d31;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 10px 14px;
      max-width: 440px;
      margin-top: 6px;
    }}
    .fallback-icon {{ font-size: 24px; }}
    .fallback-info {{ flex: 1; min-width: 0; }}
    .fallback-name {{ font-weight: 600; font-size: 13.5px; color: #f2f3f5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .fallback-meta {{ font-size: 11px; color: #949ba4; }}
    .fallback-btn {{
      padding: 4px 10px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      font-size: 11.5px;
      color: #dbdee1;
      text-decoration: none;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: background 0.15s;
    }}
    .fallback-btn:hover {{ background: #5865f2; color: #fff; text-decoration: none; }}

    .profile-modal-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      z-index: 999;
      align-items: center;
      justify-content: center;
    }}
    .profile-modal-overlay.active {{
      display: flex;
    }}
    .discord-profile-card {{
      background: var(--bg-popover);
      width: 340px;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(193, 42, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.1);
      animation: popIn 0.18s cubic-bezier(0.18, 0.89, 0.32, 1.28);
      position: relative;
    }}
    @keyframes popIn {{
      from {{ transform: scale(0.92); opacity: 0; }}
      to {{ transform: scale(1); opacity: 1; }}
    }}
    .profile-banner {{
      height: 105px;
      background: linear-gradient(135deg, var(--gx-dark-purple), var(--gx-purple));
      position: relative;
    }}
    .profile-close-btn {{
      position: absolute;
      top: 10px;
      right: 12px;
      width: 28px;
      height: 28px;
      background: rgba(0, 0, 0, 0.4);
      border: none;
      border-radius: 50%;
      color: #fff;
      font-size: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }}
    .profile-close-btn:hover {{
      background: rgba(0, 0, 0, 0.8);
    }}
    .profile-avatar-container {{
      position: absolute;
      bottom: -36px;
      left: 18px;
    }}
    .profile-avatar-img {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      border: 6px solid var(--bg-popover);
      background: var(--bg-popover);
      object-fit: cover;
    }}
    .profile-body {{
      padding: 44px 18px 20px;
    }}
    .profile-names {{
      margin-bottom: 12px;
    }}
    .profile-display-name {{
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .profile-username {{
      font-size: 14px;
      color: var(--text-muted);
    }}
    .profile-divider {{
      height: 1px;
      background: rgba(255, 255, 255, 0.1);
      margin: 14px 0;
    }}
    .profile-section-title {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .profile-roles {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }}
    .role-pill {{
      background: #2b2d31;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      padding: 4px 8px;
      font-size: 12px;
      color: #dbdee1;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .role-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .profile-member-since {{
      font-size: 12.5px;
      color: #dbdee1;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .profile-user-id {{
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11.5px;
      color: var(--text-muted);
      font-family: Consolas, monospace;
    }}
    .copy-id-btn {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-subtle);
      color: #fff;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
    }}
    .copy-id-btn:hover {{
      background: var(--brand);
    }}
  </style>
</head>
<body>

  <header class="discord-header">
    <div class="header-left">
      <span class="channel-icon">#</span>
      <span class="channel-name">{channel_name_safe}</span>
      <span class="header-badge badge-closed">CLOSED</span>
      <span class="header-badge badge-{ticket_type_safe}">{ticket_type_safe.upper()}</span>
    </div>
    <div class="header-actions">
      <button type="button" class="action-btn" onclick="downloadJSON()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        JSON
      </button>
      <button type="button" class="action-btn" onclick="window.print()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
        Print
      </button>
    </div>
  </header>

  <main class="transcript-container">

    <section class="meta-hero-card">
      <div class="meta-hero-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--gx-purple);"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        <span>Ticket Archive — #{channel_name_safe}</span>
      </div>

      <div class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">👤 CUSTOMER</div>
          <div class="meta-value">
            <span class="clickable-user" onclick="showUserProfile('{creator_id}')">
              <img class="meta-avatar" src="{creator_avatar}" alt="avatar" />
              <span>{creator_display}</span>
            </span>
          </div>
        </div>

        <div class="meta-item">
          <div class="meta-label">🤝 CLAIMED BY</div>
          <div class="meta-value">
            {claimed_html}
          </div>
        </div>

        <div class="meta-item">
          <div class="meta-label">🔒 CLOSED BY</div>
          <div class="meta-value">
            <span class="clickable-user" onclick="showUserProfile('{closed_id}')">
              <img class="meta-avatar" src="{closed_avatar}" alt="avatar" />
              <span>{closed_display}</span>
            </span>
          </div>
        </div>

        <div class="meta-item">
          <div class="meta-label">📦 LICENSE PLAN</div>
          <div class="meta-value" style="color: var(--gx-purple);">
            {plan_title_safe}
          </div>
        </div>

        <div class="meta-item">
          <div class="meta-label">💳 PAYMENT METHOD</div>
          <div class="meta-value">
            {pay_method_safe}
          </div>
        </div>

        <div class="meta-item">
          <div class="meta-label">⏱️ TOTAL MESSAGES</div>
          <div class="meta-value">
            {messages_count} Messages
          </div>
        </div>
      </div>

      {rating_html}
    </section>

    <div id="messages-list" class="messages-list">
      <!-- Injected via JavaScript -->
    </div>

  </main>

  <div id="profile-modal" class="profile-modal-overlay" onclick="closeProfileModal(event)">
    <div class="discord-profile-card" onclick="event.stopPropagation()">
      <div id="modal-banner" class="profile-banner">
        <button type="button" class="profile-close-btn" onclick="closeProfileModal()" title="Close">&times;</button>
        <div class="profile-avatar-container">
          <img id="modal-avatar" class="profile-avatar-img" src="" alt="avatar" />
        </div>
      </div>
      <div class="profile-body">
        <div class="profile-names">
          <div class="profile-display-name">
            <span id="modal-display-name">User</span>
            <span id="modal-bot-badge" class="bot-tag" style="display: none;">BOT</span>
          </div>
          <div id="modal-username" class="profile-username">@username</div>
        </div>
        <div class="profile-divider"></div>

        <div class="profile-section-title">ROLES</div>
        <div id="modal-roles" class="profile-roles"></div>

        <div class="profile-section-title">MEMBER SINCE</div>
        <div id="modal-member-since" class="profile-member-since"></div>

        <div class="profile-user-id">
          <span>USER ID: <span id="modal-user-id">0</span></span>
          <button type="button" class="copy-id-btn" onclick="copyUserId()">Copy ID</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const TRANSCRIPT_DATA = {json_str};

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    function formatTime(isoStr) {{
      if (!isoStr) return '';
      try {{
        const d = new Date(isoStr);
        return d.toLocaleDateString('en-US', {{ month: 'numeric', day: 'numeric', year: 'numeric' }}) +
               ' ' + d.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit' }});
      }} catch (e) {{
        return isoStr;
      }}
    }}

    function formatDateShort(isoStr) {{
      if (!isoStr) return 'N/A';
      try {{
        const d = new Date(isoStr);
        return d.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', year: 'numeric' }});
      }} catch (e) {{
        return isoStr;
      }}
    }}

    function parseDiscordMarkdown(content) {{
      if (!content) return '';
      let text = escapeHtml(content);

      text = text.replace(/```([a-z]*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>');
      text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
      text = text.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
      text = text.replace(/\\*([^\\*]+)\\*/g, '<em>$1</em>');
      text = text.replace(/~~([^~]+)~~/g, '<del>$1</del>');
      text = text.replace(/^> (.*)$/gm, '<blockquote style="border-left: 3px solid #4e5058; padding-left: 8px; margin: 4px 0; color: #dbdee1;">$1</blockquote>');

      text = text.replace(/&lt;@!?([0-9]+)&gt;/g, (match, uid) => {{
        const p = TRANSCRIPT_DATA.participants ? TRANSCRIPT_DATA.participants[uid] : null;
        const name = p ? ('@' + (p.display_name || p.name)) : ('@User');
        return `<span class="msg-mention" onclick="showUserProfile('${{uid}}')">${{escapeHtml(name)}}</span>`;
      }});

      text = text.replace(/&lt;@&amp;([0-9]+)&gt;/g, '<span class="msg-mention">@Role</span>');
      text = text.replace(/&lt;#([0-9]+)&gt;/g, '<span class="msg-mention">#channel</span>');

      return text;
    }}

    function renderMessages() {{
      const container = document.getElementById('messages-list');
      if (!container) return;

      const msgs = TRANSCRIPT_DATA.messages || [];
      if (!msgs.length) {{
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">No messages in this ticket.</div>';
        return;
      }}

      let htmlOut = '';
      msgs.forEach(m => {{
        const roleColor = m.author_role_color || '#c12aff';
        const formattedTime = formatTime(m.timestamp);

        let attHtml = '';
        if (m.attachments && m.attachments.length) {{
          m.attachments.forEach(att => {{
            const imgSrc = att.data_uri || att.url;
            if (att.is_image) {{
              attHtml += `<div class="msg-attachment"><img class="attachment-img" src="${{imgSrc}}" alt="${{escapeHtml(att.filename)}}" onclick="window.open('${{imgSrc}}', '_blank')" onerror="handleAttachmentImgError(this, '${{escapeHtml(att.filename)}}', '${{escapeHtml(att.url)}}')" /></div>`;
            }} else {{
              attHtml += `<div class="msg-attachment"><a href="${{att.url}}" target="_blank" class="action-btn">📎 ${{escapeHtml(att.filename)}}</a></div>`;
            }}
          }});
        }}

        let embedHtml = '';
        if (m.embeds && m.embeds.length) {{
          m.embeds.forEach(emb => {{
            let fieldsHtml = '';
            if (emb.fields && emb.fields.length) {{
              fieldsHtml = '<div class="embed-fields">' + emb.fields.map(f => `
                <div class="embed-field">
                  <div class="embed-field-name">${{escapeHtml(f.name)}}</div>
                  <div class="embed-field-value">${{parseDiscordMarkdown(f.value)}}</div>
                </div>
              `).join('') + '</div>';
            }}

            let embImage = '';
            if (emb.image && emb.image.url) {{
              let imgUrl = emb.image.url.replace('attachment://PRE_IN.png', '/images/PRE IN.png').replace('attachment://PRE.png', '/images/PRE.png');
              embImage = `<img class="embed-image" src="${{imgUrl}}" onclick="window.open('${{imgUrl}}', '_blank')" onerror="this.style.display='none'" />`;
            }}

            let buttonsHtml = '';
            if (emb.buttons && emb.buttons.length) {{
              buttonsHtml = '<div class="embed-action-row">' + emb.buttons.map(b => `
                <span class="embed-btn embed-btn-${{b.style || 2}}">
                  ${{b.emoji ? `<span class="embed-btn-emoji">${{escapeHtml(b.emoji)}}</span>` : ''}}
                  ${{b.label ? `<span>${{escapeHtml(b.label)}}</span>` : ''}}
                </span>
              `).join('') + '</div>';
            }}

            embedHtml += `
              <div class="discord-embed ${{emb.is_v2_container ? 'discord-v2-container' : ''}}" style="border-left-color: ${{emb.color || 'var(--gx-purple)'}};">
                ${{emb.title ? `<div class="embed-title">${{escapeHtml(emb.title)}}</div>` : ''}}
                ${{emb.description ? `<div class="embed-desc">${{parseDiscordMarkdown(emb.description)}}</div>` : ''}}
                ${{embImage}}
                ${{fieldsHtml}}
                ${{buttonsHtml}}
                ${{emb.footer && emb.footer.text ? `<div class="embed-footer">${{escapeHtml(emb.footer.text)}}</div>` : ''}}
              </div>
            `;
          }});
        }}

        htmlOut += `
          <div class="message-group">
            <div class="msg-avatar-wrap" onclick="showUserProfile('${{m.author_id}}')">
              <img class="msg-avatar" src="${{m.author_avatar}}" alt="${{escapeHtml(m.author_name)}}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'" />
            </div>
            <div class="msg-content-wrap">
              <div class="msg-header">
                <span class="msg-author" style="color: ${{roleColor}};" onclick="showUserProfile('${{m.author_id}}')">
                  ${{escapeHtml(m.author_display_name || m.author_name)}}
                </span>
                ${{m.author_bot ? '<span class="bot-tag">BOT</span>' : ''}}
                <span class="msg-timestamp">${{formattedTime}}</span>
              </div>
              ${{m.content ? `<div class="msg-text">${{parseDiscordMarkdown(m.content)}}</div>` : ''}}
              ${{attHtml}}
              ${{embedHtml}}
            </div>
          </div>
        `;
      }});

      container.innerHTML = htmlOut;
    }}

    window.handleAttachmentImgError = function(imgEl, filename, originalUrl) {{
      const wrap = imgEl.parentElement;
      if (!wrap) return;
      wrap.innerHTML = `
        <div class="attachment-fallback-card">
          <div class="fallback-icon">🖼️</div>
          <div class="fallback-info">
            <div class="fallback-name">${{escapeHtml(filename)}}</div>
            <div class="fallback-meta">Attachment archived • (Discord CDN session expired)</div>
          </div>
          <a href="${{escapeHtml(originalUrl)}}" target="_blank" class="fallback-btn">Open Link ↗</a>
        </div>
      `;
    }};

    function showUserProfile(userId) {{
      const p = (TRANSCRIPT_DATA.participants && TRANSCRIPT_DATA.participants[userId]) || null;
      if (!p) return;

      const modal = document.getElementById('profile-modal');
      const banner = document.getElementById('modal-banner');
      const avatar = document.getElementById('modal-avatar');
      const displayName = document.getElementById('modal-display-name');
      const username = document.getElementById('modal-username');
      const botBadge = document.getElementById('modal-bot-badge');
      const rolesContainer = document.getElementById('modal-roles');
      const memberSince = document.getElementById('modal-member-since');
      const userIdEl = document.getElementById('modal-user-id');

      const topColor = p.top_role_color || '#581C87';
      banner.style.background = `linear-gradient(135deg, ${{topColor}}, #1e1f22)`;

      avatar.src = p.avatar || 'https://cdn.discordapp.com/embed/avatars/0.png';
      displayName.textContent = p.display_name || p.name || 'User';
      username.textContent = '@' + (p.name || 'user');
      botBadge.style.display = p.bot ? 'inline-block' : 'none';
      userIdEl.textContent = p.id;

      if (p.roles && p.roles.length) {{
        rolesContainer.innerHTML = p.roles.map(r => `
          <div class="role-pill">
            <span class="role-dot" style="background: ${{r.color || '#c12aff'}};"></span>
            <span>${{escapeHtml(r.name)}}</span>
          </div>
        `).join('');
      }} else {{
        rolesContainer.innerHTML = '<span style="font-size: 12px; color: var(--text-muted);">No server roles</span>';
      }}

      const discordJoined = formatDateShort(p.created_at);
      const serverJoined = formatDateShort(p.joined_at);
      memberSince.innerHTML = `
        <div><span style="color: var(--text-muted);">Discord:</span> <strong>${{discordJoined}}</strong></div>
        <div><span style="color: var(--text-muted);">GX Server:</span> <strong>${{serverJoined}}</strong></div>
      `;

      modal.classList.add('active');
    }}

    function closeProfileModal(event) {{
      if (event && event.target !== event.currentTarget) return;
      document.getElementById('profile-modal').classList.remove('active');
    }}

    function copyUserId() {{
      const uid = document.getElementById('modal-user-id').textContent;
      navigator.clipboard.writeText(uid).then(() => {{
        const btn = document.querySelector('.copy-id-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy ID', 1500);
      }});
    }}

    function downloadJSON() {{
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(TRANSCRIPT_DATA, null, 2));
      const a = document.createElement('a');
      a.setAttribute("href", dataStr);
      a.setAttribute("download", `transcript_${{TRANSCRIPT_DATA.id || 'ticket'}}.json`);
      document.body.appendChild(a);
      a.click();
      a.remove();
    }}

    renderMessages();
  </script>
</body>
</html>
"""

async def log_and_export_ticket(
    channel: discord.TextChannel,
    guild: discord.Guild,
    closer: discord.Member | discord.User,
    reason: str = "Ticket Closed",
    bot: commands.Bot = None
) -> dict:
    """Extract ticket history, save JSON and HTML, and dispatch audit log embed to channel 1548141255710736386."""
    try:
        data = await extract_ticket_data(channel, guild, closer, reason, bot)
        ticket_id = data["id"]

        # 1. Save JSON transcript
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
        json_path = os.path.join(config.TRANSCRIPTS_DIR, f"transcript_{ticket_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON transcript to {json_path}")

        # 2. Save standalone HTML transcript
        html_content = render_html_transcript(data)
        html_path = os.path.join(config.TRANSCRIPTS_DIR, f"transcript_{ticket_id}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Saved HTML transcript to {html_path}")

        # 3. Dispatch to Ticket Logs Room (1548141255710736386)
        log_ch = guild.get_channel(config.TICKET_LOG_CHANNEL_ID)
        if not log_ch and bot:
            try:
                log_ch = await bot.fetch_channel(config.TICKET_LOG_CHANNEL_ID)
            except Exception as e:
                logger.warning(f"Could not fetch ticket log channel {config.TICKET_LOG_CHANNEL_ID}: {e}")

        if log_ch and isinstance(log_ch, discord.TextChannel):
            creator = data.get("creator", {})
            claimed = data.get("claimed_by")
            closed = data.get("closed_by", {})
            ttype = data.get("ticket_type", "purchase")

            web_url = f"{config.PORTAL_BASE_URL}/transcript.html?id={ticket_id}"

            embed = discord.Embed(
                title=f"📑 Ticket Transcript — #{channel.name}",
                description=f"Ticket session closed and archived. Full chat history, embeds, and profiles recorded.",
                color=0x581C87,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            # Details Field
            claim_text = f"<@{claimed['id']}>" if claimed else "❌ `Unclaimed`"
            details_text = (
                f"• **Channel**: `#{channel.name}`\n"
                f"• **Ticket Type**: `{'🛒 Purchase Ticket' if ttype == 'purchase' else '🛠️ Support Ticket'}`\n"
                f"• **Opened By**: <@{creator.get('id', '0')}> (`{creator.get('display_name', 'Customer')}`)\n"
                f"• **Claimed By**: {claim_text}\n"
                f"• **Closed By**: <@{closed.get('id', closer.id)}> (`{closer.display_name}`)\n"
                f"• **Close Reason**: `{reason}`"
            )
            embed.add_field(name="📋 Ticket Information", value=details_text, inline=False)

            # Order / Review field if purchase
            if ttype == "purchase":
                pdetails = data.get("purchase_details", {})
                rating_data = data.get("rating")
                rating_str = f"{rating_data['stars']} (`{rating_data['comment']}`)" if rating_data else "*No rating submitted*"

                order_text = (
                    f"• **Selected Plan**: `{pdetails.get('plan', 'GX App License')}`\n"
                    f"• **Payment Method**: `{pdetails.get('payment_method', 'N/A')}`\n"
                    f"• **Service Rating**: {rating_str}"
                )
                embed.add_field(name="🛒 Order & Quality Review", value=order_text, inline=False)
            elif ttype == "support":
                sdetails = data.get("support_details", {})
                support_text = (
                    f"• **Category**: `{sdetails.get('category', 'General')}`\n"
                    f"• **Inquiry Notes**: `{sdetails.get('issue', 'None provided')}`"
                )
                embed.add_field(name="🔧 Support Details", value=support_text, inline=False)

            embed.add_field(
                name="📊 Session Statistics",
                value=f"• **Total Messages**: `{len(data.get('messages', []))}`\n• **Participants**: `{len(data.get('participants', {}))}`",
                inline=True
            )

            embed.set_footer(text="GX Ticket Archiver • Web & Offline Transcripts", icon_url=guild.icon.url if guild.icon else None)

            # Action Row with Web Transcript Button
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="🌐 View Web Transcript",
                style=discord.ButtonStyle.link,
                url=web_url
            ))

            # HTML File attachment for offline viewing
            file_att = discord.File(html_path, filename=f"transcript_{channel.name}.html")

            try:
                await log_ch.send(embed=embed, view=view, file=file_att)
                logger.info(f"Dispatched ticket transcript embed to channel {log_ch.id}")
            except Exception as e:
                logger.error(f"Failed to dispatch embed to ticket log channel: {e}")
        else:
            logger.warning(f"Ticket log channel {config.TICKET_LOG_CHANNEL_ID} not found or not a TextChannel.")

        # Clean active ticket metadata
        remove_ticket_meta(channel.id)
        return data

    except Exception as e:
        logger.error(f"Error generating transcript for {channel.name}: {e}", exc_info=True)
        return {}
