
import os
import secrets
from contextlib import asynccontextmanager
import httpx
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
        "🎬 Welcome to STRANGE AMERICA AI STUDIO!\n"
        "Use /make followed by your documentary topic.\n"
        "Example: /make Bodie Ghost Town"
    )

async def make_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🎬 Tell me your documentary topic!\n"
            "Example: /make Bodie Ghost Town"
        )
        return

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        await update.message.reply_text(
            "❌ Gemini API key is missing in Render."
        )
        return

    topic = " ".join(context.args)

    await update.message.reply_text(
        f"🎬 Creating your documentary about: {topic}\n"
        "🧠 Gemini AI is writing your script. Please wait..."
    )

    prompt = f"""
You are the lead documentary scriptwriter for STRANGE AMERICA.

Create an engaging, original English-language YouTube documentary
about: {topic}

Requirements:
- Write a compelling opening hook.
- Create a detailed narration with clear sections.
- Use an atmospheric, cinematic American documentary tone.
- Include scene suggestions in [VISUAL] labels.
- Include narration in [VOICEOVER] labels.
- Keep historical claims accurate.
- Never invent dates, quotations, people or events.
- If a fact needs verification, mark it [VERIFY FACT].
- End with a memorable conclusion.

Target length: approximately 1000-1200 words.
This is an original script, not copied from another creator.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={
                    "contents": [
                        {"parts": [{"text": prompt}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 5000
                    }
                }
            )

            response.raise_for_status()
            data = response.json()

        parts = data["candidates"][0]["content"]["parts"]
        script = "\n".join(
            part.get("text", "") for part in parts
        ).strip()

        if not script:
            raise ValueError("Gemini returned an empty response.")

        await update.message.reply_text(
            "✅ YOUR DOCUMENTARY SCRIPT IS READY!"
        )

        for i in range(0, len(script), 3500):
            await update.message.reply_text(script[i:i + 3500])

    except httpx.HTTPStatusError as error:
        print("Gemini API error:", error.response.text)
        await update.message.reply_text(
            f"❌ Gemini API error: HTTP {error.response.status_code}. "
            "Check your API key, model access and free-tier limits."
        )

    except Exception as error:
        print("Documentary generation error:", repr(error))
        await update.message.reply_text(
            "❌ Script generation failed. Check Render Logs."
        )




telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("make", make_command))

telegram_app.add_handler(
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
