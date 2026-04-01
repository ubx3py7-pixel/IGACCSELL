"""
bot.py — Instagram Account Marketplace Bot
=========================================
Run:  python bot.py
"""

import logging
import telebot
from telebot import types

import config
import database as db
import keyboards as kb
from utils import fmt_account, fmt_account_detail, fmt_order_row

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ─── Bot instance ─────────────────────────────────────────────────────────────
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown")

# ─── In-memory state machine ──────────────────────────────────────────────────
#   state_data[user_id] = {"state": str, **extra_fields}

state_data: dict[int, dict] = {}

# State constants
S_IDLE           = "idle"
S_ADD_YEAR       = "add_year"
S_ADD_FOLLOWERS  = "add_followers"
S_ADD_FOLLOWING  = "add_following"
S_ADD_POSTS      = "add_posts"
S_ADD_TYPE       = "add_type"
S_ADD_PRICE      = "add_price"
S_BROADCAST      = "broadcast"
S_ADD_ADMIN      = "add_admin"


def get_state(uid: int) -> str:
    return state_data.get(uid, {}).get("state", S_IDLE)


def set_state(uid: int, state: str, **extra) -> None:
    state_data.setdefault(uid, {})
    state_data[uid]["state"] = state
    state_data[uid].update(extra)


def clear_state(uid: int) -> None:
    state_data.pop(uid, None)


# ─── Broadcast helpers ────────────────────────────────────────────────────────

def broadcast_to_users(text: str, exclude: int | None = None,
                       markup: types.InlineKeyboardMarkup | None = None) -> tuple[int, int]:
    users = db.get_all_user_ids()
    ok = fail = 0
    for uid in users:
        if uid == exclude:
            continue
        try:
            bot.send_message(uid, text, reply_markup=markup)
            ok += 1
        except Exception:
            fail += 1
    return ok, fail


def notify_admins(text: str, exclude: int | None = None) -> None:
    for aid in db.get_all_admin_ids():
        if aid == exclude:
            continue
        try:
            bot.send_message(aid, text)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  USER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message) -> None:
    user = message.from_user
    is_new = db.upsert_user(user.id, user.username or "", user.first_name or "")
    if is_new:
        log.info("New user: %s (%s)", user.id, user.username)

    welcome = (
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "🛒 *Instagram Account Marketplace*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Browse and purchase aged Instagram accounts "
        "with real follower bases.\n\n"
        "Use the buttons below to get started 👇"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=kb.main_menu())


@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back_main(call: types.CallbackQuery) -> None:
    bot.edit_message_text(
        "🏠 *Main Menu* — What would you like to do?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb.main_menu(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "how_it_works")
def cb_how_it_works(call: types.CallbackQuery) -> None:
    text = (
        "ℹ️ *How It Works*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*1.* Browse accounts by creation year\n"
        "*2.* Pick an account that fits your needs\n"
        "*3.* Click *Buy Now* and confirm your order\n"
        "*4.* Contact our admin to complete payment\n"
        "*5.* Receive your account credentials ✅\n\n"
        "💬 All transactions are handled personally "
        f"by our admin: *{config.ADMIN_USERNAME}*"
    )
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.back_to_main(),
    )


# ── Step 1: Browse → Year picker ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "browse")
def cb_browse(call: types.CallbackQuery) -> None:
    years = db.get_available_years()
    if not years:
        bot.edit_message_text(
            "😔 *No accounts available right now.*\n\nCheck back soon!",
            call.message.chat.id, call.message.message_id,
            reply_markup=kb.back_to_main(),
        )
        return

    bot.edit_message_text(
        "📅 *Select Account Creation Year*\n\n"
        "Older accounts tend to have higher authority.\n"
        "Choose a year to see available accounts:",
        call.message.chat.id, call.message.message_id,
        reply_markup=kb.year_select(years),
    )


# ── Step 2: Account listing ───────────────────────────────────────────────────

def _show_account_list(chat_id: int, message_id: int, year: int, page: int) -> None:
    per_page = config.ACCOUNTS_PER_PAGE
    accounts = db.get_accounts_by_year(year, page, per_page)
    total    = db.count_accounts_by_year(year)

    if not accounts:
        bot.edit_message_text(
            f"😔 No accounts available for *{year}*.",
            chat_id, message_id, reply_markup=kb.back_to_main(),
        )
        return

    lines = [f"📋 *Accounts from {year}* — {total} available\n"]
    for i, acc in enumerate(accounts, start=1 + page * per_page):
        lines.append(fmt_account(acc, index=i))
        lines.append("")          # blank line between accounts

    lines.append("_Tap an account below to view details & purchase_ 👇")
    text = "\n".join(lines)

    bot.edit_message_text(
        text, chat_id, message_id,
        reply_markup=kb.account_list(accounts, year, page, total),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("year:"))
def cb_year(call: types.CallbackQuery) -> None:
    year = int(call.data.split(":")[1])
    _show_account_list(call.message.chat.id, call.message.message_id, year, 0)


@bot.callback_query_handler(func=lambda c: c.data.startswith("page:"))
def cb_page(call: types.CallbackQuery) -> None:
    _, year_s, page_s = call.data.split(":")
    _show_account_list(call.message.chat.id, call.message.message_id,
                       int(year_s), int(page_s))


# ── Step 3: Account detail ────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("acc:"))
def cb_acc_detail(call: types.CallbackQuery) -> None:
    _, acc_id_s, year_s, page_s = call.data.split(":")
    acc = db.get_account_by_id(int(acc_id_s))

    if not acc or acc["is_sold"]:
        bot.answer_callback_query(call.id, "❌ Account no longer available!", show_alert=True)
        return

    text = (
        f"🔍 *Account Details*\n\n"
        f"{fmt_account_detail(acc)}\n\n"
        f"_Ready to buy? Tap Buy Now!_"
    )
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.account_detail(acc["id"], int(year_s), int(page_s)),
    )


# ── Step 4: Buy → Confirm ─────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy:"))
def cb_buy(call: types.CallbackQuery) -> None:
    acc_id = int(call.data.split(":")[1])
    acc    = db.get_account_by_id(acc_id)

    if not acc or acc["is_sold"]:
        bot.answer_callback_query(call.id, "❌ Account no longer available!", show_alert=True)
        return

    text = (
        f"🛒 *Order Summary*\n\n"
        f"{fmt_account_detail(acc)}\n\n"
        f"⚠️ After confirming, you'll be connected to our admin "
        f"to arrange payment and account transfer."
    )
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.order_confirm(acc_id),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def cb_confirm(call: types.CallbackQuery) -> None:
    acc_id = int(call.data.split(":")[1])
    acc    = db.get_account_by_id(acc_id)
    user   = call.from_user

    if not acc or acc["is_sold"]:
        bot.answer_callback_query(call.id, "❌ Account no longer available!", show_alert=True)
        return

    order_id = db.place_order(user.id, user.username or str(user.id), acc_id)
    log.info("Order #%s placed by user %s for account %s", order_id, user.id, acc_id)

    # Confirmation to buyer
    text = (
        f"✅ *Order Placed — #{order_id}*\n\n"
        f"{fmt_account_detail(acc)}\n\n"
        f"📩 *Next step:*\n"
        f"Contact our admin to arrange payment:\n"
        f"👤 {config.ADMIN_USERNAME}\n\n"
        f"_Share your Order ID_ `#{order_id}` _with the admin to proceed._"
    )
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.post_order(config.ADMIN_USERNAME),
    )

    # Admin notification
    admin_msg = (
        f"🔔 *New Order — #{order_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User:     [{user.first_name}](tg://user?id={user.id})\n"
        f"🆔 User ID:  `{user.id}`\n"
        f"📛 Username: @{user.username or 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Account:*\n{fmt_account_detail(acc)}"
    )
    notify_admins(admin_msg)


# ── My Orders ─────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "my_orders")
def cb_my_orders(call: types.CallbackQuery) -> None:
    orders = db.get_user_orders(call.from_user.id)
    if not orders:
        text = "📋 *My Orders*\n\nYou haven't placed any orders yet."
    else:
        rows = "\n".join(fmt_order_row(o, i) for i, o in enumerate(orders[:10], 1))
        text = f"📋 *My Orders* ({len(orders)} total)\n\n{rows}"

    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.back_to_main(),
    )


# ── No-op (pagination label) ──────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN FLOW
# ═══════════════════════════════════════════════════════════════════════════════

def admin_only(message: types.Message) -> bool:
    if not db.is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 *Admin only command.*")
        return False
    return True


@bot.message_handler(commands=["admin"])
def cmd_admin_panel(message: types.Message) -> None:
    if not admin_only(message):
        return
    bot.send_message(
        message.chat.id,
        "⚙️ *Admin Panel*\nChoose an action:",
        reply_markup=kb.admin_panel(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
def cb_admin_stats(call: types.CallbackQuery) -> None:
    if not db.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return
    stats = db.get_stats()
    text = (
        f"📊 *Bot Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users:       `{stats['total_users']}`\n"
        f"✅ Available Accounts:`{stats['available_accs']}`\n"
        f"💰 Sold Accounts:     `{stats['sold_accs']}`\n"
        f"📦 Total Orders:      `{stats['total_orders']}`\n"
        f"👮 Total Admins:      `{stats['total_admins']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Total Revenue:     `${stats['total_revenue']:.2f}`"
    )
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=kb.admin_panel(),
    )


# ── /addacc flow ──────────────────────────────────────────────────────────────

@bot.message_handler(commands=["addacc"])
def cmd_addacc(message: types.Message) -> None:
    if not admin_only(message):
        return
    _start_addacc(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_addacc")
def cb_admin_addacc(call: types.CallbackQuery) -> None:
    if not db.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _start_addacc(call.from_user.id, call.message.chat.id)


def _start_addacc(uid: int, chat_id: int) -> None:
    set_state(uid, S_ADD_YEAR)
    bot.send_message(
        chat_id,
        "➕ *Add New Account — Step 1/6*\n\n"
        "Enter the *creation year* of the Instagram account:\n"
        "_Example: 2018_",
    )


# ── /broadcast flow ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message: types.Message) -> None:
    if not admin_only(message):
        return
    _start_broadcast(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def cb_admin_broadcast(call: types.CallbackQuery) -> None:
    if not db.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _start_broadcast(call.from_user.id, call.message.chat.id)


def _start_broadcast(uid: int, chat_id: int) -> None:
    set_state(uid, S_BROADCAST)
    bot.send_message(
        chat_id,
        "📢 *Broadcast Message*\n\n"
        "Type the message you want to send to *all users*.\n"
        "Supports Markdown formatting.",
    )


# ── /addadmin flow ────────────────────────────────────────────────────────────

@bot.message_handler(commands=["addadmin"])
def cmd_addadmin(message: types.Message) -> None:
    if not admin_only(message):
        return
    _start_addadmin(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_addadmin")
def cb_admin_addadmin(call: types.CallbackQuery) -> None:
    if not db.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _start_addadmin(call.from_user.id, call.message.chat.id)


def _start_addadmin(uid: int, chat_id: int) -> None:
    set_state(uid, S_ADD_ADMIN)
    bot.send_message(
        chat_id,
        "👮 *Add Admin*\n\n"
        "Send the *numeric Telegram user ID* of the person you want to promote.\n\n"
        "_Tip: they can get their ID from @userinfobot_",
    )


# ── /stats shortcut ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["stats"])
def cmd_stats(message: types.Message) -> None:
    if not admin_only(message):
        return
    stats = db.get_stats()
    text = (
        f"📊 *Bot Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users:        `{stats['total_users']}`\n"
        f"✅ Available Accounts: `{stats['available_accs']}`\n"
        f"💰 Sold Accounts:      `{stats['sold_accs']}`\n"
        f"📦 Total Orders:       `{stats['total_orders']}`\n"
        f"👮 Total Admins:       `{stats['total_admins']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Total Revenue:      `${stats['total_revenue']:.2f}`"
    )
    bot.reply_to(message, text)


# ── Account-type callback (mid-flow) ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("acctype:"))
def cb_account_type(call: types.CallbackQuery) -> None:
    uid = call.from_user.id
    if get_state(uid) != S_ADD_TYPE:
        bot.answer_callback_query(call.id)
        return
    acc_type = call.data.split(":")[1]
    state_data[uid]["acc_type"] = acc_type
    set_state(uid, S_ADD_PRICE, **{k: v for k, v in state_data[uid].items() if k != "state"})
    bot.edit_message_text(
        f"✅ Type set to: *{acc_type}*\n\n"
        "➕ *Add New Account — Step 6/6*\n\n"
        "Enter the *price* in USD:\n_Example: 29.99_",
        call.message.chat.id, call.message.message_id,
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_cancel")
def cb_admin_cancel(call: types.CallbackQuery) -> None:
    clear_state(call.from_user.id)
    bot.edit_message_text(
        "❌ *Action cancelled.*",
        call.message.chat.id, call.message.message_id,
        reply_markup=kb.back_to_main(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT MESSAGE STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message: types.Message) -> None:
    uid  = message.from_user.id
    text = message.text.strip()
    state = get_state(uid)

    # ── Add Account wizard ────────────────────────────────────────────────────

    if state == S_ADD_YEAR:
        try:
            year = int(text)
            if not (2010 <= year <= 2025):
                raise ValueError
            state_data[uid]["year"] = year
            set_state(uid, S_ADD_FOLLOWERS, **{k: v for k, v in state_data[uid].items() if k != "state"})
            bot.reply_to(message,
                "➕ *Add New Account — Step 2/6*\n\n"
                "Enter the *Followers* count:\n_Example: 15000_")
        except ValueError:
            bot.reply_to(message, "❌ Invalid year. Enter a year between 2010 and 2025:")

    elif state == S_ADD_FOLLOWERS:
        try:
            followers = int(text.replace(",", "").replace(".", ""))
            state_data[uid]["followers"] = followers
            set_state(uid, S_ADD_FOLLOWING, **{k: v for k, v in state_data[uid].items() if k != "state"})
            bot.reply_to(message,
                "➕ *Add New Account — Step 3/6*\n\n"
                "Enter the *Following* count:\n_Example: 500_")
        except ValueError:
            bot.reply_to(message, "❌ Enter a valid number (e.g. 15000):")

    elif state == S_ADD_FOLLOWING:
        try:
            following = int(text.replace(",", "").replace(".", ""))
            state_data[uid]["following"] = following
            set_state(uid, S_ADD_POSTS, **{k: v for k, v in state_data[uid].items() if k != "state"})
            bot.reply_to(message,
                "➕ *Add New Account — Step 4/6*\n\n"
                "Enter the *Posts* count:\n_Example: 240_")
        except ValueError:
            bot.reply_to(message, "❌ Enter a valid number:")

    elif state == S_ADD_POSTS:
        try:
            posts = int(text.replace(",", "").replace(".", ""))
            state_data[uid]["posts"] = posts
            set_state(uid, S_ADD_TYPE, **{k: v for k, v in state_data[uid].items() if k != "state"})
            bot.reply_to(message,
                "➕ *Add New Account — Step 5/6*\n\n"
                "Select the account *type*:",
                reply_markup=kb.account_type_select())
        except ValueError:
            bot.reply_to(message, "❌ Enter a valid number:")

    elif state == S_ADD_PRICE:
        try:
            price = float(text.replace("$", "").replace(",", ""))
            if price <= 0:
                raise ValueError

            d = state_data[uid]
            acc_id = db.add_account(
                d["year"], d["followers"], d["following"],
                d["posts"], d["acc_type"], price,
            )
            acc = db.get_account_by_id(acc_id)
            clear_state(uid)
            log.info("Admin %s added account #%s", uid, acc_id)

            bot.reply_to(
                message,
                f"✅ *Account Added Successfully!*\n\n{fmt_account_detail(acc)}",
            )

            # Notify all users about new account
            notify_text = (
                f"📢 *New Account Available!*\n\n"
                f"A new *{d['acc_type']}* Instagram account from *{d['year']}* "
                f"has just been listed!\n\n"
                f"👥 {d['followers']:,} followers\n"
                f"💰 Price: *${price:.2f}*\n\n"
                f"Open the bot to browse and purchase! 👇"
            )
            browse_btn = types.InlineKeyboardMarkup()
            browse_btn.add(types.InlineKeyboardButton("🛍️ Browse Now", callback_data="browse"))
            ok, fail = broadcast_to_users(notify_text, exclude=uid, markup=browse_btn)
            bot.send_message(
                message.chat.id,
                f"📢 New account notification sent to {ok} users ({fail} failed).",
            )

        except ValueError:
            bot.reply_to(message, "❌ Enter a valid price (e.g. 29.99):")

    # ── Broadcast ─────────────────────────────────────────────────────────────

    elif state == S_BROADCAST:
        broadcast_text = (
            f"📢 *Announcement*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{text}"
        )
        clear_state(uid)
        ok, fail = broadcast_to_users(broadcast_text, exclude=uid)
        bot.reply_to(
            message,
            f"✅ Broadcast sent!\n👥 Delivered: {ok}\n❌ Failed: {fail}",
        )

    # ── Add Admin ─────────────────────────────────────────────────────────────

    elif state == S_ADD_ADMIN:
        # Support forwarded message or raw ID
        new_id: int | None = None
        if message.forward_from:
            new_id = message.forward_from.id
        else:
            try:
                new_id = int(text)
            except ValueError:
                pass

        if new_id is None:
            bot.reply_to(message,
                "❌ Could not read that user ID.\n"
                "Forward a message from them, or paste their numeric ID:")
            return

        db.add_admin(new_id, "")
        clear_state(uid)
        log.info("Admin %s added new admin %s", uid, new_id)
        bot.reply_to(
            message,
            f"✅ User `{new_id}` is now an admin!\n\n"
            f"_They will need to use /admin to access the panel._",
        )
        try:
            bot.send_message(
                new_id,
                "🎉 *Congratulations!* You've been promoted to admin.\n"
                "Use /admin to open the admin panel.",
            )
        except Exception:
            pass

    # ── Default ───────────────────────────────────────────────────────────────

    else:
        bot.send_message(
            message.chat.id,
            "👋 Use /start to open the menu.",
            reply_markup=kb.main_menu(),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    db.init_db()
    log.info("Database initialised ✓")
    log.info("Starting bot — polling…")
    bot.infinity_polling(timeout=30, long_polling_timeout=15)
