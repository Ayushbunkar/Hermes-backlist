import os
import config
import logging
import whitelist_db as wdb
import backlink_db as bdb

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
except ImportError:
    pass

import config
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
    try:
        c.execute("INSERT INTO onboard_sessions (chat_id, user_id, step) VALUES (%s, %s, %s)", (str(chat_id), str(user_id), "start"))
    except Exception:
        # If session exists, rollback the failed insert and update it instead
        conn.rollback()
        c.execute("UPDATE onboard_sessions SET step=%s WHERE chat_id=%s AND user_id=%s", ("start", str(chat_id), str(user_id)))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("Welcome to Hermes Onboarding! What is your project URL%s")

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
        step = row["step"]
        if step == "start":
            project_url = update.message.text
            c.execute("UPDATE onboard_sessions SET step=%s WHERE chat_id=%s", ("complete", str(chat_id)))
            
            # Send confirmation with Inline Keyboard (Buttons)
            keyboard = [[InlineKeyboardButton("Confirm", callback_data=f"confirm_{project_url}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(f"Project URL set to {project_url}.", reply_markup=reply_markup)
        conn.commit()
    else:
        import subprocess
        import sys
        import os
        script_path = os.path.join(os.path.dirname(__file__), "handle_card_feedback.py")
        subprocess.Popen([
            sys.executable,
            script_path,
            "--message-text", update.message.text,
            "--chat-id", str(chat_id),
            "--user-id", str(user_id),
            "--username", update.effective_user.username or "",
            "--reply-to-message-id", str(update.message.message_id)
        ])
    conn.close()

async def handle_callback(update, context):
    """Handles inline keyboard button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("confirm_"):
        project = query.data.split("confirm_")[1]
        
        import whitelist_db as wdb
        import config
        wdb.init_whitelist_db(config.BL_DB_PATH)
        name = project.split("://")[-1] if "://" in project else project
        pid = wdb.upsert_project(project, niche="auto", name=name)
        
        # Seed default whitelist domains so the daemon actually has sites to scan
        default_sites = ["reddit.com", "news.ycombinator.com", "bitcointalk.org"]
        for site in default_sites:
            wdb.upsert_whitelist_site(pid, site, added_by="seed", db_path=config.BL_DB_PATH)
        
        if project.startswith("pdf://"):
            conn = config.get_db_connection()
            c = conn.cursor()
            c.execute("SELECT content FROM pdf_cache WHERE project_url=%s", (project,))
            row = c.fetchone()
            if row:
                pdf_text = row["content"]
                wdb.update_project_config(project, {"pdf_context": pdf_text}, db_path=config.BL_DB_PATH)
                c.execute("SELECT id FROM projects WHERE project_url=%s", (project,))
                pid_row = c.fetchone()
                if pid_row:
                    import vocab_miner
                    vocab_miner.seed_pdf_vocab_with_ai(pid_row["id"], pdf_text, db_path=config.BL_DB_PATH)
            conn.close()
            
        await query.edit_message_text(text=f"Project {project} formally confirmed and initialized via Hermes!")
    elif query.data.startswith("bl_"):
        import subprocess
        import sys
        import os
        script_path = os.path.join(os.path.dirname(__file__), "handle_card_feedback.py")
        subprocess.Popen([
            sys.executable,
            script_path,
            "--payload", query.data,
            "--chat-id", str(update.effective_chat.id),
            "--user-id", str(update.effective_user.id),
            "--username", update.effective_user.username or "",
            "--reply-to-message-id", str(query.message.message_id)
        ])

async def handle_document(update, context):
    """Handles file uploads (e.g., config jsons, PDFs)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    conn = config.get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS onboard_sessions (chat_id TEXT, user_id TEXT, step TEXT, PRIMARY KEY(chat_id, user_id))")
    c.execute("SELECT step FROM onboard_sessions WHERE chat_id=%s AND user_id=%s LIMIT 1", (str(chat_id), str(user_id)))
    row = c.fetchone()
    
    if row and row["step"] == "start":
        doc = update.message.document
        if not doc.file_name.lower().endswith(".pdf"):
            await update.message.reply_text("Please send a valid PDF file.")
            conn.close()
            return
            
        await update.message.reply_text("Downloading and reading PDF... Please wait.")
        
        file = await context.bot.get_file(doc.file_id)
        file_path = f"/tmp/{doc.file_name}"
        await file.download_to_drive(file_path)
        
        import PyPDF2
        text = ""
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for i in range(min(10, len(reader.pages))):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        text += page_text + "\\n"
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            await update.message.reply_text("Could not read this PDF. Please send a valid file or a URL.")
            conn.close()
            return
            
        c.execute("UPDATE onboard_sessions SET step=%s WHERE chat_id=%s", ("complete", str(chat_id)))
        project_url = f"pdf://{doc.file_name}"
        
        c.execute("CREATE TABLE IF NOT EXISTS pdf_cache (project_url TEXT PRIMARY KEY, content TEXT)")
        c.execute("DELETE FROM pdf_cache WHERE project_url=%s", (project_url,))
        c.execute("INSERT INTO pdf_cache (project_url, content) VALUES (%s, %s)", (project_url, text))
        conn.commit()
        conn.close()
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("Confirm PDF Project", callback_data=f"confirm_{project_url}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"PDF '{doc.file_name}' read successfully ({len(text)} characters). Shall we proceed%s", reply_markup=reply_markup)
    else:
        conn.close()
        file_id = update.message.document.file_id
        logger.info(f"Received document upload with ID: {file_id}")
        await update.message.reply_text("File upload received and routed natively via Hermes.")

async def add_command(update, context):
    """Handles /add <url> <niche>"""
    if not context.args:
        await update.message.reply_text("Usage: /add <project_url> [niche]")
        return
    project = context.args[0]
    niche = " ".join(context.args[1:]) if len(context.args) > 1 else "auto"
    
    try:
        wdb.init_whitelist_db(config.BL_DB_PATH)
        name = project.split("://")[-1] if "://" in project else project
        pid = wdb.upsert_project(project, niche=niche, name=name)
        
        default_sites = ["reddit.com", "news.ycombinator.com", "bitcointalk.org"]
        for site in default_sites:
            wdb.upsert_whitelist_site(pid, site, added_by="seed", db_path=config.BL_DB_PATH)
            
        await update.message.reply_text(f"✅ Project {project} added successfully! Niche set to: {niche}. Tracking started.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding project: {e}")

async def projects_command(update, context):
    """Handles /projects"""
    try:
        wdb.init_whitelist_db(config.BL_DB_PATH)
        projects = wdb.get_active_projects(config.BL_DB_PATH)
        if not projects:
            await update.message.reply_text("No active projects found.")
            return
        
        msg = "📊 Active Projects:\n\n"
        for p in projects:
            msg += f"🔹 {p['project_url']}\n   Niche: {p['niche']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching projects: {e}")

async def delete_command(update, context):
    """Handles /delete <url>"""
    if not context.args:
        await update.message.reply_text("Usage: /delete <project_url>")
        return
    project = context.args[0]
    try:
        wdb.init_whitelist_db(config.BL_DB_PATH)
        wdb.delete_project(project, config.BL_DB_PATH)
        await update.message.reply_text(f"🗑️ Project {project} has been deleted.")
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting project: {e}")

async def scan_command(update, context):
    """Handles /scan"""
    try:
        wdb.init_whitelist_db(config.BL_DB_PATH)
        projects = wdb.get_active_projects(config.BL_DB_PATH)
        total_due = 0
        for p in projects:
            total_due += wdb.set_project_sites_due_now(p["id"], config.BL_DB_PATH)
        
        await update.message.reply_text(f"🔍 Scan triggered! Marked {total_due} sources as due now. The orchestrator will pick them up shortly.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error triggering scan: {e}")

async def stats_command(update, context):
    """Handles /stats"""
    try:
        conn = config.get_db_connection()
        c = conn.cursor()
        
        wdb.init_whitelist_db(config.BL_DB_PATH)
        projects = wdb.get_active_projects(config.BL_DB_PATH)
        
        c.execute("SELECT status, count(*) FROM harvest_leads GROUP BY status")
        rows = c.fetchall()
        
        stats = {r["status"]: r["count"] for r in rows}
        total = sum(stats.values())
        
        msg = "📈 Hermes Global Stats\n\n"
        msg += f"Active Projects: {len(projects)}\n"
        msg += f"Total Leads Found: {total}\n"
        msg += f"Approved & Drafted: {stats.get('DRAFTED', 0) + stats.get('SENT', 0)}\n"
        msg += f"Pending Review: {stats.get('SCORED', 0) + stats.get('GATED', 0)}\n"
        msg += f"Rejected: {stats.get('REJECTED', 0)}\n"
        
        await update.message.reply_text(msg)
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching stats: {e}")

def main():
    logger.info("Starting native Python Telegram Webhook Receiver...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("onboard", onboard_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("projects", projects_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == '__main__':
    main()
