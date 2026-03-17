import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789               # Change to your telegram ID
CHANNEL_USERNAME = "@yourchannel"  # User must join this channel

DB_FILE = "data.json"

# ----------------- DATABASE -----------------
def load_data():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(data, user_id):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "referrals": 0,
            "balance": 0.0,
            "referred_by": None
        }
    return data[user_id]

# ----------------- CHECK JOIN CHANNEL -----------------
async def is_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_join(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Check Again", callback_data="check_join")]
    ]
    text = "❌ You must join our channel first!"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------- START -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_joined(user_id, context):
        return await force_join(update, context)

    data = load_data()
    user = get_user(data, user_id)

    # referral
    if context.args:
        ref_id = context.args[0]
        # 1 user = 1 referral only & prevent self-referral
        if ref_id != str(user_id) and user["referred_by"] is None:
            user["referred_by"] = ref_id
            ref_user = get_user(data, ref_id)

            ref_user["referrals"] += 1

            # reward after 50 referrals
            if ref_user["referrals"] % 50 == 0:
                ref_user["balance"] += 0.05

    save_data(data)

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📤 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="ref")]
    ]

    await update.message.reply_text(
        "Welcome!\nEarn money by inviting friends 💸",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------- BUTTON -----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_joined(user_id, context):
        return await force_join(update, context)

    data = load_data()
    user = get_user(data, user_id)

    if query.data == "balance":
        await query.message.reply_text(
            f"👥 Referrals: {user['referrals']}\n💰 Balance: ${user['balance']:.2f}"
        )

    elif query.data == "ref":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await query.message.reply_text(f"🔗 Your referral link:\n{link}")

    elif query.data == "withdraw":
        if user["balance"] <= 0:
            return await query.message.reply_text("❌ No balance to withdraw!")
        await query.message.reply_text("📸 Send your QR code to request withdraw")
        context.user_data["awaiting_qr"] = True

    elif query.data == "check_join":
        if await is_joined(user_id, context):
            await query.message.reply_text("✅ You joined! Use /start again")
        else:
            await force_join(update, context)

    save_data(data)

# ----------------- HANDLE QR PHOTO -----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_qr"):
        user = update.effective_user
        photo = update.message.photo[-1].file_id

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=f"💸 Withdraw Request\nUser: {user.id}"
        )

        await update.message.reply_text("✅ Your withdraw request has been sent to admin")
        context.user_data["awaiting_qr"] = False

# ----------------- RUN BOT -----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("Bot running...")
app.run_polling()
