import io
import os
import base64
import httpx
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save

# API Endpoint (Standard Quotly API)
QUOTLY_API = "https://bot.lyo.su/quote/generate"

async def image_to_base64(image_path):
    """Converts the downloaded PFP to Base64 for the API"""
    img = Image.open(image_path)
    img.save("sticker.png", "PNG")
    with open("sticker.png", "rb") as f:
        data = f.read()
    # Cleanup temp files
    os.remove("sticker.png")
    return base64.b64encode(data).decode()

@app.on_message(filters.command(["q", "quote"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def quotly_handler(client: Client, message: Message):
    # 1. Check for Reply
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ **Reply to a message to quote it.**")

    # 2. Send "Working" status
    msg = await message.reply_text("🎨 **Creating Quote...**")
    
    reply = message.reply_to_message
    user = reply.from_user
    
    # 3. Get Text content
    text = reply.text or reply.caption or ""
    if not text:
        return await msg.edit("❌ **I can only quote text messages.**")

    # 4. Process Profile Picture
    pfp_b64 = ""
    try:
        if user.photo:
            pfp_path = await client.download_media(user.photo.big_file_id)
            pfp_b64 = await image_to_base64(pfp_path)
            os.remove(pfp_path)
    except:
        pass # Continue even if PFP fails

    # 5. Build JSON Payload
    # This tells the API how to draw the sticker
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "messages": [
            {
                "entities": [],
                "avatar": True,
                "from": {
                    "id": user.id,
                    "name": user.first_name + (f" {user.last_name}" if user.last_name else ""),
                    "username": user.username or "",
                    "photo": {
                        "small_file_id": "", 
                        "big_file_id": "", 
                        "file": pfp_b64 
                    }
                },
                "text": text,
                "replyMessage": {}
            }
        ]
    }

    # 6. Send to API & Get Sticker
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(QUOTLY_API, json=payload)
            
            if response.status_code != 200:
                return await msg.edit("❌ **API Error.** Please try again later.")
            
            # Convert response to file
            sticker = io.BytesIO(response.read())
            sticker.name = "sticker.webp"
            
            # Send Sticker
            await message.reply_sticker(sticker)
            await msg.delete()
            
    except Exception as e:
        await msg.edit(f"❌ **Error:** {e}")

__module__ = "Quotly"
__help__ = """
**🎨 Quotly Sticker**

/q - Reply to a message to turn it into a sticker!
"""
