import os
import random
import logging
import re
import httpx
import edge_tts
from pyrogram import Client, filters, enums
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save

# --- LOGGER ---
logger = logging.getLogger("MariaAI")

# --- CONFIGURATION ---
GEMINI_KEY = getattr(config, "GEMINI_API_KEY", None)
# We use the raw URL now, bypassing the library issues
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

# --- VOICE SETTINGS ---
VOICE_MODEL = "hi-IN-SwaraNeural"
VOICE_RATE = "+5%"
VOICE_PITCH = "+15Hz"

chat_memory = {}

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Maria, a young Indian girl (girlfriend personality).
RULES:
1. Keep sentences SHORT (5-8 words).
2. Use Hinglish (Hindi + English).
3. Act naturally with fillers: "Hmm", "Achha", "Haan".
4. NEVER say you are an AI.
"""

async def generate_voice(text, chat_id):
    file_path = f"voice_{chat_id}.mp3"
    # Basic text cleaning
    clean_text = re.sub(r'[^\w\s,?.!-]', '', text)
    try:
        communicate = edge_tts.Communicate(clean_text, VOICE_MODEL, rate=VOICE_RATE, pitch=VOICE_PITCH)
        await communicate.save(file_path)
        return file_path
    except Exception as e:
        return None

def is_targeted(filter, client, message):
    if message.chat.type == enums.ChatType.PRIVATE: return True
    if message.mentioned: return True
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == client.me.id: return True
    return False

smart_filter = filters.create(is_targeted)

@app.on_message(filters.text & ~filters.bot & smart_filter, group=-5)
@error
@save
async def ai_chat_handler(client, message):
    if not GEMINI_KEY: return

    logger.info(f"📨 AI received message: {message.text[:20]}...") 

    chat_id = message.chat.id
    user_text = message.text
    if message.chat.type != enums.ChatType.PRIVATE:
        user_text = user_text.replace(f"@{client.me.username}", "").strip()
    if not user_text: return

    mode = "text" if random.random() < 0.6 else "voice"
    lower = user_text.lower()
    if any(x in lower for x in ["voice", "bol", "audio", "suno"]): mode = "voice"
    elif any(x in lower for x in ["text", "chat", "likh", "msg"]): mode = "text"

    await client.send_chat_action(chat_id, enums.ChatAction.RECORD_AUDIO if mode == "voice" else enums.ChatAction.TYPING)

    # --- RAW HTTP REQUEST (NO LIBRARY) ---
    try:
        # Simple memory handling
        if chat_id not in chat_memory: chat_memory[chat_id] = []
        
        # Add user message
        chat_memory[chat_id].append({"role": "user", "parts": [{"text": user_text}]})
        
        # Keep memory short (last 6 messages + prompt)
        context = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}] + chat_memory[chat_id][-6:]

        payload = {
            "contents": context,
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 200,
            }
        }

        async with httpx.AsyncClient(timeout=15) as http_client:
            response = await http_client.post(API_URL, json=payload)
            
            if response.status_code != 200:
                logger.error(f"API Error {response.status_code}: {response.text}")
                await message.reply("⚠️ AI is sleeping (API Error).")
                return

            data = response.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        logger.error(f"Request Failed: {e}")
        return

    # Add AI reply to memory
    chat_memory[chat_id].append({"role": "model", "parts": [{"text": raw_text}]})

    # Clean text logic (Simplified)
    clean_text = re.sub(r'\|.*?\|', '', raw_text).strip()
    clean_text = clean_text.replace("*", "")

    # Send Response
    try:
        if mode == "voice":
            v_path = await generate_voice(clean_text, chat_id)
            if v_path and os.path.exists(v_path):
                await message.reply_voice(v_path)
                os.remove(v_path)
            else:
                await message.reply(clean_text)
        else:
            await message.reply(clean_text)
    except Exception as e:
        logger.error(f"Send Error: {e}")

__module__ = "Chatbot"
__help__ = "**🗣️ Maria AI Chatbot**\nMaria talks in Hinglish voice & text."
