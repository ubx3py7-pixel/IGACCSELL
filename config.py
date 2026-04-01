import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Settings ───────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))   # Your Telegram user ID
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@YourAdminUsername")

# ─── Database ───────────────────────────────────────────────────────────────
DB_PATH = "instagram_shop.db"

# ─── Pagination ─────────────────────────────────────────────────────────────
ACCOUNTS_PER_PAGE = 5
