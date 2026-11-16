
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to STRANGE AMERICA AI STUDIO!\n\n"
        "Your documentary studio is ready.\n\n"
        "Send /help to see commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 STRANGE AMERICA AI STUDIO\n\n"
        "/start - Start the bot\n"
        "/help - Show commands\n\n"
        "AI production features are coming soon!"
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Your idea received! 🚀 AI production features are coming soon."
    )

def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN is missing!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    print("STRANGE AMERICA AI STUDIO is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
