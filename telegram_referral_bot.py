from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import os

# ===== TOKEN =====
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Missing TOKEN")

# ===== SETTINGS =====
CHANNEL = "@AshleiArchive"
PRIVATE_CHANNEL = "@ashleepremium"
REQUIRED_JOINS = 2

# ===== DB =====
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

cur.execute("""
CREATE TABLE IF NOT EXISTS joins_log (
    user_id INTEGER,
    joined_user_id INTEGER,
    PRIMARY KEY (user_id, joined_user_id)
)
""")

conn.commit()

# ===== BUTTONS =====
def build_keyboard(joins):
    if joins >= REQUIRED_JOINS:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔓 Unlock Now", callback_data="unlock")
        ]])

    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"{joins}/{REQUIRED_JOINS} Share",
            url="https://t.me/share/url?url=https://t.me/AshleiArchive"
        )
    ]])

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

    warning = ""
    if joins == 1:
        warning = "\n⚠️ You are 1 invite away."

    msg = await update.message.reply_photo(
        photo=open("image.jpg", "rb"),
        caption=(
            "Invite friends to unlock\n"
            f"Progress: {joins}/{REQUIRED_JOINS}"
            f"{warning}"
        ),
        reply_markup=build_keyboard(joins)
    )

    cur.execute("UPDATE users SET message_id=? WHERE user_id=?", (msg.message_id, user_id))
    conn.commit()

# ===== UPDATE UI =====
async def update_ui(context, user_id, joins):
    cur.execute("SELECT message_id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if not row or not row[0]:
        return

    warning = ""
    if joins == 1:
        warning = "\n⚠️ You are 1 invite away."

    try:
        await context.bot.edit_message_caption(
            chat_id=user_id,
            message_id=row[0],
            caption=(
                "Invite friends to unlock\n"
                f"Progress: {joins}/{REQUIRED_JOINS}"
                f"{warning}"
            ),
            reply_markup=build_keyboard(joins)
        )
    except:
        pass

# ===== TRACK JOIN (ANTI-FAKE) =====
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member

    if not cm or not cm.invite_link:
        return

    if cm.new_chat_member.status != "member":
        return

    user_id = cm.invite_link.creator.id
    joined_user_id = cm.new_chat_member.user.id

    # prevent duplicate counting
    cur.execute("""
    SELECT 1 FROM joins_log
    WHERE user_id=? AND joined_user_id=?
    """, (user_id, joined_user_id))

    if cur.fetchone():
        return

    cur.execute("""
    INSERT INTO joins_log (user_id, joined_user_id)
    VALUES (?, ?)
    """, (user_id, joined_user_id))
    conn.commit()

    cur.execute("SELECT joins FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if not row:
        return

    joins = row[0] + 1

    if joins >= REQUIRED_JOINS:
        try:
            await context.bot.unban_chat_member(PRIVATE_CHANNEL, user_id)
        except:
            pass

    cur.execute("UPDATE users SET joins=? WHERE user_id=?", (joins, user_id))
    conn.commit()

    await update_ui(context, user_id, joins)

# ===== UNLOCK BUTTON =====
async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    cur.execute("SELECT joins FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if not row or row[0] < REQUIRED_JOINS:
        await query.edit_message_caption(
            caption="Not enough invites yet."
        )
        return

    try:
        await context.bot.unban_chat_member(PRIVATE_CHANNEL, user_id)
    except:
        pass

    await query.edit_message_caption(
        caption="Unlocked. Access granted."
    )

# ===== RUN BOT =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(ChatMemberHandler(track, ChatMemberHandler.CHAT_MEMBER))
app.add_handler(CallbackQueryHandler(unlock, pattern="unlock"))

app.run_polling()
