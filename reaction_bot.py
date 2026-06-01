import os
import json
import requests
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import asyncio
import threading

app_flask = Flask(__name__)

TOKENS_FILE = "tokens.json"
bots = {}  # ذخیره application هر ربات

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f)

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_token = context.bot.token
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    data = {
        "chat_id": update.effective_chat.id,
        "message_id": update.effective_message.message_id,
        "reaction": [{"type": "emoji", "emoji": "🔥"}]
    }
    try:
        requests.post(url, json=data, timeout=3)
        print(f"Reaction sent for bot {bot_token[:10]}...")
    except Exception as e:
        print(e)

def start_bot(token):
    if token in bots:
        return
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, auto_react))
    # اجرا در thread مجزا برای عدم تداخل با Flask
    def run():
        asyncio.set_event_loop(asyncio.new_event_loop())
        app.run_polling()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    bots[token] = app

def stop_bot(token):
    if token in bots:
        # در عمل توقف واقعی پیچیده‌ست؛ برای سادگی حذف از دیکشنری و بی‌اعتنایی به درخواست‌های بعدی
        del bots[token]

@app_flask.route('/add_token', methods=['POST'])
def add_token():
    data = request.json
    new_token = data.get('token')
    if not new_token:
        return jsonify({"error": "no token"}), 400
    tokens = load_tokens()
    if new_token not in tokens:
        tokens.append(new_token)
        save_tokens(tokens)
        start_bot(new_token)
    return jsonify({"status": "ok"}), 200

@app_flask.route('/')
def index():
    return "Reaction bot manager is running"

if __name__ == "__main__":
    # استارت همه توکن‌های قبلی
    for token in load_tokens():
        start_bot(token)
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host="0.0.0.0", port=port)
