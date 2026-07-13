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
async def handle_message(
    
