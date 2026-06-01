import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8564154154:AAGWvLfqMkLX2Bnh3mCDuLNkfuGKZJEws08"

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": "🔥"}]
    }

    try:
        requests.post(url, json=data)
        print("reaction sent")
    except Exception as e:
        print(e)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, auto_react))

print("Bot started...")
app.run_polling()
