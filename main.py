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

# Flask Server (Render အတွက် လိုအပ်သည်)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Database Initialization
def init_db():
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS movies (name TEXT PRIMARY KEY, msg_id INTEGER)')
    conn.commit()
    conn.close()

init_db() # Bot စတက်သည်နှင့် Database တည်ဆောက်ခြင်း

def get_db():
    return sqlite3.connect('movies.db', check_same_thread=False)

# Message ဖျက်ရန် Background Task
async def delete_after_delay(context, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel မှ အချက်အလက်သိမ်းခြင်း
    if update.channel_post and update.channel_post.chat.id == int(os.environ.get('DB_CHANNEL_ID', 0)):
        text = update.channel_
