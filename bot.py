
import os
import secrets
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ---------------- CONFIGURATION ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RENDER_URL = (
    os.getenv("RENDER_EXTERNAL_URL")
    or os.getenv("RENDER_URL")
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or secrets.token_urlsafe(32)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in Render environment.")

if not RENDER_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL is missing.")


# ---------------- TELEGRAM COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to STRANGE AMERICA AI STUDIO!\n\n"
        "Your AI documentary studio is ready.\n\n"
        "Use:\n"
        "/make Bodie Ghost Town\n\n"
        "To create a documentary script."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 STRANGE AMERICA AI STUDIO HELP\n\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/make Topic - Generate a documentary script\n\n"
        "Example:\n"
        "/make Bodie Ghost Town"
    )


# ---------------- GEMINI DOCUMENTARY ENGINE ----------------

async def make_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    logger.info("MAKE COMMAND STARTED")

    if not context.args:
        await update.message.reply_text(
            "🎬 Tell me your documentary topic!\n"
            "Example: /make Bodie Ghost Town"
        )
        return

    if not GEMINI_API_KEY:
        await update.message.reply_text(
            "❌ Gemini API key is missing in Render."
        )
        return

    topic = " ".join(context.args)

    await update.message.reply_text(
        f"🎬 Creating your documentary about: {topic}\n\n"
        "🧠 Gemini AI is writing your script. Please wait..."
    )

    prompt = f"""
You are the lead documentary writer for STRANGE AMERICA.

Create an original, engaging English-language YouTube documentary
about: {topic}

Requirements:

1. Write a powerful opening hook.
2. Create a detailed documentary narration.
3. Divide the story into clear sections.
4. Use cinematic American documentary storytelling.
5. Include [VISUAL] scene suggestions.
6. Include [VOICEOVER] narration.
7. Include [MUSIC] and [SFX] suggestions.
8. Keep historical claims accurate.
9. Never invent dates, quotations, people or events.
10. Mark uncertain information as [VERIFY FACT].
11. End with a memorable conclusion.

Target length: approximately 1000-1200 words.

Make the script original and copyright-safe.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=120) as client:

            response = await client.post(
                url,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 5000
                    }
                }
            )

            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            raise ValueError(
                "Gemini returned no candidates."
            )

        parts = candidates[0]["content"]["parts"]

        script = "\n".join(
            part.get("text", "")
            for part in parts
        ).strip()

        if not script:
            raise ValueError("Gemini returned an empty script.")

        await update.message.reply_text(
            "✅ YOUR DOCUMENTARY SCRIPT IS READY!\n\n"
            f"📌 Topic: {topic}"
        )

        for i in range(0, len(script), 3500):
            await update.message.reply_text(
                script[i:i + 3500]
            )

        logger.info("DOCUMENTARY SCRIPT GENERATED SUCCESSFULLY")

    except httpx.HTTPStatusError as error:

        logger.error(
            "Gemini HTTP error: %s",
            error.response.text
        )

        await update.message.reply_text(
            f"❌ Gemini API error: HTTP {error.response.status_code}.\n"
            "Check your API key, model access and free-tier quota."
        )

    except Exception as error:

        logger.exception("DOCUMENTARY GENERATION FAILED")

        await update.message.reply_text(
            "❌ Script generation failed.\n"
            "Please check Render Logs."
        )


# ---------------- NORMAL TEXT MESSAGES ----------------

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    logger.info("NORMAL MESSAGE RECEIVED: %s", text)

    await update.message.reply_text(
        "🚀 Idea received!\n"
        "AI production features are coming soon."
    )


# ---------------- TELEGRAM APPLICATION ----------------

telegram_app = Application.builder().token(BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("make", make_command))

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    )
)


# ---------------- FASTAPI WEBHOOK ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting STRANGE AMERICA AI STUDIO")

    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        url=f"{RENDER_URL.rstrip('/')}/telegram",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )

    logger.info("TELEGRAM WEBHOOK CONNECTED SUCCESSFULLY")

    yield

    await telegram_app.stop()
    await telegram_app.shutdown()

    logger.info("BOT STOPPED")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def home():

    return {
        "status": "STRANGE AMERICA AI STUDIO is running!"
    }


@app.post("/telegram")
async def telegram_webhook(request: Request):

    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token",
        ""
    )

    if not secrets.compare_digest(
        supplied_secret,
        WEBHOOK_SECRET
    ):
        return Response(status_code=403)

    try:
        data = await request.json()

        logger.info(
            "INCOMING TELEGRAM UPDATE: %s",
            data.get("update_id")
        )

        update = Update.de_json(
            data,
            telegram_app.bot
        )

        await telegram_app.process_update(update)

        return JSONResponse({"ok": True})

    except Exception:

        logger.exception("TELEGRAM WEBHOOK FAILED")

        return JSONResponse(
            {"ok": False},
            status_code=500
        )
