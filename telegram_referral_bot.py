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

    msg = await update.message.reply_photo(
        photo=open("image.jpg", "rb"),
        caption=(
            "Invite friends to unlock\n"
            f"Progress: {joins}/{REQUIRED_JOINS}\n\n"
            "Tap share button below"
        ),
        reply_markup=build_keyboard(joins)
    )

    cur.execute(
        "UPDATE users SET message_id=? WHERE user_id=?",
        (msg.message_id, user_id)
    )
    conn.commit()
