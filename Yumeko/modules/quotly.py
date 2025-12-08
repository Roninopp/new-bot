"""
Advanced Quote Sticker Module with API support
Creates beautiful quote stickers like @QuotLyBot
Commands: /q, /q r, /qt, /qt -r
"""
import logging
from io import BytesIO
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

logger = logging.getLogger(__name__)

# API Configuration
API_HEADERS = {
    "Accept-Language": "en-US",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

class QuotlyException(Exception):
    """Custom exception for Quotly API errors"""
    pass

# ==================== Helper Functions ====================

async def get_message_sender_id(ctx: Message):
    """Get the sender's ID from various message types"""
    if ctx.forward_date:
        if ctx.forward_sender_name:
            return 1
        elif ctx.forward_from:
            return ctx.forward_from.id
        elif ctx.forward_from_chat:
            return ctx.forward_from_chat.id
        else:
            return 1
    elif ctx.from_user:
        return ctx.from_user.id
    elif ctx.sender_chat:
        return ctx.sender_chat.id
    else:
        return 1

async def get_message_sender_name(ctx: Message):
    """Get the sender's display name"""
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
    """Get the sender's username"""
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
    """Get the sender's profile photo"""
    if ctx.forward_date:
        if (
            not ctx.forward_sender_name
            and not ctx.forward_from
            and ctx.forward_from_chat
            and ctx.forward_from_chat.photo
        ):
            return {"big_file_id": ctx.forward_from_chat.photo.big_file_id}
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
                {"big_file_id": ctx.forward_from.photo.big_file_id}
                if ctx.forward_from.photo
                else None
            )
    elif ctx.from_user and ctx.from_user.photo:
        return {"big_file_id": ctx.from_user.photo.big_file_id}
    elif (
        ctx.from_user
        or ctx.sender_chat
        and not ctx.sender_chat.photo
        or not ctx.sender_chat
    ):
        return None
    else:
        return {"big_file_id": ctx.sender_chat.photo.big_file_id}

async def get_text_or_caption(ctx: Message):
    """Get text or caption from message"""
    if ctx.text:
        return ctx.text
    elif ctx.caption:
        return ctx.caption
    else:
        return ""

# ==================== API Functions ====================

async def pyrogram_to_quotly(messages, is_reply):
    """Convert Pyrogram messages to Quotly API format"""
    if not isinstance(messages, list):
        messages = [messages]
    
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "messages": []
    }

    for message in messages:
        message_payload = {
            "entities": [],
            "avatar": True,
            "from": {},
            "text": await get_text_or_caption(message),
            "replyMessage": {}
        }
        
        # Handle text entities (bold, italic, etc.)
        entities = message.entities or message.caption_entities
        if entities:
            for entity in entities:
                message_payload["entities"].append({
                    "type": entity.type.name.lower(),
                    "offset": entity.offset,
                    "length": entity.length
                })
        
        # Get sender info
        sender = message.from_user or message.sender_chat
        
        # Handle premium emoji status
        emoji_status_document_id = None
        if sender and hasattr(sender, 'emoji_status') and sender.emoji_status:
            emoji_status_document_id = sender.emoji_status.custom_emoji_id
            
        message_payload["from"] = {
            "id": await get_message_sender_id(message),
            "name": await get_message_sender_name(message),
            "username": await get_message_sender_username(message),
            "type": message.chat.type.name.lower(),
            "photo": await get_message_sender_photo(message),
            "emojiStatus": (
                {"document_id": emoji_status_document_id}
                if emoji_status_document_id
                else None
            )
        }
        
        # Handle reply message if needed
        if message.reply_to_message and is_reply:
            reply_sender = message.reply_to_message.from_user or message.reply_to_message.sender_chat
            reply_emoji_id = None
            if reply_sender and hasattr(reply_sender, 'emoji_status') and reply_sender.emoji_status:
                reply_emoji_id = reply_sender.emoji_status.custom_emoji_id
                
            message_payload["replyMessage"] = {
                "name": await get_message_sender_name(message.reply_to_message),
                "text": await get_text_or_caption(message.reply_to_message),
                "chatId": await get_message_sender_id(message.reply_to_message),
                "emojiStatus": (
                    {"document_id": reply_emoji_id}
                    if reply_emoji_id
                    else None
                )
            }
        
        payload["messages"].append(message_payload)
    
    # Make API request
    try:
        async with aiohttp.ClientSession(headers=API_HEADERS) as session:
            async with session.post(
                "https://bot.lyo.su/quote/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    error_text = await response.text()
                    logger.error(f"Quotly API Error: {error_text}")
                    raise QuotlyException(f"API returned status {response.status}")
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        raise QuotlyException(f"Network error: {str(e)}")

# ==================== Modified Message Class ====================

class ModifiedMessage(Message):
    """Wrapper to modify message text while keeping other attributes"""
    def __init__(self, original_message, new_text=None):
        self.__dict__ = original_message.__dict__.copy()
        
        if new_text is not None:
            self.text = new_text
            self.entities = None
            self.caption = None
            self.caption_entities = None
        
        self.reply_to_message = original_message.reply_to_message

# ==================== Command Handlers ====================

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def quote_command(client: Client, message: Message):
    """
    Create a quote sticker from a message
    
    Usage:
    /q - Reply to a message to quote it
    /q r - Reply to a message and include its reply
    """
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to quote it!**")
        return

    processing = await message.reply_text("**🎨 Creating quote sticker...**")
    
    # Check if reply mode is enabled
    is_reply_mode = len(message.command) > 1 and message.command[1].lower() == 'r'
    
    target_message = ModifiedMessage(message.reply_to_message)

    try:
        # Generate quote using API
        quote_data = await pyrogram_to_quotly([target_message], is_reply=is_reply_mode)
        
        # Send as sticker
        bio_sticker = BytesIO(quote_data)
        bio_sticker.name = "quote.webp"
        
        await message.reply_sticker(bio_sticker)
        await processing.delete()
        
    except QuotlyException as e:
        await processing.edit_text(f"**❌ API Error:**\n`{str(e)}`")
    except Exception as e:
        logger.error(f"Quote generation failed: {e}")
        await processing.edit_text(f"**❌ Error:**\n`{str(e)}`")

@app.on_message(filters.command("qt", prefixes=config.config.COMMAND_PREFIXES))
async def custom_quote_command(client: Client, message: Message):
    """
    Create a quote sticker with custom text
    
    Usage:
    /qt [text] - Reply to a message and add your own text
    /qt -r [text] - Same as above but include the replied message's reply
    """
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to add custom text!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "**❌ Provide text to quote!**\n\n"
            "**Examples:**\n"
            "• `/qt Hello there!`\n"
            "• `/qt -r Hello there!` (includes reply)"
        )
        return

    processing = await message.reply_text("**🎨 Creating custom quote...**")
    
    # Get the text after the command
    full_text_input = message.text.split(None, 1)[1]
    
    is_reply_mode = False
    custom_text = ""

    # Check for -r flag
    if full_text_input.lower().strip().startswith("-r"):
        is_reply_mode = True
        parts = full_text_input.split(None, 1)
        if len(parts) > 1:
            custom_text = parts[1]
        else:
            await processing.edit_text("**❌ Provide text after the `-r` flag!**")
            return
    else:
        custom_text = full_text_input

    # Create modified message with custom text
    modified_message = ModifiedMessage(message.reply_to_message, custom_text)

    try:
        # Generate quote using API
        quote_data = await pyrogram_to_quotly([modified_message], is_reply=is_reply_mode)
        
        # Send as sticker
        bio_sticker = BytesIO(quote_data)
        bio_sticker.name = "quote.webp"
        
        await message.reply_sticker(bio_sticker)
        await processing.delete()
        
    except QuotlyException as e:
        await processing.edit_text(f"**❌ API Error:**\n`{str(e)}`")
    except Exception as e:
        logger.error(f"Custom quote generation failed: {e}")
        await processing.edit_text(f"**❌ Error:**\n`{str(e)}`")

# ==================== Help Documentation ====================

__help__ = """
**💬 Quote Sticker Module:**

Create beautiful quote stickers like @QuotLyBot!

**Commands:**
• `/q` - Reply to a message to quote it
• `/q r` - Quote message with its reply included
• `/qt [text]` - Quote with custom text
• `/qt -r [text]` - Custom quote with reply

**Features:**
• 🎨 Beautiful Telegram-style design
• 👤 Shows profile pictures
• 💎 Supports premium emoji status
• ✨ Handles text formatting (bold, italic, etc.)
• 🔗 Can include replied messages
• 📝 Custom text replacement

**Examples:**
1. Basic quote:
   → Reply to message → `/q`

2. Quote with reply:
   → Reply to message → `/q r`

3. Custom text:
   → Reply to message → `/qt This is custom text!`

4. Custom text with reply:
   → Reply to message → `/qt -r Custom text here!`

**Note:** Uses external API for high-quality rendering!
"""

__module__ = "Quote"
