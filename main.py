import os
import sqlite3
import asyncio
from flask import Flask
from threading import Thread
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

# Flask ကို Thread အနေနဲ့ စတင်ခြင်း
Thread(target=run_flask).start()

# 2. Configuration (Environment Variables မှ ခေါ်ယူခြင်း)
TOKEN = os.environ.get('TOKEN')
GROUP_ID = int(os.environ.get('GROUP_ID'))
DB_CHANNEL_ID = int(os.environ.get('DB_CHANNEL_ID'))

# 3. Database
conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT, msg_id INTEGER)')
conn.commit()

# 4. Bot Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Database ထဲ သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == DB_CHANNEL_ID:
        text = update.channel_post.caption or update.channel_post.text
        if text:
            movie_name = text.split('\n')[0].strip().lower()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    # Group ထဲမှ ရှာဖွေခြင်း
    if update.message and update.message.chat.id == GROUP_ID:
        query = update.message.text.strip().lower()
        search_query = '%' + '%'.join(query.split()) + '%'
        
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်🔎 ခနစောင့်ပေးပါ🎬🍿 ...")
            await asyncio.sleep(5)
            try:
                await context.bot.delete_message(chat_id=GROUP_ID, message_id=status_msg.message_id)
            except:
                pass
                
            forwarded_msg = await context.bot.copy_message(
                chat_id=GROUP_ID,
                from_chat_id=DB_CHANNEL_ID,
                message_id=result[0]
            )
            
            # Forward လုပ်ထားတဲ့ Post ကို ၅ မိနစ် (၃၀၀ စက္ကန့်) စောင့်ပြီး ဖျက်ရန်
            await asyncio.sleep(300)
            try:
                await context.bot.delete_message(chat_id=GROUP_ID, message_id=forwarded_msg.message_id)
            except Exception as e:
                print(f"Error deleting movie post: {e}")
        else:
            await update.message.reply_text("ဒီ Movie ကို မတွေ့ရှိပါရှင်။")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TOKEN environment variable is not set!")
    else:
        bot_app =
            
