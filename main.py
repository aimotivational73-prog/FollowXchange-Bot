import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Logging on kardi hai taaki koi error aaye toh clearly dikhe
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Settings from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@okaxis")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

WAITING_FOR_SCREENSHOT, WAITING_FOR_USERNAME = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Buy 100 Points (Rs 10)", callback_data="pkg_100_10")],
        [InlineKeyboardButton("🛒 Buy 500 Points (Rs 45)", callback_data="pkg_500_45")],
        [InlineKeyboardButton("🛒 Buy 1000 Points (Rs 80)", callback_data="pkg_1000_80")],
        [InlineKeyboardButton("🛒 Buy 5000 Points (Rs 350)", callback_data="pkg_5000_350")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the *FollowXchange Payment Bot*!\n\n"
        "Select your preferred points package to continue:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Type /start to buy points. Follow the instructions to pay and upload screenshot.")

async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, points, amount = query.data.split("_")
    context.user_data["points"] = points
    context.user_data["amount"] = amount
    upi_url = f"upi://pay?pa={UPI_ID}&pn=FollowXchange&am={amount}&cu=INR"
    
    await query.edit_message_text(
        f"📊 *Package:* {points} Points for Rs {amount}\n\n"
        f"💳 *Pay Here:* `{UPI_ID}`\n"
        f"🔗 [Click to Pay via App]({upi_url})\n\n"
        f"📸 *Next:* Upload your payment screenshot here.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return WAITING_FOR_SCREENSHOT

async def screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["screenshot"] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Screenshot received!\n⌨️ Now, type your *FollowXchange Username*:", parse_mode="Markdown")
    return WAITING_FOR_USERNAME

async def username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fx_username = update.message.text.strip()
    user_chat_id = update.message.chat_id
    points = context.user_data.get("points")
    amount = context.user_data.get("amount")
    screenshot = context.user_data.get("screenshot")
    
    await update.message.reply_text("⏳ Please wait while Admin verifies your payment.")
    
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_chat_id}_{amount}_{points}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_chat_id}_{amount}"),
        ]
    ]
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=screenshot,
        caption=f"🚨 *New Payment*\nUsername: `{fx_username}`\nPoints: {points}\nAmount: Rs {amount}",
        reply_markup=InlineKeyboardMarkup(admin_keyboard),
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send /start again.")
    context.user_data.clear()
    return ConversationHandler.END

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    action, user_id, amount = parts[0], int(parts[1]), parts[2]
    
    if action == "app":
        await context.bot.send_message(chat_id=user_id, text=f"🥳 *Approved!* Rs {amount} payment verified.", parse_mode="Markdown")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n🟢 *APPROVED*", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=user_id, text=f"⚠️ *Rejected!* Rs {amount} payment failed verification.", parse_mode="Markdown")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n🔴 *REJECTED*", parse_mode="Markdown")

def main():
    # Crash rokne ke liye checks
    if not BOT_TOKEN or not WEBHOOK_URL:
        logger.error("🚨 BOT_TOKEN or WEBHOOK_URL is missing in Render Settings!")
        return

    # Render automatically provides a PORT variable
    PORT = int(os.environ.get("PORT", "10000"))

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected, pattern="^pkg_")],
        states={
            WAITING_FOR_SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot_received)],
            WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(app|rej)_"))

    # Ye line server start karegi bina crash hue
    logger.info("🚀 Starting Webhook Server...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/tgwebhook"
    )

if __name__ == "__main__":
    main()
