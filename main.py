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

BOT_TOKEN = "8894164052:AAHGUTlFdf4lI_4zvH3-2WnOJzjKHLwigak"
ADMIN_IDS = [8573542782]
VERCEL_AD_URL = "https://watch-ad-to-unlock-video.vercel.app/"
FIREBASE_URL = "https://appcreator99-1eb09-default-rtdb.firebaseio.com"
BANNER_IMAGE_URL = "https://i.ibb.co/RTTTK5GV/760137aee5990c82ab3886590d63f744.jpg"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

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
            await update.message.reply_text("Database me abhi koi video nahi hai. Admin se upload karne ko bole!")
        return

    is_member = await check_membership(context.bot, user.id)
    if not is_member:
        await update.message.reply_photo(
            photo=BANNER_IMAGE_URL,
            caption=get_force_join_text(user),
            reply_markup=get_join_keyboard(),
            parse_mode="Markdown"
        )
        return

    keyboard = [[InlineKeyboardButton("🎬 Get Video", callback_data="get_video_btn")]]
    await update.message.reply_text(
        "Verification successful! Click below to access video:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    is_member = await check_membership(context.bot, user.id)
    if not is_member:
        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
        await query.message.reply_photo(
            photo=BANNER_IMAGE_URL,
            caption=get_force_join_text(user),
            reply_markup=get_join_keyboard(),
            parse_mode="Markdown"
        )
    else:
        keyboard = [[InlineKeyboardButton("🎬 Get Video", callback_data="get_video_btn")]]
        await query.message.reply_text(
            "Verification successful! Click below to access video:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

async def get_video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🎬 Watch Ad to Unlock Video", url=VERCEL_AD_URL)]]
    await query.message.reply_text(
        "Click the button below to watch the rewarded ad. Once the ad finishes, you will be redirected back here with your video!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
        await query.message.reply_text("Video bhejo ya forward karo, database me add ho jayegi.")
    elif query.data == "adm_clear_videos":
        fb_delete("videos")
        await query.message.reply_text("Sabhi videos delete ho gayi hain.")
    elif query.data == "adm_broadcast":
        context.user_data["state"] = "awaiting_broadcast"
        await query.message.reply_text("Broadcast message likh kar bhejo:")
    elif query.data == "adm_channels":
        channels = fb_get("channels") or {}
        ch_text = "\n".join([f"`{data['channel_id']}` -> {data['invite_link']}" for _, data in channels.items()]) if channels else "Koi channel added nahi hai."
        await query.message.reply_text(
            f"📢 **Current Force-Join Channels:**\n{ch_text}\n\n"
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
        try:
            requests.post(f"{FIREBASE_URL}/videos.json", json=file_id, timeout=5)
            await update.message.reply_text("✅ Video Firebase me save ho gayi!")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        context.user_data["state"] = None

async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        link = context.args[1]
        safe_key = ch_id.replace("@", "").replace("-", "minus_").replace(".", "_")
        fb_put(f"channels/{safe_key}", {"channel_id": ch_id, "invite_link": link})
        await update.message.reply_text(f"Channel add ho gaya: `{ch_id}`", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("Usage: `/addchannel <channel_id> <invite_link>`")

async def del_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = context.args[0]
        safe_key = ch_id.replace("@", "").replace("-", "minus_").replace(".", "_")
        fb_delete(f"channels/{safe_key}")
        await update.message.reply_text(f"Channel remove ho gaya: `{ch_id}`", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("Usage: `/delchannel <channel_id>`")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(get_video_callback, pattern="^get_video_btn$"))
    app.add_handler(CommandHandler("adminTTT", admin_panel))
    app.add_handler(CommandHandler("addchannel", add_channel_cmd))
    app.add_handler(CommandHandler("delchannel", del_channel_cmd))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^adm_"))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_video_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_admin_inputs))

    print("Hornfinder Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
