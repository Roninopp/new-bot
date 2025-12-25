from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from Yumeko import app
from Yumeko.database import total_users, total_chats
import asyncio
import config

# Help text for the module
__help__ = """
**📢 Broadcast System - Reach Everyone! 📢**

**Admin Only Commands:**

• `/broadcastall` - Broadcast to all groups + users
• `/broadcastgroups` - Broadcast only to groups
• `/broadcastusers` - Broadcast only to users in DM

**How to Use:**
1. Reply to any message/post with the broadcast command
2. Bot will forward that message to all groups/users
3. You'll get a progress report!

**Supports:**
✓ Text messages
✓ Photos/Videos
✓ Documents/Files
✓ Forwarded posts from channels
✓ Any type of media

**Note:** Only bot admins can use these commands!
"""

__module__ = "Broadcast"

# Check if user is admin/owner
async def is_admin(user_id: int) -> bool:
    """Check if user is in the admin list."""
    return user_id in config.config.OWNER_ID

@app.on_message(filters.command("broadcastall", prefixes=config.config.COMMAND_PREFIXES) & filters.reply)
async def broadcast_all(client: Client, message: Message):
    """Broadcast message to all groups and users."""
    # Check if user is admin
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ This command is only for bot admins!")
        return
    
    # Get the message to broadcast
    broadcast_msg = message.reply_to_message
    
    # Send initial status
    status_msg = await message.reply_text("📢 **Broadcasting Started...**\n\nFetching all chats and users...")
    
    # Get all users and groups
    all_users = await total_users.find_all()
    all_chats = await total_chats.find_all()
    
    total_users_count = len(all_users)
    total_chats_count = len(all_chats)
    
    await status_msg.edit_text(
        f"📢 **Broadcasting in Progress...**\n\n"
        f"👥 Total Users: {total_users_count}\n"
        f"💬 Total Groups: {total_chats_count}\n\n"
        f"⏳ Please wait..."
    )
    
    # Broadcast to users
    success_users = 0
    failed_users = 0
    blocked_users = 0
    deleted_users = 0
    
    for user in all_users:
        try:
            await broadcast_msg.forward(user['user_id'])
            success_users += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast_msg.forward(user['user_id'])
            success_users += 1
        except UserIsBlocked:
            blocked_users += 1
        except InputUserDeactivated:
            deleted_users += 1
        except PeerIdInvalid:
            failed_users += 1
        except Exception:
            failed_users += 1
    
    # Broadcast to groups
    success_groups = 0
    failed_groups = 0
    
    for chat in all_chats:
        try:
            await broadcast_msg.forward(chat['chat_id'])
            success_groups += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast_msg.forward(chat['chat_id'])
            success_groups += 1
        except Exception:
            failed_groups += 1
    
    # Send final report
    await status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"📊 **User Statistics:**\n"
        f"✓ Success: {success_users}\n"
        f"✗ Failed: {failed_users}\n"
        f"🚫 Blocked: {blocked_users}\n"
        f"❌ Deleted: {deleted_users}\n\n"
        f"📊 **Group Statistics:**\n"
        f"✓ Success: {success_groups}\n"
        f"✗ Failed: {failed_groups}\n\n"
        f"🎯 **Total Reached:** {success_users + success_groups}"
    )

@app.on_message(filters.command("broadcastgroups", prefixes=config.config.COMMAND_PREFIXES) & filters.reply)
async def broadcast_groups(client: Client, message: Message):
    """Broadcast message only to groups."""
    # Check if user is admin
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ This command is only for bot admins!")
        return
    
    # Get the message to broadcast
    broadcast_msg = message.reply_to_message
    
    # Send initial status
    status_msg = await message.reply_text("📢 **Broadcasting to Groups...**\n\nFetching all groups...")
    
    # Get all groups
    all_chats = await total_chats.find_all()
    total_chats_count = len(all_chats)
    
    await status_msg.edit_text(
        f"📢 **Broadcasting in Progress...**\n\n"
        f"💬 Total Groups: {total_chats_count}\n\n"
        f"⏳ Please wait..."
    )
    
    # Broadcast to groups
    success_groups = 0
    failed_groups = 0
    
    for chat in all_chats:
        try:
            await broadcast_msg.forward(chat['chat_id'])
            success_groups += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast_msg.forward(chat['chat_id'])
            success_groups += 1
        except Exception:
            failed_groups += 1
    
    # Send final report
    await status_msg.edit_text(
        f"✅ **Broadcast to Groups Completed!**\n\n"
        f"📊 **Group Statistics:**\n"
        f"✓ Success: {success_groups}\n"
        f"✗ Failed: {failed_groups}\n\n"
        f"🎯 **Total Groups Reached:** {success_groups}"
    )

@app.on_message(filters.command("broadcastusers", prefixes=config.config.COMMAND_PREFIXES) & filters.reply)
async def broadcast_users(client: Client, message: Message):
    """Broadcast message only to users in DM."""
    # Check if user is admin
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ This command is only for bot admins!")
        return
    
    # Get the message to broadcast
    broadcast_msg = message.reply_to_message
    
    # Send initial status
    status_msg = await message.reply_text("📢 **Broadcasting to Users...**\n\nFetching all users...")
    
    # Get all users
    all_users = await total_users.find_all()
    total_users_count = len(all_users)
    
    await status_msg.edit_text(
        f"📢 **Broadcasting in Progress...**\n\n"
        f"👥 Total Users: {total_users_count}\n\n"
        f"⏳ Please wait..."
    )
    
    # Broadcast to users
    success_users = 0
    failed_users = 0
    blocked_users = 0
    deleted_users = 0
    
    for user in all_users:
        try:
            await broadcast_msg.forward(user['user_id'])
            success_users += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast_msg.forward(user['user_id'])
            success_users += 1
        except UserIsBlocked:
            blocked_users += 1
        except InputUserDeactivated:
            deleted_users += 1
        except PeerIdInvalid:
            failed_users += 1
        except Exception:
            failed_users += 1
    
    # Send final report
    await status_msg.edit_text(
        f"✅ **Broadcast to Users Completed!**\n\n"
        f"📊 **User Statistics:**\n"
        f"✓ Success: {success_users}\n"
        f"✗ Failed: {failed_users}\n"
        f"🚫 Blocked: {blocked_users}\n"
        f"❌ Deleted: {deleted_users}\n\n"
        f"🎯 **Total Users Reached:** {success_users}"
    )

# Optional: Broadcast without reply (with text)
@app.on_message(filters.command("broadcastall", prefixes=config.config.COMMAND_PREFIXES) & ~filters.reply)
async def broadcast_all_text(client: Client, message: Message):
    """Broadcast text message to all groups and users."""
    # Check if user is admin
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ This command is only for bot admins!")
        return
    
    # Get the text after command
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text(
            "❌ **Usage:**\n\n"
            "**Method 1:** Reply to a message with `/broadcastall`\n"
            "**Method 2:** `/broadcastall Your message here`"
        )
        return
    
    broadcast_text = text[1]
    
    # Send initial status
    status_msg = await message.reply_text("📢 **Broadcasting Started...**\n\nFetching all chats and users...")
    
    # Get all users and groups
    all_users = await total_users.find_all()
    all_chats = await total_chats.find_all()
    
    total_users_count = len(all_users)
    total_chats_count = len(all_chats)
    
    await status_msg.edit_text(
        f"📢 **Broadcasting in Progress...**\n\n"
        f"👥 Total Users: {total_users_count}\n"
        f"💬 Total Groups: {total_chats_count}\n\n"
        f"⏳ Please wait..."
    )
    
    # Broadcast to users
    success_users = 0
    failed_users = 0
    blocked_users = 0
    deleted_users = 0
    
    for user in all_users:
        try:
            await client.send_message(user['user_id'], broadcast_text)
            success_users += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.send_message(user['user_id'], broadcast_text)
            success_users += 1
        except UserIsBlocked:
            blocked_users += 1
        except InputUserDeactivated:
            deleted_users += 1
        except PeerIdInvalid:
            failed_users += 1
        except Exception:
            failed_users += 1
    
    # Broadcast to groups
    success_groups = 0
    failed_groups = 0
    
    for chat in all_chats:
        try:
            await client.send_message(chat['chat_id'], broadcast_text)
            success_groups += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.send_message(chat['chat_id'], broadcast_text)
            success_groups += 1
        except Exception:
            failed_groups += 1
    
    # Send final report
    await status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"📊 **User Statistics:**\n"
        f"✓ Success: {success_users}\n"
        f"✗ Failed: {failed_users}\n"
        f"🚫 Blocked: {blocked_users}\n"
        f"❌ Deleted: {deleted_users}\n\n"
        f"📊 **Group Statistics:**\n"
        f"✓ Success: {success_groups}\n"
        f"✗ Failed: {failed_groups}\n\n"
        f"🎯 **Total Reached:** {success_users + success_groups}"
    )
