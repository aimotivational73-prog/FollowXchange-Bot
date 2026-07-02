import os
import uuid
import logging
from datetime import datetime
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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- PROMO CODES CONFIGURATION ---
PROMO_CODES = {
    "WELCOME20": {"discount_percent": 15, "active": True, "valid_until": "2026-12-31", "min_amount": 69},
    "FESTIVAL10": {"discount_percent": 5, "active": True, "valid_until": "2026-12-31", "min_amount": 69},
}

# --- PACKAGES CONFIGURATION (Managed via Admin Commands) ---
PACKAGES = {
    100: 19,
    200: 29,
    300: 49,
    500: 69,
    1000: 119,
    2500: 249,
    5000: 499
}

WEBSITE_URL = "https://followxchange.store"
INSTAGRAM_PAGE = "https://www.instagram.com/followxchangeofcl?igsh=MWpha3o5ODNpYXNmZQ=="

LEGAL_FOOTER = (
    "\n\n⚖️ *Legal & Privacy Agreement:*\n"
    "By proceeding with this transaction, you acknowledge and agree to our "
    f"[Terms & Conditions]({WEBSITE_URL}/terms-conditions.html), "
    f"[Privacy Policy]({WEBSITE_URL}/privacy-policy.html), and "
    f"[Refund Policy]({WEBSITE_URL}/refund-policy.html).\n"
    "⚠️ *Disclaimer:* FollowXchange is a 3rd-party growth service and is strictly NOT affiliated with, endorsed by, or connected to Instagram or Meta Platforms Inc."
)

WAITING_FOR_PROMO_DECISION, WAITING_FOR_PROMO, WAITING_FOR_SCREENSHOT, WAITING_FOR_USERNAME = range(4)

ptb_app = Application.builder().token(BOT_TOKEN).build()


# ==========================================
#        ADMIN CONTROL COMMANDS
# ==========================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows all admin commands (Only works for Admin)."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    text = (
        "🛠 **ADMIN CONTROL PANEL** 🛠\n\n"
        "**🎫 PROMO CODES:**\n"
        "➕ Add: `/addpromo <CODE> <DISCOUNT_%> <YYYY-MM-DD> <MIN_RS>`\n"
        "❌ Del: `/delpromo <CODE>`\n"
        "📋 List: `/listpromo`\n\n"
        "**📦 FOLLOWER PACKAGES:**\n"
        "➕ Add/Edit: `/addpkg <FOLLOWERS> <PRICE_RS>`\n"
        "❌ Del: `/delpkg <FOLLOWERS>`\n"
        "📋 List: `/listpkg`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- PROMO COMMANDS ---
async def add_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    try:
        code = context.args[0].upper()
        discount = int(context.args[1])
        valid_until = context.args[2]
        min_amount = float(context.args[3])
        datetime.strptime(valid_until, "%Y-%m-%d") # Verify date format
        PROMO_CODES[code] = {"discount_percent": discount, "active": True, "valid_until": valid_until, "min_amount": min_amount}
        await update.message.reply_text(f"✅ **Promo Added!**\nCode: `{code}`\nDiscount: {discount}%\nValid till: {valid_until}\nMin Order: Rs {min_amount}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Usage: `/addpromo <CODE> <DISCOUNT> <YYYY-MM-DD> <MIN_AMOUNT>`", parse_mode="Markdown")

async def del_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    try:
        code = context.args[0].upper()
        if code in PROMO_CODES:
            del PROMO_CODES[code]
            await update.message.reply_text(f"🗑️ Promo code `{code}` deleted successfully!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Code `{code}` not found.", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Usage: `/delpromo <CODE>`", parse_mode="Markdown")

async def list_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    if not PROMO_CODES:
        await update.message.reply_text("No active promo codes right now.")
        return
    text = "🎟 **Active Promo Codes:**\n\n"
    for code, data in PROMO_CODES.items():
        text += f"▪️ **{code}** - {data['discount_percent']}% off (Min Rs {data['min_amount']}) | Till: {data['valid_until']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# --- PACKAGE COMMANDS ---
async def add_pkg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    try:
        followers = int(context.args[0])
        price = int(context.args[1])
        PACKAGES[followers] = price
        await update.message.reply_text(f"✅ **Package Updated!**\n📦 Followers: {followers}\n💰 Price: Rs {price}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Usage: `/addpkg <FOLLOWERS> <PRICE>`\nExample: `/addpkg 10000 899`", parse_mode="Markdown")

async def del_pkg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    try:
        followers = int(context.args[0])
        if followers in PACKAGES:
            del PACKAGES[followers]
            await update.message.reply_text(f"🗑️ Package for `{followers}` followers deleted!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Package for `{followers}` not found.", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Usage: `/delpkg <FOLLOWERS>`", parse_mode="Markdown")

async def list_pkg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID: return
    if not PACKAGES:
        await update.message.reply_text("No active packages.")
        return
    text = "📦 **Active Follower Packages:**\n\n"
    for followers in sorted(PACKAGES.keys()):
        text += f"▪️ **{followers} Followers** - Rs {PACKAGES[followers]}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


# ==========================================
#          USER FACING BOT LOGIC
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends premium welcome message with 2 initial options."""
    keyboard = [
        [InlineKeyboardButton("🛒 View Follower Packages", callback_data="show_packages")],
        [InlineKeyboardButton("ℹ️ Help & Support", callback_data="help_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🌟 **Welcome to the Premium FollowXchange Bot!** 🌟\n\n"
        "Grow your Instagram presence securely with our high-quality, authentic followers.\n\n"
        "🔥 *Pro Tip:* Follow our [Instagram Page]({INSTAGRAM_PAGE}) for daily exclusive Promo Codes!\n\n"
        "Please select an option below to get started:\n"
        f"{LEGAL_FOOTER}"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides usage instructions."""
    help_text = (
        "ℹ️ **How to buy followers securely:**\n\n"
        "1️⃣ Select a package from the menu.\n"
        "2️⃣ Apply a Promo Code (if valid) to get a discount.\n"
        "3️⃣ Complete payment using UPI.\n"
        "4️⃣ Upload payment screenshot here.\n"
        "5️⃣ Enter your App username for delivery.\n\n"
        "🔥 *Follow us on Instagram for Daily Promo Codes:* "
        f"[Click Here to Follow]({INSTAGRAM_PAGE})\n\n"
        f"Support: {WEBSITE_URL}"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown", disable_web_page_preview=True)
    elif update.callback_query:
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_home")]]
        await update.callback_query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dynamically loads packages from the PACKAGES dictionary."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_packages":
        keyboard = []
        # Sort and dynamically generate the buttons based on admin's list
        for followers in sorted(PACKAGES.keys()):
            price = PACKAGES[followers]
            keyboard.append([InlineKeyboardButton(f"🛒 {followers} Followers (Rs {price})", callback_data=f"pkg_{followers}_{price}")])
            
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_home")])
        
        await query.edit_message_text("📦 **Select your preferred package:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif query.data == "help_info":
        await help_command(update, context)
    elif query.data == "back_home":
        await start(update, context)

async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await query.edit_message_text(f"📦 **Order ID:** {context.user_data['order_id']}\nSelected: {followers_count} Followers for Rs {amount}.\n\n💡 Do you have a promo code?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return WAITING_FOR_PROMO_DECISION

async def promo_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "promo_yes":
        await query.edit_message_text("🎟 **Enter your Promo Code:**\n\n*(Check our Instagram stories for daily codes!)*", parse_mode="Markdown")
        return WAITING_FOR_PROMO
    else:
        context.user_data["final_amount"] = context.user_data["original_amount"]
        context.user_data["promo_applied"] = "None"
        return await show_payment_details(update, context, is_query=True)

async def promo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    if code.lower() == 'skip':
        context.user_data["final_amount"] = context.user_data["original_amount"]
        context.user_data["promo_applied"] = "None"
        return await show_payment_details(update, context, is_query=False)

    orig_amount = context.user_data["original_amount"]
    
    # 1. Check if Code exists & Active
    if code in PROMO_CODES and PROMO_CODES[code]["active"]:
        # 2. Date Check
        exp_date = datetime.strptime(PROMO_CODES[code]["valid_until"], "%Y-%m-%d")
        if datetime.now() > exp_date:
            await update.message.reply_text("❌ **Code Expired.** Check our Instagram for fresh codes!", parse_mode="Markdown")
            return WAITING_FOR_PROMO
        
        # 3. Min Amount Check
        if orig_amount <= PROMO_CODES[code]["min_amount"]:
            await update.message.reply_text(f"❌ **Minimum order required is Rs {PROMO_CODES[code]['min_amount'] + 1}.**\nAdd more followers to use this code!", parse_mode="Markdown")
            return WAITING_FOR_PROMO
        
        # Apply Discount
        discount = PROMO_CODES[code]["discount_percent"]
        final_amount = orig_amount - (orig_amount * (discount / 100))
        context.user_data["final_amount"] = round(final_amount, 2)
        context.user_data["promo_applied"] = code
        await update.message.reply_text(f"🎉 **Promo Code Accepted!**\nNew Total: **Rs {context.user_data['final_amount']}**.", parse_mode="Markdown")
        return await show_payment_details(update, context, is_query=False)
    else:
        await update.message.reply_text(f"❌ **Invalid Promo Code.**\n*Follow our [Instagram]({INSTAGRAM_PAGE}) for daily codes!*", parse_mode="Markdown", disable_web_page_preview=True)
        return WAITING_FOR_PROMO

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query=False):
    amount = context.user_data.get("final_amount")
    followers = context.user_data.get("selected_followers")
    order_id = context.user_data.get("order_id")
    upi_url = f"upi://pay?pa={UPI_ID}&pn=FollowXchange&am={amount}&cu=INR&tr={order_id}"
    
    text = f"🧾 **SECURE CHECKOUT**\n🆔 `{order_id}`\n📦 {followers} Followers\n💰 **Rs {amount}**\n\n💳 **UPI:** `{UPI_ID}`\n[Pay Now via UPI App]({upi_url})\n\n📸 *After payment, upload the screenshot.*\n{LEGAL_FOOTER}"
    if is_query: await update.callback_query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    else: await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    return WAITING_FOR_SCREENSHOT

async def screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["screenshot_file_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ **Screenshot Received.**\n\n⏳ *Verification usually takes 5 mins - 2 hours (up to 24 hours max).*\n\n⌨️ Enter your **App Username**:")
    return WAITING_FOR_USERNAME

async def username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fx_username = update.message.text.strip()
    user_chat_id = update.message.chat_id
    followers_count = context.user_data.get("selected_followers", "Unknown")
    amount = context.user_data.get("final_amount", "Unknown")
    order_id = context.user_data.get("order_id", "Unknown")
    promo = context.user_data.get("promo_applied", "None")
    
    await update.message.reply_text(f"✅ **Order {order_id} Submitted!**\nWe will notify you here once approved.")
    
    admin_keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_chat_id}_{amount}_{followers_count}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_chat_id}_{amount}")]]
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=context.user_data["screenshot_file_id"], caption=f"🚨 **NEW ORDER**\nOrder: {order_id}\nUser: {fx_username}\nAmount: Rs {amount}\nPromo: {promo}", reply_markup=InlineKeyboardMarkup(admin_keyboard))
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("❌ Cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def admin_decision(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, target_user_id, amount = data[0], int(data[1]), data[2]
    if action == "app":
        followers_count = data[3]
        await context.bot.send_message(chat_id=target_user_id, text=f"🥳 **PAYMENT APPROVED!**\n\nYour {followers_count} Followers (Rs {amount}) order is confirmed!")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n🟢 **APPROVED ✅**")
    else:
        await context.bot.send_message(chat_id=target_user_id, text="⚠️ **PAYMENT REJECTED**\n\nScreenshot verification failed. Please contact support.")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n🔴 **REJECTED ❌**")

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
    
    # Admin Management Commands
    ptb_app.add_handler(CommandHandler("admin", admin_panel))
    ptb_app.add_handler(CommandHandler("addpromo", add_promo))
    ptb_app.add_handler(CommandHandler("delpromo", del_promo))
    ptb_app.add_handler(CommandHandler("listpromo", list_promo))
    ptb_app.add_handler(CommandHandler("addpkg", add_pkg))
    ptb_app.add_handler(CommandHandler("delpkg", del_pkg))
    ptb_app.add_handler(CommandHandler("listpkg", list_pkg))
    
    ptb_app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^(show_packages|help_info|back_home)$"))
    ptb_app.add_handler(conv_handler)
    ptb_app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(app|rej)_"))
    
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/tgwebhook")
    yield
    await ptb_app.stop()
    await ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)
@app.post("/tgwebhook")
async def handle_webhook(request: Request):
    json_data = await request.json()
    await ptb_app.process_update(Update.de_json(json_data, ptb_app.bot))
    return Response(status_code=200)
