# Discord Server Manager Bot 🤖

A modular Discord Bot built in Python (`discord.py` v2) designed to streamline server management across all your Discord communities. Features slash commands, automated member onboarding (welcome messages & auto-roles), server event logging, and full moderation controls with SQLite persistence.

---

## 🚀 Setup & Setup Instructions

### 1. Create a Discord Bot Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name your bot (e.g., `ServerManager`), and create it.
3. In the left menu, navigate to **Bot**:
   - Click **Reset Token** (or Copy Token) and copy the **Bot Token**.
   - Scroll down to **Privileged Gateway Intents** and enable:
     - ✅ **Server Members Intent** (required for welcome messages, auto-roles, member join/leave logs)
     - ✅ **Message Content Intent** (required for message edit/delete event logging)
   - Save Changes.

### 2. Configure Environment Variables

1. Open the [.env](file:///d:/Discord%20Bot%20GX/.env) file in the project root directory.
2. Replace `your_bot_token_here` with your actual Discord Bot token:
   ```env
   DISCORD_TOKEN=your_actual_bot_token_here
   DEFAULT_PREFIX=!
   ```

### 3. Invite the Bot to Your Server

1. In the Discord Developer Portal, navigate to **OAuth2** -> **URL Generator**.
2. Under **Scopes**, check:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Under **Bot Permissions**, check:
   - ✅ `Administrator` (or select specific permissions: Manage Server, Manage Roles, Manage Channels, Kick Members, Ban Members, Moderate Members, Read/Send Messages, Manage Messages).
4. Copy the generated URL at the bottom, paste it into your browser, and select the server you want to manage.

### 4. Running the Bot

Using the pre-configured virtual environment:

```powershell
.\venv\Scripts\python main.py
```

---

## ⚡ Slash Command Reference

### 🛠️ Utility Commands
| Command | Description |
|---|---|
| `/ping` | Check bot latency and API ping. |
| `/serverinfo` | View server statistics, owner, member count, channel counts, and boost level. |
| `/userinfo [user]` | Display detailed information about a member (join date, account age, roles). |

### ⚙️ Server Management & Setup
| Command | Permissions Required | Description |
|---|---|---|
| `/setwelcome <channel> [message]` | Administrator | Configure welcome channel and message template. `{user}` and `{server}` placeholders supported. |
| `/setlogchannel <channel>` | Administrator | Route server audit logs (message deletions, edits, join/leaves) to a channel. |
| `/setautorole <role>` | Administrator | Automatically assign a role to new members upon joining. |
| `/createchannel <name> <type> [category]` | Manage Channels | Create a text or voice channel under an optional category. |
| `/createrole <name> [hex_color]` | Manage Roles | Create a new role with a custom hex color code (e.g. `#3498DB`). |

### 🛡️ Moderation Commands
| Command | Permissions Required | Description |
|---|---|---|
| `/kick <member> [reason]` | Kick Members | Kick a member from the server. |
| `/ban <member> [reason] [delete_days]` | Ban Members | Ban a member and optionally delete past messages (0-7 days). |
| `/unban <user_id> [reason]` | Ban Members | Unban a user by their numerical User ID. |
| `/timeout <member> <minutes> [reason]` | Moderate Members | Temporarily mute/timeout a member (up to 28 days). |
| `/purge <amount>` | Manage Messages | Bulk delete 1-100 messages in the current channel. |
| `/warn <member> <reason>` | Moderate Members | Issue a warning to a member and record it in the database. |
| `/warnings <member>` | Moderate Members | View all recorded warnings for a member. |
| `/clearwarnings <member>` | Moderate Members | Clear all recorded warnings for a member. |

---

## 📂 Project Architecture

```
d:/Discord Bot GX/
├── cogs/
│   ├── logging.py             # Event listeners (joins, leaves, edits, deletes)
│   ├── moderation.py          # Slash commands for kick, ban, warn, timeout, purge
│   ├── server_management.py   # Slash commands for welcome, log channel, autorole, channel/role creation
│   └── utility.py             # Slash commands for ping, serverinfo, userinfo
├── .env                       # Bot secret credentials (ignored in Git)
├── .env.example               # Environment template
├── .gitignore                 # Git exclusions (.env, venv/, *.db)
├── config.py                  # Environment config loader
├── database.py                # Async SQLite database wrapper (aiosqlite)
├── main.py                    # Main bot initialization & cog launcher
└── requirements.txt           # Python dependencies (discord.py, python-dotenv, aiosqlite)
```
