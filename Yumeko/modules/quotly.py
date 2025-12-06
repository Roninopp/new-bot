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

# The Official Quotly API
QUOTLY_API = "https://bot.lyo.su/quote/generate"

async def get_pfp_base64(client: Client, user_id: int):
    """
    Downloads PFP, Resizes it (Crucial for API speed), and converts to Base64
    """
    try:
        # Download the SMALL version of the photo (thumbs) to save bandwidth
        photo = await client.download_media(user_id, file_name=f"pfp_{user_id}.jpg")
        
        if not photo:
            return None

        # Resize Image (API rejects large payloads)
        img = Image.open(photo)
        img = img.resize((120, 120)) # Resize to icon size
        
        # Save to memory buffer as PNG
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Encode
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        
        # Cleanup
        os.remove(photo)
        return img_str
    except Exception:
        return None

@app.on_message(filters.command(["q", "quote"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def quotly_handler(client: Client, message: Message):
    # 1. Check for Reply
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ **Reply to a text message to quote it.**")

    # 2. Status Message
    status_msg = await message.reply_text("🎨 **Making Quote...**")
    
    reply = message.reply_to_message
    user = reply.from_user
    
    # 3. Get Content
    text = reply.text or reply.caption or ""
    if not text:
        return await status_msg.edit("❌ **I can only quote text messages.**")

    # 4. Get Profile Picture (Base64)
    # We use a placeholder if PFP fails, but we try hard to get it
    pfp_data = await get_pfp_base64(client, user.photo.big_file_id if user.photo else None)
    
    # 5. Build JSON Payload (Strict Format)
    # This structure MUST be exact for the API to render the user details
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
                        "url": pfp_data  # API expects Base64 string here
                    }
                },
                "text": text,
                "replyMessage": {}
            }
        ]
    }

    # 6. Send to API
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(QUOTLY_API, json=payload)
            
            # Check if API returned an image or an error text
            if response.status_code != 200:
                return await status_msg.edit("❌ **API Error.** The server is busy.")
            
            # If response is JSON (Error), don't try to send as sticker
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return await status_msg.edit("❌ **API Error:** Failed to render image.")

            # 7. Convert Response to Sticker File
            sticker_io = io.BytesIO(response.read())
            sticker_io.name = "sticker.webp"
            
            # 8. Send
            await message.reply_sticker(sticker_io)
            await status_msg.delete()
            
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {e}")

__module__ = "Quotly"
__help__ = """
**🎨 Quotly Sticker**

Turn any text message into a sticker!

/q - Reply to a message.
"""
