import os
import sys
import json
import asyncio
import threading
import time
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# چاپ خطاها در همان لحظه
print("📢 برنامه در حال راه‌اندازی...", flush=True)

app_flask = Flask(__name__)

TOKENS_FILE = "tokens.json"
REACTIONS_FILE = "reactions.json"
bots = {}

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
    reactions = load_reactions()
    return reactions.get(token, "🔥")

def set_reaction_for_bot(token, reaction):
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

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_token = context.bot.token
    reaction = get_reaction_for_bot(bot_token)
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    data = {
        "chat_id": update.effective_chat.id,
        "message_id": update.effective_message.message_id,
        "reaction": [{"type": "emoji", "emoji": reaction}]
    }
    try:
        requests.post(url, json=data, timeout=3)
        print(f"✅ واکنش {reaction} ارسال شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

def start_reaction_bot(token):
    if token in bots:
        return
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, auto_react))
    
    def run_bot():
        asyncio.set_event_loop(asyncio.new_event_loop())
        print(f"🚀 ربات ری‌اکشن‌زن {token[:10]}... راه‌اندازی شد")
        app.run_polling()
    
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    bots[token] = app

MOTHER_BOT_TOKEN = os.environ.get('MOTHER_BOT_TOKEN')
if not MOTHER_BOT_TOKEN:
    print("❌ خطای مرگبار: متغیر محیطی MOTHER_BOT_TOKEN تنظیم نشده است!")
    sys.exit(1)

def get_bots_keyboard():
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

def get_reaction_keyboard(bot_token):
    current_reaction = get_reaction_for_bot(bot_token)
    keyboard = [
        [
            InlineKeyboardButton(f"{'✅' if current_reaction == '🔥' else '⬜'} 🔥", callback_data=f"react_{bot_token}_🔥"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '👍' else '⬜'} 👍", callback_data=f"react_{bot_token}_👍"),
            InlineKeyboardButton(f"{'✅' if current_reaction == '❤️' else '⬜'} ❤️", callback_data=f"react_{bot_token}_❤️")
        ],
        [
            InlineKeyboardButton("✏️ سفارشی", callback_data=f"custom_{bot_token}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data=f"menu_{bot_token}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def mother_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8852010090":
        await update.message.reply_text("⛔ شما دسترسی ندارید.")
        return
    keyboard = get_bots_keyboard()
    await update.message.reply_text(
        f"🤖 ربات مادر\nتعداد ربات‌ها: {len(load_tokens())}\nفعال: {len(bots)}",
        reply_markup=keyboard
    )

async def mother_handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("react_"):
        parts = data.split("_")
        bot_token = parts[1] + "_" + parts[2]
        reaction = parts[3]
        set_reaction_for_bot(bot_token, reaction)
        await query.edit_message_text(f"✅ واکنش به {reaction} تغییر کرد", reply_markup=get_reaction_keyboard(bot_token))
    
    elif data.startswith("custom_"):
        bot_token = data[7:]
        context.user_data['custom_reaction_token'] = bot_token
        await query.edit_message_text("✏️ ایموجی مورد نظر را ارسال کنید:")
    
    elif data.startswith("menu_"):
        bot_token = data[5:]
        await query.edit_message_text("منوی واکنش:", reply_markup=get_reaction_keyboard(bot_token))
    
    elif data.startswith("select_"):
        bot_token = data[7:]
        await query.edit_message_text("انتخاب واکنش:", reply_markup=get_reaction_keyboard(bot_token))
    
    elif data == "add_new":
        context.user_data['awaiting_token'] = True
        await query.edit_message_text("➕ توکن ربات جدید را ارسال کنید:")
    
    elif data == "close":
        await query.delete_message()

async def mother_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('custom_reaction_token'):
        token = context.user_data['custom_reaction_token']
        reaction = update.message.text.strip()
        set_reaction_for_bot(token, reaction)
        del context.user_data['custom_reaction_token']
        await update.message.reply_text(f"✅ واکنش سفارشی {reaction} تنظیم شد", reply_markup=get_reaction_keyboard(token))
        return
    
    if context.user_data.get('awaiting_token'):
        token = update.message.text.strip()
        if ':' in token and len(token) > 30:
            if add_token_to_list(token):
                start_reaction_bot(token)
                await update.message.reply_text("✅ ربات جدید اضافه شد")
            else:
                await update.message.reply_text("⚠️ توکن تکراری است")
        else:
            await update.message.reply_text("❌ توکن نامعتبر")
        context.user_data['awaiting_token'] = False
        keyboard = get_bots_keyboard()
        await update.message.reply_text("منوی اصلی:", reply_markup=keyboard)

def start_mother_bot():
    print("🤖 راه‌اندازی ربات مادر...", flush=True)
    app = ApplicationBuilder().token(MOTHER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", mother_start))
    app.add_handler(CallbackQueryHandler(mother_handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mother_handle_message))
    
    def run_mother():
        asyncio.set_event_loop(asyncio.new_event_loop())
        print("✅ ربات مادر اجرا می‌شود", flush=True)
        app.run_polling()
    
    thread = threading.Thread(target=run_mother, daemon=True)
    thread.start()

@app_flask.route('/')
def index():
    return "✅ ربات فعال است"

@app_flask.route('/health')
def health():
    return jsonify({"status": "ok", "bots": len(bots), "tokens": len(load_tokens())})

def ping_self():
    port = os.environ.get('PORT', 5000)
    while True:
        try:
            requests.get(f"http://localhost:{port}/health", timeout=5)
        except:
            pass
        time.sleep(600)

if __name__ == "__main__":
    print("🚀 شروع برنامه...", flush=True)
    
    # راه‌اندازی ربات مادر
    start_mother_bot()
    
    # راه‌اندازی ربات‌های ذخیره شده
    for token in load_tokens():
        start_reaction_bot(token)
    
    # پینگ به خود
    threading.Thread(target=ping_self, daemon=True).start()
    
    # اجرای Flask
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 اجرای Flask روی پورت {port}", flush=True)
    app_flask.run(host='0.0.0.0', port=port)
