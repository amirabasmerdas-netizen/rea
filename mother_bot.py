import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKENS_FILE = "reaction_bots_tokens.json"

# تابع برای ذخیره توکن جدید
def save_token(new_token):
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            tokens = json.load(f)
    else:
        tokens = []
    if new_token not in tokens:
        tokens.append(new_token)
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f)
        return True
    return False

# تابع استارت برای مالک
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":  # مالک
        await update.message.reply_text("⛔ شما دسترسی ندارید.")
        return

    await update.message.reply_text(
        "🎛 ربات مادر فعال است.\n\nلطفاً توکن ربات ری‌اکشن‌زن جدید را ارسال کنید:",
        reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
    )
    context.user_data['awaiting_token'] = True

# دریافت توکن از مالک
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        return

    if context.user_data.get('awaiting_token'):
        token = update.message.text.strip()
        # بررسی ساده توکن
        if token.startswith("") and len(token) > 30:
            if save_token(token):
                await update.message.reply_text("✅ توکن ذخیره شد. ربات ری‌اکشن‌زن جدید فعال می‌شود.")
                # فراخوانی API ری‌اکشن‌زن برای اضافه کردن توکن جدید
                await call_reaction_bot_api_to_add_token(token)
            else:
                await update.message.reply_text("⚠️ این توکن قبلاً اضافه شده.")
        else:
            await update.message.reply_text("❌ توکن نامعتبر است. دوباره ارسال کن.")
        context.user_data['awaiting_token'] = False

async def call_reaction_bot_api_to_add_token(token):
    # آدرس ربات ری‌اکشن‌زن که روی Render هاست شده
    REACTION_BOT_API_URL = "https://your-reaction-bot.onrender.com/add_token"
    try:
        import requests
        requests.post(REACTION_BOT_API_URL, json={"token": token})
    except Exception as e:
        print(f"خطا در ارسال توکن به ری‌اکشن‌زن: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_token'] = False
    await update.message.reply_text("عملیات لغو شد.")

# اجرای ربات مادر
if __name__ == "__main__":
    MOTHER_BOT_TOKEN = "توکن_ربات_مادر_اینجا"

    app = ApplicationBuilder().token(MOTHER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات مادر در حال اجراست...")
    app.run_polling()
