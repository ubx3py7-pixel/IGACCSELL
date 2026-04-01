# 🛒 Instagram Account Marketplace Bot

A fully-featured Telegram bot for selling Instagram accounts with inline navigation,
multi-step admin wizards, order notifications, and persistent SQLite storage.

---

## 📁 Project Structure

```
instagram_bot/
├── bot.py            ← Main bot (all handlers & state machine)
├── database.py       ← SQLite layer (users, accounts, orders, admins)
├── keyboards.py      ← All InlineKeyboardMarkup builders
├── utils.py          ← Formatting helpers
├── config.py         ← Env-based configuration
├── requirements.txt
├── .env.example      ← Copy to .env and fill in your values
└── README.md
```

---

## ⚡ Quick Start

### 1 — Create your bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive

### 2 — Get your Telegram user ID

Message **@userinfobot** — it replies with your numeric user ID.

### 3 — Set up the environment

```bash
cd instagram_bot
cp .env.example .env
# Edit .env with your token, user ID, and admin username
```

Your `.env` should look like:
```
BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPER_ADMIN_ID=987654321
ADMIN_USERNAME=@YourUsername
```

### 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### 5 — Run the bot

```bash
python bot.py
```

---

## 🧭 User Commands & Flow

| Action | How |
|---|---|
| Start / Main Menu | `/start` |
| Browse accounts | Tap **Browse Accounts** button |
| View account detail | Tap any account in the list |
| Place an order | Tap **Buy Now → Confirm Order** |
| View order history | Tap **My Orders** |

**Flow:**
```
/start
  └─ Browse Accounts
       └─ Select Year (2018 · 2019 · 2020 …)
            └─ Account List  ←→ Paginate
                 └─ Account Detail
                      └─ Buy Now
                           └─ Confirm Order
                                └─ Contact Admin (link)
```

---

## ⚙️ Admin Commands

| Command | Action |
|---|---|
| `/admin` | Open the inline admin panel |
| `/addacc` | Add a new account (6-step wizard) |
| `/broadcast` | Send a message to all users |
| `/addadmin` | Promote a user to admin |
| `/stats` | View bot statistics |

### Adding an Account (`/addacc` wizard)

```
Step 1 — Creation year   (e.g. 2018)
Step 2 — Followers       (e.g. 15000)
Step 3 — Following       (e.g. 500)
Step 4 — Posts           (e.g. 240)
Step 5 — Account type    [Public / Private] ← inline buttons
Step 6 — Price in USD    (e.g. 29.99)
```

After step 6 the account is saved and **all users receive a notification** automatically.

### Adding an Admin (`/addadmin`)

Send the target user's **numeric Telegram ID**, or **forward any message** from them.
The new admin can then access `/admin`.

---

## 🔔 Notification Events

| Event | Who gets notified |
|---|---|
| New account added | ✅ All registered users |
| Order confirmed by user | ✅ All admins |
| Promoted to admin | ✅ New admin (DM) |
| Broadcast sent | ✅ All registered users |

---

## 🗄️ Database Schema (SQLite)

```sql
users    (user_id, username, first_name, joined_at)
admins   (user_id, username, added_at)
accounts (id, creation_year, followers, following, posts,
          account_type, price, is_sold, added_at)
orders   (id, user_id, username, account_id, placed_at)
```

The database file `instagram_shop.db` is created automatically on first run.

---

## 🔐 Security Notes

- `SUPER_ADMIN_ID` is hardcoded via `.env` and **cannot be removed** by other admins.
- All admin commands check `is_admin()` before execution.
- Accounts are never deleted from the DB — they are marked `is_sold=1` after ordering,
  which hides them from the browse list.
- Keep your `.env` private. Never commit it to version control.

---

## 🚀 Running in Production

### systemd service

```ini
[Unit]
Description=Instagram Marketplace Bot
After=network.target

[Service]
WorkingDirectory=/path/to/instagram_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
EnvironmentFile=/path/to/instagram_bot/.env

[Install]
WantedBy=multi-user.target
```

### Or with screen / tmux

```bash
screen -S instabot
python bot.py
# Ctrl+A D to detach
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `pyTelegramBotAPI` | Telegram Bot API wrapper |
| `python-dotenv` | Load `.env` variables |

Python **3.10+** required (uses `X | Y` type union syntax).
