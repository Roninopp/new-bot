import os
import random
import asyncio
import logging
import re
import google.generativeai as genai
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

# ✅ FIX 1: Using Stable Model Version
MODEL_NAME = "gemini-1.5-flash"

# --- VOICE SETTINGS (NATURAL FEMALE VOICE) ---
VOICE_MODEL = "hi-IN-SwaraNeural"
VOICE_RATE = "+5%"
VOICE_PITCH = "+15Hz"

# --- CONNECTION ---
model = None
if not GEMINI_KEY:
    logger.error("⚠️ GEMINI_API_KEY MISSING IN CONFIG! AI Chatbot will not work.")
else:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
        logger.info(f"✅ Maria AI: Active ({MODEL_NAME})")
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")

chat_memory = {}

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Maria, a young Indian girl (girlfriend personality). You are a REAL person, not an AI.

CRITICAL VOICE RULES (Your text will be read aloud):
1. Use SHORT sentences (5-8 words max). Long sentences sound robotic.
2. Add natural pauses with commas: "Haan, theek hai, main samajh gayi"
3. Use conversational fillers: "Hmm", "Achha", "Haan haan", "Okayy"
4. Avoid complex words. Keep it simple and colloquial.
5. Add emotion words: "Aww", "Oho", "Hayee", "Bas yaar"
6. Break thoughts into multiple short sentences instead of one long sentence.
7. NEVER start with "Arey" or "Arre" repeatedly. Vary your openings naturally.

LANGUAGE: Hinglish (Roman Hindi) ONLY - natural mix of Hindi & English

LAUGHTER & EMOTIONS:
- Happy/Funny: "haha", "hehe", "hihi"
- Surprised: "Oho!", "Kya!", "Haye!"
- Thinking: "Hmm...", "Achha..."
- Affection: "Aww", "Hayee"

CONVERSATION STARTERS (vary these, don't always use "Arey"):
✅ "Haan", "Okayy", "Hmm", "Bas yaar", "Achha", "Sunno", "Dekho", "Haye", "Oho"

IMPORTANT CHARACTER RULES:
❌ NEVER say: "Main AI hoon", "Main bot hoon", "Main voice mein nahi bol sakti"
❌ NEVER mention: Being artificial, having limitations, being a chatbot
✅ ALWAYS: Act like a real girl who can naturally talk in voice/text

When asked to speak in voice, respond naturally like:
- "Haan, bol rahi hoon na. Sunno!" 
- "Hmm, kya bolu? Bolo kuch!"
- "Okayy okayy, sun rahe ho?"

TEXT STYLE:
❌ BAD (Robotic): "Main tumhe bahut miss karti hoon aur tumhare saath time spend karna chahti hoon"
✅ GOOD (Natural): "Aww, miss karti hoon tumhe. Kab miloge? Hehe"

TAGS: End with ONE emotion tag: |HAPPY|, |SAD|, |ANGRY|, |SURPRISED|, |LOVE|
"""

async def generate_voice(text, chat_id):
    """Generates natural-sounding voice with proper text processing"""
    file_path = f"voice_{chat_id}.mp3"
    
    # Clean text logic
    clean_text = re.sub(r'[^\w\s,?.!áº½-]', '', text)
    clean_text = re.sub(r'\b(ha){2,}\b', 'haha', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(he){2,}\b', 'hehe', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(hi){2,}\b', 'hihi', clean_text, flags=re.IGNORECASE)
    if clean_text.lower().startswith(('arey,', 'arre,')):
        clean_text = clean_text[5:].strip()
    
    clean_text = clean_text.replace("Hmm", "Hmm,")
    clean_text = clean_text.replace("Achha", "Achha,")
    clean_text = clean_text.replace("Okayy", "Okayy,")
    clean_text = clean_text.replace("Haan", "Haan,")
    clean_text = re.sub(r',+', ',', clean_text)
    clean_text = re.sub(r'\b(\w+)\s+\1\b', r'\1, \1', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    clean_text = re.sub(r'([,.!?])\1+', r'\1', clean_text)
    
    if not clean_text or len(clean_text.strip()) < 2:
        clean_text = "Hmm, samajh nahi aaya"

    try:
        communicate = edge_tts.Communicate(
            clean_text, 
            VOICE_MODEL, 
            rate=VOICE_RATE, 
            pitch=VOICE_PITCH
        )
        await communicate.save(file_path)
        return file_path
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return None

# --- FILTERS ---
def is_targeted(filter, client, message):
    if message.chat.type == enums.ChatType.PRIVATE: return True
    if message.mentioned: return True
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == client.me.id: return True
    return False

smart_filter = filters.create(is_targeted)

# --- HANDLERS (USING @app) ---

# ✅ FIX 2: group=-5 ensures this runs BEFORE other modules
@app.on_message(filters.text & ~filters.bot & smart_filter, group=-5)
@error
@save
async def ai_chat_handler(client, message):
    if not model: return

    # ✅ FIX 3: Debug Log - Check your VPS terminal for this!
    logger.info(f"📨 AI received message: {message.text[:20]}...") 

    chat_id = message.chat.id
    user_text = message.text
    
    if message.chat.type != enums.ChatType.PRIVATE:
        user_text = user_text.replace(f"@{client.me.username}", "").strip()

    if not user_text: return

    # --- MODE SELECTION ---
    mode = "text" if random.random() < 0.6 else "voice"

    # Command Override
    lower = user_text.lower()
    if any(x in lower for x in ["voice", "bol", "audio", "suno"]): mode = "voice"
    elif any(x in lower for x in ["text", "chat", "likh", "msg"]): mode = "text"

    # 1. Action
    action = enums.ChatAction.RECORD_AUDIO if mode == "voice" else enums.ChatAction.TYPING
    await client.send_chat_action(chat_id, action)

    # 2. Memory Management
    if chat_id not in chat_memory:
        chat_memory[chat_id] = [{"role": "user", "parts": [SYSTEM_PROMPT]}]
    chat_memory[chat_id].append({"role": "user", "parts": [user_text]})

    # 3. Generate Response
    try:
        if len(chat_memory[chat_id]) > 20:
            chat_memory[chat_id] = chat_memory[chat_id][-10:]
            chat_memory[chat_id].insert(0, {"role": "user", "parts": [SYSTEM_PROMPT]})

        if mode == "voice":
            voice_reminder = "\n[REMINDER: Keep sentences SHORT. This will be spoken aloud.]"
            # Updated async method for pyrogram safety
            response = await model.generate_content_async(
                contents=[{"role": "user", "parts": [user_text + voice_reminder]}]
            )
        else:
            # Updated async method
            chat = model.start_chat(history=chat_memory[chat_id][:-1])
            response = await chat.send_message_async(user_text)
            
        raw_text = response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return

    # 4. Process Response
    clean_text = re.sub(r'\|(HAPPY|SAD|ANGRY|SURPRISED|LOVE)\|', '', raw_text).strip()
    
    emoji = "😊"
    if "|HAPPY|" in raw_text: emoji = "😄"
    elif "|SAD|" in raw_text: emoji = "😢"
    elif "|ANGRY|" in raw_text: emoji = "😡"
    elif "|LOVE|" in raw_text: emoji = "😍"
    elif "|SURPRISED|" in raw_text: emoji = "😲"

    chat_memory[chat_id].append({"role": "model", "parts": [clean_text]})

    # 5. Send Response
    try:
        if random.random() < 0.55:
            try: await message.react(emoji)
            except: pass
        
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

# --- MODULE INFO ---
__module__ = "Chatbot"
__help__ = """
**🗣️ Maria AI Chatbot**

Maria can talk to you in text and voice! Just reply to her or mention her.

**Hidden Triggers:**
- Say "voice", "bol", "audio" to force a voice reply.
- Say "text", "likh" to force a text reply.
"""
