import sqlite3
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = "8942001881:AAER0JVXXlkSiH8B1Ff3N0vRVoW5du8D7sY"
GROUP_ID = -1003906056351
DB_CHANNEL_ID = -1004438806546

conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT, msg_id INTEGER)')
conn.commit()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Database သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == DB_CHANNEL_ID:
        text = update.channel_post.caption or update.channel_post.text
        if text:
            movie_name = text.split('\n')[0].strip().lower()
            cursor.execute('INSERT OR REPLACE INTO movies (name, msg_id) VALUES (?, ?)', 
                           (movie_name, update.channel_post.message_id))
            conn.commit()
        return

    # 2. Group ထဲမှ ရှာဖွေခြင်း
    if update.message and update.message.chat.id == GROUP_ID:
        query = update.message.text.strip().lower()
        search_query = '%' + '%'.join(query.split()) + '%'
        
        cursor.execute('SELECT msg_id FROM movies WHERE name LIKE ?', (search_query,))
        result = cursor.fetchone()
        
        if result:
            # ရှာဖွေနေကြောင်း စာပို့ခြင်း
            status_msg = await update.message.reply_text("ရုပ်ရှင်ရှာဖွေနေပါတယ်🔎 ခနစောင့်ပေးပါ🎬🍿 ...")
            
            # စာကို ၅ စက္ကန့်နေရင် ဖျက်ရန် (အရင်ကအတိုင်း)
            await asyncio.sleep(5)
            try:
                await context.bot.delete_message(chat_id=GROUP_ID, message_id=status_msg.message_id)
            except:
                pass
                
            # ရုပ်ရှင် ပို့ခြင်း
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
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot is running...")
    app.run_polling()
