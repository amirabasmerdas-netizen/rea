import os
import json
import asyncio
import threading
import time
import requests
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ====== بخش Flask برای Webhook و مدیریت توکن ======
app_flask = Flask(__name__)

TOKENS_FILE = "tokens.json"
bots = {}  # دیکشنری برای ذخیره Application هر ربات

# ====== توابع مدیریت توکن ======
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f)

def add_token_to_list(new_token):
    tokens = load_tokens()
    if new_token not in tokens:
        tokens.append(new_token)
        save_tokens(tokens)
        return True
    return False

# ====== کد ربات ری‌اکشن‌زن ======
async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_token = context.bot.token
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    data = {
        "chat_id": update.effective_chat.id,
        "message_id": update.effective_message.message_id,
        "reaction": [{"type": "emoji", "emoji": "🔥"}]
    }
    try:
        response = requests.post(url, json=data, timeout=3)
        if response.status_code == 200:
            print(f"✅ ری‌اکشن فرستاده شد برای ربات {bot_token[:10]}...")
        else:
            print(f"❌ خطا در ری‌اکشن: {response.text}")
    except Exception as e:
        print(f"❌ استثنا: {e}")

def start_reaction_bot(token):
    """استارت یک ربات ری‌اکشن‌زن جدید"""
    if token in bots:
        print(f"ربات با توکن {token[:10]}... قبلاً فعال است")
        return
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, auto_react))
    
    # اجرا در ترد جداگانه
    def run_bot():
        asyncio.set_event_loop(asyncio.new_event_loop())
        print(f"🚀 ربات ری‌اکشن‌زن {token[:10]}... راه‌اندازی شد")
        app.run_polling()
    
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    bots[token] = {"app": app, "thread": thread}

# ====== کد ربات مادر ======
MOTHER_BOT_TOKEN = "توکن_ربات_مادر_اینجا"  # این رو از environment variable بخون

async def mother_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        await update.message.reply_text("⛔ شما دسترسی ندارید.")
        return
    
    await update.message.reply_text(
        "🤖 ربات مادر فعال است.\n\n"
        "لطفاً توکن ربات ری‌اکشن‌زن جدید را ارسال کنید:\n"
        "(مثال: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)"
    )
    context.user_data['awaiting_token'] = True

async def mother_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        return
    
    if context.user_data.get('awaiting_token'):
        token = update.message.text.strip()
        
        # اعتبارسنجی ساده توکن
        if len(token) > 30 and ':' in token:
            if add_token_to_list(token):
                # استارت ربات جدید
                start_reaction_bot(token)
                await update.message.reply_text(
                    f"✅ توکن با موفقیت اضافه شد!\n"
                    f"ربات ری‌اکشن‌زن جدید فعال شد.\n"
                    f"توکن: `{token[:15]}...`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("⚠️ این توکن قبلاً اضافه شده است.")
        else:
            await update.message.reply_text("❌ توکن نامعتبر است. دوباره ارسال کنید.")
        
        context.user_data['awaiting_token'] = False

async def mother_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_token'] = False
    await update.message.reply_text("❌ عملیات لغو شد.")

async def mother_list_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        await update.message.reply_text("⛔ شما دسترسی ندارید.")
        return
    
    tokens = load_tokens()
    if not tokens:
        await update.message.reply_text("📭 هیچ ربات ری‌اکشن‌زنی ثبت نشده است.")
        return
    
    active_count = len(bots)
    message = f"📊 لیست ربات‌های ری‌اکشن‌زن:\n"
    message += f"مجموع: {len(tokens)} عدد\n"
    message += f"فعال: {active_count} عدد\n\n"
    
    for i, token in enumerate(tokens[-10:], 1):  # فقط 10 تای آخر
        status = "✅" if token in bots else "⏸"
        message += f"{status} {i}. `{token[:15]}...`\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def start_mother_bot():
    """استارت ربات مادر"""
    app = ApplicationBuilder().token(MOTHER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", mother_start))
    app.add_handler(CommandHandler("cancel", mother_cancel))
    app.add_handler(CommandHandler("list", mother_list_tokens))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mother_handle_message))
    
    def run_mother():
        asyncio.set_event_loop(asyncio.new_event_loop())
        print("🤖 ربات مادر در حال اجراست...")
        app.run_polling()
    
    thread = threading.Thread(target=run_mother, daemon=True)
    thread.start()
    return thread

# ====== API برای مدیریت از طریق ربات مادر (اختیاری) ======
@app_flask.route('/add_token', methods=['POST'])
def api_add_token():
    """API برای اضافه کردن توکن جدید (همون کاری که ربات مادر می‌کنه)"""
    data = request.json
    new_token = data.get('token')
    if not new_token:
        return jsonify({"error": "no token provided"}), 400
    
    if add_token_to_list(new_token):
        start_reaction_bot(new_token)
        return jsonify({"status": "ok", "message": "token added"}), 200
    else:
        return jsonify({"status": "duplicate", "message": "token already exists"}), 200

@app_flask.route('/tokens', methods=['GET'])
def api_list_tokens():
    """لیست تمام توکن‌ها"""
    tokens = load_tokens()
    return jsonify({
        "total": len(tokens),
        "active": len(bots),
        "tokens": tokens
    })

@app_flask.route('/')
def index():
    return "🤖 Reaction Bot Manager is running!"

@app_flask.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "total_bots": len(bots),
        "registered_tokens": len(load_tokens())
    })

# ====== پینگ به خود برای جلوگیری از خوابیدن Render ======
def ping_self():
    """هر 10 دقیقه به خودش پینگ می‌زنه تا Render خاموشش نکنه"""
    port = os.environ.get('PORT', 5000)
    url = f"http://localhost:{port}/health"
    while True:
        try:
            response = requests.get(url, timeout=5)
            print(f"💓 Self-ping: {response.status_code}")
        except Exception as e:
            print(f"❌ Self-ping failed: {e}")
        time.sleep(600)  # 10 دقیقه

# ====== اجرای اصلی ======
if __name__ == "__main__":
    # دریافت توکن ربات مادر از environment variable
    MOTHER_BOT_TOKEN = os.environ.get('MOTHER_BOT_TOKEN', '')
    if not MOTHER_BOT_TOKEN:
        print("⚠️ هشدار: توکن ربات مادر تنظیم نشده است!")
        print("لطفاً متغیر محیطی MOTHER_BOT_TOKEN را در Render تنظیم کنید.")
    else:
        # استارت ربات مادر
        start_mother_bot()
        print("✅ ربات مادر راه‌اندازی شد")
    
    # استارت تمام ربات‌های ری‌اکشن‌زن قبلی
    tokens = load_tokens()
    print(f"📋 تعداد توکن‌های ذخیره شده: {len(tokens)}")
    for token in tokens:
        start_reaction_bot(token)
    
    # شروع پینگ به خود
    threading.Thread(target=ping_self, daemon=True).start()
    
    # اجرای Flask برای Webhook و API
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Flask server running on port {port}")
    app_flask.run(host='0.0.0.0', port=port)
