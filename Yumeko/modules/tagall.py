import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from Yumeko import app
import config

# Store active mention processes
active_mentions = {}

async def get_members(client: Client, chat_id: int, limit: int = 200):
    """Get list of members from a chat"""
    members = []
    try:
        async for member in client.get_chat_members(chat_id, limit=limit):
            if not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception as e:
        print(f"Error getting members: {e}")
    return members

async def mention_users(client: Client, message: Message, members: list, text: str, mode: str = "normal"):
    """Mention users with different modes"""
    chat_id = message.chat.id
    mentioned_count = 0
    
    if mode == "normal":
        # Normal mode: 5 users per message
        batch_size = 5
    elif mode == "fast":
        # Fast mode: 10 users per message
        batch_size = 10
    elif mode == "single":
        # Single mode: 1 user per message
        batch_size = 1
    else:
        batch_size = 5
    
    for i in range(0, len(members), batch_size):
        if chat_id not in active_mentions:
            break
            
        batch = members[i:i + batch_size]
        mentions = " ".join([f"[{user.first_name}](tg://user?id={user.id})" for user in batch])
        
        try:
            if text:
                msg_text = f"{text}\n\n{mentions}"
            else:
                msg_text = mentions
                
            await client.send_message(chat_id, msg_text)
            mentioned_count += len(batch)
            await asyncio.sleep(1.5 if mode == "normal" else 0.8 if mode == "fast" else 2)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error mentioning: {e}")
            continue
    
    return mentioned_count

@app.on_message(filters.command("tagall", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def tagall(client: Client, message: Message):
    """Tag all members in the group"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    
    # Get custom text
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "📢 **Attention Everyone!**"
    
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    
    # Get members
    members = await get_members(client, chat_id)
    
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**🏷️ Starting mention process...**")
    
    # Mark as active
    active_mentions[chat_id] = True
    
    # Start mentioning
    mentioned = await mention_users(client, message, members, text, mode="normal")
    
    # Remove from active
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    
    await status_msg.edit_text(f"**✅ Mentioned {mentioned} members successfully!**")

@app.on_message(filters.command("fastag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def fastag(client: Client, message: Message):
    """Fast tag all members (10 per message)"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "⚡ **Fast Mention!**"
    
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    members = await get_members(client, chat_id)
    
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**⚡ Starting fast mention...**")
    
    active_mentions[chat_id] = True
    mentioned = await mention_users(client, message, members, text, mode="fast")
    
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    
    await status_msg.edit_text(f"**✅ Fast mentioned {mentioned} members!**")

@app.on_message(filters.command("singletag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def singletag(client: Client, message: Message):
    """Tag members one by one (slow but spam-safe)"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "🎯 **Single Mention**"
    
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    members = await get_members(client, chat_id)
    
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**🎯 Starting single mentions (slow)...**")
    
    active_mentions[chat_id] = True
    mentioned = await mention_users(client, message, members, text, mode="single")
    
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    
    await status_msg.edit_text(f"**✅ Mentioned {mentioned} members individually!**")

@app.on_message(filters.command("cancel", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def cancel_mention(client: Client, message: Message):
    """Cancel ongoing mention process"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if chat_id in active_mentions:
        del active_mentions[chat_id]
        await message.reply_text("**🛑 Mention process cancelled!**")
    else:
        await message.reply_text("**⚠️ No active mention process found!**")

@app.on_message(filters.command("admintag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def admintag(client: Client, message: Message):
    """Tag only admins in the group"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "👑 **Calling All Admins!**"
    
    status_msg = await message.reply_text("**🔍 Fetching admins...**")
    
    # Get admins
    admins = []
    try:
        async for admin in client.get_chat_members(chat_id, filter="administrators"):
            if not admin.user.is_bot:
                admins.append(admin.user)
    except Exception as e:
        await status_msg.edit_text(f"**❌ Error:** `{str(e)}`")
        return
    
    if not admins:
        await status_msg.edit_text("**❌ No admins found!**")
        return
    
    # Mention all admins in one message
    mentions = " ".join([f"[{admin.first_name}](tg://user?id={admin.id})" for admin in admins])
    
    msg_text = f"{text}\n\n{mentions}"
    
    await message.reply_text(msg_text)
    await status_msg.delete()

@app.on_message(filters.command("botstag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def botstag(client: Client, message: Message):
    """Tag all bots in the group"""
    chat_id = message.chat.id
    
    # Check if user is admin
    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "🤖 **Calling All Bots!**"
    
    status_msg = await message.reply_text("**🔍 Fetching bots...**")
    
    # Get bots
    bots = []
    try:
        async for member in client.get_chat_members(chat_id):
            if member.user.is_bot:
                bots.append(member.user)
    except Exception as e:
        await status_msg.edit_text(f"**❌ Error:** `{str(e)}`")
        return
    
    if not bots:
        await status_msg.edit_text("**❌ No bots found!**")
        return
    
    # Mention all bots in one message
    mentions = " ".join([f"[{bot.first_name}](tg://user?id={bot.id})" for bot in bots])
    
    msg_text = f"{text}\n\n{mentions}"
    
    await message.reply_text(msg_text)
    await status_msg.delete()

__help__ = """
**📢 Mention All Module:**

Tag/mention members in your group with various modes!

**Commands:**
• `/tagall [text]` - Tag all members (5 per message)
• `/fastag [text]` - Fast tag (10 per message)
• `/singletag [text]` - Tag one by one (spam-safe)
• `/admintag [text]` - Tag only admins
• `/botstag [text]` - Tag all bots
• `/cancel` - Cancel ongoing mention process

**Features:**
• Multiple tagging modes for different needs
• Admin-only commands for safety
• Flood protection built-in
• Cancelable processes
• Custom messages support

**Examples:**
`/tagall Meeting in 5 minutes!`
`/fastag Everyone please vote!`
`/admintag Need admin help here`

**Note:** Only group admins can use these commands.
"""

__module__ = "Mention All"
