from telegram import Update
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
import sqlite3
import os

# ===== TOKEN =====
TOKEN = os.getenv("TOKEN")

# ===== SETTINGS =====
CHANNEL = "https://t.me/AshleiArchive"
PRIVATE_CHANNEL = "https://t.me/+_9Jo1QhekgNiN2I1"
REQUIRED_JOINS = 2

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invite_link TEXT,
    joins INTEGER DEFAULT 0,
    unlocked INTEGER DEFAULT 0,
    message_id INTEGER
)
""")
conn.commit()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cur.execute("SELECT invite_link, joins FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if row:
        link, joins = row
    else:
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL,
            name=str(user_id)
        )
        link = link_obj.invite_link
        joins = 0

        cur.execute("""
        INSERT OR REPLACE INTO users (user_id, invite_link, joins, unlocked, message_id)
        VALUES (?, ?, 0, 0, NULL)
        """, (user_id, link))
        conn.commit()

    msg = await update.message.reply_text(
        f"Share this link\n"
        f"Bring {REQUIRED_JOINS} people to unlock\n"
        f"Progress: {joins}/{REQUIRED_JOINS}\n\n"
        f"{link}"
    )

    cur.execute("UPDATE users SET message_id=? WHERE user_id=?", (msg.message_id, user_id))
    conn.commit()

# ===== UPDATE UI =====
async def update_ui(context, user_id, joins, link):
    cur.execute("SELECT message_id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if not row:
        return

    message_id = row[0]

    try:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=(
                f"Share this link\n"
                f"Bring {REQUIRED_JOINS} people to unlock\n"
                f"Progress: {joins}/{REQUIRED_JOINS}\n\n"
                f"{link}"
            )
        )
    except:
        pass

# ===== TRACK JOINS =====
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member

    if not cm or not cm.invite_link:
        return

    if cm.new_chat_member.status != "member":
        return

    link_used = cm.invite_link.invite_link

    cur.execute("""
    SELECT user_id, joins, invite_link, unlocked
    FROM users
    WHERE invite_link=?
    """, (link_used,))
    row = cur.fetchone()

    if not row:
        return

    user_id, joins, link, unlocked = row

    joins += 1

    if joins >= REQUIRED_JOINS:
        unlocked = 1
        try:
            await context.bot.unban_chat_member(PRIVATE_CHANNEL, user_id)
        except:
            pass

    cur.execute("""
    UPDATE users
    SET joins=?, unlocked=?
    WHERE user_id=?
    """, (joins, unlocked, user_id))
    conn.commit()

    await update_ui(context, user_id, joins, link)

# ===== RUN BOT =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(ChatMemberHandler(track, ChatMemberHandler.CHAT_MEMBER))

app.run_polling()
