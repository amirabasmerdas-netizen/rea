import os
import json
import asyncio
import threading
import time
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ====== بخش Flask برای Webhook و مدیریت توکن ======
app_flask = Flask(__name__)

TOKENS_FILE = "tokens.json"
REACTIONS_FILE = "reactions.json"  # فایل برای ذخیره واکنش هر ربات
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

def load_reactions():
    if os.path.exists(REACTIONS_FILE):
        with open(REACTIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_reactions(reactions):
    with open(REACTIONS_FILE, "w") as f:
        json.dump(reactions, f)

def get_reaction_for_bot(token):
    """دریافت واکنش اختصاصی هر ربات"""
    reactions = load_reactions()
    return reactions.get(token, "🔥")  # پیش‌فرض 🔥

def set_reaction_for_bot(token, reaction):
    """تنظیم واکنش برای ربات خاص"""
    reactions = load_reactions()
    reactions[token] = reaction
    save_reactions(reactions)

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
    reaction = get_reaction_for_bot(bot_token)  # دریافت واکنش اختصاصی
    
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    data = {
        "chat_id": update.effective_chat.id,
        "message_id": update.effective_message.message_id,
        "reaction": [{"type": "emoji", "emoji": reaction}]
    }
    try:
        response = requests.post(url, json=data, timeout=3)
        if response.status_code == 200:
            print(f"✅ ری‌اکشن {reaction} فرستاده شد برای ربات {bot_token[:10]}...")
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
        reaction = get_reaction_for_bot(token)
        print(f"🚀 ربات ری‌اکشن‌زن {token[:10]}... راه‌اندازی شد (واکنش: {reaction})")
        app.run_polling()
    
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    bots[token] = {"app": app, "thread": thread}

# ====== کد ربات مادر ======
MOTHER_BOT_TOKEN = os.environ.get('MOTHER_BOT_TOKEN', '')

# کیبوردهای شیشه‌ای برای انتخاب واکنش
def get_reaction_keyboard(bot_token):
    """ساخت کیبورد برای انتخاب واکنش"""
    current_reaction = get_reaction_for_bot(bot_token)
    keyboard = [
        [
            InlineKeyboardButton(f"{'✅' if current_reaction == '🔥' else '⬜'} 🔥", callback_data=f"react_{bot_token}_🔥"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '👍' else '⬜'} 👍", callback_data=f"react_{bot_token}_👍"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '❤️' else '⬜'} ❤️", callback_data=f"react_{bot_token}_❤️")
        ],
        [
            InlineKeyboardButton(f"{'✅' if current_reaction == '😂' else '⬜'} 😂", callback_data=f"react_{bot_token}_😂"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '😮' else '⬜'} 😮", callback_data=f"react_{bot_token}_😮"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '😢' else '⬜'} 😢", callback_data=f"react_{bot_token}_😢")
        ],
        [
            InlineKeyboardButton(f"{'✅' if current_reaction == '🎉' else '⬜'} 🎉", callback_data=f"react_{bot_token}_🎉"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '💯' else '⬜'} 💯", callback_data=f"react_{bot_token}_💯"),
            InlineKeyboardButton("✏️ سفارشی", callback_data=f"custom_{bot_token}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data=f"menu_{bot_token}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_bots_keyboard():
    """ساخت کیبورد برای انتخاب ربات"""
    tokens = load_tokens()
    keyboard = []
    for i, token in enumerate(tokens):
        reaction = get_reaction_for_bot(token)
        short_token = token[:15] + "..."
        keyboard.append([InlineKeyboardButton(
            f"{reaction} ربات {i+1}: {short_token}", 
            callback_data=f"select_{token}"
        )])
    keyboard.append([InlineKeyboardButton("➕ اضافه کردن ربات جدید", callback_data="add_new")])
    keyboard.append([InlineKeyboardButton("❌ بستن", callback_data="close")])
    return InlineKeyboardMarkup(keyboard)

async def mother_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        await update.message.reply_text("⛔ شما دسترسی ندارید.")
        return
    
    keyboard = get_bots_keyboard()
    await update.message.reply_text(
        "🤖 **ربات مادر مدیریت ری‌اکشن‌زن**\n\n"
        "📊 آمار:\n"
        f"• تعداد کل ربات‌ها: {len(load_tokens())}\n"
        f"• ربات‌های فعال: {len(bots)}\n\n"
        "🔧 از منوی زیر انتخاب کنید:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def mother_handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if str(user_id) != "8852010090":
        await query.edit_message_text("⛔ شما دسترسی ندارید.")
        return
    
    data = query.data
    
    # مدیریت انتخاب واکنش
    if data.startswith("react_"):
        parts = data.split("_")
        bot_token = parts[1] + "_" + parts[2]  # ریاستور توکن (چون توکن شامل : است)
        reaction = parts[3]
        
        # تنظیم واکنش جدید
        set_reaction_for_bot(bot_token, reaction)
        
        # به روز رسانی کیبورد
        keyboard = get_reaction_keyboard(bot_token)
        short_token = bot_token[:15] + "..."
        await query.edit_message_text(
            f"✅ واکنش ربات `{short_token}` به {reaction} تغییر کرد.\n\n"
            f"واکنش فعلی: {reaction}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # مدیریت واکنش سفارشی
    elif data.startswith("custom_"):
        bot_token = data[7:]
        context.user_data['custom_reaction_token'] = bot_token
        await query.edit_message_text(
            "✏️ لطفاً واکنش مورد نظر را به صورت ایموجی ارسال کنید.\n"
            "مثال: 🚀 یا 💎 یا هر ایموجی دیگری\n\n"
            "برای لغو /cancel را بزنید."
        )
    
    # منوی اصلی ربات
    elif data.startswith("menu_"):
        bot_token = data[5:]
        keyboard = get_reaction_keyboard(bot_token)
        short_token = bot_token[:15] + "..."
        current_reaction = get_reaction_for_bot(bot_token)
        await query.edit_message_text(
            f"🎛 **مدیریت ربات**\n"
            f"توکن: `{short_token}`\n"
            f"واکنش فعلی: {current_reaction}\n\n"
            f"واکنش جدید را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # انتخاب ربات برای مدیریت
    elif data.startswith("select_"):
        bot_token = data[7:]
        keyboard = get_reaction_keyboard(bot_token)
        short_token = bot_token[:15] + "..."
        current_reaction = get_reaction_for_bot(bot_token)
        await query.edit_message_text(
            f"🎛 **مدیریت ربات**\n"
            f"توکن: `{short_token}`\n"
            f"واکنش فعلی: {current_reaction}\n\n"
            f"واکنش جدید را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # اضافه کردن ربات جدید
    elif data == "add_new":
        context.user_data['awaiting_token'] = True
        await query.edit_message_text(
            "➕ **اضافه کردن ربات جدید**\n\n"
            "لطفاً توکن ربات جدید را ارسال کنید:\n"
            "مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
            "برای لغو /cancel را بزنید.",
            parse_mode='Markdown'
        )
    
    elif data == "close":
        await query.delete_message()

async def mother_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        return
    
    # مدیریت واکنش سفارشی
    if context.user_data.get('custom_reaction_token'):
        token = context.user_data['custom_reaction_token']
        reaction = update.message.text.strip()
        
        # بررسی اینکه آیا ایموجی است (ساده)
        if len(reaction) <= 2 and reaction not in ["/cancel", "لغو"]:
            set_reaction_for_bot(token, reaction)
            del context.user_data['custom_reaction_token']
            
            keyboard = get_reaction_keyboard(token)
            short_token = token[:15] + "..."
            await update.message.reply_text(
                f"✅ واکنش سفارشی {reaction} برای ربات `{short_token}` تنظیم شد.",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ لطفاً یک ایموجی معتبر ارسال کنید.")
        return
    
    # مدیریت اضافه کردن توکن جدید
    if context.user_data.get('awaiting_token'):
        token = update.message.text.strip()
        
        if token.lower() == "/cancel":
            context.user_data['awaiting_token'] = False
            await update.message.reply_text("❌ عملیات اضافه کردن لغو شد.")
            return
        
        # اعتبارسنجی ساده توکن
        if len(token) > 30 and ':' in token:
            if add_token_to_list(token):
                start_reaction_bot(token)
                await update.message.reply_text(
                    f"✅ **ربات جدید با موفقیت اضافه شد!**\n\n"
                    f"توکن: `{token[:20]}...`\n"
                    f"واکنش پیش‌فرض: 🔥\n\n"
                    f"از منوی اصلی می‌توانید واکنش آن را تغییر دهید.",
                    parse_mode='Markdown'
                )
                # نمایش دوباره منوی اصلی
                keyboard = get_bots_keyboard()
                await update.message.reply_text(
                    "🔧 منوی مدیریت:",
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text("⚠️ این توکن قبلاً اضافه شده است.")
        else:
            await update.message.reply_text("❌ توکن نامعتبر است. دوباره ارسال کنید.")
        
        context.user_data['awaiting_token'] = False
        return

async def mother_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        return
    
    context.user_data['awaiting_token'] = False
    context.user_data['custom_reaction_token'] = False
    await update.message.reply_text("❌ عملیات لغو شد.")
    
    # نمایش منوی اصلی
    keyboard = get_bots_keyboard()
    await update.message.reply_text("🔧 منوی مدیریت:", reply_markup=keyboard)

def start_mother_bot():
    """استارت ربات مادر"""
    if not MOTHER_BOT_TOKEN:
        print("⚠️ توکن ربات مادر تنظیم نشده است!")
        return None
    
    app = ApplicationBuilder().token(MOTHER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", mother_start))
    app.add_handler(CommandHandler("cancel", mother_cancel))
    app.add_handler(CallbackQueryHandler(mother_handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mother_handle_message))
    
    def run_mother():
        asyncio.set_event_loop(asyncio.new_event_loop())
        print("🤖 ربات مادر در حال اجراست...")
        app.run_polling()
    
    thread = threading.Thread(target=run_mother, daemon=True)
    thread.start()
    return thread

# ====== API برای مدیریت از طریق HTTP ======
@app_flask.route('/add_token', methods=['POST'])
def api_add_token():
    data = request.json
    new_token = data.get('token')
    reaction = data.get('reaction', '🔥')
    
    if not new_token:
        return jsonify({"error": "no token provided"}), 400
    
    if add_token_to_list(new_token):
        set_reaction_for_bot(new_token, reaction)
        start_reaction_bot(new_token)
        return jsonify({"status": "ok", "message": "token added"}), 200
    else:
        return jsonify({"status": "duplicate", "message": "token already exists"}), 200

@app_flask.route('/change_reaction', methods=['POST'])
def api_change_reaction():
    data = request.json
    token = data.get('token')
    new_reaction = data.get('reaction')
    
    if not token or not new_reaction:
        return jsonify({"error": "token and reaction required"}), 400
    
    set_reaction_for_bot(token, new_reaction)
    return jsonify({
        "status": "ok",
        "token": token[:15] + "...",
        "new_reaction": new_reaction
    }), 200

@app_flask.route('/list_bots', methods=['GET'])
def api_list_bots():
    tokens = load_tokens()
    bots_info = []
    for token in tokens:
        bots_info.append({
            "token": token[:15] + "...",
            "reaction": get_reaction_for_bot(token),
            "active": token in bots
        })
    return jsonify({
        "total": len(tokens),
        "active": len(bots),
        "bots": bots_info
    })

@app_flask.route('/')
def index():
    return "🤖 Reaction Bot Manager with customizable reactions!"

@app_flask.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "total_bots": len(bots),
        "registered_tokens": len(load_tokens()),
        "bots_reactions": load_reactions()
    })

# ====== پینگ به خود برای جلوگیری از خوابیدن Render ======
def ping_self():
    port = os.environ.get('PORT', 5000)
    url = f"http://localhost:{port}/health"
    while True:
        try:
            response = requests.get(url, timeout=5)
            print(f"💓 Self-ping: {response.status_code}")
        except Exception as e:
            print(f"❌ Self-ping failed: {e}")
        time.sleep(600)

# ====== اجرای اصلی ======
if __name__ == "__main__":
    # استارت ربات مادر
    start_mother_bot()
    
    # استارت تمام ربات‌های ری‌اکشن‌زن قبلی
    tokens = load_tokens()
    print(f"📋 تعداد توکن‌های ذخیره شده: {len(tokens)}")
    for token in tokens:
        start_reaction_bot(token)
    
    # شروع پینگ به خود
    threading.Thread(target=ping_self, daemon=True).start()
    
    # اجرای Flask
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Flask server running on port {port}")
    app_flask.run(host='0.0.0.0', port=port)
