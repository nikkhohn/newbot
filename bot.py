# bot.py
import logging
from telegram import Update
from telegram.ext import (
    Application, ChatJoinRequestHandler, MessageHandler,
    CommandHandler, ContextTypes, filters
)
import json, os

# ============ SETTINGS ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
        "welcome_msg": {"text": "🎉 Welcome {name}! Khush Amdeed!", "photo": None},
        "leave_msg": {"text": "😢 {name} ne group chhod diya. Alvida!", "photo": None},
        "start_msg": {"text": "👋 Assalam o Alaikum {name}!\n\nIs bot ke baare mein janne ke liye admin se contact karo.", "photo": None}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ── Purana format migrate karo ──
for key in ["welcome_msg", "leave_msg", "start_msg"]:
    if isinstance(data.get(key), str):
        data[key] = {"text": data[key], "photo": None}
if "start_msg" not in data:
    data["start_msg"] = {"text": "👋 Assalam o Alaikum {name}!\n\nIs bot ke baare mein janne ke liye admin se contact karo.", "photo": None}
save_data(data)

# ── Admin Check ──
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ── Formatted message bhejo ──
async def send_formatted_msg(bot, chat_id, msg_data, name):
    text = msg_data["text"].replace("{name}", name)
    photo = msg_data.get("photo")
    try:
        if photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"Message send error: {e}")

# ── Message set karne ka common function ──
async def set_msg_handler(update, context, msg_key, label):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin ye kar sakta hai!")
        return

    msg = update.message
    new_data = None

    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.photo:
            new_data = {"text": replied.caption or "", "photo": replied.photo[-1].file_id}
        elif replied.text:
            new_data = {"text": replied.text, "photo": None}
    elif msg.photo:
        new_data = {"text": " ".join(context.args) if context.args else "", "photo": msg.photo[-1].file_id}
    elif context.args:
        new_data = {"text": " ".join(context.args), "photo": None}
    else:
        await update.message.reply_text(
            f"📝 *{label} set karne ke 3 tarike:*\n\n"
            f"1️⃣ *Seedha text:*\n`/{msg_key.replace('_msg','')} Hello {{name}}!`\n\n"
            f"2️⃣ *Reply karke:*\nApna message type karo → reply karo `/{msg_key.replace('_msg','')}` se\n\n"
            f"3️⃣ *Image ke saath:*\nImage bhejo, caption mein `/{msg_key.replace('_msg','')}` likho\n\n"
            f"💡 `{{name}}` se user ka naam aayega",
            parse_mode="Markdown"
        )
        return

    data[msg_key] = new_data
    save_data(data)

    await update.message.reply_text(f"✅ *{label} set ho gaya! Preview:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data[msg_key], update.effective_user.first_name)

# ══════════════════════════════════
#         EVENTS
# ══════════════════════════════════

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    chat = request.chat

    await context.bot.approve_chat_join_request(chat.id, user.id)

    if user.id not in data["members"]:
        data["members"].append(user.id)
        save_data(data)

    try:
        await send_formatted_msg(context.bot, user.id, data["welcome_msg"], user.first_name)
    except:
        await send_formatted_msg(context.bot, chat.id, data["welcome_msg"], user.first_name)

    print(f"✅ Accepted: {user.first_name}")

async def handle_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    chat = update.message.chat

    if user.id in data["members"]:
        data["members"].remove(user.id)
        save_data(data)

    await send_formatted_msg(context.bot, chat.id, data["leave_msg"], user.first_name)

# ══════════════════════════════════
#         BOT COMMANDS
# ══════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Agar admin hai to admin panel dikhao
    if is_admin(user.id):
        await update.message.reply_text(
            "🤖 *Admin Panel*\n\n"
            "*Commands:*\n"
            "✏️ /setwelcome - Welcome msg set karo\n"
            "✏️ /setleave - Leave msg set karo\n"
            "✏️ /setstart - Start msg set karo\n"
            "👁 /showmsg - Current msgs dekho\n"
            "📢 /broadcast - Sabko message bhejo\n"
            "📊 /stats - Members count\n\n"
            "*Tip:* `{name}` se user ka naam aayega",
            parse_mode="Markdown"
        )
    else:
        # Normal user ko custom start message dikhao
        await send_formatted_msg(context.bot, user.id, data["start_msg"], user.first_name)

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_msg_handler(update, context, "welcome_msg", "Welcome Message")

async def set_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_msg_handler(update, context, "leave_msg", "Leave Message")

async def set_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_msg_handler(update, context, "start_msg", "Start Message")

async def show_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text("📋 *Current Messages:*", parse_mode="Markdown")

    await update.message.reply_text("👋 *Welcome Msg:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["welcome_msg"], update.effective_user.first_name)

    await update.message.reply_text("😢 *Leave Msg:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["leave_msg"], update.effective_user.first_name)

    await update.message.reply_text("▶️ *Start Msg:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["start_msg"], update.effective_user.first_name)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin broadcast kar sakta hai!")
        return

    msg = update.message
    broadcast_data = None

    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.photo:
            broadcast_data = {"text": replied.caption or "", "photo": replied.photo[-1].file_id}
        elif replied.text:
            broadcast_data = {"text": replied.text, "photo": None}
    elif context.args:
        broadcast_data = {"text": " ".join(context.args), "photo": None}

    if not broadcast_data:
        await update.message.reply_text(
            "📢 *Usage:*\n"
            "1️⃣ `/broadcast Aapka message`\n"
            "2️⃣ Kisi message ko reply karo `/broadcast` se",
            parse_mode="Markdown"
        )
        return

    success, failed = 0, 0
    status = await update.message.reply_text(f"📤 Sending {len(data['members'])} members ko...")

    for user_id in data["members"].copy():
        try:
            await send_formatted_msg(context.bot, user_id, broadcast_data, "")
            success += 1
        except:
            failed += 1

    await status.edit_text(
        f"✅ *Broadcast Complete!*\n\n📨 Sent: {success}\n❌ Failed: {failed}",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"📊 *Stats:*\n\n👥 Total Members: {len(data['members'])}",
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
    app.add_handler(CommandHandler("setstart", set_start))
    app.add_handler(CommandHandler("showmsg", show_msg))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/setwelcome'), set_welcome))
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/setleave'), set_leave))
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/setstart'), set_start))

    print("🚀 Bot chal raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
