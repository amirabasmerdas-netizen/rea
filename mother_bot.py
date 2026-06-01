import os
import json
import subprocess
import sys
from pathlib import Path
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- تنظیمات ----------
MOTHER_TOKEN = os.environ.get("MOTHER_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")  # آدرس رندر مثل https://rea-vj4q.onrender.com
PORT = int(os.environ.get("PORT", 8443))

if not MOTHER_TOKEN:
    print("ERROR: MOTHER_BOT_TOKEN environment variable not set")
    sys.exit(1)

if not WEBHOOK_URL:
    print("ERROR: RENDER_EXTERNAL_URL environment variable not set")
    sys.exit(1)

TOKENS_FILE = "tokens.json"
REACTION_SCRIPT = "reaction_bot.py"
ACTIVE_PROCESSES = {}

# 👇 شناسه واقعی مالک را اینجا وارد کنید (شناسه خودتان)
OWNER_ID = 8852010090  # این را به شناسه عددی خودتان تغییر دهید

# ---------- توابع کمکی ----------
def load_tokens():
    if Path(TOKENS_FILE).exists():
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def start_reaction_bot(token):
    if token in ACTIVE_PROCESSES and ACTIVE_PROCESSES[token].poll() is None:
        print(f"ربات با توکن {token} قبلاً در حال اجراست.")
        return
    process = subprocess.Popen(
        [sys.executable, REACTION_SCRIPT, token],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    ACTIVE_PROCESSES[token] = process
    print(f"✅ ربات با توکن {token} راه‌اندازی شد (PID: {process.pid})")

def stop_reaction_bot(token):
    proc = ACTIVE_PROCESSES.get(token)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del ACTIVE_PROCESSES[token]
        print(f"🛑 ربات با توکن {token} متوقف شد.")
        return True
    return False

def restart_all_bots():
    tokens = load_tokens()
    for token in tokens:
        start_reaction_bot(token)

# ---------- هندلرها ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text(f"⛔ شما مجاز به استفاده از این ربات نیستید.\nشناسه شما: {user_id}")
        return
    await update.message.reply_text(
        "🤖 **ربات مادر ری اکشن زن**\n\n"
        "لطفاً توکن ربات ری اکشن زن جدید را ارسال کنید.\n"
        "مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
        "📌 **دستورات:**\n"
        "/start - نمایش راهنما\n"
        "/list - لیست ربات‌های فعال\n"
        "/stop توکن - متوقف کردن یک ربات\n"
        "/ping - بررسی وضعیت ربات",
        parse_mode="Markdown"
    )

async def add_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    token = update.message.text.strip()
    if not token or ":" not in token:
        await update.message.reply_text("❌ فرمت توکن نامعتبر است. لطفاً یک توکن معتبر بفرستید.")
        return
    tokens = load_tokens()
    if token in tokens:
        await update.message.reply_text("⚠️ این توکن قبلاً اضافه شده است.")
        return
    tokens.append(token)
    save_tokens(tokens)
    start_reaction_bot(token)
    await update.message.reply_text(f"✅ ربات ری اکشن زن با موفقیت راه‌اندازی شد!\nتوکن: `{token}`", parse_mode="Markdown")

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) == 0:
        await update.message.reply_text("لطفاً توکن ربات مورد نظر را وارد کنید.\nمثال: /stop 1234567890:ABC...")
        return
    token = context.args[0]
    tokens = load_tokens()
    if token not in tokens:
        await update.message.reply_text("❌ این توکن در لیست وجود ندارد.")
        return
    if stop_reaction_bot(token):
        tokens.remove(token)
        save_tokens(tokens)
        await update.message.reply_text(f"🛑 ربات با توکن `{token}` متوقف و از لیست حذف شد.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ ربات مورد نظر در حال اجرا نبود، اما از لیست حذف شد.")
        tokens.remove(token)
        save_tokens(tokens)

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    tokens = load_tokens()
    if not tokens:
        await update.message.reply_text("هیچ ربات ری اکشن زنی تعریف نشده است.")
        return
    msg = "📋 لیست ربات‌های فعال:\n"
    for t in tokens:
        status = "✅ در حال اجرا" if t in ACTIVE_PROCESSES and ACTIVE_PROCESSES[t].poll() is None else "❌ متوقف"
        msg += f"- `{t[:20]}...` → {status}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("🏓 پونگ! ربات فعال است.")

# ---------- راه‌اندازی Webhook ----------
def main():
    app = Application.builder().token(MOTHER_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_bot))
    app.add_handler(CommandHandler("list", list_bots))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_token))
    
    restart_all_bots()
    
    print(f"راه‌اندازی Webhook روی {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )

if __name__ == "__main__":
    main()
