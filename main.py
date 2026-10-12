import os
import random
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Vercel Ads Website Link
VERCEL_AD_URL = "https://watch-ad-to-unlock-video.vercel.app/"

# Firebase Realtime Database
FIREBASE_URL = "https://appcreator99-1eb09-default-rtdb.firebaseio.com"

# Force Join Card Banner Photo URL
BANNER_IMAGE_URL = "https://i.ibb.co/RTTTK5GV/760137aee5990c82ab3886590d63f744.jpg"

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
        logging.error(f"Firebase GET error: {e}")
        return None
    return None

def fb_put(endpoint: str, data):
    try:
        requests.put(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PUT error: {e}")

def fb_patch(endpoint: str, data):
    try:
        requests.patch(f"{FIREBASE_URL}/{endpoint}.json", json=data, timeout=5)
    except Exception as e:
        logging.error(f"Firebase PATCH error: {e}")

def fb_delete(endpoint: str):
    try:
        requests.delete(f"{FIREBASE_URL}/{endpoint}.json", timeout=5)
    except Exception as e:
        logging.error(f"Firebase DELETE error: {e}")

# ----------------- CHANNEL CHECKING & LAYOUT -----------------
async def check_membership(bot, user_id: int) -> bool:
    channels = fb_get("channels") or {}
    if not channels:
        return True

    for _, data in channels.items():
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
    row = []

    for _, data in channels.items():
        link = data.get("invite_link", "")
        row.append(InlineKeyboardButton("JOIN ↗️", url=link))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("Verify ✅", callback_data="verify_join")])
    return InlineKeyboardMarkup(buttons)

def get_force_join_text(user):
    name = (user.first_name or "USER").upper()
    return (
        "⚠️ **You Must Join Our All Channels**\n\n"
        f"👋 **HEY {name},**\n\n"
        "LOW MEMBER PE SPECIAL REWARD MIL RAHA HAI BIG OPPORTUNITY 💵💎\n\n"
        "Please join all channels given below to unlock the videos!\n\n"
        "**DM:** https://t.me/Hornfinder_bot"
    )

# ----------------- USER HANDLERS -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    fb_patch(f"users/{user.id}", {"user_id": user.id, "username": user.username or ""})

    if context.args and context.args[0] == "unlock":
        videos = fb_get("videos") or {}
        if videos:
            file_ids = list(videos.values())
            chosen_video = random.choice(file_ids)
            await update.message.reply_video(
                video=chosen_video,
                caption="Ad verified successfully! Enjoy your video 🎉"
            )
        else:
            await update.message.
