import os
import sqlite3
import asyncio
import threading
import time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# 2. Database
conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT, msg_id INTEGER)')
conn.commit()

# 3. Bot Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == int(os.environ.get('DB_CHANNEL_ID', 0)):
        text = update.channel_post.caption or update.channel_post.text
        if text:
            movie_name = text.split('\n')[0].strip().lower()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    if update.message and update.message.chat.id == int(os.environ.get('GROUP_ID', 0)):
        query = update.message.text.strip().lower()
        if not query: return
        search_query = '%' + '%'.join(query.split()) + '%'
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်...")
            forwarded_msg = await context.bot.copy_message(
                chat_id=update.message.chat.id,
                from_chat_id=int(os.environ.get('DB_CHANNEL_ID', 0)),
                message_id=result[0]
            )
            await context.bot.delete_message(chat_id=update.message.chat.id, message_id=status_msg.message_id)
            await asyncio.sleep(300)
            try: await context.bot.delete_message(chat_id=update.message.chat.id, message_id=forwarded_msg.message_id)
            except: pass
        else:
            await update.message.reply_text("ဒီ Movie ကို မတွေ့ရှိပါရှင်။")

# 4. Running Logic
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    token = os.environ.get('TOKEN')
    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.ALL, handle_message))
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    # Flask ကို Background Thread နဲ့အရင် စတင်ပါ
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3) # Flask အလုပ်လုပ်ဖို့ အချိန်ခဏပေးပါ
    # Bot ကို Main Process မှာ စတင်ပါ
    run_bot()
