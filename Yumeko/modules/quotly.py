"""
Plugin for creating quote stickers from messages using the external API.
This version adds support for Telegram Premium status emojis.
"""
import logging
import os
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

logger = logging.getLogger(__name__)

# --- API Client Setup ---
API_HEADERS = {
    "Accept-Language": "en-US",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
}

class QuotlyException(Exception):
    pass

# --- Helper Functions ---

async def get_message_sender_id(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_sender_name: return 1
        elif ctx.forward_from: return ctx.forward_from.id
        elif ctx.forward_from_chat: return ctx.forward_from_chat.id
        else: return 1
    elif ctx.from_user: return ctx.from_user.id
    elif ctx.sender_chat: return ctx.sender_chat.id
    else: return 1

async def get_message_sender_name(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_sender_name:
            return ctx.forward_sender_name
        elif ctx.forward_from:
            return (
                f"{ctx.forward_from.first_name} {ctx.forward_from.last_name}"
                if ctx.forward_from.last_name
                else ctx.forward_from.first_name
            )
        elif ctx.forward_from_chat:
            return ctx.forward_from_chat.title
        else:
            return "Anonymous"
    elif ctx.from_user:
        if ctx.from_user.last_name:
            return f"{ctx.from_user.first_name} {ctx.from_user.last_name}"
        else:
            return ctx.from_user.first_name
    elif ctx.sender_chat:
        return ctx.sender_chat.title
    else:
        return "Anonymous"

async def get_message_sender_username(ctx: Message):
    if ctx.forward_date:
        if (
            not ctx.forward_sender_name
            and not ctx.forward_from
            and ctx.forward_from_chat
            and ctx.forward_from_chat.username
        ):
            return ctx.forward_from_chat.username
        elif (
            not ctx.forward_sender_name
            and not ctx.forward_from
            and ctx.forward_from_chat
            or ctx.forward_sender_name
            or not ctx.forward_from
        ):
            return ""
        else:
            return ctx.forward_from.username or ""
    elif ctx.from_user and ctx.from_user.username:
        return ctx.from_user.username
    elif (
        ctx.from_user
        or ctx.sender_chat
        and not ctx.sender_chat.username
        or not ctx.sender_chat
    ):
        return ""
    else:
        return ctx.sender_chat.username

async def get_message_sender_photo(ctx: Message):
    if ctx.forward_date:
        if (
            not ctx.forward_sender_name
            and not ctx.forward_from
            and ctx.forward_from_chat
            and ctx.forward_from_chat.photo
        ):
            return { "big_file_id": ctx.forward_from_chat.photo.big_file_id }
        elif (
            not ctx.forward_sender_name
            and not ctx.forward_from
            and ctx.forward_from_chat
            or ctx.forward_sender_name
            or not ctx.forward_from
        ):
            return None
        else:
            return (
                { "big_file_id": ctx.forward_from.photo.big_file_id } if ctx.forward_from.photo else None
            )
    elif ctx.from_user and ctx.from_user.photo:
        return { "big_file_id": ctx.from_user.photo.big_file_id }
    elif (
        ctx.from_user
        or ctx.sender_chat
        and not ctx.sender_chat.photo
        or not ctx.sender_chat
    ):
        return None
    else:
        return { "big_file_id": ctx.sender_chat.photo.big_file_id }

async def get_text_or_caption(ctx: Message):
    if ctx.text:
        return ctx.text
    elif ctx.caption:
        return ctx.caption
    else:
        return ""

# --- API Payload Builder ---
async def pyrogram_to_quotly(messages, is_reply):
    if not isinstance(messages, list):
        messages = [messages]
    
    payload = {"type": "quote", "format": "webp", "backgroundColor": "#1b1429", "messages": []}

    for message in messages:
        message_payload = {
            "entities": [], "avatar": True, "from": {}, "text": await get_text_or_caption(message), "replyMessage": {}
        }
        entities = message.entities or message.caption_entities
        if entities:
            for entity in entities:
                message_payload["entities"].append({"type": entity.type.name.lower(), "offset": entity.offset, "length": entity.length})
        
        sender = message.from_user or message.sender_chat
        
        emoji_status_document_id = None
        if sender and sender.emoji_status:
            emoji_status_document_id = sender.emoji_status.custom_emoji_id
            
        message_payload["from"] = {
            "id": await get_message_sender_id(message),
            "name": await get_message_sender_name(message),
            "username": await get_message_sender_username(message),
            "type": message.chat.type.name.lower(),
            "photo": await get_message_sender_photo(message),
            "emojiStatus": { "document_id": emoji_status_document_id } if emoji_status_document_id else None
        }
        
        if message.reply_to_message and is_reply:
            reply_sender = message.reply_to_message.from_user or message.reply_to_message.sender_chat
            reply_emoji_id = None
            if reply_sender and reply_sender.emoji_status:
                reply_emoji_id = reply_sender.emoji_status.custom_emoji_id
                
            message_payload["replyMessage"] = {
                "name": await get_message_sender_name(message.reply_to_message),
                "text": await get_text_or_caption(message.reply_to_message),
                "chatId": await get_message_sender_id(message.reply_to_message),
                "emojiStatus": { "document_id": reply_emoji_id } if reply_emoji_id else None
            }
        
        payload["messages"].append(message_payload)
    
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.post("https://bot.lyo.su/quote/generate", json=payload, timeout=20) as r:
            if r.status == 200:
                return await r.read()
            else:
                error_text = await r.text()
                logger.error(f"Quotly API Error: {error_text}")
                raise QuotlyException(error_text)

class ModifiedMessage(Message):
    """A wrapper to ensure message objects are consistent."""
    def __init__(self, original_message, new_text=None):
        self.__dict__ = original_message.__dict__.copy()
        
        if new_text is not None:
            self.text = new_text
            self.entities = None
            self.caption = None
            self.caption_entities = None
        
        self.reply_to_message = original_message.reply_to_message


# --- Command Handler for /q and /q r ---
@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def msg_quotly_cmd(client: Client, message: Message):
    ww = await message.reply_text("**💬 Creating quote sticker...**")

    if not message.reply_to_message:
        return await ww.edit("**❌ Please reply to a message to quote it!**")

    is_reply_mode = len(message.command) > 1 and message.command[1].lower() == 'r'
    
    target_message = ModifiedMessage(message.reply_to_message)
    file_name = f"sticker_{message.id}.webp"

    try:
        make_quotly = await pyrogram_to_quotly([target_message], is_reply=is_reply_mode)
        
        # Save to disk to ensure it's treated as a file by the OS
        with open(file_name, "wb") as f:
            f.write(make_quotly)
        
        await client.send_sticker(
            chat_id=message.chat.id, 
            sticker=file_name, 
            reply_to_message_id=message.id
        )
        await ww.delete()
    except Exception as e:
        logger.error(f"Failed to create quote sticker: {e}")
        await ww.edit(f"**❌ Error:** `{e}`")
    finally:
        # Cleanup the file
        if os.path.exists(file_name):
            os.remove(file_name)

# --- Command Handler for /qt {custom_text} ---
@app.on_message(filters.command("qt", prefixes=config.config.COMMAND_PREFIXES))
async def custom_quote_cmd(client: Client, message: Message):
    ww = await message.reply_text("**💬 Creating custom quote...**")

    if not message.reply_to_message:
        return await ww.edit("**❌ Please reply to a message to add custom text!**")
    
    if len(message.command) < 2:
        return await ww.edit(
            "**❌ Please provide the text you want to quote!**\n\n"
            "**Examples:**\n"
            "• `/qt Hello there!`\n"
            "• `/qt -r Hello there!`"
        )

    full_text_input = message.text.split(None, 1)[1]
    
    is_reply_mode = False
    custom_text = ""

    if full_text_input.lower().strip().startswith("-r"):
        is_reply_mode = True
        parts = full_text_input.split(None, 1)
        if len(parts) > 1:
            custom_text = parts[1]
        else:
            return await ww.edit("**❌ Please provide text *after* the `-r` flag!**")
    else:
        is_reply_mode = False
        custom_text = full_text_input

    modified_message = ModifiedMessage(message.reply_to_message, custom_text)
    file_name = f"sticker_{message.id}.webp"

    try:
        make_quotly = await pyrogram_to_quotly([modified_message], is_reply=is_reply_mode)
        
        # Save to disk to ensure it's treated as a file by the OS
        with open(file_name, "wb") as f:
            f.write(make_quotly)
        
        await client.send_sticker(
            chat_id=message.chat.id, 
            sticker=file_name, 
            reply_to_message_id=message.id
        )
        await ww.delete()
    except Exception as e:
        logger.error(f"Failed to create custom quote sticker: {e}")
        await ww.edit(f"**❌ Error:** `{e}`")
    finally:
        # Cleanup the file
        if os.path.exists(file_name):
            os.remove(file_name)

# --- Help Documentation ---
__help__ = """
**💬 Quote Sticker Module:**

Create beautiful quote stickers like @QuotLyBot using API!

**Commands:**
• `/q` - Reply to a message to quote it
• `/q r` - Quote message with its reply included
• `/qt [text]` - Reply to a message and replace with custom text
• `/qt -r [text]` - Custom text quote with reply included
"""

__module__ = "Quote"
