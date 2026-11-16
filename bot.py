
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing!")

if not RENDER_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL is missing!")

WEBHOOK_SECRET = secrets.token_urlsafe(32)

telegram_app = Application.builder().token(BOT_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to STRANGE AMERICA AI STUDIO!\n\n"
        "Your documentary studio is online!\n\n"
        "Send /help to see commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 STRANGE AMERICA AI STUDIO\n\n"
        "/start - Start the bot\n"
        "/help - Show commands\n\n"
        "More AI production features are coming soon!"
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Idea received!\nAI production features are coming soon."
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("make", make_command))
    MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        url=f"{RENDER_URL.rstrip('/')}/telegram",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )

    yield

    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def home():
    return {"status": "STRANGE AMERICA AI STUDIO is running!"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not secrets.compare_digest(supplied_secret, WEBHOOK_SECRET):
        return Response(status_code=403)

    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)

    return JSONResponse({"ok": True})
