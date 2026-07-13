import os
import sqlite3
import asyncio
import threading
import time
import re
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Flask Web Server (Render အတွက် Port ဖွင့်ပေးရန်)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Database ချိတ်ဆက်ခြင်း
conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT, msg_id INTEGER)')
conn.commit()

# 3. Bot Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel ထဲက Post များကို Database ထဲ သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == int(os.environ.get('DB_CHANNEL_ID', 0)):
        text = update.channel_post.caption or update.channel_post.text
        if text:
            # Channel မှ နာမည်ကို သန့်စင်ပြီး သိမ်းဆည်းရန်
            movie_name = text.split('\n')[0].strip().lower()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    # Group ထဲမှ ရှာဖွေခြင်း
    if update.message and update.message.chat.id == int(os.environ.get('GROUP_ID', 0)):
        query = update.message.text.strip().lower()
        if not query: return
        
        # [အရေးကြီး] User ပို့လိုက်တဲ့စာထဲက Effect များနှင့် သင်္ကေတများအားလုံးကို ဖြုတ်ပေးခြင်း
        # ဥပမာ - *Bold*, (2022), [2022] စသည်တို့ကို ဖယ်ရှားပြီး space ဖြင့် အစားထိုးခြင်း
        clean_query = re.sub(r'[*_`~()\[\]]', ' ', query)
        search_query = '%' + '%'.join(clean_query.split()) + '%'
        
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်🔎...")
            forwarded_msg = await context.bot.copy_message(
                chat_id=update.message.chat.id,
                from_chat_id=int(os.environ.get('DB_CHANNEL_ID', 0)),
                message_id=result[0]
            )
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=status_msg.message_id)
            except:
                pass
            
            # Post ကို ၅ မိနစ်နေရင် ဖျက်ရန်
            await asyncio.sleep(300)
            try:
                await context.bot.delete_message(chat_id=update.message.chat.id, message_id=forwarded_msg.message_id)
            except:
                pass
        else:
            await update.message.reply_text("ဒီ Movie ကို မတွေ့ရှိပါရှင်။")

def run_bot():
    token = os.environ.get('TOKEN')
    if not token:
        print("Error: TOKEN environment variable is not set!")
        return
    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot is running...")
    # Polling ကို မြန်စေရန် poll_interval ကို 0.1 သို့ ထားရှိသည်
    bot_app.run_polling(drop_pending_updates=True, poll_interval=0.1)

if __name__ == '__main__':
    # Flask ကို Background Thread နဲ့အရင် စတင်ပါ
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3) # Flask အလုပ်လုပ်ဖို့ အချိန်ခဏပေးပါ
    # Bot ကို Main Thread မှာ စတင်ပါ
    run_bot()
            
