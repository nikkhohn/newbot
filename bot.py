# bot.py
import logging
from telegram import Update, Message
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
        "welcome_msg": {
            "text": "🎉 Welcome {name}! Khush Amdeed!",
            "photo": None,
            "entities": []
        },
        "leave_msg": {
            "text": "😢 {name} ne group chhod diya. Alvida!",
            "photo": None,
            "entities": []
        }
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ── Migration: purana format handle karo ──
if isinstance(data.get("welcome_msg"), str):
    data["welcome_msg"] = {"text": data["welcome_msg"], "photo": None, "entities": []}
if isinstance(data.get("leave_msg"), str):
    data["leave_msg"] = {"text": data["leave_msg"], "photo": None, "entities": []}

# ── Admin Check ──
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ── Message bhejo (photo + text + formatting ke saath) ──
async def send_formatted_msg(bot, chat_id, msg_data, name):
    text = msg_data["text"].replace("{name}", name)
    photo = msg_data.get("photo")
    entities = msg_data.get("entities", [])

    # Entities ko adjust karo {name} replacement ke liye
    # (simple approach: parse_mode None, entities as-is)
    try:
        if photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text
            )
    except Exception as e:
        logging.error(f"Message send error: {e}")

# ── Join Request Auto-Accept ──
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

# ── Member Leave ──
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
        "*Message set karne ka tarika:*\n"
        "1️⃣ Bot ko koi bhi message reply karo `/setwelcome` ya `/setleave` ke saath\n"
        "2️⃣ Ya seedha `/setwelcome Aapka message` likho\n"
        "3️⃣ Image bhejni ho to image ke caption mein `/setwelcome` likho\n\n"
        "*Tip:* `{name}` likhne se user ka naam aayega",
        parse_mode="Markdown"
    )

# ── /setwelcome ──
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin ye kar sakta hai!")
        return

    msg = update.message
    new_msg_data = None

    # Case 1: Kisi message ko reply kiya
    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.photo:
            # Photo ke saath message
            photo_id = replied.photo[-1].file_id
            caption = replied.caption or ""
            new_msg_data = {"text": caption, "photo": photo_id, "entities": []}
        elif replied.text:
            new_msg_data = {"text": replied.text, "photo": None, "entities": []}

    # Case 2: Image ke caption mein command
    elif msg.photo:
        photo_id = msg.photo[-1].file_id
        caption = " ".join(context.args) if context.args else ""
        new_msg_data = {"text": caption, "photo": photo_id, "entities": []}

    # Case 3: Seedha text command ke saath
    elif context.args:
        new_msg_data = {"text": " ".join(context.args), "photo": None, "entities": []}

    else:
        await update.message.reply_text(
            "📝 *Welcome message set karne ke 3 tarike:*\n\n"
            "1️⃣ *Seedha text:*\n`/setwelcome Hello {name}! Welcome! 🎉`\n\n"
            "2️⃣ *Kisi message ko reply karke:*\nApna message type karo, usse reply karo `/setwelcome` likh ke\n\n"
            "3️⃣ *Image ke saath:*\nImage bhejo aur caption mein `/setwelcome` likho\n\n"
            "💡 `{name}` se user ka naam aayega",
            parse_mode="Markdown"
        )
        return

    data["welcome_msg"] = new_msg_data
    save_data(data)

    # Confirm karo preview ke saath
    await update.message.reply_text("✅ *Welcome message set ho gaya! Preview:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["welcome_msg"], update.effective_user.first_name)

# ── /setleave ──
async def set_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin ye kar sakta hai!")
        return

    msg = update.message
    new_msg_data = None

    # Case 1: Kisi message ko reply kiya
    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.photo:
            photo_id = replied.photo[-1].file_id
            caption = replied.caption or ""
            new_msg_data = {"text": caption, "photo": photo_id, "entities": []}
        elif replied.text:
            new_msg_data = {"text": replied.text, "photo": None, "entities": []}

    # Case 2: Image ke caption mein command
    elif msg.photo:
        photo_id = msg.photo[-1].file_id
        caption = " ".join(context.args) if context.args else ""
        new_msg_data = {"text": caption, "photo": photo_id, "entities": []}

    # Case 3: Seedha text
    elif context.args:
        new_msg_data = {"text": " ".join(context.args), "photo": None, "entities": []}

    else:
        await update.message.reply_text(
            "📝 *Leave message set karne ke 3 tarike:*\n\n"
            "1️⃣ *Seedha text:*\n`/setleave Bye {name}! 😢`\n\n"
            "2️⃣ *Kisi message ko reply karke:*\nApna message type karo, usse reply karo `/setleave` likh ke\n\n"
            "3️⃣ *Image ke saath:*\nImage bhejo aur caption mein `/setleave` likho\n\n"
            "💡 `{name}` se user ka naam aayega",
            parse_mode="Markdown"
        )
        return

    data["leave_msg"] = new_msg_data
    save_data(data)

    await update.message.reply_text("✅ *Leave message set ho gaya! Preview:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["leave_msg"], update.effective_user.first_name)

# ── /showmsg ──
async def show_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text("📋 *Current Messages:*", parse_mode="Markdown")

    await update.message.reply_text("👋 *Welcome Message:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["welcome_msg"], update.effective_user.first_name)

    await update.message.reply_text("😢 *Leave Message:*", parse_mode="Markdown")
    await send_formatted_msg(context.bot, update.effective_chat.id, data["leave_msg"], update.effective_user.first_name)

# ── /broadcast ──
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin broadcast kar sakta hai!")
        return

    msg = update.message
    broadcast_data = None

    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.photo:
            broadcast_data = {"text": replied.caption or "", "photo": replied.photo[-1].file_id, "entities": []}
        elif replied.text:
            broadcast_data = {"text": replied.text, "photo": None, "entities": []}
    elif context.args:
        broadcast_data = {"text": " ".join(context.args), "photo": None, "entities": []}

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

    # Photo ke saath command handle karo
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r'^/setwelcome'),
        set_welcome
    ))
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r'^/setleave'),
        set_leave
    ))

    print("🚀 Bot chal raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
