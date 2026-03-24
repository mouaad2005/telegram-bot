import yt_dlp
import os
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 🔥 logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN is missing")

user_state = {}

# 🔥 تنظيف الرابط (حل TikTok + اختصارات)
def clean_url(url):
    try:
        url = url.split("?")[0]
        r = requests.get(url, allow_redirects=True, timeout=5)
        return r.url
    except:
        return url

# 🔥 تحميل
def download(url, audio=False):
    url = clean_url(url)

    ydl_opts = {
        'format': 'best',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        }
    }

    if audio:
        ydl_opts['format'] = 'bestaudio'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if 'entries' in info:
            info = info['entries'][0]

        return ydl.prepare_filename(info)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎵 TikTok", callback_data="tiktok")],
        [InlineKeyboardButton("📸 Instagram", callback_data="instagram")],
        [InlineKeyboardButton("📘 Facebook", callback_data="facebook")],
        [InlineKeyboardButton("▶️ YouTube", callback_data="youtube")]
    ]

    await update.message.reply_text(
        "👋 Welcome!\nChoose a platform:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# اختيار منصة
async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = query.data
    await query.message.reply_text("📎 Send the link")

# استقبال الرابط
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    if user_id not in user_state:
        await update.message.reply_text("❌ Press /start first")
        return

    platform = user_state[user_id]

    # YouTube → خيار
    if platform == "youtube":
        user_state[user_id] = {"platform": "youtube", "url": url}

        keyboard = [
            [InlineKeyboardButton("🎥 Video", callback_data="yt_video")],
            [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="yt_audio")]
        ]

        await update.message.reply_text(
            "Choose format:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text("⚡ Downloading...")

    try:
        file_path = await asyncio.to_thread(download, url, False)
        file_size = os.path.getsize(file_path)

        with open(file_path, 'rb') as f:
            if file_size > 49 * 1024 * 1024:
                await update.message.reply_document(f)
            else:
                await update.message.reply_video(f)

        os.remove(file_path)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ Failed to download")

# أزرار يوتيوب
async def youtube_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in user_state or isinstance(user_state[user_id], str):
        await query.message.reply_text("❌ Send link first")
        return

    data = user_state[user_id]
    url = data["url"]

    await query.message.reply_text("⚡ Downloading...")

    try:
        if query.data == "yt_audio":
            file_path = await asyncio.to_thread(download, url, True)

            with open(file_path, 'rb') as f:
                await query.message.reply_audio(f)
        else:
            file_path = await asyncio.to_thread(download, url, False)
            file_size = os.path.getsize(file_path)

            with open(file_path, 'rb') as f:
                if file_size > 49 * 1024 * 1024:
                    await query.message.reply_document(f)
                else:
                    await query.message.reply_video(f)

        os.remove(file_path)

    except Exception as e:
        print("ERROR:", e)
        await query.message.reply_text("❌ Failed to download")

# تشغيل
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(platform_choice, pattern="^(tiktok|instagram|facebook|youtube)$"))
app.add_handler(CallbackQueryHandler(youtube_buttons, pattern="^yt_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")

try:
    app.run_polling()
except Exception as e:
    print("CRASH ERROR:", e)
