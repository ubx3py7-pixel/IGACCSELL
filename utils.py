"""
utils.py — Shared formatting helpers.
"""

import sqlite3


def fmt_account(acc: sqlite3.Row, index: int | None = None) -> str:
    """Return a nicely formatted account summary block."""
    type_icon = "🔒" if acc["account_type"] == "Private" else "🔓"
    header = f"*#{index}* " if index is not None else ""
    return (
        f"{header}{type_icon} *{acc['account_type']} Account · {acc['creation_year']}*\n"
        f"┌ 👥 Followers: `{acc['followers']:,}`\n"
        f"├ ➡️  Following: `{acc['following']:,}`\n"
        f"├ 📸 Posts:     `{acc['posts']:,}`\n"
        f"└ 💰 Price:     *${acc['price']:.2f}*"
    )


def fmt_account_detail(acc: sqlite3.Row) -> str:
    """Full detail block used on the detail screen."""
    type_icon = "🔒" if acc["account_type"] == "Private" else "🔓"
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{type_icon} *{acc['account_type']} Instagram Account*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅  Created:    *{acc['creation_year']}*\n"
        f"👥  Followers:  `{acc['followers']:,}`\n"
        f"➡️   Following:  `{acc['following']:,}`\n"
        f"📸  Posts:      `{acc['posts']:,}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰  *Price: ${acc['price']:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


def fmt_order_row(order: sqlite3.Row, idx: int) -> str:
    type_icon = "🔒" if order["account_type"] == "Private" else "🔓"
    date = order["placed_at"][:10]
    return (
        f"*{idx}.* Order #{order['id']} — {date}\n"
        f"   {type_icon} {order['account_type']} · {order['creation_year']}\n"
        f"   👥 {order['followers']:,} followers · 💰 ${order['price']:.2f}\n"
    )
