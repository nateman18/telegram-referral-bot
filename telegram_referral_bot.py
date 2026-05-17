from telegram import Update
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
import sqlite3

# ===== CONFIG =====
TOKEN = "YOUR_BOT_TOKEN"
CHANNEL = "@YOUR_CHANNEL"

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invite_link TEXT,
    joins INTEGER DEFAULT 0,
    unlocked INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cur.execute("SELECT invite_link FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if row and row[0]:
        link = row[0]
    else:
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL,
            name=str(user_id)
        )

        link = link_obj.invite_link

        cur.execute("""
        INSERT OR REPLACE INTO users (user_id, invite_link, joins, unlocked)
        VALUES (?, ?, 0, 0)
        """, (user_id, link))
        conn.commit()

    await update.message.reply_text(
        "Join 2 people to unlock access:\n" + link
    )

# ===== TRACK JOINS =====
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member

    if not cm or not cm.invite_link:
        return

    if cm.new_chat_member.status != "member":
        return

    link_used = cm.invite_link.invite_link

    cur.execute("SELECT user_id, joins, unlocked FROM users WHERE invite_link=?",
                (link_used,))
    row = cur.fetchone()

    if not row:
        return

    user_id, joins, unlocked = row

    joins += 1

    if joins >= 2:
        unlocked = 1

    cur.execute("""
    UPDATE users SET joins=?, unlocked=? WHERE user_id=?
    """, (joins, unlocked, user_id))
    conn.commit()

# ===== APP =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(ChatMemberHandler(track, ChatMemberHandler.CHAT_MEMBER))