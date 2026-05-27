# bot.py
import logging
from telegram import Update
from telegram.ext import (
    Application, ChatJoinRequestHandler, MessageHandler,
    CommandHandler, ContextTypes, filters
)
import json, os

# ============ SETTINGS ============
BOT_TOKEN = os.getenv("BOT_TOKEN")        # ✅ Token ab environment se aayega
ADMIN_IDS = [8555676613]
DATA_FILE = "data.json"
# ==================================

logging.basicConfig(level=logging.INFO)

# ── Data Load/Save ──
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "members": [],
        "welcome_msg": "🎉 Welcome {name}! Khush Amdeed!",
        "leave_msg": "😢 {name} ne group chhod diya. Alvida!"
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ── Admin Check ──
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ── Join Request Auto-Accept ──
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    chat = request.chat

    await context.bot.approve_chat_join_request(chat.id, user.id)

    if user.id not in data["members"]:
        data["members"].append(user.id)
        save_data(data)

    msg = data["welcome_msg"].format(name=user.first_name)
    try:
        await context.bot.send_message(chat_id=user.id, text=msg)
    except:
        await context.bot.send_message(chat_id=chat.id, text=msg)

    print(f"✅ Accepted: {user.first_name}")

# ── Member Leave ──
async def handle_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    chat = update.message.chat

    if user.id in data["members"]:
        data["members"].remove(user.id)
        save_data(data)

    msg = data["leave_msg"].format(name=user.first_name)
    await context.bot.send_message(chat_id=chat.id, text=msg)

# ══════════════════════════════════
#         BOT COMMANDS
# ══════════════════════════════════

# ── /start ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Active Hai!*\n\n"
        "*Admin Commands:*\n"
        "✏️ /setwelcome - Welcome msg set karo\n"
        "✏️ /setleave - Leave msg set karo\n"
        "👁 /showmsg - Current msgs dekho\n"
        "📢 /broadcast - Sabko message bhejo\n"
        "📊 /stats - Members count\n\n"
        "*Tip:* {name} likhne se user ka naam aayega",
        parse_mode="Markdown"
    )

# ── /setwelcome ──
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin ye kar sakta hai!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 *Usage:*\n/setwelcome Aapka welcome message\n\n"
            "Tip: {name} se user ka naam aayega\n"
            "Example: /setwelcome Hello {name}, welcome to our group! 🎉",
            parse_mode="Markdown"
        )
        return

    new_msg = " ".join(context.args)
    data["welcome_msg"] = new_msg
    save_data(data)

    await update.message.reply_text(
        f"✅ *Welcome message update ho gaya!*\n\n"
        f"📝 New Message:\n{new_msg}",
        parse_mode="Markdown"
    )

# ── /setleave ──
async def set_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin ye kar sakta hai!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 *Usage:*\n/setleave Aapka leave message\n\n"
            "Tip: {name} se user ka naam aayega\n"
            "Example: /setleave Bye {name}, tumhari yaad aayegi! 😢",
            parse_mode="Markdown"
        )
        return

    new_msg = " ".join(context.args)
    data["leave_msg"] = new_msg
    save_data(data)

    await update.message.reply_text(
        f"✅ *Leave message update ho gaya!*\n\n"
        f"📝 New Message:\n{new_msg}",
        parse_mode="Markdown"
    )

# ── /showmsg ──
async def show_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        f"📋 *Current Messages:*\n\n"
        f"👋 *Welcome Msg:*\n{data['welcome_msg']}\n\n"
        f"😢 *Leave Msg:*\n{data['leave_msg']}",
        parse_mode="Markdown"
    )

# ── /broadcast ──
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin broadcast kar sakta hai!")
        return

    if not context.args:
        await update.message.reply_text(
            "📢 *Usage:*\n/broadcast Aapka message\n\n"
            "Example: /broadcast Aaj raat 8 baje live hoga!",
            parse_mode="Markdown"
        )
        return

    msg = " ".join(context.args)
    success, failed = 0, 0

    status = await update.message.reply_text(f"📤 Sending {len(data['members'])} members ko...")

    for user_id in data["members"].copy():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Broadcast Message:*\n\n{msg}",
                parse_mode="Markdown"
            )
            success += 1
        except:
            failed += 1

    await status.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"📨 Sent: {success}\n"
        f"❌ Failed: {failed}",
        parse_mode="Markdown"
    )

# ── /stats ──
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"📊 *Stats:*\n\n"
        f"👥 Total Members: {len(data['members'])}",
        parse_mode="Markdown"
    )

# ── Main ──
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_member_left))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setleave", set_leave))
    app.add_handler(CommandHandler("showmsg", show_msg))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    print("🚀 Bot chal raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
