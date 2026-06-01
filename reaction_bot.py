import sys
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """واکنش خودکار به هر پیام با ایموجی 🔥"""
    try:
        # استفاده از متد جدید کتابخانه برای ارسال واکنش
        await update.effective_message.react(emoji="🔥")
        print(f"واکنش به پیام {update.effective_message.message_id} در چت {update.effective_chat.id}")
    except Exception as e:
        print(f"خطا در ارسال واکنش: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python reaction_bot.py <BOT_TOKEN>")
        sys.exit(1)

    TOKEN = sys.argv[1]
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, auto_react))

    print(f"ربات ری اکشن زن با توکن {TOKEN} شروع به کار کرد (Polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
