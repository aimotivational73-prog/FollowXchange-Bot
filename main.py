import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@okaxis")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://your-app.onrender.com

# Conversation States
WAITING_FOR_SCREENSHOT, WAITING_FOR_USERNAME = range(2)

# Global PTB Application Instance
ptb_app = Application.builder().token(BOT_TOKEN).build()


# --- Bot Command & Conversation Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends welcome message with package choices."""
    keyboard = [
        [InlineKeyboardButton("🛒 Buy 100 Followers (Rs 20)", callback_data="pkg_100_20")],
        [InlineKeyboardButton("🛒 Buy 500 Followers (Rs 55)", callback_data="pkg_500_55")],
        [InlineKeyboardButton("🛒 Buy 1000 Followers (Rs 90)", callback_data="pkg_1000_90")],
        [InlineKeyboardButton("🛒 Buy 5000 Followers (Rs 360)", callback_data="pkg_5000_360")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the **FollowXchange Payment Bot**!\n\n"
        "Boost your profile quickly by purchasing followers below. "
        "Select your preferred followers package to continue:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides usage instructions."""
    await update.message.reply_text(
        "ℹ️ **How to buy followers:**\n\n"
        "1. Type /start and select a package.\n"
        "2. Complete the payment using the generated UPI details.\n"
        "3. Upload your payment screenshot directly into this chat.\n"
        "4. Provide your FollowXchange platform username when prompted.\n"
        "5. Wait briefly while our admin team verifies your transaction!",
        parse_mode="Markdown"
    )


async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles package clicks and displays payment links."""
    query = update.callback_query
    await query.answer()
    
    _, followers_count, amount = query.data.split("_")
    context.user_data["selected_followers"] = followers_count
    context.user_data["selected_amount"] = amount
    
    # Generate deep-linking UPI URL
    upi_url = f"upi://pay?pa={UPI_ID}&pn=FollowXchange&am={amount}&cu=INR"
    
    await query.edit_message_text(
        f"📊 **Package Selected:** {followers_count} Followers for Rs {amount}\n\n"
        f"💳 **How to Pay:**\n"
        f"• Tap to copy UPI ID: `{UPI_ID}`\n"
        f"• Or use this link to open your payment app: [Pay Now via UPI]({upi_url})\n\n"
        f"📸 **Next Step:**\n"
        f"After completing your transaction, please upload your **payment screenshot** directly to this chat.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return WAITING_FOR_SCREENSHOT


async def screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves screenshot file ID and prompts for user platform handle."""
    photo_file_id = update.message.photo[-1].file_id
    context.user_data["screenshot_file_id"] = photo_file_id
    
    await update.message.reply_text(
        "✅ Screenshot received successfully!\n\n"
        "⌨️ Please type your **FollowXchange Username** exactly as it appears on the website so we can credit your account:"
    )
    return WAITING_FOR_USERNAME


async def username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forwards submission dataset directly to administrative terminal."""
    fx_username = update.message.text.strip()
    user_chat_id = update.message.chat_id
    
    followers_count = context.user_data.get("selected_followers", "Unknown")
    amount = context.user_data.get("selected_amount", "Unknown")
    screenshot = context.user_data.get("screenshot_file_id")
    
    # Notify user submission is pending review
    await update.message.reply_text(
        "⏳ Thank you! Your payment details have been routed to our verification queue. "
        "You will receive an automatic notification here once approved."
    )
    
    # Generate evaluation components for administration panel
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_chat_id}_{amount}_{followers_count}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_chat_id}_{amount}"),
        ]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)
    
    admin_caption = (
        f"🚨 **New Payment Verification Request**\n\n"
        f"👤 **Platform Username:** `{fx_username}`\n"
        f"🆔 **Telegram Chat ID:** `{user_chat_id}`\n"
        f"📦 **Requested Item:** {followers_count} Followers\n"
        f"💰 **Transaction Value:** Rs {amount}"
    )
    
    # Forward complete packet to admin endpoint
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=screenshot,
        caption=admin_caption,
        reply_markup=admin_markup,
        parse_mode="Markdown"
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels active conversation tracking state sequence."""
    await update.message.reply_text("❌ Action cancelled. Type /start to open the package menu again.")
    context.user_data.clear()
    return ConversationHandler.END


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes verification decisions returned from administrative inputs."""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("_")
    action = data_parts[0]
    target_user_id = int(data_parts[1])
    amount = data_parts[2]
    
    if action == "app":
        followers_count = data_parts[3]
        # Notify user of successful account crediting
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🥳 **Payment Confirmed!**\n\n"
                     f"Your purchase of **{followers_count} Followers** (Rs {amount}) has been approved. "
                     f"The followers will appear in your platform dashboard momentarily.",
                parse_mode="Markdown"
            )
            # Update admin view interface state
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n🟢 **Status:** Approved by Admin.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to message user {target_user_id}: {e}")
            
    elif action == "rej":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"⚠️ **Payment Verification Failed**\n\n"
                     f"Your order matching Rs {amount} was rejected by verification. "
                     f"Please confirm transaction logs, clear screenshots, or contact customer support.",
                parse_mode="Markdown"
            )
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n🔴 **Status:** Rejected by Admin.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to message user {target_user_id}: {e}")


# --- FastAPI Engine Lifecycle Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register core pipeline architectures
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected, pattern="^pkg_")],
        states={
            WAITING_FOR_SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot_received)],
            WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )
    
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(CommandHandler("help", help_command))
    ptb_app.add_handler(conv_handler)
    ptb_app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(app|rej)_"))

    # Activate bot orchestration instances
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/tgwebhook")
    logger.info(f"Webhook set successfully to: {WEBHOOK_URL}/tgwebhook")
    
    yield
    
    # Graceful shutdown process execution
    await ptb_app.stop()
    await ptb_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/tgwebhook")
async def handle_webhook(request: Request):
    """Transforms webhook requests directly into Telegram pipeline signals."""
    json_data = await request.json()
    update = Update.de_json(json_data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)


@app.get("/")
async def health_check():
    """Serves response patterns satisfying hosting target keepalive requirements."""
    return {"status": "online", "platform": "FollowXchange"}
