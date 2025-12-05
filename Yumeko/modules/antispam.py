import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatPermissions
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save
from Yumeko.decorator.chatadmin import chatadmin
from aiohttp import ClientSession
from python_arq import ARQ

# --- CONFIGURATION ---
# We use the ARQ Key from your config to scan images
ARQ_API_URL = "https://arq.hamker.dev"
aiohttp_session = ClientSession()
arq = ARQ(ARQ_API_URL, config.ARQ_API_KEY, aiohttp_session)

# --- MEMORY DATABASE (Resets on Restart) ---
# To make this permanent, you need to add MongoDB functions like in chatbot.py
antispam_status = {}

# NSFW Emojis for Sticker Check
NSFW_EMOJIS = ["🍆", "🍑", "💦", "🥵", "🔞", "🍌", "🫦", "😩", "🖕", "🥒"]

# NSFW Keywords for Video/Caption Check
NSFW_KEYWORDS = [
    "porn", "sex", "nude", "xxx", "hentai", "pussy", "dick", "cock", 
    "boobs", "vagina", "whore", "slut", "onlyfans", "brazzers", "xnxx",
    "xvideos", "pornheub", "nsfw", "18+", "uncensored"
]

# --- HELPER FUNCTIONS ---

async def is_antispam_on(chat_id: int) -> bool:
    return antispam_status.get(chat_id, False)

async def tag_admins(client: Client, chat_id: int, warning_msg: str):
    """Tags all admins in the chat with the warning"""
    try:
        admins = []
        async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if not member.user.is_bot:
                admins.append(member.user.mention)
        
        if admins:
            # Send message tagging admins
            admin_tag = ", ".join(admins)
            await client.send_message(
                chat_id, 
                f"{warning_msg}\n\n🚨 **Admins Alert:** {admin_tag}"
            )
    except Exception:
        pass

# --- COMMANDS ---

@app.on_message(filters.command("antispam", prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def antispam_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("usage: /antispam [on / off]")
        return
    
    state = message.command[1].lower()
    chat_id = message.chat.id
    
    if state == "on":
        antispam_status[chat_id] = True
        await message.reply_text("🛡️ **Anti-NSFW System Enabled!**\nI will now scan images and stickers for inappropriate content.")
    elif state == "off":
        antispam_status[chat_id] = False
        await message.reply_text("⚠️ **Anti-NSFW System Disabled.**")
    else:
        await message.reply_text("usage: /antispam [on / off]")

# --- WATCHER (The Scanner) ---

@app.on_message((filters.photo | filters.sticker | filters.video | filters.document) & filters.group, group=11)
@error
async def nsfw_scanner(client: Client, message: Message):
    chat_id = message.chat.id
    
    # 1. Check if feature is ON
    if not await is_antispam_on(chat_id):
        return

    # 2. Ignore Admins (Optional: remove this if you want to scan admins too)
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return

    is_nsfw = False
    reason = "Detected inappropriate content."

    # --- SCAN LOGIC ---

    # A. STICKER CHECK (Fastest)
    if message.sticker:
        if message.sticker.emoji in NSFW_EMOJIS:
            is_nsfw = True
            reason = f"Sticker contains NSFW emoji ({message.sticker.emoji})"

    # B. CAPTION/FILENAME CHECK (Fast)
    caption = message.caption or ""
    if message.video or message.document:
        if hasattr(message, "document") and message.document.file_name:
            caption += " " + message.document.file_name
        
        for word in NSFW_KEYWORDS:
            if word in caption.lower():
                is_nsfw = True
                reason = f"Caption/Filename contains NSFW keyword: '{word}'"
                break

    # C. IMAGE SCANNING (The Heavy Part - Powered by ARQ)
    # Only scan if not already flagged and if it's a photo
    if not is_nsfw and message.photo:
        try:
            # Download small version to save bandwidth/RAM
            file = await client.download_media(message, file_name="nsfw_scan.jpg")
            
            # Send to API
            results = await arq.nsfw_scan(file=file)
            
            # Check Result
            if results.ok:
                # If NSFW probability is > 90%
                if results.result.nsfw_score > 0.9: 
                    is_nsfw = True
                    reason = f"AI detected NSFW Image (Score: {results.result.nsfw_score})"
            
            # Cleanup
            if os.path.exists(file):
                os.remove(file)
                
        except Exception as e:
            print(f"NSFW Scan Error: {e}")
            # If scan fails, we let it pass to avoid blocking normal images
            pass

    # --- PUNISHMENT ---
    if is_nsfw:
        try:
            # 1. Delete the media
            await message.delete()
            
            # 2. Tag User & Admins
            warning_text = (
                f"🚨 **NSFW CONTENT DETECTED!**\n\n"
                f"👤 **User:** {message.from_user.mention}\n"
                f"🚫 **Reason:** {reason}\n"
                f"⚠️ **Action:** Message Deleted."
            )
            
            await tag_admins(client, chat_id, warning_text)
            
        except Exception as e:
            print(f"Failed to punish user: {e}")

__module__ = "AntiSpam"
__help__ = """
**🛡️ Anti-NSFW System**

Automatically detects and deletes pornographic images, stickers, and videos.

/antispam on - Enable protection
/antispam off - Disable protection
"""
