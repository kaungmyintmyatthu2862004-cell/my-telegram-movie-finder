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

# Logging စနစ်ထည့်သွင်းခြင်း (Error စစ်ရန်)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Database
conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT, msg_id INTEGER)')
conn.commit()

# မက်ဆေ့ခ်ျဖျက်ပေးမည့် Background Task
async def delete_message_after_delay(context, chat_id, message_id):
    await asyncio.sleep(300) # 5 မိနစ်စောင့်
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"✅ မက်ဆေ့ခ်ျ {message_id} အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။")
    except Exception as e:
        logger.error(f"❌ မက်ဆေ့ခ်ျ {message_id} ဖျက်မရပါ (Error: {e})")

# 3. Bot Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel မှ အချက်အလက်သိမ်းရန်
    if update.channel_post and update.channel_post.chat.id == int(os.environ.get('DB_CHANNEL_ID', 0)):
        text = update.channel_post.caption or update.channel_post.text
        if text:
            first_line = text.split('\n')[0].strip()
            movie_name = re.sub(r'[^a-zA-Z0-9\s]', ' ', first_line).lower()
            movie_name = ' '.join(movie_name.split())
            
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    # Group မှ ရှာဖွေရန်
    if update.message and update.message.chat.id == int(os.environ.get('GROUP_ID', 0)):
        query = update.message.text.strip().lower()
        if not query: return
        
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        stop_words = ['ကြည့်ချင်တယ်', 'ပေးပါ', 'ရှာပေးပါ', 'လိုချင်တယ်', 'ကြည့်မယ်', 'ပို့ပေးပါ', 'ရုပ်ရှင်']
        for word in stop_words:
            clean_query = clean_query.replace(word, '')
        clean_query = ' '.join(clean_query.split())
        
        if not clean_query: return
        
        search_query = f"%{clean_query}%"
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်...")
            forwarded_msg = await context.bot.copy_message(
                chat_id=update.message.chat.id,
                from_chat_id=int(os.environ.get('DB_CHANNEL_ID', 0)),
                message_id=result[0]
            )
            
            # မက်ဆေ့ခ်ျဖျက်ခြင်း အပိုင်း
            try: await context.bot.delete_message(chat_id=update.message.chat.id, message_id=status_msg.message_id)
            except: pass
            
            asyncio.create_task(delete_message_after_delay(context, update.message.chat.id, forwarded_msg.message_id))
        else:
            await update.message.reply_text("ဒီ Movie ကို ရှာမတွေ့ပါရှင်။")

def run_bot():
    token = os.environ.get('TOKEN')
    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.ALL, handle_message))
    bot_app.run_polling(drop_pending_updates=True, poll_interval=0.1)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    run_bot()
        
