import os
import random
import logging
import asyncio
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
WEBAPP_URL = "https://placeholder.onrender.com"  # Replace with your actual Render URL when ready

# Firebase Configuration
FIREBASE_URL = "https://appcreator99-1eb09-default-rtdb.firebaseio.com"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ----------------- FIREBASE HELPERS -----------------
def fb_get(endpoint: str):
    try:
        res = requests.get(f"{FIREBASE_URL}/{endpoint}.json", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logging.error(f"Firebase GET error ({endpoint}): {e}")
    return None

def fb_put(endpoint: str, data):
    try:
        requests.put(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PUT error ({endpoint}): {e}")

def fb_patch(endpoint: str, data):
    try:
        requests.patch(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PATCH error ({endpoint}): {e}")

def fb_delete(endpoint: str):
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

# ----------------- CHANNEL CHECKING -----------------
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
            reply_markup=InlineKeyboardMarkup(
