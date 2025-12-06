import io
import os
import base64
import httpx
from PIL import Image
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save

# API Endpoint
QUOTLY_API = "https://bot.lyo.su/quote/generate"

# Map Pyrogram Entities to API Entities
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
    """Downloads PFP, Resizes, and returns Base64"""
    try:
        if not user_id: return None
        
        photo = await client.download_media(user_id, file_name=f"pfp_{user_id}.jpg")
        if not photo: return None

        img = Image.open(photo)
        img = img.resize((100, 100)) # Keep it small for API stability
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        os.remove(photo)
        return img_str
    except Exception:
        return None

def parse_entities(message: Message):
    api_entities = []
    if not message.entities:
        return api_entities

    for entity in message.entities:
        if entity.type in ENTITY_MAP:
            data = {
                "type": ENTITY_MAP[entity.type],
                "offset": entity.offset,
                "length": entity.length
            }
            # Only add URL if it exists (Fixes 'Unknown API Error')
            if entity.type == enums.MessageEntityType.TEXT_LINK and entity.url:
                data["url"] = entity.url
                
            api_entities.append(data)
            
    return api_entities

@app.on_message(filters.command(["q", "quote"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def quotly_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ **Reply to a text message.**")

    # Reply Loading...
    msg = await message.reply_text("🎨 **Drawing Quote...**")
    
    reply = message.reply_to_message
    user = reply.from_user
    
    # Text Content
    text = reply.text or reply.caption or ""
    if not text:
        return await msg.edit("❌ **No text found to quote.**")

    # Get PFP
    pfp_data = None
    if user and user.photo:
        pfp_data = await get_pfp_base64(client, user.photo.big_file_id)
    
    # Safe Name
    if user:
        first = user.first_name or "Unknown"
        last = user.last_name or ""
        full_name = f"{first} {last}".strip()
        username = user.username or ""
        user_id = user.id
    else:
        full_name = "Deleted Account"
        username = ""
        user_id = 0

    # Build JSON Payload
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "messages": [
            {
                "entities": parse_entities(reply),
                "avatar": True,
                "from": {
                    "id": user_id,
                    "name": full_name,
                    "username": username,
                    "photo": {
                        "url": pfp_data 
                    }
                },
                "text": text,
                "replyMessage": {} 
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(QUOTLY_API, json=payload)
            
            if response.status_code != 200:
                try:
                    # Try to get the error message from API
                    err = response.json()
                    return await msg.edit(f"❌ **API Error:** {err.get('message', 'Unknown')}")
                except:
                    return await msg.edit(f"❌ **API Error:** {response.status_code}")

            # Success
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
"""
