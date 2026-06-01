import os
import json
import subprocess
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- تنظیمات از محیط Render ----------
MOTHER_TOKEN = os.environ.get("MOTHER_BOT_TOKEN")          # توکن ربات مادر
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")        # آدرس وب‌هوک (مثل https://your-app.onrender.com)
if not WEBHOOK_URL:
    print("ERROR: RENDER_EXTERNAL_URL not set")
    sys.exit(1)

TOKENS_FILE = "tokens.json"          # فایل ذخیره توکن‌ها
REACTION_SCRIPT = "reaction_bot.py"  # نام فایل ربات ری اکشن زن
ACTIVE_PROCESSES = {}                # نگهداری پروسه‌های در حال اجرا: token -> process

# ---------- توابع کمکی ----------
def load_tokens():
    """بارگذاری لیست توکن‌ها از فایل"""
    if Path(TOKENS_FILE).exists():
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(tokens):
    """ذخیره لیست توکن‌ها در فایل"""
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def start_reaction_bot(token):
    """اجرای ربات ری اکشن زن به عنوان یک پروسهٔ جداگانه"""
    if token in ACTIVE_PROCESSES and ACTIVE_PROCESSES[token].poll() is None:
        print(f"ربات با توکن {token} قبلاً در حال اجراست.")
        return

    # اجرای اسکریپت ری اکشن زن با پاس دادن توکن از طریق آرگومان
    process = subprocess.Popen(
        [sys.executable, REACTION_SCRIPT, token],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    ACTIVE_PROCESSES[token] = process
    print(f"✅ ربات با توکن {token} راه‌اندازی شد (PID: {process.pid})")

def stop_reaction_bot(token):
    """متوقف کردن یک ربات ری اکشن زن در حال اجرا"""
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
    """پس از راه‌اندازی مجدد ربات مادر، همه ربات‌های قبلی را دوباره اجرا کن"""
    tokens = load_tokens()
    for token in tokens:
        start_reaction_bot(token)

# ---------- هندلرهای ربات مادر ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام خوش‌آمدگویی و درخواست توکن"""
    owner_id = 8852010090   # شناسه مالک (طبق خواسته)
    if update.effective_user.id != owner_id:
        await update.message.reply_text("⛔ شما مجاز به استفاده از این ربات نیستید.")
        return
    await update.message.reply_text(
        "🤖 سلام مالک عزیز!\n"
        "لطفاً توکن ربات ری اکشن زن جدید را ارسال کنید.\n"
        "مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
        "برای توقف یک ربات از دستور /stop استفاده کنید."
    )

async def add_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توکن جدید و افزودن آن به لیست"""
    owner_id = 8852010090
    if update.effective_user.id != owner_id:
        return

    token = update.message.text.strip()
    if not token or ":" not in token:
        await update.message.reply_text("❌ فرمت توکن نامعتبر است. لطفاً یک توکن معتبر بفرستید.")
        return

    tokens = load_tokens()
    if token in tokens:
        await update.message.reply_text("⚠️ این توکن قبلاً اضافه شده است.")
        return

    # اضافه کردن به لیست و ذخیره
    tokens.append(token)
    save_tokens(tokens)

    # اجرای ربات جدید
    start_reaction_bot(token)

    await update.message.reply_text(f"✅ ربات ری اکشن زن با موفقیت راه‌اندازی شد!\nتوکن: `{token}`", parse_mode="Markdown")

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توقف یک ربات ری اکشن زن با توکن داده شده"""
    owner_id = 8852010090
    if update.effective_user.id != owner_id:
        return

    if len(context.args) == 0:
        await update.message.reply_text("لطفاً توکن ربات مورد نظر را وارد کنید.\nمثال: /stop 1234567890:ABC...")
        return

    token = context.args[0]
    tokens = load_tokens()
    if token not in tokens:
        await update.message.reply_text("❌ این توکن در لیست وجود ندارد.")
        return

    # توقف پروسه و حذف از لیست
    if stop_reaction_bot(token):
        tokens.remove(token)
        save_tokens(tokens)
        await update.message.reply_text(f"🛑 ربات با توکن `{token}` متوقف و از لیست حذف شد.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ ربات مورد نظر در حال اجرا نبود، اما از لیست حذف شد.")
        # در هر صورت از لیست پاک می‌کنیم
        tokens.remove(token)
        save_tokens(tokens)

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست ربات‌های فعال"""
    owner_id = 8852010090
    if update.effective_user.id != owner_id:
        return
    tokens = load_tokens()
    if not tokens:
        await update.message.reply_text("هیچ ربات ری اکشن زنی تعریف نشده است.")
        return
    msg = "📋 لیست ربات‌های فعال:\n"
    for t in tokens:
        status = "✅ در حال اجرا" if t in ACTIVE_PROCESSES and ACTIVE_PROCESSES[t].poll() is None else "❌ متوقف"
        msg += f"- `{t}` → {status}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------- راه‌اندازی ربات مادر با وب‌هوک ----------
def main():
    if not MOTHER_TOKEN:
        print("ERROR: MOTHER_BOT_TOKEN environment variable not set")
        sys.exit(1)

    # ساخت اپلیکیشن
    app = Application.builder().token(MOTHER_TOKEN).build()

    # اضافه کردن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_bot))
    app.add_handler(CommandHandler("list", list_bots))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_token))

    # اجرای همه ربات‌های ذخیره شده در فایل
    restart_all_bots()

    # راه‌اندازی وب‌هوک (برای Render)
    print(f"Setting webhook to {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )

if __name__ == "__main__":
    main()
