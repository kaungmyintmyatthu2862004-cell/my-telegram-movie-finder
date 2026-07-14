import os
import sqlite3
import asyncio
import threading
import time
import re
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Render မှာ Data ပျောက်ခြင်းမှ ကာကွယ်ရန် Temporary Storage ကို သုံးပါ
DB_PATH = '/tmp/movies.db'

# Flask Server (Render အတွက် လိုအပ်သည်)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Database Initialization
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT PRIMARY KEY, msg_id INTEGER)')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully at /tmp/movies.db")
    except Exception as e:
        logger.error(f"Database Init Error: {e}")

init_db()

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# Message ဖျက်ရန် Background Task
async def delete_after_delay(context, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Environment Variables စစ်ဆေးခြင်း
    DB_CHANNEL_ID = os.environ.get('DB_CHANNEL_ID')
    GROUP_ID = os.environ.get('GROUP_ID')
    
    if not DB_CHANNEL_ID or not GROUP_ID:
        logger.error("DB_CHANNEL_ID သို့မဟုတ် GROUP_ID မရှိပါ")
        return

    # Channel မှ အချက်အလက်သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == int(DB_CHANNEL_ID):
        text = update.channel_post.caption or update.channel_post.text
        if text:
            first_line = text.split('\n')[0].strip()
            movie_name = re.sub(r'[^a-zA-Z0-9\s]', ' ', first_line).lower()
            movie_name = ' '.join(movie_name.split())
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', (movie_name, update.channel_post.message_id))
            conn.commit()
            conn.close()
        return

    # Group မှ ရှာဖွေခြင်း
    if update.message and update.message.chat.id == int(GROUP_ID):
        query = update.message.text.strip().lower()
        if not query: return
        
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        stop_words = ['ကြည့်ချင်တယ်', 'ပေးပါ', 'ရှာပေးပါ', 'လိုချင်တယ်', 'ကြည့်မယ်', 'ပို့ပေးပါ', 'ရုပ်ရှင်']
        for word in stop_words: clean_query = clean_query.replace(word, ' ')
        clean_query = ' '.join(clean_query.split())
        
        if not clean_query: return
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (f"%{clean_query}%",))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်🔎...")
            await asyncio.sleep(2) 
            
            try: await context.bot.delete_message(chat_id=update.message.chat.id, message_id=status_msg.message_id)
            except: pass
            
            try:
                forwarded_msg = await context.bot.copy_message(
                    chat_id=update.message.chat.id,
                    from_chat_id=int(DB_CHANNEL_ID),
                    message_id=result[0]
                )
                asyncio.create_task(delete_after_delay(context, update.message.chat.id, forwarded_msg.message_id, 300))
            except Exception as e:
                logger.error(f"Forward Error: {e}")
        else:
            await update.message.reply_text("ဒီ Movie ကို ရှာမတွေ့ပါရှင်။")

def run_bot():
    TOKEN = os.environ.get('TOKEN')
    if not TOKEN:
        logger.error("TOKEN မရှိပါ! Environment Variable တွင် စစ်ဆေးပါ။")
        return
    
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.ALL, handle_message))
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    run_bot()
