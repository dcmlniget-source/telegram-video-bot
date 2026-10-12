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
BANNER_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800"

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
            member = await bot.get_chat_member(chat_id=
