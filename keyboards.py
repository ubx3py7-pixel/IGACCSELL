"""
keyboards.py — All InlineKeyboardMarkup builders for the bot.
"""

from telebot import types
from config import ACCOUNTS_PER_PAGE


# ─── User-facing keyboards ───────────────────────────────────────────────────

def main_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🛍️  Browse Accounts", callback_data="browse"),
        types.InlineKeyboardButton("📋  My Orders",        callback_data="my_orders"),
        types.InlineKeyboardButton("ℹ️   How It Works",     callback_data="how_it_works"),
    )
    return kb


def year_select(years: list[int]) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    btns = [
        types.InlineKeyboardButton(f"📅 {y}", callback_data=f"year:{y}")
        for y in years
    ]
    kb.add(*btns)
    kb.row(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    return kb


def account_list(accounts, year: int, page: int,
                 total: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)

    for acc in accounts:
        type_icon = "🔒" if acc["account_type"] == "Private" else "🔓"
        label = (
            f"{type_icon} {acc['followers']:,} flw · "
            f"{acc['posts']} posts · ${acc['price']:.2f}"
        )
        kb.add(types.InlineKeyboardButton(label, callback_data=f"acc:{acc['id']}:{year}:{page}"))

    # Pagination row
    total_pages = max(1, (total + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀️ Prev", callback_data=f"page:{year}:{page - 1}"))
    nav.append(types.InlineKeyboardButton(f"  {page + 1}/{total_pages}  ", callback_data="noop"))
    if (page + 1) * ACCOUNTS_PER_PAGE < total:
        nav.append(types.InlineKeyboardButton("Next ▶️", callback_data=f"page:{year}:{page + 1}"))
    if len(nav) > 1:
        kb.row(*nav)

    kb.row(types.InlineKeyboardButton("🔙 Back to Years", callback_data="browse"))
    return kb


def account_detail(account_id: int, year: int, page: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("💳  Buy Now", callback_data=f"buy:{account_id}"))
    kb.add(types.InlineKeyboardButton("🔙 Back to List", callback_data=f"page:{year}:{page}"))
    return kb


def order_confirm(account_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("✅ Confirm Order", callback_data=f"confirm:{account_id}"),
        types.InlineKeyboardButton("❌ Cancel",         callback_data="back_main"),
    )
    return kb


def post_order(admin_username: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    handle = admin_username.lstrip("@")
    kb.add(types.InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{handle}"))
    kb.add(types.InlineKeyboardButton("🏠 Main Menu",     callback_data="back_main"))
    return kb


def back_to_main() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="back_main"))
    return kb


# ─── Admin-facing keyboards ──────────────────────────────────────────────────

def account_type_select() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("🔓 Public",  callback_data="acctype:Public"),
        types.InlineKeyboardButton("🔒 Private", callback_data="acctype:Private"),
    )
    kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel"))
    return kb


def admin_panel() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(
        types.InlineKeyboardButton("➕ Add Account",  callback_data="admin_addacc"),
        types.InlineKeyboardButton("📢 Broadcast",    callback_data="admin_broadcast"),
    )
    kb.row(
        types.InlineKeyboardButton("👤 Add Admin",    callback_data="admin_addadmin"),
        types.InlineKeyboardButton("📊 Stats",        callback_data="admin_stats"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Close",     callback_data="back_main"))
    return kb
