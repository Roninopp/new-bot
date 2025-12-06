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
    """Downloads PFP, Resizes to 100x100, and returns Base64"""
    try:
        photo = await client.download_media(user_id, file_name=f"pfp_{user_id}.jpg")
        if not photo: return None

        img = Image.open(photo)
        img = img.resize((100, 100)) # Small size for API stability
        
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
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ **Reply to a text message.**")

    status_msg = await message.reply_text("🎨 **Making Quote...**")
    
    reply = message.reply_to_message
    user = reply.from_user
    
    # Text Content
    text = reply.text or reply.caption or ""
    if not text:
        return await status_msg.edit("❌ **No text found to quote.**")

    # Get PFP
    pfp_data = await get_pfp_base64(client, user.photo.big_file_id if user.photo else None)
    
    # Build User Name
    first = user.first_name or "Unknown"
    last = user.last_name or ""
    full_name = f"{first} {last}".strip()

    # Build Message Object
    msg_data = {
        "entities": parse_entities(reply),
        "avatar": True,
        "from": {
            "id": user.id,
            "name": full_name,
            "username": user.username or "",
            "photo": {
                "url": pfp_data 
            }
        },
        "text": text,
        "replyMessage": {} # We keep this empty or handle nested replies later
    }

    # Build Final JSON
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "messages": [msg_data]
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(QUOTLY_API, json=payload)
            
            # DEBUGGING: If it fails, show WHY it failed
            if response.status_code != 200:
                return await status_msg.edit(f"❌ **API Error:** {response.status_code}")
            
            # If the API returned JSON (Error), print the error message
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    err_json = response.json()
                    err_msg = err_json.get('message', 'Unknown API Error')
                    return await status_msg.edit(f"❌ **Render Failed:** {err_msg}")
                except:
                    return await status_msg.edit("❌ **Failed to render (Unknown JSON).**")

            # Success
            sticker_io = io.BytesIO(response.read())
            sticker_io.name = "sticker.webp"
            
            await message.reply_sticker(sticker_io)
            await status_msg.delete()
            
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {e}")

__module__ = "Quotly"
__help__ = """
**🎨 Quotly Sticker**

/q - Reply to a message to make it a sticker.
"""
