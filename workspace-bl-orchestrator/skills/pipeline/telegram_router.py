import os
import config
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
except ImportError:
    pass

import config
import sqlite3
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN

logger = logging.getLogger("telegram_router")
logging.basicConfig(level=logging.INFO)

async def onboard_command(update, context):
    """Handles /onboard (Replaces backlink-onboarder)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    conn = config.get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS onboard_sessions (chat_id TEXT, user_id TEXT, step TEXT, PRIMARY KEY(chat_id, user_id))")
    c.execute("INSERT INTO onboard_sessions (chat_id, user_id, step) VALUES (%s, %s, %s)", (str(chat_id), str(user_id), "start"))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("Welcome to Hermes Onboarding! What is your project URL?")

async def handle_message(update, context):
    """Handles text messages for state progression."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    conn = config.get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS onboard_sessions (chat_id TEXT, user_id TEXT, step TEXT, PRIMARY KEY(chat_id, user_id))")
    c.execute("SELECT step FROM onboard_sessions WHERE chat_id=%s AND user_id=%s LIMIT 1", (str(chat_id), str(user_id)))
    row = c.fetchone()
    
    if row:
        step = row[0]
        if step == "start":
            project_url = update.message.text
            c.execute("UPDATE onboard_sessions SET step=%s WHERE chat_id=%s", ("complete", str(chat_id)))
            
            # Send confirmation with Inline Keyboard (Buttons)
            keyboard = [[InlineKeyboardButton("Confirm", callback_data=f"confirm_{project_url}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(f"Project URL set to {project_url}.", reply_markup=reply_markup)
        conn.commit()
    conn.close()

async def handle_callback(update, context):
    """Handles inline keyboard button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("confirm_"):
        project = query.data.split("confirm_")[1]
        await query.edit_message_text(text=f"Project {project} formally confirmed via Hermes!")

async def handle_document(update, context):
    """Handles file uploads (e.g., config jsons)."""
    file_id = update.message.document.file_id
    logger.info(f"Received document upload with ID: {file_id}")
    await update.message.reply_text("File upload received and routed natively via Hermes.")

def main():
    logger.info("Starting native Python Telegram Webhook Receiver...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("onboard", onboard_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == '__main__':
    main()
