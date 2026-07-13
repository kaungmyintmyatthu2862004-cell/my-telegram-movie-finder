import os
import sqlite3
import asyncio
import threading
import time
import re
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

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

# 5 မိနစ်နေမှ Message ဖျက်ပေးမည့် Background Task
async def delete_message_after_delay(context, chat_id, message_id):
    await asyncio.sleep(300)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# 3. Bot Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel ထဲက Post များကို Database ထဲ သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == int(os.environ.get('DB_CHANNEL_ID', 0)):
        text = update.channel_post.caption or update.channel_post.text
        if text:
            movie_name = text.split('\n')[0].strip().lower()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    # Group ထဲမှ ရှာဖွေခြင်း
    if update.message and update.message.chat.id == int(os.environ.get('GROUP_ID', 0)):
        query = update.message.text.strip().lower()
        if not query: return
        
        # စာလုံးပိုများ ("ကြည့်ချင်တယ်" စသည်) ဖယ်ထုတ်ပြီး နာမည်သန့်စင်ခြင်း
        words = re.sub(r'[*_`~()\[\]]', ' ', query).split()
        stop_words = ['ကြည့်ချင်တယ်', 'ပေးပါ', 'ရှာပေးပါ', 'လိုချင်တယ်', 'ကြည့်မယ်', 'ကြည့်ချင်']
        filtered_words = [w for w in words if w not in stop_words]
        search_query = '%' + '%'.join(filtered_words) + '%'
        
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်🔎...")
            forwarded_msg = await context.bot.copy_message(
                chat_id=update.message.chat.id,
                from_chat_id=int(os.environ.get('DB_CHANNEL_ID', 0)),
                message_id=result[0]
            )
            try: await context.bot.delete_message(chat_id=update.message.chat.id, message_id=status_msg.message_id)
            except: pass
            
            # ၅ မိနစ်နေရင် ဖျက်ရန် Background Task
            asyncio.create_task(delete_message_after_delay(context, update.message.chat.id, forwarded_msg.message_id))
        else:
            await update.message.reply_text("ဒီ Movie ကို မတွေ့ရှိပါရှင်။")

def run_bot():
    token = os.environ.get('TOKEN')
    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.ALL, handle_message))
    bot_app.run_polling(drop_pending_updates=True, poll_interval=0.1)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    run_bot()
                                     
