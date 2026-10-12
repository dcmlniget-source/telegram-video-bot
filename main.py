import os
import random
import sqlite3
import logging
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = "8894164052:AAHGUTlFdf4lI_4zvH3-2WnOJzjKHLwigak"
ADMIN_IDS = [123456789]  # Change to your numeric Telegram User ID
PORT = int(os.environ.get("PORT", 8080))
WEBAPP_URL = "https://placeholder.onrender.com"  # Update after Render gives your URL

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

DB_FILE = "bot_data.db"

# ----------------- DATABASE SETUP -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            invite_link TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_FILE)

# ----------------- MONETAG REWARDED AD HTML -----------------
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watch Ad to Unlock</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="//libtl.com/sdk.js" data-zone="11938713" data-sdk="show_11938713"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #121212;
            color: #ffffff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 90vh;
            margin: 0;
            text-align: center;
            padding: 20px;
        }
        .btn {
            background: #2481cc;
            color: white;
            border: none;
            padding: 15px 32px;
            font-size: 18px;
            font-weight: bold;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4);
            margin-top: 20px;
        }
        .status {
            margin-top: 20px;
            font-size: 14px;
            color: #888888;
        }
    </style>
</head>
<body>
    <h2>Unlock Your Video</h2>
    <p>Watch a short sponsored message to claim your random video reward.</p>
    <button class="btn" id="adBtn" onclick="watchAd()">Play Rewarded Ad</button>
    <div class="status" id="statusText">Ready</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        function watchAd() {
            const btn = document.getElementById('adBtn');
            const status = document.getElementById('statusText');
            btn.disabled = true;
            status.innerText = "Loading ad...";

            if (typeof show_11938713 === 'function') {
                show_11938713('pop').then(() => {
                    status.innerText = "Completed! Sending video...";
                    tg.sendData("ad_completed");
                    tg.close();
                }).catch(e => {
                    btn.disabled = false;
                    status.innerText = "Ad could not load. Tap again.";
                });
            } else {
                status.innerText = "Ad script initializing, please retry...";
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

async def serve_ad_page(request):
    return web.Response(text=HTML_CONTENT, content_type="text/html")

# ----------------- CHANNEL CHECKING -----------------
async def check_membership(bot, user_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_id FROM channels")
    channels = c.fetchall()
    conn.close()

    if not channels:
        return True

    for (ch_id,) in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def get_join_keyboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_id, invite_link FROM channels")
    rows = c.fetchall()
    conn.close()

    buttons = []
    for idx, (_, link) in enumerate(rows, 1):
        buttons.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=link)])
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_join")])
    return InlineKeyboardMarkup(buttons)

# ----------------- BOT HANDLERS -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user.id, user.username))
    conn.commit()
    conn.close()

    is_member = await check_membership(context.bot, user.id)
    if not is_member:
        await update.message.reply_text(
            "uh , ohh it looks like you are not joined all channels join channel below and click verify .",
            reply_markup=get_join_keyboard(),
        )
        return

    keyboard = [
        [InlineKeyboardButton("🎬 Get Video", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    await update.message.reply_text(
        "You have verified successfully! Click below to unlock your video:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    is_member = await check_membership(context.bot, user_id)
    if not is_member:
        await query.message.reply_text(
            "uh , ohh it looks like you are not joined all channels join channel below and click verify .",
            reply_markup=get_join_keyboard(),
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🎬 Get Video", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
        await query.message.reply_text(
            "Verification successful! Click below to unlock your video:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    if data == "ad_completed":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT file_id FROM videos ORDER BY RANDOM() LIMIT 1")
        row = c.fetchone()
        conn.close()

        if row:
            await update.effective_message.reply_video(
                video=row[0],
                caption="Here is your video! Enjoy 🎉"
            )
        else:
            await update.effective_message.reply_text("No videos are currently available in the database.")

# ----------------- ADMIN COMMANDS (/adminTTT) -----------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("➕ Add Video", callback_data="adm_add_video"),
         InlineKeyboardButton("🗑 Clear All Videos", callback_data="adm_clear_videos")],
        [InlineKeyboardButton("🔗 Channel Settings", callback_data="adm_channels")]
    ]
    await update.message.reply_text("🛠 **Admin Control Panel**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer()

    if query.data == "adm_stats":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM videos")
        total_videos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM channels")
        total_channels = c.fetchone()[0]
        conn.close()

        await query.message.reply_text(
            f"📊 **Bot Statistics**\n\n"
            f"• Total Registered Users: `{total_users}`\n"
            f"• Uploaded Videos: `{total_videos}`\n"
            f"• Mandatory Channels: `{total_channels}`",
            parse_mode="Markdown"
        )

    elif query.data == "adm_add_video":
        context.user_data["state"] = "awaiting_video"
        await query.message.reply_text("Send or forward the video you want to add to the bot.")

    elif query.data == "adm_clear_videos":
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM videos")
        conn.commit()
        conn.close()
        await query.message.reply_text("All videos cleared from the library.")

    elif query.data == "adm_broadcast":
        context.user_data["state"] = "awaiting_broadcast"
        await query.message.reply_text("Send the message you want to broadcast to all users.")

    elif query.data == "adm_channels":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT channel_id, invite_link FROM channels")
        rows = c.fetchall()
        conn.close()

        ch_text = "\n".join([f"`{ch[0]}` -> {ch[1]}" for ch in rows]) if rows else "No channels configured."
        await query.message.reply_text(
            f"📢 **Current Channels:**\n{ch_text}\n\n"
            "• Add: `/addchannel <channel_id_or_@username> <invite_link>`\n"
            "• Remove: `/delchannel <channel_id_or_@username>`",
            parse_mode="Markdown"
        )

async def handle_admin_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    state = context.user_data.get("state")
    if not state:
        return

    if state == "awaiting_broadcast":
        context.user_data["state"] = None
        msg = update.message.text
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        recipients = c.fetchall()
        conn.close()

        sent, failed = 0, 0
        for (uid,) in recipients:
            try:
                await context.bot.send_message(chat_id=uid, text=msg)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Broadcast complete.\nDelivered: {sent} | Failed: {failed}")

async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if context.user_data.get("state") == "awaiting_video":
        file_id = update.message.video.file_id
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO videos (file_id) VALUES (?)", (file_id,))
            conn.commit()
            await update.message.reply_text("✅ Video stored successfully!")
        except sqlite3.IntegrityError:
            await update.message.reply_text("This video already exists in the catalog.")
        finally:
            conn.close()
        context.user_data["state"] = None

async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        link = context.args[1]
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO channels (channel_id, invite_link) VALUES (?, ?)", (ch_id, link))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Added channel: `{ch_id}`", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("Usage: `/addchannel <channel_id> <invite_link>`")

async def del_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM channels WHERE channel_id = ?", (ch_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Removed channel: `{ch_id}`", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("Usage: `/delchannel <channel_id>`")

# ----------------- MAIN EXECUTION -----------------
async def run_server():
    server = web.Application()
    server.router.add_get("/", serve_ad_page)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # User Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # Admin Handlers
    app.add_handler(CommandHandler("adminTTT", admin_panel))
    app.add_handler(CommandHandler("addchannel", add_channel_cmd))
    app.add_handler(CommandHandler("delchannel", del_channel_cmd))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^adm_"))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_video_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_admin_inputs))

    # Start ad web server
    loop = app.loop
    loop.create_task(run_server())

    print(f"Bot and WebApp Server running on port {PORT}...")
    app.run_polling()

if __name__ == "__main__":
    main()
              
