import os
import random
import json
import logging
import requests
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
ADMIN_IDS = [8573542782]
PORT = int(os.environ.get("PORT", 8080))
WEBAPP_URL = "https://placeholder.onrender.com"  # Replace with your actual Render URL

# Firebase Configuration
FIREBASE_URL = "https://appcreator99-1eb09-default-rtdb.firebaseio.com"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ----------------- FIREBASE HELPERS -----------------
def fb_get(endpoint: str):
    """Fetch data from Firebase Realtime Database."""
    try:
        res = requests.get(f"{FIREBASE_URL}/{endpoint}.json", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logging.error(f"Firebase GET error ({endpoint}): {e}")
    return None

def fb_put(endpoint: str, data):
    """Write/replace data in Firebase."""
    try:
        requests.put(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PUT error ({endpoint}): {e}")

def fb_patch(endpoint: str, data):
    """Update specific keys in Firebase."""
    try:
        requests.patch(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PATCH error ({endpoint}): {e}")

def fb_delete(endpoint: str):
    """Delete node from Firebase."""
    try:
        requests.delete(f"{FIREBASE_URL}/{endpoint}.json", timeout=5)
    except Exception as e:
        logging.error(f"Firebase DELETE error ({endpoint}): {e}")

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

# ----------------- CHANNEL MEMBERSHIP CHECK -----------------
async def check_membership(bot, user_id: int) -> bool:
    channels = fb_get("channels") or {}
    if not channels:
        return True

    for ch_raw, data in channels.items():
        ch_id = data.get("channel_id")
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def get_join_keyboard():
    channels = fb_get("channels") or {}
    buttons = []
    idx = 1
    for _, data in channels.items():
        link = data.get("invite_link", "")
        buttons.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=link)])
        idx += 1
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_join")])
    return InlineKeyboardMarkup(buttons)

# ----------------- USER HANDLERS -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    fb_patch(f"users/{user.id}", {"user_id": user.id, "username": user.username or ""})

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
        videos = fb_get("videos") or {}
        if videos:
            file_ids = list(videos.values())
            chosen_video = random.choice(file_ids)
            await update.effective_message.reply_video(
                video=chosen_video,
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
        users = fb_get("users") or {}
        videos = fb_get("videos") or {}
        channels = fb_get("channels") or {}

        await query.message.reply_text(
            f"📊 **Bot Statistics (Firebase)**\n\n"
            f"• Total Registered Users: `{len(users)}`\n"
            f"• Uploaded Videos: `{len(videos)}`\n"
            f"• Mandatory Channels: `{len(channels)}`",
            parse_mode="Markdown"
        )

    elif query.data == "adm_add_video":
        context.user_data["state"] = "awaiting_video"
        await query.message.reply_text("Send or forward the video you want to add to the bot.")

    elif query.data == "adm_clear_videos":
        fb_delete("videos")
        await query.message.reply_text("All videos cleared from Firebase.")

    elif query.data == "adm_broadcast":
        context.user_data["state"] = "awaiting_broadcast"
        await query.message.reply_text("Send the message you want to broadcast to all users.")

    elif query.data == "adm_channels":
        channels = fb_get("channels") or {}
        ch_text = "\n".join([f"`{data['channel_id']}` -> {data['invite_link']}" for _, data in channels.items()]) if channels else "No channels configured."
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
        users = fb_get("users") or {}

        sent, failed = 0, 0
        for uid_str in users.keys():
            try:
                await context.bot.send_message(chat_id=int(uid_str), text=msg)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Broadcast complete.\nDelivered: {sent} | Failed: {failed}")

async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if context.user_data.get("state") == "awaiting_video":
        file_id = update.message.video.file_id
        # Push to Firebase videos list
        try:
            requests.post(f"{FIREBASE_URL}/videos.json", json=file_id, timeout=5)
            await update.message.reply_text("✅ Video stored successfully in Firebase!")
        except Exception as e:
            await update.message.reply_text(f"Error saving video: {e}")
        context.user_data["state"] = None

async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        link = context.args[1]
        safe_key = ch_id.replace("@", "").replace("-", "minus_").replace(".", "_")
        fb_put(f"channels/{safe_key}", {"channel_id": ch_id, "invite_link": link})
        await update.message.reply_text(f"Added channel: `{ch_id}`", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("Usage: `/addchannel <channel_id> <invite_link>`")

async def del_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        safe_key = ch_id.replace("@", "").replace("-", "minus_").replace(".", "_")
        fb_delete(f"channels/{safe_key}")
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

    # Web Server for WebApp
    loop = app.loop
    loop.create_task(run_server())

    print(f"Bot and WebApp Server running on port {PORT} with Firebase Database...")
    app.run_polling()

if __name__ == "__main__":
    main()
