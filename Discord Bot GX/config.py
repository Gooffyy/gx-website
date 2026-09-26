import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

CLIENT_ROLE_ID = int(os.getenv("CLIENT_ROLE_ID", "1547640724604850186"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "1547640722013036637"))
ASSIGN_LOG_CHANNEL_ID = int(os.getenv("ASSIGN_LOG_CHANNEL_ID", "1547753183424806983"))
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8080/dashboard.html")
GUILD_ID = int(os.getenv("GUILD_ID", "1547636843388870748"))

# Resolve root data/licenses.json and vouches.json paths
LICENSES_FILE_PATH = os.getenv(
    "LICENSES_FILE_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "licenses.json"))
)
VOUCHES_FILE_PATH = os.getenv(
    "VOUCHES_FILE_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vouches.json"))
)
VOUCHES_CHANNEL_ID = int(os.getenv("VOUCHES_CHANNEL_ID", "1547753169864495154"))
TICKET_LOG_CHANNEL_ID = int(os.getenv("TICKET_LOG_CHANNEL_ID", "1548141255710736386"))
TRANSCRIPTS_DIR = os.getenv(
    "TRANSCRIPTS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "transcripts"))
)
PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "http://localhost:8080")

