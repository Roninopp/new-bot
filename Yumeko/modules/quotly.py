import io
import os
import base64
import httpx
from PIL import Image
from pyrogram import Client, filters, enums
from pyrogram.types import Message, MessageEntity
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save

# --- QUOTLY API CONFIG ---
QUOTLY_API = "https://bot.lyo.su/quote/generate"

# Entity Mapping (Pyrogram -> API)
ENTITY_MAP = {
    enums.MessageEntityType.BOLD: "bold",
    enums.MessageEntityType.ITALIC: "italic",
    enums.MessageEntityType.UNDERLINE: "underline",
    enums.MessageEntityType.STRIKETHROUGH: "strikethrough",
    enums.MessageEntityType.SPOILER: "spoiler",
    enums.MessageEntityType.URL: "url",
    enums.MessageEntityType.TEXT_LINK: "text_link",
    enums.MessageEntityType.MENTION: "mention",
    enums.MessageEntityType.CODE: "code",
    enums.MessageEntityType.PRE: "pre",
}

async def get_pfp_base64(client: Client, user_id: int):
    """Downloads PFP, Resizes it to 100x100 (Fixes API Error), and returns Base64"""
    try:
        photo = await client.download_media(user_id, file_name=f"pfp_{user_id}.jpg")
        if not photo: return None

        img = Image.open(photo)
        img = img.resize((120, 120)) # Critical Fix: Resize for API speed
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        os.remove(photo)
        return img_str
    except Exception:
        return None

def parse_entities(message: Message):
    """Converts Pyrogram Entities to Quotly API format"""
    api_entities = []
    if not message.entities:
        return api_entities

    for entity in message.entities:
        if entity.type in ENTITY_MAP:
            api_entities.append({
                "type": ENTITY_MAP[entity.type],
                "offset": entity.offset,
                "length": entity.length,
                "url": entity.url if entity.type == enums.MessageEntityType.TEXT_LINK else None
            })
    return api_entities

@app.on_message(filters.command(["q", "quote"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def quotly_handler(client: Client, message: Message):
    # 1. Check for Reply
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ **Reply to a text message to quote it.**")

    reply = message.reply_to_message
    
    # 2. Status
    msg = await message.reply_text("🎨 **Making Quote...**")

    # 3. Get Content
    text = reply.text or reply.caption or ""
    if not text:
        return await msg.edit("❌ **I can only quote text messages.**")

    # 4. Prepare Data
    user = reply.from_user
    pfp_data = await get_pfp_base64(client, user.photo.big_file_id if user.photo else None)
    entities = parse_entities(reply)

    # 5. Build JSON Payload
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "messages": [
            {
                "entities": entities, # Now supports Bold/Italic etc.
                "avatar": True,
                "from": {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name or ''}".strip(),
                    "username": user.username or "",
                    "photo": {
                        "url": pfp_data 
                    }
                },
                "text": text,
                "replyMessage": {} # (Can be expanded for replies later)
            }
        ]
    }

    # 6. Send to API
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(QUOTLY_API, json=payload)
            
            if response.status_code != 200:
                return await msg.edit("❌ **API Error.** The server is busy.")
            
            # Check content type (JSON = Error, WebP = Success)
            if "application/json" in response.headers.get("content-type", ""):
                return await msg.edit("❌ **Failed to render.**")

            # 7. Convert & Send
            sticker_io = io.BytesIO(response.read())
            sticker_io.name = "sticker.webp"
            
            await message.reply_sticker(sticker_io)
            await msg.delete()
            
    except Exception as e:
        await msg.edit(f"❌ **Error:** {e}")

__module__ = "Quotly"
__help__ = """
**🎨 Quotly Sticker**

/q - Reply to a message to make it a sticker.
Supports Bold, Italic, and Links!
"""
