import os
import uuid
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


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@okaxis")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://your-app.onrender.com


PROMO_CODES = {
    "WELCOME20": {"discount_percent": 15, "active": True},
    "FESTIVAL10": {"discount_percent": 5, "active": True},
    "FREEDOM50": {"discount_percent": 10, "active": False} 
}


WEBSITE_ URL = "https://followxchange.store"
Instagram PAGE = "https://www.instagram.com/followxchangeofcl?igsh=MWpha3o5ODNpYXNmZQ=="
LEGAL_FOOTER = (
    "\n\n⚖️ *Legal & Privacy Agreement:*\n"
    "By proceeding with this transaction, you acknowledge and agree to our "
    f"[Terms & Conditions]({https://followxchange.store/terms-conditions.html}/terms-conditions.html), "
    f"[Privacy Policy]({https://followxchange.store/privacy-policy.html}/privacy-policy.html), and "
    f"[Refund Policy]({https://followxchange.store/refund-policy.html}/refund-policy.html).\n"
    "⚠️ *Disclaimer:* FollowXchange is a 3rd-party growth service and is strictly NOT affiliated with, endorsed by, or connected to Instagram or Meta Platforms Inc."
)


WAITING_FOR_PROMO_DECISION, WAITING_FOR_PROMO, WAITING_FOR_SCREENSHOT, WAITING_FOR_USERNAME = range(4)


ptb_app = Application.builder().token(BOT_TOKEN).build()




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends welcome message with package choices."""
    keyboard = [
        [InlineKeyboardButton("🛒 Buy 100 Followers (Rs 19)", callback_data="pkg_100_19")],
        [InlineKeyboardButton("🛒 Buy 200 Followers (Rs 29)", callback_data="pkg_200_29")],
        [InlineKeyboardButton("🛒 Buy 300 Followers (Rs 49)", callback_data="pkg_300_49")],
        [InlineKeyboardButton("🛒 Buy 500 Followers (Rs 69)", callback_data="pkg_500_69")],
        [InlineKeyboardButton("🛒 Buy 1000 Followers (Rs 119)", callback_data="pkg_1000_119")],
        [InlineKeyboardButton("🛒 Buy 2500 Followers (Rs 249)", callback_data="pkg_2500_249")],
        [InlineKeyboardButton("🛒 Buy 5000 Followers (Rs 499)", callback_data="pkg_5000_499")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🌟 **Welcome to the FollowXchange Bot!** 🌟\n\n"
        "Grow your Instagram presence instantly with our high-quality, authentic followers. "
        "Secure your order by selecting a package below:\n"
        f"{LEGAL_FOOTER}"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides usage instructions."""
    await update.message.reply_text(
        "ℹ️ **How to buy followers securely:**\n\n"
        "1️⃣ Type /start and select your preferred package.\n"
        "2️⃣ Apply a Promo Code (if you have one) to get a discount.\n"
        "3️⃣ Complete the payment safely using the provided UPI details.\n"
        "4️⃣ Upload your successful payment screenshot here.\n"
        "5️⃣ Enter your exact FollowXchange App username.\n"
        "6️⃣ Sit back! Our admin team will verify and deliver your followers quickly.\n\n"
        f"Need more help? Contact our support via the website: {WEBSITE_URL}",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles package clicks and asks for promo code."""
    query = update.callback_query
    await query.answer()
    
    _, followers_count, amount = query.data.split("_")
    
    
    context.user_data["selected_followers"] = followers_count
    context.user_data["original_amount"] = float(amount)
    context.user_data["order_id"] = f"FX-{uuid.uuid4().hex[:6].upper()}" 
    
    keyboard = [
        [InlineKeyboardButton("🎟 Yes, I have a Promo Code", callback_data="promo_yes")],
        [InlineKeyboardButton("⏭ No, Skip to Payment", callback_data="promo_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📦 **Order Initiated (ID: {context.user_data['order_id']})**\n"
        f"You selected **{followers_count} Followers** for **Rs {amount}**.\n\n"
        f"💡 Do you have a promo code for a discount?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return WAITING_FOR_PROMO_DECISION


async def promo_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles promo code decision (Yes/No)."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "promo_yes":
        await query.edit_message_text(
            "🎟 **Enter your Promo Code:**\n\n"
            "*(Type your promo code below and send it. Type `skip` if you changed your mind.)*",
            parse_mode="Markdown"
        )
        return WAITING_FOR_PROMO
    else:
        
        context.user_data["final_amount"] = context.user_data["original_amount"]
        context.user_data["promo_applied"] = "None"
        return await show_payment_details(update, context, is_query=True)


async def promo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validates the entered promo code."""
    code = update.message.text.strip().upper()
    
    if code.lower() == 'skip':
        context.user_data["final_amount"] = context.user_data["original_amount"]
        context.user_data["promo_applied"] = "None"
        return await show_payment_details(update, context, is_query=False)

    if code in PROMO_CODES and PROMO_CODES[code]["active"]:
        discount = PROMO_CODES[code]["discount_percent"]
        orig_amount = context.user_data["original_amount"]
        
        
        final_amount = orig_amount - (orig_amount * (discount / 100))
        context.user_data["final_amount"] = round(final_amount, 2)
        context.user_data["promo_applied"] = code
        
        await update.message.reply_text(
            f"🎉 **Promo Code Accepted!**\n"
            f"You got a {discount}% discount. Your new total is **Rs {context.user_data['final_amount']}**.",
            parse_mode="Markdown"
        )
        return await show_payment_details(update, context, is_query=False)
    else:
        await update.message.reply_text(
            "❌ **Invalid or Expired Promo Code.**\n"
            "Please try again or type `skip` to proceed without a discount.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_PROMO


async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query=False):
    """Displays final payment details and UPI link."""
    amount = context.user_data.get("final_amount")
    followers = context.user_data.get("selected_followers")
    order_id = context.user_data.get("order_id")
    
    upi_url = f"upi://pay?pa={UPI_ID}&pn=FollowXchange&am={amount}&cu=INR&tr={order_id}"
    
    text = (
        f"🧾 **SECURE CHECKOUT**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **Order ID:** `{order_id}`\n"
        f"📦 **Package:** {followers} Followers\n"
        f"💰 **Total to Pay:** Rs {amount}\n\n"
        f"💳 **HOW TO PAY:**\n"
        f"1️⃣ Tap to copy UPI ID: `{UPI_ID}`\n"
        f"2️⃣ Or use Auto-Pay Link: [Pay Now via UPI App]({upi_url})\n\n"
        f"📸 **FINAL STEP:**\n"
        f"Once payment is completed, please **Upload the Payment Screenshot** directly in this chat."
        f"{LEGAL_FOOTER}"
    )
    
    if is_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
        
    return WAITING_FOR_SCREENSHOT


async def screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves screenshot file ID and prompts for user platform handle."""
    photo_file_id = update.message.photo[-1].file_id
    context.user_data["screenshot_file_id"] = photo_file_id
    
    await update.message.reply_text(
        "✅ **Screenshot Verified Securely!**\n\n"
        "⌨️ Please type your exact **Username** (without @) so we can deliver your followers:"
    )
    return WAITING_FOR_USERNAME


async def username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forwards submission dataset directly to administrative terminal."""
    fx_username = update.message.text.strip()
    user_chat_id = update.message.chat_id
    
    followers_count = context.user_data.get("selected_followers", "Unknown")
    amount = context.user_data.get("final_amount", "Unknown")
    promo = context.user_data.get("promo_applied", "None")
    order_id = context.user_data.get("order_id", "Unknown")
    screenshot = context.user_data.get("screenshot_file_id")
    
    
    await update.message.reply_text(
        f"⏳ **Order Placed Successfully! (ID: {order_id})**\n\n"
        "Your payment and details have been securely routed to our verification queue. "
        "You will receive a confirmation message here as soon as our admins approve it.\n\n"
        "Thank you for choosing FollowXchange! ❤️"
    )
    
    
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Approve Order", callback_data=f"app_{user_chat_id}_{amount}_{followers_count}"),
            InlineKeyboardButton("❌ Reject Order", callback_data=f"rej_{user_chat_id}_{amount}"),
        ]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)
    
    admin_caption = (
        f"🚨 **NEW PAYMENT VERIFICATION** 🚨\n\n"
        f"🆔 **Order ID:** `{order_id}`\n"
        f"👤 **Username:** `{fx_username}`\n"
        f"💬 **Telegram User ID:** `{user_chat_id}`\n"
        f"📦 **Followers Requested:** {followers_count}\n"
        f"💰 **Amount Paid:** Rs {amount}\n"
        f"🎟 **Promo Used:** {promo}"
    )
    
    
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
    await update.message.reply_text("❌ Action safely cancelled. Type /start when you are ready to order again.")
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
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🥳 **PAYMENT APPROVED!**\n\n"
                     f"Your purchase of **{followers_count} Followers** (Rs {amount}) has been successfully verified. "
                     f"The followers will be routed to your account momentarily. Enjoy!\n\n"
                     f"Need more? Just type /start to order again.",
                parse_mode="Markdown"
            )
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n🟢 **STATUS: APPROVED ✅**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to message user {target_user_id}: {e}")
            
    elif action == "rej":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"⚠️ **PAYMENT REJECTED**\n\n"
                     f"We could not verify your payment of Rs {amount}. "
                     f"Please ensure you uploaded a clear screenshot of a SUCCESSFUL transaction. "
                     f"If you believe this is an error, please contact our support team on the website.",
                parse_mode="Markdown"
            )
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n🔴 **STATUS: REJECTED ❌**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to message user {target_user_id}: {e}")




@asynccontextmanager
async def lifespan(app: FastAPI):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected, pattern="^pkg_")],
        states={
            WAITING_FOR_PROMO_DECISION: [CallbackQueryHandler(promo_action, pattern="^promo_")],
            WAITING_FOR_PROMO: [MessageHandler(filters.TEXT & ~filters.COMMAND, promo_received)],
            WAITING_FOR_SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot_received)],
            WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )
    
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(CommandHandler("help", help_command))
    ptb_app.add_handler(conv_handler)
    ptb_app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(app|rej)_"))

    
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/tgwebhook")
    logger.info(f"Webhook set successfully to: {WEBHOOK_URL}/tgwebhook")
    
    yield
    
    
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
    return {"status": "online", "platform": "FollowXchange Premium Bot"}
